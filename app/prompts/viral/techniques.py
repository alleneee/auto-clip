"""
病毒式传播技术库
包含黄金三秒法则、节奏控制、情感曲线设计等病毒式传播技巧
"""

from typing import Dict, List
from enum import Enum


class ViralTechniques:
    """病毒式传播技术集合"""

    # 黄金三秒法则
    GOLDEN_3_SECONDS = """
开头 3 秒决定用户是否继续观看：
- 第 1 秒：强烈视觉冲击或悬念引入
- 第 2 秒：核心信息点快速传递
- 第 3 秒：制造期待感，让用户想看下去
"""

    # 节奏控制
    RHYTHM_CONTROL = {
        "sentence_length": "15-20字/句，避免冗长",
        "info_density": "每5-10秒一个信息点",
        "transition_speed": "场景切换频率: 3-5秒/次",
        "emotion_curve": "制造期待、惊喜、满足的情绪曲线",
        "silence_usage": "适当留白，给观众思考和反应时间"
    }

    # 结构范式
    STRUCTURE_PARADIGM = {
        "opening": {
            "duration": "0-3秒",
            "role": "钩子引入",
            "techniques": ["悬念", "反转", "数字冲击"]
        },
        "development": {
            "duration": "20-40%总时长",
            "role": "问题展开/背景铺垫",
            "techniques": ["故事叙述", "痛点共鸣", "场景还原"]
        },
        "climax": {
            "duration": "30-45秒位置",
            "role": "高潮/惊艳时刻",
            "techniques": ["结果展示", "技巧揭秘", "反转高潮"]
        },
        "ending": {
            "duration": "最后5-10秒",
            "role": "行动号召/回味",
            "techniques": ["总结要点", "引导互动", "留悬念"]
        }
    }

    # 情感曲线模板（基于视频时长）
    EMOTION_CURVES = {
        "short": {  # 15-30秒
            "name": "快速冲击型",
            "pattern": [
                {"time": "0-3s", "emotion": "好奇/惊讶", "intensity": 0.8},
                {"time": "3-15s", "emotion": "期待/兴奋", "intensity": 0.9},
                {"time": "15-30s", "emotion": "满足/回味", "intensity": 0.7}
            ],
            "tips": "快速进入高潮，不拖泥带水"
        },
        "medium": {  # 30-60秒
            "name": "起承转合型",
            "pattern": [
                {"time": "0-5s", "emotion": "好奇", "intensity": 0.7},
                {"time": "5-20s", "emotion": "铺垫/共鸣", "intensity": 0.5},
                {"time": "20-45s", "emotion": "高潮/惊喜", "intensity": 1.0},
                {"time": "45-60s", "emotion": "满足/期待下次", "intensity": 0.6}
            ],
            "tips": "适当铺垫，高潮在2/3位置"
        },
        "long": {  # 60-90秒
            "name": "多波峰型",
            "pattern": [
                {"time": "0-5s", "emotion": "引入", "intensity": 0.7},
                {"time": "5-25s", "emotion": "第一波峰", "intensity": 0.8},
                {"time": "25-40s", "emotion": "过渡", "intensity": 0.5},
                {"time": "40-70s", "emotion": "第二波峰", "intensity": 1.0},
                {"time": "70-90s", "emotion": "收尾升华", "intensity": 0.7}
            ],
            "tips": "多个小高潮，保持节奏变化"
        }
    }

    # 音频-视觉协同技巧
    AUDIO_VISUAL_SYNC = {
        "music_beat_match": "剪辑点与音乐节拍对齐",
        "sound_effect_timing": "音效在关键动作瞬间触发",
        "volume_dynamics": "音量随情绪变化（高潮期音量↑，铺垫期音量↓）",
        "silence_for_impact": "关键时刻静音1-2秒，制造冲击",
        "voice_rhythm": "配音语速与画面节奏匹配"
    }

    # 视觉冲击技巧
    VISUAL_IMPACT = {
        "color_contrast": "冷暖色对比，突出重点",
        "motion_speed": "慢动作用于展示细节，快动作制造紧张感",
        "camera_movement": "运镜变化增加动感（推、拉、摇、移）",
        "text_animation": "关键文字动效突出",
        "transition_style": "转场符合内容节奏（快切 vs 淡入淡出）"
    }

    @classmethod
    def get_emotion_curve_by_duration(cls, duration: int) -> Dict:
        """
        根据视频时长推荐情感曲线

        Args:
            duration: 视频时长（秒）

        Returns:
            推荐的情感曲线模板
        """
        if duration <= 30:
            return cls.EMOTION_CURVES["short"]
        elif duration <= 60:
            return cls.EMOTION_CURVES["medium"]
        else:
            return cls.EMOTION_CURVES["long"]

    @classmethod
    def generate_clip_rhythm_guide(cls, target_duration: int) -> Dict:
        """
        生成剪辑节奏指南

        Args:
            target_duration: 目标时长（秒）

        Returns:
            剪辑节奏建议
        """
        # 计算各阶段时长
        opening_duration = min(3, target_duration * 0.05)
        development_duration = target_duration * 0.35
        climax_start = target_duration * 0.5
        climax_duration = target_duration * 0.3
        ending_duration = target_duration * 0.15

        return {
            "opening": {
                "start": 0,
                "end": opening_duration,
                "focus": "钩子吸引",
                "clip_count": 1,
                "avg_clip_length": opening_duration
            },
            "development": {
                "start": opening_duration,
                "end": opening_duration + development_duration,
                "focus": "内容展开",
                "clip_count": max(2, int(development_duration / 5)),
                "avg_clip_length": 5
            },
            "climax": {
                "start": climax_start,
                "end": climax_start + climax_duration,
                "focus": "高潮呈现",
                "clip_count": max(2, int(climax_duration / 4)),
                "avg_clip_length": 4
            },
            "ending": {
                "start": target_duration - ending_duration,
                "end": target_duration,
                "focus": "收尾升华",
                "clip_count": 1,
                "avg_clip_length": ending_duration
            },
            "total_clips": max(5, int(target_duration / 5)),
            "transition_frequency": f"每{target_duration / max(5, int(target_duration / 5)):.1f}秒切换"
        }

    @classmethod
    def get_viral_checklist(cls) -> List[Dict[str, str]]:
        """
        获取病毒式传播检查清单

        Returns:
            检查项列表
        """
        return [
            {
                "category": "开头吸引力",
                "items": [
                    "前3秒是否有明确钩子？",
                    "是否制造了悬念或惊喜？",
                    "视觉冲击力是否足够？"
                ]
            },
            {
                "category": "节奏控制",
                "items": [
                    "信息密度是否合理（5-10秒/点）？",
                    "是否有节奏变化和呼吸感？",
                    "场景切换是否流畅自然？"
                ]
            },
            {
                "category": "情感设计",
                "items": [
                    "是否有清晰的情感曲线？",
                    "高潮位置是否合理（约2/3处）？",
                    "结尾是否有余韵或行动号召？"
                ]
            },
            {
                "category": "音视协同",
                "items": [
                    "剪辑点是否与音乐节拍对齐？",
                    "关键时刻音效是否到位？",
                    "音量变化是否符合情绪起伏？"
                ]
            },
            {
                "category": "视觉呈现",
                "items": [
                    "色彩对比是否突出重点？",
                    "运镜是否增加动感？",
                    "文字动效是否恰当？"
                ]
            }
        ]
