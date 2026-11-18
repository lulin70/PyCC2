# MC2 Wave 4 技术设计：AI 移动统一（MOVE_TO pathfinder 化）

- 日期：2026-11-18
- 目标：AI MOVE_TO 系 intent 改走 `CombatDirector.issue_order`（origin=COMMANDER），AI 与玩家共用 pathfinder 连续移动
- 上游：[MC2_WAVE1_DESIGN_20261118.md](MC2_WAVE1_DESIGN_20261118.md) §6 后续项；Wave 1/2/3 均已交付

## 1. 现状锚点
- Wave 1 已迁：AI ATTACK intent → issue_order（含士气门预检）；MOVE_TO/RETREAT/REGROUP/PATROL/FLANKING 等保留原路径
- 原路径：`ai_service` TacticExecutor `unit.move_to_tile` 一步瞬移（与玩家 pathfinder + `_move_orders` 连续移动轨迹不同）
- Wave 3 新增：process_movements 占位快照 + yield——AI 走连续移动后自动获得让路协商（本次统一的主要收益）

## 2. 设计
1. `MOVE_TO` intent → 构造 `TacticalOrder(command="move", origin=COMMANDER, params={"target": tile})` → `issue_order`；路径由 `_cmd_move` 的 PathFinder 生成，移动由 process_movements 连续推进
2. RETREAT/REGROUP/PATROL/FLANKING：凡"到达某 tile"语义的 intent 全部映射为 move（保留各自决策逻辑，只换执行腿）；FLANKING 若含朝向语义则拆为 move + 现有朝向逻辑
3. 回退保底：无 director 引用 / 单位不在 unit_map / pathfinder 不可达（find_path 失败）→ 回退原 executor 一步移动（可用性优先于纯度，与 Wave 1 ATTACK 回退策略一致）
4. TacticExecutor 的移动一步执行路径保留为回退分支，不删除

## 3. 行为影响评估（预期且接受的变化）
- AI 移动从瞬移变连续——这是本波目的（机制统一），**非行为保持重构**；但战斗结果影响面限于 AI 到达时间/轨迹，武器/士气/胜利机制零改动
- 现有 AI 测试若断言"一步到位"需更新为连续推进断言——属测试随实现语义升级，逐条列出报告

## 4. 测试计划
- unit：MOVE_TO→TacticalOrder 映射；pathfinder 不可达回退；无 director 回退
- integration：AI 移动经 issue_order（_order_log 含 origin=COMMANDER）；AI 对冲场景获得 yield（复用 Wave 3 对冲测试模式）；AI 到达后可攻击（链路）
- 回归：全量 0 failed；AI 相关 e2e 全过

## 5. 验收
同前波：全量 0 failed + lint/mypy 绿 + 远端 CI 全绿 + 本文档回写实现记录。完成后 PyCC2 优化计划（MC2-01…06）全部收官，TD-081 按用户指示暂缓。

## 6. 实现记录（2026-11-18，Coder 交付后回写）

### 交付数字
- 全量回归：**7761 passed / 4 skipped / 0 failed**（--ignore=tests/benchmark；新增 41 用例）
- ruff check / format（全仓 756 文件）、mypy（MYPYPATH=src -p pycc2，407 文件）全绿
- 已知随机顺序 flaky（test_phase3_los_blocked_by_terrain）两轮全量均一次通过

### 实际改动
- 修改：`services/ai_service.py`（`_COMMANDER_MOVE_INTENTS` 常量 :61-69；`_execute_single_intent` 分派 :469-481；`_issue_commander_move` :483-546；`_resolve_move_target` :548-561；`execute_intents` 文档更新）
- 修改：`infrastructure/save_system.py`（SavePositionData.pixel_offset `dict[str, int]` → `dict[str, float]`，:76-87——见偏离决策 1）
- 新增：`tests/unit/test_ai_service_move_routing.py`（34 用例：映射/回退/士气门/混合语义不迁移）、`tests/integration/test_ai_pathfinder_movement.py`（7 用例：issue_order 日志、连续推进、对冲 yield、静态阻挡 yield、到达后攻击链路）

### intent 迁移清单
- **迁移（7 项）**：MOVE_TO、PATROL、RETREAT（无目标时保留 (x-3, y-3) safe_pos 决策逻辑）、REGROUP、FLANKING（combat_mixin._execute_flanking 为纯 move 委托，无朝向语义，无需拆分）、COORDINATED_ADVANCE、CAPTURE_VL（logistics_mixin 文档串明示纯 move 委托）
- **保留 executor 路径（含内嵌移动腿）**：TAKE_COVER（有"原地掩护"分支）、DEFEND_VL（有"到位转 defend 模式"分支）、CLEAR_BUILDING / ASSAULT_FORTIFIED / SCAVENGE_AMMO / LAY_MINE / HEAL_WOUNDED / RALLY_NCO / MOUNT_TANK（移动腿与子系统状态机耦合，非纯"到达某 tile"语义）

### 回退链（照抄 Wave 1 ATTACK 模式，全部回退到原 executor 一步移动）
无 tick 战场上下文 / 无 director / 单位不在 unit_entities / 单位不在 all_units（unit_map）/ 无显式目的地（executor no-op 分支）/ director 无 pathfinder / find_path 不可达。可达性预检放在士气门之前，避免 BROKEN 30% 拒单被双重掷骰。

### AI 测试更新清单
- **无需更新**：全量排查后，无既有测试经 AIService+director 断言 AI 移动"一步到位"——`test_tactic_executor.py` 等断言一步移动的测试直接测 executor（本波保留为回退分支，行为不变）；AI-service 级测试（test_ai_service_integration / test_ai_gameloop_integration）未注入 director，走回退路径，行为不变

### 偏离设计决策（2 项）
1. `save_system.SavePositionData.pixel_offset` schema int → float：连续移动插值（combat_director.py:1022）一直写 float 偏移、两个存档写入端（save_system.py:434 / save_controller.py:127）也写 float，schema 声明 int 是存量矛盾；本波 AI 连续移动使 e2e"移动中存档"首次触发该缺陷（基线验证：stash 本波改动后 3 个存档 e2e 通过）。修正 schema 与生产事实一致，1 行，武器/士气/胜利机制零改动
2. CAPTURE_VL / COORDINATED_ADVANCE 计入迁移清单：设计 §2.2 点名 RETREAT/REGROUP/PATROL/FLANKING，但按"凡'到达某 tile'语义全部映射"的判定条件，经 TacticExecutor 全表核对后这两项同为纯 move 委托，纳入迁移；混合语义项保守留在 executor（§2.2 判定条件的另一侧）

### 收官状态
MC2-01…06 全部交付；Wave 1 §6 登记的"AI MOVE_TO 系 intent 指令层迁移"后续项随本波关闭。
