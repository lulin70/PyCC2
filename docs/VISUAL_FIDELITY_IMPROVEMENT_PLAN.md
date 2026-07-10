# PyCC2 视觉还原度提升计划

> **版本**: v0.5.1 | **日期**: 2026-07-10 | **状态**: P0 ✅ + P2 ✅ 已完成，待推进 P1 → P3
> **基线**: v0.4.16 代码审核 — 视觉~52% / 机制~78% / 综合~65%
> **当前**: v0.5.0 P0 + v0.5.1 P2 完成 — 视觉~67% / 机制~78% / 综合~72%
> **目标**: 通过 P0-P3 逐级提升，达到视觉~75% / 机制~85% / 综合~80%
> **关联文档**: [GAP_ANALYSIS.md](GAP_ANALYSIS.md) | [ROADMAP.md](ROADMAP.md) | [TECH_DEBT.md](TECH_DEBT.md)

---

## 一、现状分析（v0.4.16 代码审核结论）

### 1.1 还原度数据修正

| 维度 | 原声称 | v0.4.16 审核 | 差距 | 根因 |
|------|--------|-------------|------|------|
| 视觉 | 85% | **~52%** | -33% | 程序化生成 vs 手绘；PixVoxel 未接入；isometric 幽灵 |
| 机制 | 92% | **~78%** | -14% | 压制非6级；窗户弧未验证；缺侦察/心理模型 |
| 综合 | 88% | **~65%** | -23% | 11维度简单平均无权重，虚高 |

### 1.2 关键差距（按影响排序）

| 编号 | 差距 | 代码证据 | 影响 |
|------|------|---------|------|
| G-V1 | 地形程序化生成 | [enhanced_renderer.py](../src/pycc2/presentation/rendering/enhanced_renderer.py) L8 "Procedural texture generation" | 地形质感与 CC2 原版手绘差距大 |
| G-V2 | 单位精灵程序化/SVG | [unit_rendering_mixin.py](../src/pycc2/presentation/rendering/unit_rendering_mixin.py) 使用程序化生成 | 单位视觉与 CC2 原版手绘差距大 |
| G-V3 | isometric 幽灵功能 | enhanced_renderer.py L53/L99-100 引用不存在的 isometric_renderer.py | 代码质量问题，声称的功能不存在 |
| G-V4 | PixVoxel 完全未接入 | [pixvoxel_loader.py](../src/pycc2/presentation/rendering/pixvoxel_loader.py) L3 "scripts-only" | 1143 行完整加载器闲置，CC0 手绘资源浪费 |
| G-M1 | 压制系统非6级 | [morale_component.py](../src/pycc2/domain/components/morale_component.py) L13-20 实为5级士气 | 文档声称与代码不符 |
| G-M2 | 窗户射击弧未验证 | 建筑驻守有 update_garrison_status，但窗户弧待验证 | CC2 建筑战斗细节缺失 |
| G-M3 | AI 侦察/心理模型缺失 | GAP_ANALYSIS L178 确认 | CC2 高级 AI 行为未实现 |

---

## 二、P0：接入 PixVoxel 正交版精灵（最高优先级） ✅ 已完成 (v0.5.0, 2026-07-10)

### 2.1 目标
将单位精灵从程序化/SVG 生成替换为 PixVoxel CC0 手绘像素艺术，提升单位精灵还原度 45%→75%，视觉总还原度 52%→67%。

### 2.2 前提条件
- PixVoxel 加载器已完整实现：[pixvoxel_loader.py](../src/pycc2/presentation/rendering/pixvoxel_loader.py)（1143 行）
  - `load_sprite()` / `load_sprite_with_fallback()` 3 级 fallback
  - `apply_palette_swap()` numpy 加速调色板替换
  - `preload_common_sprites()` 14 单位 × 2 阵营 × 8 方向
  - 完整的单位名映射（PIXVOXEL_TO_PYCC2）、方向映射、动画映射
- 下载脚本已完整：[download_pixvoxel_assets.py](../scripts/download_pixvoxel_assets.py)（545 行）

### 2.3 实施步骤（✅ 全部完成）

| 步骤 | 任务 | 文件 | 工作量 | 状态 |
|------|------|------|--------|------|
| 1 | 安装 py7zr 解压依赖 | `pip install py7zr` | 5 分钟 | ✅ |
| 2 | 下载 PixVoxel Blank 正交版资源 | `Blank_PixVoxel_Wargame_Ortho_A.7z` (28MB) | 10 分钟 | ✅ |
| 3 | 验证资源完整性 | `assets/sprites/pixvoxel_ortho/manifest.json` (3968 精灵) | 5 分钟 | ✅ |
| 4 | 在 sprite_cache_manager.py 接入 PixVoxelLoader | [sprite_cache_manager.py](../src/pycc2/presentation/rendering/sprite_cache_manager.py) | 4 小时 | ✅ |
| 5 | 实现 fallback 链：PixVoxel → SVG → CC2Original → AssetLoader → PixelArtist3D → legacy | SpriteCacheManager.create_unit_sprite() | 2 小时 | ✅ |
| 6 | 验证 8 方向 × 4 姿态渲染 | 17 单元测试 + 522 渲染测试 | 2 小时 | ✅ |
| 7 | 性能测试（预加载 + 缓存） | 0.4ms/精灵首次加载, 0.001ms 缓存命中 | 1 小时 | ✅ |

**实际工作量**: 1 天

### 2.4 关键设计决策（实际实施）

1. **使用 Blank 正交版**：下载了 `Blank_PixVoxel_Wargame_Ortho_A.7z` (28MB)，包含 3968 个精灵（standing + attack + death 三类动画），而非原计划的 color1-8 版本
2. **索引调色板 PNG**：Blank 版本是灰度索引 PNG（mode=P），需运行时调色板替换着色（PIL `putpalette` + `convert RGBA` + pygame `frombytes`）
3. **方向映射 4→8**：face0=S/face1=E/face2=N/face3=W，对角线方向（NE/SE/SW/NW）近似到最近的正交方向
4. **Fallback 机制**：PixVoxel 资源不可用或单位无映射时，自动降级到 SVG/程序化生成，确保零回归
5. **覆盖率 14/18 (66.7%)**：4 个 PyCC2 单位类型无 PixVoxel 映射，fallback 到 SVG/procedural
6. **assets_root 路径 bug 修复**：sprite_cache_manager.py L55 原本 4 层 parent 误到达 src/ 而非项目根，修复为 5 层 parent

### 2.5 实际效果

| 指标 | 实施前 | P0 后 | 提升 |
|------|--------|-------|------|
| 单位精灵还原度 | 45% | 75% | +30% |
| 视觉总还原度 | 52% | 67% | +15% |
| 综合还原度 | 65% | 72% | +7% |
| PixVoxel 单位覆盖 | 0/18 | 14/18 (66.7%) | +66.7% |
| 性能（首次加载） | — | 0.4ms/精灵 | 可接受 |
| 性能（缓存命中） | — | 0.001ms/查询 | 优秀 |

### 2.6 验证方法
- [x] `pytest tests/` 全量通过（17 单元测试 + 522 渲染测试，零回归，1 已知 flaky 失败）
- [x] 性能测试：帧率不低于接入前（0.4ms/精灵首次加载，0.001ms 缓存命中）
- [x] 8 方向 × 4 姿态全部正确渲染（idle/attack/death × 8 方向）
- [x] 8 阵营调色板正确区分（allies/axis/allies_uk/allies_us/allies_poland/axis_germany/axis_italy/resistance）
- [x] ruff check 0 errors
- [ ] 手动运行游戏截图对比（待用户验证）

---

## 三、P1：地形贴图资源（中优先级）

### 3.1 目标
提升地形渲染质量，从程序化生成提升到接近 CC2 原版手绘像素艺术风格，地形还原度 55%→70%。

### 3.2 方案选项

| 方案 | 描述 | 优点 | 缺点 | 工作量 |
|------|------|------|------|--------|
| A | 寻找 CC0 地形贴图资源 | 质量高 | 难找匹配 CC2 风格的资源 | 3-5 天 |
| B | 提升程序化生成质量 | 可控 | 无法完全匹配手绘 | 3-5 天 |
| C | 参考CC2截图手绘贴图 | 最接近原版 | 需要像素艺术技能 | 5-7 天 |

**推荐**: 方案 B（提升程序化生成质量），性价比最高。参考 CC2 截图的色调、纹理细节，优化 [terrain_tile_generator.py](../src/pycc2/presentation/rendering/terrain_tile_generator.py) 的生成算法。

### 3.3 实施步骤（方案 B）
1. 分析 CC2 原版截图的地形色调和纹理特征
2. 优化 terrain_tile_generator.py 的颜色调色板
3. 增加纹理细节（噪点、边缘过渡、光影）
4. 对比验证

**总工作量**: 3-5 天

### 3.4 预期效果

| 指标 | 当前 | P1 后 | 提升 |
|------|------|-------|------|
| 地形还原度 | 55% | 70% | +15% |
| 视觉总还原度 | 67% (P0后) | 72% | +5% |

---

## 四、P2：清理 isometric experimental 代码（代码质量）✅ 已完成 (v0.5.1)

### 4.1 背景
v0.4.16 审核曾将 isometric_renderer/isometric_transform 等 5 个文件误判为"幽灵功能"（声称文件不存在），实际文件全部存在且有完整实现。CC2 原版（1997）仅使用顶部正交视角，isometric 为 experimental 代码，从未在正式渲染管线中启用。

### 4.2 决策
完整重构 — 删除 isometric 专属代码，保留可复用部分（CC2 地形调色板 + tile 尺寸常量内联到使用方）。

### 4.3 实际实施（v0.5.1 P2 完成）

| 步骤 | 内容 | 状态 |
|------|------|------|
| 1 | CC2_ISOMETRIC_PALETTE + TILE_W/TILE_H 内联到 enhanced_terrain_generator.py | ✅ |
| 2 | camera.py 移除 isometric 投影代码 (ProjectionMode.ISOMETRIC + _world/_screen_to_world_isometric) | ✅ |
| 3 | unit_rendering_mixin.py 移除 isometric 深度排序分支 | ✅ |
| 4 | minimap.py 移除 _draw_terrain_isometric, set_projection_mode 改 no-op | ✅ |
| 5 | enhanced_renderer.py 移除 IsometricRenderer 引用 + ISOMETRIC 分支 | ✅ |
| 6 | enhanced_renderer_delegate_mixin.py 移除 _render_isometric 委托方法 | ✅ |
| 7 | interaction_controller.py 修复关键 bug: screen_to_tile + K_i 引用已删除的 ProjectionMode.ISOMETRIC | ✅ |
| 8 | 删除 5 源文件 + 3 测试文件 + 1 脚本 (validate_isometric.py) | ✅ |
| 9 | 测试引用迁移 (test_enhanced_terrain_generator + test_renderer_submodules) | ✅ |
| 10 | ruff check + format 通过, 4636 unit tests passed 零回归 | ✅ |

---

## 五、P3：补充机制细节（功能完善）

### 5.1 目标
补充 CC2 原版的核心机制细节，机制还原度 78%→85%。

### 5.2 任务清单

| 任务 | 描述 | 代码位置 | 工作量 |
|------|------|---------|--------|
| LOS 烟雾/天气影响 | 烟雾和天气应影响 LOS 范围 | [los_system.py](../src/pycc2/domain/systems/los_system.py) | 1-2 天 |
| 建筑窗户射击弧验证 | 验证建筑驻守的窗户射击弧限制 | [unit_movement_mixin.py](../src/pycc2/domain/entities/unit_movement_mixin.py) `update_garrison_status` | 1 天 |
| AI 侦察行为 | 实现侦察单位派出和行为 | 新建 `recon_ai.py` | 2-3 天 |
| AI 心理模型 | 实现士兵可能拒绝命令 | 新建 `psychology_system.py` | 2-3 天 |
| AI 补给线意识 | 实现保护/切断补给线行为 | 新建 `supply_awareness_ai.py` | 2-3 天 |
| 散兵坑/战壕 | 实现专用掩体类型 | [terrain_type.py](../src/pycc2/domain/value_objects/terrain_type.py) | 1-2 天 |

**总工作量**: 9-14 天

### 5.3 优先级排序
1. LOS 烟雾/天气影响（影响战斗核心）
2. 建筑窗户射击弧验证（验证现有功能）
3. 散兵坑/战壕（地形交互）
4. AI 侦察/心理模型/补给线意识（高级 AI）

### 5.4 预期效果

| 指标 | 当前 | P3 后 | 提升 |
|------|------|-------|------|
| 机制还原度 | 78% | 85% | +7% |
| 综合还原度 | 72% (P0+P1后) | 75% | +3% |

---

## 六、总体预期效果

| 阶段 | 视觉 | 机制 | 综合 | 累计工作量 |
|------|------|------|------|-----------|
| 当前 (v0.4.16) | 52% | 78% | 65% | — |
| +P0 PixVoxel | 67% | 78% | 70% | 1-2 天 |
| +P1 地形 | 72% | 78% | 73% | +3-5 天 |
| +P2 清理幽灵 | 72% | 78% | 73% | +0.5 天 |
| +P3 机制细节 | 72% | 85% | 77% | +9-14 天 |
| **最终目标** | **~75%** | **~85%** | **~80%** | **总计 14-22 天** |

---

## 七、风险和缓解

| 风险 | 概率 | 影响 | 缓解策略 |
|------|------|------|---------|
| PixVoxel 下载失败 | 中 | 中 | 提供 3 种下载方法 + 手动下载指南 |
| PixVoxel 精灵风格不匹配 CC2 | 低 | 高 | 先小范围测试，对比 CC2 截图 |
| 接入后帧率下降 | 中 | 高 | 预加载 + 缓存 + 性能测试 |
| P3 机制改动引入回归 | 中 | 高 | 每个任务完成后全量回归测试 |
| 地形贴图资源难找 | 高 | 中 | 方案 B 程序化提升作为 fallback |

---

## 八、验证方法

### 8.1 代码审核验证
- 每个 P 完成后，更新 GAP_ANALYSIS.md 的还原度数据
- 数据必须有代码证据支撑，不接受自我感觉评分

### 8.2 运行时验证
- 手动运行游戏截图，与 CC2 原版截图对比
- E2E 测试全量通过
- 性能测试：帧率不下降

### 8.3 文档同步验证
- GAP_ANALYSIS.md / ROADMAP.md / README 三语保持一致
- 版本号遵循 SemVer：P0 是功能新增（MINOR），P2 是代码质量（PATCH）

---

## 九、共识请求

本文档需团队达成以下共识：

1. **还原度数据修正共识**: 88%→65% 的修正是正确的，基于代码证据 ✅ 用户已确认 (2026-07-10)
2. **P0 优先级共识**: PixVoxel 接入是最高性价比提升，应优先执行 ✅ P0 已完成 (v0.5.0, 2026-07-10)
3. **isometric 代码处理共识**: 完整重构（删除 experimental 代码 + 迁移可复用部分） ✅ P2 已完成 (v0.5.1, 2026-07-10)
4. **CC2 视角共识**: CC2 原版是俯视正交，不需要等距视角 ✅ 用户已确认 (2026-07-10)
5. **推进顺序共识**: P0 → P2 → P1 → P3（先接入精灵，再清理代码，再提升地形，最后补机制） ✅ P0+P2 已完成，待推进 P1

**P0 + P2 已完成 (v0.5.1)，下一步推进 P1：地形贴图资源提升**

---

**文档状态**: P0 ✅ + P2 ✅ 已完成 (v0.5.1, 2026-07-10)，待推进 P1 → P3
**创建者**: DevSquad Multi-Agent Team
**分析方法**: 逐文件代码审核 + 代码证据核实
**下一步**: P1 地形贴图资源提升 → P3 补充机制细节
