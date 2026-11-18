# MC2-03/04 技术设计（Wave 2）

- 日期：2026-11-18
- 目标：驾驶员技能成长（MC2-03）+ 接触记忆衰减（MC2-04），**CC2 核心机制行为保持**
- 上游：[MC2_RESEARCH_20261118.md](MC2_RESEARCH_20261118.md) §3 / [MC2_WAVE1_DESIGN_20261118.md](MC2_WAVE1_DESIGN_20261118.md)（Wave 1 已交付，7608 passed）

## 1. 现状锚点

### MC2-03 经验现状
- `Veterancy` 值对象已存在（挂 `unit.veterancy`），仅 `record_kill()` 一个计数源（combat_director.py:824-827）
- `record_stats`（combat_director.py:803-828）已有 shot/hit/damage/kill 全量事件流——use/success 双计数的天然挂点
- MC2 参照（warrior.h）：`numSkillUses[skill][stats]` + `numSkillSuccesses[skill][stats]` 双计数，rank 由成功/使用比推导

### MC2-04 接触现状
- `FogOfWarService`（services/fog_of_war_service.py:23）三态网格（HIDDEN/EXPLORED/VISIBLE），每帧由 `_update_fog_of_war`（game_loop_updating.py:302）驱动，5-tick 间隔
- 离开视野即回落 EXPLORED（地形记忆），**单位无残影**——CC2 玩家体验缺"最后目击位置"

## 2. MC2-03 设计：技能成长

### 扩展 `Veterancy`（不改名不删字段，只增）
```python
@dataclass
class VeteranSkillStats:      # 单技能双计数
    uses: int = 0
    successes: int = 0

class Veterancy:
    skill_stats: dict[str, VeteranSkillStats]   # "gunnery" 起步，结构可扩展
    rank: float          # 0.0–5.0，由成功比 + 击杀推导
    def record_shot(self, hit: bool) -> None    # uses+=1; hit 则 successes+=1
    def record_kill(self) -> None               # 保留原语义
    @property
    def hit_rate(self) -> float                  # successes/max(uses,1)
```
- rank 漂移规则（CC2 精神：成长缓慢、有上限）：`rank = min(5.0, kills * 0.25 + hit_rate * 2.0)`，纯派生属性，不引入新的可变状态

### 消费点（行为保持的边界）
1. `record_stats` 在 `record_shot` 分支同时调 `attacker.veterancy.record_shot(damage > 0)`（attacker 有 veterancy 才记；与 record_kill 同守卫风格）
2. 命中率影响精度：**本波不改 ballistics 精度公式**（避免 AI/平衡回归）——rank 仅做派生统计 + 存档持久化，消费留给后续 wave（登记）
3. 存档：检查现有 save/load 对 unit 字段的序列化方式，veterancy 新字段跟随序列化；读回一致用例必须过

## 3. MC2-04 设计：接触记忆残影

### 新增 `services/contact_memory.py`
```python
@dataclass
class UnitContact:
    unit_id: str
    faction: str
    last_seen_tile: tuple[int, int]
    last_seen_tick: int

class ContactMemory:
    """按观察方阵营维护"最后目击"表（MC2 Contact.cpp 精神）。
    VISIBLE→ 不记录（单位本身可见）；单位从可见区消失 → 记录残影；
    残影超过 CONTACT_DECAY_TICKS（默认 600 tick ≈ 10 秒逻辑时间）→ 过期清除。
    """
    def observe(units, visible_grid, tick) -> None
    def ghosts(faction: str) -> list[UnitContact]     # 查询某阵营的当前残影
```
- 挂点：`FogOfWarService.update` 之后由 `_update_fog_of_war` 调 `contact_memory.observe(...)`（同 5-tick 节奏，异常不破主循环——与 fog 同一 try 包裹策略）
- 渲染：ghost 在渲染层以半透明阵营色轮廓绘制（alpha 90），过期不画。渲染侧只读 `ghosts(faction)`，不反向写
- 重置：任务开始/读档时 `contact_memory.clear()`

### 明确不做
- 不改 fog 三态语义；不改 LOS 判定；不做声音接触（MC2 有，留后续）

## 4. 测试计划

| 层 | 用例 |
|----|------|
| unit | Veterancy.record_shot 双计数/hit_rate 边界；rank 单调性（100 hit → rank 只升不降）；rank 上限 5.0；ContactMemory 记录/过期/清除/阵营隔离 |
| integration | record_stats 全链路（开火未中 uses+1，命中 uses+successes+1）；存档读回 veterancy 一致；fog 更新后残影生成与衰减（tick 推进 600+ 后 ghosts 空）；ghost 渲染不崩（dummy 驱动） |
| 回归 | 全量 0 failed；ruff/mypy 全绿 |

## 5. 验收门禁（Wave 2 关闭条件）
1. 全量回归 0 failed + ruff check/format + mypy（CI 同口径）全绿
2. 远端 CI 全部 job 绿灯（RELEASE_GATE_W5 强制前置）
3. 设计文档回写实现记录（含偏离决策）

## 6. 实现记录（2026-11-18，Coder 交付后回写）

### 交付数字
- 全量回归：**7672 passed / 4 skipped / 0 failed**（Wave 1 基线 7608 + 新增 64 用例）
- ruff/format/mypy（406 文件）全绿；64 新用例主会话独立复验通过

### 关键实现落点
- Veterancy 扩展：`veterancy_component.py`（VeteranSkillStats 双计数 + record_shot + hit_rate/skill_rank 派生 + to_dict/from_dict）
- 挂点：`combat_director.record_stats:820-823`（与 record_kill 同守卫风格）
- ContactMemory：`services/contact_memory.py`（新增，衰减 600 tick）；挂 `_update_fog_of_war`（独立 try 保护）；ghost 渲染在 **fog 暗化层之后**（enhanced_renderer.py:460-468，残影必须画在雾上）；start_deployment/quick_load 清表
- 存档：战役持久化走整体序列化（campaign_state to_dict/from_dict），skill_stats 自动持久化

### 偏离设计决策（4 项）
1. 派生 float 命名 `skill_rank` 而非 `rank`——现有 `rank` 是 VeteranRank 枚举属性（unit_movement_mixin/campaign_state/melee_combat 在消费），改名会破坏 CC2 行为
2. `observe` 增加 `observer_faction` 参数（原签名无法表达阵营隔离）
3. `ghosts` 增加可选 `tick` 参数（测试边介用）
4. 死亡单位立即清除接触（避免渲染已死单位残影）

### 范围外发现（登记）
- 快速存/读档（save_controller/save_system 字段白名单）从不序列化 veterancy——既有行为，本波未改；如需快速存档携带成长，后续 wave 在白名单加整体 veterancy 块
