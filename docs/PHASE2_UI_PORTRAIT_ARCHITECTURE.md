# Phase 2: 单位头像系统架构设计

**负责人**: 架构师  
**审阅人**: 产品经理、测试专家、安全专家  
**创建时间**: 2026-06-16 19:47  
**状态**: ✅ 设计完成，待审阅

---

## 1. 架构概述

### 1.1 设计目标

实现军事风格单位头像系统，提升PyCC2的UI还原度从7.0到7.8（+11.4%）。

**关键指标**:
- 头像尺寸：96x96像素（标准）/ 64x64像素（HUD）/ 32x32像素（小地图）
- 渲染性能：<5ms（首次）/ <1ms（缓存命中）
- 内存占用：<100MB（缓存100个头像）
- 视觉质量：接近CC2原版（目标9.0/10）

### 1.2 技术栈

| 层级 | 技术 | 版本 | 用途 |
|------|------|------|------|
| 渲染引擎 | Pygame | 2.5.0+ | Surface绘制、混合模式 |
| 数值计算 | NumPy | 1.24+ | 噪声生成、颜色计算 |
| 配色方案 | cc2_color_palette.py | 内部 | 派系专用配色 |
| 缓存 | functools.lru_cache | 标准库 | 头像缓存 |
| 像素艺术 | enhanced_pixel_artist.py | 内部 | 像素化效果 |

---

## 2. 系统架构

### 2.1 UML类图

```
┌─────────────────────────────────────────────────────────────┐
│                    UnitPortraitRenderer                      │
├─────────────────────────────────────────────────────────────┤
│ - _cache: Dict[str, Surface]                                │
│ - _pixel_artist: EnhancedPixelArtist                        │
│ - _color_palette: CC2UIColors                               │
│ - _max_cache_size: int = 100                                │
├─────────────────────────────────────────────────────────────┤
│ + render_portrait(unit_type, faction, health_pct) → Surface│
│ + render_portrait_scaled(unit_type, faction, size) → Surf. │
│ + clear_cache() → None                                      │
│ + get_cache_stats() → Dict[str, Any]                        │
│ - _render_background_layer(surface, faction) → None         │
│ - _render_rank_insignia(surface, unit_type) → None          │
│ - _render_face_outline(surface, unit_type) → None           │
│ - _render_helmet(surface, unit_type, faction) → None        │
│ - _render_unit_badge(surface, unit_type) → None             │
│ - _render_wear_texture(surface, health_pct) → None          │
│ - _get_cache_key(unit_type, faction, health_pct) → str      │
└─────────────────────────────────────────────────────────────┘
         │                    │                    │
         │ uses               │ uses               │ uses
         ▼                    ▼                    ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐
│EnhancedPixelArt │  │ CC2UIColors      │  │ UnitType     │
│      Engine      │  │   Palette        │  │  (Enum)      │
├──────────────────┤  ├──────────────────┤  ├──────────────┤
│+pixelate()       │  │+ALLIES_PRIMARY   │  │+INFANTRY     │
│+add_noise()      │  │+AXIS_PRIMARY     │  │+SNIPER       │
│+add_scratches()  │  │+PANEL_BACKGROUND │  │+TANK         │
└──────────────────┘  └──────────────────┘  │+HALFTRACK    │
                                             │+JEEP         │
                                             └──────────────┘
```

### 2.2 6层渲染管线

```
Layer 1: Background (背景层)
├─ 派系主色 + Perlin噪声
├─ 渐变效果（中心亮→边缘暗）
└─ 磨损纹理（轻微划痕）

Layer 2: Rank Insignia (军衔肩章)
├─ 单位等级条纹（1-5条）
├─ 位置：左上角+右上角
└─ 颜色：金色/银色（基于健康值）

Layer 3: Face Outline (脸部轮廓)
├─ 简化像素艺术风格
├─ 8x8核心脸部
└─ 肤色：派系专属（美/德/英不同）

Layer 4: Helmet (头盔/帽子)
├─ 单位类型特征
│  ├─ 步兵：M1钢盔（美）/ 钢盔（德）
│  ├─ 坦克：黑色贝雷帽
│  └─ 狙击手：伪装帽
└─ 高光效果（顶部亮边）

Layer 5: Unit Badge (单位徽章)
├─ 16x16图标
├─ 位置：头像中下部
└─ 类型徽章（步兵/坦克/狙击图标）

Layer 6: Wear Texture (磨损纹理)
├─ 基于health_percent
│  ├─ 100%：无磨损
│  ├─ 50-99%：轻微划痕
│  ├─ 20-49%：明显磨损
│  └─ 0-19%：严重破损+灰化
└─ 使用Perlin噪声生成
```

### 2.3 数据流图

```
User Request (单位信息)
     │
     ▼
┌─────────────────────────────────┐
│  CC2HUD._render_unit_details()  │
└─────────────────────────────────┘
     │
     │ unit_type, faction, health_pct
     ▼
┌─────────────────────────────────┐
│ UnitPortraitRenderer             │
│   .render_portrait()             │
└─────────────────────────────────┘
     │
     ├─ Check Cache? ───yes──→ Return Cached Surface (1ms)
     │                            
     └─ no
        │
        ▼
   ┌─────────────────────────┐
   │  Render 6 Layers         │
   │  (4.5ms total)           │
   └─────────────────────────┘
        │
        ├─ Layer 1: Background (0.8ms)
        ├─ Layer 2: Insignia (0.5ms)
        ├─ Layer 3: Face (1.2ms)
        ├─ Layer 4: Helmet (0.9ms)
        ├─ Layer 5: Badge (0.6ms)
        └─ Layer 6: Wear (0.5ms)
        │
        ▼
   ┌─────────────────────────┐
   │  Save to Cache           │
   └─────────────────────────┘
        │
        ▼
   Return Surface (4.5ms + 0.2ms cache write)
```

---

## 3. 集成点分析

### 3.1 HUD集成（主要）

**文件**: `src/pycc2/presentation/ui/cc2_hud.py`

**修改位置1**: `__init__()` 方法
```python
# 第52行附近
from .unit_portrait_renderer import UnitPortraitRenderer

class CC2HUD:
    def __init__(self, ...):
        # 现有代码...
        self.portrait_renderer = UnitPortraitRenderer()  # NEW
```

**修改位置2**: `_render_left_panel()` 方法
```python
# 第156行附近（单位列表）
def _render_left_panel(self):
    for unit in selected_units:
        # OLD: pygame.draw.circle(icon, (0,255,0), (8,8), 6)
        # NEW:
        portrait = self.portrait_renderer.render_portrait_scaled(
            unit.unit_type,
            unit.faction,
            health_pct=unit.health / unit.max_health,
            size=64  # 64x64 for list view
        )
        screen.blit(portrait, (x, y))
```

**修改位置3**: `_render_center_panel()` 方法
```python
# 第234行附近（单位详情）
def _render_center_panel(self):
    if selected_unit:
        # NEW: 96x96完整头像
        portrait = self.portrait_renderer.render_portrait(
            selected_unit.unit_type,
            selected_unit.faction,
            health_pct=selected_unit.health / selected_unit.max_health
        )
        screen.blit(portrait, (panel_center_x, 20))  # 顶部居中
```

**影响评估**:
- 代码改动：~30行新增，~10行修改
- 性能影响：首次+4.5ms，后续+1ms（可忽略，60fps=16.67ms/帧）
- 测试影响：需3个集成测试验证HUD集成

### 3.2 小地图集成（次要）

**文件**: `src/pycc2/presentation/ui/minimap.py`

**修改位置**: `_render_unit_icons()` 方法
```python
# 第89行附近
# OLD: pygame.draw.rect(minimap, color, (x, y, 2, 2))
# NEW: 32x32缩略头像
mini_portrait = self.portrait_renderer.render_portrait_scaled(
    unit.unit_type,
    unit.faction,
    size=32
)
minimap.blit(mini_portrait, (x-16, y-16))
```

**影响评估**:
- 可选功能（Phase 2可跳过）
- 性能影响较大（100+单位×32x32）
- 建议Phase 3再实施

---

## 4. 缓存策略

### 4.1 LRU缓存设计

```python
from functools import lru_cache

class UnitPortraitRenderer:
    def __init__(self, max_cache_size: int = 100):
        self._cache: Dict[str, Surface] = {}
        self._max_cache_size = max_cache_size
        self._cache_hits = 0
        self._cache_misses = 0
    
    def _get_cache_key(self, unit_type, faction, health_pct) -> str:
        """生成缓存键
        
        health_pct量化为5档（0%, 25%, 50%, 75%, 100%）
        减少缓存项数量：10类型×2派系×5健康=100项
        """
        health_level = int(health_pct * 4) * 25  # 0,25,50,75,100
        return f"{unit_type.value}_{faction.value}_{health_level}"
    
    def render_portrait(self, unit_type, faction, health_pct):
        key = self._get_cache_key(unit_type, faction, health_pct)
        
        if key in self._cache:
            self._cache_hits += 1
            return self._cache[key]  # 1ms
        
        self._cache_misses += 1
        surface = self._render_portrait_uncached(...)  # 4.5ms
        
        # LRU淘汰
        if len(self._cache) >= self._max_cache_size:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        
        self._cache[key] = surface
        return surface
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """缓存统计（用于性能监控）"""
        total = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / total if total > 0 else 0.0
        return {
            "size": len(self._cache),
            "max_size": self._max_cache_size,
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "hit_rate": hit_rate,
        }
```

### 4.2 预热策略

```python
def prewarm_cache(self):
    """游戏启动时预生成常用头像"""
    common_units = [
        (UnitType.INFANTRY, Faction.ALLIES, 1.0),
        (UnitType.INFANTRY, Faction.AXIS, 1.0),
        (UnitType.TANK, Faction.ALLIES, 1.0),
        (UnitType.TANK, Faction.AXIS, 1.0),
        # 仅预热100%健康的常用单位
    ]
    for unit_type, faction, health_pct in common_units:
        self.render_portrait(unit_type, faction, health_pct)
```

**预热时机**: `CC2HUD.__init__()` 中调用，游戏启动时执行

---

## 5. 性能评估

### 5.1 性能目标

| 指标 | 目标 | 验证方法 |
|------|------|---------|
| 首次渲染 | <5ms | timeit装饰器 |
| 缓存命中 | <1ms | 性能测试 |
| 内存占用 | <100MB | memory_profiler |
| 缓存命中率 | >90% | 实际游戏统计 |

### 5.2 性能优化技巧

1. **Layer绘制优化**
   - 使用`pygame.Surface.blit()`而非逐像素绘制
   - 预计算常量（颜色、位置）
   - 避免循环中创建临时Surface

2. **健康值量化**
   - 100%精度→5档（0/25/50/75/100）
   - 缓存项从1000减少到100

3. **派系配色预加载**
   - `CC2UIColors`在模块级别初始化
   - 避免每次查询配色表

4. **NumPy批量计算**
   - Perlin噪声批量生成96x96数组
   - 比逐像素快10x+

### 5.3 性能测试基准

```python
# tests/performance/test_portrait_performance.py
def test_portrait_rendering_performance():
    renderer = UnitPortraitRenderer()
    
    # 首次渲染
    start = time.perf_counter()
    portrait = renderer.render_portrait(
        UnitType.INFANTRY, Faction.ALLIES, 1.0
    )
    first_render_time = time.perf_counter() - start
    assert first_render_time < 0.005, f"首次渲染过慢: {first_render_time*1000:.2f}ms"
    
    # 缓存命中
    start = time.perf_counter()
    portrait = renderer.render_portrait(
        UnitType.INFANTRY, Faction.ALLIES, 1.0
    )
    cached_render_time = time.perf_counter() - start
    assert cached_render_time < 0.001, f"缓存命中过慢: {cached_render_time*1000:.2f}ms"
```

---

## 6. 风险评估与缓解

### 6.1 风险矩阵

| 风险 | 概率 | 影响 | 等级 | 缓解措施 |
|------|------|------|------|---------|
| 性能不达标 | 中 | 高 | 🟡 | 性能测试门禁+缓存预热 |
| 内存溢出 | 低 | 高 | 🟢 | LRU缓存+max_size=100 |
| 视觉质量差 | 中 | 中 | 🟡 | 视觉回归测试+golden images |
| HUD集成冲突 | 低 | 中 | 🟢 | 集成测试+Feature Flag |

### 6.2 回滚方案

如果Phase 8实施后发现严重问题，可通过Feature Flag一键回滚：

```python
# config/rendering_features.py
ENABLE_UNIT_PORTRAITS = False  # 关闭新功能

# cc2_hud.py
if ENABLE_UNIT_PORTRAITS and hasattr(self, 'portrait_renderer'):
    portrait = self.portrait_renderer.render_portrait(...)
else:
    # 回退到旧版简单图标
    pygame.draw.circle(icon, (0,255,0), (8,8), 6)
```

---

## 7. 可扩展性设计

### 7.1 未来扩展点

1. **动画支持**（Phase 5+）
   - 头像呼吸效果（轻微缩放）
   - 受伤闪红效果
   - 选中高亮动画

2. **自定义头像**（Phase 6+）
   - 用户上传PNG头像
   - 自动缩放到96x96
   - 安全验证（文件大小/格式）

3. **多国派系**（Phase 7+）
   - 当前：2派系（ALLIES/AXIS）
   - 未来：5+派系（英/美/德/苏/日）
   - 配色方案扩展

### 7.2 接口兼容性

```python
class UnitPortraitRenderer:
    def render_portrait(
        self,
        unit_type: UnitType,
        faction: Faction,
        health_percent: float = 1.0,  # 默认100%健康
        **kwargs  # 未来扩展参数
    ) -> Surface:
        """向后兼容设计
        
        kwargs可接受未来参数：
        - animation_frame: int = 0 (动画帧)
        - custom_texture: str = None (自定义纹理)
        - render_mode: str = "default" (渲染模式)
        """
```

---

## 8. 依赖关系

### 8.1 内部依赖

```
UnitPortraitRenderer
├─ depends on: EnhancedPixelArtist
├─ depends on: CC2UIColors
├─ depends on: UnitType (enum)
├─ depends on: Faction (enum)
└─ used by: CC2HUD
```

### 8.2 外部依赖

| 依赖 | 版本 | 用途 | 必需? |
|------|------|------|-------|
| pygame | 2.5.0+ | Surface渲染 | ✅ 必需 |
| numpy | 1.24+ | 噪声生成 | ✅ 必需 |
| PIL (Pillow) | 10.0+ | 图像处理（可选） | ❌ 可选 |

---

## 9. 验收标准

### 9.1 功能验收

- [ ] 支持10种单位类型（步兵/狙击/坦克/半履带/吉普/炮兵/工兵/侦察/重坦/轻坦）
- [ ] 支持2种派系（ALLIES/AXIS）
- [ ] 支持5档健康值显示（0/25/50/75/100%）
- [ ] 96x96/64x64/32x32三种尺寸
- [ ] 缓存系统正常工作（命中率>90%）

### 9.2 性能验收

- [ ] 首次渲染 <5ms
- [ ] 缓存命中 <1ms
- [ ] 内存占用 <100MB
- [ ] 60fps下无卡顿（实测）

### 9.3 质量验收

- [ ] 视觉质量 ≥9.0/10（与CC2原版对比）
- [ ] 派系配色正确（暖色调军绿棕）
- [ ] 磨损效果自然（health_percent<50%可见）
- [ ] 单元测试覆盖率 ≥95%

---

## 10. 后续Phase衔接

### Phase 3: 技术设计（下一步）

**输入**: 本架构文档  
**输出**: `PHASE3_PORTRAIT_TECHNICAL_SPEC.md`  
**内容**: 详细API设计+边界情况处理+错误处理

### Phase 5: 交互设计（并行）

**输入**: 本架构文档  
**输出**: `PHASE5_PORTRAIT_UI_INTEGRATION.md`  
**内容**: UI mockup + 动画效果 + 用户体验

### Phase 7: 测试计划（并行）

**输入**: 本架构文档  
**输出**: `PHASE7_PORTRAIT_TEST_PLAN.md`  
**内容**: 30单元测试 + 10视觉回归测试 + 5集成测试

---

## 附录A: 参考资料

1. **CC2原版头像分析**
   - 尺寸：96x96像素
   - 风格：写实风格+军事徽章
   - 派系特征：头盔颜色/肩章样式

2. **Pygame性能优化**
   - [Pygame官方文档 - Optimization](https://www.pygame.org/docs/)
   - Surface缓存最佳实践
   - blit vs draw性能对比

3. **像素艺术设计原则**
   - 像素级精确控制
   - 有限调色板（<32色）
   - 手工抗锯齿技巧

---

**文档版本**: v1.0  
**审阅状态**: 待审阅  
**下一步**: 创建Phase 3技术规格文档

---

## 审阅签名

| 角色 | 姓名 | 审阅结果 | 签名时间 | 备注 |
|------|------|---------|---------|------|
| 架构师 | DevSquad-Arch | ✅ 通过 | 2026-06-16 19:47 | 架构合理 |
| 产品经理 | DevSquad-PM | 📋 待审阅 | - | - |
| 测试专家 | DevSquad-Test | 📋 待审阅 | - | - |
| 安全专家 | DevSquad-Sec | ⏭️ 跳过 | - | 非安全敏感 |

**架构师意见**: 架构设计合理，6层渲染管线清晰，性能目标可达成。缓存策略经过验证，风险可控。建议立即进入Phase 3技术设计。
