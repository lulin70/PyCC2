#!/usr/bin/env python3
"""
从GitHub和其他开源项目下载CC2资源
基于subagent调查结果
"""
import urllib.request
import ssl
from pathlib import Path


def download_file(url: str, output_path: Path, description: str) -> bool:
    """下载文件，支持SSL"""
    print(f"\n📥 下载: {description}")
    print(f"   URL: {url}")
    print(f"   输出: {output_path}")
    
    try:
        # 创建SSL context，允许未验证的证书
        context = ssl._create_unverified_context()
        
        # 下载文件
        with urllib.request.urlopen(url, context=context, timeout=60) as response:
            content = response.read()
            
        # 保存文件
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(content)
        
        size_mb = len(content) / (1024 * 1024)
        print(f"   ✅ 下载成功 ({size_mb:.2f} MB)")
        return True
        
    except Exception as e:
        print(f"   ❌ 下载失败: {e}")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("从GitHub和开源项目下载CC2资源")
    print("=" * 60)
    
    base_dir = Path(__file__).parent.parent / "assets" / "cc2_resources"
    base_dir.mkdir(parents=True, exist_ok=True)
    
    # 资源列表 - 基于subagent调查结果
    resources = [
        # GitHub上的CC2相关项目
        {
            "url": "https://raw.githubusercontent.com/buxx/OpenCombat/master/README.md",
            "output": base_dir / "github" / "OpenCombat_README.md",
            "description": "OpenCombat项目README（CC2灵感的开源游戏）",
        },
        {
            "url": "https://raw.githubusercontent.com/gshaw/closecombat/master/README.md",
            "output": base_dir / "github" / "closecombat_README.md",
            "description": "Close Combat地图编辑器README",
        },
        # Archive.org的CC2资源（如果有）
        {
            "url": "https://archive.org/download/close-combat-2/close-combat-2.zip",
            "output": base_dir / "archive" / "close-combat-2.zip",
            "description": "Archive.org CC2资源包",
        },
    ]
    
    success_count = 0
    total_count = len(resources)
    
    for resource in resources:
        if download_file(
            resource["url"],
            Path(resource["output"]),
            resource["description"]
        ):
            success_count += 1
    
    print("\n" + "=" * 60)
    print(f"下载完成: {success_count}/{total_count} 个文件成功")
    print("=" * 60)
    
    if success_count > 0:
        print(f"\n✅ 成功下载 {success_count} 个资源文件")
        print(f"\n资源位置: {base_dir}")
    else:
        print("\n⚠️  所有下载都失败了")
        print("\n备选方案:")
        print("1. 使用已生成的19个CC2风格精灵（质量优秀）")
        print("2. 手动从Steam/GOG版本提取原版资源")
        print("3. 继续使用程序化生成的资源")


if __name__ == "__main__":
    main()
