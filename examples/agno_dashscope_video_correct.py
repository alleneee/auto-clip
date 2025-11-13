#!/usr/bin/env python3
"""
Agno + DashScope qwen-vl-plus - 本地视频上传解析（正确方式）

官方文档：https://docs.agno.com/concepts/models/dashscope

Author: Auto-Clip Team
Date: 2025-11-12
"""

import sys
from pathlib import Path
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).parent.parent))

# 加载环境变量
load_dotenv()

console = Console()


def demo_dashscope_video_with_agno():
    """
    ✅ 正确方式：使用agno框架 + DashScope qwen-vl-plus分析本地视频

    核心要点：
    1. agno 原生支持 DashScope
    2. 使用 agno.media.Video 加载本地文件
    3. qwen-vl-plus 模型支持视频理解
    """
    from agno.agent import Agent
    from agno.media import Video
    from agno.models.dashscope import DashScope

    console.print("\n" + "=" * 70, style="bold cyan")
    console.print("✅ 正确方式：Agno + DashScope 本地视频分析", style="bold cyan")
    console.print("=" * 70 + "\n", style="bold cyan")

    # 1. 创建Agent（使用DashScope的qwen-vl-plus视觉模型）
    console.print("🤖 初始化Agno Agent（DashScope qwen-vl-plus）...", style="blue")

    agent = Agent(
        model=DashScope(id="qwen-vl-plus"),  # ✅ DashScope视觉模型
        markdown=True
    )

    console.print("✅ Agent创建成功", style="green")

    # 2. 加载本地视频
    video_path = "/Users/niko/auto-clip/tmp/7514135682735639860.mp4"

    if not Path(video_path).exists():
        console.print(f"❌ 视频不存在: {video_path}", style="bold red")
        console.print("💡 请修改 video_path 为实际路径", style="yellow")
        return

    console.print(f"\n📹 加载视频: {Path(video_path).name}", style="blue")

    # ✅ 关键：使用 agno.media.Video 加载本地文件
    video = Video(filepath=str(Path(video_path).absolute()))

    console.print("✅ 视频加载成功", style="green")

    # 3. 分析视频
    prompt = """
请详细分析这个视频的内容，包括：

1. **主要场景**：描述视频中的环境和背景
2. **人物和动作**：识别人物及其行为
3. **情感氛围**：分析视频传达的情感基调
4. **关键时刻**：标注重要的时间节点
5. **视觉风格**：镜头运用、色彩、构图等

请用结构化的方式输出。
"""

    console.print("\n🔍 开始分析视频...", style="blue")

    try:
        # ✅ 调用Agent分析视频
        response = agent.run(
            prompt,
            videos=[video]  # 传入Video对象
        )

        # 显示结果
        console.print("\n📊 分析结果:", style="bold green")
        content = response.content if hasattr(response, 'content') else str(response)
        console.print(Panel(content, title="DashScope qwen-vl-plus 分析", border_style="green"))

        # 代码示例
        code_example = """
# ✅ 正确的 Agno + DashScope 视频分析代码
from agno.agent import Agent
from agno.media import Video
from agno.models.dashscope import DashScope

# 1. 创建Agent
agent = Agent(
    model=DashScope(id="qwen-vl-plus"),
    markdown=True
)

# 2. 加载本地视频
video = Video(filepath="/path/to/video.mp4")

# 3. 分析视频
response = agent.run(
    "请分析这个视频的内容",
    videos=[video]
)

print(response.content)
"""
        console.print("\n💻 代码示例:", style="bold yellow")
        console.print(Panel(code_example, title="Python代码", border_style="yellow"))

        # 配置要求
        config_info = """
环境变量配置（.env文件）：

DASHSCOPE_API_KEY=sk-xxxxxxxxxxxx

获取API密钥：https://dashscope.aliyun.com/api-keys
"""
        console.print("\n⚙️  配置要求:", style="bold cyan")
        console.print(Panel(config_info, title="环境配置", border_style="cyan"))

    except Exception as e:
        console.print(f"\n❌ 分析失败: {e}", style="bold red")
        import traceback
        console.print(traceback.format_exc(), style="red")


def demo_dashscope_video_async():
    """
    异步方式使用 Agno + DashScope 分析视频
    """
    import asyncio
    from agno.agent import Agent
    from agno.media import Video
    from agno.models.dashscope import DashScope

    console.print("\n" + "=" * 70, style="bold magenta")
    console.print("⚡ 异步方式：Agno + DashScope", style="bold magenta")
    console.print("=" * 70 + "\n", style="bold magenta")

    async def analyze_async():
        # 创建Agent
        agent = Agent(
            model=DashScope(id="qwen-vl-plus"),
            markdown=True
        )

        # 加载视频
        video_path = "/Users/niko/auto-clip/tmp/7514135682735639860.mp4"

        if not Path(video_path).exists():
            console.print(f"❌ 视频不存在: {video_path}", style="bold red")
            return

        video = Video(filepath=str(Path(video_path).absolute()))

        console.print("🔍 异步分析中...", style="blue")

        # ✅ 异步调用
        response = await agent.arun(
            "请简要分析这个视频的主要内容",
            videos=[video]
        )

        console.print("\n📊 异步分析结果:", style="bold green")
        content = response.content if hasattr(response, 'content') else str(response)
        console.print(Panel(content, title="异步结果", border_style="green"))

        # 代码示例
        code_example = """
# ✅ 异步方式
import asyncio
from agno.agent import Agent
from agno.media import Video
from agno.models.dashscope import DashScope

async def main():
    agent = Agent(
        model=DashScope(id="qwen-vl-plus"),
        markdown=True
    )

    video = Video(filepath="/path/to/video.mp4")

    # 使用 arun 进行异步调用
    response = await agent.arun(
        "分析视频",
        videos=[video]
    )

    print(response.content)

asyncio.run(main())
"""
        console.print("\n💻 异步代码示例:", style="bold yellow")
        console.print(Panel(code_example, title="异步Python代码", border_style="yellow"))

    # 运行异步函数
    asyncio.run(analyze_async())


def demo_dashscope_video_streaming():
    """
    流式输出：实时查看分析结果
    """
    from agno.agent import Agent
    from agno.media import Video
    from agno.models.dashscope import DashScope

    console.print("\n" + "=" * 70, style="bold yellow")
    console.print("🌊 流式输出：Agno + DashScope", style="bold yellow")
    console.print("=" * 70 + "\n", style="bold yellow")

    # 创建Agent
    agent = Agent(
        model=DashScope(id="qwen-vl-plus"),
        markdown=True
    )

    # 加载视频
    video_path = "/Users/niko/auto-clip/tmp/7514135682735639860.mp4"

    if not Path(video_path).exists():
        console.print(f"❌ 视频不存在: {video_path}", style="bold red")
        return

    video = Video(filepath=str(Path(video_path).absolute()))

    console.print("🌊 流式分析中（实时显示）...\n", style="blue")

    # ✅ 流式输出
    agent.print_response(
        "请分析这个视频的视觉风格和主要元素",
        videos=[video],
        stream=True  # 启用流式输出
    )

    # 代码示例
    code_example = """
# ✅ 流式输出方式
from agno.agent import Agent
from agno.media import Video
from agno.models.dashscope import DashScope

agent = Agent(
    model=DashScope(id="qwen-vl-plus"),
    markdown=True
)

video = Video(filepath="/path/to/video.mp4")

# 使用 print_response 和 stream=True 实现流式输出
agent.print_response(
    "分析视频",
    videos=[video],
    stream=True  # 实时显示分析结果
)
"""
    console.print("\n\n💻 流式输出代码示例:", style="bold yellow")
    console.print(Panel(code_example, title="流式Python代码", border_style="yellow"))


def main():
    """主函数"""
    console.print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   ✅ Agno + DashScope qwen-vl-plus 本地视频分析       ║
║                                                              ║
║   官方支持 | 原生集成 | 简单高效                            ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""", style="bold cyan")

    console.print("📋 选择演示方式:", style="bold")
    console.print("  1️⃣  同步方式（基础用法）", style="cyan")
    console.print("  2️⃣  异步方式（高性能）", style="magenta")
    console.print("  3️⃣  流式输出（实时显示）", style="yellow")
    console.print("  0️⃣  运行所有示例", style="green")

    try:
        choice = input("\n请输入选择 (0-3): ").strip()

        if choice == "1":
            demo_dashscope_video_with_agno()
        elif choice == "2":
            demo_dashscope_video_async()
        elif choice == "3":
            demo_dashscope_video_streaming()
        elif choice == "0":
            demo_dashscope_video_with_agno()
            demo_dashscope_video_async()
            demo_dashscope_video_streaming()
        else:
            console.print("❌ 无效选择", style="bold red")
            return

        # 总结
        console.print("\n" + "=" * 70, style="bold green")
        console.print("✨ 关键要点总结", style="bold green")
        console.print("=" * 70 + "\n", style="bold green")

        summary = """
1. ✅ agno 原生支持 DashScope（不需要额外适配器）
2. ✅ 使用 agno.models.dashscope.DashScope 类
3. ✅ qwen-vl-plus 模型支持视频理解
4. ✅ 使用 agno.media.Video 加载本地视频文件
5. ✅ 支持同步、异步、流式三种调用方式

与 Gemini 的区别：
- Gemini: 需要先 upload_file() 到 Google 服务器
- DashScope: 直接使用 Video(filepath="...") 即可

推荐使用场景：
- 国内项目：DashScope（网络稳定、响应快）
- 国际项目：Gemini（全球覆盖、性能强）
"""
        console.print(Panel(summary, title="总结", border_style="green"))

    except KeyboardInterrupt:
        console.print("\n\n👋 演示中断", style="yellow")
    except Exception as e:
        console.print(f"\n❌ 演示出错: {e}", style="bold red")
        import traceback
        console.print(traceback.format_exc(), style="red")


if __name__ == "__main__":
    main()
