# PyCC2 Phase 4-5 详细设计文档

> **创建日期**：2026-06-28
> **基线版本**：v0.4.0（Phase 1-3 已完成）
> **目标版本**：v0.5.0（Phase 4）→ v0.6.0（Phase 5）
> **依据**：D8_REMEDIATION_PLAN.md + 3 份 subagent 研究报告

---

## 一、关键发现（研究阶段产出）

### 1.1 GAP_ANALYSIS.md 文档矛盾
- R8（AI 伏击/撤退/反击）标记 "✅ RESOLVED v0.3.0" 但行为表标记 "❌ 未实现"
- R9（丘陵高度系统）标记 "✅ RESOLVED" 但实际数据管道断裂
- **结论**：以代码实际状态为准，文档标记不准确

### 1.2 TacticExecutor 缺口（P0 阻断项）
5 个 TacticType 有枚举无 handler，AI 意图会落空：
- `FLANKING`（FlankingAI 发出）
- `COORDINATED_ADVANCE`（InfantryTankCoordAI 发出）
- `CAPTURE_VL`（VictoryPointAI 发出）
- `DEFEND_VL`（VictoryPointAI 发出）
- `DEMOLISH_BRIDGE`（RetreatDecisionAI 发出）

### 1.3 地形高度系统数据管道断裂
- `GameMap.elevation_grid` 字段存在但 `from_json` 不从 `tiles_enhanced` 读取
- `LOSSystem._get_elevation` 读 `enhanced["elevation"]` 但地图无此键
- 结果：`elevation_grid` 始终全零，LOS 高度阻挡逻辑形同虚设

### 1.4 SupplyLineManager 未接入
- `SupplyLineManager` 类完整但从未被实例化
- `campaign_four_layer.py` 用自己的内联补给逻辑，与 Manager 重复

---

## 二、Phase 4: CC2 机制补全（v0.5.0）

### 2.1 P4-0: 修复 TacticExecutor 5 个缺失 handler（前置阻断项）

**优先级**：P0 — 必须先修，否则新 AI 行为的意图会落空

| TacticType | 实现方案 | 复用资源 |
|------------|---------|---------|
| `FLANKING` | 转 `MOVE_TO` + 设侧翼路径 | `TacticalAdvisor._flank_position` |
| `COORDINATED_ADVANCE` | 转 `MOVE_TO` + 保持编队间距 | 无 |
| `CAPTURE_VL` | 转 `MOVE_TO` 目标 VL 位置 | `VictoryPointAI._nearest_vl` |
| `DEFEND_VL` | 转 `DEFEND` 在 VL 位置 | 无 |
| `DEMOLISH_BRIDGE` | 检查单位是否在桥旁 → 设置桥为 `BRIDGE_DESTROYED` | `GameMap.set_terrain` |

**修改文件**：
- `src/pycc2/domain/ai/tactic_executor.py` — dispatch_table 新增 5 个 handler
- `tests/unit/test_tactic_executor.py` — 5 个新测试

### 2.2 P4-1: AI 伏击行为（通用步兵伏击）

**现状**：`ATAmbushAI` 仅覆盖 AT vs 坦克；缺通用步兵伏击

**方案**：新建 `AmbushAI(TacticalAIBase)`

**触发条件**：
- 步兵单位在树林/建筑/战壕地形（concealment > 0.5）
- 敌方单位正在接近且未发现我方
- 夜间加成（复用 `NIGHT_AMBUSH_DETECTION_BONUS`）

**行为流程**：
1. `evaluate`: 检测友方步兵在隐蔽地形 + 敌方接近 → 返回 score
2. `execute`: 发出 `SET_AMBUSH` 意图（HOLD_POSITION + 隐蔽 + 等待开火距离）
3. 触发后发出 `BREAK_AMBUSH`（集中火力攻击最近敌单位）

**新增 TacticType**：`SET_AMBUSH`、`BREAK_AMBUSH`

**修改文件**：
- `src/pycc2/domain/ai/tactic_intent.py` — 新增枚举
- `src/pycc2/domain/ai/ambush_ai.py` — **新建**
- `src/pycc2/domain/ai/tactic_executor.py` — 新增 2 个 handler
- `src/pycc2/services/ai_service.py` — 注册 `AmbushAI`
- `tests/unit/test_ambush_ai.py` — **新建**
- `tests/e2e/test_ai_behaviors_e2e.py` — 伏击场景

### 2.3 P4-2: AI 撤退决策增强

**现状**：`RetreatDecisionAI` 已完整，但 `DEMOLISH_BRIDGE` 落空

**方案**：增强现有撤退 + 补炸桥 handler（P4-0 已覆盖）

**增强内容**：
- 断后逻辑：HP > 70% 的单位发出 `HOLD_POSITION` + `SUPPRESS_FIRE` 掩护撤退
- 分阶段撤退：先撤伤员(HP < 30%)，再撤主力(HP < 50%)，最后断后

**修改文件**：
- `src/pycc2/domain/ai/retreat_ai.py` — 增强断后逻辑
- `tests/unit/test_retreat_ai.py` — 扩充断后测试

### 2.4 P4-3: AI 反击行为（全新战略层级）

**现状**：仅近战 `COUNTER_ATTACK_RATIO = 0.5`，无战略反击

**方案**：新建 `CounterattackAI(TacticalAIBase)`

**触发条件**：
- `force_ratio` 从 < 1.0 转为 > 1.2（增援到达）
- 敌方处于进攻姿态（敌方单位在前线比例 > 60%）
- 我方士气 > 50%

**行为流程**：
1. `evaluate`: 检测增援到达 + 力量逆转 → 返回高 score (0.8+)
2. `execute`: 选最弱敌单位 → 集中 2-3 个友方单位发出 `COUNTER_ATTACK`
3. `CommanderAI` 联动：`generate_orders` 增加反击分支

**新增 TacticType**：`COUNTER_ATTACK`

**修改文件**：
- `src/pycc2/domain/ai/tactic_intent.py` — 新增枚举
- `src/pycc2/domain/ai/counterattack_ai.py` — **新建**
- `src/pycc2/domain/ai/tactic_executor.py` — 新增 handler
- `src/pycc2/domain/ai/commander_ai.py` — 增援到达时触发反击
- `src/pycc2/services/ai_service.py` — 注册 `CounterattackAI`
- `tests/unit/test_counterattack_ai.py` — **新建**
- `tests/e2e/test_ai_behaviors_e2e.py` — 反击场景

### 2.5 P4-4: 补给线征用点采购 UI

**现状**：`SupplyLineManager` 完整但未接入；`campaign_four_layer.py` 用内联逻辑

**方案**：接入 Manager + 新建采购 UI

**实施步骤**：
1. 将 `campaign_four_layer._get_supply_type` 改为委托 `SupplyLineManager`
2. `SupplyLineManager` 新增 `procure(allocate_points)` 方法
3. 新建 `supply_procurement_ui.py`（参考 deployment_ui SRP 模式）
4. `CampaignUI` 新增 `SUPPLY_PROCUREMENT` 状态

**修改文件**：
- `src/pycc2/domain/systems/supply_line.py` — 新增采购方法
- `src/pycc2/domain/systems/campaign_four_layer.py` — 委托 Manager
- `src/pycc2/presentation/ui/supply_procurement_ui.py` — **新建**
- `src/pycc2/presentation/ui/campaign_ui.py` — 新增状态
- `tests/unit/test_supply_procurement.py` — **新建**
- `tests/e2e/test_campaign_supply_e2e.py` — **新建**

### 2.6 P4-5: 地形高度系统修复

**现状**：字段和 LOS 逻辑已存在但数据管道断裂

**实施步骤**：
1. 修复 `GameMap.from_json` 从 `tiles_enhanced` 读取 height/elevation
2. 修复 `LOSSystem._get_elevation` 改读 `GameMap.elevation_grid`
3. 为 4 张丘陵地图生成 elevation 数据
4. 接入 `pathfinder.py` 坡度开销
5. 接入 `combat_mechanics_enhanced.py` 高低地加成

**修改文件**：
- `src/pycc2/domain/entities/game_map.py` — 修复 from_json
- `src/pycc2/domain/systems/los_system.py` — 修复数据源
- `src/pycc2/domain/systems/pathfinder.py` — 接入坡度开销
- `data/scenarios/groesbeek_heights.json` 等 — 填充 elevation
- `tests/unit/test_los_height.py` — **新建**

---

## 三、Phase 5: 长期架构改进（v0.6.0）

### 3.1 P5-4: CI 管道 4 阶段分离（最低风险，先做）

**现状**：4 个 job（lint/test/slow-tests/docker），test job 混跑全量

**方案**：重写 ci.yml 为 5 个 job + 串行依赖链

```
lint → unit-tests → integration-tests → e2e-tests → docker-build
                    ↑ slow-tests (并行)  ↑ benchmark (并行)
```

**修改文件**：`.github/workflows/ci.yml`

### 3.2 P5-3: slow 测试优化

**现状**：14 个 slow 测试，~3.5min，主要是 sprite 生成

**方案**：
1. `pixel_artist.py` 实现 `@lru_cache` sprite 缓存
2. 测试用 session-scoped fixture 共享 canvas
3. 像素验证改用 numpy 向量化

**修改文件**：
- `src/pycc2/presentation/rendering/pixel_artist.py` — 缓存
- `tests/unit/test_pixel_artist.py` — fixture 优化

### 3.3 P5-1: 大文件拆分（分批推进）

**实测**：43 个 >500 行文件（文档说 29，偏旧），11 个 >1000 行

**拆分顺序**：
1. 第 1 批：4 个数据文件（weapons/campaign_data/unit_diversity/weapon_sounds）
2. 第 2 批：3 个已有经验文件（game_loop/morale_system/enhanced_renderer 残余）
3. 第 3 批：4 个渲染子系统
4. 第 4 批：10 个 AI 子系统
5. **跳过**：`tactic_executor.py`（TD-064 评估不拆）

### 3.4 P5-2: 独立 application 层

**现状**：`services/` 混合 service/controller/loop/manager/event_bus

**迁移顺序**：
1. event_bus/dispatcher/protocol → `infrastructure/events/`
2. random_context → `infrastructure/random/`
3. game_loop + assembler → `application/loop/`
4. controllers → `application/controllers/`
5. services + managers → `application/use_cases/`

**依赖**：P5-1 第 2 批（game_loop 拆分）完成后

---

## 四、执行优先级

### Phase 4 执行顺序
1. **P4-0**：修复 5 个缺失 handler（前置阻断项）
2. **P4-2**：撤退增强（工作量最小，基础已好）
3. **P4-1**：通用伏击（中等工作量）
4. **P4-3**：反击行为（工作量最大，全新）
5. **P4-5**：地形高度修复（接线工作）
6. **P4-4**：补给线 UI（最大 UI 工作量）

### Phase 5 执行顺序
1. **P5-4**：CI 4 阶段（最低风险，先做）
2. **P5-3**：slow 测试优化（低风险高收益）
3. **P5-1 第 1-2 批**：数据文件 + game_loop 拆分
4. **P5-2**：application 层独立
5. **P5-1 第 3-5 批**：剩余文件拆分

---

## 五、验证标准

### Phase 4 验收
- [ ] P4-0：5 个 handler 补齐 + 测试通过
- [ ] P4-1：伏击 AI 单元测试 + E2E 场景
- [ ] P4-2：撤退增强 + 断后测试
- [ ] P4-3：反击 AI 单元测试 + E2E 场景
- [ ] P4-4：补给采购 UI 可交互 + E2E
- [ ] P4-5：LOS 高度阻挡生效 + 4 张地图有 elevation
- [ ] ruff 0 / mypy 0 / 全量测试通过
- [ ] 模拟真实用户 E2E 测试通过（硬约束）

### Phase 5 验收
- [ ] P5-1：无 >1000 行文件（tactic_executor 除外）
- [ ] P5-2：application/ 目录独立 + 依赖方向正确
- [ ] P5-3：slow 测试 <1s/个
- [ ] P5-4：CI 4 阶段串行 + 总时长 <15min
- [ ] ruff 0 / mypy 0 / 全量测试通过

---

**文档状态**：Phase 4 进行中 (P4-0/1/2/3/4/5 ✅ + P5-4 ✅)，P5-3 进行中
**创建者**：DevSquad V3.8

---

## 六、执行进度记录

### 2026-06-28 已完成

| 任务 | Commit | 验证 |
|------|--------|------|
| P4-0 修复5个缺失handler | `f450408` | 17 测试通过 |
| P4-5 地形高度系统修复 | `f450408` | 3 测试 + 60 回归通过 |
| P5-4 CI 4阶段分离 | `f450408` | YAML 语法验证通过 |
| P4-1 通用伏击 AmbushAI | `2564773` | 15 测试通过 |
| P4-2 撤退断后增强 | `2564773` | 3 测试 + 33 回归通过 |
| P4-3 战略反击 CounterattackAI | `2564773` | 5 测试通过 |
| P4-4 补给线征用点采购UI | `16ca262` (+ `bbae572` 含核心3文件) | 31 测试通过 + 227 回归通过；ruff/mypy 0 |
| P5-3 slow测试优化 | `bbae572` | @lru_cache(128) + 5 session fixture；3.5min→0.56s |

### 2026-06-28 待推进

| 任务 | 优先级 | 依赖 |
|------|--------|------|
| P5-1 第2批 game_loop/morale_system 拆分 | 中 | 无 |
| P5-2 application层独立 | 中 | P5-1 第2批 |
| P5-1 第3-5批 剩余文件拆分 | 低 | P5-2 |

### 2026-06-28 P5-1 第1批完成

| 文件 | 原→facade | 子模块 | Commit | 验证 |
|------|----------|--------|--------|------|
| campaign_data.py | 1456→63L | arnhem(690)+nijmegen(376)+eindhoven(366) | `45d6b06` | 268 tests ✅ |
| cc2_authentic_weapons.py | 1854→76L | weapon_type_defs(141)+allied(468)+axis(378)+vehicle(826) | `63a40c1` | 84 tests ✅ / 69 weapons |
| unit_diversity_expansion.py | 1000→228L | vehicle_variant(388)+faction_variant(366) | `b6dfad3` | 69 tests ✅ / 277 templates |
| weapon_sounds.py | 607L | (评估完成，无需拆分) | — | — |

**全量回归**: ruff 0 / mypy 0 (356 files) / 3734 unit + 618 integration/e2e = 4352 tests passed

---

## 七、P5-1 第1批：数据文件拆分详细设计

> **目标**：4 个大数据文件（共 4917 行）按 SRP 拆分为 facade + 子模块，目标各 facade <300 行
> **原则**：facade 模式保持公共 API 100% 向后兼容，循环导入通过"先定义 dataclass 后导入子模块"解决
> **验证**：每文件拆分后运行 `ruff check` + `mypy` + 对应单元测试

### 7.1 cc2_authentic_weapons.py (1854L → ~100L facade)

**现状结构**：
- L1-142：3 个枚举 (WeaponType/InfantryRole/VehicleType) + WeaponProfile dataclass
- L143-1785：`build_cc2_weapon_database()` 单体函数 1642 行，按武器类型分段（轻/中/重型坦克炮、车载 MG、迫击炮、反坦克、手枪、狙击、步枪等 24 个区段）
- L1786-end：`get_cc2_weapons()` + `get_weapons_for_faction()` 公共 API

**拆分方案**：
| 新文件 | 内容 | 预估行数 |
|--------|------|---------|
| `weapon_type_defs.py` | 3 枚举 + WeaponProfile dataclass | ~142 |
| `allied_weapon_profiles.py` | `build_allied_weapons() -> dict[str, WeaponProfile]`（美军/英军武器） | ~800 |
| `axis_weapon_profiles.py` | `build_axis_weapons() -> dict[str, WeaponProfile]`（德军武器） | ~800 |
| `cc2_authentic_weapons.py` (facade) | `build_cc2_weapon_database()` 合并两 dict + `get_cc2_weapons()` + `get_weapons_for_faction()` | ~100 |

**循环导入规避**：`weapon_type_defs.py` 无外部依赖 → 子模块导入 type_defs → facade 导入子模块

### 7.2 campaign_data.py (1456L → ~80L facade)

**现状结构**：
- L1-49：imports + `create_market_garden_campaign()` 函数开始
- L50-719：**Arnhem Sector** — 3 个 operation（Landing/Perimeter Defense/Evacuation）
- L721-1077：**Nijmegen Sector** — 2 个 operation（Waal Crossing/Bridge Defense）
- L1079-1425：**Eindhoven Sector** — 2 个 operation（Hell's Highway/Corridor Defense）
- L1427-1456：Grand Campaign 组装 + `_SUPPLY_LINE_AMMO_RESUPPLY` + `_HP_RECOVERY_PER_DAY` 常量

**拆分方案**：
| 新文件 | 内容 | 预估行数 |
|--------|------|---------|
| `arnhem_campaign_data.py` | `build_arnhem_sector() -> SectorCampaignDefinition` | ~670 |
| `nijmegen_campaign_data.py` | `build_nijmegen_sector() -> SectorCampaignDefinition` | ~357 |
| `eindhoven_campaign_data.py` | `build_eindhoven_sector() -> SectorCampaignDefinition` | ~347 |
| `campaign_data.py` (facade) | `create_market_garden_campaign()` 组合 3 sector + 常量 | ~80 |

**循环导入规避**：sector 文件仅依赖 domain entities（`OperationDefinition`/`BattleDefinition` 等）→ facade 导入 3 个 sector

### 7.3 unit_diversity_expansion.py (1000L → ~300L facade)

**现状结构**：
- L1-94：imports + `UnitDiversityGenerator` 类开始
- L95-521：`generate_variants` + `generate_vehicle_variants`（371 行，车辆变体生成）
- L522-927：`generate_experience_variants` + `generate_faction_variants`（349 行，阵营变体生成）
- L928-947：`count_total_units`/`get_all_units`/`get_units_by_faction` 查询方法
- L948-end：`get_expanded_unit_database()` 公共 API

**拆分方案**：
| 新文件 | 内容 | 预估行数 |
|--------|------|---------|
| `vehicle_variant_generator.py` | `VehicleVariantGenerator` 类（含 `generate_vehicle_variants` 逻辑） | ~400 |
| `faction_variant_generator.py` | `FactionVariantGenerator` 类（含 `generate_faction_variants` 逻辑） | ~380 |
| `unit_diversity_expansion.py` (facade) | `UnitDiversityGenerator` 委托 2 子生成器 + 查询方法 + 公共 API | ~300 |

**委托模式**：facade `__init__` 实例化 2 子生成器，`generate_*` 方法委托调用，结果聚合到 `_variants` 列表

### 7.4 weapon_sounds.py (607L — 不拆分)

**决策**：607 行仅略超 500 阈值，模块内聚（Profile dataclass + 默认配置 + Generator 类），拆分 ROI 低。**标记为"评估完成，无需拆分"**。

### 7.5 执行顺序与验证

1. **先拆 campaign_data.py**（最清晰，纯数据搬运，零逻辑风险）
2. **再拆 cc2_authentic_weapons.py**（类似纯数据，但需注意 WeaponProfile 引用）
3. **最后拆 unit_diversity_expansion.py**（涉及类委托，逻辑稍复杂）

每步验证：`ruff check <new_files> && MYPYPATH=src mypy <new_files> && pytest tests/unit/test_<relevant> -q`
全量验证：`ruff check src/ && MYPYPATH=src mypy -p pycc2 && SDL_VIDEODRIVER=dummy python -m pytest tests/ -x -q --timeout=120`

---

## 八、P5-1 第2批：逻辑类拆分详细设计

> **目标**：2 个大逻辑文件（共 1529 行）按 SRP 拆分，game_loop.py 采用 mixin 模式，morale_system.py 采用"types + calculator + effects + facade"模式
> **原则**：公共 API 100% 向后兼容；循环导入通过"先定义 dataclass 后导入子模块"解决；mixin 类禁止持有自有状态，所有状态由 facade 的 `self` 提供
> **验证**：每文件拆分后运行 `ruff check` + `mypy` + 对应单元测试 + 全量回归

### 8.1 game_loop.py (828L → ~250L facade + 3 mixin + types)

**现状结构**：
- L1-71：imports + 模块常量 `LOGIC_DT`/`TARGET_FPS`/`MAX_FRAME_TIME`
- L73-88：`GameState` dataclass（slots=True，11 字段）
- L90-142：`GameLoop` dataclass（39 字段：8 公有 + 31 私有）
- L143-166：`__post_init__`/`deployment_ui`/`deployment_phase_active`/`_get_time_speed`
- L167-286：`run()` 主循环（~120L）
- L287-362：渲染方法 `_apply_camera_effects`/`_render_scene`（~76L）
- L363-596：更新方法 `_update_logic` + 10 个 `_update_*` + `_ensure_ai_units_registered`（~234L）
- L623-719：战斗/事件处理 `_handle_player_command`/`_execute_attack`/`_on_unit_attacked*`/`_on_projectile_fired`/`_process_combat_popups`（~97L）
- L720-808：输入/部署/属性访问器 `_handle_input`/`start_deployment`/`complete_deployment`/`get_deployment_state`/`set_campaign_ui`/`campaign_ui`/`victory_manager`/`shutdown`
- L809-828：存档 `quick_save`/`quick_load`/`list_saves`

**导入者（来自 grep）**：`save_controller.py`、`game_loop_assembler.py`、`main.py` + 14 个测试文件
**必须保持的公共 API**：`GameState`、`GameLoop`、`LOGIC_DT`、`MAX_FRAME_TIME`（`TARGET_FPS` 为内部常量，保持但可不导出）

**拆分方案（mixin 模式）**：

| 新文件 | 内容 | 预估行数 |
|--------|------|---------|
| `game_loop_types.py` | `GameState` dataclass + `LOGIC_DT`/`TARGET_FPS`/`MAX_FRAME_TIME` 常量 | ~70 |
| `game_loop_rendering.py` | `GameLoopRenderingMixin`（`_apply_camera_effects`/`_render_scene`） | ~85 |
| `game_loop_updating.py` | `GameLoopUpdatingMixin`（`_update_logic` + 10 `_update_*` + `_ensure_ai_units_registered`） | ~245 |
| `game_loop_combat.py` | `GameLoopCombatMixin`（`_handle_player_command`/`_execute_attack`/`_on_unit_attacked*`/`_on_projectile_fired`/`_process_combat_popups`） | ~105 |
| `game_loop.py` (facade) | `GameLoop(GameLoopRenderingMixin, GameLoopUpdatingMixin, GameLoopCombatMixin)` dataclass：字段 + `__post_init__` + `run()` + 部署 + 存档 + 属性访问器 | ~260 |

**循环导入规避**：
1. `game_loop_types.py` 无外部 pycc2 依赖（仅 `dataclass`/`field`）→ 可被所有 mixin 和 facade 安全导入
2. 每个 mixin 文件 `from pycc2.services.game_loop_types import GameState`（仅类型，运行时不触发循环）
3. facade `game_loop.py` 导入 3 个 mixin + `game_loop_types`，定义 `GameLoop(*Mixin)` dataclass
4. `GameLoopAssembler` 在 `__post_init__` 中延迟导入（已是现有模式）

**Mixin 设计契约**：
- mixin 类只定义方法，不定义 `__init__`、不持有 `_xxx` 字段
- mixin 方法通过 `self.<attr>` 访问 facade 的字段（类型注解用 `TYPE_CHECKING` 导入 `GameLoop` 或使用 `Protocol`）
- mixin 类标记 `@dataclass` 不需要（不实例化）；仅作为方法容器
- facade 继承顺序：`GameLoop(GameLoopRenderingMixin, GameLoopUpdatingMixin, GameLoopCombatMixin)` — MRO 自左向右

### 8.2 morale_system.py (701L → ~150L facade + types + calculator + 2 effects 模块)

**现状结构**：
- L1-33：imports
- L34-58：`MoraleEvent` 枚举（7 事件）+ `MoraleState` 枚举（5 状态）
- L59-79：`RoutingTarget` + `MoraleCalculationResult` dataclass
- L80-172：`MoraleCalculator` 类（6 方法 + 1 静态方法）— 纯计算逻辑，无副作用
- L174-674：`MoraleSystem` 类（11 个 `@staticmethod`）：
  - 状态查询：`get_state`/`get_accuracy_modifier`/`get_movement_modifier`/`can_move`/`can_accept_orders`/`predict_state`
  - 压制与恢复：`apply_suppression`/`update_morale_recovery`
  - 路由与溃逃：`check_routing_behavior`/`_calculate_flee_target`/`_play_morale_collapse_voice`
  - 传染与重整：`apply_panic_contagion`/`apply_nco_rally`
- L676-701：`demo_morale_system()` 演示函数

**导入者（来自 grep）**：
- `src/`：`combat_service.py`、`game_loop.py`、`sprite_renderer.py`、`tactic_executor.py`、`suppression_overlay_renderer.py`、`attack_line_system.py`、`unit.py`、`combat_resolver.py`、`__init__.py`
- `tests/`：`test_morale_system.py`、`test_morale_calculator.py`、`test_combat_resolver.py`、`test_battle_flow_e2e.py`、`test_comprehensive_acceptance.py`、`test_full_customer_journey.py`、`test_performance_baseline.py`、`test_performance.py`

**必须保持的公共 API**：
- `MoraleEvent`、`MoraleState`、`RoutingTarget`、`MoraleCalculationResult`（类型）
- `MoraleCalculator`（类）
- `MoraleSystem`（类，所有静态方法签名不变）
- `demo_morale_system`（函数）

**拆分方案（types + calculator + effects + facade）**：

| 新文件 | 内容 | 预估行数 |
|--------|------|---------|
| `morale_types.py` | `MoraleEvent`/`MoraleState` 枚举 + `RoutingTarget`/`MoraleCalculationResult` dataclass | ~80 |
| `morale_calculator.py` | `MoraleCalculator` 类（6 方法 + `predict_state`） — 纯计算 | ~105 |
| `morale_effects.py` | `MoraleEffects` 类（静态方法：`apply_suppression`/`update_morale_recovery`/`apply_panic_contagion`/`apply_nco_rally`） | ~210 |
| `morale_routing.py` | `MoraleRouting` 类（静态方法：`check_routing_behavior`/`_calculate_flee_target`/`_play_morale_collapse_voice`） | ~155 |
| `morale_system.py` (facade) | `MoraleSystem` 类（所有原静态方法名不变，方法体委托到 `MoraleCalculator`/`MoraleEffects`/`MoraleRouting`）+ `demo_morale_system()` | ~165 |

**循环导入规避**：
1. `morale_types.py` 无 pycc2 依赖（仅 `Enum`/`dataclass`）→ 安全基石
2. `morale_calculator.py` 依赖 `morale_types` + `MoraleComponent`/`Unit`（已存在的 domain 实体）
3. `morale_effects.py` / `morale_routing.py` 依赖 `morale_types` + `morale_calculator`（仅类型注解） + `Unit`/`GameMap`（运行时延迟导入避免循环）
4. facade `morale_system.py` 导入 4 个子模块 + 通过 `__all__` 重新导出全部类型，保持现有导入语句 100% 兼容

**Facade 委托模式**：
```python
class MoraleSystem:
    @staticmethod
    def get_state(morale_value: int) -> MoraleState:
        return MoraleStateResolver.resolve(morale_value)  # 或直接内联
    @staticmethod
    def apply_suppression(unit: Unit, amount: float, dt: float) -> dict:
        return MoraleEffects.apply_suppression(unit, amount, dt)
    @staticmethod
    def check_routing_behavior(unit: Unit, game_map=None) -> tuple[bool, object]:
        return MoraleRouting.check_routing_behavior(unit, game_map)
    # ...
```

**特殊处理**：
- `MoraleSystem.get_state`/`get_accuracy_modifier` 等纯查表方法可直接保留在 facade（< 20 行总计），无需委托
- `_play_morale_collapse_voice` 是音频副作用方法，与路由逻辑耦合（溃逃时播放），归入 `morale_routing.py`
- `demo_morale_system()` 函数保留在 facade 末尾

### 8.3 执行顺序与验证

**优先级**：先拆 `morale_system.py`（影响面更小，纯静态方法委托），后拆 `game_loop.py`（mixin 模式更复杂）

**步骤 1：morale_system.py 拆分**
1. 创建 `morale_types.py` — 转移 4 个类型定义
2. 创建 `morale_calculator.py` — 转移 `MoraleCalculator` 类
3. 创建 `morale_effects.py` — 提取 4 个 effects 静态方法为 `MoraleEffects` 类
4. 创建 `morale_routing.py` — 提取 3 个 routing 静态方法为 `MoraleRouting` 类
5. 重写 `morale_system.py` facade — 保留 `MoraleSystem` 类所有原方法签名，方法体委托；末尾保留 `demo_morale_system()`
6. 验证：`ruff check src/pycc2/domain/systems/morale_*.py && MYPYPATH=src mypy src/pycc2/domain/systems/morale_*.py && pytest tests/unit/test_morale_system.py tests/unit/test_morale_calculator.py tests/unit/test_combat_resolver.py -q`

**步骤 2：game_loop.py 拆分**
1. 创建 `game_loop_types.py` — 转移 `GameState` + 3 个常量
2. 创建 `game_loop_rendering.py` — 提取 2 个渲染方法为 `GameLoopRenderingMixin`
3. 创建 `game_loop_updating.py` — 提取 12 个更新方法为 `GameLoopUpdatingMixin`
4. 创建 `game_loop_combat.py` — 提取 5 个战斗方法为 `GameLoopCombatMixin`
5. 重写 `game_loop.py` facade — 定义 `GameLoop(*Mixin)` dataclass + 主循环 `run()` + 部署 + 存档
6. 验证：`ruff check src/pycc2/services/game_loop*.py && MYPYPATH=src mypy src/pycc2/services/game_loop*.py && pytest tests/unit/test_game_loop.py tests/integration/test_combat_loop.py tests/integration/test_deployment_to_battle.py -q`

**步骤 3：全量回归**
```bash
ruff check src/ tests/ && \
MYPYPATH=src mypy -p pycc2 && \
SDL_VIDEODRIVER=dummy python -m pytest tests/ -x -q --timeout=120 \
  --deselect tests/integration/test_visual_smoke.py::test_visual_smoke_test
```

### 8.4 风险与缓解

| 风险 | 缓解措施 |
|------|---------|
| Mixin 方法访问 facade 私有字段时类型检查失败 | 使用 `TYPE_CHECKING` 导入 `GameLoop` 并在 mixin 方法内 `if TYPE_CHECKING: _: GameLoop = self` 注解；或使用 `Protocol` |
| `MoraleSystem` 静态方法委托链引入运行时开销 | 性能敏感方法（`get_state`/`get_accuracy_modifier`）直接内联在 facade；仅副作用方法（`apply_suppression` 等涉及 IO/状态修改）委托 |
| `game_loop.py` 的 `__post_init__` 延迟导入 `GameLoopAssembler` 可能因模块拆分后路径变化失效 | 保持现有 `from pycc2.services.game_loop_assembler import GameLoopAssembler` 路径不变；assembler 不需要修改 |
| 测试中 `from pycc2.services.game_loop import LOGIC_DT, MAX_FRAME_TIME, GameLoop, GameState` 失败 | facade `game_loop.py` 通过 `__all__` 重新导出 `LOGIC_DT`/`MAX_FRAME_TIME`/`GameState` |
| `morale_system.__init__.py` 中 `from pycc2.domain.systems.morale_system import MoraleCalculator` 失败 | facade 重新导出 `MoraleCalculator`，`__init__.py` 无需修改 |

### 8.5 完成记录表

| 文件 | 拆分前 | facade | 子模块数 | 子模块行数 | 测试通过 | commit |
|------|-------|--------|---------|-----------|---------|--------|
| morale_system.py | 701L | 311L | 4 | types 122L / calculator 123L / effects 249L / routing 169L | ruff 0 / mypy 0 / 94 单元 + 145 e2e 通过 | b2b51da |
| game_loop.py | 828L | 401L | 4 | types 47L / rendering 130L / combat 136L / updating 349L | ruff 0 / mypy 0 (364文件) / 102 单元 + 34 e2e + 全量 4398 通过 | (本次提交) |

### 8.6 game_loop.py 拆分技术要点（mixin 模式）

**mypy 兼容性关键**：mixin 类不能使用 `self: GameLoop` 注解（mypy 报 "The erased type of self is not a supertype of its class"）。采用 **类级属性声明模式**（Django mixin 标准模式）：
- 每个 mixin 在类体顶部声明所依赖的 facade 字段为类级类型注解（无默认值）
- facade 通过 dataclass 字段提供实际值
- 跨 mixin 方法（如 `_update_popups` 调用 `_process_combat_popups`）在调用方 mixin 中声明方法 stub

**继承顺序**：`GameLoop(GameLoopRenderingMixin, GameLoopUpdatingMixin, GameLoopCombatMixin)` — MRO 自左向右，rendering 优先于 combat（`_render_scene` 中调用 `_process_combat_popups`）

**循环导入规避**：
1. `game_loop_types.py` 无 pycc2 依赖 → 可被所有 mixin 安全导入
2. 每个 mixin 仅导入 `game_loop_types`（类型），不导入 facade
3. facade 导入 3 个 mixin + `game_loop_types`，定义 dataclass
4. `GameLoopAssembler` 在 `__post_init__` 中延迟导入（保持现有模式）
