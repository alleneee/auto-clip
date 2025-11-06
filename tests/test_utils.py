#!/usr/bin/env python3
"""
工具类测试脚本
测试 video_utils 和 audio_utils 的所有功能
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.utils.video_utils import (
    get_video_info,
    extract_video_clip,
    concatenate_video_clips,
    video_to_base64
)
from app.utils.audio_utils import (
    extract_audio_from_video,
    convert_audio_format,
    merge_audio_files,
    trim_audio
)


def print_section(title: str):
    """打印章节标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def test_video_info():
    """测试获取视频信息"""
    print_section("1. 测试获取视频信息 (get_video_info)")

    test_video = "tmp/7514135682735639860.mp4"

    try:
        info = get_video_info(test_video)
        print(f"✅ 视频路径: {test_video}")
        print(f"   时长: {info['duration']:.2f} 秒")
        print(f"   分辨率: {info['width']}x{info['height']}")
        print(f"   帧率: {info['fps']:.2f} fps")
        print(f"   文件大小: {info['size_bytes'] / 1024 / 1024:.2f} MB")
        return True
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        return False


def test_extract_video_clip():
    """测试视频剪辑"""
    print_section("2. 测试视频剪辑 (extract_video_clip)")

    test_video = "tmp/7514135682735639860.mp4"
    output_path = "tmp/test_clip.mp4"

    try:
        # 获取视频时长
        info = get_video_info(test_video)
        duration = info['duration']

        # 剪辑前3秒
        clip_duration = min(3.0, duration)
        result = extract_video_clip(
            video_path=test_video,
            start_time=0.0,
            end_time=clip_duration,
            output_path=output_path
        )

        print(f"✅ 原视频: {test_video}")
        print(f"   剪辑时间: 0.0 - {clip_duration:.1f} 秒")
        print(f"   输出文件: {result}")

        # 验证输出文件
        if os.path.exists(result):
            clip_info = get_video_info(result)
            print(f"   剪辑时长: {clip_info['duration']:.2f} 秒")
            print(f"   文件大小: {clip_info['size_bytes'] / 1024:.2f} KB")

        return True
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        return False


def test_concatenate_videos():
    """测试视频拼接"""
    print_section("3. 测试视频拼接 (concatenate_video_clips)")

    # 使用两个测试视频
    video_paths = [
        "tmp/7514135682735639860.mp4",
        "tmp/7542453439801950251.mp4"
    ]
    output_path = "tmp/test_concatenated.mp4"

    try:
        result = concatenate_video_clips(
            clip_paths=video_paths,
            output_path=output_path
        )

        print(f"✅ 拼接视频数量: {len(video_paths)}")
        for i, path in enumerate(video_paths, 1):
            info = get_video_info(path)
            print(f"   视频{i}: {path} ({info['duration']:.2f}秒)")

        print(f"   输出文件: {result}")

        # 验证输出文件
        if os.path.exists(result):
            concat_info = get_video_info(result)
            print(f"   拼接后时长: {concat_info['duration']:.2f} 秒")
            print(f"   文件大小: {concat_info['size_bytes'] / 1024 / 1024:.2f} MB")

        return True
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_video_to_base64():
    """测试视频转 Base64"""
    print_section("4. 测试视频转 Base64 (video_to_base64)")

    test_video = "tmp/7514135682735639860.mp4"

    try:
        base64_str = video_to_base64(test_video)

        print(f"✅ 视频路径: {test_video}")
        print(f"   Base64 长度: {len(base64_str):,} 字符")
        print(f"   Base64 前50字符: {base64_str[:50]}...")

        # 验证 Base64 格式
        if base64_str and len(base64_str) > 0:
            print(f"   ✅ Base64 编码成功")

        return True
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        return False


def test_extract_audio():
    """测试音频提取"""
    print_section("5. 测试音频提取 (extract_audio_from_video)")

    test_video = "tmp/7514135682735639860.mp4"
    output_path = "tmp/test_audio.mp3"

    try:
        result = extract_audio_from_video(
            video_path=test_video,
            output_path=output_path
        )

        print(f"✅ 视频路径: {test_video}")
        print(f"   输出音频: {result}")

        # 验证输出文件
        if os.path.exists(result):
            file_size = os.path.getsize(result)
            print(f"   文件大小: {file_size / 1024:.2f} KB")

        return True
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        return False


def test_convert_audio_format():
    """测试音频格式转换"""
    print_section("6. 测试音频格式转换 (convert_audio_format)")

    input_audio = "tmp/test_audio.mp3"
    output_path = "tmp/test_audio.wav"

    # 先确保有音频文件
    if not os.path.exists(input_audio):
        print("⏭️  跳过：需要先运行音频提取测试")
        return True

    try:
        result = convert_audio_format(
            input_path=input_audio,
            output_path=output_path,
            target_format="wav"
        )

        print(f"✅ 输入音频: {input_audio}")
        print(f"   输出格式: WAV")
        print(f"   输出文件: {result}")

        # 验证输出文件
        if os.path.exists(result):
            file_size = os.path.getsize(result)
            print(f"   文件大小: {file_size / 1024:.2f} KB")

        return True
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        return False


def test_trim_audio():
    """测试音频裁剪"""
    print_section("7. 测试音频裁剪 (trim_audio)")

    input_audio = "tmp/test_audio.mp3"
    output_path = "tmp/test_audio_trimmed.mp3"

    # 先确保有音频文件
    if not os.path.exists(input_audio):
        print("⏭️  跳过：需要先运行音频提取测试")
        return True

    try:
        result = trim_audio(
            audio_path=input_audio,
            start_time=0.0,
            end_time=3.0,
            output_path=output_path
        )

        print(f"✅ 输入音频: {input_audio}")
        print(f"   裁剪时间: 0.0 - 3.0 秒")
        print(f"   输出文件: {result}")

        # 验证输出文件
        if os.path.exists(result):
            file_size = os.path.getsize(result)
            print(f"   文件大小: {file_size / 1024:.2f} KB")

        return True
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        return False


def cleanup_test_files():
    """清理测试生成的文件"""
    print_section("清理测试文件")

    test_files = [
        "tmp/test_clip.mp4",
        "tmp/test_concatenated.mp4",
        "tmp/test_audio.mp3",
        "tmp/test_audio.wav",
        "tmp/test_audio_trimmed.mp3"
    ]

    for file_path in test_files:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"🗑️  已删除: {file_path}")
            except Exception as e:
                print(f"⚠️  删除失败 {file_path}: {e}")


def main():
    """主测试函数"""
    print("\n" + "🎬" * 30)
    print("  视频/音频工具类测试")
    print("🎬" * 30)

    # 检查测试视频是否存在
    test_videos = [
        "tmp/7514135682735639860.mp4",
        "tmp/7542453439801950251.mp4"
    ]

    print("\n📋 检查测试环境...")
    for video in test_videos:
        if os.path.exists(video):
            print(f"✅ 找到测试视频: {video}")
        else:
            print(f"❌ 缺少测试视频: {video}")
            return

    # 运行所有测试
    results = {}

    # Video Utils 测试
    results['video_info'] = test_video_info()
    results['extract_clip'] = test_extract_video_clip()
    results['concatenate'] = test_concatenate_videos()
    results['video_base64'] = test_video_to_base64()

    # Audio Utils 测试
    results['extract_audio'] = test_extract_audio()
    results['convert_audio'] = test_convert_audio_format()
    results['trim_audio'] = test_trim_audio()

    # 打印测试总结
    print_section("测试总结")

    total = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed

    print(f"\n总计: {total} 个测试")
    print(f"✅ 通过: {passed}")
    print(f"❌ 失败: {failed}")

    if failed == 0:
        print("\n🎉 所有测试通过！")
    else:
        print("\n⚠️  部分测试失败，请检查错误信息")

    # 询问是否清理测试文件
    print("\n" + "=" * 60)
    cleanup = input("是否清理测试生成的文件？(y/n): ").lower().strip()
    if cleanup == 'y':
        cleanup_test_files()
    else:
        print("📁 测试文件已保留在 tmp/ 目录")

    print("\n" + "🎬" * 30)


if __name__ == "__main__":
    main()
