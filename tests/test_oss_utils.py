#!/usr/bin/env python3
"""
OSS 工具类测试脚本
测试 OSS 客户端的所有核心功能
"""
import os
import sys
import asyncio
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.utils.oss_client import oss_client


def print_section(title: str):
    """打印章节标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


async def test_upload():
    """测试文件上传"""
    print_section("1. 测试文件上传 (upload)")

    test_file = "tmp/7514135682735639860.mp4"
    oss_path = "test/test_video.mp4"

    try:
        if not os.path.exists(test_file):
            print(f"❌ 测试文件不存在: {test_file}")
            return False

        result = await oss_client.upload(
            local_path=test_file,
            oss_path=oss_path
        )

        print(f"✅ 本地文件: {test_file}")
        print(f"   OSS路径: {result['oss_path']}")
        print(f"   文件大小: {result['size'] / 1024 / 1024:.2f} MB")
        print(f"   公网URL: {result['public_url']}")
        if result.get('etag'):
            print(f"   ETag: {result['etag']}")

        return True

    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        return False


async def test_object_exists():
    """测试对象存在性检查"""
    print_section("2. 测试对象存在性检查 (object_exists)")

    oss_path = "test/test_video.mp4"
    non_existent_path = "test/non_existent_file.mp4"

    try:
        exists = oss_client.object_exists(oss_path)
        print(f"✅ 检查路径: {oss_path}")
        print(f"   对象存在: {'是' if exists else '否'}")

        not_exists = oss_client.object_exists(non_existent_path)
        print(f"   检查路径: {non_existent_path}")
        print(f"   对象存在: {'是' if not_exists else '否'}")

        return True

    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        return False


async def test_generate_signed_url():
    """测试生成签名URL"""
    print_section("3. 测试生成签名URL (generate_signed_url)")

    oss_path = "test/test_video.mp4"

    try:
        # 生成1小时有效期的GET URL
        url = oss_client.generate_signed_url(
            oss_path=oss_path,
            expires=3600,
            method='GET'
        )

        print(f"✅ OSS路径: {oss_path}")
        print(f"   有效期: 3600秒 (1小时)")
        print(f"   签名URL长度: {len(url)} 字符")
        print(f"   URL前100字符: {url[:100]}...")

        return True

    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        return False


async def test_download_to_memory():
    """测试下载到内存"""
    print_section("4. 测试下载到内存 (download)")

    oss_path = "test/test_video.mp4"

    try:
        # 检查对象是否存在
        if not oss_client.object_exists(oss_path):
            print(f"⏭️  跳过：对象不存在 {oss_path}")
            print(f"   请先运行上传测试")
            return True

        content = await oss_client.download(oss_path=oss_path)

        print(f"✅ OSS路径: {oss_path}")
        print(f"   下载内容大小: {len(content) / 1024 / 1024:.2f} MB")
        print(f"   数据类型: {type(content).__name__}")

        return True

    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        return False


async def test_download_to_file():
    """测试下载到文件"""
    print_section("5. 测试下载到文件 (download to file)")

    oss_path = "test/test_video.mp4"
    local_path = "tmp/test_download.mp4"

    try:
        # 检查对象是否存在
        if not oss_client.object_exists(oss_path):
            print(f"⏭️  跳过：对象不存在 {oss_path}")
            print(f"   请先运行上传测试")
            return True

        await oss_client.download(
            oss_path=oss_path,
            local_path=local_path
        )

        print(f"✅ OSS路径: {oss_path}")
        print(f"   本地保存: {local_path}")

        # 验证文件
        if os.path.exists(local_path):
            file_size = os.path.getsize(local_path)
            print(f"   文件大小: {file_size / 1024 / 1024:.2f} MB")
        else:
            print(f"   ⚠️ 文件未找到")

        return True

    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        return False


async def test_delete():
    """测试删除对象"""
    print_section("6. 测试删除对象 (delete)")

    oss_path = "test/test_video.mp4"

    try:
        # 检查对象是否存在
        exists_before = oss_client.object_exists(oss_path)
        print(f"   删除前对象存在: {'是' if exists_before else '否'}")

        if not exists_before:
            print(f"⏭️  跳过：对象不存在 {oss_path}")
            return True

        # 删除对象
        success = await oss_client.delete(oss_path)

        # 再次检查
        exists_after = oss_client.object_exists(oss_path)

        print(f"✅ OSS路径: {oss_path}")
        print(f"   删除操作: {'成功' if success else '失败'}")
        print(f"   删除后对象存在: {'是' if exists_after else '否'}")

        return True

    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        return False


def cleanup_test_files():
    """清理测试生成的文件"""
    print_section("清理测试文件")

    test_files = [
        "tmp/test_download.mp4"
    ]

    for file_path in test_files:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"🗑️  已删除: {file_path}")
            except Exception as e:
                print(f"⚠️  删除失败 {file_path}: {e}")


async def main():
    """主测试函数"""
    print("\n" + "☁️" * 30)
    print("  OSS 工具类测试")
    print("☁️" * 30)

    # 检查测试视频是否存在
    test_video = "tmp/7514135682735639860.mp4"

    print("\n📋 检查测试环境...")
    if os.path.exists(test_video):
        print(f"✅ 找到测试视频: {test_video}")
    else:
        print(f"❌ 缺少测试视频: {test_video}")
        return

    # 运行所有测试
    results = {}

    results['upload'] = await test_upload()
    results['object_exists'] = await test_object_exists()
    results['signed_url'] = await test_generate_signed_url()
    results['download_memory'] = await test_download_to_memory()
    results['download_file'] = await test_download_to_file()
    results['delete'] = await test_delete()

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

    # 自动清理测试文件
    cleanup_test_files()

    print("\n" + "☁️" * 30)


if __name__ == "__main__":
    asyncio.run(main())
