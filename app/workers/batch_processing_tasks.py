"""
批处理任务模块
使用 Celery group/chord 编排多视频批处理工作流
"""
import os
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from celery import group, chord
import aiohttp

from app.workers.celery_app import celery_app
from app.config import settings
from app.models.video_source import VideoSource, VideoSourceType
from app.models.task import TaskStatus
from app.models.batch_processing import (
    VideoAnalysisResult,
    ClipPlan,
    ClipSegment,
    BatchProcessResponse,
    BatchProcessStatus
)
from app.services import (
    video_compression_service,
    temp_storage_service,
    video_editing_service
)
from app.services.video_production_orchestrator import VideoProductionOrchestrator
from app.utils.ai_clients.dashscope_client import DashScopeClient
from app.utils.logger import logger
from app.utils.json_parser import parse_json_with_model, JSONParseError


# ======================
# 辅助函数
# ======================


def extract_key_moments(analysis_text: str, video_duration: float) -> List[Dict[str, Any]]:
    """
    从AI分析文本中提取关键时刻

    支持的时间格式：
    - MM:SS (例如: 01:30)
    - HH:MM:SS (例如: 00:01:30)
    - 秒数 (例如: 90秒, 90s)

    Args:
        analysis_text: AI分析文本
        video_duration: 视频总时长（秒）

    Returns:
        关键时刻列表，每项包含 timestamp, description, confidence
    """
    import re

    if not analysis_text:
        return []

    key_moments = []

    # 时间戳模式：HH:MM:SS, MM:SS, 或秒数
    time_patterns = [
        # HH:MM:SS 格式
        (r'(\d{1,2}):(\d{2}):(\d{2})', lambda h, m, s: int(h) * 3600 + int(m) * 60 + int(s)),
        # MM:SS 格式
        (r'(?<!\d)(\d{1,2}):(\d{2})(?!\d)', lambda m, s: int(m) * 60 + int(s)),
        # 秒数格式 (90秒, 90s)
        (r'(\d+)\s*[秒s]', lambda s: int(s))
    ]

    # 关键词（用于判断这是一个关键时刻）
    moment_keywords = [
        '精彩', '高潮', '亮点', '关键', '重要', '特写', '转折',
        'highlight', 'key', 'important', 'climax', 'peak'
    ]

    # 按行分割文本
    lines = analysis_text.split('\n')

    for line in lines:
        line = line.strip()
        if not line or len(line) < 10:
            continue

        # 检查是否包含关键词
        has_keyword = any(kw in line.lower() for kw in moment_keywords)

        # 尝试匹配时间戳
        for pattern, converter in time_patterns:
            matches = re.finditer(pattern, line)

            for match in matches:
                try:
                    # 转换为秒数
                    timestamp = converter(*match.groups())

                    # 验证时间戳在视频范围内
                    if timestamp < 0 or timestamp > video_duration:
                        continue

                    # 提取描述（时间戳前后的文本）
                    start_pos = max(0, match.start() - 50)
                    end_pos = min(len(line), match.end() + 100)
                    description = line[start_pos:end_pos].strip()

                    # 清理描述
                    description = re.sub(r'\s+', ' ', description)

                    # 计算置信度
                    confidence = 0.5  # 基础置信度
                    if has_keyword:
                        confidence += 0.3
                    if len(description) > 30:
                        confidence += 0.2

                    key_moments.append({
                        'timestamp': timestamp,
                        'description': description,
                        'confidence': min(confidence, 1.0)
                    })

                except (ValueError, IndexError):
                    continue

    # 去重（相同或相近的时间戳）
    unique_moments = []
    seen_timestamps = set()

    for moment in sorted(key_moments, key=lambda x: x['timestamp']):
        timestamp = moment['timestamp']
        # 5秒内的时间戳视为重复
        if not any(abs(timestamp - seen) < 5 for seen in seen_timestamps):
            unique_moments.append(moment)
            seen_timestamps.add(timestamp)

    logger.info(f"从分析文本中提取 {len(unique_moments)} 个关键时刻")
    return unique_moments


def calculate_clip_plan_quality(
    clip_plan: Dict[str, Any],
    analysis_results: List[Dict[str, Any]],
    target_duration: Optional[float] = None
) -> float:
    """
    计算剪辑方案质量评分

    评分维度：
    1. 视频覆盖率 (30%): 使用了多少源视频
    2. 时长符合度 (25%): 与目标时长的匹配程度
    3. 片段多样性 (20%): 片段数量和分布
    4. 优先级质量 (15%): 高优先级片段比例
    5. AI分析质量 (10%): reasoning的完整性

    Args:
        clip_plan: 剪辑方案字典
        analysis_results: 分析结果列表
        target_duration: 目标时长

    Returns:
        质量评分 (0.0-1.0)
    """
    segments = clip_plan.get('segments', [])
    total_duration = clip_plan.get('total_duration', 0)
    reasoning = clip_plan.get('reasoning', '')

    if not segments:
        return 0.0

    scores = {}

    # 1. 视频覆盖率 (30%)
    valid_results = [r for r in analysis_results if r.get('status') == 'analyzed']
    if valid_results:
        used_videos = set(seg.get('video_index', -1) for seg in segments)
        coverage_ratio = len(used_videos) / len(valid_results)
        scores['coverage'] = min(coverage_ratio, 1.0) * 0.30
    else:
        scores['coverage'] = 0.0

    # 2. 时长符合度 (25%)
    if target_duration and target_duration > 0:
        duration_diff = abs(total_duration - target_duration)
        # 允许10%的误差范围
        tolerance = target_duration * 0.1
        if duration_diff <= tolerance:
            duration_score = 1.0
        else:
            # 超出容差范围，线性递减
            duration_score = max(0, 1.0 - (duration_diff - tolerance) / target_duration)
        scores['duration'] = duration_score * 0.25
    else:
        # 无目标时长，评分基于总时长合理性 (60-300秒较好)
        if 60 <= total_duration <= 300:
            scores['duration'] = 0.25
        elif total_duration < 60:
            scores['duration'] = (total_duration / 60) * 0.25
        else:
            scores['duration'] = max(0, (600 - total_duration) / 300) * 0.25

    # 3. 片段多样性 (20%)
    segment_count = len(segments)
    if segment_count >= 5:
        diversity_score = 1.0
    elif segment_count >= 3:
        diversity_score = 0.8
    elif segment_count >= 2:
        diversity_score = 0.6
    else:
        diversity_score = 0.4
    scores['diversity'] = diversity_score * 0.20

    # 4. 优先级质量 (15%)
    priorities = [seg.get('priority', 0) for seg in segments]
    if priorities:
        high_priority_count = sum(1 for p in priorities if p >= 7)
        priority_ratio = high_priority_count / len(priorities)
        avg_priority = sum(priorities) / len(priorities)
        # 综合考虑高优先级比例和平均优先级
        priority_score = (priority_ratio * 0.6 + (avg_priority / 10) * 0.4)
        scores['priority'] = min(priority_score, 1.0) * 0.15
    else:
        scores['priority'] = 0.0

    # 5. AI分析质量 (10%)
    if reasoning and len(reasoning) > 20:
        # 基于reasoning长度和关键词
        reasoning_keywords = ['精彩', '高潮', '重点', '关键', '亮点', 'highlight']
        keyword_count = sum(1 for kw in reasoning_keywords if kw in reasoning.lower())
        reasoning_score = min(0.5 + keyword_count * 0.1, 1.0)
        scores['reasoning'] = reasoning_score * 0.10
    else:
        scores['reasoning'] = 0.05  # 基础分

    # 计算总分
    total_score = sum(scores.values())

    logger.info(
        f"质量评分详情: "
        f"覆盖率={scores.get('coverage', 0):.3f}, "
        f"时长={scores.get('duration', 0):.3f}, "
        f"多样性={scores.get('diversity', 0):.3f}, "
        f"优先级={scores.get('priority', 0):.3f}, "
        f"推理={scores.get('reasoning', 0):.3f}, "
        f"总分={total_score:.3f}"
    )

    return round(total_score, 3)

def run_async(coro):
    """在 Celery 任务中运行异步函数"""
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # 如果事件循环已在运行，创建新的
        import nest_asyncio
        nest_asyncio.apply()
    return loop.run_until_complete(coro)


async def download_video(url: str, output_path: str) -> str:
    """
    下载视频文件

    Args:
        url: 视频 URL
        output_path: 输出路径

    Returns:
        str: 下载的文件路径
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                raise ValueError(f"下载失败: HTTP {response.status}")

            # 流式下载
            with open(output_path, 'wb') as f:
                async for chunk in response.content.iter_chunked(8192):
                    f.write(chunk)

    return output_path


# ======================
# Celery 任务
# ======================

@celery_app.task(
    bind=True,
    name='batch_processing.prepare_video',
    max_retries=3,
    default_retry_delay=60
)
def prepare_video_task(self, video_source_dict: Dict[str, Any], video_index: int) -> Dict[str, Any]:
    """
    准备视频任务：下载或验证本地视频

    Args:
        video_source_dict: VideoSource 字典
        video_index: 视频索引

    Returns:
        Dict: {
            'video_index': int,
            'local_path': str,
            'source': VideoSource dict,
            'error': Optional[str]
        }
    """
    try:
        logger.info(f"准备视频 #{video_index}: {video_source_dict}")

        video_source = VideoSource(**video_source_dict)
        local_path = None

        if video_source.type == VideoSourceType.LOCAL:
            # 本地文件：验证存在性
            if not os.path.exists(video_source.path):
                raise ValueError(f"本地文件不存在: {video_source.path}")
            local_path = video_source.path

        elif video_source.type in [VideoSourceType.OSS, VideoSourceType.URL]:
            # 远程文件：下载到本地
            filename = f"downloaded_{video_index}_{Path(video_source.url).name}"
            local_path = os.path.join(settings.temp_dir, filename)

            # 异步下载
            run_async(download_video(video_source.url, local_path))

        # 验证视频时长
        is_valid = run_async(
            video_compression_service.validate_video_duration(local_path)
        )

        if not is_valid:
            metadata = run_async(
                video_compression_service.get_video_metadata(local_path)
            )
            raise ValueError(
                f"视频时长 {metadata.duration}秒 超过最大限制 "
                f"{settings.MAX_VIDEO_DURATION}秒"
            )

        return {
            'video_index': video_index,
            'local_path': local_path,
            'source': video_source_dict,
            'error': None
        }

    except Exception as e:
        logger.error(f"准备视频 #{video_index} 失败: {str(e)}", exc_info=True)
        return {
            'video_index': video_index,
            'local_path': None,
            'source': video_source_dict,
            'error': str(e)
        }


@celery_app.task(
    bind=True,
    name='batch_processing.compress_and_upload',
    max_retries=2,
    default_retry_delay=120
)
def compress_and_upload_task(
    self,
    prepared_video: Dict[str, Any],
    compression_profile: str,
    temp_expiry_hours: int
) -> Dict[str, Any]:
    """
    压缩并上传到临时 OSS

    Args:
        prepared_video: prepare_video_task 的返回值
        compression_profile: 压缩策略
        temp_expiry_hours: 临时存储过期时间（小时）

    Returns:
        Dict: VideoAnalysisResult 部分数据 + OSS 信息
    """
    video_index = prepared_video['video_index']

    try:
        # 检查准备阶段是否有错误
        if prepared_video['error']:
            return {
                'video_index': video_index,
                'error': prepared_video['error'],
                'status': 'failed'
            }

        local_path = prepared_video['local_path']
        logger.info(f"压缩视频 #{video_index}: {local_path}")

        # 获取原始元信息
        original_metadata = run_async(
            video_compression_service.get_video_metadata(local_path)
        )

        # 压缩视频
        compressed_filename = f"compressed_{video_index}_{Path(local_path).name}"
        compressed_path = os.path.join(settings.compressed_dir, compressed_filename)

        _, compression_stats = run_async(
            video_compression_service.compress_video(
                local_path,
                compressed_path,
                profile_name=compression_profile
            )
        )

        # 上传到临时 OSS
        upload_result = run_async(
            temp_storage_service.upload_temp_file(
                compressed_path,
                prefix="compressed",
                expiry_hours=temp_expiry_hours
            )
        )

        return {
            'video_index': video_index,
            'video_source': prepared_video['source'],
            'duration': original_metadata.duration,
            'resolution': original_metadata.resolution,
            'fps': original_metadata.fps,
            'file_size': original_metadata.file_size,
            'compressed_oss_url': upload_result['signed_url'],
            'oss_key': upload_result['oss_key'],
            'compression_profile': compression_stats['profile_used'],
            'compression_ratio': compression_stats['compression_ratio'],
            'processing_time': compression_stats['processing_time'],
            'error': None,
            'status': 'compressed'
        }

    except Exception as e:
        logger.error(f"压缩和上传视频 #{video_index} 失败: {str(e)}", exc_info=True)
        return {
            'video_index': video_index,
            'error': str(e),
            'status': 'failed'
        }


@celery_app.task(
    bind=True,
    name='batch_processing.analyze_video',
    max_retries=2,
    default_retry_delay=60
)
def analyze_video_task(
    self,
    compressed_video: Dict[str, Any],
    vl_model: str
) -> Dict[str, Any]:
    """
    VL 模型分析视频

    Args:
        compressed_video: compress_and_upload_task 的返回值
        vl_model: VL 模型名称

    Returns:
        Dict: 完整的 VideoAnalysisResult 数据
    """
    video_index = compressed_video['video_index']

    try:
        # 检查压缩阶段是否有错误
        if compressed_video['error']:
            return {
                **compressed_video,
                'vl_analysis': {},
                'analysis_summary': '',
                'key_moments': []
            }

        logger.info(f"分析视频 #{video_index} 使用 {vl_model}")

        # 调用 VL 模型
        dashscope_client = DashScopeClient(api_key=settings.DASHSCOPE_API_KEY)

        # 构建分析提示
        prompt = (
            "请分析这个视频的内容，包括：\n"
            "1. 视频主题和核心内容\n"
            "2. 关键场景和重要时刻\n"
            "3. 视觉风格和画面质量\n"
            "4. 适合剪辑的精彩片段"
        )

        analysis_result = run_async(
            dashscope_client.call_vl_model(
                model=vl_model,
                video_url=compressed_video['compressed_oss_url'],
                prompt=prompt
            )
        )

        # 提取关键时刻（从AI分析文本中智能提取）
        analysis_text = analysis_result.get('output', {}).get('text', '')
        video_duration = compressed_video.get('duration', 0)

        key_moments = extract_key_moments(analysis_text, video_duration)

        return {
            **compressed_video,
            'vl_analysis': analysis_result,
            'analysis_summary': analysis_text,
            'key_moments': key_moments,
            'status': 'analyzed'
        }

    except Exception as e:
        logger.error(f"分析视频 #{video_index} 失败: {str(e)}", exc_info=True)
        return {
            **compressed_video,
            'vl_analysis': {},
            'analysis_summary': f"分析失败: {str(e)}",
            'key_moments': [],
            'error': compressed_video.get('error') or str(e),
            'status': 'analysis_failed'
        }


@celery_app.task(
    bind=True,
    name='batch_processing.generate_clip_plan'
)
def generate_clip_plan_task(
    self,
    analysis_results: List[Dict[str, Any]],
    text_model: str,
    target_duration: Optional[float],
    clip_strategy: str
) -> Dict[str, Any]:
    """
    生成剪辑方案（聚合任务）

    Args:
        analysis_results: 所有视频的分析结果列表
        text_model: 文本模型名称
        target_duration: 目标时长（秒）
        clip_strategy: 剪辑策略

    Returns:
        Dict: ClipPlan 数据
    """
    try:
        logger.info(f"生成剪辑方案: {len(analysis_results)} 个视频")

        # 过滤失败的分析结果
        valid_results = [
            r for r in analysis_results
            if r.get('status') in ['analyzed', 'compressed'] and not r.get('error')
        ]

        if not valid_results:
            raise ValueError("所有视频分析都失败，无法生成剪辑方案")

        # 构建聚合提示
        video_summaries = []
        for result in valid_results:
            video_summaries.append(
                f"视频 #{result['video_index']}:\n"
                f"  时长: {result['duration']:.1f}秒\n"
                f"  分析: {result['analysis_summary'][:200]}"
            )

        aggregated_context = "\n\n".join(video_summaries)

        clip_plan_prompt = (
            f"基于以下视频分析结果，生成一个剪辑方案：\n\n"
            f"{aggregated_context}\n\n"
            f"要求：\n"
            f"1. 剪辑策略: {clip_strategy}\n"
            f"2. 目标时长: {target_duration or '自动决定'}秒\n"
            f"3. 选择每个视频中最精彩的片段\n"
            f"4. 确保片段之间的连贯性\n"
            f"5. 返回 JSON 格式的剪辑方案\n\n"
            f"JSON 格式示例：\n"
            f'{{\n'
            f'  "strategy": "剪辑策略描述",\n'
            f'  "total_duration": 预计总时长,\n'
            f'  "segments": [\n'
            f'    {{\n'
            f'      "video_index": 视频索引,\n'
            f'      "start_time": 开始时间,\n'
            f'      "end_time": 结束时间,\n'
            f'      "duration": 片段时长,\n'
            f'      "reason": "选择理由",\n'
            f'      "priority": 优先级(0-10)\n'
            f'    }}\n'
            f'  ],\n'
            f'  "reasoning": "方案推理过程"\n'
            f'}}'
        )

        # 调用文本模型
        dashscope_client = DashScopeClient(api_key=settings.DASHSCOPE_API_KEY)

        clip_plan_result = run_async(
            dashscope_client.call_text_model(
                model=text_model,
                prompt=clip_plan_prompt
            )
        )

        # 解析剪辑方案（使用健壮的JSON解析器）
        clip_plan_text = clip_plan_result.get('output', {}).get('text', '{}')

        # 使用健壮的JSON解析和Pydantic验证
        try:
            clip_plan = parse_json_with_model(clip_plan_text, ClipPlan, strict=False)
            clip_plan_json = clip_plan.dict()
            logger.info("成功解析并验证AI生成的剪辑方案")
        except JSONParseError as parse_error:
            logger.warning(f"解析剪辑方案失败: {parse_error}, 使用默认方案")
            # 生成默认剪辑方案（取每个视频的前30秒）
            default_segments = [
                ClipSegment(
                    video_index=r['video_index'],
                    start_time=0,
                    end_time=min(30, r['duration']),
                    duration=min(30, r['duration']),
                    reason='视频开头精彩片段',
                    priority=5
                )
                for r in valid_results
            ]
            clip_plan = ClipPlan(
                strategy='默认剪辑策略：取每个视频的精彩片段',
                total_duration=min(target_duration or 180, sum(r['duration'] for r in valid_results)),
                segments=default_segments,
                reasoning='由于AI生成方案解析失败，使用默认策略'
            )
            clip_plan_json = clip_plan.dict()

        # 计算质量评分
        quality_score = calculate_clip_plan_quality(
            clip_plan_json,
            analysis_results,
            target_duration
        )

        return {
            **clip_plan_json,
            'quality_score': quality_score,
            'error': None
        }

    except Exception as e:
        logger.error(f"生成剪辑方案失败: {str(e)}", exc_info=True)
        return {
            'strategy': '',
            'total_duration': 0,
            'segments': [],
            'reasoning': f"生成失败: {str(e)}",
            'error': str(e)
        }


@celery_app.task(
    bind=True,
    name='batch_processing.execute_clip_plan'
)
def execute_clip_plan_task(
    self,
    clip_plan: Dict[str, Any],
    video_paths: List[str],
    output_quality: str
) -> Dict[str, Any]:
    """
    执行剪辑方案（最终任务）

    Args:
        clip_plan: ClipPlan 数据
        video_paths: 原始视频路径列表
        output_quality: 输出质量

    Returns:
        Dict: {
            'final_video_path': str,
            'final_video_url': str (OSS),
            'duration': float,
            'file_size': int,
            'error': Optional[str]
        }
    """
    try:
        if clip_plan.get('error'):
            raise ValueError(f"剪辑方案错误: {clip_plan['error']}")

        logger.info(f"执行剪辑方案: {len(clip_plan['segments'])} 个片段")

        # 转换为 ClipSegment 对象
        segments = [ClipSegment(**seg) for seg in clip_plan['segments']]

        # 生成输出路径
        output_filename = f"final_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        output_path = os.path.join(settings.processed_dir, output_filename)

        # 执行剪辑方案
        final_path, stats = run_async(
            video_editing_service.process_clip_plan(
                video_paths,
                segments,
                output_path,
                output_quality
            )
        )

        # 上传最终视频到 OSS（永久存储）
        if temp_storage_service.is_oss_configured():
            # 这里应该上传到永久存储区域，而不是临时区域
            # 简化版：使用临时存储但设置更长过期时间
            upload_result = run_async(
                temp_storage_service.upload_temp_file(
                    final_path,
                    prefix="final",
                    expiry_hours=24 * 7  # 7天过期
                )
            )
            final_url = upload_result['public_url']
        else:
            final_url = f"file://{final_path}"

        # 在返回结果中包含 analysis_results，供下游任务使用
        result = {
            'final_video_path': final_path,
            'final_video_url': final_url,
            'duration': stats['total_duration'],
            'file_size': stats['output_size'],
            'processing_time': stats['processing_time'],
            'video_paths': video_paths,  # 传递给下游任务
            'analysis_results': clip_plan.get('analysis_results', []),  # 保存分析结果
            'error': None
        }

        return result

    except Exception as e:
        logger.error(f"执行剪辑方案失败: {str(e)}", exc_info=True)
        return {
            'final_video_path': None,
            'final_video_url': None,
            'duration': 0,
            'file_size': 0,
            'error': str(e)
        }


@celery_app.task(
    bind=True,
    name='batch_processing.produce_final_video_with_narration',
    max_retries=2,
    default_retry_delay=60
)
def produce_final_video_with_narration_task(
    self,
    clip_result: Dict[str, Any],
    video_paths: List[str] = None,
    config: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    完整视频生产任务：基于剪辑结果生成带旁白的最终视频

    这是完整的视频生产流程，包括：
    1. 使用剪辑结果作为基础视频
    2. 基于视频内容生成解说脚本
    3. 生成TTS口播音频
    4. 合成视频与音频
    5. 添加背景音乐（可选）

    Args:
        clip_result: execute_clip_plan_task 的返回结果（包含 analysis_results）
        video_paths: 源视频路径列表（通过 Celery 的 s() 传递）
        config: 配置（通过 Celery 的 s() 传递），包含:
            - add_narration: bool, 是否添加配音
            - narration_style: str, 解说风格
            - narration_voice: str, TTS音色
            - background_music_path: str, 背景音乐路径
            - original_audio_volume: float, 原音量

    Returns:
        Dict: {
            'final_video_path': str,
            'final_video_url': str,
            'duration': float,
            'file_size': int,
            'has_narration': bool,
            'has_background_music': bool,
            'processing_time': float,
            'error': Optional[str]
        }
    """
    try:
        # 检查上游任务是否失败
        if clip_result.get('error'):
            raise ValueError(f"上游剪辑任务失败: {clip_result['error']}")

        # 提取参数（从 clip_result 或使用默认值）
        if video_paths is None:
            video_paths = clip_result.get('video_paths', [])
        if config is None:
            config = {}

        logger.info(
            f"开始完整视频生产流程:\n"
            f"  基础剪辑视频: {clip_result.get('final_video_path')}\n"
            f"  是否添加配音: {config.get('add_narration', True)}\n"
            f"  解说风格: {config.get('narration_style', 'professional')}"
        )

        # 如果不需要配音和背景音乐，直接返回基础剪辑结果
        if not config.get('add_narration', True) and not config.get('background_music_path'):
            logger.info("无需额外处理，直接使用基础剪辑结果")
            return clip_result

        # 初始化视频生产编排器
        orchestrator = VideoProductionOrchestrator()

        # 从 clip_result 中提取分析结果
        analysis_results = clip_result.get('analysis_results', [])

        # 构建剪辑决策（从分析结果和剪辑结果重建）
        clip_decision = {
            'theme': _extract_theme_from_analysis(analysis_results) if analysis_results else "精彩视频",
            'total_duration': clip_result.get('duration', 0),
            'clips': _reconstruct_clips_info(analysis_results) if analysis_results else []
        }

        # 生成最终输出路径
        output_filename = f"final_with_narration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        output_path = os.path.join(settings.processed_dir, output_filename)

        # 调用完整的视频生产流程
        production_result = run_async(
            orchestrator.produce_video_from_decision(
                source_videos=video_paths,
                clip_decision=clip_decision,
                output_path=output_path,
                narration_style=config.get('narration_style', 'professional'),
                narration_voice=config.get('narration_voice', 'Cherry'),
                add_narration=config.get('add_narration', True),
                background_music_path=config.get('background_music_path'),
                original_audio_volume=config.get('original_audio_volume', 0.3)
            )
        )

        # 上传最终视频到 OSS
        final_path = production_result['final_video_path']
        if temp_storage_service.is_oss_configured():
            upload_result = run_async(
                temp_storage_service.upload_temp_file(
                    final_path,
                    prefix="final_narration",
                    expiry_hours=24 * 7  # 7天过期
                )
            )
            final_url = upload_result['public_url']
        else:
            final_url = f"file://{final_path}"

        # 收集统计信息
        stats = production_result['statistics']

        result = {
            'final_video_path': final_path,
            'final_video_url': final_url,
            'duration': stats['final_duration'],
            'file_size': stats['final_size'],
            'has_narration': stats.get('has_narration', False),
            'has_background_music': stats.get('has_background_music', False),
            'script_word_count': stats.get('script_word_count', 0),
            'processing_time': production_result['processing_time'],
            'error': None
        }

        logger.info(
            f"完整视频生产完成:\n"
            f"  最终视频: {final_path}\n"
            f"  文件大小: {stats['final_size_mb']:.2f}MB\n"
            f"  视频时长: {stats['final_duration']:.2f}秒\n"
            f"  配音状态: {'已添加' if stats['has_narration'] else '未添加'}\n"
            f"  脚本字数: {stats.get('script_word_count', 0)}字"
        )

        return result

    except Exception as e:
        logger.error(f"完整视频生产失败: {str(e)}", exc_info=True)
        return {
            'final_video_path': None,
            'final_video_url': None,
            'duration': 0,
            'file_size': 0,
            'has_narration': False,
            'has_background_music': False,
            'processing_time': 0,
            'error': str(e)
        }


def _extract_theme_from_analysis(analysis_results: List[Dict[str, Any]]) -> str:
    """从分析结果中提取视频主题"""
    themes = []
    for result in analysis_results:
        if result.get('analysis_summary'):
            # 提取前100个字符作为主题
            summary = result['analysis_summary'][:100]
            themes.append(summary)

    if themes:
        return " | ".join(themes[:3])  # 最多3个视频的主题
    return "精彩视频合集"


def _reconstruct_clips_info(analysis_results: List[Dict[str, Any]]) -> List[Dict]:
    """从分析结果重建片段信息（用于脚本生成）"""
    clips = []
    for idx, result in enumerate(analysis_results):
        if result.get('key_moments'):
            for moment in result['key_moments']:
                clips.append({
                    'video_index': idx,
                    'timestamp': moment.get('timestamp', 0),
                    'description': moment.get('description', ''),
                    'confidence': moment.get('confidence', 0.5)
                })

    # 如果没有关键时刻，使用分析摘要
    if not clips:
        for idx, result in enumerate(analysis_results):
            if result.get('analysis_summary'):
                clips.append({
                    'video_index': idx,
                    'timestamp': 0,
                    'description': result['analysis_summary'][:200],
                    'confidence': 0.8
                })

    return clips


# ======================
# 主编排任务
# ======================

@celery_app.task(
    bind=True,
    name='batch_processing.batch_process_videos'
)
def batch_process_videos_task(
    self,
    video_sources: List[Dict[str, Any]],
    config: Dict[str, Any]
) -> str:
    """
    批处理视频主任务（使用 Celery chord 编排）

    Args:
        video_sources: VideoSource 字典列表
        config: 批处理配置

    Returns:
        str: 任务ID
    """
    task_id = self.request.id

    try:
        logger.info(f"开始批处理任务 {task_id}: {len(video_sources)} 个视频")

        # 阶段1: 并行准备所有视频（下载/验证）
        prepare_tasks = group([
            prepare_video_task.s(video_source, idx)
            for idx, video_source in enumerate(video_sources)
        ])

        # 阶段2: 并行压缩和上传
        # 阶段3: 并行 VL 分析
        # 阶段4: 聚合分析结果，生成剪辑方案
        # 阶段5: 执行剪辑方案

        # 获取视频路径列表
        video_paths = [vs.get('path') or vs.get('url') for vs in video_sources]

        # 决定是否使用完整视频生产流程
        use_full_production = config.get('add_narration', False) or config.get('background_music_path')

        if use_full_production:
            # 完整流程：包含脚本生成、TTS、音频合成
            logger.info("使用完整视频生产流程（包含配音和音乐）")

            # 使用 chord 串联所有阶段
            workflow = chord([
                # 准备 → 压缩上传 → VL分析（链式调用）
                prepare_video_task.s(video_source, idx)
                | compress_and_upload_task.s(
                    config.get('global_compression_profile', 'balanced'),
                    config.get('temp_storage_expiry_hours', 24)
                )
                | analyze_video_task.s(config.get('vl_model', 'qwen-vl-plus'))
                for idx, video_source in enumerate(video_sources)
            ])(
                # 聚合任务：生成剪辑方案
                generate_clip_plan_task.s(
                    config.get('text_model', 'qwen-plus'),
                    config.get('target_duration'),
                    config.get('clip_strategy', 'highlights')
                )
                # 基础剪辑任务
                | execute_clip_plan_task.s(
                    video_paths,
                    config.get('output_quality', 'high')
                )
                # 完整视频生产任务（新增）
                | produce_final_video_with_narration_task.s(
                    video_paths=video_paths,
                    config=config
                )
            )
        else:
            # 简化流程：仅剪辑拼接
            logger.info("使用简化流程（仅剪辑拼接）")

            workflow = chord([
                # 准备 → 压缩上传 → VL分析（链式调用）
                prepare_video_task.s(video_source, idx)
                | compress_and_upload_task.s(
                    config.get('global_compression_profile', 'balanced'),
                    config.get('temp_storage_expiry_hours', 24)
                )
                | analyze_video_task.s(config.get('vl_model', 'qwen-vl-plus'))
                for idx, video_source in enumerate(video_sources)
            ])(
                # 聚合任务：生成剪辑方案
                generate_clip_plan_task.s(
                    config.get('text_model', 'qwen-plus'),
                    config.get('target_duration'),
                    config.get('clip_strategy', 'highlights')
                )
                # 最终任务：执行剪辑方案
                | execute_clip_plan_task.s(
                    video_paths,
                    config.get('output_quality', 'high')
                )
            )

        # 异步执行工作流
        result = workflow.apply_async()

        logger.info(f"批处理工作流已启动: task_id={task_id}, workflow_id={result.id}")

        return task_id

    except Exception as e:
        logger.error(f"批处理任务 {task_id} 启动失败: {str(e)}", exc_info=True)
        raise


# ======================
# 任务服务专用任务
# ======================


@celery_app.task(
    bind=True,
    name='task_service.process_video_pipeline',
    max_retries=2,
    default_retry_delay=60
)
def process_video_pipeline_task(
    self,
    task_id: str,
    video_ids: List[str],
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    处理视频流水线任务（TaskService专用）

    这是一个简化的任务，用于从TaskService触发视频处理流程

    Args:
        task_id: 任务ID（来自TaskService）
        video_ids: 视频ID列表
        config: 处理配置

    Returns:
        Dict: 任务结果信息
    """
    try:
        logger.info(
            f"开始处理任务 {task_id}",
            video_count=len(video_ids),
            celery_task_id=self.request.id
        )

        # 这里可以调用实际的批处理流程
        # 或者实现自定义的处理逻辑

        # 示例：简单返回成功状态
        # 实际应用中，这里应该调用具体的视频处理逻辑

        result = {
            'task_id': task_id,
            'celery_task_id': self.request.id,
            'video_ids': video_ids,
            'status': TaskStatus.PROCESSING.value,
            'message': '任务已提交到Celery队列',
            'config': config
        }

        logger.info(f"任务 {task_id} 提交成功: {self.request.id}")

        return result

    except Exception as e:
        logger.error(
            f"任务 {task_id} 处理失败: {str(e)}",
            exc_info=True
        )
        return {
            'task_id': task_id,
            'status': TaskStatus.FAILED.value,
            'error': str(e)
        }
