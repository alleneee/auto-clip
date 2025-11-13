"""
智能剪辑策略模块
提供基于内容的智能片段排序、节奏调整和质量优化

功能：
1. 智能片段排序 - 基于内容相似度和情感曲线
2. 节奏调整 - 自动调整片段时长和顺序以优化观看体验
3. 内容去重 - 检测并移除重复或相似的片段
4. 质量评估 - 评估片段质量并筛选最佳内容
"""
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from app.models.batch_processing import ClipSegment
from app.utils.logger import logger


class ClipPriority(Enum):
    """片段优先级"""
    CRITICAL = 5    # 关键片段
    HIGH = 4        # 高优先级
    MEDIUM = 3      # 中等优先级
    LOW = 2         # 低优先级
    FILLER = 1      # 填充片段


class ContentType(Enum):
    """内容类型"""
    ACTION = "action"           # 动作场景
    DIALOGUE = "dialogue"       # 对话场景
    LANDSCAPE = "landscape"     # 风景画面
    CLOSEUP = "closeup"         # 特写镜头
    TRANSITION = "transition"   # 过渡画面


@dataclass
class ClipMetrics:
    """片段质量指标"""
    visual_quality: float       # 视觉质量 (0-1)
    audio_quality: float        # 音频质量 (0-1)
    content_richness: float     # 内容丰富度 (0-1)
    emotional_impact: float     # 情感影响力 (0-1)
    overall_score: float        # 综合评分 (0-1)


class SmartClipStrategy:
    """智能剪辑策略"""

    def __init__(self):
        """初始化策略"""
        # 情感关键词映射
        self.emotion_keywords = {
            'positive': ['精彩', '亮点', '高潮', '惊艳', '震撼', '感动'],
            'negative': ['失误', '错误', '问题', '遗憾'],
            'neutral': ['过渡', '转场', '介绍', '说明']
        }

        # 内容类型关键词
        self.content_keywords = {
            ContentType.ACTION: ['动作', '运动', '跑', '跳', '快速'],
            ContentType.DIALOGUE: ['说话', '对话', '访谈', '采访', '解说'],
            ContentType.LANDSCAPE: ['风景', '全景', '远景', '环境'],
            ContentType.CLOSEUP: ['特写', '细节', '面部', '表情'],
            ContentType.TRANSITION: ['转场', '过渡', '切换']
        }

    def analyze_clip_emotion(self, segment: ClipSegment) -> Dict[str, float]:
        """
        分析片段的情感倾向

        Args:
            segment: 视频片段

        Returns:
            情感分数 {'positive': 0-1, 'negative': 0-1, 'neutral': 0-1}
        """
        reason = segment.reason.lower() if segment.reason else ""

        scores = {
            'positive': 0.0,
            'negative': 0.0,
            'neutral': 0.5  # 默认中性
        }

        # 基于关键词计算情感分数
        for emotion, keywords in self.emotion_keywords.items():
            matches = sum(1 for kw in keywords if kw in reason)
            if matches > 0:
                scores[emotion] = min(1.0, matches * 0.3)

        # 归一化
        total = sum(scores.values())
        if total > 0:
            scores = {k: v/total for k, v in scores.items()}

        return scores

    def classify_content_type(self, segment: ClipSegment) -> ContentType:
        """
        分类片段的内容类型

        Args:
            segment: 视频片段

        Returns:
            内容类型
        """
        reason = segment.reason.lower() if segment.reason else ""

        # 统计每种类型的关键词匹配数
        type_scores = {}
        for content_type, keywords in self.content_keywords.items():
            matches = sum(1 for kw in keywords if kw in reason)
            type_scores[content_type] = matches

        # 返回匹配最多的类型
        if max(type_scores.values()) > 0:
            return max(type_scores, key=type_scores.get)

        return ContentType.TRANSITION  # 默认为过渡

    def calculate_clip_metrics(self, segment: ClipSegment) -> ClipMetrics:
        """
        计算片段质量指标

        Args:
            segment: 视频片段

        Returns:
            质量指标
        """
        # 基于优先级和时长计算基础分数
        priority_score = segment.priority / 5.0  # 归一化到 0-1

        # 时长评分（理想时长3-8秒）
        duration = segment.duration
        if 3 <= duration <= 8:
            duration_score = 1.0
        elif duration < 3:
            duration_score = duration / 3.0
        else:
            duration_score = max(0.3, 1.0 - (duration - 8) * 0.1)

        # 情感影响力（基于正面情感）
        emotions = self.analyze_clip_emotion(segment)
        emotional_impact = emotions.get('positive', 0.5)

        # 内容丰富度（基于描述长度和关键词）
        reason_length = len(segment.reason) if segment.reason else 0
        content_richness = min(1.0, reason_length / 100)

        # 综合评分（加权平均）
        overall_score = (
            priority_score * 0.3 +
            duration_score * 0.2 +
            emotional_impact * 0.3 +
            content_richness * 0.2
        )

        return ClipMetrics(
            visual_quality=priority_score,
            audio_quality=duration_score,
            content_richness=content_richness,
            emotional_impact=emotional_impact,
            overall_score=overall_score
        )

    def sort_clips_by_narrative(
        self,
        segments: List[ClipSegment],
        narrative_style: str = "crescendo"
    ) -> List[ClipSegment]:
        """
        根据叙事风格排序片段

        Args:
            segments: 片段列表
            narrative_style: 叙事风格
                - "crescendo": 渐强式（从低到高）
                - "decrescendo": 渐弱式（从高到低）
                - "wave": 波浪式（高低起伏）
                - "chronological": 按时间顺序

        Returns:
            排序后的片段列表
        """
        if not segments:
            return []

        logger.info(f"智能排序片段，叙事风格: {narrative_style}")

        # 计算每个片段的质量指标
        segments_with_metrics = [
            (seg, self.calculate_clip_metrics(seg))
            for seg in segments
        ]

        if narrative_style == "crescendo":
            # 渐强式：按综合评分升序
            sorted_segments = sorted(
                segments_with_metrics,
                key=lambda x: x[1].overall_score
            )

        elif narrative_style == "decrescendo":
            # 渐弱式：按综合评分降序
            sorted_segments = sorted(
                segments_with_metrics,
                key=lambda x: x[1].overall_score,
                reverse=True
            )

        elif narrative_style == "wave":
            # 波浪式：高低交替
            sorted_by_score = sorted(
                segments_with_metrics,
                key=lambda x: x[1].overall_score
            )

            # 交替选择高分和低分片段
            result = []
            low_idx = 0
            high_idx = len(sorted_by_score) - 1

            while low_idx <= high_idx:
                # 先添加高分
                if high_idx >= low_idx:
                    result.append(sorted_by_score[high_idx])
                    high_idx -= 1

                # 再添加低分
                if low_idx <= high_idx:
                    result.append(sorted_by_score[low_idx])
                    low_idx += 1

            sorted_segments = result

        else:  # chronological
            # 按原始时间顺序
            sorted_segments = sorted(
                segments_with_metrics,
                key=lambda x: (x[0].video_index, x[0].start_time)
            )

        # 提取片段（去掉指标）
        result = [seg for seg, _ in sorted_segments]

        logger.info(
            f"片段排序完成:\n"
            f"  原始顺序: {[s.priority for s in segments]}\n"
            f"  新顺序: {[s.priority for s in result]}"
        )

        return result

    def remove_duplicate_clips(
        self,
        segments: List[ClipSegment],
        time_threshold: float = 5.0
    ) -> List[ClipSegment]:
        """
        移除重复或相似的片段

        Args:
            segments: 片段列表
            time_threshold: 时间相似度阈值（秒）

        Returns:
            去重后的片段列表
        """
        if not segments:
            return []

        logger.info(f"检测重复片段，时间阈值: {time_threshold}秒")

        unique_segments = []
        seen_ranges = []

        for segment in segments:
            # 检查是否与已有片段重叠或相近
            is_duplicate = False

            for seen_video_idx, seen_start, seen_end in seen_ranges:
                # 同一视频
                if segment.video_index == seen_video_idx:
                    # 检查时间重叠
                    if (abs(segment.start_time - seen_start) < time_threshold and
                        abs(segment.end_time - seen_end) < time_threshold):
                        is_duplicate = True
                        logger.debug(
                            f"检测到重复片段: "
                            f"{segment.start_time:.1f}-{segment.end_time:.1f} "
                            f"与 {seen_start:.1f}-{seen_end:.1f} 相似"
                        )
                        break

            if not is_duplicate:
                unique_segments.append(segment)
                seen_ranges.append((
                    segment.video_index,
                    segment.start_time,
                    segment.end_time
                ))

        removed_count = len(segments) - len(unique_segments)
        if removed_count > 0:
            logger.info(f"移除 {removed_count} 个重复片段")

        return unique_segments

    def optimize_clip_duration(
        self,
        segments: List[ClipSegment],
        target_total_duration: Optional[float] = None,
        min_clip_duration: float = 2.0,
        max_clip_duration: float = 10.0
    ) -> List[ClipSegment]:
        """
        优化片段时长

        Args:
            segments: 片段列表
            target_total_duration: 目标总时长（秒）
            min_clip_duration: 最小片段时长
            max_clip_duration: 最大片段时长

        Returns:
            优化后的片段列表
        """
        if not segments:
            return []

        logger.info(
            f"优化片段时长:\n"
            f"  目标总时长: {target_total_duration}秒\n"
            f"  片段时长范围: {min_clip_duration}-{max_clip_duration}秒"
        )

        optimized = []

        for segment in segments:
            # 裁剪过长的片段
            if segment.duration > max_clip_duration:
                # 从中间裁剪
                center = (segment.start_time + segment.end_time) / 2
                half_duration = max_clip_duration / 2

                new_start = max(segment.start_time, center - half_duration)
                new_end = min(segment.end_time, center + half_duration)

                optimized_segment = ClipSegment(
                    video_index=segment.video_index,
                    start_time=new_start,
                    end_time=new_end,
                    priority=segment.priority,
                    reason=f"{segment.reason} (优化时长)"
                )

                logger.debug(
                    f"裁剪过长片段: {segment.duration:.1f}s -> "
                    f"{optimized_segment.duration:.1f}s"
                )

            # 扩展过短的片段（如果可能）
            elif segment.duration < min_clip_duration:
                expand_duration = min_clip_duration - segment.duration
                new_start = segment.start_time
                new_end = segment.end_time + expand_duration

                optimized_segment = ClipSegment(
                    video_index=segment.video_index,
                    start_time=new_start,
                    end_time=new_end,
                    priority=segment.priority,
                    reason=f"{segment.reason} (扩展时长)"
                )

                logger.debug(
                    f"扩展过短片段: {segment.duration:.1f}s -> "
                    f"{optimized_segment.duration:.1f}s"
                )

            else:
                optimized_segment = segment

            optimized.append(optimized_segment)

        # 如果有目标总时长，按质量筛选片段
        if target_total_duration:
            current_duration = sum(s.duration for s in optimized)

            if current_duration > target_total_duration:
                # 按质量评分排序，保留高质量片段
                segments_with_scores = [
                    (seg, self.calculate_clip_metrics(seg).overall_score)
                    for seg in optimized
                ]
                segments_with_scores.sort(key=lambda x: x[1], reverse=True)

                selected = []
                accumulated_duration = 0

                for seg, score in segments_with_scores:
                    if accumulated_duration + seg.duration <= target_total_duration:
                        selected.append(seg)
                        accumulated_duration += seg.duration

                logger.info(
                    f"按目标时长筛选片段: {len(optimized)} -> {len(selected)}"
                )

                optimized = selected

        return optimized

    def create_optimal_clip_plan(
        self,
        segments: List[ClipSegment],
        narrative_style: str = "crescendo",
        target_duration: Optional[float] = None,
        remove_duplicates: bool = True
    ) -> Tuple[List[ClipSegment], Dict[str, Any]]:
        """
        创建优化的剪辑方案

        Args:
            segments: 原始片段列表
            narrative_style: 叙事风格
            target_duration: 目标时长
            remove_duplicates: 是否移除重复片段

        Returns:
            (优化后的片段列表, 统计信息)
        """
        logger.info("创建优化剪辑方案")

        # 1. 移除重复片段
        if remove_duplicates:
            segments = self.remove_duplicate_clips(segments)

        # 2. 优化片段时长
        segments = self.optimize_clip_duration(
            segments,
            target_total_duration=target_duration
        )

        # 3. 智能排序
        segments = self.sort_clips_by_narrative(
            segments,
            narrative_style=narrative_style
        )

        # 4. 生成统计信息
        total_duration = sum(s.duration for s in segments)
        metrics = [self.calculate_clip_metrics(s) for s in segments]
        avg_quality = sum(m.overall_score for m in metrics) / len(metrics) if metrics else 0

        stats = {
            'clip_count': len(segments),
            'total_duration': total_duration,
            'average_quality': avg_quality,
            'narrative_style': narrative_style,
            'content_types': {
                content_type.value: sum(
                    1 for s in segments
                    if self.classify_content_type(s) == content_type
                )
                for content_type in ContentType
            }
        }

        logger.info(
            f"剪辑方案优化完成:\n"
            f"  片段数: {stats['clip_count']}\n"
            f"  总时长: {stats['total_duration']:.2f}秒\n"
            f"  平均质量: {stats['average_quality']:.2f}\n"
            f"  叙事风格: {narrative_style}"
        )

        return segments, stats


# 单例实例
smart_clip_strategy = SmartClipStrategy()
