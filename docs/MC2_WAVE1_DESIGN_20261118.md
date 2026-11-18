# MC2-01/02 技术设计（Wave 1）

- 日期：2026-11-18
- 目标：战术指令层统一 + 触发器统一，**行为保持**（CC2 核心机制零变化）
- 来源研究：[MC2_RESEARCH_20261118.md](MC2_RESEARCH_20261118.md)
- 验收底线：全量回归 0 failed + ruff/mypy/radon 全绿 + 远端 CI 全绿

## 1. 现状（探查结论，均有 file:line 锚）

### 指令链路（两条，未统一）
- 玩家：`EventDispatcher._handle_battle_input`（event_dispatcher.py:317）→ `input_router.route_input` → 发布 `PlayerCommand` 事件 → `CombatDirector._on_player_command_event`（combat_director.py:129）→ `handle_player_command` → `_CMD_DISPATCH` 字典（:33，11 种命令）→ `_cmd_*` 方法（统一签名 `data/unit_map/units/game_map`）
- AI：`game_loop_updating._update_ai`（:504）→ `ai_service.tick` 产出 intents → `ai_service.execute_intents`（:518）直接执行——**绕过 CombatDirector**
- AI 内部已有 `CommanderOrder` 数据对象（commander_ai.py:35，含 order_type/priority/expires）
- `PlayerCommand` 是 TypedDict（event_types.py:6：command/unit_ids/target_id/target/timestamp），无 origin

### 触发点现状（game_loop_updating.py）
- 每帧顺序 `_update_logic`（:105）：reinforcements → combat → ai → victory
- 增援：`ReinforcementService.update`（服务化良好，保留）
- 补给/走廊：`_update_logistics`（:206-264）内联 corridor_must_remain_open 检查 + supply_dwindling 衰减
- 规则效果：`_update_scenario_effects`（:266-300）内联 fanatic_defenders（士气钳制）+ combined_arms_bonus（每 30 tick 邻近加成）
- 胜利：`_update_victory`（:529）→ VictoryManager（已抽象，保留）

### special_rules 消费点分布（ScenarioRules.has，15 处）
- game_loop_updating.py：5 处（本轮迁入触发器）
- game_loop.py：7 处（air_support/vls/night/amphibious/bridge/fortified/scatter —— 配置性规则，启动时一次性应用，**不是触发器，保留**）
- deployment_ui.py / deployment_manager.py：3 处（部署期一次性，**保留**）

## 2. MC2-01 设计：TacticalOrder 统一指令层

### 新增 `src/pycc2/domain/value_objects/tactical_order.py`
```python
class OrderOrigin(Enum):
    PLAYER = "player"; COMMANDER = "commander"; SELF = "self"

@dataclass(frozen=True)
class TacticalOrder:
    command: str                    # 与 _CMD_DISPATCH 键一致
    unit_ids: tuple[str, ...]
    origin: OrderOrigin
    params: Mapping[str, Any]       # target_id / target / 火力模式等
    timestamp: float = 0.0
    issued_tick: int = 0            # 回放/录像依据
```

### 改动点（全部行为保持）
1. `PlayerCommand` TypedDict 加 `origin: NotRequired[str]`（缺省 "player"，旧发布点零改动）。
2. `CombatDirector`：
   - 新增统一入口 `issue_order(order: TacticalOrder, ...) -> bool`：构造 data 视图 → 走既有 `_CMD_DISPATCH` → `_cmd_*`。原 `_cmd_*` 方法体**一行不动**。
   - `handle_player_command` 改为从事件构造 TacticalOrder（origin=PLAYER）后调 `issue_order`。行为等价。
3. `ai_service.execute_intents`：move/attack 类 intent 改为构造 `TacticalOrder(origin=COMMANDER)` 调 `CombatDirector.issue_order`（通过注入的 director 引用；若语义无法 1:1 映射的 intent 保留原路径并登记后续项）。
4. 指令记录：CombatDirector 维护环形 `_order_log`（deque maxlen=1000）供回放/调试。

### 明确不做
- 不改 `_cmd_*` 内部逻辑；不改 UI 发布点签名；不引入网络序列化（M6 再做）。

## 3. MC2-02 设计：TriggerSystem 触发器统一

### 新增 `src/pycc2/services/trigger_system.py`
```python
@dataclass
class Trigger:
    trigger_id: str
    condition: Callable[[BattleState], bool]
    action: Callable[[BattleState], None]
    once: bool = False
    cooldown_ticks: int = 0        # 0=每满足即触发

class TriggerSystem:
    def register(t: Trigger) -> None: ...
    def tick(state) -> list[str]: ...   # 返回本帧触发的 trigger_id（可观测）
```
- 注册表可观测：`list_triggers()` 返回 (id, 已触发次数, 上次触发 tick)。

### 迁移范围（game_loop_updating.py 内联块 → 注册式触发器）
| 触发器 | 条件 | 动作 | 原代码锚 |
|--------|------|------|---------|
| corridor_supply_block | corridor VL 被轴心占领 | 阻断本帧补给 | :215-222 |
| supply_dwindling_decay | supply_dwindling 规则开启 | 补给量 ×0.85 衰减 | :249-250, :263-264 |
| fanatic_defenders_floor | fanatic_defenders 开启 | AXIS 士气 <30 钳到 30 | :273-276 |
| combined_arms_bonus | 每 30 tick | 4 格内有己方装甲 → 命中 ×1.10 | :278-300 |
| reinforcement_due（委托） | ReinforcementService.due | 委托 service.update | :166-189 |

- `_update_logistics` / `_update_scenario_effects` 保留为薄委托（测试可能直接引用），体内逻辑移入触发器。
- 增援/胜利服务本体不动，只加委托触发器使触发表成为单一帧序权威。

### 明确不做
- game_loop.py 的 7 处启动期配置规则、部署期 3 处规则不迁移（不是触发器语义）。
- 不做场景 JSON 自定义触发器 DSL（后续 wave）。

## 4. 测试计划

| 层 | 用例 |
|----|------|
| unit | TacticalOrder 构造/origin 缺省；TriggerSystem once/cooldown/条件不满足不触发 |
| integration | 玩家 PlayerCommand → issue_order 等价性（旧路径与新路径同结果）；AI intent 经 issue_order 执行；触发器迁移后 fanatic/combined_arms/supply 行为与原实现一致（对照断言） |
| 回放 | 同一指令序列重放两次，_order_log 与战斗结果一致 |
| 回归 | 全量 pytest（--ignore=tests/benchmark）0 failed；ruff/mypy/radon/文档一致性全绿 |

## 5. 角色分工（DevSquad）
- Architect：本设计（已完成）
- Coder：§2/§3 实现（general-purpose agent 执行，约束：不动 _cmd_* 方法体、全量回归绿）
- Tester：§4 测试计划执行
- DevOps：推送 + 远端 CI 强制前置确认

## 6. 实现记录（2026-11-18，Coder 交付后回写）

### 交付数字
- 全量回归：**7608 passed / 4 skipped / 0 failed**（基线 7556 + 新增 52 用例）
- ruff check / format、mypy（CI 同口径，405 文件）全绿；新增测试 52 passed 独立复验通过
- `_cmd_*` 方法体零改动（行为保持硬约束达成）

### 实际改动
- 新增：`domain/value_objects/tactical_order.py`、`services/trigger_system.py`、unit×2 + integration×2 测试文件
- 修改：`event_types.py`（origin 字段）、`combat_director.py`（issue_order + _order_log，:139-193）、`ai_service.py`（ATTACK intent 走 issue_order(origin=COMMANDER)，:420-489）、`game_loop_updating.py`（三方法薄委托 + build_scenario_triggers 6 触发器）、`game_loop.py`/`game_loop_assembler.py`（装配）

### 偏离设计决策（7 项，均有行为保持依据）
1. `TacticalOrder.origin` 缺省 `PLAYER`（向后兼容）
2. logistics 组 3 触发器（设计表 2 个）：新增 `supply_resupply_pass` 承载补给主循环——corridor 阻断/衰减与主循环有早退耦合，按注册顺序执行才能精确复现原控制流（对照测试验证含"阻断时跳过衰减"）
3. `combined_arms_bonus` 用条件内递增计数器复现 30-tick 节奏（保持 `_combined_arms_counter` 原始语义），TriggerSystem 的 once/cooldown 能力由 unit 测试覆盖
4. `reinforcement_due` 对 duck-typed 服务回退每 tick 委托（兼容现有测试桩）
5. `TriggerSystem` 增加 `group` 字段与 `tick(state, group=None)`——三个薄委托需独立 tick 子集互不推进节奏；基础 API 不变
6. `_ensure_trigger_system` 为模块级函数（stub 测试环境懒构建）
7. AI intent 映射结果：仅 ATTACK 1:1 迁移（走士气门预检，ROUTING/BROKEN 拒单行为一致）；MOVE_TO 系列保留原路径——executor 一步移动与 director pathfinder 连续移动轨迹不同，强行映射会改变 AI 行为，违反行为保持约束。登记后续项。

### 后续项（登记）
- AI MOVE_TO/RETREAT 等 intent 的指令层迁移：需先统一 AI 移动机制（pathfinder 化），另行设计
- 场景 JSON 自定义触发器 DSL（原计划后续 wave）
- 回放系统消费 `_order_log`（TacticalOrder.issued_tick 已锚定时间线）

