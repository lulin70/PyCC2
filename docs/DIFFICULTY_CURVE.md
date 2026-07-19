# PyCC2 难度曲线设计文档 v0.8.0

**Status**: 🚧 设计中
**Created**: 2026-07-18
**Version**: 0.8.0
**Companion**: [ROADMAP_v0.8.0.md](ROADMAP_v0.8.0.md)

## 1. 设计目标

PyCC2 是一款 WWII 战术战斗模拟器，难度系统的目标是:
1. **新用户友好**: EASY 难度让新手能在 10 分钟内理解核心机制并获胜
2. **渐进式挑战**: 4 级难度提供平滑递进，避免断崖式跳跃
3. **AI 行为差异化**: 不同难度的 AI 应有可感知的战术差异 (不仅限于数值调整)
4. **教学融入**: 新手引导系统应与难度曲线协同，逐步解锁战术概念

## 2. 4 级难度设计

### 2.1 难度等级概览

| 等级 | 名称 | 目标用户 | 学习目标 | AI 行为特征 |
|------|------|---------|---------|------------|
| EASY | 新兵 | 首次接触战术游戏 | 基本操作 (选/移/攻) + 胜利条件 | 反应慢、命中率低、不使用高级战术 |
| MEDIUM | 士兵 | 有 RTS 基础的玩家 | 掩体使用 + 烟雾弹 + 基础战术 | 标准反应、正常命中率、不用侧翼/压制 |
| HARD | 老兵 | 熟悉 CC2 系列的玩家 | 侧翼包抄 + 压制火力 + 协同 | 快速反应、高命中率、使用侧翼/压制 |
| VETERAN | 精锐 | 战术游戏高手 | 全战术应用 + 资源管理 | 极速反应、极高命中率、全战术 + 协同 |

### 2.2 DifficultyConfig 参数递进逻辑

基于 `src/pycc2/domain/ai/difficulty_system.py` 的 PRESETS，4 级难度的参数递进遵循以下原则:

#### 感知层 (Perception)

| 参数 | EASY | MEDIUM | HARD | VETERAN | 递进逻辑 |
|------|------|--------|------|---------|---------|
| vision_range_multiplier | 0.7 | 1.0 | 1.2 | 1.4 | 视野范围递增 30% → 20% → 17% |
| perception_accuracy | 0.6 | 1.0 | 1.0 | 1.0 | EASY 有 40% 概率丢失目标，MEDIUM+ 完全感知 |
| reaction_delay_ticks | 15 | 0 | 0 | 0 | EASY 反应延迟 15 ticks (约 0.5 秒)，MEDIUM+ 即时反应 |

#### 战斗层 (Combat)

| 参数 | EASY | MEDIUM | HARD | VETERAN | 递进逻辑 |
|------|------|--------|------|---------|---------|
| base_hit_chance | 0.25 | 0.5 | 0.65 | 0.75 | 命中率递增 25pp → 15pp → 10pp |
| aim_time_multiplier | 2.0 | 1.0 | 0.7 | 0.5 | 瞄准时间递减 50% → 30% → 29% |
| suppress_effectiveness | 0.5 | 1.0 | 1.3 | 1.5 | 压制效果递增 100% → 30% → 15% |

#### 战术层 (Tactics)

| 参数 | EASY | MEDIUM | HARD | VETERAN | 递进逻辑 |
|------|------|--------|------|---------|---------|
| tactical_variety | 0.8 | 1.0 | 0.6 | 0.3 | EASY 高多样性 (随机性强) → VETERAN 低多样性 (专注最优战术) |
| retreat_threshold | 0.5 | 0.3 | 0.2 | 0.15 | 撤退阈值递减 (高难度更顽固) |
| aggressiveness | 0.2 | 0.5 | 0.75 | 0.9 | 攻击性递增 30pp → 25pp → 15pp |
| coordination_enabled | False | False | True | True | MEDIUM 及以下不协同，HARD+ 协同 |
| use_flanking | False | False | True | True | 侧翼包抄仅在 HARD+ 启用 |
| use_suppression_tactics | False | False | True | True | 压制战术仅在 HARD+ 启用 |

#### 资源层 (Resources)

| 参数 | EASY | MEDIUM | HARD | VETERAN | 递进逻辑 |
|------|------|--------|------|---------|---------|
| ammo_conservation | 0.3 | 1.0 | 1.0 | 1.0 | EASY 浪费弹药 (60% 概率不射击)，MEDIUM+ 节约 |
| burst_size | 2 | 3 | 4 | 5 | 连发弹数递增 |
| burst_interval_ticks | 60 | 30 | 20 | 15 | 连发间隔递减 |

#### 士气层 (Morale)

| 参数 | EASY | MEDIUM | HARD | VETERAN | 递进逻辑 |
|------|------|--------|------|---------|---------|
| morale_stability | 1.5 | 1.0 | 0.85 | 0.7 | 士气稳定性递减 (高难度 AI 更易崩溃) |
| panic_contagion_range | 3.0 | 5.0 | 6.0 | 7.0 | 恐慌传染范围递增 |

### 2.3 参数递进设计原则

1. **感知先行**: 低难度 AI 感知能力受限 (视野/精度/反应)，给玩家时间学习操作
2. **战斗递进**: 命中率/瞄准时间递进让玩家感受到 AI 越来越精准
3. **战术解锁**: 高级战术 (侧翼/压制/协同) 在 HARD+ 解锁，给玩家进阶目标
4. **资源管理**: EASY 浪费弹药让玩家有更多容错空间
5. **士气平衡**: 高难度 AI 士气更脆弱 (compensation for 更强战斗能力)

## 3. 新手引导系统扩展

### 3.1 现状

`TutorialStep` 6 步:
1. WELCOME — 欢迎界面 + 操作说明
2. SELECT_UNIT — 选择单位
3. MOVE_UNIT — 移动单位
4. ATTACK_ENEMY — 攻击敌人
5. VICTORY_CONDITIONS — 胜利条件
6. COMPLETE — 完成

### 3.2 扩展方案 (v0.8.0: 6→10 步)

在 ATTACK_ENEMY 和 VICTORY_CONDITIONS 之间插入 4 步战术教学:

| 步骤 | 名称 | 教学内容 | 触发条件 |
|------|------|---------|---------|
| 5 | USE_COVER | 掩体使用: 树林/建筑提供掩护但减速移动 | 玩家单位进入树林/建筑时 |
| 6 | SMOKE_GRENADE | 烟雾弹: 按 G 部署烟雾遮蔽视线，掩护移动 | 玩家拥有烟雾弹单位时 |
| 7 | FLANKING | 侧翼包抄: 从侧面攻击敌人效果更好 (降低敌人还击) | 玩家单位位于敌人侧翼时 |
| 8 | SUPPRESSION | 压制火力: MG 单位可压制敌人降低其还击精度 | 玩家拥有 MG 单位时 |

### 3.3 教学引导与难度协同

| 难度 | 引导策略 |
|------|---------|
| EASY | 全 10 步引导强制显示，contextual hints 频繁触发 |
| MEDIUM | 全 10 步引导可选显示 (玩家可跳过)，contextual hints 适度 |
| HARD | 仅显示新增 4 步战术教学 (假设玩家已掌握基础) |
| VETERAN | 不显示引导，仅 contextual hints 在首次遇到新战术时提示 |

## 4. AI 难度缩放全覆盖

### 4.1 现状 (v0.7.7)

7/9 AI 模块已接入 DifficultySystem:
- ✅ tactical_flanking (use_flanking, aggressiveness)
- ✅ tactical_suppression (use_suppression_tactics, suppress_effectiveness)
- ✅ tactical_coordination (coordination_enabled, aggressiveness)
- ✅ smoke_tactical_ai (aggressiveness)
- ✅ at_ambush_ai (aggressiveness)
- ✅ combat_engagement (aggressiveness, base_hit_chance, ammo_conservation)
- ✅ commander_ai (通过 TacticalContext)

2/9 未接入:
- ❌ recon_ai — 硬编码 `_MIN_EXPECTED_ENEMY_FACTOR=0.5`, `_MAX_RECON_PER_TICK=3`
- ❌ supply_awareness_ai — 硬编码 `_THREAT_THRESHOLD=0.3`, `_ATTACK_ADVANTAGE_THRESHOLD=1.5`, `_SUPPLY_SCAN_RADIUS=8`

### 4.2 接入方案 (v0.8.0)

#### 4.2.1 recon_ai.py 接入

**接入点**: `ReconAI.evaluate(context)` 方法

**参数映射**:
```python
# 现状 (硬编码):
_MIN_EXPECTED_ENEMY_FACTOR = 0.5
_MAX_RECON_PER_TICK = 3

# v0.8.0 (动态化):
if context.difficulty_config is not None:
    cfg = context.difficulty_config
    # 低难度 → 期望敌人更少 (AI 更"乐观"，不积极侦察)
    min_expected_enemy = 0.5 * cfg.perception_accuracy
    # 低难度 → 战术多样性高 → 侦察次数少 (随机性分散)
    max_recon_per_tick = max(1, int(3 * cfg.tactical_variety))
    # 评分权重根据 aggressiveness 调整
    intel_weight = 0.5 * (1.0 - cfg.aggressiveness * 0.3)
    defensive_weight = 0.2 + cfg.aggressiveness * 0.3
else:
    # fallback 到原硬编码值
    min_expected_enemy = 0.5
    max_recon_per_tick = 3
    intel_weight = 0.5
    defensive_weight = 0.2
```

**预期效果**:
- EASY (perception_accuracy=0.6): `min_expected_enemy=0.30`, `max_recon_per_tick=2` → 侦察更少
- VETERAN (perception_accuracy=1.0, tactical_variety=0.3): `min_expected_enemy=0.50`, `max_recon_per_tick=1` → 专注最优侦察

#### 4.2.2 supply_awareness_ai.py 接入

**接入点**: `SupplyAwarenessAI.evaluate(context)` + `_identify_supply_points(context)` 方法

**参数映射**:
```python
# 现状 (硬编码):
_THREAT_THRESHOLD = 0.3
_ATTACK_ADVANTAGE_THRESHOLD = 1.5
_SUPPLY_SCAN_RADIUS = 8
_MAX_SUPPLY_ORDERS_PER_TICK = 3

# v0.8.0 (动态化):
if context.difficulty_config is not None:
    cfg = context.difficulty_config
    # 低难度 → 威胁阈值更高 (反应更慢)
    threat_threshold = 0.3 / cfg.perception_accuracy  # EASY: 0.5, VETERAN: 0.3
    # 低难度 → 攻击优势阈值更高 (更保守)
    attack_threshold = 1.5 * (1.5 - cfg.aggressiveness)  # EASY: 1.65, VETERAN: 0.975
    # 视野范围决定扫描半径
    scan_radius = max(3, int(8 * cfg.vision_range_multiplier))  # EASY: 5, VETERAN: 11
    # 战术多样性决定订单数
    max_orders = max(1, int(3 * cfg.tactical_variety))
else:
    # fallback 到原硬编码值
    threat_threshold = 0.3
    attack_threshold = 1.5
    scan_radius = 8
    max_orders = 3
```

**预期效果**:
- EASY (perception_accuracy=0.6, aggressiveness=0.2): 威胁阈值 0.5 (反应慢), 攻击阈值 1.65 (保守)
- VETERAN (perception_accuracy=1.0, aggressiveness=0.9): 威胁阈值 0.3 (敏感), 攻击阈值 0.975 (激进)

## 5. 测试策略

### 5.1 新增测试套件: tests/unit/ai/test_difficulty_scaling.py

| 测试用例 | 验证目标 | 断言 |
|---------|---------|------|
| test_easy_ai_recon_frequency_lower | EASY 侦察频率 < VETERAN | `easy_max_recon < veteran_max_recon` |
| test_easy_ai_supply_threshold_higher | EASY 补给威胁阈值 > VETERAN | `easy_threshold > veteran_threshold` |
| test_easy_ai_attack_advantage_threshold_higher | EASY 攻击阈值 > VETERAN | `easy_attack > veteran_attack` |
| test_veteran_ai_recon_scan_wider | VETERAN 扫描半径 > EASY | `veteran_radius > easy_radius` |
| test_difficulty_levels_progressive | 4 级难度参数递进 | 单调性验证 |
| test_recon_ai_respects_perception_accuracy | 侦察 AI 响应 perception_accuracy | 参数变化 → 行为变化 |
| test_supply_ai_respects_vision_range | 补给 AI 响应 vision_range_multiplier | 参数变化 → 行为变化 |

### 5.2 回归测试

- `tests/unit/test_recon_ai.py` — 现有测试通过 (fallback 路径保持兼容)
- `tests/unit/test_supply_awareness_ai.py` — 现有测试通过
- `tests/e2e/test_ai_behaviors_e2e.py` — E2E 行为一致

## 6. 验收标准

1. AI 难度缩放覆盖率 7/9 → 9/9 模块
2. TutorialStep 6 → 10 步 (新增 4 步战术教学)
3. test_difficulty_scaling.py ≥7 个测试全通过
4. 全量测试 6291+ passed 零回归
5. ruff 0 + mypy 0 + check_doc_consistency 11/11
6. 版本号 0.8.0 + 文档同步

## 7. 未来规划 (v0.9.0+)

- 难度配置外部化 (JSON/YAML 文件，便于 modder 调优)
- 动态难度调整 (基于玩家表现自动调整 AI 参数)
- 关卡-难度联动 (关卡进度影响 AI 难度)
- 难度专属剧情/对话 (不同难度有不同的战场叙事)
