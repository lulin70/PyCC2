#!/usr/bin/env python3
"""
解压CC2资源文件
"""
import zipfile
from pathlib import Path


def extract_resources():
    """解压所有CC2资源"""
    base_dir = Path(__file__).parent.parent / "assets" / "cc2_resources"
    
    resources = [
        ("CC2Guide-SpriteFiles-v9.zip", "sprite_guide"),
        ("CC2MapMuseum.zip", "maps"),
        ("CC2Guide-Terrain-File-v5.pdf", "terrain_guide"),  # 实际上是ZIP
    ]
    
    print("=" * 60)
    print("CC2资源解压工具")
    print("=" * 60)
    
    for filename, extract_dir in resources:
        zip_path = base_dir / filename
        output_dir = base_dir / extract_dir
        
        if not zip_path.exists():
            print(f"\n❌ 文件不存在: {filename}")
            continue
        
        print(f"\n📦 解压: {filename}")
        print(f"   输出目录: {output_dir}")
        
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # 获取文件列表
                file_list = zip_ref.namelist()
                print(f"   包含 {len(file_list)} 个文件")
                
                # 解压所有文件
                zip_ref.extractall(output_dir)
                
                # 显示前5个文件
                print(f"   文件示例:")
                for f in file_list[:5]:
                    print(f"     - {f}")
                if len(file_list) > 5:
                    print(f"     ... 还有 {len(file_list) - 5} 个文件")
                
                print(f"   ✅ 解压成功")
                
        except Exception as e:
            print(f"   ❌ 解压失败: {e}")
            continue
    
    print("\n" + "=" * 60)
    print("解压完成")
    print("=" * 60)
    
    # 列出所有解压的目录
    print("\n📁 解压的资源:")
    for _, extract_dir in resources:
        dir_path = base_dir / extract_dir
        if dir_path.exists():
            file_count = len(list(dir_path.rglob("*")))
            print(f"   {extract_dir}: {file_count} 个文件")


if __name__ == "__main__":
    extract_resources()
