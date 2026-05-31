# SPEC v0.3.5 — EnhancedRenderer 模块拆分重构

> **文档版本**: 1.0
> **创建日期**: 2026-05-31
> **状态**: 🟡 待审批
> **DevSquad 角色**: Architect + Tester + Coder 共识

---

## 1. 问题定义

### 1.1 当前问题

`enhanced_renderer.py` 是一个 **5972 行的巨型单体文件**，包含 7 个类：

| 类名 | 行范围 | 行数 | 方法数 | 职责 |
|------|--------|------|--------|------|
| `TopDownLightingConfig` | L73-L81 | 9 | 0 | 照明配置数据类 |
| `PaletteGenerator` | L150-L2488 | **2339** | 18 | 调色板生成 |
| `ProceduralTextureGenerator` | L230-L1719 | **1490** | 20 | 程序化纹理 |
| `SpriteGenerator` | L1720-L2501 | **782** | 29 | 精灵生成 |
| `TerrainTileCache` | L2489-L2663 | **175** | 10 | 地形缓存 |
| `TopDownParticleSystem` | L2664-L3073 | **410** | 19 | 粒子系统 |
| `EnhancedRenderer` | L3074-L5972 | **2899** | 65 | 主渲染器 |

**核心问题**:
- ❌ 单一文件 5972 行，远超可维护阈值（建议 < 500 行/文件）
- ❌ `EnhancedRenderer` 主类 2899 行，承担过多协调职责
- ❌ 修改任何子功能都需要触碰主文件，增加回归风险
- ❌ 代码审查困难，新人上手成本高

### 1.2 目标

将 `enhanced_renderer.py` 从 **5972 行 → 目标 < 3500 行**（v0.3.5 阶段）

**v0.3.5 具体目标**:
- 提取 `TopDownLightingConfig` → `lighting_config.py` (-9 行)
- 提取 `TerrainTileCache` → `terrain_tile_cache.py` (-175 行)
- 提取 `PaletteGenerator` → `palette_generator.py` (-2339 行)

**预期结果**: 5972 - 2523 = **~3449 行**（减少 42%）

---

## 2. 优化方案

### 2.1 提取策略：保守渐进式

**原则**: 每次只提取 1 个模块，立即测试，确保零回归后再继续。

#### Step 1: TopDownLightingConfig (风险: 🟢 极低)

**源位置**: [enhanced_renderer.py:L73-L81](file:///Users/lin/trae_projects/PyCC2/src/pycc2/presentation/rendering/enhanced_renderer.py#L73-L81)

**目标文件**: `/src/pycc2/presentation/rendering/lighting_config.py`

```python
@dataclass
class TopDownLightingConfig:
    """Configuration for top-down lighting effects."""
    ambient_light: float = 0.6
    diffuse_direction: Tuple[float, float] = (0.3, -0.5)
    diffuse_strength: float = 0.4
    specular_strength: float = 0.15
    shadow_softness: float = 0.7
```

**依赖分析**:
- ✅ 无外部依赖（仅使用 dataclass 和 Tuple 类型注解）
- ✅ 仅被 `EnhancedRenderer.__init__()` 引用
- ✅ 提取风险：**零**

**测试影响**:
- 预计影响测试数：**0 个**（纯数据类，无逻辑变更）

---

#### Step 2: TerrainTileCache (风险: 🟢 低)

**源位置**: [enhanced_renderer.py:L2489-L2663](file:///Users/lin/trae_projects/PyCC2/src/pycc2/presentation/rendering/enhanced_renderer.py#L2489-L2663)

**目标文件**: `/src/pycc2/presentation/rendering/terrain_tile_cache.py`

**类签名**:
```python
class TerrainTileCache:
    def __init__(self, cache_size: int = 256):
        ...

    # 10 个方法:
    def get_tile(self, terrain_type: str, variant: int = 0) -> Optional[pygame.Surface]:
    def _generate_tile(self, terrain_type: str, variant: int) -> pygame.Surface:
    def _generate_grass_tile(self, variant: int) -> pygame.Surface:
    def _generate_dirt_tile(self, variant: int) -> pygame.Surface:
    def _generate_road_tile(self, variant: int) -> pygame.Surface:
    def _generate_water_tile(self, variant: int) -> pygame.Surface:
    def _generate_forest_tile(self, variant: int) -> pygame.Surface:
    def clear(self) -> None:
    def size(self) -> int:
    def prefetch_common_tiles(self) -> None:
```

**依赖分析**:
- ✅ 外部依赖：`pygame`, `random`, `logging`
- ✅ 被 `EnhancedRenderer.__init__()` 实例化
- ✅ 被 `EnhancedRenderer._render_terrain_layer()` 调用
- ⚠️ 内部调用 `PaletteGenerator` 的方法（需 import）
- ✅ 提取风险：**低**（接口清晰，10个方法职责明确）

**测试影响**:
- 直接引用该类的测试：预计 **1-2 个**
- 间接影响（通过 EnhancedRenderer）：预计 **5-8 个**
- 总计影响：**~10 个测试**

**关键注意事项**:
```python
# TerrainTileCache 内部依赖 PaletteGenerator
# 原代码 (L2520):
palette_gen = PaletteGenerator()  # ← 同文件内直接引用

# 提取后需改为:
from .palette_generator import PaletteGenerator  # ← 显式导入
```

---

#### Step 3: PaletteGenerator (风险: 🟡 中等)

**源位置**: [enhanced_renderer.py:L150-L2488](file:///Users/lin/trae_projects/PyCC2/src/pycc2/presentation/rendering/enhanced_renderer.py#L150-L2488)

**目标文件**: `/src/pycc2/presentation/rendering/palette_generator.py`

**类签名**:
```python
class PaletteGenerator:
    def __init__(self, seed: Optional[int] = None):
        ...

    # 18 个方法:
    def generate_terrain_palette(self, biome: str = "temperate") -> Dict[str, Tuple[int, int, int]]:
    def generate_unit_palette(self, faction: str = "allied") -> Dict[str, Tuple[int, int, int]]:
    def generate_building_palette(self, building_type: str = "house") -> Dict[str, Tuple[int, int, int]]:
    def generate_effect_palette(self, effect_type: str = "explosion") -> Dict[str, Tuple[int, int, int]]:
    def generate_seasonal_variation(self, base_palette: Dict, season: str) -> Dict:
    def generate_time_of_day_variation(self, base_palette: Dict, time: str) -> Dict:
    def generate_weather_variation(self, base_palette: Dict, weather: str) -> Dict:
    def blend_palettes(self, palette1: Dict, palette2: Dict, factor: float = 0.5) -> Dict:
    def create_gradient(self, color1: Tuple, color2: Tuple, steps: int = 10) -> List[Tuple]:
    def apply_shading(self, color: Tuple, shade_factor: float) -> Tuple:
    def get_shadow_color(self, base_color: Tuple) -> Tuple:
    def get_highlight_color(self, base_color: Tuple) -> Tuple:
    def desaturate(self, color: Tuple, amount: float = 0.5) -> Tuple:
    def warmify(self, color: Tuple, amount: float = 0.3) -> Tuple:
    def coolify(self, color: Tuple, amount: float = 0.3) -> Tuple:
    def randomize_hue(self, color: Tuple, range_degrees: float = 15) -> Tuple:
    def validate_palette(self, palette: Dict) -> bool:
    def export_to_surface(self, palette: Dict, size: Tuple[int, int] = (256, 32)) -> pygame.Surface:
```

**依赖分析**:
- ✅ 外部依赖：`pygame`, `random`, `typing` (Dict, Tuple, Optional, List)
- ✅ 被 `EnhancedRenderer.__init__()` 实例化
- ✅ 被 `ProceduralTextureGenerator` 内部调用
- ✅ 被 `TerrainTileCache` 内部调用
- ✅ 被 `SpriteGenerator` 内部调用
- ⚠️ **被 3 个其他提取目标类内部引用** —— 这是关键依赖链

**测试影响**:
- 直接引用该类的测试：预计 **3-5 个**
- 间接影响（通过其他类）：预计 **15-20 个**
- 总计影响：**~20-25 个测试**

**关键注意事项**:
```python
# PaletteGenerator 是核心依赖，必须最先或同步提取
# 依赖链：
#   EnhancedRenderer → PaletteGenerator (直接)
#   EnhancedRenderer → ProceduralTextureGenerator → PaletteGenerator (间接)
#   EnhancedRenderer → SpriteGenerator → PaletteGenerator (间接)
#   EnhancedRenderer → TerrainTileCache → PaletteGenerator (间接)

# 提取后所有引用处需添加显式导入
from .palette_generator import PaletteGenerator
```

---

## 3. 执行计划

### 3.1 Phase A: 准备工作 (不修改代码)

- [ ] **A1**: 备份当前稳定版本 (`git tag backup-v0.3.4`)
- [ ] **A2**: 运行基线测试，记录当前通过数 (应为 3371/3372)
- [ ] **A3**: 创建新文件占位符（空文件 + docstring）

### 3.2 Phase B: Step 1 提取 TopDownLightingConfig

- [ ] **B1**: 创建 `lighting_config.py`，移动类定义
- [ ] **B2**: 在 `enhanced_renderer.py` 中添加 `from .lighting_config import TopDownLightingConfig`
- [ ] **B3**: 删除原类定义（保留 import）
- [ ] **B4**: 运行完整测试套件
- [ ] **B5**: 验证 0 测试失败

### 3.3 Phase C: Step 2 提取 TerrainTileCache

- [ ] **C1**: 创建 `terrain_tile_cache.py`，移动类定义 + 添加 PaletteGenerator 导入
- [ ] **C2**: 在 `enhanced_renderer.py` 中添加 `from .terrain_tile_cache import TerrainTileCache`
- [ ] **C3**: 删除原类定义
- [ ] **C4**: 运行完整测试套件
- [ ] **C5**: 验证 ≤2 测试失败（如有则修复）

### 3.4 Phase D: Step 3 提取 PaletteGenerator

- [ ] **D1**: 创建 `palette_generator.py`，移动类定义
- [ ] **D2**: 在以下文件中添加显式导入：
  - `enhanced_renderer.py`
  - `procedural_texture_generator.py` (如果已提取)
  - `sprite_generator.py` (如果已提取)
  - `terrain_tile_cache.py` (已在 Phase C 完成)
- [ ] **D3**: 删除原类定义
- [ ] **D4**: 运行完整测试套件
- [ ] **D5**: 验证 ≤5 测试失败（如有则修复）

### 3.5 Phase E: 最终验证

- [ ] **E1**: 统计 `enhanced_renderer.py` 新行数（目标 < 3500）
- [ ] **E2**: 运行完整回归测试（目标 3371+ 通过）
- [ ] **E3**: 运行 E2E 视觉测试（14/14 通过）
- [ ] **E4**: 运行 E2E 幽灵功能检测（6/6 通过）
- [ ] **E5**: 代码走查（确认无遗漏 import 或断开的引用）

---

## 4. 风险矩阵

| 风险项 | 概率 | 影响 | 缓解措施 | 负责人 |
|--------|------|------|----------|--------|
| **循环依赖** (A↔B 互相 import) | 低 | 🔴 高 | 严格单向依赖图；延迟导入 (lazy import) | Architect |
| **测试大面积失败** (>10 个) | 中 | 🟡 中 | 每步只提取 1 个类；即时回滚 | Tester |
| **运行时 ImportError** | 低 | 🔴 高 | 每步运行 `python -c "from ... import ..."` 验证 | Coder |
| **性能回退** (import 开销) | 极低 | 🟢 低 | 使用相对导入；Python 缓存已编译模块 | DevOps |
| **IDE/类型检查器报错** | 中 | 🟢 低 | 更新 `py.typed` 标记；添加 `__all__` 声明 | Coder |

### 4.1 回滚方案

**每步都有 Git checkpoint**:
```bash
# 如果 Step N 失败，立即回滚到前一步
git checkout HEAD~1  # 回退到最后一次成功提交
# 或者回到备份点
git checkout backup-v0.3.4
```

**回滚触发条件**:
- ❌ 单步测试失败 > 5 个且无法在 15 分钟内修复
- ❌ 出现循环依赖错误
- ❌ E2E 视觉测试失败 > 1 个

---

## 5. 验收标准

### 5.1 必须达成 (Must)

- [ ] `enhanced_renderer.py` 行数 < **3600 行**（从 5972 行减少 ≥ 39%）
- [ ] 完整单元测试 **3371+ 通过**（允许 1 个预存失败）
- [ ] E2E 视觉测试 **14/14 通过**
- [ ] E2E 幽灵功能检测 **6/6 通过**
- [ ] **零循环依赖**（`python -c "import pycc2"` 无报错）
- [ ] 所有新文件有完整的 docstring 和类型注解

### 5.2 应该达成 (Should)

- [ ] 新文件的单元测试覆盖率 > 80%
- [ ] `EnhancedRenderer` 主类 < **2800 行**（从 2899 行减少）
- [ ] 代码复杂度（圈复杂度）不增加

### 5.3 可以达成 (Could)

- [ ] 提取 `TopDownLightingConfig` 到独立配置包
- [ ] 为 `PaletteGenerator` 添加 CLI 工具（调试用）

---

## 6. 时间估算

| 阶段 | 预估时间 | 并行度 |
|------|----------|--------|
| Phase A: 准备工作 | 5 分钟 | 串行 |
| Phase B: Step 1 (LightingConfig) | 10 分钟 | 串行 |
| Phase C: Step 2 (TerrainTileCache) | 20 分钟 | 串行 |
| Phase D: Step 3 (PaletteGenerator) | 30 分钟 | 串行 |
| Phase E: 最终验证 | 15 分钟 | 串行 |
| **总计** | **~80 分钟** | — |

> ⚠️ **注意**: 不含测试运行时间（完整回归 ~12 分钟），实际总耗时 ~90-120 分钟。

---

## 7. 成功指标对比

| 指标 | v0.3.4 (当前) | v0.3.5 (目标) | 改善幅度 |
|------|---------------|----------------|----------|
| **enhanced_renderer.py 行数** | 5972 | ~3449 | **-42%** |
| **文件内类数量** | 7 个 | 4 个 | **-43%** |
| **EnhancedRenderer 主类行数** | 2899 | ~2899 | 不变* |
| **独立模块文件数** | 0 | 3 个 | **+3** |
| **测试通过数** | 3371/3372 | 3371+/3372+ | 不降低 |
| **E2E 视觉测试** | 14/14 | 14/14 | 不降低 |
| **E2E 幽灵检测** | 6/6 | 6/6 | 不降低 |
| **循环依赖** | N/A | 0 | ✅ |

> *注: EnhancedRenderer 主类行数不变是正常的——本次只提取其内部的嵌套类，不重构主类本身逻辑。

---

## 8. 后续路线图 (v0.3.6+)

完成 v0.3.5 后的后续提取计划：

| 版本 | 提取目标 | 预期减少行数 | 风险等级 |
|------|----------|--------------|----------|
| **v0.3.6** | ProceduralTextureGenerator | -1490 行 | 🟡 中 |
| **v0.3.7** | SpriteGenerator | -782 行 | 🟡 中 |
| **v0.3.8** | TopDownParticleSystem | -410 行 | 🟢 低 |
| **v0.3.9** | EnhancedRenderer 方法级拆分 | -500+ 行 | 🔴 高 |
| **Target** | **最终目标 < 2000 行** | **总减少 66%** | — |

---

## 附录 A: 依赖关系图

```
┌─────────────────────────────────────────────────────────┐
│                   enhanced_renderer.py                    │
│                  (目标: 5972 → ~3449 行)                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────────────┐                               │
│  │   EnhancedRenderer   │ ← 主协调者 (2899 行，不动)     │
│  │   ┌────────────────┐ │                               │
│  │   │ 引用:          │ │                               │
│  │   │ • LightingCfg  │──┼──→ lighting_config.py (NEW)  │
│  │   │ • PaletteGen   │──┼──→ palette_generator.py (NEW)│
│  │   │ • TextureGen   │──┼──→ (留在本文件，v0.3.6 提取)  │
│  │   │ • SpriteGen    │──┼──→ (留在本文件，v0.3.7 提取)  │
│  │   │ • TileCache    │──┼──→ terrain_tile_cache.py (NEW)│
│  │   │ • ParticleSys  │──┼──→ (留在本文件，v0.3.8 提取)  │
│  │   └────────────────┘ │                               │
│  └──────────────────────┘                               │
│                                                         │
└─────────────────────────────────────────────────────────┘

外部依赖方向 (单向):
  palette_generator.py ←── terrain_tile_cache.py
  palette_generator.py ←── procedural_texture_generator.py (未来)
  palette_generator.py ←── sprite_generator.py (未来)
```

---

## 附录 B: 测试清单

### B.1 每步必跑测试

```bash
# 1. 快速冒烟测试（每次提取后立即执行，~30 秒）
pytest tests/unit/test_enhanced_renderer.py -v --tb=short -q

# 2. 受影响模块测试（~2 分钟）
pytest tests/unit/test_enhanced_renderer.py \
       tests/unit/test_palette*.py \
       tests/unit/test_terrain*.py \
       -v --tb=short -q

# 3. 完整回归测试（Phase E 执行，~12 分钟）
pytest --tb=short -q

# 4. E2E 测试（Phase E 执行）
pytest scripts/e2e_v031_visual_test.py -v
pytest scripts/e2e_v034_ghost_feature_test.py -v
```

### B.2 关键监控指标

```python
# 必须持续监控的指标
METRICS = {
    "file_line_count": lambda: count_lines("enhanced_renderer.py"),
    "test_pass_rate": lambda: run_tests().pass_rate,
    "import_success": lambda: test_import("pycc2.presentation.rendering"),
    "e2e_visual": lambda: run_e2e_visual().pass_count,
    "e2e_ghost": lambda: run_e2e_ghost().pass_count,
}

# 阈值
THRESHOLDS = {
    "file_line_count": ("<=", 3600),
    "test_pass_rate": (">=", 3371 / 3372),  # 允许 1 个预存失败
    "import_success": ("==", True),
    "e2e_visual": ("==", 14),
    "e2e_ghost": ("==", 6),
}
```

---

## 决策记录

| 日期 | 决策内容 | 决策人 | 理由 |
|------|----------|--------|------|
| 2026-05-31 | 采用保守渐进式提取策略 | DevSquad Architect | 降低大规模重构风险 |
| 2026-05-31 | v0.3.5 只提取 3 个低风险模块 | DevSquad Consensus | 先易后难，建立信心 |
| 2026-05-31 | 每步必须完整测试后才继续 | DevSquad Tester | 防止回归累积 |

---

**审批区域**

- [ ] **Architect 审核**: 结构合理性、依赖方向正确性
- [ ] **Tester 审核**: 测试覆盖充分性、回滚机制完备性
- [ ] **Coder 审核**: 技术可行性、实现细节准确性
- [ ] **用户最终批准**: ✅ **等待您的审批**

---

> 📎 **关联文档**:
> - [SPEC_v034_optimization.md](./SPEC_v034_optimization.md) — v0.3.4 父版本 SPEC
> - [GAP_ANALYSIS.md](./GAP_ANALYSIS.md) — 项目差距分析
> - [README.md](../README.md) — 项目概览
