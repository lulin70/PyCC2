# Archived Debug Scripts

> **归档日期**: 2026-07-13 | **来源**: v0.6.9 Wave 3 清理

这些脚本是早期开发阶段用于调试、验证和资源提取的一次性工具。经全仓库引用审计确认无外部引用（src/ 和 tests/ 中均无 import 或调用），已归档到此目录。

## 归档原因

- **零外部引用**: `grep -rn` 全仓库扫描确认无源码或测试引用
- **历史用途完成**: 脚本完成的功能已有正式实现或不再需要
- **保留物理文件**: 便于历史参考，不直接删除

## 脚本清单

| 脚本 | 原始用途 |
|------|----------|
| convert_cc2_map.py | CC2 原版地图格式转换工具 |
| create_cc2_style_sprites.py | CC2 风格精灵生成工具 |
| download_cc2_resources.py | CC2 原版资源下载工具 |
| extract_cc2_resources.py | CC2 原版资源提取工具 |
| profile_renderer.py | 渲染器性能分析工具 |
| run_and_capture.py | 游戏运行并截图工具 |
| screenshot_real_game.py | 真实游戏截图工具 |
| verify_png_in_game.py | PNG 精灵游戏内验证工具 |
| verify_real_maps.py | 真实地图验证工具 |
| verify_save_load.py | 存档加载验证工具 |

## 活跃脚本（保留在 scripts/）

| 脚本 | 用途 |
|------|------|
| download_pixvoxel_assets.py | PixVoxel 精灵资源下载（pixvoxel_loader.py 引用） |
| gen_campaign_maps.py | 战役地图生成（文档引用） |
| gen_historical_maps.py | 历史地图生成（文档引用） |
| gen_test_map.py | 测试地图生成（文档引用） |
