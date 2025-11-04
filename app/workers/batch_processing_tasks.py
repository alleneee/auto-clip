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
from app.utils.ai_clients.dashscope_client import DashScopeClient
from app.utils.logger import logger


# ======================
# 辅助函数
# ======================

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

        # 提取关键时刻（简化版，实际应该解析 AI 返回）
        # TODO: 实现更智能的关键时刻提取
        key_moments = []

        return {
            **compressed_video,
            'vl_analysis': analysis_result,
            'analysis_summary': analysis_result.get('output', {}).get('text', ''),
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

        # 解析剪辑方案（简化版）
        # TODO: 实现更健壮的 JSON 解析和验证
        import json
        clip_plan_text = clip_plan_result.get('output', {}).get('text', '{}')

        # 尝试提取 JSON
        try:
            # 查找 JSON 内容
            start_idx = clip_plan_text.find('{')
            end_idx = clip_plan_text.rfind('}') + 1
            if start_idx != -1 and end_idx > start_idx:
                clip_plan_json = json.loads(clip_plan_text[start_idx:end_idx])
            else:
                raise ValueError("未找到有效的 JSON")
        except Exception as parse_error:
            logger.warning(f"解析剪辑方案 JSON 失败: {parse_error}, 使用默认方案")
            # 生成默认剪辑方案（取每个视频的前30秒）
            clip_plan_json = {
                'strategy': '默认剪辑策略：取每个视频的精彩片段',
                'total_duration': min(target_duration or 180, sum(r['duration'] for r in valid_results)),
                'segments': [
                    {
                        'video_index': r['video_index'],
                        'start_time': 0,
                        'end_time': min(30, r['duration']),
                        'duration': min(30, r['duration']),
                        'reason': '视频开头精彩片段',
                        'priority': 5
                    }
                    for r in valid_results
                ],
                'reasoning': '由于 AI 生成方案解析失败，使用默认策略'
            }

        return {
            **clip_plan_json,
            'quality_score': 0.8,  # TODO: 实现质量评分
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

        return {
            'final_video_path': final_path,
            'final_video_url': final_url,
            'duration': stats['total_duration'],
            'file_size': stats['output_size'],
            'processing_time': stats['processing_time'],
            'error': None
        }

    except Exception as e:
        logger.error(f"执行剪辑方案失败: {str(e)}", exc_info=True)
        return {
            'final_video_path': None,
            'final_video_url': None,
            'duration': 0,
            'file_size': 0,
            'error': str(e)
        }


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
            # 最终任务：执行剪辑方案
            | execute_clip_plan_task.s(
                [vs.get('path') or vs.get('url') for vs in video_sources],
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
