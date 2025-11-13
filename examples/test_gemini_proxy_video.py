#!/usr/bin/env python3
"""
实际测试 Gemini 代理模式的视频分析
"""

import sys
import os
from pathlib import Path

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agents.content_analyzer import ContentAnalyzerAgent

print("=" * 70)
print("🧪 测试 Gemini 代理视频分析")
print("=" * 70)
print()

# 检查环境变量
api_key = os.getenv("GOOGLE_API_KEY")
base_url = os.getenv("GEMINI_BASE_URL")
model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

if not api_key or not base_url:
    print("❌ 错误：请先配置环境变量")
    print()
    print("需要在 .env 文件中配置：")
    print("  GOOGLE_API_KEY=sk-...")
    print("  GEMINI_BASE_URL=https://api.bianxie.ai/v1/chat/completions")
    print("  GEMINI_MODEL=gemini-2.0-flash")
    sys.exit(1)

print(f"✅ API Key: {api_key[:20]}...")
print(f"✅ Base URL: {base_url}")
print(f"✅ Model: {model}")
print()

# 创建 Agent
print("🤖 创建 ContentAnalyzerAgent...")
analyzer = ContentAnalyzerAgent(
    model=model,
    provider="gemini-proxy",
    temperature=0.3
)
print("✅ Agent 创建成功")
print()

# 测试视频路径
video_path = "/Users/niko/auto-clip/tmp/7514135682735639860.mp4"

if not Path(video_path).exists():
    print(f"❌ 视频文件不存在: {video_path}")
    print("💡 请将 video_path 替换为实际的视频路径")
    sys.exit(1)

print(f"📹 视频文件: {Path(video_path).name}")
print(f"📦 文件大小: {Path(video_path).stat().st_size / (1024*1024):.2f} MB")
print()

# 分析视频
print("🔍 开始分析视频...")
print("⏳ 请稍候（通常需要 10-30 秒）...")
print()

try:
    result = analyzer.analyze(video_path, video_id="test_gemini_proxy")

    print("=" * 70)
    print("✅ 分析完成！")
    print("=" * 70)
    print()

    # 显示结果
    print("📊 分析结果摘要:")
    print(f"  视频ID: {result.video_id}")
    print(f"  总时长: {result.duration:.1f}秒")
    print(f"  时间轴片段: {len(result.timeline)}个")
    print(f"  关键时刻: {len(result.key_moments)}个")
    print(f"  语音转录: {'有' if result.transcription else '无'}")
    print()

    # 显示关键时刻
    if result.key_moments:
        print("🎯 关键时刻 Top 5:")
        for i, moment in enumerate(result.key_moments[:5], 1):
            print(f"  {i}. {moment.timestamp:.1f}s")
            print(f"     描述: {moment.description}")
            print(f"     剪辑潜力: {moment.clip_potential:.2f}")
            print(f"     类型: {moment.sync_type}")
            print()

    # 显示时间轴片段摘要
    if result.timeline:
        print("📹 时间轴片段摘要（前3个）:")
        for i, segment in enumerate(result.timeline[:3], 1):
            print(f"  {i}. {segment.start:.1f}s - {segment.end:.1f}s")
            print(f"     视觉: {segment.visual[:60]}...")
            print(f"     音频: {segment.audio[:60]}...")
            print(f"     情绪: {segment.emotion}, 重要性: {segment.importance}/10")
            print()

    print("=" * 70)
    print("🎉 测试成功！Gemini 代理工作正常")
    print("=" * 70)

except Exception as e:
    print()
    print("=" * 70)
    print("❌ 测试失败")
    print("=" * 70)
    print()
    print(f"错误信息: {e}")
    print()
    print("可能的原因：")
    print("  1. API 密钥无效或过期")
    print("  2. 代理服务不可用")
    print("  3. 网络连接问题")
    print("  4. 视频格式不支持")
    print()
    import traceback
    print("详细错误堆栈：")
    traceback.print_exc()
