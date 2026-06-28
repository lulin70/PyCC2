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
| P5-1 第1批 数据文件拆分 | 中 | 无（独立于 P4-4） |
| P5-2 application层独立 | 中 | P5-1 第2批 |
| P5-1 第3-5批 剩余文件拆分 | 低 | P5-2 |

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
