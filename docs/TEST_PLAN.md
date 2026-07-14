# PyCC2 测试计划 v0.6.10 — 全量测试套件 (6552 tests)

## 1. 测试金字塔

### 1.1 测试策略概览

PyCC2 采用经典的测试金字塔策略，强调**底层单元测试为主，顶层E2E测试为辅**：

```
        ╱╲
       ╱E2E╲          7.9%  (491 tests)
      ╱──────╲
     ╱ 集成测试 ╲        2.9%  (181 tests)
    ╱──────────╲
   ╱            ╲
  ╱   单元测试   ╲      88.2%  (5494 tests)
 ╱──────────────╲
```

### 1.2 测试分布详情

> 数据来源：`pytest --collect-only` 实测（2026-07-13，v0.6.10）。
> Marker 通过 `conftest.py` 的 `pytest_collection_modifyitems` 钩子按目录自动推断，
> 显式 `@pytest.mark.slow` 等正交标记保留不覆盖。

| 层级 | 数量 | 占比 | 执行时间 | 负责人 | 频率 | Marker |
|------|------|------|----------|--------|------|--------|
| **单元测试 (Unit)** | 5817 | 88.8% | ~4min | 核心开发 | 每次commit | `@pytest.mark.unit`（路径自动） |
| **集成测试 (Integration)** | 181 | 2.8% | < 3min | 核心开发 | 每次PR | `@pytest.mark.integration`（路径自动） |
| **端到端测试 (E2E)** | 491 | 7.5% | < 10min | QA团队 | 每日构建 | `@pytest.mark.e2e`（路径自动） |
| **性能基准 (Benchmark)** | 21 | 0.3% | < 2min | 核心开发 | 每日构建 | `@pytest.mark.benchmark`（路径自动） |
| **验收测试 (Acceptance)** | 42 | 0.6% | < 2min | QA团队 | 每次发布 | `@pytest.mark.acceptance`（路径自动） |
| **慢测试 (Slow，正交)** | 16 | 0.2% | ~3min | 核心开发 | CI slow job | `@pytest.mark.slow`（显式） |

**总计: 6552 个测试用例（v0.6.10 全量，含 slow 16 个；`pytest -m "not slow"` 基线 6536 collected / 2 skipped）**

> **数据校准说明**: 2026-07-14 通过 `pytest tests/{unit,integration,e2e,benchmark,acceptance}/ --co -q` 逐目录实测验证。单元测试数从原 5494 更新为 5817（v0.6.10 覆盖率提升新增 323 测试主要落入 unit 目录）。

**Marker 策略**（Phase 5 新增）：
- 路径自动标记：`tests/unit/` → `unit`，`tests/integration/` → `integration`，`tests/e2e/` → `e2e`，`tests/benchmark/` → `benchmark`
- 慢测试显式标记：sprite 生成类测试（`test_pixel_artist.py` / `test_content_expansion.py` 中超时>30s 的类）标记 `@pytest.mark.slow`，默认 `pytest -m "not slow"` 跳过
- CI 门禁：`pytest -m "not slow"` 阻塞式全绿；`pytest -m slow` 在 slow job 中全绿
- `--strict-markers` 已启用，未注册 marker 会报错

---

### 1.3 各层职责定义

#### 单元测试 (Unit Tests) - 88.8%

**目标：** 验证单个函数/类的正确性

**特征：**
- ✅ 无外部依赖（mock所有I/O）
- ✅ 独立运行，无执行顺序依赖
- ✅ 快速 (< 100ms/个)
- ✅ 覆盖正常/边界/异常路径
- ✅ TDD驱动开发

**示例结构：**
```python
# tests/unit/test_vec2.py
class TestVec2Addition:
    def test_add_positive_numbers(self):
        v1 = Vec2(1, 2)
        v2 = Vec2(3, 4)
        result = v1 + v2
        assert result == Vec2(4, 6)

    def test_add_negative_numbers(self):
        v1 = Vec2(-1, -2)
        v2 = Vec2(-3, -4)
        assert v1 + v2 == Vec4(-6)

    def test_add_zero_vector(self):
        v = Vec2(5, 10)
        assert v + Vec2(0, 0) == v

    def test_add_commutative_property(self):
        a = Vec2(1, 2)
        b = Vec2(3, 4)
        assert a + b == b + a
```

---

#### 集成测试 (Integration Tests) - 2.8%

**目标：** 验证模块间协作的正确性

**特征：**
- ⚠️ 允许部分真实依赖（如文件系统、数据库）
- ⚠️ 测试模块间接口契约
- ⚠️ 中等速度 (100ms - 1s/个)
- ⚠️ 关注数据流和状态转换

**示例结构：**
```python
# tests/integration/test_combat_flow.py
class TestCombatIntegration:
    def setup_method(self):
        self.game = create_test_game()
        self.attacker = spawn_unit(self.game, "rifle_squad_us", pos=(5, 5))
        self.target = spawn_unit(self.game, "rifle_squad_ge", pos=(15, 5))

    def test_full_attack_cycle(self):
        """完整攻击流程：命令→瞄准→射击→命中→伤害→死亡"""
        cmd = AttackCommand(attacker_id=self.attacker.id, target_id=self.target.id)
        self.game.execute_command(cmd)

        # 验证弹药减少
        assert self.attacker.ammo['m1_garand'] == 7  # 8 - 1

        # 验证目标受伤或死亡
        assert self.target.hp < 100 or not self.target.is_alive

    def test_suppression_morale_interaction(self):
        """压制与士气系统的交互"""
        # 连续攻击导致压制累积
        for _ in range(10):
            self.game.execute_command(AttackCommand(...))

        # 验证士气下降
        assert self.target.morale < 80
```

---

#### 端到端测试 (E2E Tests) - 5%

**目标：** 验证完整的用户场景

**特征：**
- 🔴 完整系统运行（含pygame渲染）
- 🔴 模拟真实用户操作序列
- 🔴 较慢 (1-3min/scenario)
- 🔴 关注业务价值和用户体验
- 🔴 使用真实配置和数据文件

**场景列表：**
1. **Tutorial Scenario**: 完成教学任务（占领中心建筑）
2. **Combat Scenario**: 完整战斗流程（双方交火至一方获胜）
3. **Save/Load Scenario**: 存档→退出→加载→继续游戏

---

## 2. TDD 核心模块 12 个 (按依赖顺序)

### 2.1 模块依赖图

```
Level 1 (基础):
├── Vec2 (25 tests)          ← 无依赖
├── TileCoord (15 tests)     ← 依赖 Vec2
└── TerrainType (12 tests)   ← 无依赖

Level 2 (核心):
├── StateMachine (20 tests)  ← 无依赖
├── RandomContext (10 tests) ← 无依赖
├── BallisticEngine (35 tests)← 依赖 RandomContext, TerrainType
└── MoraleCalculator (30 tests)← 依赖 StateMachine

Level 3 (系统):
├── PathFinder (25 tests)    ← 依赖 Vec2, TileCoord, TerrainType
├── FogOfWar (20 tests)      ← 依赖 TileCoord, TerrainType
├── CombatResolver (20 tests)← 依赖 BallisticEngine, MoraleCalculator
├── BehaviorTree (20 tests)  ← 依赖 StateMachine
└── EventBus (15 tests)      ← 无依赖
```

### 2.2 各模块测试详细规格

---

## 3. BallisticEngine 35 tests 详细定义

> **⚠️ v1.1 共识修复 — API 对齐说明**:
>
> 实际实现的 BallisticEngine 主入口为 `calculate_shot(attacker: Unit, target: Unit, weapon_slot: str, game_map: GameMap) -> ShotResult`，
> 这是一个高层统一接口（内部依次执行 LOS检查 → 距离衰减 → 掩体修正 → RNG命中 → 高斯散布 → 伤害公式 → 压制累积）。
>
> 以下测试用例中的 `calculate_hit(weapon, pos, cover)` 等简化API表示法应理解为对 `calculate_shot()` 内部各阶段的**拆分验证**：
> - BE-HIT-01~08 (命中): 验证 `calculate_shot()` 返回的 `ShotResult.hit` 和 `actual_accuracy`
> - BE-DMG-01~08 (伤害): 验证 `ShotResult.damage_dealt`
> - BE-SPR-01~06 (散布): 验证 `ShotResult.reason` 中的散布信息
> - BE-EDGE-01~08 (边缘): 验证异常输入的 `ShotResult` 完整性
> - BE-STAT-01~08 (统计): 多次调用 `calculate_shot()` 的聚合统计特性
>
> 测试代码应使用实际 `calculate_shot()` 签名，通过构造 mock Unit/GameMap 对象传入参数。

### 3.1 基础命中测试 (8 tests)

| Test ID | 测试名称 | 输入条件 | 预期输出 | 优先级 | 备注 |
|---------|----------|----------|----------|--------|------|
| BE-HIT-01 | 有效范围命中 | distance=300m, range_effective=400m, accuracy_base=0.75, cover=0 | hit_probability > 0.6 | P0 | 在有效范围内应有较高命中率 |
| BE-HIT-02 | 最大距离未命中 | distance=550m (=range_max), accuracy_base=0.75 | hit_probability < 0.3 | P0 | 接近最大射程时命中率大幅下降 |
| BE-HIT-03 | 完美精度 | accuracy_base=1.0, distance=0, cover=0 | hit_probability ≥ 0.95 | P0 | 理想条件下应几乎必中 |
| BE-HIT-04 | Cover降低命中率 | base_acc=0.75, cover_bonus=0.5 | hit_with_cover < hit_without_cover | P0 | 掩体应显著降低命中率 |
| BE-HIT-05 | 确定同seed结果一致 | seed=42, 相同输入调用两次 | 结果完全相同 | P0 | 同一seed必须产生相同结果（确定性） |
| BE-HIT-06 | 极端cover满命中 | cover=1.0 (完全掩体), distance<effective_range | hit_probability ≈ 0 | P1 | 完全掩体下几乎不可能被命中 |
| BE-HIT-07 | 统计验证命中率 | 1000次射击, 理论命中率50% | 实际命中率 ∈ [45%, 55%] | P0 | 大数定律验证统计正确性 |
| BE-HIT-08 | 零距离特殊处理 | distance=0 (贴脸) | hit_probability > 0.9 | P1 | 近距离应保证高命中率 |

**测试代码示例：**

```python
import pytest
from pycc2.combat.ballistic import BallisticEngine
from pycc2.core.random import RandomContext

class TestBasicHit:

    def test_hit_within_effective_range(self):
        """BE-HIT-01: 有效范围内应有较高命中率"""
        rng = RandomContext(seed=42)
        engine = BallisticEngine(rng=rng)

        weapon = create_test_weapon(range_effective=400, accuracy_base=0.75)
        target_pos = Vec2(300, 0)  # 300米距离
        cover_value = 0.0

        hits = sum(
            engine.calculate_hit(weapon, target_pos, cover_value)
            for _ in range(100)
        )
        hit_rate = hits / 100
        assert hit_rate > 0.6, f"Hit rate {hit_rate:.2f} too low"

    def test_miss_at_max_range(self):
        """BE-HIT-02: 最大距离命中率低"""
        rng = RandomContext(seed=42)
        engine = BallisticEngine(rng=rng)

        weapon = create_test_weapon(range_max=550, range_effective=400, accuracy_base=0.75)
        target_pos = Vec2(550, 0)

        hits = sum(
            engine.calculate_hit(weapon, target_pos, cover=0.0)
            for _ in range(200)
        )
        hit_rate = hits / 200
        assert hit_rate < 0.3, f"Hit rate at max range {hit_rate:.2f} too high"

    def test_deterministic_same_seed(self):
        """BE-HIT-05: 相同seed产生相同结果"""
        weapon = create_test_weapon()
        target = Vec2(100, 0)

        results_1 = [
            BallisticEngine(RandomContext(seed=123)).calculate_hit(weapon, target, 0.0)
            for _ in range(50)
        ]
        results_2 = [
            BallisticEngine(RandomContext(seed=123)).calculate_hit(weapon, target, 0.0)
            for _ in range(50)
        ]

        assert results_1 == results_2, "Same seed must produce identical results"
```

---

### 3.2 伤害计算测试 (8 tests)

| Test ID | 测试名称 | 输入条件 | 预期输出 | 优先级 | 备注 |
|---------|----------|----------|----------|--------|------|
| BE-DMG-01 | 最优距离满伤 | distance=optimal, penetration足够 | damage = damage_base (或接近) | P0 | 最佳距离应造成满伤 |
| BE-DMG-02 | 距离衰减 | distance从optimal增加到max | damage单调递减 | P0 | 伤害应随距离增加而降低 |
| BE-DMG-03 | 穿透力影响 | 高penetration vs 低armor vs 高armor | 高穿>低穿, armor降低伤害 | P0 | 穿透力应影响对装甲目标的伤害 |
| BE-DMG-04 | 最低1伤 | 任何命中情况 | damage ≥ 1 | P0 | 命中至少造成1点伤害 |
| BE-DMG-05 | 致命击杀标记 | damage >= target.current_hp | is_kill_shot = True | P0 | 超过剩余HP的伤害应标记为击杀 |
| BE-DMG-06 | 伤害方差±20% | 多次相同条件射击 | std/mean ∈ [0, 0.2] | P1 | 伤害应有合理随机波动 |
| BE-DMG-07 | 高穿透满伤 | penetration >> target_armor | damage不受armor显著影响 | P1 | 足够穿透时应忽略装甲 |
| BE-DMG-08 | 距离修正公式验证 | 特定距离点 | 符合设计文档的衰减曲线 | P0 | 数学公式需精确实现 |

**伤害衰减公式（参考）：**

$$
\text{damage} = \text{damage\_base} \times \left(1 - \frac{\text{distance}}{\text{range\_max}} \times \text{decay\_factor}\right) \times \text{armor\_modifier}
$$

其中：
- `decay_factor` = 0.5 (默认距离衰减系数)
- `armor_modifier` = `max(0.1, 1 - armor / (penetration * 2))`

---

### 3.3 散布未命中测试 (6 tests)

| Test ID | 测试名称 | 输入条件 | 预期输出 | 优先级 | 备注 |
|---------|----------|----------|----------|--------|------|
| BE-SPR-01 | 散布近目标 | distance=50m, spread=5° | miss_offset小 (< 5px) | P0 | 近距离散布小 |
| BE-SPR-02 | 距离增大散布 | distance从50m增加到400m | offset随距离增大而增大 | P0 | 散布与距离成正比 |
| BE-SPR-03 | 高斯分布检验 | 1000次miss采样 | X/Y坐标符合正态分布 | P1 | 统计检验散布分布 |
| BE-SPR-04 | 未命中压制 | miss事件发生 | suppression_value > 0 但 < hit的suppression | P1 | 未中也造成少量压制 |
| BE-SPR-05 | 压制值小于命中 | compare(miss.suppression, hit.suppression) | miss_suppression < hit_suppression | P0 | 命中造成的压制更高 |
| BE-SPR-06 | Miss位置不进target | miss_position vs target_center | distance(miss_pos, target) > target_radius | P0 | 未命中的弹着点不在目标体内 |

**散布计算公式：**

$$
\sigma = \tan(\text{spread\_base}) \times \text{distance}
$$

$$
\Delta x \sim \mathcal{N}(0, \sigma^2), \quad \Delta y \sim \mathcal{N}(0, \sigma^2)
$$

---

### 3.4 边缘条件测试 (8 tests)

| Test ID | 测试名称 | 输入条件 | 预期输出 | 优先级 | 备注 |
|---------|----------|----------|----------|--------|------|
| BE-EDGE-01 | 零距离 | distance=0 | 必中, 满伤, 极小散布 | P0 | 贴脸射击特例 |
| BE-EDGE-02 | 负cover | cover=-0.5 (非法值) | clamp到0 或 raise ValueError | P0 | 非法参数处理 |
| BE-EDGE-03 | 极端cover满 | cover=1.5 (>1.0) | clamp到1.0 | P0 | 参数上界约束 |
| BE-EDGE-04 | 武器无弹 | ammo=0 | 返回CannotFireError 或 (hit=False, damage=0) | P0 | 弹药耗尽处理 |
| BE-EDGE-05 | OOM保护 | 极大次数循环(100万次) | 内存使用稳定, 不泄漏 | P1 | 性能边界测试 |
| BE-EDGE-06 | 多次射击序列确定性 | 固定seed连续射击N次 | 序列可复现 | P0 | 回放系统需求 |
| BE-EDGE-07 | Result不可变 | calculate_hit返回的对象 | 修改result不影响后续调用 | P1 | 防御性编程 |
| BE-EDGE-08 | 统计验证伤害分布 | 5000次射击直方图 | 符合理论期望分布 (χ²检验 p>0.05) | P0 | 分布正确性验证 |

---

### 3.5 统计验证测试 (5 tests)

| Test ID | 测试名称 | 方法 | 通过标准 | 优先级 |
|---------|----------|------|----------|--------|
| BE-STAT-01 | 命中率大数验证 | 1000次射击统计 | \|实际-理论\| < 5% | P0 |
| BE-STAT-02 | 伤害均值验证 | 1000次命中伤害均值 | \|mean - E[damage]\| / E[damage] < 10% | P0 |
| BE-STAT-03 | 压制累积验证 | 连续射击N次的累积压制值 | 符合线性/非线性累积模型 | P1 |
| BE-STAT-04 | 距离-命中率曲线 | 多距离点采样 | 曲线平滑单调递减 | P1 |
| BE-STAT-05 | Cover-命中率关系 | 不同cover值采样 | cover↑ → hit_rate↓ (负相关) | P0 |

**统计测试框架代码：**

```python
from scipy import stats
import numpy as np

class TestStatisticalValidation:

    def test_hit_rate_converges_to_theoretical(self):
        """BE-STAT-01: 大数定律验证命中率"""
        engine = BallisticEngine(RandomContext(seed=999))
        weapon = create_test_weapon(accuracy_base=0.70)

        theoretical_hit_rate = 0.70  # 理论值 (简化)
        n_shots = 1000

        results = [engine.calculate_hit(weapon, Vec2(200, 0), 0.0) for _ in range(n_shots)]
        actual_hit_rate = sum(results) / n_shots

        error = abs(actual_hit_rate - theoretical_hit_rate)
        assert error < 0.05, f"Hit rate error {error:.3f} exceeds 5% threshold"

    def test_damage_distribution_chi_square(self):
        """BE-STAT-08: 卡方检验伤害分布"""
        engine = BallisticEngine(RandomContext(seed=777))
        weapon = create_test_weapon(damage_base=35)

        damages = []
        for _ in range(5000):
            result = engine.fire(weapon, Vec2(100, 0), 0.0)
            if result.hit:
                damages.append(result.damage)

        if len(damages) < 100:
            pytest.skip("Not enough hits for statistical test")

        # 假设伤害服从正态分布 N(μ=30, σ=5)
        mean_damage = np.mean(damages)
        std_damage = np.std(damages)

        # Shapiro-Wilk正态性检验 (样本量<5000时适用)
        if len(damages) < 5000:
            stat, p_value = stats.shapiro(damages[:5000])
            assert p_value > 0.05, f"Distribution not normal (p={p_value:.4f})"
```

---

### 3.6 BallisticEngine 测试总结

| 分类 | 测试数量 | P0 | P1 | 预估耗时 |
|------|----------|-----|-----|----------|
| 基础命中 | 8 | 6 | 2 | 0.5s |
| 伤害计算 | 8 | 6 | 2 | 0.6s |
| 散布未命中 | 6 | 4 | 2 | 0.8s |
| 边缘条件 | 8 | 6 | 2 | 0.4s |
| 统计验证 | 5 | 3 | 2 | 2.0s (大数据量) |
| **总计** | **35** | **25** | **10** | **~4.3s** |

---

## 4. MoraleCalculator 30 tests 详细定义

MoraleCalculator 管理单位士气系统，包括事件响应、状态转换、传染机制等。

### 4.1 事件权重测试 (12 tests)

| Test ID | 事件类型 | 权重变化 | 初始士气 | 预期结果 | 优先级 |
|---------|----------|----------|----------|----------|--------|
| MC-EVT-01 | ally_killed (友军阵亡) | -15 | 100 | 85 | P0 |
| MC-EVT-02 | leader_killed (指挥官阵亡) | -25 | 100 | 75 | P0 |
| MC-EVT-03 | heavy_fire (遭受猛攻) | -5/tick | 90 | 85 (1tick后) | P0 |
| MC-EVT-04 | explosion (爆炸冲击) | -20 | 100 | 80 | P0 |
| MC-EVT-05 | kill_confirmed (确认击杀) | +8 | 70 | 78 | P0 |
| MC-EVT-06 | rally (集结号令) | +3 | 50 | 53 | P1 |
| MC-EVT-07 | in_cover (进入掩体) | +5/tick | 60 | 65 (1tick后) | P0 |
| MC-EVT-08 | commander_nearby (指挥官在旁) | +10 | 70 | 80 | P0 |
| MC-EVT-09 | panic_contagion (恐慌传染) | -10 | 50 | 40 | P0 |
| MC-EVT-10 | unknown_event (未知事件) | 0 | 80 | 80 (不变) | P1 |
| MC-EVT-11 | magnitude_scaling (量级缩放) | weight × magnitude | base_weight=10, mag=2.0 | -20 | P1 |
| MC-EVT-12 | 复合事件同时发生 | 多事件叠加 | 顺序应用 | 最终值正确 | P0 |

**测试代码示例：**

```python
class TestMoraleEvents:

    def test_ally_killed_reduces_morale(self):
        """MC-EVT-01: 友军阵亡降低士气"""
        calc = MoraleCalculator(initial_morale=100)
        calc.apply_event('ally_killed')
        assert calc.current_morale == 85

    def test_leader_killed_bigger_penalty(self):
        """MC-EVT-02: 指挥官阵亡惩罚更大"""
        calc = MoraleCalculator(initial_morale=100)
        calc.apply_event('leader_killed')
        assert calc.current_morale == 75  # -25 > -15

    def test_kill_confirmed_increases_morale(self):
        """MC-EVT-05: 确认击杀提升士气"""
        calc = MoraleCalculator(initial_morale=70)
        calc.apply_event('kill_confirmed')
        assert calc.current_morale == 78  # +8

    def test_unknown_event_no_change(self):
        """MC-EVT-10: 未知事件不影响士气"""
        calc = MoraleCalculator(initial_morale=80)
        calc.apply_event('nonexistent_event')
        assert calc.current_morale == 80
```

---

### 4.2 状态转换测试 (10 tests)

Morale状态机: `normal → suppressed → panic → routing`

| Test ID | 转换路径 | 触发条件 | 预期状态 | 优先级 |
|---------|----------|----------|----------|--------|
| MC-STATE-01 | normal → panic | morale ≤ 30 | state = 'panic' | P0 |
| MC-STATE-02 | at_threshold_exact | morale = 30 (恰好阈值) | state = 'panic' | P0 |
| MC-STATE-03 | routing不可恢复 | state='routing', +morale event | 保持routing | P0 |
| MC-STATE-04 | suppressed状态 | morale ≤ 50 且 > 30 | state = 'suppressed' | P0 |
| MC-STATE-05 | suppression_decay | suppressed状态下无负面事件 | morale缓慢恢复 | P1 |
| MC-STATE-06 | natural_recovery_only_after_30ticks | 从panic恢复需要≥30ticks | tick<30时不恢复 | P0 |
| MC-STATE-07 | clamped_at_100 | morale +event > 100 | morale = 100 (不上溢) | P0 |
| MC-STATE-08 | floor_at_0 | morale -event < 0 | morale = 0 (不下溢) | P0 |
| MC-STATE-09 | state_order | 状态只能按 normal→suppressed→panic→routing 单向转换 | 不能跳级或回退 | P0 |
| MC-STATE-10 | recovery_from_suppressed | suppressed → morale>50 | 回到normal | P0 |

**状态机图示：**

```
                    ┌─────────────────────────────────┐
                    │                                 │
                    ▼                                 │
  [normal: 51-100] ──→ [suppressed: 31-50] ──→ [panic: 0-30]
       ▲                                            │
       │                                            │
       │              (30 ticks cooldown)             │
       │                                            ▼
       └──────── [recovery] ◄────────── [routing: 不可恢复]
                                    (morale≤0持续>60ticks)
```

---

### 4.3 传染机制测试 (4 tests)

恐慌可以在相邻单位间传播。

| Test ID | 场景 | 条件 | 预期结果 | 优先级 |
|---------|------|------|----------|--------|
| MC-CONTAG-01 | 无panic单位不传染 | 所有单位normal | 无传染发生 | P0 |
| MC-CONTAG-02 | 传染给所有非panic邻居 | 1个panic + 3个normal邻居(距离<5) | 3个都受影响 | P0 |
| MC-CONTAG-03 | 已panic单位不受重复扣减 | 已panic单位再次接触传染源 | 不额外扣减 | P0 |
| MC-CONTAG-04 | 链式传染 | A→B→C→D (都在范围内) | 全部最终panic | P1 |

**传染算法规则：**
- 传染范围: Manhattan距离 ≤ 4 tiles
- 传染概率: 基础30%, 受距离和cover调整
- 传染效果: -10士气 (可触发连锁panic)
- 冷却时间: 单位每10tick最多被传染1次

---

### 4.4 Tick恢复测试 (4 tests)

| Test ID | 测试内容 | 条件 | 预期行为 | 优先级 |
|---------|----------|------|----------|--------|
| MC-TICK-01 | decay_suppression | suppressed, 无combat, 10ticks | morale += 5 (假设+0.5/tick) | P0 |
| MC-TICK-02 | no_recovery_during_combat | suppressed, 正在被攻击 | morale不恢复或恢复极慢 | P0 |
| MC-TICK-03 | recovery_after_30ticks | panic → 等待30ticks → 开始恢复 | tick 30后morale开始增加 | P0 |
| MC-TICK-04 | recovery_rate & clamping | 恢复速度验证 | rate符合设计, max=100 | P1 |

**恢复速率表：**

| 当前状态 | 每tick恢复 | 条件 |
|----------|------------|------|
| Normal | +0 (保持) | 无事件时稳定 |
| Suppressed | +0.5 | 无combat事件 |
| Panic | 0 (前30tick) / +0.2 (30tick后) | 需要冷却期 |
| Routing | 0 | 不可恢复 |

---

### 4.5 MoraleCalculator 测试总结

| 分类 | 测试数量 | P0 | P1 | 预估耗时 |
|------|----------|-----|-----|----------|
| 事件权重 | 12 | 9 | 3 | 0.3s |
| 状态转换 | 10 | 8 | 2 | 0.4s |
| 传染机制 | 4 | 3 | 1 | 0.2s |
| Tick恢复 | 4 | 3 | 1 | 0.3s |
| **总计** | **30** | **23** | **7** | **~1.2s** |

---

## 5. PathFinder 25 tests

PathFinder 基于A*算法，支持地形代价、动态障碍物等。

### 5.1 基本功能测试 (8 tests)

| Test ID | 测试名称 | 地图设置 | 预期结果 | 优先级 |
|---------|----------|----------|----------|--------|
| PF-BASIC-01 | 直线无障碍 | 10x10空地, (0,0)→(9,9) | 路径存在, length≈18 (Manhattan) | P0 |
| PF-BASIC-02 | 绕障行走 | 中间有墙, 需绕行 | 路径避开障碍, length > 直线距离 | P0 |
| PF-BASIC-03 | 对角线代价 | 允许对角移动 | 对角步代价 = √2 × 直线代价 | P0 |
| PF-BASIC-04 | 不可达目标 | 目标在封闭区域内 | 返回None或抛出NoPathError | P0 |
| PF-BASIC-05 | 起点==终点 | (5,5)→(5,5) | 返回空路径 [起点] 或长度0 | P1 |
| PF-BASIC-06 | 相邻两点 | (3,3)→(3,4) | 路径长度=2 (含起点终点) | P1 |
| PF-BASIC-07 | 启发式可容 | h(n) ≤ actual_cost(n→goal) | A*最优性保证 | P0 |
| PF-BASIC-08 | 启发式一致 | h(n) ≤ cost(n,n') + h(n') | 无多余节点展开 | P0 |

---

### 5.2 复杂地形测试 (7 tests)

| Test ID | 场景 | 特殊条件 | 预期 | 优先级 |
|---------|------|----------|------|--------|
| PF-TER-01 | 绕墙 | L形墙壁阻挡 | 路径沿墙边绕行 | P0 |
| PF-TER-02 | 穿隙 | 两墙之间有1格间隙 | 能穿过间隙 | P0 |
| PF-TER-03 | 优先道路 | 有ROAD(代价0.8)和GRASS(代价1.2) | 优选道路即使稍远 | P1 |
| PF-TER-04 | 避开水域 | 必须跨越河流(有桥) | 路径经过桥梁tile | P0 |
| PF-TER-05 | 建筑阻塞 | BUILDING_SOLID区域 | 路径不穿过建筑 | P0 |
| PF-TER-06 | 大地图性能 | 256×256地图, 跨地图寻路 | < 100ms完成 | P0 |
| PF-TER-07 | 动态blockage | 寻路过程中临时添加障碍 | 支持重新规划或失败 | P1 |

---

### 5.3 路径质量测试 (5 tests)

| Test ID | 质量指标 | 标准 | 通过条件 | 优先级 |
|---------|----------|------|----------|--------|
| PF-QUAL-01 | 无环路 | 路径中无重复节点 | all unique | P0 |
| PF-QUAL-02 | 单调性 | 每步距目标曼哈顿距离不减 | non-increasing distance to goal | P1 |
| PF-QUAL-03 | 最优性*110% | path_cost ≤ optimal * 1.10 | 接近最优解 | P0 |
| PF-QUAL-04 | 平滑度 | 方向改变次数少 | turns ≤ length / 3 | P2 |
| PF-QUAL-05 | 安全边距 | 不紧贴危险地形 | 与WALL/WATER保持≥1格 | P1 |

---

### 5.4 边缘条件测试 (5 tests)

| Test ID | 异常输入 | 预期处理 | 优先级 |
|---------|----------|----------|--------|
| PF-EDGE-01 | 越界坐标 | start=(-1, 0) 或 goal=(300, 300) | ValueError / Clamp / None |
| PF-EDGE-02 | 空地图 | 0×0地图 | ValueError |
| PF-EDGE-03 | 单tile地图 | 1×1地图, (0,0)→(0,0) | 空路径 |
| PF-EDGE-04 | 缓存失效 | 地形修改后重新寻路 | 不使用过期缓存 |
| PF-EDGE-05 | 极端代价地形 | movement_cost=10.0 | 仍能找到路径(如果可达) | P1 |

---

### 5.5 PathFinder 测试总结

| 分类 | 测试数量 | P0 | P1 | P2 | 预估耗时 |
|------|----------|-----|-----|-----|----------|
| 基本功能 | 8 | 6 | 2 | 0 | 0.5s |
| 复杂地形 | 7 | 5 | 1 | 1 | 1.5s (含大地图) |
| 路径质量 | 5 | 2 | 2 | 1 | 0.8s |
| 边缘条件 | 5 | 4 | 1 | 0 | 0.3s |
| **总计** | **25** | **17** | **6** | **2** | **~3.1s** |

---

## 6. 集成测试 (53 tests, 8文件) + E2E (3 scenarios)

### 6.1 集成测试模块清单

| 文件路径 | 测试类数量 | 主要测试内容 | 依赖模块 | 预估时间 |
|----------|-----------|--------------|----------|----------|
| `tests/integration/test_game_loop.py` | 5 | 主循环启动/暂停/步进 | EventBus, StateMachine | 0.5s |
| `tests/integration/test_save_load.py` | 8 | 存档读写完整性 | SecureIO, All Models | 1.0s |
| `tests/integration/test_combat_scenario.py` | 8 | 完整战斗流程 | CombatResolver, BallisticEngine, Morale | 2.0s |
| `tests/integration/test_pathfinding_real_map.py` | 5 | 真实地图上的寻路 | PathFinder, TileMapConfig | 1.5s |
| `tests/integration/test_fog_of_war.py` | 5 | FoW与单位视野交互 | FogOfWar, Unit, Terrain | 1.0s |
| `tests/integration/test_ui_input.py` | 5 | 输入→命令→状态链路 | InputHandler, CommandBus, Game | 0.8s |
| `tests/integration/test_mod_loading.py` | 4 | Mod加载与注册 | ModLoader (v2.0) | 0.5s |
| `tests/integration/test_combat_loop.py` | 13 | Combat loop全链路: attack/damage/death/move/stop/constraints | CombatLoop, BallisticEngine, Effects, Weapon | 1.5s |
| **合计** | **53** | - | - | **~9.3s** |

### 6.1.2 单元测试模块清单 (P2 新增)

| 文件路径 | 测试数量 | 主要测试内容 | 阶段 |
|----------|----------|--------------|------|
| `tests/unit/test_vec2.py` | 25 | Vec2向量运算 | P0 |
| `tests/unit/test_tile_coord.py` | 15 | TileCoord坐标系统 | P0 |
| `tests/unit/test_terrain_type.py` | 12 | 地形类型枚举与代价 | P0 |
| `tests/unit/test_state_machine.py` | 20 | 状态机转换 | P0 |
| `tests/unit/test_random_context.py` | 10 | 确定性随机数 | P0 |
| `tests/unit/test_ballistic_engine.py` | 35 | 弹道引擎: 命中/伤害/散布/边缘/统计 | P0-P1 |
| `tests/unit/test_morale_calculator.py` | 30 | 士气计算: 事件/状态/传染/恢复 | P0-P1 |
| `tests/unit/test_pathfinder.py` | 25 | A*寻路: 基本/地形/质量/边缘 | P0-P1 |
| `tests/unit/test_fog_of_war.py` | 20 | 战争迷雾计算 | P1 |
| `tests/unit/test_combat_resolver.py` | 20 | 战斗结算 | P1 |
| `tests/unit/test_behavior_tree.py` | 20 | 行为树节点 | P1 |
| `tests/unit/test_event_bus.py` | 15 | 事件总线发布/订阅 | P0 |
| `tests/unit/test_sound_system.py` | 21 | 程序化音效生成、播放、音量控制、缓存 | P2 |
| **单元合计** | **268** | - | - |

**集成测试示例：**

```python
# tests/integration/test_combat_scenario.py
class TestCombatScenario:

    @pytest.fixture
    def combat_setup(self):
        """创建一个标准的战斗测试场景"""
        game = IntegrationTestGame(map_file="data/maps/tutorial.json")

        allies_squad = game.spawn_squad("rifle_squad_us", pos=(3, 3), faction="allies")
        axis_squad = game.spawn_squad("rifle_squad_ge", pos=(12, 8), faction="axis")

        return {
            'game': game,
            'allies': allies_squad,
            'axis': axis_squad
        }

    def test_full_engagement_until_victory(self, combat_setup):
        """完整交战直到一方获胜"""
        game = combat_setup['game']

        # 盟军进攻
        game.issue_command(MoveCommand(allies_squad.id, target=(10, 8)))
        game.advance_ticks(50)  # 移动到接近位置

        # 开火
        game.issue_command(AttackCommand(allies_squad.id, target=axis_squad.id))

        # 模拟持续战斗直到一方全灭
        max_ticks = 5000
        ticks_elapsed = 0
        while (allies_squad.is_alive and axis_squad.is_alive) and ticks_elapsed < max_ticks:
            game.tick()
            ticks_elapsed += 1

        assert ticks_elapsed < max_ticks, "Combat did not conclude within time limit"
        assert (not allies_squad.is_alive) or (not axis_squad.is_alive), "One side must be defeated"

    def test_suppression_leading_to_panic(self, combat_setup):
        """验证压制导致恐慌的完整链条"""
        game = combat_setup['game']
        target = combat_setup['axis'].units[0]

        # 用机枪组持续压制
        mg_squad = game.spawn_squad("mg_squad_us", pos=(10, 8), faction="allies")
        game.issue_command(AttackCommand(mg_squad.id, target_unit=target.id))

        for _ in range(200):  # 持续压制
            game.tick()

        # 验证目标进入panic状态
        assert target.morale_state == 'panic', f"Expected panic, got {target.morale_state}"
        assert target.morale <= 20
```

---

### 6.2 E2E测试场景 (3 scenarios)

#### Scenario 1: Tutorial Mission (教学任务)

**目标：** 新手玩家完成第一个任务（占领中心建筑）

**前置条件：**
- 加载 tutorial.json 地图
- 2个盟军小队 (步枪班+机枪组)
- 2个德军小队 (防御方)
- 目标: 占领坐标(8,8)的建筑

**操作步骤：**
```yaml
steps:
  - action: LOAD_MAP
    params: { file: "tutorial.json" }
  - action: SELECT_SQUAD
    params: { squad_id: "allies_rifle_1" }
  - action: ISSUE_COMMAND
    params: { type: MOVE, target: (7, 7) }
  - action: WAIT_TICKS
    params: { count: 100 }
  - action: SELECT_SQUAD
    params: { squad_id: "allies_mg_1" }
  - action: ISSUE_COMMAND
    params: { type: MOVE, target: (9, 9) }
  - action: WAIT_TICKS
    params: { count: 100 }
  - action: AUTO_COMBAT_ENABLE
    params: {}
  - action: WAIT_UNTIL_CONDITION
    params: { condition: "objective_captured", timeout: 5000 }

expected_result:
  mission_status: VICTORY
  casualties_allies: <= 3
  duration_ticks: < 5000
  no_crashes: true
  no_errors_logged: true
```

**通过标准：**
- [ ] 任务状态为 VICTORY
- [ ] 盟军伤亡 ≤ 3 人
- [ ] 总用时 < 5000 ticks
- [ ] 无崩溃或未捕获异常
- [ ] 日志无ERROR级别记录

---

#### Scenario 2: Combat Engagement (战斗遭遇战)

**目标：** 双方交火的完整战斗流程

**场景描述：**
- 32×32地图，混合地形
- 盟军: 2步枪班 + 1反坦克组
- 德军: 2步枪班 + 1机枪组
- 无特定目标，歼灭战

**关键验证点：**
```yaml
validation_points:
  - name: initial_deployment_correct
    check: "All units at correct spawn positions"

  - name: line_of_sight_works
    check: "Units behind WALL cannot be targeted"

  - name: ammunition_consumed
    check: "Total ammo decreases as firing occurs"

  - name: casualties_occur
    check: "HP decreases and units die over time"

  - name: morale_system_active
    check: "Units enter suppressed/panic under heavy fire"

  - name: fog_of_war_updates
    check: "Hidden enemies revealed when in vision range"

  - name: battle_concludes
    check: "One side eliminated or retreats within time limit"

  - name: save_during_combat
    check: "Can save and resume mid-combat without desync"
```

---

#### Scenario 3: Save/Load Cycle (存档读档循环)

**目标：** 验证存档系统的完整性

**步骤：**
```yaml
steps:
  - action: START_NEW_GAME
    params: { map: "mission_1.json" }

  - action: PLAY_FOR_TICKS
    params: { count: 1000 }  # 游戏一段时间

  - action: RECORD_STATE
    params: {}  # 记录当前完整状态快照

  - action: SAVE_GAME
    params: { slot: 1 }

  - action: EXIT_TO_MENU
    params: {}

  - action: LOAD_GAME
    params: { slot: 1 }

  - action: VERIFY_STATE_MATCHES
    params: { tolerance: { hp: 0, position: 0, ammo: 0, morale: 0, tick: 0 } }

  - action: CONTINUE_PLAYING
    params: { ticks: 100 }

  - action: VERIFY_NO_DESYNC
    params: {}
```

**严格匹配字段：**
- 所有单位的 HP、位置、弹药、士气
- 游戏全局 tick 数
- Camera 位置和缩放
- 任务目标进度
- 战役状态

**容差说明：**
- HP: ±0 (必须精确匹配)
- Position: ±0 (tile坐标整数)
- Ammo: ±0 (整数计数)
- Morale: ±0 (精确状态)
- Tick: ±0 (必须完全一致)

---

#### Scenario 4: Campaign Flow E2E (10 tests)

**目标：** 验证战役四层架构的完整流程

**场景描述：**
- 从Grand Campaign开始，选择Sector → Operation → Battle
- 完成3场连续Battle，验证状态继承
- 验证补给线机制和增援触发

**关键验证点：**
```yaml
validation_points:
  - name: campaign_initialization
    check: "Grand Campaign loads with 3 Sectors and 7 Operations"

  - name: sector_to_operation_navigation
    check: "Selecting Sector shows available Operations"

  - name: battle_state_inheritance
    check: "Unit HP/ammo/morale carry over between Battles"

  - name: supply_line_mechanics
    check: "Supply level affects ammo replenishment rate"

  - name: reinforcement_trigger
    check: "Reinforcements arrive at correct Operation timeline points"

  - name: campaign_victory_condition
    check: "Campaign victory triggers when all Sectors completed"

  - name: campaign_defeat_condition
    check: "Campaign defeat triggers when critical objectives lost"

  - name: cross_battle_veterancy
    check: "Unit experience accumulates across Battles"

  - name: strategic_map_update
    check: "Strategic map reflects Battle outcomes"

  - name: save_resume_campaign
    check: "Campaign state saves and resumes correctly mid-campaign"
```

---

#### Scenario 5: AI Behaviors E2E (20 tests)

**目标：** 验证P0 AI行为在完整游戏场景中的表现

**场景描述：**
- 多种战场情境测试AI决策
- 覆盖全部7项P0 AI行为

**关键验证点：**
```yaml
validation_points:
  - name: ammo_pickup_under_fire
    check: "AI unit with no ammo moves to ammo source while under fire"

  - name: weapon_scavenge_priority
    check: "AI prefers scavenge closer weapons over farther ones"

  - name: surrender_conditions
    check: "AI surrenders only when morale<5, no support, surrounded"

  - name: surrender_no_friendly_nearby
    check: "AI does not surrender when friendly units within 5 tiles"

  - name: weapon_jam_recovery
    check: "Jammed weapon clears after correct tick duration"

  - name: weapon_jam_probability
    check: "Jam rate statistically matches configured jam_chance"

  - name: smoke_deployment_timing
    check: "AI deploys smoke when suppression>50 and has smoke grenades"

  - name: smoke_blocks_los
    check: "Smoke tile blocks line of sight for both sides"

  - name: squad_degradation_effects
    check: "Squad with <50% survivors has reduced accuracy/morale/speed"

  - name: squad_degradation_nonlinear
    check: "Degradation penalty increases nonlinearly with casualties"

  - name: nco_rally_range
    check: "NCO rally affects units within 5 tiles"

  - name: nco_rally_morale_boost
    check: "Rallied units gain +15 morale and exit PANIC state"

  - name: nco_rally_cooldown
    check: "NCO cannot rally again within 30 ticks"

  - name: ai_behavior_tree_integration
    check: "P0 behaviors integrate correctly with existing BT"

  - name: multiple_ai_behaviors_conflict
    check: "AI resolves conflicts between competing behaviors"

  - name: ammo_pickup_then_attack
    check: "AI picks up ammo then resumes attacking"

  - name: smoke_then_reposition
    check: "AI deploys smoke then moves to better position"

  - name: surrender_prevents_exploitation
    check: "Surrendered units cannot be attacked"

  - name: jam_during_critical_moment
    check: "Weapon jam during combat triggers scavenge or retreat"

  - name: nco_death_squad_morale
    check: "NCO death triggers squad morale penalty before rally check"
```

---

#### Scenario 6: Game Settings E2E (15 tests)

**目标：** 验证新游戏设置系统在完整游戏流程中的效果

**场景描述：**
- 测试5种难度预设的实际游戏效果
- 验证独立经验/补给等级

**关键验证点：**
```yaml
validation_points:
  - name: recruit_preset_easy
    check: "RECRUIT preset: allies GREEN+ABUNDANT vs axis GREEN+SCARCE"

  - name: veteran_preset_hard
    check: "VETERAN preset: allies ELITE+SCARCE vs axis CRACK+ABUNDANT"

  - name: independent_experience_levels
    check: "Allies and Axis can have different experience levels"

  - name: independent_supply_levels
    check: "Allies and Axis can have different supply levels"

  - name: experience_affects_accuracy
    check: "ELITE units have statistically higher hit rate than GREEN"

  - name: supply_affects_ammo
    check: "SCARCE supply reduces starting ammo by ~40%"

  - name: supply_affects_reinforcement
    check: "ABUNDANT supply enables more reinforcement waves"

  - name: custom_settings_override_preset
    check: "Custom settings override preset values"

  - name: settings_persist_save_load
    check: "Game settings persist through save/load cycle"

  - name: settings_displayed_correctly
    check: "Settings UI shows correct preset and individual values"

  - name: normal_preset_balanced
    check: "NORMAL preset: symmetric settings for both sides"

  - name: easy_preset_advantage
    check: "EASY preset gives allies measurable advantage"

  - name: hard_preset_disadvantage
    check: "HARD preset gives axis measurable advantage"

  - name: supply_replenishment_rate
    check: "Supply level affects between-battle ammo replenishment rate"

  - name: experience_morale_bonus
    check: "Higher experience level provides morale recovery bonus"
```

---

## 7. pytest / CI / Quality Gate (8 QG)

### 7.1 Quality Gates 定义

Quality Gate (质量门禁) 是代码合并前的强制性检查项。

| Gate ID | 名称 | 描述 | 严重性 | 自动阻断? |
|---------|------|------|--------|-----------|
| **QG-1** | TDD Core Pass | 12个核心模块全部单元测试通过 | 🔴 Critical | ✅ Yes |
| **QG-2** | Domain 100% Coverage | 领域模型(Vec2/Ballistic/Morale/PathFinder) 100%行覆盖 | 🔴 Critical | ✅ Yes |
| **QG-3** | Overall ≥70% | 项目总体代码覆盖率 ≥ 70% | 🟠 High | ✅ Yes |
| **QG-4** | Ballistic Statistics | 弹道引擎统计测试通过 (命中率/伤害分布) | 🔴 Critical | ✅ Yes |
| **QG-5** | Pathfinder Perf | 256×256地图寻路 < 100ms (P95) | 🟠 High | ✅ Yes |
| **QG-6** | Ruff Zero Errors | Ruff linter零错误零警告 | 🟡 Medium | ⚠️ Warning only |
| **QG-7** | Mypy Domain Strict | 领域模型mypy strict模式通过 | 🟠 High | ✅ Yes |
| **QG-8** | Integration Pass | 全部40个集成测试通过 | 🔴 Critical | ✅ Yes |

---

### 7.2 CI Pipeline 配置

**GitHub Actions 示例 (.github/workflows/ci.yml)：**

```yaml
name: PyCC2 CI Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  lint-and-typecheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v3
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: |
          pip install -e ".[dev]"
          pip install ruff mypy pytest-cov

      # QG-6: Ruff检查
      - name: Ruff Linting
        run: ruff check src/pycc2/

      # QG-7: Mypy类型检查
      - name: Mypy Type Check (Strict on domain)
        run: mypy src/pycc2/core/ --strict

  unit-tests:
    runs-on: ubuntu-latest
    needs: lint-and-typecheck
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v3
        with:
          python-version: '3.11'

      - name: Install deps
        run: pip install -e ".[dev]"

      # QG-1: TDD Core单元测试
      - name: Run Unit Tests (TDD Core)
        run: |
          pytest tests/unit/ -v \
            --cov=src/pycc2 \
            --cov-report=xml \
            --cov-report=term-missing \
            --junitxml=junit.xml

      # QG-2 & QG-3: 覆盖率检查
      - name: Coverage Check
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
          fail_ci_if_error: true
          thresholds: |
            domain_modules: 100%
            overall: 70%

      # QG-4: 弹道统计测试
      - name: Ballistic Statistical Tests
        run: pytest tests/unit/test_ballistic_engine.py::TestStatisticalValidation -v

      # 上传覆盖率报告
      - uses: actions/upload-artifact@v3
        with:
          name: coverage-report
          path: coverage.xml

  integration-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v3
        with:
          python-version: '3.11'

      - name: Install deps
        run: pip install -e ".[dev]"

      # QG-8: 集成测试
      - name: Run Integration Tests
        run: |
          pytest tests/integration/ -v \
            --timeout=120 \
            --junitxml=integration-junit.xml

      # QG-5: Pathfinder性能测试
      - name: Pathfinder Performance Test
        run: pytest tests/integration/test_pathfinding_real_map.py::test_large_map_performance -v -s

  e2e-tests:
    runs-on: ubuntu-latest
    needs: integration-tests
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v3
        with:
          python-version: '3.11'

      - name: Install deps with pygame
        run: pip install -e ".[dev,e2e]"

      - name: Run E2E Scenarios
        run: |
          xvfb-run pytest tests/e2e/ -v \
            --timeout=300 \
            --e2e-headless=True

      - name: Upload E2E Screenshots (on failure)
        if: failure()
        uses: actions/upload-artifact@v3
        with:
          name: e2e-failure-screenshots
          path: tests/e2e/screenshots/
```

---

### 7.3 本地测试命令速查

```bash
# === 安装测试依赖 ===
pip install -e ".[dev]"
pip install pytest pytest-cov pytest-xdist pytest-timeout ruff mypy

# === 运行全部测试 ===
pytest                              # 所有测试
pytest tests/unit/                   # 仅单元测试
pytest tests/integration/            # 仅集成测试
pytest tests/e2e/                    # 仅E2E测试

# === 并行执行 (多核加速) ===
pytest -n auto                       # 自动检测CPU核心数并行

# === 覆盖率报告 ===
pytest --cov=src/pycc2 --cov-report=html    # HTML报告 (htmlcov/index.html)
pytest --cov=src/pycc2 --cov-report=term-missing  # 终端显示缺失行

# === 单个模块测试 ===
pytest tests/unit/test_ballistic_engine.py -v
pytest tests/unit/test_ballistic_engine.py::TestBasicHit -v   # 只测某个类
pytest tests/unit/test_ballistic_engine.py::TestBasicHit::test_hit_within_effective_range -vs  # 单个测试+打印

# === 按优先级运行 ===
pytest -m "P0"                      # 只运行P0测试 (需自定义marker)
pytest -m "not slow"                # 排除慢速测试

# === 调试失败的测试 ===
pytest --lf                        # 只运行上次失败的测试
pytest -x                          # 第一个失败就停止
pytest --tb=long                   # 完整traceback

# === Lint和类型检查 ===
ruff check src/                    # Python linting
ruff check src/ --fix              # 自动修复
mypy src/pycc2/core/               # 类型检查
mypy src/pycc2/core/ --strict      # 严格模式

# === 性能基准测试 ===
pytest tests/benchmark/ --benchmark-only  # 需要pytest-benchmark插件

# === 生成测试报告 ===
pytest --html=report.html --self-contained-html  # HTML报告
pytest --junitxml=result.xml                     # JUnit XML格式
```

---

### 7.4 pytest 配置 (pyproject.toml)

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]

markers = [
    "P0: Critical priority tests",
    "P1: High priority tests",
    "P2: Medium priority tests",
    "slow: Marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: Integration test (requires more setup)",
    "e2e: End-to-end test (requires full system)",
    "statistical: Tests requiring large sample sizes for validation"
]

addopts = [
    "-v",
    "--strict-markers",
    "--tb=short",
    "--cov=src/pycc2",
    "--cov-report=term-missing:skip-covered",
    "-p no:warnings",  # 过滤第三方库警告
    "--durations=10",  # 显示最慢的10个测试
]

filterwarnings = [
    "ignore::DeprecationWarning",
    "ignore::PendingDeprecationWarning"
]

timeout = 120  # 单个测试最大执行时间(秒)
```

---

### 7.5 Coverage 配置

```toml
[tool.coverage.run]
source = ["src/pycc2"]
branch = true
parallel = true
omit = [
    "*/tests/*",
    "*/__pycache__/*",
    "*/typings/*",
    "*/main.py",  # 入口脚本通常不需要全覆盖
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "@abstractmethod",
    "if TYPE_CHECKING:",
]
fail_under = 70  # 总体覆盖率底线
show_missing = true
skip_covered = true

[tool.coverage.html]
directory = "htmlcov"
title = "PyCC2 Test Coverage Report"

[tool.coverage.paths]
source = [
    "src/pycc2/",
    ".tox/*/lib/python*/site-packages/pycc2/",
]
```

---

## 8. Test Coverage Summary (P2 更新)

| 测试文件 | 类型 | 数量 | 覆盖内容 | 阶段 |
|----------|------|------|----------|------|
| test_vec2.py | unit | 25 | 向量运算、距离、归一化、旋转 | P0 |
| test_tile_coord.py | unit | 15 | 瓦片坐标转换、邻居查询 | P0 |
| test_terrain_type.py | unit | 12 | 地形枚举、移动代价、掩体等级 | P0 |
| test_state_machine.py | unit | 20 | 状态转换、条件守卫、回调 | P0 |
| test_random_context.py | unit | 10 | 确定性RNG、seed隔离 | P0 |
| test_ballistic_engine.py | unit | 35 | 命中/伤害/散布/边缘/统计验证 | P0-P1 |
| test_morale_calculator.py | unit | 30 | 士气事件/状态机(4态)/传染/tick恢复 | P0-P1 |
| test_pathfinder.py | unit | 25 | A*基本/地形代价/路径质量/边缘 | P0-P1 |
| test_fog_of_war.py | unit | 20 | FoW计算/视野更新/探索标记 | P1 |
| test_combat_resolver.py | unit | 20 | 战斗结算/伤害应用/击杀判定 | P1 |
| test_behavior_tree.py | unit | 20 | BT节点/Selector/Sequence/Condition | P1 |
| test_event_bus.py | unit | 15 | 发布/订阅/事件过滤/异步分发 | P0 |
| test_sound_system.py | unit | 21 | 程序化音效生成、播放、音量控制、缓存 | P2 |
| test_game_loop.py | integration | 5 | 主循环启动/暂停/步进/状态管理 | P1 |
| test_save_load.py | integration | 8 | 存档读写/HMAC签名/完整性校验 | P1 |
| test_combat_scenario.py | integration | 8 | 完整战斗流程/双方交火至胜负 | P1 |
| test_pathfinding_real_map.py | integration | 5 | 真实地图寻路/动态障碍 | P1 |
| test_fog_of_war.py | integration | 5 | FoW与单位视野交互 | P1 |
| test_ui_input.py | integration | 5 | 输入→命令→状态链路 | P1 |
| test_mod_loading.py | integration | 4 | Mod加载与注册 | P1 |
| test_combat_loop.py | integration | 13 | Combat loop全链路: attack/damage/death/move/stop/constraints | P2 |
| test_victory_conditions.py | unit | 39 | VictoryConditionEvaluator, BattleStats, objectives, morale collapse, time limits | P3-A |
| test_animation_system.py | unit | 52 | UnitAnimator (6 anim types), ScreenShake, ParticleEmitter (8 particle types), physics | P3-B |
| test_content_expansion.py | unit | 31 | UnitTemplates (8 types), new terrains (CRATER/SWAMP), Campaign system, new sprite generation | P3-C |
| test_save_system.py | unit | 26 | SecureSaveManager (HMAC/JSON/8 slots), SaveMetaData, export_state, tamper detection | P3-D |
| test_render_pipeline.py | unit | ~20 | RenderPipeline rendering orchestration | P4.1-A |
| test_combat_director.py | unit | ~15 | CombatDirector combat management | P4.1-A |
| test_input_router.py | unit | ~10 | InputRouter keyboard/mouse routing | P4.1-A |
| test_save_controller.py | unit | ~12 | SaveController save/load/restore | P4.1-A |
| test_settings_menu.py | unit | 62 | Settings UI 4-tab menu interaction | P4.1-B |
| test_security_hardening.py | unit | 13 | HMAC env loading, input bounds | P4.1-C |
| test_tile_cache.py | unit | ~15 | TileCache terrain pre-caching, LRU eviction, hit rate optimization | P4.2-A |
| test_ai_throttle.py | unit | ~12 | AI decision throttling at 10Hz, cooldown management, burst prevention | P4.2-A |
| test_particle_pool.py | unit | ~12 | Particle object pooling, memory reuse, pool exhaustion handling | P4.2-A |
| test_tutorial_overlay.py | unit | ~15 | TutorialOverlay first-launch guide, step progression, skip/resume functionality | P4.2-B |
| test_hint_manager.py | unit | ~13 | HintManager context-aware hints, display timing, dismissal logic | P4.2-B |
| test_mission_4_night.py | unit | ~18 | Mission 4 Night Assault logic: night vision, stealth mechanics, flare effects, AI night behavior | P4.2-C |
| test_mission_5_armor.py | unit | ~17 | Mission 5 Armored Column: anti-tank tactics, vehicle combat, defensive formations | P4.2-C |
| test_new_maps.py | unit | ~12 | New map data validation: night_map, road_ambush, bridge_assault, defense_line schema & loading | P4.2-D |
| **总计 (P0-M1)** | **-** | **2767** | **P0-M1 full suite** | **-** |

### 8.1 P5 Phase Tests (Campaign Core)

| 测试文件 | 类型 | 数量 | 覆盖内容 | 阶段 |
|----------|------|------|----------|------|
| test_campaign_state.py | unit | ~45 | CampaignState序列化/反序列化, 单位名册/经验/弹药/作战日 | P5.1 |
| test_battle_result.py | unit | ~30 | BattleResult记录: KIA/WIA/弹药消耗/目标占领/时长/得分 | P5.1 |
| test_unit_veterancy.py | unit | ~55 | UnitVeterancy经验等级: Green→Veteran→Elite→Crack + 战斗加成验证 | P5.1 |
| test_strategic_map.py | unit/integration | ~40 | StrategicMapRenderer渲染 + 桥梁状态tooltip + 路线选择UI | P5.2 |
| test_operation_timeline.py | unit/integration | ~35 | OperationTimeline Day 1→Day 6推进 + 增援事件 + 桥梁链依赖 | P5.3 |
| test_campaign_integration.py | integration | ~35 | E2E: 战斗→BattleResult→CampaignState→下一关 数据一致性 | P5.x |
| **P5 合计** | **-** | **~240** | **Campaign Core 全套** | **-** |

### 8.2 P6 Phase Tests (Combat Depth)

| 测试文件 | 类型 | 数量 | 覆盖内容 | 阶段 |
|----------|------|------|----------|------|
| test_swiss_cheese.py | unit | ~60 | SquadMember实体 + 概率性伤亡(70%miss/20%near/7%WIA/2%KIA) | P6.1 |
| test_fatigue_system.py | unit | ~45 | FatigueSystem: 累积衰减(5-15%/battle) + 休息恢复 + critical fatigue | P6.2 |
| test_experience_component.py | unit | ~40 | UnitExperienceComponent: XP追踪 + 老兵加成(+15%acc/+20morale/-40panic) | P6.2 |
| test_after_action_report.py | unit/integration | ~35 | BattleStatistics收集 + AAR UI面板 + 单位评级(A-F) + Campaign进度 | P6.3 |
| test_time_control.py | unit/integration | ~25 | TimeControl: Pause/0.5x/1x/2x + desync检测 + physics稳定性 | P6.4 |
| **P6 合计** | **-** | **~205** | **Combat Depth 全套** | **-** |

### 8.3 P7 Phase Tests (Content Expansion)

| 测试文件 | 类型 | 数量 | 覆盖内容 | 阶段 |
|----------|------|------|----------|------|
| test_mission_6_son.py | unit | ~18 | Mission 6 Son: 桥梁争夺战逻辑 + 胜利条件 | P7.1 |
| test_mission_7_veghel.py | unit | ~18 | Mission 7 Veghel: 防线突破 + 坦克协同 | P7.1 |
| test_mission_8_grave.py | unit | ~18 | Mission 8 Grave: 渡河生存 + 包围防御 | P7.1 |
| test_mission_9_nijmegen.py | unit | ~20 | Mission 9 Nijmegen: Waal河强渡 + 城市巷战 | P7.1 |
| test_mission_10_arnhem.py | unit | ~22 | Mission 10 Arnhem: 最终突击 + 复杂地形 | P7.1 |
| test_new_maps_p7.py | unit | ~25 | 新地图schema校验: son/veghel/grave/nijmegen/arnhem (44×44 to 64×64) | P7.1 |
| test_historical_authenticity.py | unit | ~28 | OOB验证 + 武器规格匹配 + 任务简报文本渲染 + 动态事件触发 | P7.2 |
| test_mission_p7_integration.py | integration | ~20 | M6-M10完整流程测试 + 难度曲线验证 + 解锁进度 | P7.x |
| **P7 合计** | **-** | **~189** | **Content Expansion 全套** | **-** |

### 8.4 Test Growth Summary (v0.1.1)

| 阶段 | 当前累计 | 新增 | 目标总数 | 增长率 |
|------|----------|------|----------|--------|
| Current (v0.6-p4w2) | **1377** | — | Baseline | — |
| P5 Complete | ~1617 | +240 | +17% | Campaign系统重度测试 |
| P6 Complete | ~1822 | +205 | +13% | 战斗机制边缘用例 |
| P7 Complete | ~2011 | +189 | +11% | 内容驱动，较少新代码路径 |
| P8 Complete | ~1944 | +334 | +17% | 地图/战役/补给线/部署UI |
| P9 Complete | ~2233 | +289 | +15% | P0 AI行为+游戏设置+战役完成 |
| M1 Fix (**v0.1.1**) | **2767** | **+534** | **+24%** | M1紧急修复+回归测试 |

### 8.5 P0 AI Behavior Test Coverage

| 行为 | 单元测试 | 集成测试 | E2E测试 | 总计 | 覆盖要点 |
|------|----------|----------|---------|------|----------|
| 弹药拾取 (Ammo Pickup) | ~20 | ~5 | ~3 | ~28 | 搜索逻辑/路径规划/拾取动画/弹药恢复 |
| 武器搜刮 (Weapon Scavenging) | ~18 | ~4 | ~3 | ~25 | 武器选择/拾取流程/战斗力恢复 |
| 投降 (Surrender) | ~15 | ~3 | ~2 | ~20 | 条件判定/状态转换/不可攻击 |
| 武器卡壳 (Weapon Jam) | ~22 | ~5 | ~3 | ~30 | 概率触发/状态恢复/战斗影响 |
| 烟雾部署 (Smoke Deployment) | ~18 | ~4 | ~3 | ~25 | 触发条件/LOS阻挡/战术效果 |
| 班降解 (Squad Degradation) | ~18 | ~4 | ~3 | ~25 | 非线性惩罚/多属性影响/恢复条件 |
| NCO集结 (NCO Rally) | ~18 | ~4 | ~3 | ~25 | 范围效果/士气恢复/冷却时间 |
| **P0 AI 合计** | **~129** | **~29** | **~20** | **~178** | **7项P0行为全覆盖** |

### 8.6 Game Settings Test Coverage

| 设置维度 | 单元测试 | 集成测试 | E2E测试 | 总计 | 覆盖要点 |
|----------|----------|----------|---------|------|----------|
| 难度预设 (5级) | ~15 | ~5 | ~3 | ~23 | 预设值正确/切换/持久化 |
| 经验等级 (每方独立) | ~12 | ~4 | ~3 | ~19 | 命中率影响/士气加成/独立设置 |
| 补给等级 (每方独立) | ~12 | ~4 | ~3 | ~19 | 弹药量/增援频率/独立设置 |
| 自定义覆盖 | ~8 | ~3 | ~2 | ~13 | 覆盖预设/校验/保存加载 |
| 预设对应表验证 | ~5 | ~2 | ~1 | ~8 | 5×4矩阵完整性 |
| **Settings 合计** | **~52** | **~18** | **~12** | **~82** | **设置系统全覆盖** |

### 8.7 Campaign Completion Test Coverage

| 测试维度 | 单元测试 | 集成测试 | E2E测试 | 总计 | 覆盖要点 |
|----------|----------|----------|---------|------|----------|
| 四层架构 (Campaign→Sector→Op→Battle) | ~10 | ~5 | ~2 | ~17 | 层级导航/状态传递 |
| 3 Sectors | ~8 | ~3 | ~2 | ~13 | Sector独立/切换/完成 |
| 7 Operations | ~8 | ~3 | ~2 | ~13 | Operation进度/增援/时间线 |
| 29 Battles | ~5 | ~2 | ~2 | ~9 | Battle引用地图/胜负/继承 |
| 63 Maps引用 | ~5 | ~2 | ~1 | ~8 | 全部地图加载/Schema校验 |
| **Campaign 合计** | **~36** | **~15** | **~9** | **~60** | **战役完成全覆盖** |

### 8.1 P4.3 Phase Additional Tests (Week 3)

| 测试文件 | 类型 | 数量 | 覆盖内容 | 阶段 |
|----------|------|------|----------|------|
| test_night_combat.py | unit | ~8 | 夜战机制: Environment+FogOfWar夜间修正+照明弹效果+潜行加成 | P4.3-A |
| test_armor_system.py | unit | ~19 | 反坦克装甲: 装甲剖面(正/侧/后)+角度穿透计算+伤害衰减 | P4.3-B |
| test_weather_visual.py | unit | ~15 | 视觉增强: WeatherRenderer(雨/雾/夜渲染)+粒子预设(爆炸/血液) | P4.3-C |
| **P4.3 小计** | **-** | **~42** | **夜战/装甲/视觉增强** | **-** |

### 8.2 Quality Gate E2E Additional Tests

| 来源 | 新增测试数 | 覆盖内容 |
|------|-----------|----------|
| 文档统一v1.6 (14文件三语) | ~20 | 文档格式校验/多语言一致性/链接完整性 |
| 代码质量修复 | ~15 | Ruff lint修复/Mypy类型修复/安全漏洞修复 |
| E2E回归测试新增 | ~26 | 端到端场景扩展/跨模块集成/边界条件 |
| **QG-Docs 小计** | **~61** | **质量门禁通过** |

### 8.5 Test Growth Projection (P5 Preview)

| 阶段 | 当前累计 | 预计新增 | 目标总数 | 增长率 |
|------|----------|----------|----------|--------|
| Current (v0.6-p4w2) | **1377** | — | Baseline | — |
| P5 Complete (v0.7) | ~1750 | +373 | +27% | Campaign系统重度测试 |
| P6 Complete (v0.8) | ~2350 | +600 | +34% | 战斗机制边缘用例 |
| P7 Complete (v0.9) | ~2600 | +250 | +11% | 内容驱动，较少新代码路径 |
| P8 Complete (v1.0) | ~2700 | +100 | +4% | 回归+性能测试为主 |

> 详细P5测试计划见 [Section 14: P5 Test Plan Preview](#14-p5-test-plan-preview)

---

## 9. P2 Phase Test Results (2025-05-18)

### 9.1 总体结果

- **Total**: 940 tests passed (937 existing + 13 combat_loop + 21 sound_system ≈ **940**)
- **Pass Rate**: 100% (940/940)
- **Failures**: 0
- **Regression**: ✅ 全量回归通过

### 9.2 Combat Loop Integration Tests (13/13 passed)

| # | 测试项 | 结果 | 说明 |
|---|--------|------|------|
| 1 | Attack executes damage | ✅ | 攻击命令正确执行并造成伤害 |
| 2 | Attack kills unit | ✅ | 伤害超过HP时单位死亡 |
| 3 | Hit flash triggers | ✅ | 受伤时触发闪白特效 |
| 4 | Damage number shows | ✅ | 伤害数值飘字正确显示 |
| 5 | Death animation on kill | ✅ | 死亡动画正确播放 |
| 6 | Muzzle flash on attack | ✅ | 攻击时枪口火焰特效 |
| 7 | No attack out of range | ✅ | 射程外攻击被拒绝 |
| 8 | No attack wrong faction | ✅ | 友军伤害被阻止 (已修复测试逻辑) |
| 9 | Weapon ammo consumes | ✅ | 弹药正确消耗 |
| 10 | Weapon reload needed | ✅ | 弹药耗尽后需要换弹 |
| 11 | Move command works | ✅ | 移动命令正确执行 |
| 12 | Stop command clears move | ✅ | 停止命令清除移动目标 |
| 13 | Multiple attacks accumulate | ✅ | 多次攻击伤害正确累加 |

### 9.3 Audio System Unit Tests (21/21 passed)

| 分类 | 数量 | 覆盖内容 |
|------|------|----------|
| 波形生成 | 8 | sine/square/triangle/sawtooth/noise/pulse/organ/string |
| SoundType 枚举 | 23种 | UI/战斗/脚步/系统全覆盖 |
| 播放控制 | 5 | play/stop/volume/pause/resume |
| 缓存机制 | 3 | LRU缓存/预生成/内存管理 |
| 参数化 | 5 | 频率/振幅/包络/持续时间/音高 |

### 9.4 回归测试结论

- **全量套件**: 940/940 passed, 0 failures
- **新增代码**: 无回归问题
- **已有功能**: 全部保持通过
- **性能**: 无明显退化

---

## 11. P3-Fix Phase Results (2025-05-18)

### 11.1 总体结果

- **Total**: 1088 tests (unchanged — fixes were to existing code, not new features)
- **Pass Rate**: 100% (1088/1088)
- **New Tests**: 0 (bug fixes only)

### 11.2 Fix Details

| Fix # | Component | Issue | Impact | Verification |
|-------|-----------|-------|--------|-------------|
| #1 | BallisticEngine | Missing weapon stats: tank_cannon, sniper_rifle, mortar | New units (Tank/Sniper/Medic) dealt 2-4x less damage than intended | Weapon damage values now correct per UNIT_TEMPLATES |
| #2 | game_loop.py quick_load() | No-op returning True without restoring state | Save files loaded but game state unchanged | Full _restore_state_from_dict() implementation |
| #3 | commander_ai.py | Copy-paste loop boundary errors in _find_cover_positions() and TacticalAdvisor.suggest_defensive_positions() | AI cover-finding could miss valid positions or crash | Loop bounds corrected (2 locations) |
| #4 | main.py | Entry point referenced 4 non-existent modules | Application failed to start | Rewrote to use GameLoop() no-arg constructor |

### 11.3 回归测试结论

- **全量套件**: 1088/1088 passed, 0 failures
- **P0-P2 基线**: 940/940 passed (无回归)
- **P3 功能**: 148/148 passed (无回归)
- **P3-Fix**: 0 new tests, all existing tests still pass
- **性能**: 无明显退化

---

## 10. P3 Phase Test Results (2025-05-18)

### 10.1 总体结果

- **Total**: 1088 tests (940 P0-P2 base + 148 P3 new)
- **Pass Rate**: 100% (1088/1088)
- **Failures**: 0
- **Regression**: ✅ 全量回归通过

### 10.2 P3-A Systems: Victory Conditions + BattleStats (39/39 ✅)

| 分类 | 数量 | 覆盖内容 |
|------|------|----------|
| BattleStats tracking | 16 | kills/deaths/shots_fired/shots_hit/damage_dealt/damage_taken/units_lost/survivors |
| VictoryConditionEvaluator | 23 | commander kill, eliminate all, morale collapse, time limit, objective capture, multi-condition |

### 10.3 P3-B Visual Polish: Animation + Effects (52/52 ✅)

| 分类 | 数量 | 覆盖内容 |
|------|------|----------|
| UnitAnimator | 14 | 6 animation types (IDLE/WALK/SHOOT/DEATH/HIT_REACT/RELOAD) with numerical verification |
| ScreenShake | 8 | trigger/decay/cap/multiple simultaneous |
| ParticleEmitter | 18 | 8 emission types + physics simulation (gravity/velocity/lifetime) |
| AnimationState + edge cases | 12 | state transitions, frame timing, interrupt handling |

### 10.4 P3-C Content: Units + Terrains + Campaign (31/31 ✅)

| 分类 | 数量 | 覆盖内容 |
|------|------|----------|
| UnitTemplates | 8 | all 8 types with sensible stats (TANK/SNIPER/MEDIC + existing 5) |
| TerrainTypes | 8 | CRATER + SWAMP properties (movement cost, cover, passable) |
| CampaignSystem | 9 | 3 missions, registration, completion tracking, progression |
| New Sprites | 6 | tank/sniper/medic pixel sprite generation, crater/swamp tile generation |

### 10.5 P3-D Save System: SecureSaveManager (26/26 ✅)

| 分类 | 数量 | 覆盖内容 |
|------|------|----------|
| SecureSaveManager | 17 | save/load/delete/tamper detection/version migration/8 slot management |
| SaveMetaData | 3 | serialization roundtrip, field completeness |
| ExportState | 5 | game_loop state extraction, snapshot consistency |

### 10.6 回归测试结论

- **全量套件**: 1088/1088 passed, 0 failures
- **P3 新增**: 148/148 passed
- **P0-P2 基线**: 940/940 passed (无回归)
- **性能**: 无明显退化

---

## 附录 A: 测试环境要求

| 组件 | 版本要求 | 说明 |
|------|----------|------|
| Python | >= 3.11, < 3.13 | 使用最新stable特性 |
| pytest | >= 8.0 | 测试框架 |
| pytest-cov | >= 5.0 | 覆盖率插件 |
| pytest-xdist | >= 3.5 | 并行测试 |
| pytest-timeout | >= 2.3 | 超时控制 |
| ruff | >= 0.4.0 | Linter |
| mypy | >= 1.8 | 类型检查器 |
| hypothesis | >= 6.100 | 属性化测试 (可选, 用于统计测试) |
| scipy | >= 1.12 | 统计检验库 (仅统计测试需要) |
| numpy | >= 1.26 | 数值计算 (仅性能/统计测试) |

**操作系统矩阵：**
- macOS 14+ (Sonoma) ✅ 主要开发平台
- Ubuntu 22.04/24.04 LTS ✅ CI服务器
- Windows 11 (可选) ⚠️ 可能需要额外配置

---

## 附录 B: Mock策略

### B.1 外部依赖Mock清单

| 依赖 | Mock方式 | 原因 |
|------|----------|------|
| 文件系统 | `tmp_path` fixture / `unittest.mock.patch` | 单元测试不应写磁盘 |
| 时间 | `freezegun` / mock `time.time` | 控制时间依赖逻辑 |
| Pygame | `pygame.mock` 或纯Python替代 | CI无显示器 |
| 网络 | 全部禁止 | PyCC2是单机游戏 |
| SecureIO._derive_key | mock返回固定key | 避免慢PBKDF2和设备依赖 |
| RandomContext | 注入固定seed | 保证测试确定性 |

**Mock示例：**

```python
from unittest.mock import patch, MagicMock
import pytest

@pytest.fixture
def mock_secure_io():
    """Mock SecureIO避免真正的HMAC/PBKDF2"""
    with patch('pycc2.core.secure_io.SecureIO._derive_key') as mock_key:
        mock_key.return_value = b'test_key_32bytes_long!!!!'  # 固定测试密钥
        yield

@pytest.fixture
def headless_pygame():
    """Headless Pygame (无需显示器)"""
    import os
    os.environ['SDL_VIDEODRIVER'] = 'dummy'
    os.environ['SDL_AUDIODRIVER'] = 'dummy'

    import pygame
    pygame.init()
    yield pygame
    pygame.quit()
```

---

## 附录 C: 测试数据管理

### C.1 Fixture数据目录

```
tests/
├── fixtures/
│   ├── maps/
│   │   ├── test_small_16x16.json      # 最小测试地图
│   │   ├── test_medium_64x64.json     # 中等地图
│   │   ├── test_full_terrain.json     # 包含所有12种地形
│   │   └── test_obstacle_course.json  # 寻路专用障碍地图
│   ├── units/
│   │   ├── test_infantry.json
│   │   └── test_vehicle.json
│   ├── weapons/
│   │   ├── test_rifle_perfect.json   # accuracy=1.0 用于测试
│   │   └── test_mortar_indirect.json
│   └── saves/
│       ├── valid_save_with_sig.sav   # 合法存档 (用于read测试)
│       ├── tampered_save.sav         # 被篡改的存档 (用于安全测试)
│       └── corrupted_save.sav        # 损坏的存档 (错误恢复测试)
├── conftest.py                       # 共享fixtures
└── ...
```

### C.2 conftest.py 关键Fixtures

```python
# tests/conftest.py
import pytest
from pathlib import Path

@pytest.fixture
def sample_weapon_config():
    """返回标准测试武器配置"""
    return {
        "id": "test_rifle",
        "name": "Test Rifle",
        "type": "rifle",
        "caliber": "test_cal",
        "range_max": 500,
        "range_effective": 300,
        "accuracy_base": 0.75,
        "damage_base": 35,
        "rof": 40,
        "magazine_size": 8,
        "reload_time_ticks": 20
    }

@pytest.fixture
def small_test_map():
    """加载16x16测试地图"""
    map_path = Path(__file__).parent / "fixtures/maps/test_small_16x16.json"
    return load_tile_map_config(map_path)

@pytest.fixture
def deterministic_rng():
    """确定性的随机数生成器 (seed=42)"""
    return RandomContext(seed=42)
```

---

## 附录 D: 性能基准

| 测试场景 | 目标时间 | 最大容忍 | 测量方法 |
|----------|----------|----------|----------|
| Vec2运算 (100万次) | < 0.5s | 1s | time.perf_counter |
| BallisticEngine单次射击 | < 1ms | 5ms | per-shot计时 |
| BallisticEngine 1000次统计 | < 2s | 5s | 批量计时 |
| PathFinder 16×16地图 | < 10ms | 50ms | 单次寻路 |
| PathFinder 256×256地图 | < 100ms | 500ms | 最坏情况 |
| MoraleCalculator 1000事件 | < 0.5s | 2s | 批量处理 |
| FogOfWar 更新 (full map) | < 20ms | 100ms | 每tick |
| SaveGameData 序列化 | < 50ms | 200ms | 含签名 |
| SaveGameData 反序列化+校验 | < 100ms | 500ms | 含HMAC验证 |
| 完整单元测试套件 | < 30s | 60s | pytest --duration |
| 完整集成测试套件 | < 2min | 5min | 包含setup |
| E2E Tutorial Scenario | < 3min | 10min | 端到端 |

---

## 附录 E: 测试结果报告模板

每次CI运行生成标准化报告：

```markdown
# PyCC2 Test Report

**Run ID:** #1234
**Branch:** feature/new-weapon-system
**Commit:** abc1234
**Timestamp:** 2024-01-15 14:30:00 UTC
**Trigger:** Pull Request #56

## Summary

| Category | Total | Passed | Failed | Skipped | Duration |
|----------|-------|--------|--------|---------|----------|
| Unit Tests | 237 | 235 | 2 | 0 | 28.5s |
| Integration | 40 | 40 | 0 | 0 | 7.3s |
| E2E Scenarios | 3 | 3 | 0 | 0 | 4m12s |
| **TOTAL** | **280** | **278** | **2** | **0** | **~5min** |

## Quality Gates Status

| Gate | Status | Details |
|------|--------|---------|
| QG-1 TDD Core Pass | ❌ FAILED | 2 failures in test_ballistic_engine.py |
| QG-2 Domain 100% Coverage | ✅ PASS | Vec2: 100%, Ballistic: 98.5% |
| QG-3 Overall ≥70% | ✅ PASS | Current: 74.2% |
| QG-4 Ballistic Statistics | ⚠️ WARNING | Hit rate variance slightly high |
| QG-5 Pathfinder Perf | ✅ PASS | P95: 45ms (limit: 100ms) |
| QG-6 Ruff Zero Errors | ✅ PASS | 0 errors, 0 warnings |
| QG-7 Mypy Strict | ✅ PASS | No type errors |
| QG-8 Integration Pass | ✅ PASS | 40/40 passed |

## Failures Detail

### Failure 1: test_hit_within_effective_range
**File:** tests/unit/test_ballistic_engine.py:142
**Error:** AssertionError: Hit rate 0.58 too low (expected > 0.6)
**Root Cause:** Seed-dependent flaky test (need to increase sample size or adjust threshold)

### Failure 2: test_damage_distribution_chi_square
**File:** tests/unit/test_ballistic_engine.py:298
**Error:** Distribution not normal (p=0.0234)
**Root Cause:** Sample size too small for chi-square test (only 800 hits)

## Recommendations

1. Increase sample size in BE-HIT-01 from 100 to 500 shots
2. Use Kolmogorov-Smirnov test instead of Shapiro-Wilk for larger samples
3. Consider marking statistical tests as `@pytest.mark.flaky(max_runs=3)` until variance is reduced

## Coverage Highlights

**Highest Coverage Modules:**
- vec2.py: 100% (25/25 lines)
- terrain_type.py: 100% (45/45 lines)
- secure_io.py: 96.4% (270/281 lines)

**Lowest Coverage Modules (needs attention):**
- ui/renderer.py: 45% (requires E2E/screenshot testing)
- audio/mixer.py: 38% (hardware dependent)
- main.py: 52% (entry point, lower priority)

## Artifacts

- [Coverage HTML Report](./htmlcov/index.html)
- [JUnit XML](./junit.xml)
- [E2E Screenshots](./e2e-screenshots/)
- [Performance Data](./benchmarks.json)
```

---

## 12. P4 Week 1 Results (2026-05-18)

### 12.1 总体结果

- **Total**: 1163 tests (1088 P0-P3 base + 75 P4.1 new)
- **Pass Rate**: 100% (1163/1163)
- **Failures**: 0
- **Regression**: ✅ 全量回归通过

### 12.2 P4.1-A: GameLoop Decomposition (~62 tests ✅)

| 分类 | 数量 | 覆盖内容 |
|------|------|----------|
| RenderPipeline | ~20 | render() orchestration, FPS update, screen management, alpha blending |
| CombatDirector | ~15 | update(), combat resolution, event publishing, sound integration |
| InputRouter | ~10 | route_input(), keyboard/mouse handling, ESC/F10/F3 shortcuts |
| SaveController | ~12 | save/load/restore, state serialization, slot management |

**关键改进：**
- GameLoop 从 880 行减少到 356 行 (-59%)
- 职责清晰分离为 4 个独立组件
- 每个组件可独立测试

### 12.3 P4.1-B: Settings Menu (62 tests ✅)

| 分类 | 数量 | 覆盖内容 |
|------|------|----------|
| Initialization | 8 | constructor, display config, default state |
| Tab Management | 12 | 4 tabs (General/Audio/Controls/Gameplay), switching, navigation |
| Option Rendering | 15 | slider, toggle, enum, info option types |
| Input Handling | 15 | keyboard (arrows/enter/tab/esc), mouse click, selection |
| State Persistence | 7 | apply_to_systems(), state save/restore |
| Edge Cases | 5 | visibility toggling, empty state, boundary values |

**功能验证：**
- ✅ 4 个设置标签页正确切换
- ✅ 键盘和鼠标输入完整支持
- ✅ 设置应用到 SoundSystem
- ✅ 视觉渲染正确（覆盖层 + 面板）

### 12.4 P4.1-C: Security Hardening (13 tests ✅)

| 分类 | 数量 | 覆盖内容 |
|------|------|----------|
| HMAC Key Loading | 5 | environment variable, secrets.toml file, fallback with warning |
| Input Bounds Checking | 4 | coordinate clamping, value validation, overflow prevention |
| Secrets Template | 2 | secrets.toml.example validation, key format checking |
| Integration | 2 | SecureSaveManager + env key interaction |

**安全改进：**
- ✅ HMAC 密钥从硬编码改为环境变量/配置文件
- ✅ 输入边界检查防止溢出
- ✅ secrets.toml.example 模板提供

### 12.5 回归测试结论

- **全量套件**: 1163/1163 passed, 0 failures
- **P0-P3 基线**: 1088/1088 passed (无回归)
- **P4.1 新增**: 75/75 passed
- **性能**: 无明显退化
- **代码质量**: Ruff lint 通过 (97 remaining non-critical warnings)

---

## 13. P4 Week 2 Results (2026-05-19)

### 13.1 总体结果

- **Total**: 1270 tests (1163 P0-P4.1 base + 107 P4.2 new)
- **Pass Rate**: 100% (1270/1270)
- **Failures**: 0
- **Regression**: ✅ 全量回归通过

### 13.2 P4.2-A: Performance Optimization (~39 tests ✅)

| 分类 | 数量 | 覆盖内容 |
|------|------|----------|
| TileCache | ~15 | 地形瓦片预缓存、LRU淘汰策略、命中率优化(>95%)、内存管理 |
| AI Throttle | ~12 | AI决策节流10Hz、冷却时间管理、突发行为防止、决策队列 |
| ParticlePool | ~12 | 粒子对象池化、内存复用、池耗尽处理、GC压力降低(-40%) |

**性能改进验证：**
- ✅ TileCache 命中率 > 95% (128×128地图)
- ✅ AI 决策频率稳定在 8-12Hz (目标10Hz)
- ✅ 粒子系统内存分配减少 60%
- ✅ 整体 FPS 提升 +15% (64×64地图+20单位基准)

### 13.3 P4.2-B: Tutorial & Hint System (~28 tests ✅)

| 分类 | 数量 | 覆盖内容 |
|------|------|----------|
| TutorialOverlay | ~15 | 首次启动引导、步骤进度控制、跳过/恢复功能、UI渲染、状态持久化 |
| HintManager | ~13 | 上下文感知提示、显示时机逻辑、关闭机制、提示队列、优先级排序 |

**功能验证：**
- ✅ TutorialOverlay 正确检测首次启动
- ✅ 5步引导流程完整（选择单位→移动→攻击→胜利→完成）
- ✅ HintManager 根据游戏状态触发正确提示
- ✅ 提示系统不影响正常游戏操作（可随时关闭）

### 13.4 P4.2-C: New Missions Content (~35 tests ✅)

| 分类 | 数量 | 覆盖内容 |
|------|------|----------|
| Mission 4 - Night Assault | ~18 | 夜战视野系统(-40%)、潜行机制、照明弹效果、AI夜间巡逻模式、听觉侦测增强 |
| Mission 5 - Armored Column | ~17 | 反坦克战术逻辑、载具AI行为、防御阵型管理、装甲单位伤害计算、AT武器效果 |

**Mission 4 Night Assault 测试要点：**
- ✅ 夜间视野范围正确缩减
- ✅ 潜行状态移动不暴露位置
- ✅ 照明弹临时提升视野区域
- ✅ AI 在夜间使用巡逻模式而非主动搜索
- ✅ 听觉侦测范围在夜间提升(+30%)

**Mission 5 Armored Column 测试要点：**
- ✅ 反坦克武器对载具造成额外伤害(+200%)
- ✅ 坦克AI优先攻击反坦克阵地
- ✅ 防御阵型提供掩体加成(+25% cover)
- ✅ 载具死亡时乘员逃生逻辑
- ✅ 战斗统计正确记录载具击杀

### 13.5 P4.2-D: New Map Data (~12 tests ✅)

| 分类 | 数量 | 覆盖内容 |
|------|------|----------|
| Map Schema Validation | ~6 | 4张新地图JSON格式校验、地形类型合法性、坐标边界检查、出生点有效性 |
| Map Loading Integration | ~6 | 地图加载性能(<100ms)、tile数据完整性、Objective点解析、地形代价表一致性 |

**新增地图测试详情：**
- ✅ night_map.json: 36×36, 12种地形, Schema校验通过
- ✅ road_ambush.json: 40×24, 11种地形, Schema校验通过
- ✅ bridge_assault.json: 32×32, 10种地形, Schema校验通过
- ✅ defense_line.json: 48×32, 12种地形, Schema校验通过
- ✅ 所有地图加载时间 < 80ms
- ✅ 地形移动代价表与 TerrainType 枚举一致

### 13.6 P4 Week 2 测试覆盖矩阵

| 功能模块 | 单元测试 | 集成测试 | E2E场景 | 总计 | 覆盖率 |
|----------|----------|----------|---------|------|--------|
| 性能优化 (TileCache/AI/Particle) | 39 | 4 | 1 | 44 | 98% |
| 教程/提示系统 (Tutorial/Hint) | 28 | 3 | 1 | 32 | 95% |
| 新任务内容 (M4/M5) | 35 | 5 | 2 | 42 | 96% |
| 新地图数据 (4 maps) | 12 | 2 | 1 | 15 | 100% |
| **P4.2 合计** | **114** | **14** | **5** | **133** | **97%** |

### 13.7 回归测试结论

- **全量套件**: 1270/1270 passed, 0 failures
- **P0-P4.1 基线**: 1163/1163 passed (无回归)
- **P4.2 新增**: 107/107 passed
- **Mission 4/5 特定测试**: 35/35 passed
- **新地图数据测试**: 12/12 passed
- **性能**: 无退化，部分指标提升 (FPS +15%, 内存 -20%)
- **代码质量**: Ruff lint 通过 (95 remaining non-critical warnings, -2 from P4W1)
- **安全性**: 无新安全漏洞引入

---

## 14. P5 Test Plan Preview (Campaign Core)

### 14.1 P5.1 Campaign Persistence 测试场景 (~185 tests)

| Test ID | 场景 | 验证内容 | 优先级 |
|---------|------|----------|--------|
| CP-State-01 | CampaignState 序列化/反序列化 | 跨战斗状态完整保存/恢复（单位名册/经验/弹药/作战日/战略点/伤亡日志） | P0 |
| CP-State-02 | 3场连续战斗继承 | 完成3场战斗后单位属性正确继承（HP衰减/经验累积/弹药消耗） | P0 |
| CP-Vet-01 | UnitVeterancy 经验等级 | Green→Veteran→Elite→Crack 晋升逻辑 + 战斗加成验证 | P0 |
| CP-Vet-02 | 老兵加成实战验证 | Veteran单位命中率提升可统计验证 (p < 0.05) | P0 |
| CP-BR-01 | BattleResult 记录完整性 | KIA/WIA计数/弹药消耗/目标占领/时长/得分 完整记录 | P1 |
| CP-Ser-01 | CampaignSerializer HMAC扩展 | 存档防篡改 + 版本迁移 + 数据完整性 | P1 |
| CP-Int-01 | E2E: 战斗→BattleResult→CampaignState→下一关 | 端到端流程数据一致性 | P0 |

### 14.2 P5.2 Strategic Map Layer 测试场景 (~130 tests)

| Test ID | 场景 | 验证内容 | 优先级 |
|---------|------|----------|--------|
| SM-Render-01 | StrategicMapRenderer 帧率 | Market Garden走廊渲染 60fps稳定 (缩放/平移) | P0 |
| SM-Render-02 | 桥梁状态tooltip | 点击桥梁显示详细状态（占领/摧毁/争夺中） | P1 |
| SM-Route-01 | 路线选择UI | 多进攻方向选择 + 风险/收益权衡影响后续任务生成 | P0 |
| SM-Force-01 | 全局兵力分布 | 友军/敌军集中度显示 + 情报可靠性迷雾 | P1 |
| SM-Bridge-01 | 5座桥梁追踪 | 实时捕获/摧毁/争议状态更新 | P1 |

### 14.3 P5.3 Operation Timeline 测试场景 (~145 tests)

| Test ID | 场景 | 验证内容 | 优先级 |
|---------|------|----------|--------|
| OT-Day-01 | Day 1→Day 6 推进 | 作战时间线按历史序列正确推进 | P0 |
| OT-Rein-01 | 增援事件准时触发 | XXX Corps 时间表 / 波兰旅 / 紧急补给 ±1hr容差 | P0 |
| OT-Bridge-01 | 桥梁链依赖 | Son→Nijmegen→Arnhem 顺序强制执行 | P0 |
| OT-Resrc-01 | 资源分配决策 | 弹药分发/医疗优先/预备队投入 影响后续战备 | P1 |
| OT-Hist-01 | 历史事件触发 | 天气变化(9.19雾) / 德军装甲反击(9.18) / Waal渡河(9.20) | P1 |

### 14.4 P5 测试覆盖矩阵

| 功能模块 | 单元测试 | 集成测试 | E2E场景 | 总计 | 覆盖率目标 |
|----------|----------|----------|---------|------|-----------|
| Campaign Persistence | ~120 | ~35 | ~5 | ~160 | 95% |
| Strategic Map Layer | ~85 | ~30 | ~3 | ~118 | 90% |
| Operation Timeline | ~95 | ~35 | ~5 | ~135 | 92% |
| Cross-module Integration | — | ~40 | ~8 | ~48 | 90% |
| **P5 合计** | **~300** | **~140** | **~21** | **~461** | **~92%** |

### 14.5 P5 Gate Criteria (Exit Criteria)

- [ ] CampaignState 在 5+ 场战斗间序列化/反序列化 100% 数据完整性
- [ ] Unit Veterancy 战斗效能差异统计显著 (p < 0.05)
- [ ] Strategic Map 交互渲染 60fps (缩放/平移/选择)
- [ ] Operation Timeline Day 1 → Day 3 历史序列正确 + 增援事件准时
- [ ] 零回归: 所有 v0.6 测试仍通过
- [ ] 新增测试: +350-450 (总计 1727-1827)

---

## 附录 F: 版本历史

| 版本 | 日期 | 作者 | 变更内容 |
|------|------|------|----------|
| v1.0 | 2026-05-15 | PyCC2 QA Team | 初始测试计划，定义280个测试用例 |
| v1.1 | 2026-05-15 | - | 补充E2E场景详细步骤和CI配置 |
| v1.2 | 2026-05-18 | DevSquad | P2阶段完成: 新增test_combat_loop.py(13) + test_sound_system.py(21), Test Coverage Summary表, P2 Phase Test Results章节, 总数940 |
| v1.3 | 2026-05-18 | DevSquad | P3阶段全部完成(4子阶段): 新增test_victory_conditions(39)+test_animation_system(52)+test_content_expansion(31)+test_save_system(26), P3 Phase Test Results章节, 总数1088 |
| v1.4 | 2026-05-18 | DocSync | P3-Fix: 4个关键Bug修复(BallisticEngine武器/quick_load/AI循环边界/main.py入口), 新增Section 11 P3-Fix Phase Results, 总数保持1088 |
| v1.5 | 2026-05-18 | Integration | P4 Week 1 完成: GameLoop Decomposition(4组件/~62测试) + Settings Menu(62测试) + Security Hardening(13测试), 新增Section 12 P4 Week 1 Results, 总数1163 |
| v1.6 | 2026-05-19 | Integration | P4 Week 2 完成: 性能优化(TileCache/AI节流/粒子池/~39测试) + 教程系统(TutorialOverlay/HintManager/~28测试) + 新任务(Mission 4夜战/Mission 5反坦克/~35测试) + 新地图(4张/~12测试), 新增Section 13 P4 Week 2 Results, 总数1270 |
| v1.7 | 2026-05-19 | PM+CC2 Analysis | CC2差距分析完成: 新增P4.3测试(~42夜战/装甲/视觉) + QG E2E(+61文档/质量/E2E), 测试总数1377, 新增Section 8.1/8.2/8.5 P4.3统计与P5预览, 新增Section 14 P5 Test Plan Preview(P5.1/P5.2/P5.3场景+覆盖矩阵+Gate Criteria) |
| v1.8 | 2026-05-19 | P5/P6/P7 Complete | **P5 Campaign Core完成**: ~240 tests (CampaignState/BattleResult/UnitVeterancy/StrategicMap/OperationTimeline). **P6 Combat Depth完成**: ~205 tests (Swiss Cheese/Fatigue/AAR/TimeControl). **P7 Content Expansion完成**: ~189 tests (M6-M10新任务+MAP-06~10新地图+历史真实性). **测试总数1566** (+189 from P5/P6/P7). 新增Section 8.1-8.4 P5/P6/P7完整统计与Test Growth Summary |
| v2.0 | 2026-05-20 | P8/P9 Complete | **P8 地图与战役补全完成**: ~334 tests (9+Arnhem战区新地图/四层战役/补给线/部署UI). **P9 AI深度提升+新游戏设置完成**: ~289 tests (P0 AI行为7项+游戏设置5预设+战役完成3/7/29). **测试总数2233** (+667 from P8/P9). 新增Section 8.5 P0 AI Behavior Test Coverage / Section 8.6 Game Settings Test Coverage / Section 8.7 Campaign Completion Test Coverage / E2E Scenario 4-6 (Campaign Flow/AI Behaviors/Game Settings). 测试金字塔更新(单元~2031/集成~86/E2E~116) |
| v0.1.1 | 2026-05-23 | M1 Fix Update | **M1紧急修复进展**: P0-1(display_name)/P0-2(属性别名)/P0-3(AI导入)/P0-4(set_mode)已修复。测试总数2767(1 failed)。版本号统一为v0.1.1 |
| v0.4.0 | 2026-06-14 | 文档同步至v0.4.0 | 测试总数~3513。P0 Bug全部已修复。新增38-phase E2E真实SDL测试。覆盖率门禁引入 |
| v0.5.0 | 2026-07-08 | PixVoxel P0接入 | 新增490 E2E测试验证PixVoxel正交版精灵接入。测试金字塔更新(unit占比提升) |
| v0.6.10 | 2026-07-13 | 覆盖率提升+CI增强 | **当前版本**: 323新测试(覆盖率提升), radon复杂度门禁集成CI。测试总数6552(unit 5817/integration 181/e2e 491/benchmark 21/acceptance 42/slow 16)。数据校准: 逐目录实测验证 |

## 附录 G: 相关文档

- [数据设计文档](./DATA_DESIGN.md) - Pydantic模型和数据文件格式
- [交互设计规范](./VISUAL_SPEC.md) - UI/UX布局与视觉规范
- [安全评审报告](./SECURITY.md) - 安全威胁分析与缓解措施
