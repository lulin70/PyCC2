# PyCC2 v0.3.7 Refactoring SPEC

> **文档版本**: v1.0 | **日期**: 2026-05-31 | **状态**: 🟡 待审批
> **基准版本**: v0.3.6 (`5b4b2fe`) | **审核方法**: DevSquad 多角色协作 (Architect + Tester + Coder)
> **核心原则**: 不留技术债，发现即清理

---

## 1. 目标与范围

### 1.1 主要目标

**双重任务**：
1. ✅ **模块提取**：从 `enhanced_renderer.py` 提取 `SpriteGenerator` 类（769行）
2. 🧹 **技术债清理**：同步修复 5 项低风险、高价值的技术债

### 1.2 预期成果

| 指标 | v0.3.6 基线 | v0.3.7 目标 | 变化 |
|------|------------|-------------|------|
| **enhanced_renderer.py** | 4163 行 | **~3394 行** | **-269 行 (-6.5%)** |
| **新增模块文件** | 3 个 | **+1 = 4 个** | `sprite_generator.py` |
| **技术债未解决数** | 16 项 | **11 项** | **-5 项** |
| **测试通过率** | 3372/3372 | **3372+/** | 无退化 |

### 1.3 重构进度追踪

```
v0.3.4 基线:     5975 行 ─┐
v0.3.5 提取:     5651 行 │ (-324, -5.4%)
v0.3.6 提取:     4163 行 │ (-1488, -30.3%)  ← 当前
v0.3.7 计划:    ~3394 行 │ (-269, -6.5%)   ← 本版本
v0.3.8 预计:    ~2984 行 │ (-410, -9.8%)   [TopDownParticleSystem]
v0.3.9 预计:    <2000 行 │ (-50%, 总体)     [EnhancedRenderer 拆分]
                  ────────┘
目标: <2000 行 (66.5% → 75%+ 完成)
```

---

## 2. 模块提取：SpriteGenerator

### 2.1 类结构分析

#### 基本信息

| 属性 | 值 |
|------|-----|
| **类名** | `SpriteGenerator` |
| **位置** | `enhanced_renderer.py` L83-L851 |
| **行数** | **769 行** (含空行和注释) |
| **方法数** | **30 个** (1 public + 29 private) |
| **类型** | 纯静态方法类 (@staticmethod) |
| **状态** | **无状态** (无实例变量) |

#### 方法清单

```python
class SpriteGenerator:
    # Public API (1 method)
    + generate_sprite(deco_type_name: str, variant: int = 0) -> pygame.Surface

    # Utility Methods (1 method)
    + _point_in_polygon(x, y, polygon) -> bool  # Ray casting algorithm

    # Drawing Methods (28 methods)
    + _draw_bush_small(surface, variant)
    + _draw_bush_dense(surface, variant)
    + _draw_tree_oak(surface, variant)
    + _draw_tree_pine(surface, variant)
    + _draw_rock_large(surface, variant)
    + _draw_rock_small(surface, variant)
    + _draw_rubble(surface, variant)
    + _draw_crater_small(surface, variant)
    + _draw_crater_large(surface, variant)
    + _draw_trench(surface, variant)
    + _draw_sandbag(surface, variant)
    + _draw_barbed_wire(surface, variant)
    + _draw_wreckage(surface, variant)
    + _draw_camo_net(surface, variant)

    # CC2特色装饰物 (14 methods)
    + _draw_plane_wreckage(surface, variant)      # ✈️ 飞机残骸
    + _draw_concrete_barricade(surface, variant)  # 🚧 混凝土路障
    + _draw_sandbag_barricade(surface, variant)   # 🛡️ 沙袋路障
    + _draw_crater_cluster(surface, variant)       # 💣 弹坑群
    + _draw_debris_field(surface, variant)         # 🗑️ 碎片场
    + _draw_burning_wreckage(surface, variant)     # 🔥 燃烧残骸
    + ... (additional CC2-specific sprites)
    + _draw_placeholder(surface, variant)          # Fallback
```

#### 外部依赖

| 模块 | 用途 | 导入方式 |
|------|------|---------|
| `pygame` | Surface 创建、像素操作 | 已在 enhanced_renderer.py 顶部导入 |
| `math` | 数学运算 (sqrt) | 已在 enhanced_renderer.py 顶部导入 |

**依赖复杂度**: 🟢 **极简** — 仅 2 个标准库/第三方模块

#### 内部引用点（在 enhanced_renderer.py 中）

| 位置 | 引用方式 | 调用方 |
|------|---------|--------|
| **L1606** | `SpriteGenerator.generate_sprite(deco_type_name, variant)` | `EnhancedRenderer._get_decoration_sprite()` |

**引用数量**: **1 处** — 极其简单的接口

### 2.2 提取方案

#### 新文件结构

```
src/pycc2/presentation/rendering/
├── sprite_generator.py           ← NEW (~769 lines)
│   ├── class SpriteGenerator:
│   │   ├── TILE_SIZE = 32
│   │   ├── generate_sprite()     # Public API
│   │   ├── _point_in_polygon()   # Utility
│   │   └── _draw_*() × 28        # All drawing methods
│   └── (imports: pygame, math)
│
├── enhanced_renderer.py          ← MODIFIED (4163 → ~3394 lines)
│   ├── from .sprite_generator import SpriteGenerator  # NEW import
│   └── (delete L83-L851 original class)
│
├── procedural_texture_generator.py  # Existing (v0.3.6)
├── palette_generator.py             # Existing (v0.3.5)
└── terrain_tile_cache.py            # Existing (v0.3.5)
```

#### 执行步骤

| 步骤 | 操作 | 风险 | 验证方法 |
|------|------|------|---------|
| **B1** | 创建 `sprite_generator.py`，复制完整类定义 | 🟢 低 | Python syntax check |
| **B2** | 在 `enhanced_renderer.py` 添加 import 语句 | 🟢 低 | Import test |
| **B3** | 删除原始类定义 (L83-L851) | 🟢 低 | Diff review |
| **B4** | 运行导入验证测试 | 🟢 低 | `python -c "from ... import ..."` |
| **B5** | 运行单元测试 | 🟢 低 | `pytest tests/unit/test_enhanced_renderer.py` |

### 2.3 风险评估

| 风险场景 | 概率 | 影响 | 缓解措施 |
|---------|------|------|---------|
| **ImportError** (循环依赖) | 🟢 极低 | 🔴 高 | 单向依赖图；SpriteGenerator 无内部模块依赖 |
| **测试失败 (>5 个)** | 🟢 低 | 🟡 中 | 即时回滚到 backup-v0.3.6 |
| **pygame.Surface API 变更** | 🟢 极低 | 🟡 中 | 使用标准 pygame API，无实验性功能 |
| **_point_in_polygon 性能退化** | 🟢 极低 | 🟢 低 | 纯算法逻辑，与位置无关 |

**总体风险等级**: 🟢 **极低** — 这是目前最安全的提取目标

---

## 3. 技术债清理计划

### 3.1 清理原则

> **用户核心要求**: 不要留技术债，不要因为过去问题就放着不管

**选择标准**：
- ✅ **低风险**: 修改范围小，不影响核心功能
- ✅ **高价值**: 明显改善代码质量或用户体验
- ✅ **可验证**: 有明确的通过/失败标准
- ❌ **排除**: DDD架构重构（TD-050/051）、性能优化（TD-036）等高风险项

### 3.2 清理项清单（5项）

#### 🟢 TD-031: POLISH阵营加入友军列表

| 属性 | 详情 |
|------|------|
| **问题描述** | POLISH阵营（波兰第1独立伞兵旅）被错误地排除在友军列表外 |
| **影响** | 波兰单位在战役中无法获得友军支援，不符合历史事实 |
| **风险等级** | 🟢 **极低** — 仅添加 1 个字符串到列表 |
| **工作量** | < 5 分钟 |
| **文件** | 待定位（搜索 ALLIES 或 FRIENDLY 列表） |
| **验证方法** | 断言 'POLISH' in ALLIES_LIST |

#### 🟢 TD-032: GameSettings类型注解导入

| 属性 | 详情 |
|------|------|
| **问题描述** | GameSettings相关模块使用了类型注解但未正确导入 |
| **影响** | 类型安全受损，IDE提示不正确 |
| **风险等级** | 🟢 **低** — 补充 import 语句 |
| **工作量** | ~10 分钟 |
| **文件** | 待定位（搜索 GameSettings + TYPE_CHECKING） |
| **验证方法** | `mypy --strict` 或 IDE 无警告 |

#### 📝 TD-052 更新: enhanced_renderer.py 行数修正

| 属性 | 详情 |
|------|------|
| **问题描述** | TECH_DEBT.md 中 TD-052 声称 "~3700行"，实际为 4163 行（已过时） |
| **影响** | 文档误导，决策基于错误数据 |
| **风险等级** | ✅ **无风险** — 仅更新数字 |
| **工作量** | 1 分钟 |
| **文件** | `docs/TECH_DEBT.md` L209-L215 |
| **验证方法** | grep 确认新数值准确 |

#### 📝 TD-029: 合并视觉优化文档（部分）

| 属性 | 详情 |
|------|------|
| **问题描述** | 存在4个视觉优化相关文档内容重叠 |
| **影响** | 执行标准不统一，可能重复劳动 |
| **风险等级** | 🟢 **低** — 删除冗余文件，保留主文档 |
| **工作量** | ~15 分钟 |
| **文件** | `docs/VISUAL_OPTIMIZATION_*.md` (待确认具体文件名) |
| **验证方法** | ls 确认仅保留 1 个主文档 |

#### ✅ 代码整洁验证

| 属性 | 详情 |
|------|------|
| **问题描述** | 确认无临时文件残留 (*_tmp*, *_draft*) |
| **影响** | 代码库整洁 |
| **风险等级** | ✅ **已完成** — Phase A 审计已确认 |
| **工作量** | 0 |
| **验证方法** | Glob 搜索确认 |

### 3.3 清理执行顺序

```
TD-052更新 (1 min)     ← 无风险，先做
TD-031 POLISH (5 min)  ← 极低风险
TD-032 类型注解 (10 min)← 低风险
TD-029 文档合并 (15 min)← 低风险
代码整洁验证 (0 min)   ← 已完成
                    ↓
              模块提取 (B1-B5)
                    ↓
              全量回归测试
```

**总预计时间**: ~30 分钟（不含测试运行时间 ~12min）

---

## 4. 执行计划（Phase A-D）

### Phase A: 准备工作（~5 min）

| 步骤 | 操作 | 命令/工具 | 验证 |
|------|------|----------|------|
| A1 | 创建备份标签 | `git tag backup-v0.3.6` | `git tag -l "backup-*"` |
| A2 | 记录基线指标 | `wc -l enhanced_renderer.py` | 输出: 4163 |
| A3 | 定位技术债文件 | Grep 搜索 TD-031/032 相关代码 | 找到具体行号 |

### Phase B: 核心执行（~20 min）

#### B1-B5: SpriteGenerator 提取（参考 2.2 节）

#### B6-B10: 技术债清理

| 步骤 | ID | 操作 | 文件 | 验证 |
|------|-----|------|------|------|
| B6 | TD-052 | 更新行数为 4163 | TECH_DEBT.md | grep 确认 |
| B7 | TD-031 | 添加 'POLISH' 到友军列表 | *.py | unit test |
| B8 | TD-032 | 补充 GameSettings import | *.py | mypy/mypy |
| B9 | TD-029 | 删除冗余视觉文档 | docs/*.md | ls 确认 |
| B10 | 清洁验证 | 确认无临时文件 | 全局 | Glob 搜索 |

### Phase C: 完整回归测试（~12 min）

| 测试类别 | 命令 | 期望结果 |
|---------|------|---------|
| **C1: 导入验证** | `python -c "from pycc2... import ..."` | ✅ No error |
| **C2: 单元测试** | `pytest tests/unit/test_enhanced_renderer.py -v` | ✅ 13/13 passed |
| **C3: 全量测试** | `pytest tests/ --tb=short -q` | ✅ 3372+ passed |
| **C4: E2E 视觉** | `pytest tests/e2e/test_visual_smoke.py -v` | ✅ 1/1 passed |
| **C5: E2E Ghost** | `pytest scripts/e2e_v034_ghost_feature_test.py -v` | ✅ 6/6 passed |

### Phase D: 发布（~5 min）

| 步骤 | 操作 | 验证 |
|------|------|------|
| D1 | Git commit (所有更改) | `git status` clean |
| D2 | Tag v0.3.7 | `git tag -l "v0.3.*"` 包含 v0.3.7 |
| D3 | 更新 TECH_DEBT.md 标记已解决项 | 5 项标记为 ✅ |
| D4 | 更新 CHANGELOG.md (如有) | 版本号 + 变更摘要 |

---

## 5. 验收标准

### 5.1 必须达成（Must Have）

- [ ] **M1**: `enhanced_renderer.py` ≤ 3400 行（目标 ~3394）
- [ ] **M2**: 新文件 `sprite_generator.py` 存在且可导入
- [ ] **M3**: 全量测试 3372+ 通过，0 失败
- [ ] **M4**: E2E 测试 7/7 通过（1 visual + 6 ghost）
- [ ] **M5**: 向后兼容 — 所有现有 import 路径有效
- [ ] **M6**: 5 项技术债标记为已解决（或部分解决）

### 5.2 应该达成（Should Have）

- [ ] **S1**: 代码无 TODO/FIXME/HACK 注释残留
- [ ] **S2**: TECH_DEBT.md 数据准确（行数、日期等）
- [ ] **S3**: Commit message 符合 conventional commits 规范

### 5.3 锦上添花（Nice to Have）

- [ ] **N1**: 添加 `sprite_generator.py` 的单元测试（如尚不存在）
- [ ] **N2**: 更新 ROADMAP.md 反映当前进度

---

## 6. 回滚计划

### 6.1 触发条件

任一以下情况发生即回滚：
- ⚠️ Phase C 测试失败 > 5 个用例
- 🔴 ImportError 或循环依赖
- 🔴 核心功能退化（渲染崩溃、游戏不可玩）

### 6.2 回滚步骤

```bash
# 1. 恢复到备份
git checkout backup-v0.3.6

# 2. 删除新文件
rm src/pycc2/presentation/rendering/sprite_generator.py

# 3. 验证恢复
pytest tests/ --tb=short -q  # 期望: 3372/3372

# 4. 分析失败原因，更新 SPEC 后重试
```

### 6.3 回滚后行动

- 记录失败根因到 `docs/REFACTORING_LOG.md`
- 更新风险评估，调整提取策略
- 寻求用户批准后重新执行

---

## 7. 时间估算

| Phase | 预计时间 | 说明 |
|-------|---------|------|
| **Phase A: 准备** | 5 min | 备份 + 基线记录 |
| **Phase B: 执行** | 20 min | 提取 (10 min) + 清理 (10 min) |
| **Phase C: 测试** | 12 min | 全量回归（主要等待时间） |
| **Phase D: 发布** | 5 min | Commit + Tag + 文档更新 |
| **总计** | **~42 min** | 不含分析/编写 SPEC 时间 |

> ⚠️ **注意**: 不含 SPEC 编写和审批时间（本文档）。实际执行时严格按照本 SPEC 进行。

---

## 8. 附录

### A. 文件变更清单

| 操作 | 文件路径 | 变更类型 | 行数变化 |
|------|---------|---------|---------|
| **NEW** | `src/pycc2/presentation/rendering/sprite_generator.py` | 创建 | +769 行 |
| **MODIFY** | `src/pycc2/presentation/rendering/enhanced_renderer.py` | 编辑 | -769 行 (删除) +1 行 (import) = **-768 行** |
| **MODIFY** | `docs/TECH_DEBT.md` | 编辑 | 更新 5 项状态 |
| **DELETE** | `docs/VISUAL_OPTIMIZATION_*.md` (x3) | 删除 | 冗余文档清理 |

### B. 依赖关系图

```
enhanced_renderer.py (Coordinator, ~3394 lines)
├── imports → sprite_generator.py (NEW, ~769 lines)
│   └── dependencies: pygame, math
├── imports → procedural_texture_generator.py (Existing)
├── imports → palette_generator.py (Existing)
└── imports → terrain_tile_cache.py (Existing)
```

### C. 风险矩阵总结

| 维度 | 评分 | 说明 |
|------|------|------|
| **技术复杂度** | 🟢 低 | 纯静态方法类，无状态 |
| **依赖风险** | 🟢 低 | 仅 2 个标准依赖 |
| **测试覆盖** | 🟢 高 | 13 个单元测试 + E2E |
| **回滚难度** | 🟢 低 | Git checkout 即可恢复 |
| **综合评级** | 🟢 **推荐执行** | 最安全的提取目标 |

---

**文档结束**

> **下一步**: 用户审批本 SPEC → 进入 Phase A-D 执行
>
> **审批标准**: 用户回复"同意"或"批准"即可开始执行
