"""
高级视频混剪示例代码
演示如何使用优化后的多视频混剪功能

使用场景：
1. 基础多视频拼接（带转场）
2. 并行处理加速
3. 智能片段排序
4. 画中画和分屏布局
5. 视频滤镜效果
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.advanced_video_mixing import (
    advanced_video_mixing_service,
    TransitionType,
    FilterType,
    LayoutType
)
from app.services.smart_clip_strategy import smart_clip_strategy
from app.models.batch_processing import ClipSegment


async def demo_basic_mixing():
    """示例1: 基础多视频混剪（带转场效果）"""
    print("\n=== 示例1: 基础多视频混剪 ===\n")

    # 模拟两个视频的片段
    video_paths = [
        "storage/videos/video1.mp4",
        "storage/videos/video2.mp4"
    ]

    segments = [
        ClipSegment(
            video_index=0,
            start_time=0.0,
            end_time=5.0,
            priority=4,
            reason="精彩开场"
        ),
        ClipSegment(
            video_index=1,
            start_time=10.0,
            end_time=15.0,
            priority=5,
            reason="高潮时刻"
        ),
        ClipSegment(
            video_index=0,
            start_time=20.0,
            end_time=25.0,
            priority=3,
            reason="完美收尾"
        ),
    ]

    try:
        # 使用滑动转场效果
        output_path, stats = await advanced_video_mixing_service.mix_videos_advanced(
            video_paths=video_paths,
            segments=segments,
            output_path="storage/outputs/basic_mixing.mp4",
            transition_type="slide",
            transition_duration=0.8,
            output_quality="high",
            enable_parallel=True
        )

        print(f"✅ 混剪完成: {output_path}")
        print(f"📊 统计信息:")
        for key, value in stats.items():
            print(f"   {key}: {value}")

    except Exception as e:
        print(f"❌ 混剪失败: {str(e)}")


async def demo_smart_sorting():
    """示例2: 智能片段排序"""
    print("\n=== 示例2: 智能片段排序 ===\n")

    # 创建多个片段
    segments = [
        ClipSegment(
            video_index=0,
            start_time=0.0,
            end_time=3.0,
            priority=2,
            reason="普通场景"
        ),
        ClipSegment(
            video_index=0,
            start_time=10.0,
            end_time=15.0,
            priority=5,
            reason="精彩高潮时刻"
        ),
        ClipSegment(
            video_index=1,
            start_time=5.0,
            end_time=8.0,
            priority=3,
            reason="不错的转场"
        ),
        ClipSegment(
            video_index=1,
            start_time=20.0,
            end_time=25.0,
            priority=4,
            reason="震撼的亮点"
        ),
    ]

    # 使用渐强式叙事（从低到高）
    sorted_segments, stats = smart_clip_strategy.create_optimal_clip_plan(
        segments=segments,
        narrative_style="crescendo",
        target_duration=60.0,
        remove_duplicates=True
    )

    print("📝 原始顺序:")
    for i, seg in enumerate(segments):
        print(f"   {i+1}. 优先级{seg.priority}: {seg.reason}")

    print("\n🎯 优化后顺序:")
    for i, seg in enumerate(sorted_segments):
        print(f"   {i+1}. 优先级{seg.priority}: {seg.reason}")

    print(f"\n📊 优化统计:")
    for key, value in stats.items():
        print(f"   {key}: {value}")


async def demo_pip_layout():
    """示例3: 画中画布局"""
    print("\n=== 示例3: 画中画布局 ===\n")

    # 准备两个视频片段路径（实际使用时需要真实文件）
    clip_paths = [
        "storage/temp/clip_1_0.0_2.5.mp4",
        "storage/temp/clip_2_2.5_5.0.mp4"
    ]

    try:
        output_path = await advanced_video_mixing_service.create_layout_video(
            clip_paths=clip_paths,
            layout_type="pip",
            output_path="storage/outputs/pip_demo.mp4",
            target_size=(1920, 1080)
        )

        print(f"✅ 画中画视频创建成功: {output_path}")

    except Exception as e:
        print(f"❌ 创建失败: {str(e)}")


async def demo_split_screen():
    """示例4: 分屏布局"""
    print("\n=== 示例4: 分屏布局 ===\n")

    clip_paths = [
        "storage/temp/clip_1_0.0_2.5.mp4",
        "storage/temp/clip_2_2.5_5.0.mp4"
    ]

    try:
        # 水平分屏
        output_path = await advanced_video_mixing_service.create_layout_video(
            clip_paths=clip_paths,
            layout_type="split_h",
            output_path="storage/outputs/split_h_demo.mp4",
            target_size=(1920, 1080)
        )

        print(f"✅ 水平分屏视频创建成功: {output_path}")

    except Exception as e:
        print(f"❌ 创建失败: {str(e)}")


async def demo_with_filters():
    """示例5: 应用视频滤镜"""
    print("\n=== 示例5: 应用视频滤镜 ===\n")

    video_paths = ["storage/videos/video1.mp4"]

    segments = [
        ClipSegment(
            video_index=0,
            start_time=0.0,
            end_time=10.0,
            priority=4,
            reason="应用滤镜的片段"
        ),
    ]

    # 定义滤镜配置
    filters = {
        "brightness": 0.7,    # 提高亮度
        "contrast": 0.6,      # 增强对比度
    }

    try:
        output_path, stats = await advanced_video_mixing_service.mix_videos_advanced(
            video_paths=video_paths,
            segments=segments,
            output_path="storage/outputs/filtered_video.mp4",
            apply_filters=filters,
            output_quality="high"
        )

        print(f"✅ 滤镜视频创建成功: {output_path}")
        print(f"📊 应用的滤镜: {stats['filters_applied']}")

    except Exception as e:
        print(f"❌ 创建失败: {str(e)}")


async def demo_parallel_extraction():
    """示例6: 并行提取片段（性能优化）"""
    print("\n=== 示例6: 并行提取片段 ===\n")

    video_paths = [
        "storage/videos/video1.mp4",
        "storage/videos/video2.mp4"
    ]

    # 创建多个片段（模拟大量剪辑任务）
    segments = []
    for i in range(10):
        segments.append(
            ClipSegment(
                video_index=i % 2,
                start_time=i * 5.0,
                end_time=(i + 1) * 5.0,
                priority=3,
                reason=f"片段 {i+1}"
            )
        )

    try:
        import time
        start_time = time.time()

        # 并行提取
        clip_paths = await advanced_video_mixing_service.extract_clips_parallel(
            video_paths=video_paths,
            segments=segments
        )

        elapsed_time = time.time() - start_time

        print(f"✅ 并行提取完成:")
        print(f"   提取片段数: {len(clip_paths)}")
        print(f"   总耗时: {elapsed_time:.2f}秒")
        print(f"   平均速度: {len(clip_paths)/elapsed_time:.2f} 片段/秒")

    except Exception as e:
        print(f"❌ 提取失败: {str(e)}")


async def demo_comprehensive_workflow():
    """示例7: 综合工作流（智能排序 + 高级混剪）"""
    print("\n=== 示例7: 综合工作流 ===\n")

    video_paths = [
        "storage/videos/video1.mp4",
        "storage/videos/video2.mp4"
    ]

    # 原始片段
    raw_segments = [
        ClipSegment(0, 0.0, 5.0, 2, "开场介绍"),
        ClipSegment(0, 10.0, 15.0, 5, "精彩高潮"),
        ClipSegment(1, 5.0, 10.0, 3, "转场过渡"),
        ClipSegment(1, 20.0, 25.0, 4, "震撼亮点"),
        ClipSegment(0, 30.0, 35.0, 1, "填充内容"),
    ]

    try:
        # 步骤1: 智能优化片段方案
        optimized_segments, strategy_stats = smart_clip_strategy.create_optimal_clip_plan(
            segments=raw_segments,
            narrative_style="wave",  # 波浪式叙事
            target_duration=60.0,
            remove_duplicates=True
        )

        print("📝 智能优化完成:")
        print(f"   原始片段数: {len(raw_segments)}")
        print(f"   优化后片段数: {len(optimized_segments)}")
        print(f"   平均质量评分: {strategy_stats['average_quality']:.2f}")

        # 步骤2: 高级混剪
        output_path, mixing_stats = await advanced_video_mixing_service.mix_videos_advanced(
            video_paths=video_paths,
            segments=optimized_segments,
            output_path="storage/outputs/comprehensive_output.mp4",
            transition_type="crossfade",
            transition_duration=1.0,
            apply_filters={"brightness": 0.6},
            output_quality="ultra",
            enable_parallel=True
        )

        print(f"\n✅ 综合混剪完成: {output_path}")
        print(f"\n📊 最终统计:")
        print(f"   总时长: {mixing_stats['total_duration']:.2f}秒")
        print(f"   文件大小: {mixing_stats['output_size_mb']:.2f}MB")
        print(f"   处理耗时: {mixing_stats['processing_time']:.2f}秒")
        print(f"   转场效果: {mixing_stats['transition_type']}")

    except Exception as e:
        print(f"❌ 工作流失败: {str(e)}")


def print_menu():
    """打印菜单"""
    print("\n" + "="*60)
    print("🎬 高级视频混剪功能演示")
    print("="*60)
    print("\n请选择演示示例:")
    print("  1. 基础多视频混剪（带转场）")
    print("  2. 智能片段排序")
    print("  3. 画中画布局")
    print("  4. 分屏布局")
    print("  5. 视频滤镜效果")
    print("  6. 并行提取优化")
    print("  7. 综合工作流")
    print("  8. 运行所有示例")
    print("  0. 退出")
    print("="*60)


async def main():
    """主函数"""
    demos = {
        1: ("基础多视频混剪", demo_basic_mixing),
        2: ("智能片段排序", demo_smart_sorting),
        3: ("画中画布局", demo_pip_layout),
        4: ("分屏布局", demo_split_screen),
        5: ("视频滤镜效果", demo_with_filters),
        6: ("并行提取优化", demo_parallel_extraction),
        7: ("综合工作流", demo_comprehensive_workflow),
    }

    while True:
        print_menu()

        try:
            choice = input("\n请输入选项 (0-8): ").strip()

            if choice == "0":
                print("\n👋 再见!")
                break

            elif choice == "8":
                print("\n🚀 运行所有示例...\n")
                for name, demo_func in demos.values():
                    print(f"\n{'='*60}")
                    print(f"▶️  {name}")
                    print(f"{'='*60}")
                    try:
                        await demo_func()
                    except Exception as e:
                        print(f"❌ 示例失败: {str(e)}")
                    print("\n" + "="*60)

            elif choice.isdigit() and int(choice) in demos:
                demo_num = int(choice)
                name, demo_func = demos[demo_num]
                print(f"\n▶️  运行示例: {name}")
                await demo_func()

            else:
                print("❌ 无效选项，请重新输入")

        except KeyboardInterrupt:
            print("\n\n👋 程序已中断，再见!")
            break
        except Exception as e:
            print(f"\n❌ 发生错误: {str(e)}")


if __name__ == "__main__":
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║                                                            ║
    ║     🎬 Auto-Clip 高级视频混剪功能演示                     ║
    ║                                                            ║
    ║     新功能特性:                                            ║
    ║     ✨ 多种转场效果（淡入淡出、滑动、缩放等）              ║
    ║     ⚡ 并行处理优化（4x性能提升）                          ║
    ║     🧠 智能片段排序（4种叙事风格）                         ║
    ║     🎨 视频滤镜和特效                                      ║
    ║     📐 多种布局（画中画、分屏、网格）                      ║
    ║                                                            ║
    ╚════════════════════════════════════════════════════════════╝
    """)

    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\n❌ 程序异常: {str(e)}")
