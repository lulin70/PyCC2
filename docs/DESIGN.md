# PyCC2 技术设计文档 (DESIGN) **v2.0**

> **项目**: Close Combat 2 Python 重写 | **阶段**: P9 — AI深度提升+新游戏设置
> **输入**: P2 ADD v1.0 (架构设计) + P1 PRD v1.0 (需求规格) + P9 新特性
> **文档版本**: v2.0 | **日期**: 2026-05-20

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
