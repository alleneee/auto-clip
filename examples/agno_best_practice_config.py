#!/usr/bin/env python3
"""
Agno智能剪辑Agent系统 - 最佳配置实践

最优性价比配置：
- ContentAnalyzer: Gemini 2.0 Flash（原生视频支持）
- CreativeStrategist: DeepSeek Chat（超低成本）
- TechnicalPlanner: DeepSeek Chat（超低成本）
- QualityReviewer: DeepSeek Chat（超低成本）

成本估算：~$0.02 / 60秒视频
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agents import AgnoClipTeam
from rich.console import Console

console = Console()


def create_optimized_team():
    """创建性价比最优的Agent团队"""

    # 检查环境变量
    gemini_key = os.getenv("GEMINI_API_KEY")
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")

    if not gemini_key:
        console.print("❌ GEMINI_API_KEY未设置", style="bold red")
        console.print("\n获取密钥：https://aistudio.google.com/app/apikey", style="yellow")
        return None

    if not deepseek_key:
        console.print("❌ DEEPSEEK_API_KEY未设置", style="bold red")
        console.print("\n获取密钥：https://platform.deepseek.com/", style="yellow")
        return None

    console.print("✅ API密钥配置正确", style="green")

    # 创建团队（显式指定API密钥）
    team = AgnoClipTeam(
        analyzer_model="gemini/gemini-2.0-flash-exp",
        strategist_model="deepseek/deepseek-chat",
        planner_model="deepseek/deepseek-chat",
        reviewer_model="deepseek/deepseek-chat",
        api_keys={
            "analyzer": gemini_key,
            "strategist": deepseek_key,
            "planner": deepseek_key,
            "reviewer": deepseek_key
        }
    )

    console.print("\n🤖 Agent团队配置：", style="bold cyan")
    console.print("  • ContentAnalyzer: Gemini 2.0 Flash ($0.001/video)", style="cyan")
    console.print("  • CreativeStrategist: DeepSeek Chat ($0.005/video)", style="cyan")
    console.print("  • TechnicalPlanner: DeepSeek Chat ($0.003/video)", style="cyan")
    console.print("  • QualityReviewer: DeepSeek Chat ($0.002/video)", style="cyan")
    console.print("\n💰 总成本: ~$0.02/video (60秒)", style="bold green")

    return team


def run_example(video_path: str):
    """运行示例"""

    team = create_optimized_team()
    if not team:
        return

    console.print(f"\n🎬 处理视频: {video_path}", style="bold")

    try:
        output = team.run(
            video_paths=[video_path],
            config={
                "target_duration": 60,
                "platform": "douyin"
            }
        )

        console.print("\n✅ 处理完成！", style="bold green")
        console.print(f"总耗时: {output.processing_time:.1f}秒")
        console.print(f"质量评分: {output.quality_review.overall_score}/10")

        # 保存结果
        import json
        output_file = "agno_output.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output.model_dump(), f, ensure_ascii=False, indent=2, default=str)

        console.print(f"结果已保存: {output_file}", style="cyan")

    except Exception as e:
        console.print(f"\n❌ 处理失败: {e}", style="bold red")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Agno最佳配置实践")
    parser.add_argument("video", nargs="?", help="视频文件路径")
    parser.add_argument("--test-config", action="store_true", help="仅测试配置")

    args = parser.parse_args()

    if args.test_config:
        # 仅测试配置
        console.print("="*70, style="bold blue")
        console.print("🧪 测试配置", style="bold blue")
        console.print("="*70, style="bold blue")
        team = create_optimized_team()
        if team:
            console.print("\n✅ 配置测试成功！系统就绪。", style="bold green")
    elif args.video:
        # 处理视频
        run_example(args.video)
    else:
        # 显示帮助
        parser.print_help()
        console.print("\n💡 示例用法：", style="yellow")
        console.print("  python agno_best_practice_config.py --test-config")
        console.print("  python agno_best_practice_config.py video.mp4")
