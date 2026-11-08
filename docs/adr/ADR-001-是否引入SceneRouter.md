# ADR-001：是否在 Phase 1 引入 SceneRouter

- 状态：已接受（Accepted）
- 日期：2026-11-07
- 决策者：architect、solo-coder、product-manager
- 关联：《PyCC2项目完整交付方案》v1.3 §2.5；《7 角色评审报告》ARCH-02

## 1. 背景

v1.1 方案假设当前为“单一 GameLoop 硬编码流程”，因此把“迁移到 Scene 架构”列为 P0。v1.2 以代码核对后降级为可选重构，并给出 3 条触发条件。本 ADR 用 Day 1 审计的实测数据判定是否触发。

## 2. 决策依据（实测）

### 2.1 触发条件核对

| 触发条件 | 判定标准 | 实测结果 | 结论 |
|---------|---------|---------|------|
| T1 | 存在单个函数超过 200 行 | `main.py` 最长函数 `_start_new_game` 144 行（L215-358）；`_create_game_objects` 85 行；`main()` 73 行；`game_loop.py::run` 138 行 | 未触发 |
| T2 | 新增暂停菜单/结算界面需复制大量代码 | `GameLoop` 已按渲染/更新/装配拆分为 `game_loop_rendering.py`、`game_loop_updating.py`、`game_loop_assembler.py`；菜单与战斗通过 `NewGameMenu` 返回值（字符串动作）解耦 | 未触发 |
| T3 | 单元测试无法在不启动 Pygame 的情况下测试菜单流程 | `tests/unit/test_main_entry.py` 已用 mock 覆盖 `_create_game_objects`；`NewGameMenu` 的点击逻辑在 `tests/unit/` 有覆盖（当前因 P0-01 失败，非架构原因） | 未触发 |

### 2.2 结构现状

```
main.py (454 行)
├─ _show_main_menu()        → NewGameMenu（730 行，动作返回字符串）
├─ _create_game_objects()   → 统一装配（消除两条路径的重复）
├─ _load_saved_game()       → SecureSaveManager + SaveController
└─ _start_new_game()        → 地图/设置 → GameLoop.start_deployment()
```

`GameLoop` 是 Facade，依赖通过 Protocol 注入（HUD、设置、教程、存档）。当前流程是“单次线性跳转”，没有多场景并存的需求。

## 3. 决策

**Phase 1 不引入 SceneRouter。**

理由：
1. 3 条触发条件均未满足，重构缺乏实证收益。
2. 当前 P0 缺陷集中在渲染层 API 漂移（见 AUDIT_REPORT P0-02），重构会扩大故障面。
3. 引入 SceneRouter 需要改造 `main.py`、`GameLoop`、`NewGameMenu` 三处入口，回归成本高，且会推迟可玩性修复。

## 4. 后果

- 正面：Phase 1 只做缺陷修复，风险与工期可控。
- 负面：暂停菜单/结算界面若后续要做，仍需在 `GameLoop` 内增加状态分支。
- 约束：新增场景必须复用 `_create_game_objects` 的装配方式，禁止再复制初始化代码。

## 5. 复审点

出现下列任一情况时重开本 ADR：

1. 任一入口函数超过 200 行，或 `main.py` 超过 600 行。
2. 需要同时维护 2 个以上并行场景（如战斗 + 战役地图 + 结算同时存在）。
3. 新增场景需要在 3 处以上复制对象装配代码。

## 6. 证据来源

- `src/pycc2/main.py`（454 行，函数长度用 AST 实测）
- `src/pycc2/services/game_loop.py`（453 行，Facade）
- `src/pycc2/services/game_loop_assembler.py`（HUD/Minimap 装配）
- `src/pycc2/presentation/ui/new_game_menu.py`（730 行，动作返回字符串）
- `docs/AUDIT_REPORT.md`（Day 1 审计）
