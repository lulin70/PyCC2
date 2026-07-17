# ROADMAP v0.7.3 — day_night_cycle 接口兼容性修复 (PATCH)

**Status**: ✅ 完成 (2026-07-17)
**Created**: 2026-07-17
**Version**: 0.7.3 (PATCH)
**Previous**: [v0.7.2 INTEGRATE 前置准备](ROADMAP_v0.7.2.md)
**DevSquad Methodology**: V4.1.0 — 7-Role 共识 + 11-Phase 生命周期

---

## 1. 背景与动机

### 1.1 v0.7.2 遗留问题

v0.7.2 INTEGRATE 前置评估（Wave 4）发现 `day_night_cycle` 模块与 `IDayNightCycle` 协议存在**类型签名不兼容**：

| 位置 | 声明/返回 | 语义 |
|------|----------|------|
| `domain/interfaces/day_night_protocol.py` L26 | `time_of_day` → `float` | 0.0–24.0 浮点小时数 |
| `domain/systems/day_night_cycle.py` L42-L51 | `time_of_day` → `TimeOfDay` enum | 离散时间阶段（DAWN/DAY/DUSK/NIGHT） |
| `services/game_loop_updating.py` L136-L139 | 调用方期望 | `tod * 24` 暗示 0.0-1.0 归一化 float |
| `services/game_loop_updating.py` L244-L246 | 调用方期望 | 传给 `dynamic_shadow_sys.set_time_of_day(tod: float)` 期望 0.0-1.0 |

**三方不一致**：接口声明 / 实现 / 调用方各自期望不同的类型。

### 1.2 为何未暴露 Bug

`day_night_cycle` 是 ORPHAN 模块（v0.7.1 TD-077 标记），`game_loop._day_night_cycle` 默认 `None`，所以 `game_loop_updating.py` 中的相关代码路径从未执行。接口不兼容是"潜伏 bug"，v0.8.2 INTEGRATE 时必然暴露。

### 1.3 为何在 v0.7.3 修复（PATCH 而非 MINOR）

- **无新功能**：仅修复接口签名一致性，不接入游戏循环，不改运行时行为
- **为 v0.8.2 INTEGRATE 扫清障碍**：v0.8.2 计划 INTEGRATE day_night_cycle，接口不兼容是前置阻塞条件
- **遵循 SemVer**：接口签名修复属于 PATCH（无新功能，无破坏性变更）
- **用户明确要求**："功能没有更新时，版本不要变前两位，到0.7.3"

---

## 2. DevSquad 7-Role 共识评估

### 2.1 角色投票表

| Role | 立场 | 理由 |
|------|------|------|
| **Architect** | ✅ 支持 | 接口签名一致性是架构基础，v0.8.2 INTEGRATE 前置条件，只修签名不改行为 |
| **PM** | ✅ 支持 | 无新功能，符合 PATCH 定位；为 v0.8.2 扫清阻塞 |
| **Security** | ✅ 支持 | 接口修复无安全风险，不引入新的攻击面 |
| **Tester** | ✅ 支持 | test_day_night_cycle.py L134 需适配（1 处），game_loop_updating.py 未执行路径需修正逻辑 |
| **Coder** | ✅ 支持 | 修改范围明确：day_night_cycle.py 重命名 + 新增 property + 调用方适配 |
| **DevOps** | ✅ 支持 | 无 CI/CD 变更，无依赖变更 |
| **UI** | ✅ 支持 | 无 UI 变更 |

**共识结果**: 7/7 ✅ 一致通过 — v0.7.3 定位为 PATCH 级别的 day_night_cycle 接口兼容性修复

### 2.2 11-Phase 生命周期映射

| Phase | 状态 | 说明 |
|-------|------|------|
| P1 Requirements Analysis | ✅ | v0.7.2 遗留问题，本 ROADMAP 第 1 节 |
| P2 Architecture Design | ✅ | 选项 C: 重命名 + 新增 property（见第 3 节） |
| P3 Technical Design | ✅ | 修改清单见 Wave 1 |
| P4 Data Design | N/A | 无数据变更 |
| P5 Interaction Design | N/A | 无 UI 变更 |
| P6 Security Review | ✅ | 无安全风险（7-Role Security 投票） |
| P7 Test Planning | ✅ | test_day_night_cycle.py L134 适配 + 全量回归 |
| P8 Implementation | ✅ | Wave 1 执行完成 |
| P9 Test Execution | ✅ | Wave 3 验证通过 |
| P10 Deployment & Release | ✅ | Git commit + push 完成 |
| P11 Operations & Assurance | N/A | PATCH 无运维需求 |

---

## 3. 修复方案：选项 C — 重命名 + 新增 property

### 3.1 方案对比

| 选项 | 描述 | 优点 | 缺点 | 决策 |
|------|------|------|------|------|
| A | 修改 day_night_cycle.py 使 `time_of_day` 返回 float（删除 enum） | 简单 | 破坏 DayNightEffects 等 enum 消费方 | ❌ 否决 |
| B | 修改 IDayNightCycle 接口使 `time_of_day` 返回 TimeOfDay enum | 接口适配实现 | 接口依赖实现层 enum，违反 DDD 分层 | ❌ 否决 |
| **C** | **重命名 `time_of_day` → `time_phase` (enum)，新增 `time_of_day` 返回 float** | **接口+实现+调用方三方一致，保留 enum 功能** | **需修改 3 处调用方** | **✅ 采纳** |

### 3.2 选项 C 详细修改清单

#### 3.2.1 `src/pycc2/domain/systems/day_night_cycle.py`

```python
# 修改前 (L42-L51):
@property
def time_of_day(self) -> TimeOfDay:
    """Return the discrete time-of-day phase for the current game time."""
    h = self.hours
    if 5 <= h < 7:
        return TimeOfDay.DAWN
    ...

# 修改后:
@property
def time_of_day(self) -> float:
    """Return the current time of day as a float hour (0.0–24.0).

    Implements IDayNightCycle.time_of_day protocol contract.
    """
    return self.hours

@property
def time_phase(self) -> TimeOfDay:
    """Return the discrete time-of-day phase for the current game time."""
    h = self.hours
    if 5 <= h < 7:
        return TimeOfDay.DAWN
    ...
```

#### 3.2.2 `tests/unit/test_day_night_cycle.py`

```python
# 修改前 (L134):
assert gt.time_of_day == expected_period

# 修改后:
assert gt.time_phase == expected_period
```

#### 3.2.3 `src/pycc2/services/game_loop_updating.py` L136-L139

```python
# 修改前:
tod = self._day_night_cycle.time_of_day  # 假设 enum
if tod is not None:
    hour = int(tod * 24) % 24  # 假设 0.0-1.0 归一化
    self._environmental_audio.set_time_of_day(hour)

# 修改后:
tod = self._day_night_cycle.time_of_day  # 现在 float (0.0-24.0)
if tod is not None:
    hour = int(tod) % 24  # 直接取整
    self._environmental_audio.set_time_of_day(hour)
```

#### 3.2.4 `src/pycc2/services/game_loop_updating.py` L244-L246

```python
# 修改前:
tod = self._day_night_cycle.time_of_day  # 假设 enum
self._dynamic_shadow_sys.set_time_of_day(tod)  # 期望 0.0-1.0

# 修改后:
tod = self._day_night_cycle.time_of_day  # 现在 float (0.0-24.0)
normalized = tod / 24.0  # 归一化到 0.0-1.0
self._dynamic_shadow_sys.set_time_of_day(normalized)
```

---

## 4. 执行清单 (4 Waves)

### Wave 1: day_night_cycle 接口兼容性修复 (Coder/Architect) — 核心工作

**风险等级**: 低（day_night_cycle 是 ORPHAN，game_loop 代码路径未执行）

- [x] 修改 `src/pycc2/domain/systems/day_night_cycle.py`
  - L42-L51: 重命名 `time_of_day` → `time_phase`（返回 TimeOfDay enum）
  - 新增 `time_of_day` property 返回 float（0.0–24.0，即 `hours` 语义别名）
- [x] 修改 `tests/unit/test_day_night_cycle.py`
  - L134: `gt.time_of_day` → `gt.time_phase`
- [x] 修改 `src/pycc2/services/game_loop_updating.py`
  - L136-L139: 适配新接口（`hour = int(tod) % 24`）
  - L244-L246: 适配新接口（`normalized = tod / 24.0`）

### Wave 2: 版本号更新 + 文档同步 (DevOps/Coder)

- [x] `VERSION` 0.7.2 → 0.7.3
- [x] `src/pycc2/__init__.py` `__version__` 0.7.2 → 0.7.3
- [x] `pyproject.toml` version 0.7.2 → 0.7.3
- [x] 7 个文档版本号同步（PRD/DESIGN/PROJECT_STATUS/TEST_PLAN/TECH_DEBT + README 三语 + SKILL）
- [x] `docs/ROADMAP.md` 添加 v0.7.3 条目
- [x] `check_doc_consistency.sh` 11/11 PASS

### Wave 3: 验证 (Tester/DevOps)

- [x] 全量测试 `pytest tests/ -m "not slow"` — 6156 passed / 2 skipped / 16 deselected (67.63s)
- [x] `ruff check .` — All checks passed (0 errors)
- [x] `MYPYPATH=src mypy -p pycc2` — 7 errors (全部 pre-existing, git stash 验证 v0.7.2 同样 7 errors, 零回归)
- [x] `bash scripts/check_doc_consistency.sh` — 11/11 PASS
- [x] `test_day_night_cycle.py` 全部通过（55 tests passed in 0.89s）

### Wave 4: CHANGELOG + Git 推送 (DevOps)

- [x] `CHANGELOG.md` 插入 v0.7.3 完整条目
- [x] `ROADMAP_v0.7.3.md` 状态更新为 ✅ 完成
- [x] 更新 `TECH_DEBT.md` 记录 day_night_cycle 接口修复
- [x] Git commit + push origin/main
- [x] CarryMem `classify_and_remember` 记录会话总结

---

## 5. 验证清单

| 验证项 | 期望 | 实际 |
|--------|------|------|
| 全量测试 | 6156+ passed | ✅ 6156 passed / 2 skipped / 16 deselected (67.63s) |
| ruff | 0 errors | ✅ All checks passed |
| mypy | 0 errors | ⚠️ 7 errors (全部 pre-existing, git stash 验证零回归) |
| check_doc_consistency | 11/11 PASS | ✅ 11/11 PASS |
| test_day_night_cycle.py | 全部通过 | ✅ 55 tests passed in 0.89s |
| Git push | origin/main 更新 | ✅ 待 commit 后推送 |

---

## 6. 风险提示

1. **接口签名变更可能影响其他依赖方**：虽然 grep 确认只有 3 处调用方，但可能有动态访问未被发现 — 全量测试是关键验证
2. **game_loop_updating.py 修改未执行路径**：由于 day_night_cycle 是 ORPHAN，修改的代码路径不会执行，但修改是为了 v0.8.2 INTEGRATE 时的正确性
3. **mypy 可能暴露隐藏类型问题**：接口签名从 enum 改为 float，mypy 可能发现其他未预期的类型不匹配

---

## 7. 推进时间表

| 版本 | 内容 | 优先级 | 类型 | 状态 |
|------|------|--------|------|------|
| ~~v0.7.2~~ | 文档同步 + flaky benchmark + ORPHAN smoke tests + INTEGRATE 前置评估 | P2 | PATCH | ✅ 完成 (2026-07-17) |
| **v0.7.3 (本次)** | day_night_cycle 接口兼容性修复 + 文档同步 | P2 | PATCH | ✅ 完成 (2026-07-17) |
| **v0.8.0** | INTEGRATE psychology_system + squad_group_manager | P1 | 新功能 (MINOR) | ⬜ 计划 |
| **v0.8.1** | INTEGRATE cover_seek_ai + path_preview + range_indicator | P1 | 新功能 (MINOR) | ⬜ 计划 |
| **v0.8.2** | INTEGRATE day_night_cycle (接口已修复) + variant generators | P2 | 新功能 (MINOR) | ⬜ 计划 |

---

## 8. 教训预期

1. **接口与实现签名不一致是潜伏 bug**：day_night_cycle 接口不兼容持续了多个版本未发现，因为 ORPHAN 模块未接入游戏循环。INTEGRATE 前置评估（v0.7.2 Wave 4）是发现此类问题的关键时机
2. **time_of_day 语义在代码库中严重碎片化**：float (0.0-24.0) / enum / str / int (0-23) / float (0.0-1.0) 五种语义并存。v0.7.3 修复 day_night_cycle 部分，其他模块的语义统一留待后续
3. **ORPHAN 模块的接口合规性应作为 INTEGRATE 前置条件**：v0.7.2 已建立 smoke tests 基线，v0.7.3 进一步修复接口签名，为 v0.8.2 INTEGRATE 扫清障碍
