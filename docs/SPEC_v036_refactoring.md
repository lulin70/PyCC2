# SPEC v0.3.6 — 提取 ProceduralTextureGenerator

> **文档版本**: 1.0
> **创建日期**: 2026-05-31
> **状态**: 🟡 待审批
> **父文档**: [SPEC_v035_refactoring.md](./SPEC_v035_refactoring.md)

---

## 1. 问题定义

### 1.1 当前状态 (v0.3.5 完成后)

`enhanced_renderer.py` 当前 **5651 行**，包含 4 个类：

| 类名 | 行范围 | 行数 | 状态 |
|------|--------|------|------|
| `ProceduralTextureGenerator` | L81-L1570 | **1490** | ⚠️ 待提取 |
| `SpriteGenerator` | L1571-L2339 | **769** | 待提取 (v0.3.7) |
| `TopDownParticleSystem` | L2340-L2749 | **410** | 待提取 (v0.3.8) |
| `EnhancedRenderer` | L2750-末尾 | ~2900 | 主协调器 |

### 1.2 v0.3.6 目标

提取 `ProceduralTextureGenerator` → `procedural_texture_generator.py`

**预期结果**: 5651 - 1490 = **~4161 行**（累计减少 30%）

---

## 2. 技术分析

### 2.1 类结构

```python
class ProceduralTextureGenerator:
    """CC2-authentic procedural texture generator (1490 lines, 19 methods)."""

    # 常量
    TILE_SIZE = 48  # CC2 authentic tile size

    # 公共方法
    @classmethod
    def generate_terrain_texture(cls, terrain_id, variation, palette, bitmask) -> Surface

    # 私有工具方法
    @staticmethod
    def _fill_with_variation(surface, base_color, rng, intensity)

    # 地形纹理生成方法 (14个)
    def _texture_open(surface, tid, var, pal, bitmask)      # L156-L236
    def _texture_road(surface, tid, var, pal, bitmask)      # L237-L365
    def _texture_grass(surface, tid, var, pal, bitmask)     # L366-L423
    def _texture_woods(surface, tid, var, pal, bitmask)     # L424-L486
    def _texture_building_enterable(...)                    # L487-L592
    def _texture_building_solid(...)                        # L593-L653
    def _texture_water(surface, tid, var, pal, bitmask)     # L654-L783
    def _texture_hedge(surface, tid, var, pal, bitmask)     # L784-L1011
    def _texture_wall(surface, tid, var, pal, bitmask)      # L1012-L1058
    def _texture_rough(surface, tid, var, pal, bitmask)     # L1059-L1097
    def _texture_shallow(surface, tid, var, pal, bitmask)   # L1098-L1130
    def _texture_bridge(surface, tid, var, pal, bitmask)    # L1131-L1282
    def _texture_crater(surface, tid, var, pal, bitmask)    # L1283-L1388
    def _texture_trench(surface, tid, var, pal, bitmask)    # L1389-L1561
    def _texture_default(surface, tid, var, pal, bitmask)   # L1562-L1569
```

### 2.2 依赖关系图

```
enhanced_renderer.py (当前)
├── EnhancedRenderer ──────────────┐
│   ├── L3085: ProceduralTextureGenerator.generate_terrain_texture()
│   ├── L3592: ProceduralTextureGenerator.generate_terrain_texture()
│   └── L3152: self._generate_cc2_style_tile() → [间接调用上者]
│
└── ProceduralTextureGenerator (L81-L1570, 1490行)
    ├── L109: PaletteGenerator()  ← 内部实例化
    ├── pygame.Surface (参数/返回值)
    ├── random.Random (像素变化)
    └── 14× _texture_*() 方法 (类内自调用)
```

### 2.3 提取后的依赖方向

```
enhanced_renderer.py (目标: ~4161行)
├── from .procedural_texture_generator import ProceduralTextureGenerator
├── from .palette_generator import PaletteGenerator
├── from .terrain_tile_cache import TerrainTileCache, ...
│
└── EnhancedRenderer (不变)
    └── [同上引用方式]

procedural_texture_generator.py (NEW, 1490行)
├── from .palette_generator import PaletteGenerator
├── import pygame
├── import random
│
└── class ProceduralTextureGenerator (完整迁移)
```

---

## 3. 执行计划

### Phase A: 准备工作 (~2 分钟)

- [ ] **A1**: 创建备份 tag (`git tag backup-v0.3.5`)
- [ ] **A2**: 记录基线行数 (应为 5651)
- [ ] **A3**: 运行冒烟测试确认当前稳定

### Phase B: 核心提取 (~15 分钟)

- [ ] **B1**: 创建 `procedural_texture_generator.py`
  - 添加文件头 docstring
  - 导入依赖: `pygame`, `random`, `PaletteGenerator`
  - 移动完整类定义 (L81-L1570)
  - 添加 `__all__` 声明

- [ ] **B2**: 更新 `enhanced_renderer.py`
  - 添加 `from .procedural_texture_generator import ProceduralTextureGenerator`
  - 删除原类定义 (L81-L1570)

- [ ] **B3**: Import 验证
  ```bash
  python -c "from pycc2.presentation.rendering.enhanced_renderer import EnhancedRenderer, ProceduralTextureGenerator; print('OK')"
  ```

- [ ] **B4**: 单元测试验证
  ```bash
  pytest tests/unit/test_enhanced_renderer.py -v --tb=short -q
  ```

### Phase C: 回归测试 (~12 分钟)

- [ ] **C1**: 完整回归测试 (3372+ 测试)
- [ ] **C2**: E2E 视觉测试 (14/14)
- [ ] **C3**: E2E 幽灵功能检测 (6/6)

### Phase D: 发布 (~2 分钟)

- [ ] **D1**: 统计最终行数 (目标 < 4200)
- [ ] **D2**: Git commit + tag v0.3.6

---

## 4. 风险矩阵

| 风险项 | 概率 | 影响 | 缓解措施 | 触发条件 |
|--------|------|------|----------|----------|
| **ImportError** (循环依赖) | 低 | 🔴 高 | 严格单向依赖；已验证无循环 | B3 步骤检测 |
| **测试失败 (>5 个)** | 中 | 🟡 中 | 每步即时回滚到 backup-v0.3.5 | C1 步骤检测 |
| **PaletteGenerator 引用断裂** | 低 | 🟡 中 | 新文件显式导入；运行时验证 | B3 步骤检测 |
| **类型注解前向引用失效** | 极低 | 🟢 低 | 使用字符串形式 `'PaletteGenerator'` | 已在代码中验证 |

### 4.1 回滚方案

```bash
# 如果任何步骤失败
git checkout backup-v0.3.5
# 或
git reset --hard HEAD~1  # 回到最后一次成功提交
```

**回滚触发条件**:
- ❌ 单元测试失败 > 5 个且 10 分钟内无法修复
- ❌ ImportError 或循环依赖
- ❌ E2E 测试失败 > 1 个

---

## 5. 验收标准

### Must (必须达成)

- [ ] `enhanced_renderer.py` < **4200 行** (从 5651 减少 ≥ 25%)
- [ ] 完整单元测试 **3372+ 通过** (不降低)
- [ ] E2E 视觉测试 **14/14 通过**
- [ ] E2E 幽灵功能检测 **6/6 通过**
- [ ] **零循环依赖**
- [ ] 新文件有完整 docstring + 类型注解

### Should (应该达成)

- [ ] ProceduralTextureGenerator 可独立导入和测试
- [ ] 所有 19 个方法保持原有签名和行为

### Could (可以达成)

- [ ] 为 ProceduralTextureGenerator 添加独立单元测试
- [ ] 性能无明显回退 (±5% FPS)

---

## 6. 成功指标对比

| 指标 | v0.3.5 (当前) | v0.3.6 (目标) | 改善幅度 |
|------|---------------|----------------|----------|
| **enhanced_renderer.py 行数** | 5651 | ~4161 | **-26%** |
| **累计减少行数** | 324 (v0.3.5) | **~1814** | **-30%** |
| **独立模块文件数** | 2 | **3** | +1 |
| **测试通过数** | 3372 | 3372+ | 不降低 |
| **E2E 全套** | 20/20 | 20/20 | 不降低 |

---

## 附录 A: 文件变更清单

### 新增文件

```
src/pycc2/presentation/rendering/
├── procedural_texture_generator.py  (NEW, ~1490 lines)
│   ├── class ProceduralTextureGenerator
│   │   ├── TILE_SIZE = 48
│   │   ├── generate_terrain_texture()
│   │   ├── _fill_with_variation()
│   │   └── 14× _texture_*() methods
│   └── __all__ = ["ProceduralTextureGenerator"]
```

### 修改文件

```
src/pycc2/presentation/rendering/enhanced_renderer.py
├── +from .procedural_texture_generator import ProceduralTextureGenerator
├── -class ProceduralTextureGenerator: (L81-L1570, -1490 lines)
└── [其余代码不变]
```

---

## 决策记录

| 日期 | 决策内容 | 决策人 | 理由 |
|------|----------|--------|------|
| 2026-05-31 | 采用单步提取策略（非分批） | DevSquad Architect | PTG 是单一类，无内部子模块可拆分 |
| 2026-05-31 | 显式导入 PaletteGenerator | DevSquad Coder | 避免 runtime ImportError |
| 2026-05-31 | 保持 @classmethod/@staticmethod 装饰器 | DevSquad Coder | 维持原有 API 兼容性 |

---

**审批区域**

- [ ] **Architect 审核**: 依赖方向正确性、接口兼容性
- [ ] **Tester 审核**: 测试覆盖充分性、回滚机制完备性
- [ ] **Coder 审核**: 技术可行性、import 链正确性
- [ ] **用户最终批准**: ✅ **等待您的审批**

---

> 📎 **关联文档**:
> - [SPEC_v035_refactoring.md](./SPEC_v035_refactoring.md) — 父版本 SPEC
> - [SPEC_v034_optimization.md](./SPEC_v034_optimization.md) — 祖父版本 SPEC
