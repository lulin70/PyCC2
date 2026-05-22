#!/usr/bin/env python3
"""
下载CC2资源文件
使用多种方法确保下载成功
"""

import os
import sys
from pathlib import Path
import subprocess
import hashlib


def download_with_wget(url: str, output_path: Path) -> bool:
    """使用wget下载（支持断点续传）"""
    try:
        cmd = [
            'wget',
            '--continue',  # 断点续传
            '--timeout=30',
            '--tries=5',
            '--output-document', str(output_path),
            url
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        print("wget未安装")
        return False


def download_with_curl(url: str, output_path: Path) -> bool:
    """使用curl下载（支持断点续传）"""
    try:
        cmd = [
            'curl',
            '-L',  # 跟随重定向
            '-C', '-',  # 断点续传
            '--retry', '5',
            '--retry-delay', '2',
            '--max-time', '300',
            '-o', str(output_path),
            url
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        print("curl未安装")
        return False


def download_with_python(url: str, output_path: Path) -> bool:
    """使用Python requests下载"""
    try:
        import requests
        
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return True
    except Exception as e:
        print(f"Python下载失败: {e}")
        return False


def verify_file(filepath: Path, min_size: int = 1000) -> bool:
    """验证文件是否有效"""
    if not filepath.exists():
        return False
    
    size = filepath.stat().st_size
    if size < min_size:
        print(f"文件太小: {size} bytes")
        return False
    
    return True


def download_file(url: str, output_path: Path, description: str) -> bool:
    """尝试多种方法下载文件"""
    print(f"\n📥 下载: {description}")
    print(f"   URL: {url}")
    print(f"   输出: {output_path}")
    
    # 如果文件已存在且有效，跳过
    if verify_file(output_path):
        print(f"   ✅ 文件已存在且有效")
        return True
    
    # 尝试多种下载方法
    methods = [
        ("curl", download_with_curl),
        ("wget", download_with_wget),
        ("Python requests", download_with_python),
    ]
    
    for method_name, method_func in methods:
        print(f"   尝试使用 {method_name}...")
        try:
            if method_func(url, output_path):
                if verify_file(output_path):
                    print(f"   ✅ 下载成功！")
                    return True
                else:
                    print(f"   ❌ 文件验证失败")
                    if output_path.exists():
                        output_path.unlink()
        except Exception as e:
            print(f"   ❌ {method_name} 失败: {e}")
    
    print(f"   ❌ 所有下载方法都失败了")
    return False


def main():
    """主函数"""
    # 设置输出目录
    project_root = Path(__file__).parent.parent
    output_dir = project_root / 'assets' / 'cc2_resources'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("CC2资源下载工具")
    print("=" * 60)
    
    # 定义要下载的资源
    resources = [
        {
            'url': 'https://closecombat2.hpage.com/get_file.php?id=23591021&vnr=473429',
            'filename': 'CC2Guide-SpriteFiles-v9.zip',
            'description': 'CC2精灵文件格式指南',
        },
        {
            'url': 'https://closecombat2.hpage.com/get_file.php?id=30120667&vnr=908650',
            'filename': 'CC2MapMuseum.zip',
            'description': 'CC2地图博物馆',
        },
        {
            'url': 'https://closecombat2.hpage.com/get_file.php?id=23591023&vnr=812344',
            'filename': 'CC2Guide-Terrain-File-v5.pdf',
            'description': 'CC2地形文件格式指南',
        },
    ]
    
    # 下载所有资源
    success_count = 0
    for resource in resources:
        output_path = output_dir / resource['filename']
        if download_file(resource['url'], output_path, resource['description']):
            success_count += 1
    
    # 总结
    print("\n" + "=" * 60)
    print(f"下载完成: {success_count}/{len(resources)} 个文件成功")
    print("=" * 60)
    
    if success_count == len(resources):
        print("\n✅ 所有资源下载成功！")
        print(f"\n资源位置: {output_dir}")
        print("\n下一步:")
        print("1. 解压ZIP文件")
        print("2. 运行 parse_cc2_spr.py 解析精灵文件")
        return 0
    else:
        print("\n⚠️ 部分资源下载失败")
        print("\n备选方案:")
        print("1. 检查网络连接")
        print("2. 手动下载资源文件")
        print("3. 使用程序化生成的精灵（已生成）")
        return 1


if __name__ == '__main__':
    sys.exit(main())
