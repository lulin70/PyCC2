# PyCC2 技术设计文档 (DESIGN) **v0.3.39**

> **项目**: Close Combat 2 Python 重写 | **阶段**: M3 — Beta Candidate
> **输入**: P2 ADD v1.0 (架构设计) + P1 PRD v1.0 (需求规格) + M1/M2/M3 修复与新增方案
> **文档版本**: v0.3.39 | **日期**: 2026-06-13

---

## 第1部分：Domain 层核心数据结构 (~420行可执行代码)

### 1.1 Vec2 值对象
```python
@dataclass(frozen=True, slots=True)
class Vec2:
    """二维向量值对象。不可变，支持运算符重载。"""
    x: float
    y: float
    # 工厂方法: zero(), from_tile()
    # 运算符: + - * / truediv neg == __hash__
    # 属性: length_squared, length, normalized, perpendicular
    # 方法: distance_to, dot, cross, lerp, angle_to, to_tile_coord, clamp_length, rotate
    TILE_SIZE: float = 32.0  # 类常量
```
包含完整的运算符重载（__add__, __sub__, __mul__, __truediv__, __neg__, __eq__, __hash__）和所有方法实现。

### 1.2 TileCoord 值对象
```python
@dataclass(frozen=True, slots=True)
class TileCoord:
    """瓦片网格坐标值对象。不可变。"""
    x: int
    y: int
    # DIRECTIONS_8: 8方向邻居偏移 (N/NE/E/SE/S/SW/W/NW)
    # get_neighbors(), get_neighbors_within(width, height)
    # 运算符: + -
    # 距离: manhattan_distance, chebyshev_distance, octile_distance
    # is_adjacent(), in_bounds(w,h), to_vec2(center=True)
```

### 1.3 TerrainType 枚举 (12种地形)
```python
class TerrainType(Enum):
    OPEN             # 移动1.0   掩体0.0   LOS:否
    ROAD             # 移动0.8   掩体0.0   LOS:否
    GRASS            # 移动1.2   掩体0.05  LOS:否
    WOODS            # 移动2.0   掩体0.30  LOS:稀疏阻挡
    BUILDING_ENTERABLE # 移动1.5   掩体0.50  LOS:否
    BUILDING_SOLID   # 移动INF   掩体1.00  LOS:是
    WATER            # 移动INF   掩体0.0   LOS:是
    HEDGE            # 移动2.5   掩体0.20  LOS:部分
    WALL             # 移动INF   掩体1.00  LOS:是
    ROUGH            # 移动1.8   掩体0.08  LOS:否
    SHALLOW          # 移动3.0   掩体0.02  LOS:否
    BRIDGE           # 移动0.9   掩体0.0   LOS:否
```
每种地形有 movement_cost, blocks_movement, blocks_line_of_sight, cover_modifier, concealment_modifier 属性。

### 1.4 五个 Component
- HealthComponent(hp/max_hp/state: HEALTHY/WOUNDED/CRITICAL/DEAD) + take_damage/heal/is_alive/hp_ratio
- MoraleComponent(value: int/panic_threshold: int/rout_threshold: int/state: NORMAL/SUPPRESSED/PANICED/ROUTING) + apply_delta/add_suppression/decay_suppression/natural_recovery
  士气范围 0-100 (整数), 恐慌阈值<30, 溃逃阈值<10
- WeaponComponent(primary_weapon_id/ammo_remaining/max_ammo/reload_ticks_left/state: READY/RELOADING/JAMMED/OUT_OF_AMMO) + fire/start_reload/tick
- PositionComponent(tile_coord/vec2/facing_rad/pixel_offset) + pixel_position/set_facing_toward
- VisionComponent(range_tiles/angle_rad/last_update_tick/visible_tiles set) + needs_update/mark_updated

### 1.5 Unit 实体
- id/name/faction(Faction.ALLIES/AXIS)/unit_type(UnitType枚举)
- 5个组件引用: health/morale/weapon/position/vision
- squad_id / state_machine
- is_alive / can_act / move_to_tile 方法

### 1.6 Squad / 1.7 Projectile / 1.8 GameMap (含Bresenham LOS / from_json加载JSON)

### 1.9 StateMachine[T] 泛型状态机
```python
class StateMachine(Generic[S]):
    def __init__(self, initial: S, transitions: dict[S, set[S]]): ...
    @property def current(self) -> S: ...
    def can_transition_to(self, target: S) -> bool: ...
    def try_transition(self, target: S) -> bool: ...
    def force_transition(self, target: S) -> None: ...
    def transition_or_raise(self, target: S) -> None: ...  # raises TransitionError
    def reset(self, state: S | None = None) -> None: ...
    def on_enter(self, state: S, callback): ...
    def on_exit(self, state: S, callback): ...
    @property def history(self) -> list[tuple[S, S]]: ...
```

---

## 第2部分：6 个核心算法伪代码 (~380行)

### 2.1 BallisticEngine.resolve_shot() — 完整弹道结算
步骤: LOS检查(Bresenham) → 距离衰减精度(1-(dist/effective)*0.6) → 掩体修正命中概率 → rng.uniform判定命中 → 高斯散布计算(散射半径∝距离×tan(dispersion_deg)) → 伤害公式(base*penetration*distance_factor*variance±20%) → 压制值累积
输出 ShotResult(hit/damage/is_killing_blow/suppression_dealt/miss_position)

### 2.2 MoraleCalculator.apply_event() — 士气系统
事件权重表: ALLY_KILLED=-15, LEADER_KILLED=-25, UNDER_HEAVY_FIRE=-5/tick, NEAR_EXPLOSION=-20, KILL_CONFIRMED=+8, RALLY=+3, IN_COVER=+5, COMMANDER_NEARBY=+10, PANIC_CONTAGION=-10
自然恢复: 非 combat 30tick后 +0.5/tick
状态阈值: <30→PANICED, <10→ROUTING
传染: 同squad友军panic→每个非panic成员-10

### 2.3 PathFinder.find_path() — A* 寻路
Octile heuristic: max(dx,dy) + (√2-1)*min(dx,dy)
开放列表heapq, 关闭set
对角线代价√2, 地形代价从cost表查表
返回TileCoord路径或None

### 2.4 FogOfWar.update_visibility() — 视野更新
36射线/每10度一条, Bresenham步进, blocking terrain停止
每5帧更新一次(性能优化)
返回 newly_revealed tiles

### 2.5 BehaviorTree.tick() — BT 执行引擎
NodeStatus: SUCCESS/FAILURE/RUNNING
Sequence: 全部SUCCESS→SUCCESS, 任一FAILURE→FAILURE
Selector: 首个SUCCESS→SUCCESS, 全部FAILURE→FAILURE
Parallel: threshold个子节点成功→成功
Condition叶: predicate评估
Action叶: execute执行
Inverter/Repeater/Wait装饰器

### 2.6 GameLoop.run() — Fix Your Timestep
LOGIC_DT=1/30, TARGET_FPS=60, MAX_FRAME_TIME=0.25
accumulator模式: 收集frame_time → while accumulator>=LOGIC_DT: update_logic → alpha=accumulator/LOGIC_DT → render(alpha) → clock.tick(TARGET_FPS)

---

## 第3部分：性能预算表

30UPS = 33.33ms/logic frame:
- AI决策: 5ms (每3帧均摊)
- 战斗结算: 3ms
- 单位移动: 2ms
- FoW: 3ms (每5帧均摊)
- 输入: 0.5ms
- 事件分发: 0.5ms
- 其他: 1ms
- 总计: ~15ms (余量18ms, 利用率45%)

---

## 第4部分：P0 Vertical Slice Task Breakdown (23项, 53小时≈1.5周)

T0.1 项目搭建(2h) → T0.2 Value Objects(2h) → T0.3 Components+Unit(3h) → T0.4 StateMachine(1.5h) → T0.5 地图加载(2h) → T0.6 BallisticEngine TDD(4h) → T0.7 MoraleCalculator TDD(3h) → T0.8 CombatResolver(2h) → T0.9 RandomContext+EventBus(2h) → T0.10 Pygame窗口(2h) → T0.11 Camera+ProtoRenderer(3h) → T0.12 单位渲染(2h) → T0.13 InputHandler(3h) → T0.14 A* PathFinder(3h) → T0.15 单位移动(3h) → T0.16 FogOfWar(3h) → T0.17 HUD骨架(4h) → T0.18 AI BehaviorTree(4h) → T0.19 AIService+CombatService编排(3h) → T0.20 VictoryChecker(1h) → T0.21 GameLoop整合(3h) → T0.22 Debug Overlay(2h) → T0.23 集成测试+打磨(3h)

含完整 DAG 依赖图。

---

## 补充: RandomContext 和 EventBus 实现
RandomContext: from_seed(seed)/from_deterministic(context_str)/live() — uniform/gauss/randint/choice/probability/shuffle
EventBus: subscribe/publish/unsubscribe/enqueue/process_queue/clear + EVENT_SCHEMAS 字典

---

## 第5部分：AI Behavior System 架构 (P9 新增)

### 5.1 行为树 + 战术编排器 + P0 模块

```
┌──────────────────────────────────────────────────────────────┐
│                    TacticalOrchestrator                       │
│  (全局战术决策: 威胁评估 → 行为优先级排序 → 资源分配)          │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ BehaviorTree │  │ BehaviorTree │  │   BehaviorTree      │  │
│  │  (Unit AI)   │  │  (Unit AI)   │  │    (Unit AI)        │  │
│  │             │  │             │  │                     │  │
│  │ ┌─────────┐ │  │ ┌─────────┐ │  │ ┌─────────────────┐ │  │
│  │ │P0 Module│ │  │ │P0 Module│ │  │ │   P0 Module     │ │  │
│  │ │AmmoPick │ │  │ │Surrender│ │  │ │  SmokeDeploy    │ │  │
│  │ │WpnScav  │ │  │ │WpnJam   │ │  │ │  SquadDegrade   │ │  │
│  │ │NCORally │ │  │ │         │ │  │ │                 │ │  │
│  │ └─────────┘ │  │ └─────────┘ │  │ └─────────────────┘ │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              P0 AI Behavior Modules                      │ │
│  │  AmmoPickup | WeaponScavenging | Surrender | WeaponJam  │ │
│  │  SmokeDeployment | SquadDegradation | NCORally          │ │
│  └─────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

### 5.2 P0 AI 行为模块接口

```python
class AIBehaviorModule(ABC):
    """P0 AI行为模块基类"""
    priority: int          # 行为优先级 (0=最高)
    cooldown_ticks: int    # 冷却时间

    @abstractmethod
    def evaluate(self, unit: Unit, context: TacticalContext) -> float:
        """评估行为适用性，返回0.0-1.0分数"""

    @abstractmethod
    def execute(self, unit: Unit, context: TacticalContext) -> BehaviorResult:
        """执行行为，返回结果"""

class AmmoPickupBehavior(AIBehaviorModule):
    """AI-P0-01: 弹药拾取"""
    priority = 10
    cooldown_ticks = 60

    def evaluate(self, unit, context):
        if unit.weapon.ammo_remaining > 0: return 0.0
        if not context.nearby_ammo_sources: return 0.0
        return 0.9  # 弹药耗尽时高优先级

    def execute(self, unit, context):
        source = context.nearest_ammo_source
        return MoveAndInteractResult(target=source, action="pickup_ammo")

class WeaponScavengingBehavior(AIBehaviorModule):
    """AI-P0-02: 武器搜刮"""
    priority = 15
    cooldown_ticks = 90

    def evaluate(self, unit, context):
        if unit.weapon.state not in (JAMMED, OUT_OF_AMMO): return 0.0
        if not context.nearby_dead_units: return 0.0
        return 0.8

class SurrenderBehavior(AIBehaviorModule):
    """AI-P0-03: 投降"""
    priority = 5  # 最高优先级(生存)
    cooldown_ticks = 0  # 不可逆，无冷却

    def evaluate(self, unit, context):
        if unit.morale.value >= 5: return 0.0
        if context.friendly_units_within_range(5): return 0.0
        if not context.is_surrounded: return 0.0
        return 1.0  # 确定投降

class WeaponJamBehavior(AIBehaviorModule):
    """AI-P0-04: 武器卡壳"""
    priority = 8
    cooldown_ticks = 0  # 被动触发

    def evaluate(self, unit, context):
        if unit.weapon.state != JAMMED: return 0.0
        return 0.85

    def execute(self, unit, context):
        # 选择: 清除故障 或 搜刮替代武器
        if context.nearby_dead_units:
            return ScavengeOrClearJamResult(prefer_scavenge=True)
        return ClearJamResult(clear_ticks=unit.weapon.jam_clear_time)

class SmokeDeploymentBehavior(AIBehaviorModule):
    """AI-P0-05: 烟雾部署"""
    priority = 12
    cooldown_ticks = 120

    def evaluate(self, unit, context):
        if unit.suppression < 50: return 0.0
        if not unit.has_smoke_grenades: return 0.0
        return 0.75

    def execute(self, unit, context):
        return DeploySmokeResult(position=unit.position, radius=3, duration_ticks=300)

class SquadDegradationBehavior(AIBehaviorModule):
    """AI-P0-06: 班降解"""
    priority = 20  # 持续性效果，低优先级
    cooldown_ticks = 0  # 持续评估

    def evaluate(self, unit, context):
        survival_rate = context.squad_survival_rate
        if survival_rate >= 0.5: return 0.0
        return 1.0 - survival_rate  # 伤亡越重分数越高

    def execute(self, unit, context):
        survival_rate = context.squad_survival_rate
        penalty = self._calculate_nonlinear_penalty(survival_rate)
        return ApplyDegradationResult(
            accuracy_modifier=penalty,
            morale_modifier=penalty * 0.8,
            speed_modifier=penalty * 0.5
        )

    def _calculate_nonlinear_penalty(self, survival_rate: float) -> float:
        """非线性惩罚: 伤亡越重惩罚越重"""
        # 使用二次函数: penalty = (1 - survival_rate)^2
        return (1.0 - survival_rate) ** 2

class NCORallyBehavior(AIBehaviorModule):
    """AI-P0-07: NCO集结"""
    priority = 7
    cooldown_ticks = 30

    def evaluate(self, unit, context):
        if not unit.is_nco: return 0.0
        if not context.nearby_panic_units: return 0.0
        return 0.8

    def execute(self, unit, context):
        return RallyResult(
            center=unit.position,
            radius=5,
            morale_boost=15,
            clear_panic=True
        )
```

### 5.3 Ammo Pickup / Weapon Scavenging 数据流

```
Unit (ammo=0) ──→ AmmoPickupBehavior.evaluate() ──→ score=0.9
    │
    ├──→ TacticalContext.nearby_ammo_sources
    │    ├── AmmoCrate (地图物品)
    │    └── DeadUnit (阵亡单位弹药)
    │
    ├──→ PathFinder.find_path(unit.pos, source.pos)
    │
    └──→ Execute: MoveTo → Interact → ammo_remaining += source.ammo
         └──→ EventBus.publish(AmmoPickupEvent)

Unit (weapon=JAMMED) ──→ WeaponScavengingBehavior.evaluate() ──→ score=0.8
    │
    ├──→ TacticalContext.nearby_dead_units
    │    └── DeadUnit.weapon (可搜刮武器)
    │
    ├──→ 选择最近/最佳武器
    │
    └──→ Execute: MoveTo → Scavenge → unit.weapon = dead_unit.weapon
         └──→ EventBus.publish(WeaponScavengedEvent)
```

### 5.4 Surrender / Weapon Jam 数据流

```
Unit (morale<5, surrounded) ──→ SurrenderBehavior.evaluate() ──→ score=1.0
    │
    ├──→ 条件检查:
    │    ├── morale.value < 5 ✓
    │    ├── no friendly within 5 tiles ✓
    │    └── enemies on 3+ sides ✓
    │
    └──→ Execute: unit.state = SURRENDERED
         ├──→ Remove from active units
         ├──→ Cannot be attacked
         └──→ EventBus.publish(UnitSurrenderedEvent)

Weapon fires ──→ rng.probability(jam_chance) ──→ JAMMED
    │
    ├──→ WeaponJamBehavior.evaluate() ──→ score=0.85
    │
    ├──→ 选择:
    │    ├── ClearJam (等待jam_clear_time ticks)
    │    └── Scavenge (如果有附近阵亡单位)
    │
    └──→ Execute:
         ├── ClearJamResult: weapon.state → READY after clear_ticks
         └── ScavengeResult: weapon replaced
```

### 5.5 Squad Degradation / NCO Rally 数据流

```
Squad casualties ──→ SquadDegradationBehavior.evaluate()
    │
    ├──→ survival_rate = alive_count / initial_count
    │
    ├──→ if survival_rate < 0.5:
    │    ├── penalty = (1 - survival_rate)²
    │    ├── accuracy_modifier = 1.0 - penalty
    │    ├── morale_modifier = 1.0 - penalty * 0.8
    │    └── speed_modifier = 1.0 - penalty * 0.5
    │
    └──→ ApplyDegradationResult → Unit stats modified
         └──→ EventBus.publish(SquadDegradedEvent)

NCO unit ──→ NCORallyBehavior.evaluate()
    │
    ├──→ if unit.is_nco AND nearby_panic_units:
    │
    ├──→ Execute: RallyResult
    │    ├── center = nco.position
    │    ├── radius = 5 tiles
    │    ├── morale_boost = +15
    │    └── clear_panic = True
    │
    └──→ Affected units:
         ├── morale.value += 15 (clamped at 100)
         ├── panic state → suppressed/normal
         └── EventBus.publish(NCORallyEvent)
```

### 5.6 Smoke Tactical AI 数据流

```
Unit (suppression>50) ──→ SmokeDeploymentBehavior.evaluate()
    │
    ├──→ 条件检查:
    │    ├── suppression > 50 ✓
    │    └── has_smoke_grenades ✓
    │
    ├──→ Execute: DeploySmokeResult
    │    ├── position = unit.position
    │    ├── radius = 3 tiles
    │    └── duration = 300 ticks
    │
    └──→ Smoke effects:
         ├── GameMap.add_smoke_zone(pos, radius, duration)
         ├── Smoke tile: blocks_los = True
         ├── Units in smoke: concealment_modifier += 0.8
         └── EventBus.publish(SmokeDeployedEvent)
              └──→ AI re-evaluates: move under smoke cover
```

---

## 第6部分：Game Settings System 架构 (P9 新增)

### 6.1 设置系统架构

```
┌─────────────────────────────────────────────────────┐
│                  GameSettingsManager                  │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │ DifficultyPre │  │ SideSettings │  │ CustomOve │ │
│  │ set (5级)     │  │ (per faction)│  │ rride     │ │
│  │              │  │              │  │           │ │
│  │ RECRUIT      │  │ allies:      │  │ user mods │ │
│  │ EASY         │  │  experience  │  │ to preset │ │
│  │ NORMAL       │  │  supply      │  │ values    │ │
│  │ HARD         │  │ axis:        │  │           │ │
│  │ VETERAN      │  │  experience  │  └───────────┘ │
│  └──────────────┘  │  supply      │                │
│        │           └──────────────┘                │
│        │                  │                        │
│        └──────┬───────────┘                        │
│               ▼                                    │
│  ┌──────────────────────────────────────────────┐  │
│  │           ResolvedSettings                    │  │
│  │  allies_experience: ExperienceLevel           │  │
│  │  allies_supply: SupplyLevel                  │  │
│  │  axis_experience: ExperienceLevel             │  │
│  │  axis_supply: SupplyLevel                    │  │
│  └──────────────────────────────────────────────┘  │
│               │                                    │
│               ▼                                    │
│  ┌──────────────────────────────────────────────┐  │
│  │           SettingsApplier                     │  │
│  │  apply_to_units() → accuracy/morale/ammo     │  │
│  │  apply_to_campaign() → supply/reinforcement   │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

### 6.2 设置数据模型

```python
class DifficultyPreset(Enum):
    RECRUIT = "recruit"
    EASY = "easy"
    NORMAL = "normal"
    HARD = "hard"
    VETERAN = "veteran"

class ExperienceLevel(Enum):
    GREEN = "green"        # 命中率-15%, 士气恢复-20%
    VETERAN = "veteran"    # 基准值
    ELITE = "elite"        # 命中率+15%, 士气恢复+20%
    CRACK = "crack"        # 命中率+25%, 士气恢复+30%, 压制抗性+40%

class SupplyLevel(Enum):
    SCARCE = "scarce"      # 弹药-40%, 无增援
    LIMITED = "limited"    # 弹药-20%, 有限增援
    NORMAL = "normal"      # 基准值
    ABUNDANT = "abundant"  # 弹药+20%, 额外增援波次

@dataclass
class SideSettings:
    experience: ExperienceLevel
    supply: SupplyLevel

@dataclass
class GameSettings:
    preset: DifficultyPreset
    allies: SideSettings
    axis: SideSettings
    custom_overrides: dict[str, Any]  # 用户自定义覆盖

    @classmethod
    def from_preset(cls, preset: DifficultyPreset) -> "GameSettings":
        """从预设创建设置"""
        PRESET_MAP = {
            DifficultyPreset.RECRUIT:  SideSettings(ExperienceLevel.GREEN, SupplyLevel.ABUNDANT),
            # allies_side / axis_side per PRD preset table
        }
        ...

    def resolve(self) -> ResolvedSettings:
        """解析最终设置(含自定义覆盖)"""
        ...
```

---

## 第7部分：Campaign Four-Layer 架构 (P8/P9 新增)

### 7.1 四层架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    Grand Campaign                            │
│  (市场花园行动整体: Day 1 - Day 6)                           │
│  ├── 战略地图: 5座桥梁状态 / 3条进攻路线                      │
│  ├── 全局资源: 预备队 / 空投补给 / 增援时间表                  │
│  └── 胜负条件: 占领Arnhem桥 / 德军反攻成功                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │  Sector 1        │  │  Sector 2        │  │  Sector 3   │ │
│  │  Allied Airborne │  │  XXX Corps       │  │  German     │ │
│  │                  │  │                  │  │  Defense    │ │
│  │  ┌────────────┐  │  │  ┌────────────┐  │  │ ┌────────┐ │ │
│  │  │ Operation  │  │  │  │ Operation  │  │  │  │Op 6-7  │ │ │
│  │  │ 1-3        │  │  │  │ 4-5        │  │  │  │        │ │ │
│  │  │            │  │  │  │            │  │  │  │        │ │ │
│  │  │ ┌────────┐ │  │  │  │ ┌────────┐ │  │  │  │┌──────┐│ │ │
│  │  │ │Battle  │ │  │  │  │ │Battle  │ │  │  │  ││Battle││ │ │
│  │  │ │1-15    │ │  │  │  │ │16-25   │ │  │  │  ││26-29 ││ │ │
│  │  │ └────────┘ │  │  │  │ └────────┘ │  │  │  │└──────┘│ │ │
│  │  └────────────┘  │  │  └────────────┘  │  │  └────────┘ │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
│                                                             │
│  3 Sectors / 7 Operations / 29 Battles / 28 Maps           │
└─────────────────────────────────────────────────────────────┘
```

### 7.2 战役数据模型

```python
@dataclass
class GrandCampaign:
    sectors: list[Sector]
    strategic_map: StrategicMap
    supply_system: SupplySystem
    timeline: OperationTimeline

@dataclass
class Sector:
    id: str
    name: str                    # "Allied Airborne" / "XXX Corps" / "German Defense"
    operations: list[Operation]
    side: Faction                # 主要阵营

@dataclass
class Operation:
    id: str
    name: str                    # "Son Bridge" / "Waal Crossing" etc.
    day: int                     # Day 1-6
    battles: list[Battle]
    reinforcements: list[ReinforcementEvent]
    supply_level: SupplyLevel

@dataclass
class Battle:
    id: str
    map_file: str                # 引用28张地图之一
    objectives: list[Objective]
    oob_allies: OrderOfBattle
    oob_axis: OrderOfBattle
    time_limit_ticks: int
    victory_conditions: list[VictoryCondition]
```

---

## 第8部分：Domain Model 更新 (P9 新增实体)

### 8.1 新增实体

| 实体 | 属性 | 说明 |
|------|------|------|
| `SURRENDERED` (UnitState) | morale<5, 不可攻击, 从战斗移除 | 投降状态 |
| `JAMMED` (WeaponState) | jam_chance触发, 需清除时间 | 武器卡壳状态 |
| `SmokeZone` | position, radius, duration_ticks, blocks_los | 烟雾区域 |
| `AmmoCrate` | position, ammo_type, ammo_count | 弹药箱 |
| `DifficultyPreset` | RECRUIT/EASY/NORMAL/HARD/VETERAN | 难度预设 |
| `ExperienceLevel` | GREEN/VETERAN/ELITE/CRACK | 经验等级 |
| `SupplyLevel` | SCARCE/LIMITED/NORMAL/ABUNDANT | 补给等级 |
| `SideSettings` | experience, supply | 每方独立设置 |
| `GameSettings` | preset, allies, axis, custom_overrides | 游戏设置 |
| `GrandCampaign` | sectors, strategic_map, supply_system, timeline | 大战役 |
| `Sector` | id, name, operations, side | 战区 |
| `Operation` | id, name, day, battles, reinforcements, supply_level | 作战行动 |
| `Battle` | id, map_file, objectives, oob, victory_conditions | 战斗 |

### 8.2 WeaponComponent 更新

```python
class WeaponComponent:
    # 新增属性
    jam_chance: float = 0.02       # 每次射击卡壳概率 (默认2%)
    jam_clear_time: int = 30       # 清除故障所需ticks
    has_smoke_grenades: bool = False
    smoke_grenade_count: int = 0

    def fire(self) -> FireResult:
        """射击，含卡壳判定"""
        if self.ammo_remaining <= 0:
            self.state = WeaponState.OUT_OF_AMMO
            return FireResult(success=False, reason="out_of_ammo")

        self.ammo_remaining -= 1

        # 卡壳判定
        if self.rng.probability(self.jam_chance):
            self.state = WeaponState.JAMMED
            return FireResult(success=False, reason="jammed")

        return FireResult(success=True)
```

### 8.3 Unit 状态扩展

```python
class UnitState(Enum):
    ACTIVE = "active"
    SUPPRESSED = "suppressed"
    PANIC = "panic"
    ROUTING = "routing"
    SURRENDERED = "surrendered"    # P9 新增
    DEAD = "dead"
```

---

## 第9部分：系统交互图更新 (P9)

### 9.1 P0 AI 行为与现有系统交互

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Ballistic   │────→│  Morale      │────→│  AI Behavior │
│  Engine      │     │  Calculator  │     │  Modules     │
│              │     │              │     │              │
│ • 命中/未命中 │     │ • 士气值变化  │     │ • AmmoPickup │
│ • 压制值     │     │ • 状态转换    │     │ • Surrender  │
│ • 武器卡壳   │     │ • 恐慌传染    │     │ • SmokeDeploy│
└──────────────┘     └──────────────┘     │ • NCORally   │
                                          └──────┬───────┘
┌──────────────┐     ┌──────────────┐            │
│  GameMap      │────→│  FogOfWar    │            │
│              │     │              │     ┌──────▼───────┐
│ • 烟雾区域   │     │ • LOS阻挡    │     │  Tactical    │
│ • 弹药箱     │     │ • 视野更新   │     │  Orchestrator│
│ • 地形掩体   │     │              │     │              │
└──────────────┘     └──────────────┘     │ • 优先级排序 │
                                          │ • 资源分配   │
┌──────────────┐     ┌──────────────┐     │ • 冲突解决   │
│  GameSettings│────→│  Squad       │────→│              │
│              │     │              │     └──────────────┘
│ • 经验等级   │     │ • 班降解     │
│ • 补给等级   │     │ • NCO标识    │
│ • 难度预设   │     │ • 存活率     │
└──────────────┘     └──────────────┘
```

### 9.2 Game Settings 影响链

```
GameSettings ──→ SettingsApplier ──→ Unit/Combat/Campaign
    │                                      │
    ├── ExperienceLevel                    ├── 命中率修正 (±15~25%)
    │   ├── GREEN: accuracy * 0.85         ├── 士气恢复修正 (±20~30%)
    │   ├── VETERAN: accuracy * 1.0        ├── 压制抗性修正 (+40% for CRACK)
    │   ├── ELITE: accuracy * 1.15         └── 弹药修正 (±20~40%)
    │   └── CRACK: accuracy * 1.25
    │
    └── SupplyLevel
        ├── SCARCE: ammo * 0.6, no reinforcement
        ├── LIMITED: ammo * 0.8, limited reinforcement
        ├── NORMAL: ammo * 1.0, standard reinforcement
        └── ABUNDANT: ammo * 1.2, extra reinforcement waves
```

---

## 第10部分：胜利条件系统设计 (M2 新增)

### 10.1 CC2原版胜利条件

CC2原版采用三重胜利条件机制，PyCC2现已完整实现：

```
┌──────────────────────────────────────────────────────────────┐
│                    Victory Conditions                         │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  1. 即时VL占领 (Instant VL Capture)                          │
│     ├── 占领所有敌方Victory Location → 立即胜利              │
│     ├── VL被占领时立即判定，无需等待                          │
│     └── 双方同时满足条件时，进攻方优先                        │
│                                                              │
│  2. 20分钟战斗计时器 (Battle Timer)                           │
│     ├── 每场战斗限时20分钟实时                                │
│     ├── 时间耗尽 → 按积分判定胜负                             │
│     └── 计时器在HUD顶部显示                                   │
│                                                              │
│  3. 积分制评分 (Point Scoring)                                │
│     ├── Bridge VL = 40分                                     │
│     ├── Road VL = 30分                                       │
│     ├── LZ VL = 20分                                         │
│     ├── Regular VL = 10-19分                                 │
│     ├── 时间耗尽时比较双方积分                                │
│     └── 积分差距决定胜利等级: 决定性/中等/勉强                 │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 10.2 胜利条件数据模型

```python
class VictoryConditionType(Enum):
    INSTANT_VL_CAPTURE = "instant_vl_capture"    # 即时VL占领
    TIMER_EXPIRY = "timer_expiry"                # 计时器到期
    POINT_SCORING = "point_scoring"              # 积分制

@dataclass
class VictoryLocation:
    id: str
    position: TileCoord
    value: int                    # 10-40分
    owner: Faction | None         # None=中立
    vl_type: VLType               # BRIDGE/ROAD/LZ/REGULAR

@dataclass
class BattleResult:
    winner: Faction | None        # None=平局
    victory_type: VictoryConditionType
    margin: str                   # "decisive" / "moderate" / "marginal"
    allied_score: int
    axis_score: int
    battle_duration_ticks: int
```

---

## 第11部分：建筑驻守系统设计 (M2 新增)

### 11.1 建筑驻守架构

```
┌──────────────────────────────────────────────────────────────┐
│                    Building Garrison System                    │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────┐    ┌──────────────────────────────┐    │
│  │  BUILDING_       │    │  BuildingGarrisonSystem      │    │
│  │  ENTERABLE       │───→│                              │    │
│  │  terrain tile    │    │  • enter_building(unit, tile) │    │
│  │                  │    │  • exit_building(unit)        │    │
│  │  capacity: 2-4   │    │  • get_garrison(tile)        │    │
│  │  units           │    │  • get_defense_bonus(unit)   │    │
│  └─────────────────┘    └──────────────────────────────┘    │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Defense Bonuses                                      │   │
│  │  ├── Cover modifier: +0.50 (BUILDING_ENTERABLE)      │   │
│  │  ├── Concealment: +0.30                              │   │
│  │  ├── Suppression resistance: +25%                    │   │
│  │  └── Incoming accuracy penalty: -20% for attackers   │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Window Firing Arc Restriction                        │   │
│  │  ├── Each building has 1-4 windows (facing dirs)     │   │
│  │  ├── Units can only fire through windows             │   │
│  │  ├── Firing arc: 90° cone per window                 │   │
│  │  └── Units must rotate to window to fire             │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 11.2 窗户射击弧度

```python
@dataclass
class BuildingWindow:
    position: TileCoord           # 窗户所在瓦片
    facing: Direction             # 窗户朝向 (N/NE/E/SE/S/SW/W/NW)
    arc_degrees: float = 90.0    # 射击弧度

    def is_in_firing_arc(self, target: Vec2) -> bool:
        """检查目标是否在窗户射击弧度内"""
        direction_to_target = (target - self.position.to_vec2()).normalized
        facing_vec = Direction.to_vec2(self.facing)
        angle = direction_to_target.angle_to(facing_vec)
        return abs(angle) <= self.arc_degrees / 2

@dataclass
class GarrisonState:
    building_tile: TileCoord
    units: list[Unit]             # 当前驻守单位 (max 2-4)
    windows: list[BuildingWindow] # 建筑窗户列表
    is_enterable: bool = True
```

---

## 第12部分：桥梁摧毁系统设计 (M2 新增)

### 12.1 工兵炸桥架构

```
┌──────────────────────────────────────────────────────────────┐
│                    Bridge Destruction System                   │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────┐    ┌──────────────────────────────┐    │
│  │  BRIDGE          │    │  BridgeDestructionSystem     │    │
│  │  terrain tile    │───→│                              │    │
│  │                  │    │  • can_destroy(unit, tile)    │    │
│  │  destroyable:    │    │  • destroy_bridge(tile)      │    │
│  │    True          │    │  • is_destroyed(tile)        │    │
│  │                  │    │                              │    │
│  └─────────────────┘    └──────────────────────────────┘    │
│                                                              │
│  前提条件:                                                    │
│  ├── 单位必须是Engineer类型                                   │
│  ├── 单位必须在桥梁相邻瓦片上                                 │
│  ├── 单位必须未被压制                                         │
│  └── 炸桥需要5秒准备时间（150 ticks）                        │
│                                                              │
│  炸桥效果:                                                    │
│  ├── BRIDGE tile → WATER tile (不可通过)                     │
│  ├── 相邻桥梁瓦片也变为WATER                                  │
│  ├── 桥上单位落入水中（阵亡）                                  │
│  ├── VL价值归零（如桥梁上有VL）                               │
│  └── EventBus.publish(BridgeDestroyedEvent)                  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 12.2 桥梁摧毁数据流

```
Engineer unit ──→ BridgeDestructionSystem.can_destroy()
    │
    ├── 条件检查:
    │    ├── unit.unit_type == ENGINEER ✓
    │    ├── adjacent_to_bridge ✓
    │    ├── not suppressed ✓
    │    └── bridge not already destroyed ✓
    │
    ├── 准备阶段 (150 ticks):
    │    ├── unit.state = DEMOLISHING
    │    ├── 进度条显示
    │    └── 可被攻击打断
    │
    └── 执行炸桥:
         ├── bridge_tile.terrain = WATER
         ├── adjacent_bridge_tiles.terrain = WATER
         ├── units_on_bridge → killed
         ├── VL on bridge → value = 0
         └── EventBus.publish(BridgeDestroyedEvent)
```

---

## 第13部分：战役继承系统设计 (M2 新增)

### 13.1 战斗间单位继承架构

```
┌──────────────────────────────────────────────────────────────┐
│                    Campaign Carryover System                   │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Battle 1 完成                                               │
│  ├── 收集存活单位状态                                         │
│  ├── 记录伤亡/弹药消耗/士气状态                               │
│  └── 保存到 CampaignState.surviving_units                    │
│           │                                                  │
│           ▼                                                  │
│  Campaign Day Briefing                                       │
│  ├── 显示战略地图                                             │
│  ├── 显示存活单位列表                                         │
│  ├── 显示伤亡报告                                             │
│  └── 预览下一场战斗                                           │
│           │                                                  │
│           ▼                                                  │
│  Battle 2 部署                                               │
│  ├── 从surviving_units加载存活单位                            │
│  ├── 保留: 经验/士气/弹药/损伤状态                            │
│  ├── 补充: 新增援单位（根据补给等级）                          │
│  └── 移除: 阵亡/投降单位                                     │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 13.2 继承数据模型

```python
@dataclass
class UnitCarryoverState:
    unit_id: str
    template_id: str
    faction: Faction
    health_ratio: float          # 当前HP/最大HP
    morale_value: int            # 当前士气值
    ammo_remaining: int          # 剩余弹药
    experience: ExperienceLevel  # 经验等级
    kills: int                   # 累计击杀
    battles_survived: int        # 存活战斗数

@dataclass
class CampaignState:
    current_day: int             # 当前战役日 (1-9)
    current_battle_index: int    # 当前战斗索引
    surviving_units: dict[str, UnitCarryoverState]  # 存活单位
    total_casualties: int        # 总伤亡
    total_kills: int             # 总击杀
    victory_locations_held: list[str]  # 已占领VL

    def apply_battle_result(self, result: BattleResult) -> None:
        """应用战斗结果，更新存活单位状态"""
        ...

    def get_reinforcements(self, supply: SupplyLevel) -> list[UnitCarryoverState]:
        """根据补给等级获取增援单位"""
        ...
```

### 13.3 战役结束画面

```python
@dataclass
class CampaignResult:
    winner: Faction
    total_days: int
    battles_fought: int
    battles_won: int
    total_casualties: int
    total_kills: int
    victory_locations_captured: int
    units_survived: int
    campaign_rating: str          # "Historic Victory" / "Marginal Victory" / etc.
```

---

## 第14部分：v0.3.31-v0.3.39 架构更新 (M3 新增)

### 14.1 更新后的技术架构树

```
PyCC2/
├── src/pycc2/
│   ├── domain/                    # 核心游戏逻辑（纯Python，高可测试性）
│   │   ├── ai/                   # 行为树AI，战术决策系统
│   │   ├── components/           # ECS：Health, Morale, Weapon, Position, Vision
│   │   ├── entities/             # Squad, Unit, GameMap, Projectile
│   │   ├── systems/              # Campaign, Combat, Ballistics, Pathfinding
│   │   └── value_objects/        # Damage, Direction, TerrainType, Vec2, AudioEnums
│   ├── services/                 # 游戏循环，AI服务，Event bus，Combat director
│   │   ├── game_loop/            # GameLoopAssembler (Composition Root)
│   │   └── ...
│   ├── presentation/             # 渲染，输入处理，UI，音频
│   │   ├── rendering/            # Camera, HUD, Minimap, Sprites, Isometric引擎
│   │   │   ├── surface_pool.py              # 统一Surface LRU池 (v0.3.31)
│   │   │   ├── shell_casing_system.py       # 药莢排出物理系统 125行 (v0.3.33)
│   │   │   ├── flash_effect_system.py       # 屏幕闪光效果系统 101行 (v0.3.33)
│   │   │   ├── weather_system.py            # 天气覆盖渲染系统 160行 (v0.3.33)
│   │   │   ├── fade_transition.py           # UI alpha淡入淡出过渡 (v0.3.32)
│   │   │   ├── ui_overlay_renderer.py       # VL标志/攻击线/队列命令/LOS (v0.3.28)
│   │   │   ├── particle_effects_renderer.py # 粒子效果渲染器 (v0.3.13)
│   │   │   ├── environment_renderer.py      # 环境渲染器 (v0.3.13)
│   │   │   ├── tank_pixel_renderer.py       # 战车像素渲染器
│   │   │   ├── infantry_pixel_renderer.py   # 步兵像素渲染器
│   │   │   └── ...               # 其他渲染模块
│   │   ├── input/                # 命令系统，交互控制器
│   │   ├── ui/                   # 菜单，面板，工具提示，部署UI
│   │   └── audio/                # 声音系统，语音命令，环境音频
│   └── infrastructure/           # 存档系统，配置，解析器
│       ├── resource_cache.py     # HTTP下载+SHA256+LRU+离线 (v0.3.37)
│       └── ...
├── data/
│   ├── maps/                     # 63个历史地图JSON文件
│   ├── scenarios/                # 11个场景配置
│   └── units/                    # 单位模板定义
├── tests/                        # ~3985测试（单元 + 集成 + E2E + 冒烟）
├── assets/                       # 精灵图，音效，CC2参考截图
└── docs/                         # 设计文档，PRD，差距分析
```

### 14.2 分层描述更新

#### Domain 层
核心业务逻辑，纯Python实现，零外部依赖。包含AI行为树、ECS组件、实体、系统和值对象。
- v0.3.29新增：`audio_enums.py`（SoundType + InteractionMode从services迁移）
- 原则：domain不依赖presentation或infrastructure

#### Services 层
游戏循环编排、AI服务、EventBus、CombatDirector。
- v0.3.26新增：GameStateView Protocol打破presentation→services循环依赖
- v0.3.26新增：GameLoopAssembler作为Composition Root（10个子方法）
- EventBus双通道：publish()自动桥接TypedDict到named handlers

#### Presentation 层
渲染、输入处理、UI、音频。最大的变化区域。
- **Rendering子层**（v0.3.28-v0.3.37重大重构）：
  - EnhancedRenderer从1389行→943行（-32%），3个子系统抽出
  - 新增：ShellCasingSystem、FlashEffectSystem、WeatherSystem、FadeTransition
  - 新增：tank_pixel_renderer.py、infantry_pixel_renderer.py
  - SurfacePool统一：6/6消费者使用共享LRU池
  - Dirty Rectangle优化：_DirtyRectTracker部分屏幕更新
- **UI子层**：
  - ThemeManager运行时激活（default/dark/light）
  - 按钮hover/click反馈 + 工具提示系统
  - FadeTransition动画（BottomPanel/Minimap/HUD）
- **Audio子层**：
  - EnvironmentalAudioSystem：11种程序化环境音

#### Infrastructure 层
存档系统、配置、解析器。
- v0.3.35：存档安全加固（权限0o600，HMAC密钥最小长度验证）
- v0.3.37：ResourceCacheManager（HTTP下载+SHA256验证+LRU缓存+离线模式）

### 14.3 关键架构指标

| 指标 | v0.3.0 | v0.3.39 | 变化 |
|------|--------|---------|------|
| 测试数 | 3372 | ~3985 | +613 |
| CC2还原度 | ~95% | ~88% | -7%（更诚实评估） |
| 层违规 | ~41 | ~25 | -39% |
| EnhancedRenderer行数 | 1389 | 943 | -32% |
| 裸print() | 200+ | ~1 | 99.3%清理 |
| E2E测试 | 17阶段/dummy | 38阶段/real SDL | 显著提升 |
| 抽出渲染模块 | 9 | 22 | +13 |
| God Classes (>1000行) | 8 | 4 | -50% |
