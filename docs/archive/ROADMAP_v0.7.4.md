# ROADMAP v0.7.4 — INTEGRATE 前置准备: psychology_system + squad_group_manager (PATCH)

**Status**: ✅ 完成 (2026-07-18)
**Created**: 2026-07-18
**Version**: 0.7.4 (PATCH)
**Previous**: [v0.7.3 day_night_cycle 接口兼容性修复](ROADMAP_v0.7.3.md)
**DevSquad Methodology**: V4.1.0 — 7-Role 共识 + 11-Phase 生命周期

---

## 1. 背景与动机

### 1.1 v0.7.3 完成 + v0.8.0+ INTEGRATE 计划

v0.7.3 完成 day_night_cycle 接口兼容性修复后，ROADMAP 中 v0.8.0 计划 INTEGRATE psychology_system + squad_group_manager。但用户明确要求"功能没有更新时，版本不要变前两位，到0.7.4"——意味着 v0.7.4 应定位为 PATCH，不实际接入游戏循环（那会改变运行时行为，属于 MINOR）。

### 1.2 两个 ORPHAN 模块现状（v0.7.1 TD-077 标记）

| 模块 | 位置 | 行数 | 外部调用方 | 专属测试 | 接口定义 | INTEGRATE 工作量 |
|------|------|------|-----------|---------|---------|-----------------|
| `psychology_system` | [domain/systems/psychology_system.py](../src/pycc2/domain/systems/psychology_system.py) | 369 | 0 (完全 ORPHAN) | ✅ [test_psychology_system.py](../tests/unit/test_psychology_system.py) (93 处 evaluate_order 调用) | 无 Protocol (纯静态类) | LOW (<2h) |
| `squad_group_manager` | [presentation/ui/squad_group_manager.py](../src/pycc2/presentation/ui/squad_group_manager.py) | 149 | 0 (完全 ORPHAN) | ⚠️ 仅 5 个 smoke tests ([test_orphan_modules_smoke.py](../tests/unit/test_orphan_modules_smoke.py)) | 无 Protocol (UI 模块) | MEDIUM (2-5h) |

### 1.3 为何在 v0.7.4 做前置准备（PATCH 而非 MINOR）

- **不修改源码**: psychology_system.py 和 squad_group_manager.py 保持不变，运行时行为零变更
- **只增强测试 + 文档**: squad_group_manager 从 5 个 smoke tests 扩展到完整单元测试，创建 INTEGRATE 设计文档
- **为 v0.8.0+ INTEGRATE 扫清障碍**: 测试覆盖 + 设计文档完成后，v0.8.0 实际接入时只需关注 game_loop 集成，无需同时补测试
- **遵循 SemVer**: 测试增强 + 文档创建属于 PATCH（无新功能，无破坏性变更）
- **用户明确要求**: "功能没有更新时，版本不要变前两位，到0.7.4"

---

## 2. DevSquad 7-Role 共识评估

### 2.1 角色投票表

| Role | 立场 | 理由 |
|------|------|------|
| **Architect** | ✅ 支持 | 前置准备符合"文档先行"原则；测试增强降低 v0.8.0 INTEGRATE 风险；不修改源码零架构影响 |
| **PM** | ✅ 支持 | 无新功能，符合 PATCH 定位；为 v0.8.0 用户可感知功能（Ctrl+数字编组）做铺垫 |
| **Security** | ✅ 支持 | 无源码变更，无新攻击面；测试增强提升代码质量信心 |
| **Tester** | ✅ 支持 | squad_group_manager 仅 5 个 smoke tests 不足以为 v0.8.0 INTEGRATE 保障，需扩展边界 + 业务逻辑测试 |
| **Coder** | ✅ 支持 | 只新增测试文件 + 设计文档，不改源码，实现范围明确 |
| **DevOps** | ✅ 支持 | 无 CI/CD 变更，无依赖变更，测试数会增加但无运行时影响 |
| **UI** | ✅ 支持 | 无 UI 变更；设计文档会规划 squad_group_manager 的 UI 接入点（Ctrl+1~9 / minimap 渲染） |

**共识结果**: 7/7 ✅ 一致通过 — v0.7.4 定位为 PATCH 级别的 INTEGRATE 前置准备（测试增强 + 设计文档，不修改源码）

### 2.2 11-Phase 生命周期映射

| Phase | 状态 | 说明 |
|-------|------|------|
| P1 Requirements Analysis | ✅ | 本 ROADMAP 第 1 节 |
| P2 Architecture Design | ✅ | 测试增强 + 设计文档（见第 3 节） |
| P3 Technical Design | ✅ | 修改清单见 Wave 1 |
| P4 Data Design | N/A | 无数据变更 |
| P5 Interaction Design | N/A | 无 UI 变更（设计文档会规划，但不实现） |
| P6 Security Review | ✅ | 无安全风险（7-Role Security 投票） |
| P7 Test Planning | ✅ | squad_group_manager 测试维度规划（见第 4 节） |
| P8 Implementation | 🚧 | Wave 1 执行 |
| P9 Test Execution | ⬜ | Wave 3 验证 |
| P10 Deployment & Release | ⬜ | Git commit + push |
| P11 Operations & Assurance | N/A | PATCH 无运维需求 |

---

## 3. v0.7.4 范围：测试增强 + 设计文档

### 3.1 不做什么（留待 v0.8.0+ MINOR）

- ❌ 不修改 psychology_system.py 源码
- ❌ 不修改 squad_group_manager.py 源码
- ❌ 不接入 game_loop / game_loop_assembler / game_loop_updating
- ❌ 不修改 input handler / minimap 渲染
- ❌ 不创建 Protocol/Interface（纯静态类和 UI 模块暂不需要）

### 3.2 做什么（PATCH 范围）

#### 3.2.1 squad_group_manager 测试增强（Wave 1 核心）

现有 5 个 smoke tests 只验证"可导入 + 可实例化"，不足以为 v0.8.0 INTEGRATE 保障。需扩展到完整单元测试覆盖：

**新增测试文件**: `tests/unit/test_squad_group_manager.py`

**测试维度规划**（参考 DevSquad Testing Iron Rules §Iron Rule 3）:

| 维度 | 符号 | 最小 % | 测试内容 |
|------|------|--------|---------|
| Happy Path | ✅ | ≥50% | create_group + select_group + get_group + clear_group + clear_all_groups 正常流程 |
| Error Case | 🔴 | ≥15% | 无效 group_num (0/10/-1) / None units / 空 list / 非法类型 |
| Boundary | 🟡 | ≥10% | group_num=1 (min) / group_num=9 (max) / 空 SquadGroup / 满 9 组 |
| Performance | ⚡ | ≥5% | 1000 单元编组 + select 性能基线 |
| Configuration | ⚙️ | ≥5% | MAX_GROUPS 自定义 / 多组同时操作 |
| Integration | 🔗 | ≥10% | add_unit_to_group + remove_unit_from_all_groups 跨组操作 / bounds 计算 |

#### 3.2.2 INTEGRATE 设计文档（Wave 1 文档）

**新增设计文档章节**: 在 ROADMAP_v0.7.4.md 第 5 节记录 INTEGRATE 设计，为 v0.8.0+ 提供接入蓝图

**psychology_system 接入蓝图**:
- 接入点: AI planning loops (`tactical_ai.py` / `ai_service.py`)
- 调用方式: `PsychologySystem.evaluate_order(unit, tactic_type)` 替换/增强 `MoraleSystem.can_accept_orders()`
- 依赖: TacticType / FatigueLevel / MoraleState / SuppressionEffect / Unit (已全部存在)
- 风险: LOW (纯静态，无状态，无副作用)

**squad_group_manager 接入蓝图**:
- 接入点 1: `game_loop._squad_group_manager` 属性 (默认 None → 实例化)
- 接入点 2: input handler (Ctrl+1~9 创建组 / 1~9 选择组)
- 接入点 3: minimap 渲染 (`get_group_bounds()` 绘制彩色矩形)
- 依赖: Unit (TYPE_CHECKING only)
- 风险: MEDIUM (涉及输入处理 + UI 渲染 + 游戏循环多处修改)

---

## 4. squad_group_manager 测试维度详细规划

### 4.1 现有 smoke tests（保留，不修改）

`tests/unit/test_orphan_modules_smoke.py::TestSquadGroupManagerSmoke` (5 tests):
- test_import_squad_group_manager
- test_squad_group_instantiation
- test_squad_group_manager_instantiation
- test_squad_group_manager_create_and_select_empty
- test_squad_group_manager_clear_all

### 4.2 新增单元测试（tests/unit/test_squad_group_manager.py）

#### TestSquadGroup (SquadGroup dataclass 单元测试)
- test_add_units_copies_list (add_units 不修改原 list)
- test_clear_empties_units (clear 后 units == [])
- test_is_empty_true_after_clear
- test_bounds_none_for_empty_group
- test_bounds_single_unit (单元素 bounds)
- test_bounds_multiple_units (多元素 bounds 计算)
- test_bounds_with_float_positions (float 坐标取整)

#### TestSquadGroupManagerCreate (create_group 测试)
- test_create_group_valid_numbers_1_to_9 (1-9 全部有效)
- test_create_group_invalid_zero (group_num=0 返回 False)
- test_create_group_invalid_ten (group_num=10 返回 False)
- test_create_group_invalid_negative (group_num=-1 返回 False)
- test_create_group_empty_list (空 list 返回 True)
- test_create_group_overwrite_existing (覆盖已有组)

#### TestSquadGroupManagerSelect (select_group 测试)
- test_select_group_valid_returns_copy (返回 copy，不泄露内部 list)
- test_select_group_invalid_returns_empty (无效 num 返回 [])
- test_select_group_after_clear (clear 后返回 [])

#### TestSquadGroupManagerClear (clear 测试)
- test_clear_group_valid (clear_group 有效)
- test_clear_group_invalid (clear_group 无效 num)
- test_clear_all_groups_resets_all (clear_all_groups 全部重置)
- test_clear_group_then_select_empty (clear 后 select 返回 [])

#### TestSquadGroupManagerUnitOps (单元操作测试)
- test_add_unit_to_group_new (添加新单元)
- test_add_unit_to_group_duplicate (重复添加同一单元不重复)
- test_add_unit_to_group_invalid_num (无效 num 返回 False)
- test_remove_unit_from_all_groups (单元从所有组移除)
- test_remove_unit_not_in_groups (移除不存在的单元无副作用)

#### TestSquadGroupManagerProperties (属性测试)
- test_total_units_in_groups_empty (空时 0)
- test_total_units_in_groups_multi (多组求和)
- test_active_group_numbers_empty (空时 [])
- test_active_group_numbers_multi (多组排序)
- test_get_group_valid (有效 num 返回 SquadGroup)
- test_get_group_invalid (无效 num 返回 None)
- test_get_group_bounds_empty (空组返回 None)
- test_get_group_bounds_valid (有效组返回 bounds)

#### TestSquadGroupManagerPerformance (性能基线)
- test_create_1000_units_performance (1000 单元编组 < 100ms)
- test_select_1000_units_performance (1000 单元选择 < 50ms)

**预计新增测试数**: ~35-40 个

---

## 5. INTEGRATE 设计文档（为 v0.8.0+ 提供接入蓝图）

### 5.1 psychology_system 接入蓝图

**当前状态**: 纯静态类，无实例状态，无副作用，可直接调用

**接入点**:
1. `src/pycc2/domain/ai/tactical_ai.py` — AI 决策时调用 `PsychologySystem.evaluate_order(unit, tactic_type)` 评估是否执行
2. `src/pycc2/services/ai_service.py` — AI service tick 时集成 psychology 评估
3. 可选: `src/pycc2/domain/systems/morale_system.py` — `can_accept_orders()` 内部调用 psychology 做精细化评估

**依赖**: 全部已存在（TacticType / FatigueLevel / MoraleState / SuppressionEffect / Unit）

**风险**: LOW
- 纯静态类，无状态，无副作用
- 现有 93 处测试调用验证了业务逻辑正确性
- additive 设计，不破坏现有 MoraleSystem.can_accept_orders()

**v0.8.0 INTEGRATE 工作量预估**: <2h

### 5.2 squad_group_manager 接入蓝图

**当前状态**: 实例类，需要 game_loop 持有 + input handler 驱动 + minimap 渲染

**接入点**:
1. `src/pycc2/services/game_loop.py` — 新增 `_squad_group_manager: SquadGroupManager | None` 属性（默认 None，v0.8.0 实例化）
2. `src/pycc2/services/game_loop_assembler.py` — 装配时实例化 SquadGroupManager
3. `src/pycc2/presentation/input/` — Ctrl+1~9 创建组 / 1~9 选择组 / Ctrl+Shift+1~9 添加到组
4. `src/pycc2/presentation/rendering/minimap*.py` — 调用 `get_group_bounds()` 绘制彩色矩形
5. `src/pycc2/presentation/ui/bottom_panel*.py` — 显示当前选中组的单元数量

**依赖**: Unit (TYPE_CHECKING only，无循环依赖风险)

**风险**: MEDIUM
- 涉及输入处理（Ctrl+数字键监听）
- 涉及 UI 渲染（minimap 矩形绘制）
- 涉及游戏循环多处修改（game_loop + assembler + input + rendering）
- 但模块本身逻辑简单（纯数据管理），测试覆盖后风险可控

**v0.8.0 INTEGRATE 工作量预估**: 2-5h

### 5.3 v0.8.0+ INTEGRATE 顺序建议

| 顺序 | 模块 | 原因 |
|------|------|------|
| 1 | psychology_system | 最低风险（纯静态），快速胜利，<2h |
| 2 | squad_group_manager | 中等风险，用户感知强（Ctrl+编组），2-5h |
| 3 | cover_seek_ai + path_preview + range_indicator | v0.8.1 |
| 4 | day_night_cycle (接口已修复) + variant generators | v0.8.2 |

---

## 6. 执行清单 (4 Waves)

### Wave 1: squad_group_manager 测试增强 (Tester/Coder) — 核心工作

**风险等级**: 极低（只新增测试文件，不修改源码）

- [ ] 创建 `tests/unit/test_squad_group_manager.py`
- [ ] 实现 TestSquadGroup (7 tests)
- [ ] 实现 TestSquadGroupManagerCreate (6 tests)
- [ ] 实现 TestSquadGroupManagerSelect (3 tests)
- [ ] 实现 TestSquadGroupManagerClear (4 tests)
- [ ] 实现 TestSquadGroupManagerUnitOps (5 tests)
- [ ] 实现 TestSquadGroupManagerProperties (8 tests)
- [ ] 实现 TestSquadGroupManagerPerformance (2 tests)
- [ ] 验证新增测试全部通过

### Wave 2: 版本号更新 + 文档同步 (DevOps/Coder)

- [ ] `VERSION` 0.7.3 → 0.7.4
- [ ] `src/pycc2/__init__.py` `__version__` 0.7.3 → 0.7.4
- [ ] `pyproject.toml` version 0.7.3 → 0.7.4
- [ ] `SKILL.md` L3 版本号 + L12 测试数更新
- [ ] `docs/PRD.md` 版本号同步
- [ ] `docs/TEST_PLAN.md` L1 版本号
- [ ] `docs/TECH_DEBT.md` 版本号 + 描述
- [ ] `docs/PROJECT_STATUS.md` 版本号 + 测试数
- [ ] `README.md` / `README_zh.md` / `README_ja.md` L3 + 描述
- [ ] `docs/DESIGN.md` 版本号 + 架构演进链
- [ ] `docs/ROADMAP.md` 添加 v0.7.4 条目 + Document Version
- [ ] `check_doc_consistency.sh` 11/11 PASS

### Wave 3: 验证 (Tester/DevOps)

- [ ] 全量测试 `pytest tests/ -m "not slow"` — 期望 6156+35 ≈ 6191+ passed
- [ ] `ruff check .` — 期望 0 errors
- [ ] `MYPYPATH=src mypy -p pycc2` — 期望 ≤7 errors (不增加)
- [ ] `bash scripts/check_doc_consistency.sh` — 期望 11/11 PASS
- [ ] `test_squad_group_manager.py` 全部通过

### Wave 4: CHANGELOG + Git 推送 (DevOps)

- [ ] `CHANGELOG.md` 插入 v0.7.4 完整条目
- [ ] `ROADMAP_v0.7.4.md` 状态更新为 ✅ 完成
- [ ] Git commit + push origin/main
- [ ] CarryMem `classify_and_remember` 记录会话总结

---

## 7. 验证清单

| 验证项 | 期望 | 实际 |
|--------|------|------|
| 全量测试 | 6191+ passed (6156 + ~35 新增) | ⬜ 待验证 |
| ruff | 0 errors | ⬜ 待验证 |
| mypy | ≤7 errors (不增加) | ⬜ 待验证 |
| check_doc_consistency | 11/11 PASS | ⬜ 待验证 |
| test_squad_group_manager.py | ~35 tests passed | ⬜ 待验证 |
| Git push | origin/main 更新 | ⬜ 待验证 |

---

## 8. 风险提示

1. **测试数增加可能影响 CI 时长**: ~35 个新测试预计增加 <2s，可忽略
2. **squad_group_manager 测试需要 Unit mock**: 模块依赖 Unit (TYPE_CHECKING only)，测试需创建轻量 mock 或使用真实 Unit
3. **设计文档与实际 v0.8.0 INTEGRATE 可能有偏差**: 接入蓝图基于当前代码分析，v0.8.0 实际接入时需重新校准

---

## 9. 推进时间表

| 版本 | 内容 | 优先级 | 类型 | 状态 |
|------|------|--------|------|------|
| ~~v0.7.3~~ | day_night_cycle 接口兼容性修复 | P2 | PATCH | ✅ 完成 (2026-07-17) |
| **v0.7.4 (本次)** | INTEGRATE 前置准备: psychology_system + squad_group_manager 测试增强 + 设计文档 | P2 | PATCH | 🚧 执行中 |
| **v0.8.0** | INTEGRATE psychology_system + squad_group_manager (接入游戏循环) | P1 | 新功能 (MINOR) | ⬜ 计划 |
| **v0.8.1** | INTEGRATE cover_seek_ai + path_preview + range_indicator | P1 | 新功能 (MINOR) | ⬜ 计划 |
| **v0.8.2** | INTEGRATE day_night_cycle (接口已修复) + variant generators | P2 | 新功能 (MINOR) | ⬜ 计划 |

---

## 10. 教训预期

1. **ORPHAN 模块 INTEGRATE 前应先补测试**: squad_group_manager 只有 5 个 smoke tests 不足以为 v0.8.0 INTEGRATE 保障。v0.7.4 前置准备补齐测试，v0.8.0 只需关注 game_loop 集成
2. **PATCH 可以做有价值的前置准备**: 不修改源码的测试增强 + 设计文档属于 PATCH 范围，既符合 SemVer 又为 MINOR 扫清障碍
3. **INTEGRATE 设计文档应作为 INTEGRATE 前置条件**: 类似 v0.7.3 的接口合规性检查，v0.7.4 的接入蓝图设计文档是 v0.8.0 INTEGRATE 的前置条件
