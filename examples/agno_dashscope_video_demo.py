#!/usr/bin/env python3
"""
Agno框架集成DashScope VL模型 - 本地视频上传解析演示

三种实现方式：
1. 方案1：直接使用DashScope官方SDK（推荐）
2. 方案2：通过Agno Tool包装DashScope客户端
3. 方案3：使用LiteLLM中间层（开发中）

Author: Auto-Clip Team
Date: 2025-11-12
"""

import sys
import os
import asyncio
import base64
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from dotenv import load_dotenv

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 加载环境变量
load_dotenv()

console = Console()


# ============================================================================
# 方案1：直接使用DashScope官方SDK（推荐，最简单）
# ============================================================================

async def demo_dashscope_sdk():
    """
    方案1：使用DashScope官方SDK上传本地视频

    特点：
    - ✅ 简单直接，项目已集成
    - ✅ 支持base64编码上传本地文件
    - ✅ 官方维护，稳定可靠
    - ❌ 不是通过agno框架调用
    """
    console.print("\n" + "=" * 70, style="bold cyan")
    console.print("方案1：DashScope官方SDK（推荐）", style="bold cyan")
    console.print("=" * 70 + "\n", style="bold cyan")

    from app.utils.ai_clients.dashscope_client import DashScopeClient

    # 检查API密钥
    if not os.getenv("DASHSCOPE_API_KEY"):
        console.print("❌ 未设置DASHSCOPE_API_KEY环境变量", style="bold red")
        return

    # 示例视频路径（替换为你的视频）
    video_path = "/Users/niko/auto-clip/tmp/7514135682735639860.mp4"

    if not Path(video_path).exists():
        console.print(f"❌ 视频文件不存在: {video_path}", style="bold red")
        console.print("💡 提示：请将 video_path 替换为实际的视频路径", style="yellow")
        return

    try:
        # 初始化客户端
        client = DashScopeClient()
        console.print(f"✅ DashScope客户端初始化成功", style="green")

        # 读取并编码视频
        console.print(f"📹 读取视频文件: {Path(video_path).name}", style="blue")
        with open(video_path, "rb") as f:
            video_base64 = base64.b64encode(f.read()).decode("utf-8")

        file_size_mb = len(video_base64) / (1024 * 1024) * 0.75  # base64约75%的原始大小
        console.print(f"📦 视频大小: {file_size_mb:.2f} MB", style="blue")

        # 分析视频
        prompt = "请详细分析这个视频的内容，包括：\n1. 主要场景和环境\n2. 人物和动作\n3. 情感氛围\n4. 关键时刻（标注时间戳）"

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("🔍 DashScope VL模型分析中...", total=None)

            result = await client.analyze_video_visual_base64(
                video_base64=video_base64,
                prompt=prompt
            )

            progress.update(task, completed=True)

        # 显示结果
        console.print("\n📊 分析结果:", style="bold green")
        console.print(Panel(result, title="qwen-vl-plus 分析结果", border_style="green"))

        # 代码示例
        code_example = """
# 方案1使用示例
from app.utils.ai_clients.dashscope_client import DashScopeClient
import base64

client = DashScopeClient()

# 读取视频
with open("video.mp4", "rb") as f:
    video_base64 = base64.b64encode(f.read()).decode("utf-8")

# 分析视频
result = await client.analyze_video_visual_base64(
    video_base64=video_base64,
    prompt="请分析视频内容"
)
"""
        console.print("\n💻 代码示例:", style="bold yellow")
        console.print(Panel(code_example, title="Python代码", border_style="yellow"))

    except Exception as e:
        console.print(f"\n❌ 分析失败: {e}", style="bold red")
        import traceback
        console.print(traceback.format_exc(), style="red")


# ============================================================================
# 方案2：通过Agno Tool包装DashScope（支持Agent调用）
# ============================================================================

async def demo_agno_tool():
    """
    方案2：创建Agno Tool包装DashScope客户端

    特点：
    - ✅ 符合agno框架规范
    - ✅ 可集成到任何Agno Agent
    - ✅ 支持Tool调用
    - ⚠️ 需要封装代码
    """
    console.print("\n" + "=" * 70, style="bold magenta")
    console.print("方案2：Agno Tool包装DashScope", style="bold magenta")
    console.print("=" * 70 + "\n", style="bold magenta")

    from agno.agent import Agent
    from agno.models.google import Gemini
    from agno.tools import tool
    import structlog

    logger = structlog.get_logger(__name__)

    # 定义Agno Tool
    @tool
    def analyze_video_dashscope(
        video_path: str,
        prompt: str = "请详细分析这个视频的内容"
    ) -> str:
        """
        使用DashScope qwen-vl-plus模型分析本地视频

        Args:
            video_path: 本地视频文件路径
            prompt: 分析提示词

        Returns:
            视频分析结果
        """
        from app.utils.ai_clients.dashscope_client import DashScopeClient

        try:
            path = Path(video_path)
            if not path.exists():
                return f"错误：视频文件不存在 - {video_path}"

            # 读取视频
            with open(path, "rb") as f:
                video_base64 = base64.b64encode(f.read()).decode("utf-8")

            # 调用DashScope
            client = DashScopeClient()
            result = asyncio.run(
                client.analyze_video_visual_base64(
                    video_base64=video_base64,
                    prompt=prompt
                )
            )

            return result

        except Exception as e:
            return f"视频分析失败: {str(e)}"

    # 创建Agent
    console.print("🤖 创建Agno Agent（集成DashScope Tool）...", style="blue")

    if not os.getenv("GEMINI_API_KEY"):
        console.print("❌ 未设置GEMINI_API_KEY环境变量（Agent需要）", style="bold red")
        console.print("💡 提示：设置GEMINI_API_KEY以使用Gemini作为Agent的大脑", style="yellow")
        return

    agent = Agent(
        name="VideoAnalyzer",
        model=Gemini(id="gemini-2.0-flash-exp"),
        tools=[analyze_video_dashscope],
        instructions=[
            "你是专业的视频分析专家",
            "当用户提供视频路径时，使用analyze_video_dashscope工具分析",
            "分析结果要详细、结构化"
        ],
        markdown=False
    )

    console.print("✅ Agent创建成功", style="green")

    # 示例视频路径
    video_path = "/Users/niko/auto-clip/tmp/7514135682735639860.mp4"

    if not Path(video_path).exists():
        console.print(f"❌ 视频文件不存在: {video_path}", style="bold red")
        return

    # 运行Agent
    console.print(f"\n🎬 开始分析视频: {Path(video_path).name}", style="blue")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("🤖 Agent工作中（调用DashScope Tool）...", total=None)

        response = agent.run(f"请分析这个视频的内容：{video_path}")

        progress.update(task, completed=True)

    # 显示结果
    console.print("\n📊 Agent分析结果:", style="bold green")
    console.print(Panel(
        response.content if hasattr(response, 'content') else str(response),
        title="Agno Agent + DashScope Tool",
        border_style="green"
    ))

    # 代码示例
    code_example = """
# 方案2使用示例
from agno.agent import Agent
from agno.models.google import Gemini
from agno.tools import tool
from app.utils.ai_clients.dashscope_client import DashScopeClient

@tool
def analyze_video_dashscope(video_path: str, prompt: str) -> str:
    \"\"\"使用DashScope分析视频\"\"\"
    client = DashScopeClient()
    # ... base64编码 + API调用
    return result

agent = Agent(
    name="VideoAnalyzer",
    model=Gemini(id="gemini-2.0-flash-exp"),
    tools=[analyze_video_dashscope],
    instructions=["你是视频分析专家"]
)

response = agent.run("分析这个视频：/path/to/video.mp4")
"""
    console.print("\n💻 代码示例:", style="bold yellow")
    console.print(Panel(code_example, title="Python代码", border_style="yellow"))


# ============================================================================
# 方案3：使用LiteLLM中间层（开发中）
# ============================================================================

async def demo_litellm():
    """
    方案3：使用LiteLLM作为中间层调用DashScope

    特点：
    - ✅ 统一多模型接口
    - ✅ 支持模型切换
    - ⚠️ LiteLLM对DashScope视频支持有限
    - ⚠️ 需要额外配置
    """
    console.print("\n" + "=" * 70, style="bold yellow")
    console.print("方案3：LiteLLM中间层（实验性）", style="bold yellow")
    console.print("=" * 70 + "\n", style="bold yellow")

    console.print("⚠️  LiteLLM对DashScope VL模型的视频支持尚不完善", style="yellow")
    console.print("💡 推荐使用方案1或方案2", style="yellow")

    # 代码示例
    code_example = """
# 方案3使用示例（LiteLLM）
from app.tools.litellm_multimodal_tool import LiteLLMMultimodalTool

# 注意：需要LiteLLM支持dashscope视频输入
tool = LiteLLMMultimodalTool(
    model="dashscope/qwen-vl-plus",
    api_key=os.getenv("DASHSCOPE_API_KEY")
)

result = await tool.analyze_video(
    video_path="/path/to/video.mp4",
    prompt="请分析视频内容"
)
"""
    console.print("\n💻 代码示例:", style="bold cyan")
    console.print(Panel(code_example, title="Python代码（实验性）", border_style="cyan"))


# ============================================================================
# 主函数
# ============================================================================

async def main():
    """主函数"""
    console.print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   🎬 Agno + DashScope VL模型 - 本地视频上传解析演示    ║
║                                                              ║
║   三种实现方案对比演示                                      ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""", style="bold cyan")

    # 检查环境变量
    console.print("🔍 检查环境变量...", style="blue")
    env_table = Table(show_header=True)
    env_table.add_column("环境变量", style="cyan")
    env_table.add_column("状态", style="magenta")
    env_table.add_column("用途", style="green")

    dashscope_key = os.getenv("DASHSCOPE_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")

    env_table.add_row(
        "DASHSCOPE_API_KEY",
        "✅ 已设置" if dashscope_key else "❌ 未设置",
        "DashScope VL模型分析"
    )
    env_table.add_row(
        "GEMINI_API_KEY",
        "✅ 已设置" if gemini_key else "❌ 未设置",
        "Agno Agent大脑（方案2）"
    )

    console.print(env_table)

    if not dashscope_key:
        console.print("\n⚠️  警告：未设置DASHSCOPE_API_KEY", style="bold yellow")
        console.print("💡 请在.env文件中配置：DASHSCOPE_API_KEY=sk-xxx", style="yellow")
        return

    # 方案选择
    console.print("\n📋 选择演示方案:", style="bold")
    console.print("  1️⃣  方案1：DashScope官方SDK（推荐）", style="cyan")
    console.print("  2️⃣  方案2：Agno Tool包装DashScope", style="magenta")
    console.print("  3️⃣  方案3：LiteLLM中间层（实验性）", style="yellow")
    console.print("  0️⃣  运行所有方案", style="green")

    try:
        choice = input("\n请输入选择 (0-3): ").strip()

        if choice == "1":
            await demo_dashscope_sdk()
        elif choice == "2":
            await demo_agno_tool()
        elif choice == "3":
            await demo_litellm()
        elif choice == "0":
            await demo_dashscope_sdk()
            await demo_agno_tool()
            await demo_litellm()
        else:
            console.print("❌ 无效选择", style="bold red")
            return

        # 总结
        console.print("\n" + "=" * 70, style="bold green")
        console.print("✨ 方案对比总结", style="bold green")
        console.print("=" * 70 + "\n", style="bold green")

        comparison_table = Table(show_header=True, title="三种方案对比")
        comparison_table.add_column("方案", style="cyan", width=20)
        comparison_table.add_column("难度", style="magenta", width=8)
        comparison_table.add_column("Agno集成", style="green", width=10)
        comparison_table.add_column("推荐度", style="yellow", width=8)
        comparison_table.add_column("备注", style="white", no_wrap=False)

        comparison_table.add_row(
            "方案1: DashScope SDK",
            "简单",
            "❌ 否",
            "⭐⭐⭐⭐⭐",
            "最简单，直接使用官方SDK"
        )
        comparison_table.add_row(
            "方案2: Agno Tool",
            "中等",
            "✅ 是",
            "⭐⭐⭐⭐",
            "符合Agno框架，可集成Agent"
        )
        comparison_table.add_row(
            "方案3: LiteLLM",
            "复杂",
            "✅ 是",
            "⭐⭐",
            "实验性，支持有限"
        )

        console.print(comparison_table)

        console.print("\n💡 推荐使用顺序:", style="bold cyan")
        console.print("  1. 如果只需要视频分析 → 方案1（最简单）", style="green")
        console.print("  2. 如果需要Agent系统 → 方案2（Agno框架）", style="green")
        console.print("  3. 如果需要多模型切换 → 方案3（开发中）", style="yellow")

    except KeyboardInterrupt:
        console.print("\n\n👋 演示中断", style="yellow")
    except Exception as e:
        console.print(f"\n❌ 演示出错: {e}", style="bold red")
        import traceback
        console.print(traceback.format_exc(), style="red")


if __name__ == "__main__":
    asyncio.run(main())
