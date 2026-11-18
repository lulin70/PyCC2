# MC2-05/06 技术设计（Wave 3）

- 日期：2026-11-18
- 目标：让路协商状态机（MC2-05）+ 战役整备闭环接线（MC2-06），CC2 核心机制行为保持
- 上游：[MC2_RESEARCH_20261118.md](MC2_RESEARCH_20261118.md) §3；Wave 1（CI 绿）/ Wave 2（进行中）

## 1. 现状锚点

### MC2-05 移动现状
- 移动执行：`combat_director.py::_update_move_orders`（:927-979）逐格推进，**无占位检查**——单位可自由穿过/重叠
- 占位现状：无全局占位表；`occupied` 集合在增援生成（reinforcement_service.py:136-171）与初始放置（game_loop.py:560-575）临时构建
- MC2 参照（warrior.h）：`yieldState`（刚让路/让路已久）+ `moveStateGoal` 协商

### MC2-06 战役现状
- 数据层完整但**零生产消费点**：`CampaignPersistenceManager`（domain/systems/campaign_persistence.py:151）+ `CampaignProgress`（:72，含 requisition_points/sectors_controlled）+ `UnitBattleState`（:27，hp/morale/experience/ammo/kills/status）+ `add_battle_result`（:95，内部已同步 current_unit_states）
- grep 证实：`add_battle_result`/`get_alive_units`/campaign 的 requisition_points 在 src 无调用者（deployment_factory 的 RP 是部署期独立参数，与战役 RP 不连通）
- 装配点已留：`game_loop.py:128 _campaign_persistence` + assembler :272-280（TD-076d 线缆已铺）

## 2. MC2-05 设计：让路协商（防死锁优先）

### 语义（CC2 精神：友军可穿越，硬阻塞只防死锁）
1. 每帧构建占位快照：`occupied_moving`（正在 _move_orders 中的单位 tile）/ `occupied_static`（其余存活单位 tile）
2. 让路判定（仅对"即将进入新 tile"的瞬间，即 dist <= move_pixels 分支）：
   - 目标 tile 在 `occupied_static` → **yield**：不推进 tile，`yield_ticks += 1`，继续面向目标
   - 互换对冲：两个移动单位互以对方当前 tile 为下一格 → 双方 yield
   - `yield_ticks > YIELD_TIMEOUT_TICKS`（默认 90 = 3 秒）→ **强制通行**（防死锁逃生阀，对应 MC2 "yielded for a while"）
3. 进入新 tile 时 `yield_ticks` 清零
4. 移动单位穿过彼此（双方都在动且非互换）不阻塞——保持现状行为，e2e 不破

### 明确不做
- 不做绕路重算（sidestep 需 path 重规划，登记后续）
- 不改 PathFinder；不改速度；不加硬碰撞

## 3. MC2-06 设计：战役整备闭环接线

### 三段接线（数据层已有，缺的是生产调用）
1. **战斗结束 → 持久化**：victory 分支（game_loop_updating.py::_update_victory 胜利发布 BattleWon 后）从 state.units 构建 `UnitBattleState` 列表 + `BattleResult`（outcome 映射 BattleOutcome，伤亡/VP 从 VictoryManager/BattleStats 取），调 `add_battle_result` 并 `save_campaign_progress`。campaign_persistence 为 None（遭遇战）时整段跳过——遭遇战行为不变。
2. **任务开始 → 状态回放**：部署装配单位后（deployment_manager 完成点），按 template_id+faction 匹配 `get_alive_units`，回放 current_hp/morale/experience/kills/ammo；阵亡单位不在部署名册。匹配不到（新任务编制变化）按现状——不阻塞。
3. **整备服务**：新建 `services/refit_service.py`：
   - `repair_cost(unit)` / `repair(unit, rp)`：花 RP 回 hp（1 RP = 1 hp 上限）
   - `reinforce_cost()` / `reinforce(unit, rp)`：补员（回复 squad manpower/morale）
   - `available_rp(faction)` 读写 CampaignProgress.requisition_points_*
   - RP 与部署期 base_rp 的连通：部署取 base_rp 时优先 campaign RP（有 campaign 才生效）
4. UI：本轮只做 service + 集成测试，战役整备屏（真实 UI）登记后续（避免本波范围膨胀）

### 明确不做
- 不动 skirmish 路径（campaign_persistence=None 时全旁路）
- 不做 sector 推进/战役地图逻辑（sectors_controlled 字段已有，消费登记后续）

## 4. 测试计划

| 层 | 用例 |
|----|------|
| unit | 占位快照构建；yield 触发/清零/超时强制通行；refit_service 修复/补员/RP 扣减边界 |
| integration | 对冲场景：两单位互换目标格 → yield → 超时后双双到达（不死锁、不永久卡）；静止单位挡路 → 跟随者 yield；战役胜利 → save → 重读 → 下一任务部署回放 hp/morale/阵亡剔除；遭遇战路径零变化 |
| 回归 | 全量 0 failed；现有移动类 e2e/uat 测试必须全过（让路不破穿越语义） |

## 5. 验收门禁
同 Wave 2：全量 0 failed + lint/mypy 绿 + 远端 CI 全绿 + 设计回写。
