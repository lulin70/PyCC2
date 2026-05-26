# ⚠️ SUPERSEDED - See VISUAL_ROUTE_CORRECTION.md
#
# This proposal was based on the INCORRECT assumption that CC2 uses Isometric projection.
# Analysis of original CC2 screenshots confirms CC2 uses Orthographic Top-Down.
# The isometric implementation is preserved as an optional experimental feature.

# PyCC2 等距投影架构方案 (Isometric Projection Architecture)

> 版本: v1.0
> 状态: 待评审
> 作者: 架构师
> 日期: 2026-05-24
> 评审人: 产品经理 / 独立开发者 / 测试专家

---

## 一、变更概述

将 PyCC2 的渲染管线从**正交俯视投影 (Orthographic Top-Down)** 迁移到**45°等距投影 (Isometric Projection)**，以还原 CC2 原版的视觉风格。

### 变更级别: 架构级 (Architecture-Level)

**影响范围**:
- 渲染管线 (Rendering Pipeline)
- 坐标系统 (Coordinate System)
- 输入处理 (Input Handling)
- 相机系统 (Camera System)
- 精灵系统 (Sprite System)
- 地图渲染 (Map Rendering)
- 小地图 (Minimap)

### 为什么需要这个变更

CC2 原版使用 45° 等距投影，建筑物显示顶面+侧面，地形有高度感，单位有"厚度"。当前正交俯视投影导致：
1. 建筑物只能看到屋顶，无立体感
2. 地形高度差异无法视觉表达
3. 单位看起来是"贴在地上的纸片"
4. 整体视觉评分仅 5.5/10，远低于 CC2 原版

---

## 二、技术方案

### 2.1 坐标变换公式

```
世界坐标 (wx, wy, wz) → 等距屏幕坐标 (sx, sy)

sx = (wx - wy) × TILE_W / 2
sy = (wx + wy) × TILE_H / 2 - wz × HEIGHT_SCALE

其中:
  TILE_W = 64 (菱形瓦片宽度)
  TILE_H = 32 (菱形瓦片高度, 2:1 宽高比)
  HEIGHT_SCALE = 16 (每级高度偏移像素)
```

**逆变换**:
```
等距屏幕坐标 (sx, sy) → 世界坐标 (wx, wy)

wx = (sx / (TILE_W/2) + sy_adjusted / (TILE_H/2)) / 2
wy = (sy_adjusted / (TILE_H/2) - sx / (TILE_W/2)) / 2

其中 sy_adjusted = sy + wz × HEIGHT_SCALE
```

### 2.2 深度排序 (Painter's Algorithm)

```
sort_key = wx + wy + wz × 0.01

绘制顺序: sort_key 从小到大 (远→近)
层优先级: terrain < decoration < unit < effect
```

### 2.3 Camera 双模式

```python
class ProjectionMode(Enum):
    ORTHOGRAPHIC = "orthographic"  # 当前模式，保持兼容
    ISOMETRIC = "isometric"        # 新模式

@dataclass
class Camera:
    projection: ProjectionMode = ProjectionMode.ORTHOGRAPHIC

    def world_to_screen(self, world_pos):
        if self.projection == ProjectionMode.ISOMETRIC:
            return self._world_to_screen_isometric(world_pos)
        return self._world_to_screen_orthographic(world_pos)
```

**关键设计决策**: 默认仍为 ORTHOGRAPHIC，通过配置切换到 ISOMETRIC，确保渐进式迁移不破坏现有功能。

---

## 三、新增文件清单

| 文件 | 职责 | 依赖 | 状态 |
|------|------|------|------|
| `isometric_transform.py` | 纯数学坐标变换 (零 pygame 依赖) | 无 | ✅ 已实现 |
| `isometric_tile_generator.py` | 程序化等距瓦片生成 | pygame, isometric_transform | ✅ 已实现 |
| `isometric_depth_sorter.py` | 深度排序策略 | isometric_transform | 待实现 |
| `isometric_renderer.py` | 等距渲染管线分支 | isometric_transform, camera | 待实现 |
| `isometric_building_renderer.py` | 建筑物等距渲染 (顶面+侧面) | isometric_transform | 待实现 |

## 四、修改文件清单

| 文件 | 变更内容 | 风险 | 状态 |
|------|---------|------|------|
| `camera.py` | 新增 ProjectionMode 枚举, 双模式 world_to_screen/screen_to_world | 低 | ✅ 已实现 |
| `enhanced_renderer.py` | 根据 camera.projection 分支渲染 | 中 | 待实现 |
| `sprite_renderer.py` | 等距深度排序 + 精灵位置偏移 | 中 | 待实现 |
| `minimap.py` | 等距小地图渲染 | 低 | 待实现 |
| `interaction_controller.py` | 等距模式下的点击拾取 | 中 | 待实现 |

---

## 五、三阶段迁移计划

### Phase 1: 基础设施 + 双模式 (当前阶段)

**目标**: 建立等距投影基础设施，不破坏现有功能

**产出**:
- [x] `isometric_transform.py` — 纯数学坐标变换
- [x] `isometric_tile_generator.py` — 7种等距瓦片程序化生成
- [x] `camera.py` — ProjectionMode 枚举 + 双模式切换
- [x] 26个单元测试全部通过
- [ ] `isometric_depth_sorter.py` — 深度排序策略

**验收标准**:
- 所有现有测试继续通过
- 新增测试覆盖等距变换
- 切换 ProjectionMode.ISOMETRIC 后坐标变换正确

### Phase 2: 完整等距渲染管线

**目标**: 实现完整的等距渲染，可切换对比

**产出**:
- [ ] `isometric_renderer.py` — 等距地形/单位/效果渲染
- [ ] `isometric_building_renderer.py` — 建筑物立体渲染
- [ ] `enhanced_renderer.py` — 投影模式分支
- [ ] `sprite_renderer.py` — 等距深度排序
- [ ] `interaction_controller.py` — 等距点击拾取
- [ ] `minimap.py` — 等距小地图

**验收标准**:
- 按 `I` 键切换正交/等距视图
- 等距模式下所有交互正常 (选择/移动/攻击)
- 建筑物显示顶面+侧面
- 视觉评分 ≥ 7/10

### Phase 3: 优化 + 默认切换

**目标**: 性能优化，等距模式成为默认

**产出**:
- [ ] 等距瓦片缓存系统
- [ ] 脏矩形渲染优化
- [ ] 精灵批处理渲染
- [ ] 默认投影切换为 ISOMETRIC
- [ ] 外部精灵资源集成 (PixVoxel CC0)

**验收标准**:
- 等距模式帧率 ≥ 30 FPS (100×100 地图)
- 内存占用 ≤ 正交模式 × 1.5
- E2E 测试全部通过

---

## 六、风险评估

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 等距模式下交互拾取不准 | 高 | 高 | 双模式并存，渐进迁移 |
| 深度排序错误导致遮挡 | 中 | 高 | 分层排序 + 单元测试 |
| 性能下降 (排序开销) | 中 | 中 | 缓存 + 脏矩形优化 |
| 现有测试回归 | 低 | 高 | Phase 1 不修改任何现有渲染逻辑 |
| 精灵资源不匹配等距视角 | 中 | 中 | PixVoxel CC0 等距精灵替代 |

---

## 七、评审要点

### 产品经理评审:
1. 等距视图是否还原了 CC2 的核心视觉体验？
2. 双模式切换是否影响用户体验？
3. 迁移期间功能是否保持完整？

### 独立开发者评审:
1. 坐标变换公式是否正确？(已通过 26 个单元测试验证)
2. Camera 双模式设计是否合理？(默认 ORTHOGRAPHIC，渐进迁移)
3. 新增文件是否遵循 DDD 架构？(presentation/rendering 层)
4. 是否有过度工程？(最小化：5个新文件 + 5个修改文件)

### 测试专家评审:
1. 等距模式下所有交互路径是否覆盖？
2. 正交/等距切换是否有状态泄漏？
3. 深度排序边界情况是否测试？
4. 性能回归测试方案是否充分？

---

## 八、外部美术资源集成方案

### 推荐资源: PixVoxel CC0 等距战争游戏精灵

| 资源 | 许可证 | 内容 | 集成方式 |
|------|--------|------|---------|
| PixVoxel Revised Isometric | CC0 | 35种军事单位+7种设施, 4方向, 站立/射击/死亡动画 | 直接加载 PNG |
| PixVoxel Mini Isometric | CC0 | 同上+296种调色板+女性士兵 | 调色板换色方案 |
| Chabull WW2 建筑/坦克 | CC0 | 俯视建筑/车辆/桥梁 | 正交模式备用 |
| CC2Spriter 提取工具 | 非商用 | 原版 CC2 精灵 | 仅参考，不可商用 |

**集成计划**:
1. 下载 PixVoxel Revised Isometric (28.8 MB, 7z)
2. 编写 `pixvoxel_loader.py` 加载器
3. 实现调色板换色 (盟军蓝→盟军绿, 轴心红→轴心灰)
4. 替换当前程序化生成的精灵

---

*文档作者: PyCC2 架构师*
*评审截止: 待定*
*下次更新: Phase 1 完成后*
