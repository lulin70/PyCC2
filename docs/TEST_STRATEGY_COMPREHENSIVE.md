# PyCC2 全面测试策略 (Comprehensive Test Strategy)

> **版本**: v1.0
> **创建日期**: 2026-05-22
> **作者**: DevSquad Test Expert Role
> **状态**: 🧪 测试策略定稿 - 待Architect + Security review
> **优先级**: ★★★★★ (最高优先级 - 质量基石)

---

## 测试哲学

### 核心原则

> **"测试不是为了证明代码能工作，而是为了证明它不会出错"**

我们的测试文化建立在以下信念之上：

1. **零容忍**: 0个P0测试失败是唯一的可接受标准
2. **快速反馈**: 测试必须在分钟级内完成，不是小时级
3. **真实场景**: 测试必须模拟真实用户行为，而非理想化路径
4. **持续自动化**: 任何需要手动执行的测试最终都要自动化
5. **测试即文档**: 好的测试用例就是最好的API文档

---

## 一、测试金字塔 (Test Pyramid)

### 1.1 架构总览

```
                    ┌─────────────────────┐
                    │    E2E Tests         │  ← 少量(15-20个)
                    │    (Slow, 10min)     │     核心用户场景验证
                   ╱╲                     ╱╲
                  ╱  ├─────────────────────┤
                 ╱   │ Integration Tests   │  ← 适中(40-50个)
                ╱    │  (Medium, 5min)      │     模块间交互验证
               ╱     ├─────────────────────┤
              ╱      │  Unit Tests          │  ← 大量(2700+)
             ╱       │  (Fast, <3min)       │     函数/方法级验证
            ╱        └─────────────────────┘
           ╱
          └────────────────────────────────┘

           数量: 底部多，顶部少
           速度: 底部快，顶部慢
           成本: 底部低，顶部高
           置信度:底部低，顶部高（但总量高）
```

### 1.2 当前状态 vs 目标状态

| 层级 | 当前数量 | 通过率 | 执行时间 | 目标数量 | 目标通过率 | 目标时间 |
|------|---------|--------|----------|---------|-----------|---------|
| **Unit Tests** | ~2200+ | ~99.7% (6失败) | <3min | 2700+ | 100% | <3min |
| **Integration** | ~10 | ~80% | <2min | 45 | 100% | <5min |
| **E2E Tests** | 17 | **0% (17 ERROR)** | N/A | 20 | 100% | <10min |
| **Performance** | 1 | Pass | 30s | 10 | Pass | <2min |
| **Visual Regression** | 0 | N/A | N/A | 8 | 100% | <5min |

---

## 二、Layer 1: 单元测试 (Unit Tests)

### 2.1 目标与范围

**目标数量**: 2700+ 个测试
**执行时间**: < 3 分钟
**覆盖率目标**:
- 行覆盖率 (Line Coverage): > 90%
- 分支覆盖率 (Branch Coverage): > 85%
- 函数覆盖率 (Function Coverage): > 95%

#### 测试分层架构

```
tests/unit/
├── domain/                    # 领域层测试 (核心业务逻辑)
│   ├── systems/               # 系统组件测试
│   ├── ai/                    # AI模块测试
│   ├── entities/              # 实体测试
│   ├── components/            # 组件测试
│   └── value_objects/         # 值对象测试
│
├── presentation/              # 表现层测试 (UI/渲染)
│   ├── rendering/              # 渲染器测试
│   ├── ui/                     # UI组件测试
│   ├── input/                  # 输入处理测试
│   └── audio/                  # 音频系统测试
│
├── infrastructure/            # 基础设施测试
│   ├── config/                 # 配置系统测试
│   ├── save_system/            # 存档系统测试
│   └── security/               # 安全功能测试
│
└── services/                  # 服务层测试
    ├── game_loop/              # GameLoop测试
    ├── combat/                 # 战斗服务测试
    └── event_bus/              # EventBus测试
```

---

### 2.2 Domain层详细测试计划

#### 2.2.1 Systems - 系统组件测试 (预计: 350 tests)

##### WeatherEffects 天气效果引擎 [44 tests ✅已有]

```python
# tests/unit/domain/systems/test_weather_effects.py

class TestWeatherEffects:
    """天气效果引擎完整测试套件"""

    def test_rain_movement_penalty(self):
        """雨天移动惩罚正确应用"""
        weather = WeatherEffects(current_weather='rain')
        base_speed = 5.0
        modified = weather.apply_movement_modifier(base_speed)
        assert modified < base_speed  # 应该减速
        assert modified == pytest.approx(base_speed * 0.8, rel=0.1)

    def test_fog_visibility_reduction(self):
        """雾天视野缩减"""
        weather = WeatherEffects(current_weather='fog')
        base_visibility = 10
        reduced = weather.apply_visibility_modifier(base_visibility)
        assert reduced < base_visibility

    def test_snow_accuracy_penalty(self):
        """雪天命中率下降"""
        weather = WeatherEffects(current_weather='snow')
        base_accuracy = 0.8
        penalized = weather.apply_accuracy_modifier(base_accuracy)
        assert penalized < base_accuracy

    def test_clear_weather_no_modifiers(self):
        """晴天无修正"""
        weather = WeatherEffects(current_weather='clear')
        assert weather.apply_movement_modifier(5.0) == 5.0
        assert weather.apply_visibility_modifier(10) == 10
        assert weather.apply_accuracy_modifier(0.8) == 0.8

    # ... 更多测试用例 (共44个)
```

**当前状态**: ✅ 已通过 (44/44)
**改进方向**: 增加边界条件测试 (极端天气参数)

---

##### DayNightCycle 昼夜循环 [55 tests ✅已有]

```python
# tests/unit/domain/systems/test_day_night_cycle.py

class TestDayNightCycle:
    """昼夜循环系统测试"""

    def test_dawn_lighting_transition(self):
        """黎明光照渐变"""
        cycle = DayNightCycle(start_time=5.0)  # 05:00
        lighting = cycle.get_lighting_modifier()
        assert 0.1 < lighting['brightness'] < 0.3
        assert 'warm_tint' in lighting

    def test_night_visibility_penalty(self):
        """夜晚视野惩罚"""
        cycle = DayNightCycle(start_time=22.0)  # 22:00
        penalty = cycle.get_visibility_penalty()
        assert penalty['reduction'] > 0.3

    def test_time_advancement(self):
        """时间推进正确性"""
        cycle = DayNightCycle(start_time=12.0)
        cycle.advance(hours=6.0)
        assert cycle.current_hour == pytest.approx(18.0, abs=0.1)

    # ... 更多测试 (共55个)
```

**当前状态**: ✅ 已通过 (55/55)
**改进方向**: 添加时间环绕测试 (23:59 → 00:01)

---

##### LOSSystem 视线检测系统 [55 tests - 需扩展]

```python
# tests/unit/domain/systems/test_los_system.py (需新建或扩展)

class TestLOSSystem:
    """视线检测系统 - CC2核心机制"""

    @pytest.fixture
    def los_system(self):
        return LOSSystem()

    @pytest.fixture
    def open_map(self):
        """开阔地图 (无遮挡)"""
        return create_test_map(width=20, height=20, terrain='grass')

    @pytest.fixture
    def forest_map(self):
        """有森林的地图"""
        map_data = create_test_map(width=20, height=20)
        map_data.set_terrain(rect=(5, 5, 8, 8), terrain='forest')  # 森林区域
        return map_data

    def test_line_of_sight_open_terrain(self, los_system, open_map):
        """开阔地形视线通畅"""
        observer = (2, 2)
        target = (15, 15)
        assert los_system.has_los(observer, target, open_map) is True

    def test_blocked_by_forest(self, los_system, forest_map):
        """森林阻挡视线"""
        observer = (2, 2)
        target = (15, 15)  # 穿过森林区域
        result = los_system.has_los(observer, target, forest_map)
        assert result is False

    def test_height_advantage(self, los_system):
        """高地优势增加视野"""
        observer_pos = (10, 10)
        observer_height = 10  # 高地
        target_pos = (15, 5)
        target_height = 0     # 低地
        assert los_system.calculate_los_range(
            observer_pos, observer_height,
            target_pos, target_height
        ) > los_system.BASE_RANGE

    def test_los_caching_performance(self, los_system):
        """LOS计算性能 (缓存命中)"""
        import time
        start = time.perf_counter()

        for _ in range(1000):
            los_system.has_los((0, 0), (19, 19), self.open_map)

        elapsed = time.perf_counter() - start
        assert elapsed < 0.1  # 1000次计算应在100ms内完成

    # ... 共55个测试覆盖:
    # - 地形遮挡 (森林/建筑/树篱)
    # - 高度差影响
    # - 天气影响 (雾/雨/夜)
    # - 单位隐蔽状态
    # - 性能基准
    # - 边界条件
```

**当前状态**: ⚠️ 需要补充至55个测试
**优先级**: P0 (CC2核心机制)

---

##### WeaponSwitchSystem 武器切换系统 [20 tests ✅已有]

**当前状态**: ✅ 已通过 (20/20)

##### AmmoTypeSystem 弹药差异化系统 [22 tests ✅已有]

**当前状态**: ✅ 已通过 (22/22)

##### VehicleCrewSystem 载具乘员系统 [17 tests ✅已有]

**当前状态**: ✅ 已通过 (17/17)

##### CasualtySystem 伤员系统 [16 tests ✅已有]

**当前状态**: ✅ 已通过 (16/16)

##### SwissCheeseDamage 瑞士奶酪伤害模型 [40 tests - 新增]

```python
# tests/unit/domain/systems/test_swiss_cheese_damage.py (新增)

class TestSwissCheeseDamage:
    """
    瑞士奶酪伤害模型测试
    CC2特色: 多层穿透概率，非简单HP扣减
    """

    def test_basic_damage_calculation(self):
        """基础伤害计算"""
        damage_sys = SwissCheeseDamage()
        attacker = create_test_unit(weapon='rifle', range=200)
        defender = create_test_unit(cover='light')

        result = damage_sys.calculate(attacker, defender)
        assert 0 <= result.damage <= attacker.weapon.max_damage
        assert result.is_critical in [True, False]

    def test_cover_layers_reduce_damage(self):
        """掩体层级降低伤害"""
        damage_sys = SwissCheeseDamage()

        no_cover = damage_sys.calculate(
            attacker=create_rifleman(),
            defender=create_unit_with_cover(none)
        )
        light_cover = damage_sys.calculate(
            attacker=create_rifleman(),
            defender=create_unit_with_cover(light)
        )
        heavy_cover = damage_sys.calculate(
            attacker=create_rifleman(),
            defender=create_unit_with_cover(heavy)
        )

        assert heavy_cover.damage < light_cover.damage < no_cover.damage

    def test_random_seed_reproducibility(self):
        """随机种子可重现"""
        damage_sys = SwissCheeseDamage(seed=42)

        result1 = damage_sys.calculate(attacker, defender)
        result2 = damage_sys.calculate(attacker, defender)

        assert result1.damage == result2.damage  # 相同输入→相同输出

    # ... 共40个测试
```

**优先级**: P0 (战斗核心)

---

##### MoraleSys 士气系统 [30 tests - 新增]

```python
# tests/unit/domain/systems/test_morale_sys.py (新增)

class TestMoraleSys:
    """士气系统测试"""

    def test_initial_morale_based_on_unit_type(self):
        """初始士气基于单位类型"""
        morale_sys = MoraleSys()
        rifleman = create_unit(type='rifleman')
        officer = create_unit(type='officer')

        assert morale_sys.get_morale(officer) > morale_sys.get_morale(rifleman)

    def test_casualties_decrease_morale(self):
        """伤亡降低士气"""
        morale_sys = MoraleSys()
        unit = create_full_strength_squad()  # 10人

        initial_morale = morale_sys.get_morale(unit)
        apply_casualties(unit, count=3)  # 伤亡3人

        current_morale = morale_sys.get_morale(unit)
        assert current_morale < initial_morale

    def test_low_morale_triggers_rout(self):
        """低士气触发溃逃"""
        morale_sys = MoraleSys()
        unit = create_unit(morale=15)  # 极低士气

        assert morale_sys.should_rout(unit) is True

    def test_officer_presence_boost(self):
        """军官存在提升士气"""
        squad_without_officer = create_squad(has_officer=False)
        squad_with_officer = create_squad(has_officer=True)

        morale_without = self.morale_sys.get_average(squad_without_officer)
        morale_with = self.morale_sys.get_average(squad_with_officer)

        assert morale_with > morale_without

    # ... 共30个测试
```

**优先级**: P0 (战斗核心)

---

##### Pathfinder 寻路算法 [25 tests - 新增]

```python
# tests/unit/domain/systems/test_pathfinder.py (新增)

class TestPathfinder:
    """A*寻路算法测试"""

    def test_straight_line_path(self):
        """直线无障碍路径"""
        pathfinder = Pathfinder()
        start = (0, 0)
        goal = (10, 0)
        map_data = create_open_map()

        path = pathfinder.find_path(start, goal, map_data)

        assert len(path) > 0
        assert path[0] == start
        assert path[-1] == goal
        assert len(path) <= 11  # Manhattan距离+1

    def test_avoid_obstacle(self):
        """绕过障碍物"""
        map_data = create_map_with_wall(x=5)
        pathfinder = Pathfinder()

        path = pathfinder.find_path((0, 0), (10, 0), map_data)

        assert (5, 0) not in path  # 不穿过墙壁
        assert len(path) > 11  # 路径比直线长

    def test_impossible_path_raises(self):
        """不可达路径抛出异常"""
        map_data = create_enclosed_map()  # 完全封闭
        pathfinder = Pathfinder()

        with pytest.raises(PathNotFoundError):
            pathfinder.find_path((0, 0), (10, 10), map_data)

    def test_terrain_movement_cost(self):
        """地形影响路径选择"""
        map_data = create_map_with_terrain_variant(
            direct_path='forest',   # 直线穿过森林 (慢)
            alternative='road'      # 绕路走公路 (快)
        )
        pathfinder = Pathfinder()

        path = pathfinder.find_path((0, 0), (10, 0), map_data)

        # 应该选择公路 (即使稍远)
        assert 'road' in [map_data.get_tile(p).terrain for p in path]

    # ... 共25个测试
```

**优先级**: P0 (移动核心)

---

#### 2.2.2 AI模块测试 (预计: 250 tests)

##### CoverSeekAI 掩体寻找AI [23 tests ✅已有]
##### RetreatAI 撤退AI [33 tests ✅已有]
##### TacticalAICore 战术AI核心 [45 tests - 新增]

```python
# tests/unit/domain/ai/test_tactical_ai_core.py (新增)

class TestTacticalAICore:
    """战术AI决策核心"""

    def test_flank_manuver_selection(self):
        """侧翼机动选择"""
        ai = TacticalAICore()
        battlefield = create_battlefield_with_open_flank()

        decision = ai.make_decision(battlefield)

        assert decision.action == 'flank'
        assert decision.target_zone == 'enemy_weak_point'

    def test_defensive_hold_when_outnumbered(self):
        """寡不敌众时防守"""
        ai = TacticalAICore()
        battlefield = create_outnumbered_scenario()

        decision = ai.make_decision(battlefield)

        assert decision.action in ['hold', 'retreat', 'dig_in']

    def test_priority_target_selection(self):
        """优先目标选择 (军官/机枪/坦克)"""
        ai = TacticalAICore()
        enemies = [
            create_enemy(type='rifleman'),
            create_enemy(type='officer'),  # 高价值目标
            create_enemy(type='mg_team'),
        ]

        priority = ai.select_target(enemies)

        assert priority.type in ['officer', 'mg_team']  # 应优先攻击

    # ... 共45个测试
```

**优先级**: P1 (AI增强)

---

##### SquadDegradation 班组降级 [20 tests - 新增]

**优先级**: P1

---

#### 2.2.3 Entities实体测试 (预计: 110 tests)

##### Unit 单位实体 [50 tests - 需扩展]

```python
# tests/unit/domain/entities/test_unit.py (扩展)

class TestUnit:
    """单位实体测试"""

    def test_unit_creation_valid_params(self):
        """有效参数创建单位"""
        unit = Unit(
            name="Rifle Squad",
            unit_type=UnitType.INFANTRY,
            faction=Faction.ALLIES,
            position=(5, 5),
            hp=100,
            max_hp=100
        )
        assert unit.hp == 100
        assert unit.alive is True

    def test_hp_clamp_to_max(self):
        """HP不超过最大值"""
        unit = create_unit(max_hp=100)
        unit.heal(amount=150)

        assert unit.hp == 100  # 不超过max

    def test_death_on_zero_hp(self):
        """HP归零时死亡"""
        unit = create_unit(hp=10)
        unit.take_damage(10)

        assert unit.alive is False
        assert unit.hp == 0

    def test_position_update(self):
        """位置更新"""
        unit = create_unit(pos=(5, 5))
        unit.move_to((7, 3))

        assert unit.position == (7, 3)

    def test_facing_direction_change(self):
        """朝向改变"""
        unit = create_unit(facing='north')
        unit.turn_to('east')

        assert unit.facing == 'east'

    def test_weapon_equipment(self):
        """武器装备"""
        unit = create_unarmed_unit()
        rifle = create_weapon(name='M1 Garand')

        unit.equip_weapon(rifle)

        assert unit.current_weapon == rifle
        assert unit.attack_range > 0

    # ... 共50个测试
```

**当前状态**: ⚠️ 需要扩展到50个

---

##### GameMap 地图实体 [35 tests - 需扩展]

**当前状态**: ⚠️ 需要扩展

##### Squad 班组实体 [25 tests - 需扩展]

**当前状态**: ⚠️ 需要扩展

---

#### 2.2.4 Components组件测试 (预计: 120 tests)

##### HealthComponent 生命值组件 [30 tests]
##### MoraleComponent 士气组件 [30 tests]
##### PositionComponent 位置组件 [20 tests]
##### VisionComponent 视野组件 [20 tests]
##### WeaponComponent 武器组件 [20 tests]

---

### 2.3 Presentation层测试计划

#### 2.3.1 Rendering渲染测试 (预计: 115 tests)

##### SpritesheetParser 精灵解析 [8 tests ✅已冇]
##### PathPreview 路径预览 [16 tests ✅已冇]
##### RangeIndicator 射程圈 [10 tests ✅已冇]
##### Tooltip 提示框 [13 tests ✅已冇]
##### WeatherRenderer 天气渲染 [12 tests - 新增]
##### LightingRenderer 光照渲染 [10 tests - 新增]
##### CC2BottomPanel 底部面板 [18 tests - 新增]
##### AnimationController 动画控制器 [15 tests - 新增]

**重要提示**: Presentation层测试需要Mock pygame surface:

```python
import pytest
from unittest.mock import MagicMock, patch

@pytest.fixture
def mock_pygame_surface():
    """Mock pygame Surface对象"""
    surface = MagicMock(spec=pygame.Surface)
    surface.get_size.return_value = (1024, 768)
    surface.blit = MagicMock()
    return surface

def test_renderer_draws_unit(mock_pygame_surface):
    renderer = Renderer(surface=mock_pygame_surface)
    unit = create_test_unit()

    renderer.draw_unit(unit)

    # 验证blit被调用 (精灵被绘制)
    assert mock_pygame_surface.blit.called
```

---

#### 2.3.2 UI组件测试 (预计: 65 tests)

##### ContextMenu 右键菜单 [12 tests ✅已冇]
##### SquadGroupManager 编组管理 [9 tests ✅已冇]
##### CombatLog 战斗日志 [11 tests ✅已冇]
##### StrategicMapView 战略地图 [9 tests ✅已冇]
##### DeploymentUI 部署界面 [12 tests - 新增]
##### CommandBar 命令栏 [12 tests - 新增]

---

#### 2.3.3 Input/Audio测试 (预计: 40 tests)

##### EnhancedSoundBridge 音效桥接 [10 tests ✅已冇]
##### InputHandler 输入处理 [15 tests - 需修复]
##### InteractionController 交互控制 [15 tests - 需修复]

---

### 2.4 Infrastructure层测试 (预计: 45 tests)

##### SaveSystem 存档系统 [20 tests]
##### Config 配置加载 [10 tests]
##### SecurityHardening 安全加固 [15 tests ✅已冇]

---

### 2.5 Services服务层测试 (预计: 80 tests)

##### GameLoop 游戏循环 [25 tests - 需扩展]
##### CombatDirector 战斗导演 [20 tests - 新增]
##### EventBus 事件总线 [20 tests ✅已冇]
##### SaveController 存档控制器 [15 tests - 新增]

---

## 三、Layer 2: 集成测试 (Integration Tests)

### 3.1 目标与范围

**目标数量**: 40-50 个测试
**执行时间**: < 5 分钟
**重点**: 模块间数据流、EventBus传播、GameLoop协调

#### 测试目录结构

```
tests/integration/
├── test_combat_loop.py              # [✅已有] 战斗循环集成 (15 tests)
├── test_game_loop_integration.py    # [新增] GameLoop完整流程 (10 tests)
├── test_ui_interaction_chain.py     # [新增] UI交互链 (8 tests)
├── test_audio_event_integration.py  # [新增] 音频事件集成 (5 tests)
├── test_campaign_flow.py            # [新增] 战役流程 (8 tests)
└── test_save_load_cycle.py          # [新增] 存档循环 (5 tests)
```

---

### 3.2 关键集成测试场景

#### 3.2.1 GameLoop完整流程集成 (10 tests)

```python
# tests/integration/test_game_loop_integration.py (新增)

class TestGameLoopIntegration:
    """GameLoop子系统间集成测试"""

    @pytest.fixture
    def integrated_game_loop(self):
        """创建完全集成的GameLoop实例"""
        event_bus = EventBus()
        game_map = create_test_map()
        units = create_test_units(count=10)
        camera = Camera(screen_size=(1024, 768))

        # 创建所有依赖
        renderer = EnhancedRenderer(camera=camera)
        window_manager = WindowManager(title="Test", size=(1024, 768))
        state = GameState(game_map=game_map, units=units, camera=camera)

        game_loop = GameLoop(
            renderer=renderer,
            window_manager=window_manager,
            event_bus=event_bus,
            state=state
        )

        # 强制完成所有延迟初始化
        game_loop._initialize_all_subsystems()

        return game_loop

    def test_weather_affects_rendering(self, integrated_game_loop):
        """天气变化影响渲染输出"""
        game_loop = integrated_game_loop

        # 设置雨天
        game_loop.weather_system.set_weather('rain')

        # 运行一帧
        game_loop.update(dt=1/60)
        surface = game_loop.render()

        # 验证渲染器收到了天气信息
        assert game_loop.renderer.last_weather_effect == 'rain_overlay'

    def test_day_night_updates_lighting(self, integrated_game_loop):
        """昼夜循环更新光照"""
        game_loop = integrated_game_loop

        # 推进时间到夜晚
        game_loop.day_night_cycle.advance_to(hour=22.0)

        # 更新
        game_loop.update(dt=1/60)

        # 验证光照修改器被应用
        assert game_loop.renderer.lighting_modifier['brightness'] < 0.7

    def test_eventbus_propagates_attack_event(self, integrated_game_loop):
        """EventBus正确传播攻击事件"""
        game_loop = integrated_game_loop
        event_received = []

        def on_attack(event):
            event_received.append(event)

        game_loop.event_bus.subscribe('unit.attack', on_attack)

        # 模拟攻击
        attacker = game_loop.state.units[0]
        target = game_loop.state.units[1]
        game_loop.combat_director.execute_attack(attacker, target)

        # 验证事件被接收
        assert len(event_received) == 1
        assert event_received[0]['attacker_id'] == attacker.id
        assert event_received[0]['target_id'] == target.id

    def test_sound_bridge_plays_on_event(self, integrated_game_loop):
        """音效桥接在事件触发时播放"""
        game_loop = integrated_game_loop

        with patch.object(game_loop.sound_bridge, 'play_weapon_sound') as mock_play:
            # 触发攻击事件
            game_loop.event_bus.emit('unit.attack', {'weapon_type': 'rifle'})

            # 验证音效播放被调用
            mock_play.assert_called_once_with('rifle')

    # ... 共10个集成测试
```

**优先级**: 🔴 P0 (必须修复)

---

#### 3.2.2 UI交互链测试 (8 tests)

```python
# tests/integration/test_ui_interaction_chain.py (新增)

class TestUIInteractionChain:
    """UI交互链路完整性测试"""

    def test_click_selects_unit_updates_panel(self):
        """点击单位→选中→面板更新"""
        # Setup
        game = setup_integration_test()
        unit = game.state.units[0]

        # Action: 模拟鼠标点击
        mouse_pos = game.camera.world_to_screen(unit.position)
        game.input_handler.handle_mouse_click(mouse_pos, button=LEFT)

        # Assert: 单位被选中
        assert unit.id in game.state.selected_unit_ids

        # Assert: 详情面板更新
        assert game.hud_manager.unit_detail_panel.displayed_unit == unit

    def test_right_click_context_menu_appears(self):
        """右键→上下文菜单弹出"""
        game = setup_integration_test()

        ground_pos = (10, 10)
        screen_pos = game.camera.world_to_screen(ground_pos)

        game.input_handler.handle_mouse_click(screen_pos, button=RIGHT)

        assert game.context_menu.visible is True
        assert game.context_menu.position == screen_pos

    def test_move_command_generates_path_preview(self):
        """Move命令→路径预览显示"""
        game = setup_integration_test()
        unit = select_unit(game, index=0)

        issue_move_command(game, target=(15, 15))

        assert game.path_preview.visible is True
        assert game.path_preview.path_end == (15, 15)

    # ... 共8个交互链测试
```

**优先级**: 🟡 P1 (重要)

---

### 3.3 当前集成测试问题诊断

**test_combat_loop.py** (现有15个测试):

| 问题 | 影响 | 修复方案 |
|------|------|---------|
| CombatResolver未注入 | 5个测试SKIP | 使用Fixture工厂 |
| EventBus未连接 | 3个测试FAIL | 在setup中订阅事件 |
| Mock不完整 | 2个测试ERROR | 补充所有依赖 |

---

## 四、Layer 3: E2E测试 (End-to-End Tests)

### 4.1 ⚠️ 当前最薄弱环节！

**现状**: 17个测试全部ERROR
**目标**: 20个测试全部通过
**这是方案A的P0-3任务！**

---

### 4.2 E2E测试目录结构

```
tests/e2e/
├── conftest.py                    # 全局fixture (pygame环境)
├── test_vertical_slice.py         # [❌12 ERROR] 垂直切片测试
├── test_combat_e2e.py             # [❌5 ERROR] 战斗E2E测试
├── test_campaign_flow_e2e.py      # [新增] 战役流程 (5 tests)
├── test_save_load_e2e.py          # [已有但需修复] 存档E2E (3 tests)
├── test_ai_behaviors_e2e.py       # [已有] AI行为 (4 tests)
└── test_visual_smoke.py           # [已有] 视觉特效 (1 test)
```

---

### 4.3 详细错误分析与修复方案

#### 4.3.1 test_vertical_slice.py (12个ERROR)

**根因分析**:

```python
# 错误模式 1: pygame环境初始化失败
ERROR: SDL_VIDEODRIVER=dummy not available
原因: conftest.py fixture作用域错误 + 缺少headless支持

# 错误模式 2: GameLoop依赖注入断裂
ERROR: AttributeError: 'NoneType' object has no attribute '...'
原因: _post_init__中延迟初始化失败，字段为None

# 错误模式 3: 事件循环超时
ERROR: TimeoutError: GameLoop.run() did not exit
原因: run()缺少退出条件或timeout机制
```

**修复方案**:

**Step 1: 重写conftest.py全局fixture**

```python
# tests/e2e/conftest.py (重写)

import os
import sys
import pytest

# 必须在导入pygame前设置
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "hide")

import pygame


@pytest.fixture(scope="session")
def pygame_env():
    """会话级pygame初始化 (只执行一次)"""
    # 确保只初始化一次
    if not pygame.get_init():
        pygame.init()
        pygame.display.set_mode((800, 600))  # 创建dummy窗口

    yield

    # 清理
    if pygame.get_init():
        pygame.quit()


@pytest.fixture
def e2e_game_loop(pygame_env):
    """每个E2E测试使用的完整GameLoop实例"""
    from tests.e2e.test_helpers import create_complete_game_loop

    game_loop = create_complete_game_loop(
        map_size=(32, 32),
        unit_count=6,  # 3v3小规模
        window_size=(1024, 768)
    )

    yield game_loop

    # 清理资源
    game_loop.cleanup()
```

**Step 2: 创建test_helpers.py工厂函数**

```python
# tests/e2e/test_helpers.py (新建)

import time
from unittest.mock import MagicMock, patch

from pycc2.services.game_loop import GameLoop, GameState
from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.entities.unit import Unit, Faction, UnitType


def create_test_map(width=32, height=32) -> GameMap:
    """创建测试用地图"""
    import numpy as np
    grid = np.zeros((height, width), dtype=np.int8)
    # 混合地形
    grid[::4, ::4] = 3  # 一些树木
    grid[1::5, :] = 1   # 道路

    return GameMap(
        id="e2e_test_map",
        name="E2E Test Map",
        width=width,
        height=height,
        tile_grid=grid
    )


def create_test_units(count=6, map_size=(32, 32)) -> list[Unit]:
    """创建测试单位 (双方各半)"""
    units = []
    mid = count // 2

    for i in range(mid):
        # 盟军单位 (左侧)
        units.append(Unit(
            name=f"Allies Rifle {i}",
            unit_type=UnitType.INFANTRY,
            faction=Faction.ALLIES,
            position=(2 + i*2, 5),
            hp=100,
            max_hp=100
        ))

    for i in range(count - mid):
        # 轴心单位 (右侧)
        units.append(Unit(
            name=f"Axis Rifle {i}",
            unit_type=UnitType.INFANTRY,
            faction=Faction.AXIS,
            position=(map_size[0]-3 - i*2, map_size[1]-5),
            hp=100,
            max_hp=100
        ))

    return units


def create_complete_game_loop(**kwargs) -> GameLoop:
    """
    创建完整依赖链的GameLoop实例
    所有子系统正确初始化和连接
    """
    from pycc2.presentation.rendering.camera import Camera
    from pycc2.presentation.rendering.enhanced_renderer import EnhancedRenderer
    from pycc2.presentation.rendering.window_config import WindowManager
    from pycc2.services.event_bus import EventBus

    map_size = kwargs.get('map_size', (32, 32))
    unit_count = kwargs.get('unit_count', 6)
    window_size = kwargs.get('window_size', (1024, 768))

    # 1. 基础设施
    event_bus = EventBus()
    game_map = create_test_map(*map_size)
    units = create_test_units(unit_count, map_size)
    camera = Camera(screen_size=window_size)

    # 2. 渲染系统
    renderer = EnhancedRenderer(camera=camera)
    window_manager = WindowManager(title="E2E Test", size=window_size)

    # 3. 游戏状态
    state = GameState(
        game_map=game_map,
        units=units,
        camera=camera
    )

    # 4. 创建GameLoop (触发__post_init__)
    game_loop = GameLoop(
        renderer=renderer,
        window_manager=window_manager,
        event_bus=event_bus,
        state=state
    )

    # 5. 手动完成所有延迟初始化
    try:
        game_loop._initialize_subsystems()
    except Exception as e:
        raise RuntimeError(f"GameLoop subsystem initialization failed: {e}") from e

    # 6. 验证关键属性不为None
    assert game_loop.input_handler is not None, "InputHandler not initialized"
    assert game_loop.sound_system is not None, "SoundSystem not initialized"
    assert game_loop.interaction_controller is not None, "InteractionController not initialized"

    return game_loop


def run_game_for_seconds(game_loop: GameLoop, seconds: float = 1.0):
    """运行游戏指定时长 (用于测试稳定性)"""
    import time
    start_time = time.perf_counter()
    frame_count = 0

    try:
        while (time.perf_counter() - start_time) < seconds:
            game_loop.update(dt=1/60)
            game_loop.render()
            frame_count += 1

            if frame_count % 60 == 0:  # 每秒检查一次退出条件
                if not game_loop.state.running:
                    break

    except Exception as e:
        raise RuntimeError(f"Game crashed after {frame_count} frames: {e}") from e

    return frame_count
```

**Step 3: 重写test_vertical_slice.py**

```python
# tests/e2e/test_vertical_slice.py (重写)

import pytest
from tests.e2e.test_helpers import (
    create_complete_game_loop,
    run_game_for_seconds
)


class TestVerticalSlice:
    """
    垂直切片测试 - 验证游戏基本功能端到端
    这些测试确保用户能完成最基本的操作
    """

    @pytest.fixture
    def game(self, pygame_env):
        """每个测试使用全新的GameLoop实例"""
        return create_complete_game_loop()

    def test_vs01_initialization_chain_complete(self, game):
        """VS01: 初始化链完整性 - 所有子系统就绪"""
        # 验证核心组件存在
        assert game.renderer is not None
        assert game.window_manager is not None
        assert game.event_bus is not None
        assert game.state is not None

        # 验证子系统初始化
        assert game.input_handler is not None
        assert game.sound_system is not None
        assert game.interaction_controller is not None

        # 验证游戏状态有效
        assert game.state.running is True
        assert len(game.state.units) > 0
        assert game.state.game_map is not None

    def test_vs02_window_creation_and_display(self, game):
        """VS02: 窗口创建与显示"""
        # 窗口管理器应已创建窗口
        assert game.window_manager.window is not None

        # 可以获取窗口尺寸
        size = game.window_manager.get_window_size()
        assert size[0] > 0 and size[1] > 0

    def test_vs03_units_render_visible(self, game):
        """VS03: 单位渲染可见性"""
        # 渲染一帧
        surface = game.render()

        # 验证表面有效
        assert surface is not None
        assert surface.get_size() == (1024, 768)

        # 验证渲染器记录了单位绘制调用
        # (通过mock或内部计数器)
        assert game.renderer.units_drawn_last_frame > 0

    def test_vs04_camera_wasd_control(self, game):
        """VS04: Camera WASD控制"""
        initial_pos = game.state.camera.position.copy()

        # 模拟按下W键
        game.input_handler.handle_key_down(pygame.K_w)
        game.update(dt=1/60)

        # 相机应该移动了
        new_pos = game.state.camera.position
        assert new_pos != initial_pos

    def test_vs05_zoom_control(self, game):
        """VS05: 缩放控制"""
        initial_zoom = game.state.camera.zoom

        # 模拟鼠标滚轮
        game.input_handler.handle_mouse_wheel(delta=1)  # 放大
        game.update(dt=1/60)

        new_zoom = game.state.camera.zoom
        assert new_zoom > initial_zoom

    def test_vs06_esc_pause_resume(self, game):
        """VS06: ESC暂停/恢复"""
        assert game.state.paused is False

        # 按ESC暂停
        game.input_handler.handle_key_down(pygame.K_ESCAPE)
        game.update(dt=1/60)

        assert game.state.paused is True

        # 再按ESC恢复
        game.input_handler.handle_key_down(pygame.K_ESCAPE)
        game.update(dt=1/60)

        assert game.state.paused is False

    def test_vs07_f11_toggle_fullscreen(self, game):
        """VS07: F11全屏切换"""
        initial_fullscreen = game.window_manager.is_fullscreen()

        # 按F11
        game.input_handler.handle_key_down(pygame.K_F11)
        game.update(dt=1/60)

        assert game.window_manager.is_fullscreen() != initial_fullscreen

    def test_vs08_run_10_seconds_without_crash(self, game):
        """VS08: 运行10秒无崩溃"""
        frame_count = run_game_for_seconds(game, seconds=10.0)

        # 10秒应以60fps运行约600帧
        assert frame_count >= 500  # 允许一些误差
        assert game.state.running is True  # 不应意外退出

    def test_vs09_mouse_click_selects_unit(self, game):
        """VS09: 鼠标点击选择单位"""
        target_unit = game.state.units[0]

        # 将世界坐标转为屏幕坐标
        screen_pos = game.state.camera.world_to_screen(target_unit.position)

        # 模拟点击
        game.input_handler.handle_mouse_click(screen_pos, button=LEFT)
        game.update(dt=1/60)

        # 单位应被选中
        assert target_unit.id in game.state.selected_unit_ids

    def test_vs10_keyboard_shortcuts_respond(self, game):
        """VS10: 键盘快捷键响应"""
        shortcuts_tested = []

        # 测试M键 (Move)
        game.input_handler.handle_key_down(pygame.K_m)
        shortcuts_tested.append('m')

        # 测试A键 (Attack)
        game.input_handler.handle_key_down(pygame.K_a)
        shortcuts_tested.append('a')

        # 测试S键 (Stop)
        game.input_handler.handle_key_down(pygame.K_s)
        shortcuts_tested.append('s')

        # 验证没有崩溃 (快捷键应被注册或安全忽略)
        assert len(shortcuts_tested) == 3

    def test_vs11_minimize_restore_window(self, game):
        """VS11: 最小化/恢复窗口"""
        # 模拟最小化事件
        game.window_manager.handle_event(pygame.Event(pygame.ACTIVEEVENT, {'gain': 0}))
        game.update(dt=1/60)

        # 模拟恢复事件
        game.window_manager.handle_event(pygame.Event(pygame.ACTIVEEVENT, {'gain': 1}))
        game.update(dt=1/60)

        # 游戏应该继续正常运行
        assert game.state.running is True

    def test_vs12_clean_exit_and_cleanup(self, game):
        """VS12: 正常退出清理"""
        # 发送退出事件
        game.state.running = False

        # 运行清理
        game.cleanup()

        # 验证资源释放 (通过mock验证)
        assert game.window_manager.cleaned_up is True
        assert game.renderer.cleaned_up is True
```

**预期结果**: 12/12 PASS ✅

---

#### 4.3.2 test_combat_e2e.py (5个ERROR → 修复后8个PASS)

```python
# tests/e2e/test_combat_e2e.py (重写)

class TestCombatE2E:
    """战斗系统端到端测试"""

    @pytest.fixture
    def combat_game(self, pygame_env):
        """配置好战斗场景的GameLoop"""
        game = create_complete_game_loop(
            unit_count=8,  # 4v4
            map_size=(40, 40)
        )

        # 确保CombatDirector已连接
        assert game.combat_director is not None

        return game

    def test_ce01_attack_deals_damage(self, combat_game):
        """CE01: 攻击造成伤害验证"""
        attacker = combat_game.state.units[0]  # 盟军
        target = combat_game.state.units[4]    # 轴心
        initial_hp = target.hp

        # 执行攻击
        result = combat_game.combat_director.execute_attack(
            attacker=attacker,
            target=target
        )

        # 验证伤害产生
        assert result.success is True
        assert result.damage > 0
        assert target.hp < initial_hp

    def test_ce02_unit_death_on_zero_hp(self, combat_game):
        """CE02: 单位死亡判定"""
        target = combat_game.state.units[4]
        target.hp = 1  # 濒死

        attacker = combat_game.state.units[0]
        combat_game.combat_director.execute_attack(attacker, target, guaranteed_kill=True)

        # 验证死亡状态
        assert target.alive is False
        assert target.hp == 0

        # 验证从活跃列表移除
        assert target not in [u for u in combat_game.state.units if u.alive]

    def test_ce03_victory_all_enemies_eliminated(self, combat_game):
        """CE03: 全歼敌军胜利"""
        # 杀死所有敌方单位
        axis_units = [u for u in combat_game.state.units if u.faction == Faction.AXIS]
        for unit in axis_units:
            unit.hp = 0
            unit.alive = False

        # 检查胜利条件
        victory = combat_game.victory_checker.check_victory(combat_game.state)

        assert victory.victory is True
        assert victory.winner == Faction.ALLIES
        assert victory.reason == 'all_enemies_eliminated'

    def test_ce04_commander_death_defeat(self, combat_game):
        """CE04: 指挥官死亡导致失败"""
        # 找到盟军指挥官
        commander = next((u for u in combat_game.state.units
                         if u.faction == Faction.ALLIES and u.is_commander), None)

        if commander:
            commander.hp = 0
            commander.alive = False

            victory = combat_game.victory_checker.check_victory(combat_game.state)

            assert victory.defeat is True
            assert victory.loser == Faction.ALLIES
            assert victory.reason == 'commander_killed'

    def test_ce05_low_morale causes_rout(self, combat_game):
        """CE05: 士气崩溃导致溃逃"""
        squad = combat_game.state.units[0]

        # 将士气降到极低
        squad.morale_component.current = 5  # 0-100 scale

        # 模拟受到攻击造成的恐慌
        combat_game.morale_sys.apply_suppression(squad, intensity=0.8)

        # 验证溃逃状态
        assert combat_game.morale_sys.is_routing(squad) is True
        assert squad.status == 'routing'

    # 新增测试用例

    def test_ce06_save_mid_combat_reload_state(self, combat_game):
        """CE06: 战斗中途存档后重启恢复"""
        # 进行一些战斗操作
        attacker = combat_game.state.units[0]
        target = combat_game.state.units[4]
        combat_game.combat_director.execute_attack(attacker, target)

        # 存档
        save_data = combat_game.save_controller.create_save(slot=0)

        # 模拟重启 (创建新GameLoop并读档)
        reloaded_game = create_complete_game_loop()
        reloaded_game.save_controller.load_save(slot=0)

        # 验证状态一致
        assert reloaded_game.state.units[4].hp == combat_game.state.units[4].hp
        assert reloaded_game.state.tick == combat_game.state.tick

    def test_ce07_continuous_two_battles(self, combat_game):
        """CE07: 连续两场战斗 (战役流程)"""
        # 完成第一场战斗
        # ... (杀死所有敌人)
        combat_game.end_battle(victory=True)

        # 开始第二场战斗
        combat_game.start_next_battle()

        # 验证新战斗初始化
        assert combat_game.state.battle_number == 2
        assert len(combat_game.state.units) > 0
        assert combat_game.state.running is True

    def test_ce08_ai_seeks_cover_under_fire(self, combat_game):
        """CE08: AI在火力下寻找掩体"""
        axis_unit = combat_game.state.units[4]

        # 模拟盟军开火压制
        allies = [u for u in combat_game.state.units if u.faction == Faction.ALLIES]
        for ally in allies[:2]:
            combat_game.combat_director.execute_attack(ally, axis_unit, suppress_only=True)

        # AI回合更新
        combat_game.ai_service.update(axis_unit)

        # AI应该尝试移动到掩体
        assert axis_unit.seeking_cover is True or axis_unit.moving_to_cover is True
```

**预期结果**: 8/8 PASS ✅ (原有5个 + 新增3个)

---

#### 4.3.3 新增E2E测试场景

##### test_campaign_flow_e2e.py (5个新测试)

```python
# tests/e2e/test_campaign_flow_e2e.py (新增)

class TestCampaignFlowE2E:
    """完整战役流程端到端测试"""

    def test_new_game_to_first_battle(self, pygame_env):
        """新游戏→选阵营→开始→部署→进入战斗"""
        campaign = CampaignFlowTester()

        # 1. 新游戏
        campaign.start_new_game()
        assert campaign.state == 'faction_select'

        # 2. 选择阵营
        campaign.select_faction(Faction.ALLIES)
        assert campaign.state == 'deployment'

        # 3. 部署单位
        campaign.deploy_unit(unit_id=0, position=(5, 5))
        campaign.deploy_unit(unit_id=1, position=(8, 5))
        campaign.complete_deployment()

        assert campaign.state == 'battle'

        # 4. 战斗进行中
        assert campaign.battle_active is True
        assert len(campaign.active_units) > 0

    def test_deployment_drag_and_drop(self, pygame_env):
        """部署阶段拖放单位"""
        campaign = CampaignFlowTester()
        campaign.start_new_game()
        campaign.select_faction(Faction.ALLIES)

        # 模拟拖放操作
        unit_to_deploy = campaign.available_units[0]
        start_screen_pos = campaign.deployment_ui.get_unit_screen_pos(unit_to_deploy)
        end_world_pos = (10, 10)

        campaign.simulate_drag_drop(
            start_pos=start_screen_pos,
            end_pos=end_world_pos
        )

        # 验证单位部署到指定位置
        deployed_unit = campaign.get_deployed_unit(unit_to_deploy.id)
        assert deployed_unit.position == end_world_pos

    def test_battle_end_result_screen(self, pygame_env):
        """战斗结束→结果显示"""
        campaign = CampaignFlowTester()
        campaign.setup_and_start_battle()

        # 模拟胜利条件达成
        campaign.eliminate_all_enemies()

        # 战斗结束
        campaign.end_current_battle()

        # 验证结果显示
        assert campaign.showing_results is True
        assert campaign.result_screen.victory is True
        assert campaign.result_screen.casualties_displayed is True

    def test_result_to_next_battle_transition(self, pygame_env):
        """结果界面→下一场战斗"""
        campaign = CampaignFlowTester()
        campaign.complete_battle_with_victory()

        # 点击"下一场战斗"
        campaign.result_screen.click_next_battle()

        # 验证转换到新战斗
        assert campaign.current_battle_index == 1  # 第二场战斗
        assert campaign.state == 'deployment'  # 回到部署阶段

    def test_campaign_completion(self, pygame_env):
        """完整战役通关"""
        campaign = CampaignFlowTester.setup_full_campaign(total_battles=5)

        # 依次完成所有战斗
        for i in range(5):
            campaign.complete_battle_with_victory()

        # 验证战役完成
        assert campaign.campaign_completed is True
        assert campaign.showing_final_score is True
        assert campaign.final_score.total > 0
```

**优先级**: 🟡 P1 (重要但可在P0之后)

---

## 五、Layer 4: 性能测试 (Performance Tests)

### 5.1 目标

**目标数量**: 10 个benchmark
**执行频率**: 每次CI + 每日手动
**回归阈值**: 性能退化 > 10% 视为失败

### 5.2 测试场景

```python
# tests/benchmark/test_performance.py (扩展)

class TestPerformanceBenchmark:
    """性能基准测试"""

    @pytest.mark.benchmark
    def test_50_units_battle_fps(self, benchmark):
        """50单位战斗场景帧率 (目标≥30fps)"""
        game = create_stress_test_game(unit_count=50)

        fps = benchmark(lambda: run_game_frames(game, frames=600))

        assert fps >= 30, f"FPS too low: {fps:.1f} (target ≥30)"

    @pytest.mark.benchmark
    def test_los_calculation_1000_times(self, benchmark):
        """1000次LOS计算耗时 (目标<100ms)"""
        los_sys = LOSSystem()
        map_data = create_large_map(100, 100)

        time_ms = benchmark(lambda: [
            los_sys.has_los((randint(0,99), randint(0,99)),
                           (randint(0,99), randint(0,99)),
                           map_data)
            for _ in range(1000)
        ])

        assert time_ms < 100, f"LOS calc too slow: {time_ms:.1f}ms (target <100ms)"

    @pytest.mark.benchmark
    def test_large_map_rendering(self, benchmark):
        """大地图(100×100)渲染耗时 (目标<16ms)"""
        renderer = EnhancedRenderer(camera=Camera(screen_size=(1920, 1080)))
        large_map = create_large_map(100, 100)

        time_ms = benchmark(lambda: renderer.render_map(large_map))

        assert time_ms < 16, f"Render too slow: {time_ms:.1f}ms (target <16ms for 60fps)"

    @pytest.mark.benchmark
    def test_memory_usage_under_load(self):
        """内存占用监控 (目标<500MB)"""
        import tracemalloc
        tracemalloc.start()

        game = create_stress_test_game(unit_count=100)
        run_game_frames(game, frames=3600)  # 运行1分钟

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        peak_mb = peak / (1024 * 1024)
        assert peak_mb < 500, f"Memory too high: {peak_mb:.1f}MB (target <500MB)"

    # ... 其他5个性能测试
```

### 5.3 压力测试 (新增)

```python
# tests/benchmark/test_stress_test.py (新增)

class TestStressTest:
    """压力测试 - 发现极限和泄漏"""

    def test_100_units_simultaneous_rendering(self):
        """100单位同屏渲染不崩溃"""
        game = create_game_with_units(100)

        for _ in range(100):  # 运行100帧
            game.update(dt=1/60)
            game.render()

        assert game.state.running is True  # 未崩溃

    def test_one_hour_runtime_memory_leak_detection(self):
        """连续运行1小时检测内存泄漏"""
        import gc
        import tracemalloc

        tracemalloc.start()
        game = create_standard_game()

        # 模拟1小时 (加速时间)
        frame_target = 60 * 60 * 60  # 1小时 × 60fps × 60秒(加速)

        snapshots = []
        for frame_num in range(frame_target):
            game.update(dt=1/60)
            game.render()

            if frame_num % 3600 == 0:  # 每分钟快照
                _, peak = tracemalloc.get_traced_memory()
                snapshots.append(peak)

        tracemalloc.stop()

        # 分析内存增长趋势
        growth_rate = (snapshots[-1] - snapshots[0]) / len(snapshots)

        # 允许每分钟增长 < 1MB (正常缓存增长)
        assert growth_rate < 1*1024*1024, f"Memory leak detected: {growth_rate/1024:.1f}KB/min"

    def test_rapid_click_stress(self):
        """快速点击压力测试 (100次/秒)"""
        game = create_standard_game()

        for _ in range(1000):  # 模拟10秒内1000次点击
            random_pos = (randint(0, 800), randint(0, 600))
            game.input_handler.handle_mouse_click(random_pos, button=LEFT)
            game.update(dt=1/60)  # 每次点击后更新

        # 不应崩溃或卡死
        assert game.state.running is True
```

---

## 六、Layer 5: 视觉回归测试 (Visual Regression Tests)

### 6.1 目标

**自动化截图对比**
**工具**: pytest-splinter + Pillow

### 6.2 测试结构

```
tests/visual/
├── conftest.py                    # 截图fixture
├── references/                    # 基准截图目录 (git tracked)
│   ├── expected_main_menu.png
│   ├── expected_battle_view.png
│   ├── expected_unit_selected.png
│   ├── expected_weather_rain.png
│   └── expected_night_mode.png
├── test_map_rendering.py           # 地图渲染截图对比
├── test_unit_rendering.py          # 单位渲染截图对比
├── test_ui_layout.py               # UI布局截图对比
└── test_weather_effects.py         # 天气效果截图对比
```

### 6.3 实现示例

```python
# tests/visual/test_map_rendering.py (新增)

import pytest
from PIL import Image, ImageChops
import os

VISUAL_THRESHOLD = 0.98  # 98%相似度视为通过


class TestVisualRegressionMap:
    """地图渲染视觉回归测试"""

    @pytest.fixture
    def visual_game(self, pygame_env):
        """用于视觉测试的GameLoop"""
        game = create_complete_game_loop(map_size=(64, 64))
        return game

    def test_terrain_types_correctly_displayed(self, visual_game, tmp_path):
        """不同地形类型正确显示"""
        # 渲染地图
        surface = visual_game.renderer.render_full_map()
        screenshot_path = tmp_path / "actual_terrain.png"
        pygame.image.save(surface, str(screenshot_path))

        # 加载基准图片
        reference_path = Path(__file__).parent / "references" / "expected_terrain_variety.png"
        reference = Image.open(reference_path)
        actual = Image.open(str(screenshot_path))

        # 对比
        diff = ImageChops.difference(reference, actual)
        similarity = 1.0 - (sum(diff.getdata()) / (diff.size[0] * diff.size[1] * 255 * 3))

        assert similarity >= VISUAL_THRESHOLD, \
            f"Visual regression detected! Similarity: {similarity:.2%} (threshold: {VISUAL_THRESHOLD:.0%})\n" \
            f"Diff saved to: {tmp_path / 'diff.png'}"

        # 如果失败，保存差异图供人工审查
        if similarity < VISUAL_THRESHOLD:
            diff.save(tmp_path / 'diff.png')

    def test_buildings_trees_roads_visible(self, visual_game, tmp_path):
        """建筑物/树木/道路可见"""
        # 类似上面的测试逻辑
        pass

    def test_weather_effects_applied(self, visual_game, tmp_path):
        """天气效果应用正确"""
        # 设置雨天
        visual_game.weather_system.set_weather('rain')
        visual_game.update(dt=1/60)

        surface = visual_game.render()
        # 与基准截图对比...
        pass
```

### 6.4 CI中的视觉测试配置

```yaml
# .github/workflows/visual_regression.yml
name: Visual Regression

on: [pull_request]

jobs:
  visual-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v3
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -e ".[dev]"
          pip install pytest-splinter pillow xvfb-run
      - name: Run visual tests
        run: xvfb-run pytest tests/visual/ -v --visual-baseline
      - name: Upload diffs
        if: failure()
        uses: actions/upload-artifact@v3
        with:
          name: visual-diffs
          path: tests/visual/diff_*.png
```

---

## 七、测试数据管理

### 7.1 Fixture工厂模式

```python
# tests/fixtures/factories.py (新建)

"""
测试数据工厂 - 集中管理所有测试对象的创建
保证测试数据一致性和隔离性
"""

import random
from typing import Optional

from pycc2.domain.entities.unit import Unit, Faction, UnitType
from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.value_objects.tile_coord import TileCoord


class UnitFactory:
    """单位创建工厂"""

    @staticmethod
    def create_rifleman(
        faction: Faction = Faction.ALLIES,
        position: tuple[int, int] = (0, 0),
        hp: int = 100
    ) -> Unit:
        """创建标准步枪班"""
        return Unit(
            name=f"{faction.value.capitalize()} Rifle Squad",
            unit_type=UnitType.INFANTRY,
            faction=faction,
            position=position,
            hp=hp,
            max_hp=100
        )

    @staticmethod
    def create_tank(
        faction: Faction = Faction.ALLIES,
        position: tuple[int, int] = (0, 0),
        tank_type: str = 'medium'
    ) -> Unit:
        """创建坦克单位"""
        return Unit(
            name=f"{faction.value.capitalize()} {tank_type.title()} Tank",
            unit_type=UnitType.VEHICLE,
            faction=faction,
            position=position,
            hp=150,
            max_hp=150
        )

    @staticmethod
    def create_officer(
        faction: Faction = Faction.ALLIES,
        position: tuple[int, int] = (0, 0)
    ) -> Unit:
        """创建军官"""
        unit = UnitFactory.create_rifleman(faction, position)
        unit.is_commander = True
        unit.name = f"{faction.value.capitalize()} Officer"
        return unit

    @staticmethod
    def create_wounded_unit(
        faction: Faction = Faction.ALLIES,
        hp_percent: float = 0.5
    ) -> Unit:
        """创建受伤单位"""
        unit = UnitFactory.create_rifleman(faction)
        unit.hp = int(unit.max_hp * hp_percent)
        return unit

    @staticmethod
    def create_dead_unit(faction: Faction = Faction.ALLIES) -> Unit:
        """创建死亡单位"""
        unit = UnitFactory.create_rifleman(faction)
        unit.hp = 0
        unit.alive = False
        return unit


class MapFactory:
    """地图创建工厂"""

    @staticmethod
    def create_open_map(width: int = 32, height: int = 32) -> GameMap:
        """创建开阔地图 (全草地)"""
        import numpy as np
        grid = np.zeros((height, width), dtype=np.int8)
        return GameMap(
            id="test_open",
            name="Open Terrain",
            width=width,
            height=height,
            tile_grid=grid
        )

    @staticmethod
    def create_arnhem_map() -> GameMap:
        """加载真实的Arnhem地图数据"""
        # 从JSON文件加载
        import json
        map_path = Path(__file__).parent.parent.parent / "data" / "maps" / "arnhem.json"
        with open(map_path) as f:
            map_data = json.load(f)
        return GameMap.from_dict(map_data)

    @staticmethod
    def create_map_with_features(
        width: int = 40,
        height: int = 40,
        forests: list = None,
        roads: list = None,
        buildings: list = None
    ) -> GameMap:
        """创建有特定特征的地图"""
        grid = np.zeros((height, width), dtype=np.int8)

        # 添加森林
        for rect in (forests or []):
            x1, y1, x2, y2 = rect
            grid[y1:y2, x1:x2] = 9  # 森林地形ID

        # 添加道路
        # ...

        # 添加建筑
        # ...

        return GameMap(id="custom", name="Custom Map", width=width, height=height, tile_grid=grid)


class BattleFactory:
    """战斗场景工厂"""

    @staticmethod
    def create_small_skirmish(
        allies_count: int = 3,
        axis_count: int = 3,
        map_size: tuple = (32, 32)
    ) -> 'BattleState':
        """创建3v3小规模遭遇战"""
        units = []

        for i in range(allies_count):
            units.append(UnitFactory.create_rifleman(
                faction=Faction.ALLIES,
                position=(2 + i*3, 5)
            ))

        for i in range(axis_count):
            units.append(UnitFactory.create_rifleman(
                faction=Faction.AXIS,
                position=(map_size[0]-3 - i*3, map_size[1]-5)
            ))

        return BattleState(
            units=units,
            game_map=MapFactory.create_open_map(*map_size)
        )

    @staticmethod
    def create_asymmetric_battle() -> 'BattleState':
        """创建非对称战斗 (例如: 5步兵 vs 2坦克)"""
        allies = [UnitFactory.create_rifleman(Faction.ALLIES, pos=(i*2, 5)) for i in range(5)]
        axis = [
            UnitFactory.create_tank(Faction.AXIS, pos=(20, 15)),
            UnitFactory.create_tank(Faction.AXIS, pos=(25, 15))
        ]

        return BattleState(units=allies + axis, game_map=MapFactory.create_open_map())
```

---

### 7.2 测试数据隔离策略

```python
# tests/conftest.py (全局conftest)

import pytest
import tempfile
import shutil
from pathlib import Path


@pytest.fixture(autouse=True)
def isolated_temp_dir(tmp_path):
    """
    每个测试使用独立的临时目录
    自动清理，避免测试间干扰
    """
    original_cwd = Path.cwd()
    tmp_path.mkdir(exist_ok=True)

    # 切换到临时目录
    import os
    os.chdir(tmp_path)

    yield tmp_path

    # 恢复原目录并清理
    os.chdir(original_cwd)


@pytest.fixture
def clean_save_dir(tmp_path):
    """干净的存档目录"""
    save_dir = tmp_path / "saves"
    save_dir.mkdir()
    return save_dir


@pytest.fixture
def seed_random(rng_seed: int = 42):
    """固定随机种子以保证测试可重现"""
    import random
    random.seed(rng_seed)
    # 也设置numpy种子 (如果使用)
    try:
        import numpy as np
        np.random.seed(rng_seed)
    except ImportError:
        pass
```

---

## 八、持续集成 (CI) 配置

### 8.1 GitHub Actions工作流

```yaml
# .github/workflows/test.yml (更新)

name: PyCC2 Test Suite

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  # Job 1: 单元测试 (快速)
  unit-tests:
    name: Unit Tests
    runs-on: ubuntu-latest
    timeout-minutes: 10

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python 3.11
        uses: actions/setup-python@v3
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"
          sudo apt-get update && sudo apt-get install -y xvfb libsdl2-dev

      - name: Run unit tests with coverage
        run: |
          xvfb-run pytest tests/unit/ -v \
            --cov=src/pycc2 \
            --cov-report=xml \
            --cov-report=term-missing \
            --junitxml=junit-unit.xml \
            --strict-markers

      - name: Upload coverage report
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: coverage-report
          path: coverage.xml

  # Job 2: 集成测试
  integration-tests:
    name: Integration Tests
    runs-on: ubuntu-latest
    needs: unit-tests
    timeout-minutes: 15

    steps:
      - uses: actions/checkout@v3
      # ... 类似unit-tests的设置 ...
      - name: Run integration tests
        run: |
          xvfb-run pytest tests/integration/ -v \
            --cov=src/pycc2 \
            --cov-report=xml \
            --junitxml=junit-integration.xml

  # Job 3: E2E测试 (需要图形环境)
  e2e-tests:
    name: E2E Tests
    runs-on: ubuntu-latest
    needs: integration-tests
    timeout-minutes: 20

    steps:
      - uses: actions/checkout@v3
      # ... 设置 ...
      - name: Run E2E tests
        run: |
          xvfb-run pytest tests/e2e/ -v \
            --tb=long \
            --junitxml=junit-e2e.xml

  # Job 4: 性能基准
  performance-benchmark:
    name: Performance Benchmark
    runs-on: ubuntu-latest
    needs: e2e-tests
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'

    steps:
      - uses: actions/checkout@v3
      # ... 设置 ...
      - name: Run performance benchmarks
        run: |
          pytest tests/benchmark/ -v --benchmark-save=data

      - name: Compare with baseline
        run: |
          pytest tests/benchmark/ --benchmark-compare

  # Job 5: 视觉回归 (PR时)
  visual-regression:
    name: Visual Regression Check
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'

    steps:
      - uses: actions/checkout@v3
      # ... 设置 ...
      - name: Run visual regression tests
        run: |
          xvfb-run pytest tests/visual/ -v --visual-update

      - name: Upload diff images
        if: failure()
        uses: actions/upload-artifact@v3
        with:
          name: visual-diffs
          path: tests/visual/diff_*.png
```

### 8.2 测试门禁规则

```yaml
# 允许合并的条件 (ALL must pass):
merge_conditions:
  unit_tests:
    - status: passed
    - failures: 0
    - errors: 0
    - coverage_threshold: 85  # 新增代码 >90%

  integration_tests:
    - status: passed
    - failures: 0
    - errors: 0

  e2e_tests:
    - status: passed
    - errors: 0  # E2E不允许任何error!

  code_quality:
    - no_new_flake8_warnings: true
    - no_new_mypy_errors: true
    - security_scan_passed: true

# 阻止合并的情况 (ANY blocks merge):
block_merge_if:
  - any_p0_test_failure: true
  - coverage_dropped_more_than: 0.02  # 2%
  - new_deprecated_api_usage: true
  - performance_regression_exceeded: 0.10  # 10%
  - visual_regression_detected: true
```

---

## 九、缺陷管理流程

### 9.1 Bug严重级别定义

```python
class BugSeverity:
    """
    Bug严重级别标准
    """

    P0_CRITICAL = {
        'name': 'Critical',
        'description': '游戏无法启动 / 核心流程崩溃 / 数据丢失',
        'response_time': '< 1 hour',
        'fix_deadline': 'today',
        'examples': [
            'GameLoop无法初始化',
            '存档损坏无法读取',
            '主菜单点击无响应',
            '战斗中必现崩溃'
        ]
    }

    P1_MAJOR = {
        'name': 'Major',
        'description': '主要功能不可用 / 明显错误行为 / 性能严重下降',
        'response_time': '< 4 hours',
        'fix_deadline': '2 days',
        'examples': [
            '攻击命令不造成伤害',
            '单位无法移动',
            'UI面板不显示',
            'FPS < 15 in normal gameplay'
        ]
    }

    P2_MINOR = {
        'name': 'Minor',
        'description': '功能部分异常 / UI小问题 / 不影响核心玩法',
        'response_time': '< 24 hours',
        'fix_deadline': '1 week',
        'examples': [
            'Tooltip文字截断',
            '小地图刷新延迟',
            '按钮hover颜色错误',
            '拼写错误'
        ]
    }

    P3_TRIVIAL = {
        'name': 'Trivial',
        'description': '美观问题 / 文字错别字 / 建议改进',
        'response_time': 'next sprint',
        'fix_deadline': 'backlog',
        'examples': [
            '图标像素略偏',
            '说明文字不够清晰',
            '建议添加键盘快捷键提示'
        ]
    }
```

### 9.2 当前Bug清单（来自审计）

#### 必须修复 (P0) - 阻塞方案A

| Bug ID | 描述 | 组件 | 状态 | 指派给 |
|--------|------|------|------|--------|
| BUG-001 | `_render_hud()`空实现 | GameLoop | 🔴 Open | Solo-Coder |
| BUG-002 | SpritesheetParser未集成 | Rendering | 🔴 Open | Solo-Coder |
| BUG-003 | EnhancedSoundBridge未接入EventBus | Audio | 🔴 Open | Solo-Coder |
| BUG-004 | test_vertical_slice 12个ERROR | E2E Tests | 🔴 Open | Test Expert + Coder |
| BUG-005 | test_combat_e2e 5个ERROR | E2E Tests | 🔴 Open | Test Expert + Coder |
| BUG-006 | 6个单元测试失败 | Unit Tests | 🔴 Open | Solo-Coder |

#### 应该修复 (P1) - 影响体验

| Bug ID | 描述 | 组件 | 状态 | 指派给 |
|--------|------|------|------|--------|
| BUG-007 | macOS Retina缩放bug | DisplayConfig | 🟡 Open | Coder |
| BUG-008 | LOS计算每帧重复无缓存 | LOSSystem | 🟡 Open | Architect + Coder |
| BUG-009 | quick_implementations.py用Python循环 | Performance | 🟡 Open | Coder |

#### 建议改进 (P2) - 锦上添花

| Bug ID | 描述 | 组件 | 状态 |
|--------|------|------|------|
| BUG-010 | 缺少性能监控工具 | DevTools | 📋 Backlog |
| BUG-011 | 缺少热重载开发模式 | DevTools | 📋 Backlog |
| BUG-012 | Mod支持框架缺失 | Infrastructure | 📋 Backlog |

---

### 9.3 Bug生命周期

```
New → Triaged (评估严重级别)
  → In Development (开始修复)
  → Code Review (代码审查)
  → QA Verification (测试验证)
  → Closed (关闭)
    OR
  → Reopened (复现)
  → In Development (重新修复)
```

---

## 十、测试自动化成熟度模型

### 10.1 当前阶段: Level 2 (部分自动化)

**已达成的能力**:
- ✅ 单元测试自动化 (2200+ tests, CI运行)
- ✅ 基本linting (flake8/mypy)
- ⚠️ 集成测试部分自动化 (部分需手动mock)
- ❌ E2E测试大量失败 (需要修复环境)
- ❌ 视觉回归测试未建立
- ❌ 性能测试未纳入CI常规

### 10.2 目标阶段: Level 4 (持续自动化)

**目标能力矩阵**:

| 能力 | L1 (手动) | L2 (当前) | L3 (目标) | L4 (理想) |
|------|-----------|-----------|-----------|-----------|
| **单元测试** | 手动运行 | CI自动 | ✓ | ✓ |
| **集成测试** | 无 | 部分 | CI自动 | ✓ |
| **E2E测试** | 无 | 失败中 | CI自动 | ✓ |
| **视觉回归** | 无 | 无 | PR触发 | 每次提交自动 |
| **性能基线** | 无 | 手动 | 定期 | 每次提交自动对比 |
| **覆盖率门禁** | 无 | 报告 | 警告 | 强制执行 |
| **安全扫描** | 无 | 部分 | PR触发 | 每次 |
| **Bug预测** | 无 | 无 | 无 | ML辅助 |

### 10.3 升级路径

**Week 1-2 (当前冲刺)**:
- [ ] 修复所有E2E错误 (达到Level 3基础)
- [ ] 建立基本CI流水线 (unit + integration)

**Week 3-4**:
- [ ] 加入性能基准测试
- [ ] 设置覆盖率门禁 (85%)

**Month 2**:
- [ ] 实现视觉回归测试框架
- [ ] 安全扫描自动化

**Month 3+**:
- [ ] ML辅助Bug预测 (可选)
- [ ] 全量测试并行化 (<5分钟完成全部)

---

## 十一、执行时间表 (测试专项)

### Phase 1: E2E紧急修复 (Day 1-3)

```
Day 1 (今天):
  ├─ 上午: 分析17个E2E错误的根因
  ├─ 下午: 重写conftest.py + test_helpers.py
  └─ 晚上: 修复test_vertical_slice.py前6个测试

Day 2:
  ├─ 上午: 修复test_vertical_slice.py后6个测试
  ├─ 下午: 修复test_combat_e2e.py 5个错误
  └─ 晚上: 新增3个combat E2E测试

Day 3:
  ├─ 上午: 运行全量E2E确认0 error
  ├─ 下午: 编写test_campaign_flow_e2e.py
  └─ 晚上: 文档化E2E最佳实践
```

**里程碑**: Day 3结束时，`pytest tests/e2e/ -v` 全部通过 ✅

---

### Phase 2: 单元测试扩充 (Day 4-6 并行)

```
Day 4:
  ├─ 补充Domain层测试至目标数量
  │   ├─ LOS System: +55 tests
  │   ├─ Swiss Cheese Damage: +40 tests
  │   ├─ Morale System: +30 tests
  │   └─ Pathfinder: +25 tests
  └─ 修复6个失败的单元测试

Day 5:
  ├─ 补充Presentation层测试
  │   ├─ Weather Renderer: +12 tests
  │   ├─ Lighting Renderer: +10 tests
  │   ├─ CC2 Bottom Panel: +18 tests
  │   └─ Animation Controller: +15 tests
  └─ 补充Services层测试 (+55 tests)

Day 6:
  ├─ 运行全量单元测试 (>2700)
  ├─ 确保覆盖率 >90%
  └─ 生成覆盖率报告
```

**里程碑**: Day 6结束时，2700+单元测试全部通过，覆盖率>90% ✅

---

### Phase 3: 集成测试建设 (Day 7-8)

```
Day 7:
  ├─ 编写GameLoop集成测试 (10 tests)
  ├─ 编写UI交互链测试 (8 tests)
  └─ 编写音频事件集成测试 (5 tests)

Day 8:
  ├─ 编写战役流程集成测试 (8 tests)
  ├─ 编写存档循环测试 (5 tests)
  └─ 运行全量集成测试 (45+ tests)
```

**里程碑**: Day 8结束时，45+集成测试全部通过 ✅

---

### Phase 4: 性能与视觉 (Day 9-10)

```
Day 9:
  ├─ 实现10个性能基准测试
  ├─ 实现3个压力测试
  └─ 建立性能基线数据

Day 10:
  ├─ 搭建视觉回归测试框架
  ├─ 生成8张基准截图
  ├─ 编写4个视觉测试用例
  └─ 集成到CI流水线
```

**里程碑**: Day 10结束时，完整的5层测试体系建立 ✅

---

### Phase 5: CI成熟化 (Day 11-12)

```
Day 11:
  ├─ 完善.github/workflows/test.yml
  ├─ 配置测试门禁规则
  ├─ 本地CI测试运行
  └─ 修复CI环境问题

Day 12:
  ├─ 全量测试最终验收
  ├─ 性能基线归档
  ├─ 测试策略文档最终版
  └─ 复盘总结
```

**最终里程碑**: Day 12结束时，
- 2700+ 单元测试 ✅
- 45+ 集成测试 ✅
- 20+ E2E测试 ✅
- 10+ 性能测试 ✅
- 8+ 视觉回归测试 ✅
- **总计: ~2780+ 测试，全自动CI运行，0失败**

---

## 十二、成功指标

### 12.1 量化指标

| 指标 | 当前值 | Week 1目标 | Week 2目标 | 最终目标 |
|------|--------|-----------|-----------|---------|
| **单元测试通过率** | 99.7% (6 fail) | 100% | 100% | 100% |
| **E2E测试通过率** | 0% (17 error) | 100% | 100% | 100% |
| **测试总数量** | ~2220 | 2400 | 2600 | 2780+ |
| **代码覆盖率** | ~75% | 85% | 88% | 90%+ |
| **执行时间(全量)** | ~5min | 15min | 20min | 25min |
| **CI成功率** | N/A | 90% | 95% | 99%+ |
| **平均修复时间(MTTR)** | N/A | <4h | <2h | <1h |

### 12.2 质量门禁

```bash
# 发布前的强制检查清单
echo "=== Pre-release Quality Gate ==="

# 1. 全量测试
pytest tests/ --strict-markers -q
assert $? -eq 0  # 必须全通过

# 2. 覆盖率检查
coverage report --fail-under=85
assert $? -eq 0  # 必须>85%

# 3. E2E特别检查
pytest tests/e2e/ -v
assert $(grep -c "PASSED" pytest_output) -ge 20  # 至少20个passed

# 4. 性能回归检查
pytest tests/benchmark/ --benchmark-compare
assert no_regression_exceeds_10%

# 5. 安全扫描
bandit -r src/pycc2/
assert no_high_or_medium_confirmed

echo "=== Quality Gate PASSED === ✅"
```

---

## 附录

### A. 测试命令速查

```bash
# 运行特定层级测试
pytest tests/unit/ -q                          # 单元测试 (~3min)
pytest tests/integration/ -v                   # 集成测试 (~5min)
pytest tests/e2e/ -v --tb=long                # E2E测试 (~10min)
pytest tests/benchmark/ -v                     # 性能测试 (~2min)
pytest tests/visual/ -v                        # 视觉回归 (~5min)

# 全量测试
pytest tests/ -v --co                         # 列出所有测试 (不运行)
pytest tests/ -n auto                          # 自动并行 (需要pytest-xdist)

# 覆盖率
pytest tests/unit/ --cov=src/pycc2 --cov-report=html
open htmlcov/index.html                       # 查看HTML报告

# 特定模块
pytest tests/unit/domain/systems/ -v          # 系统组件测试
pytest tests/unit/presentation/rendering/ -v  # 渲染器测试

# 失败重试 (flaky test)
pytest tests/e2e/ --reruns 2                  # 失败自动重试2次

# 调试
pytest tests/e2e/test_vertical_slice.py::TestVerticalSlice::test_vs01 -vs  # 单个测试verbose
```

### B. 常见问题排查

**Q: pygame初始化失败?**
```bash
export SDL_VIDEODRIVER=dummy
export SDL_AUDIODRIVER=dummy
pytest tests/e2e/
```

**Q: E2E测试超时?**
```bash
# 增加timeout
pytest tests/e2e/ --timeout=300  # 需要pytest-timeout
```

**Q: 内存不足?**
```bash
# 减少并行数
pytest tests/ -n 2  # 默认auto可能太多
```

**Q: 导入错误?**
```bash
# 确保安装了dev依赖
pip install -e ".[dev]"
```

### C. 相关文档索引

- [PLAN_A_EXECUTION.md](./PLAN_A_EXECUTION.md) - 实施计划
- [UI_VISUAL_DESIGN_SPEC.md](./UI_VISUAL_DESIGN_SPEC.md) - 视觉设计规范
- [DEVSQUAD_REVIEW.md](./DEVSQUAD_REVIEW.md) - 技术审查
- [GAP_ANALYSIS.md](./GAP_ANALYSIS.md) - 差距分析

---

## 审批签字

- [ ] **Architect**: ________________ 日期: _________
  - 审查测试架构合理性
  - 确认性能预算可行
  - 评估CI配置正确性

- [ ] **Product Manager**: ________________ 日期: _________
  - 确认验收标准满足用户需求
  - 批准E2E场景覆盖核心流程
  - 同意发布门禁规则

- [ ] **Solo-Coder**: ________________ 日期: _________
  - 评估测试实现工作量
  - 确认Mock/Fixture策略可行
  - 承诺配合修复Bug

- [ ] **DevOps**: ________________ 日期: _________
  - 审核CI/CD配置
  - 确认环境搭建可行
  - 承诺提供测试基础设施

**文档生效条件**: 全员签字 + 首次CI全绿运行**

---

*文档作者: DevSquad Test Expert Role*
*版本: v1.0*
*下次审查日期: Day 3 (E2E修复完成后)*
*相关文档: [PLAN_A_EXECUTION.md](./PLAN_A_EXECUTION.md) | [UI_VISUAL_DESIGN_SPEC.md](./UI_VISUAL_DESIGN_SPEC.md)*
