#!/usr/bin/env python3
"""
验证clip_team完整流程 - 使用tmp目录下的真实视频
"""

import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

# 加载环境变量
load_dotenv()

from app.agents import AgnoClipTeam
from rich.console import Console
from rich.table import Table
import structlog

# 初始化Console
console = Console()

# 配置日志
structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
    ],
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger(__name__)


def print_banner():
    """打印欢迎横幅"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║         🎬 Clip Team 完整流程验证                        ║
║                                                              ║
║   使用tmp目录下的真实视频验证完整工作流                  ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""
    console.print(banner, style="bold cyan")


async def main():
    """主函数"""
    print_banner()
    
    # 查找tmp目录下的视频
    tmp_dir = Path("tmp")
    video_files = list(tmp_dir.glob("*.mp4"))
    
    if not video_files:
        console.print("❌ tmp目录下没有找到视频文件", style="bold red")
        return
    
    console.print(f"\n✅ 找到 {len(video_files)} 个视频文件:", style="bold green")
    for video in video_files:
        console.print(f"  • {video.name}", style="green")

    
    # 使用所有视频进行测试（最多2个以节省时间）
    test_videos = [str(v) for v in video_files[:2]]
    console.print(f"\n🎯 使用 {len(test_videos)} 个视频:", style="bold yellow")
    for v in test_videos:
        console.print(f"  • {Path(v).name}", style="yellow")
    
    # 创建输出目录
    output_dir = Path("tmp/output")
    output_dir.mkdir(exist_ok=True)
    output_path = str(output_dir / "clipped_video.mp4")
    
    # 创建Agent团队
    console.print("\n🤖 初始化Agent团队...", style="bold")
    console.print("  • 内容分析: Gemini 2.0 Flash", style="dim")
    console.print("  • 创意策略: Qwen Max", style="dim")
    console.print("  • 技术规划: Qwen Max", style="dim")
    console.print("  • 质量评审: Qwen Max", style="dim")
    console.print("  • 视频执行: 启用", style="dim")
    
    try:
        team = AgnoClipTeam(
            analyzer_model="gemini-2.5-flash",
            strategist_model="qwen-max",
            planner_model="qwen-max",
            reviewer_model="qwen-max",
            analyzer_provider="gemini",
            text_provider="dashscope",
            enable_video_execution=True,
            enable_narration=True,  # 启用口播功能
            temp_dir="tmp"
        )
        console.print("✅ Agent团队初始化完成", style="bold green")
        console.print("  • 口播功能: 已启用", style="green")
        console.print("  • 字幕功能: 已启用", style="green")
    except Exception as e:
        console.print(f"\n❌ Agent初始化失败: {e}", style="bold red")
        return

    # 配置
    config = {
        "target_duration": 30,  # 30秒短视频
        "platform": "douyin",
        "add_narration": True,  # 添加口播旁白
        "narration_tts_provider": "kokoro",  # 使用Kokoro TTS（本地开源）
        "narration_voice": "af_heart",  # Kokoro 音色
        "narration_speed": 1.0,  # Kokoro 语速
        "generate_srt": True,  # 生成SRT字幕文件
        "burn_subtitles": True,  # 烧录字幕到视频
        "subtitle_config": {
            "font_size": 24,
            "font_color": "white",
            "bg_color": "black@0.5",
            "position": ("center", "bottom")
        }
    }
    
    console.print(f"\n🚀 开始执行完整流程（目标时长: 30秒，使用Kokoro TTS + 字幕）...\n", style="bold cyan")

    try:
        # 运行完整流程
        output = await team.run(
            video_paths=test_videos,
            config=config,
            output_path=output_path
        )
        
        # 打印结果摘要
        console.print("\n" + "=" * 70, style="bold cyan")
        console.print("📊 执行结果摘要", style="bold cyan")
        console.print("=" * 70 + "\n", style="bold cyan")
        
        # 分析结果
        table = Table(title="内容分析", show_header=True)
        table.add_column("指标", style="cyan")
        table.add_column("数值", style="magenta")
        
        analysis = output.analyses[0]
        table.add_row("视频ID", analysis.video_id)
        table.add_row("总时长", f"{analysis.duration:.1f}秒")
        table.add_row("关键时刻", f"{len(analysis.key_moments)}个")
        table.add_row("时间轴片段", f"{len(analysis.timeline)}个")
        
        console.print(table)
        
        # 策略结果
        console.print(f"\n🎨 创意策略:", style="bold green")
        console.print(f"  • 风格: {output.strategy.recommended_style}", style="green")
        console.print(f"  • 钩子: {output.strategy.viral_hook}", style="green")
        console.print(f"  • 目标时长: {output.strategy.target_duration}秒", style="green")
        
        # 技术方案
        console.print(f"\n🔧 技术方案:", style="bold magenta")
        console.print(f"  • 片段数: {len(output.technical_plan.segments)}个", style="magenta")
        console.print(f"  • 总时长: {output.technical_plan.total_duration:.1f}秒", style="magenta")
        
        # 质量评审
        pass_status = "✅ 通过" if output.quality_review.pass_review else "❌ 未通过"
        pass_style = "bold green" if output.quality_review.pass_review else "bold red"
        console.print(f"\n⭐ 质量评审:", style="bold yellow")
        console.print(f"  • 总分: {output.quality_review.overall_score:.1f}/10", style="yellow")
        console.print(f"  • 结果: {pass_status}", style=pass_style)
        console.print(f"  • 迭代次数: {output.iteration_count}", style="yellow")
        
        # 视频执行结果
        if output.clipped_video_path:
            console.print(f"\n🎬 视频剪辑:", style="bold blue")
            console.print(f"  • 输出路径: {output.clipped_video_path}", style="blue")
            console.print(f"  • 视频时长: {output.video_duration:.1f}秒", style="blue")
            console.print(f"  • 文件大小: {output.video_file_size_mb:.2f}MB", style="blue")

        # 口播和字幕结果
        if output.script:
            console.print(f"\n📝 口播脚本:", style="bold cyan")
            console.print(f"  • 标题: {output.script.title}", style="cyan")
            console.print(f"  • 脚本长度: {output.script.word_count}字", style="cyan")
            console.print(f"  • 预估时长: {output.script.estimated_speech_duration:.1f}秒", style="cyan")
            console.print(f"  • 预览: {output.script.full_script[:100]}...", style="dim cyan")

        if output.final_video_path:
            console.print(f"\n🎥 完整视频（含口播+字幕）:", style="bold green")
            console.print(f"  • 最终路径: {output.final_video_path}", style="green")
            if output.srt_file_path:
                console.print(f"  • 字幕文件: {output.srt_file_path}", style="green")
        
        # 总结
        console.print("\n" + "=" * 70, style="bold cyan")
        console.print(
            f"🎉 完整流程验证成功！总耗时: {output.processing_time:.1f}秒",
            style="bold cyan"
        )
        console.print("=" * 70 + "\n", style="bold cyan")
        
    except Exception as e:
        console.print(f"\n❌ 执行失败: {e}", style="bold red")
        logger.exception("执行异常")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
