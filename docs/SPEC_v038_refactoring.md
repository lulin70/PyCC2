# PyCC2 v0.3.8 Refactoring SPEC

> **文档版本**: v1.0 | **日期**: 2026-05-31 | **状态**: 🟡 待审批
> **基准版本**: v0.3.7 (`5b4b2fe`) | **核心原则**: 不留技术债，发现即清理
> **特殊发现**: 🔴 重复定义 Bug（与 v0.3.5 TopDownLightingConfig 相同模式）

---

## 1. 目标与范围

### 1.1 主要目标

**双重任务**：
1. 🐛 **修复重复定义 Bug**: 删除 `enhanced_renderer.py` 中的 `TopDownParticleSystem` 重复定义（~409 行）
2. 🧹 **技术债清理**: 同步更新文档 + 审计可快速解决的项

### 1.2 预期成果

| 指标 | v0.3.7 基线 | v0.3.8 目标 | 变化 |
|------|------------|-------------|------|
| **enhanced_renderer.py** | 3396 行 | **~2987 行** | **-409 行 (-12.0%)** |
| **重复定义 Bug** | 1 个 | **0 个** | **修复** |
| **测试通过率** | 3372/3372 | **3372+/** | 无退化 |

### 1.3 重构进度追踪

```
v0.3.4 基线:     5975 行 ─┐
v0.3.5 提取:     5651 行 │ (-324, -5.4%)
v0.3.6 提取:     4163 行 │ (-1488, -30.3%)
v0.3.7 提取:    3396 行 │ (-768, -12.9%)
v0.3.8 计划:    ~2987 行 │ (-409, -12.0%)  ← 本版本
                  ────────┘
累计减少:        2988 行 (-50.0%)
目标 <2000:       进度 80%+
```

---

## 2. 🔴 核心问题：TopDownParticleSystem 重复定义

### 2.1 问题详情

#### 代码位置

```python
# enhanced_renderer.py L63 (导入)
from pycc2.presentation.rendering.particle_system import TopDownParticleSystem

# enhanced_renderer.py L85-L493 (重复定义！覆盖了上面的导入)
class TopDownParticleSystem:
    """顶部视角专用粒子特效系统"""
    def __init__(self, max_particles: int = 256):
        ...
    # ... ~409 lines of duplicated code
```

#### 文件对比

| 属性 | `particle_system.py` | `enhanced_renderer.py` L85 |
|------|--------------------|--------------------------|
| **行数** | **436 行** | **~409 行** |
| **状态** | ✅ 权威版本 | 🔴 重复（应删除） |
| **创建时间** | 更早（原始模块） | 后续复制 |
| **引用数** | 被 enhanced_renderer.py 导入 | 仅内部使用 |

### 2.2 根因分析

**与 v0.3.5 TD-045/046 相同的模式**：

1. 原始开发时，`TopDownParticleSystem` 先在 `enhanced_renderer.py` 内部定义
2. 后来提取到独立模块 `particle_system.py`
3. 添加了 import 语句（L63）
4. **但忘记删除原始类定义**（L85-L493）
5. Python 的类定义是执行语句，本地定义**覆盖**了 import 的版本

### 2.3 影响评估

| 维度 | 影响 | 严重性 |
|------|------|--------|
| **功能正确性** | ⚠️ 取决于两版代码是否同步 | 中（当前测试通过，说明暂时一致）|
| **维护性** | 🔴 修改 particle_system.py 可能不生效 | 高 |
| **代码质量** | 🔴 违反 DRY 原则 | 高 |
| **风险等级** | 🟡 **中** — 必须立即修复 | - |

### 2.4 修复方案

#### 操作步骤

| 步骤 | 操作 | 风险 |
|------|------|------|
| **B1** | 验证 `particle_system.py` 与 `enhanced_renderer.py` 版本一致性 | 🟢 低 |
| **B2** | 删除 `enhanced_renderer.py` L85-L493 的重复类定义 | 🟢 低 |
| **B3** | 保留 L63 的 import 语句（已存在） | 无需操作 |
| **B4** | 运行导入验证测试 | 🟢 低 |
| **B5** | 运行全量回归测试 | 🟢 低 |

#### 预期结果

```
enhanced_renderer.py 变化:
  L63: from .particle_system import TopDownParticleSystem  ✅ 保留
  L65: (空行)
  L66: from dataclasses import dataclass           ✅ 保留
  L67: (空行)
  L68: (空行)
  L69: # ============================================================
  L70: (空行)
  L71: class EnhancedRenderer:                      ← 直接开始 (原 L495)
  
删除: L85-L493 (含空行) = ~409 行
```

---

## 3. 技术债清理计划

### 3.1 可在本版本解决项

#### 📝 TD-052 更新: enhanced_renderer.py 行数修正

| 属性 | 详情 |
|------|------|
| **问题描述** | TECH_DEBT.md 中 TD-052 声称 "3396行"，本次将降至 ~2987 |
| **风险等级** | ✅ 无风险 |
| **工作量** | 1 分钟 |

#### 📝 TD-034 状态核实: 测试失败用例

| 属性 | 详情 |
|------|------|
| **问题描述** | TD-034 声称 "2767个测试中有1个失败"，但实际我们持续看到 3372/3372 全通过 |
| **行动** | 核实并更新状态 |
| **风险等级** | ✅ 无风险 |

#### 🔴 新增: TD-053 TopDownParticleSystem 重复定义

| 属性 | 详情 |
|------|------|
| **问题描述** | `enhanced_renderer.py` L85-L493 重复定义了已存在于 `particle_system.py` 的类 |
| **影响** | DRY 违反，维护风险 |
| **状态**: | 🔄 本次修复 |

### 3.2 清理执行顺序

```
TD-053 修复 (5 min)     ← 核心任务：删除重复定义
TD-052 更新 (1 min)     ← 文档同步
TD-034 核实 (2 min)     ← 数据准确性
                    ↓
              全量回归测试
```

---

## 4. 执行计划（Phase A-D）

### Phase A: 准备工作（~3 min）

| 步骤 | 操作 | 验证 |
|------|------|------|
| A1 | 创建备份标签 `git tag backup-v0.3.7` | `git tag -l "backup-*"` |
| A2 | 对比两个版本的差异 | `diff` 输出确认一致 |
| A3 | 记录基线指标 | `wc -l` → 3396 |

### Phase B: 核心执行（~10 min）

| 步骤 | ID | 操作 | 文件 | 验证 |
|------|-----|------|------|------|
| B1 | TD-053 | 删除 L85-L493 重复类定义 | enhanced_renderer.py | grep 确认删除 |
| B2 | TD-052 | 更新行数为 ~2987 | TECH_DEBT.md | grep 确认 |
| B3 | TD-034 | 标记为"数据过时"或"已解决" | TECH_DEBT.md | 注释更新 |

### Phase C: 完整回归测试（~12 min）

| 测试类别 | 命令 | 期望结果 |
|---------|------|---------|
| **C1: 导入验证** | `python -c "from ... import ..."` | ✅ No error |
| **C2: 单元测试** | `pytest tests/unit/test_enhanced_renderer.py -v` | ✅ 13/13 passed |
| **C3: 全量测试** | `pytest tests/ --tb=short -q` | ✅ 3372+ passed |
| **C4: E2E 视觉** | `pytest tests/e2e/test_visual_smoke.py -v` | ✅ 1/1 passed |
| **C5: E2E Ghost** | `pytest scripts/e2e_v034_ghost_feature_test.py -v` | ✅ 6/6 passed |

### Phase D: 发布（~5 min）

| 步骤 | 操作 | 验证 |
|------|------|------|
| D1 | Git commit (所有更改) | `git status` clean |
| D2 | Tag v0.3.8 | `git tag -l "v0.3.*"` 包含 v0.3.8 |
| D3 | 更新 TECH_DEBT.md | TD-053 标记✅ |

---

## 5. 验收标准

### 5.1 必须达成（Must Have）

- [ ] **M1**: `enhanced_renderer.py` ≤ 3000 行（目标 ~2987）
- [ ] **M2**: `TopDownParticleSystem` 仅在 `particle_system.py` 中定义（无重复）
- [ ] **M3**: 全量测试 3372+ 通过，0 失败
- [ ] **M4**: E2E 测试 7/7 通过
- [ ] **M5**: 向后兼容 — 所有现有 import 路径有效
- [ ] **M6**: TD-053 标记为已解决

### 5.2 应该达成（Should Have）

- [ ] **S1**: TECH_DEBT.md 所有行数数据准确
- [ ] **S2**: Commit message 符合 conventional commits 规范

---

## 6. 回滚计划

### 6.1 触发条件

- ⚠️ Phase C 测试失败 > 5 个用例
- 🔴 ImportError 或循环依赖
- 🔴 功能退化

### 6.2 回滚步骤

```bash
git checkout backup-v0.3.7
pytest tests/ --tb=short -q  # 期望: 3372/3372
```

---

## 7. 附录

### A. 文件变更清单

| 操作 | 文件路径 | 变更类型 | 行数变化 |
|------|---------|---------|---------|
| **MODIFY** | `src/pycc2/presentation/rendering/enhanced_renderer.py` | 编辑 | **-409 行** (删除重复) |
| **MODIFY** | `docs/TECH_DEBT.md` | 编辑 | 更新 3 项状态 |

### B. 风险矩阵总结

| 维度 | 评分 | 说明 |
|------|------|------|
| **技术复杂度** | 🟢 **极低** | 纯删除操作，无逻辑变更 |
| **依赖风险** | 🟢 **低** | import 已存在，仅删除冗余 |
| **测试覆盖** | 🟢 **高** | 3372+ 测试 + E2E |
| **回滚难度** | 🟢 **极低** | Git checkout 即可 |
| **综合评级** | 🟢 **强烈推荐执行** | 最安全的重构操作 |

---

**文档结束**

> **下一步**: 用户审批本 SPEC → 进入 Phase A-D 执行
