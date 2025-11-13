#!/usr/bin/env python3
"""
Gemini视频分析使用示例

展示三种常见的使用场景：
1. 基础视频分析
2. 批量视频处理
3. 与现有系统集成
"""

import asyncio
import sys
from pathlib import Path
from typing import List

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.adapters.gemini_vision_adapter import GeminiVisionAdapter
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


async def example_1_basic_analysis():
    """示例1: 基础视频分析"""
    console.print("\n" + "="*70, style="bold cyan")
    console.print("📝 示例1: 基础视频分析", style="bold cyan")
    console.print("="*70, style="cyan")

    # 初始化适配器（自动读取环境变量配置）
    adapter = GeminiVisionAdapter()

    # 分析单个视频
    video_path = "/path/to/your/video.mp4"  # 替换为实际路径

    console.print(f"📹 视频: {video_path}", style="dim")
    console.print("🔄 分析中...\n", style="yellow")

    try:
        result = await adapter.analyze_from_path(
            video_path=video_path,
            prompt="""
            请分析这个视频，提供以下信息：
            1. 主要场景和背景
            2. 出现的人物或物体
            3. 关键动作和事件
            4. 整体氛围和情感基调
            """
        )

        console.print("✅ 分析完成！", style="bold green")
        console.print("\n分析结果:", style="bold")
        console.print(result, style="green")

    except FileNotFoundError:
        console.print(f"❌ 视频文件不存在: {video_path}", style="red")
        console.print("💡 请修改video_path为实际文件路径", style="yellow")
    except Exception as e:
        console.print(f"❌ 分析失败: {e}", style="red")


async def example_2_batch_processing():
    """示例2: 批量视频处理"""
    console.print("\n" + "="*70, style="bold cyan")
    console.print("📝 示例2: 批量视频处理", style="bold cyan")
    console.print("="*70, style="cyan")

    # 待处理的视频列表
    video_paths = [
        "/path/to/video1.mp4",
        "/path/to/video2.mp4",
        "/path/to/video3.mp4",
    ]

    adapter = GeminiVisionAdapter()

    console.print(f"📋 待处理: {len(video_paths)}个视频\n", style="dim")

    # 使用Progress显示进度
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:

        results = []

        for i, video_path in enumerate(video_paths, 1):
            task = progress.add_task(f"处理 {i}/{len(video_paths)}: {Path(video_path).name}", total=None)

            try:
                result = await adapter.analyze_from_path(
                    video_path=video_path,
                    prompt="请用一句话概括这个视频的主要内容"
                )
                results.append({"video": video_path, "result": result, "status": "success"})

            except Exception as e:
                results.append({"video": video_path, "error": str(e), "status": "failed"})

            progress.remove_task(task)

    # 输出结果
    console.print("\n📊 处理结果:", style="bold")
    for i, item in enumerate(results, 1):
        if item["status"] == "success":
            console.print(f"\n{i}. ✅ {Path(item['video']).name}", style="green")
            console.print(f"   {item['result'][:100]}...", style="dim green")
        else:
            console.print(f"\n{i}. ❌ {Path(item['video']).name}", style="red")
            console.print(f"   错误: {item['error']}", style="dim red")


async def example_3_integration_with_service():
    """示例3: 与现有服务集成"""
    console.print("\n" + "="*70, style="bold cyan")
    console.print("📝 示例3: 与现有服务集成", style="bold cyan")
    console.print("="*70, style="cyan")

    # 模拟一个视频处理服务
    class VideoProcessingService:
        def __init__(self, use_gemini: bool = True):
            """
            初始化服务

            Args:
                use_gemini: 是否使用Gemini（False则使用DashScope）
            """
            if use_gemini:
                from app.adapters.gemini_vision_adapter import GeminiVisionAdapter
                self.vision_adapter = GeminiVisionAdapter()
                console.print("✅ 使用Gemini视觉分析服务", style="green")
            else:
                from app.adapters.vision_adapters import DashScopeVisionAdapter
                self.vision_adapter = DashScopeVisionAdapter()
                console.print("✅ 使用DashScope视觉分析服务", style="green")

        async def analyze_and_extract_clips(
            self,
            video_path: str,
            target_themes: List[str]
        ) -> dict:
            """
            分析视频并提取符合主题的片段

            Args:
                video_path: 视频路径
                target_themes: 目标主题列表

            Returns:
                包含分析结果和推荐片段的字典
            """
            console.print(f"\n🔍 分析视频: {Path(video_path).name}", style="cyan")
            console.print(f"🎯 目标主题: {', '.join(target_themes)}", style="dim")

            # 第一步：视频内容分析
            analysis_prompt = f"""
            请分析视频内容，并判断是否包含以下主题：
            {', '.join(target_themes)}

            输出格式：
            1. 视频整体描述（50字内）
            2. 包含的主题（从目标主题列表中选择）
            3. 推荐的精彩片段时间点（格式：MM:SS）
            """

            try:
                analysis_result = await self.vision_adapter.analyze_from_path(
                    video_path=video_path,
                    prompt=analysis_prompt
                )

                console.print("\n📝 分析结果:", style="bold")
                console.print(analysis_result, style="green")

                # 第二步：基于分析结果生成剪辑计划
                # （这里简化处理，实际应用中会调用LLM生成详细计划）

                return {
                    "video": video_path,
                    "analysis": analysis_result,
                    "status": "success",
                    "recommended_clips": [
                        {"start": "00:05", "end": "00:15", "reason": "主题相关片段"},
                        {"start": "01:20", "end": "01:35", "reason": "精彩画面"},
                    ]
                }

            except Exception as e:
                console.print(f"\n❌ 处理失败: {e}", style="red")
                return {
                    "video": video_path,
                    "status": "failed",
                    "error": str(e)
                }

    # 使用服务
    service = VideoProcessingService(use_gemini=True)

    video_path = "/path/to/your/video.mp4"  # 替换为实际路径
    target_themes = ["科技", "创新", "未来"]

    try:
        result = await service.analyze_and_extract_clips(
            video_path=video_path,
            target_themes=target_themes
        )

        if result["status"] == "success":
            console.print("\n✅ 处理成功！", style="bold green")
            console.print("\n推荐片段:", style="bold")
            for i, clip in enumerate(result["recommended_clips"], 1):
                console.print(
                    f"  {i}. {clip['start']} - {clip['end']} ({clip['reason']})",
                    style="cyan"
                )

    except FileNotFoundError:
        console.print(f"\n❌ 视频文件不存在: {video_path}", style="red")
        console.print("💡 请修改video_path为实际文件路径", style="yellow")


async def example_4_custom_base_url():
    """示例4: 使用自定义Base URL（代理场景）"""
    console.print("\n" + "="*70, style="bold cyan")
    console.print("📝 示例4: 使用自定义Base URL", style="bold cyan")
    console.print("="*70, style="cyan")

    # 场景：企业内网通过代理访问Gemini
    custom_base_url = "https://your-proxy-server.com/gemini/v1beta"

    console.print(f"🌐 代理地址: {custom_base_url}", style="cyan")
    console.print("📝 适用场景: 企业内网、地区限制、流量监控\n", style="dim")

    try:
        # 使用自定义base_url初始化适配器
        adapter = GeminiVisionAdapter(base_url=custom_base_url)

        console.print("✅ 适配器初始化成功（使用自定义Base URL）", style="green")

        # 后续使用方式与标准配置完全相同
        video_path = "/path/to/your/video.mp4"

        result = await adapter.analyze_from_path(
            video_path=video_path,
            prompt="简要描述视频内容"
        )

        console.print("\n分析结果:", style="bold")
        console.print(result, style="green")

    except FileNotFoundError:
        console.print(f"❌ 视频文件不存在: {video_path}", style="red")
    except Exception as e:
        console.print(f"❌ 分析失败: {e}", style="red")
        console.print("\n💡 可能的原因:", style="yellow")
        console.print("  • 代理服务器未启动或配置错误", style="dim")
        console.print("  • 网络连接问题", style="dim")
        console.print("  • API密钥无效", style="dim")


async def main():
    """主函数 - 运行所有示例"""
    console.print("="*70, style="bold magenta")
    console.print("🚀 Gemini视频分析使用示例", style="bold magenta")
    console.print("="*70, style="magenta")

    console.print("\n💡 提示:", style="bold yellow")
    console.print("  1. 确保已配置 GEMINI_API_KEY 环境变量", style="dim")
    console.print("  2. 修改示例中的视频路径为实际文件", style="dim")
    console.print("  3. （可选）配置 GEMINI_BASE_URL 使用代理\n", style="dim")

    # 运行示例
    examples = [
        ("基础视频分析", example_1_basic_analysis),
        ("批量视频处理", example_2_batch_processing),
        ("与现有服务集成", example_3_integration_with_service),
        ("使用自定义Base URL", example_4_custom_base_url),
    ]

    for name, example_func in examples:
        console.print(f"\n▶️  运行示例: {name}", style="bold blue")
        try:
            await example_func()
        except KeyboardInterrupt:
            console.print(f"\n⚠️  示例被中断: {name}", style="yellow")
            break
        except Exception as e:
            console.print(f"\n❌ 示例失败: {name}", style="red")
            console.print(f"   错误: {e}", style="dim red")

    console.print("\n" + "="*70, style="bold magenta")
    console.print("✅ 示例演示完成", style="bold magenta")
    console.print("="*70, style="magenta")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n\n⚠️  程序被用户中断", style="yellow")
    except Exception as e:
        console.print(f"\n\n❌ 程序异常: {e}", style="bold red")
