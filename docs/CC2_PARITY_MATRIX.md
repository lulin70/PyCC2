# CC2 对照表（Parity Matrix）

本文件由 W2「内容与数据」轮次生成。所有数字从代码与数据文件实际读取，未手工估算。
数据基线：`build_cc2_unit_database()` / `get_cc2_weapons()` / `data/scenarios/*.json`。

---

## 表 1：单位模板按阵营与角色分布

总计 **115** 个 `CC2UnitTemplate`（本轮新增 5 个）。来源：
`src/pycc2/domain/systems/unit_factories/*.py` + `vehicle_variant_generator.py` + `faction_variant_generator.py`。

| 阵营 | 模板总数 | 角色分布 |
| --- | ---: | --- |
| AMERICAN | 36 | RIFLE 4、MACHINE_GUN 4、TANK_MEDIUM 4、ANTI_TANK 4、TANK_DESTROYER 3、HEAVY_ASSAULT 3、ENGINEER 2、OFFICER 2、HALFTRACK 2、ARMORED_CAR 1、FLAMETHROWER 1、MORTAR 1、SCOUT 1、SNIPER 1、SP_ARTILLERY 1、TANK_LIGHT 1、TRUCK 1 |
| BRITISH | 26 | TANK_MEDIUM 5、ANTI_TANK 4、MACHINE_GUN 2、RIFLE 2、ENGINEER 1、FLAMETHROWER 1、FLAME_TANK 1、HALFTRACK 1、HEAVY_ASSAULT 1、MORTAR 1、OFFICER 1、RECON 1、SCOUT 1、SNIPER 1、TANK_HEAVY 1、TANK_LIGHT 1、TRUCK 1 |
| GERMAN | 46 | RIFLE 8、ANTI_TANK 6、TANK_DESTROYER 5、MACHINE_GUN 4、TANK_MEDIUM 3、ARMORED_CAR 2、ENGINEER 2、FLAME_TANK 2、HEAVY_ASSAULT 2、OFFICER 2、TANK_HEAVY 2、FLAMETHROWER 1、HALFTRACK 1、MORTAR 1、RECON 1、SNIPER 1、SP_ARTILLERY 1、TANK_LIGHT 1、TRUCK 1 |
| POLISH | 10 | MACHINE_GUN 2、ANTI_TANK 1、ENGINEER 1、HEAVY_ASSAULT 1、MORTAR 1、OFFICER 1、RIFLE 1、SCOUT 1、SNIPER 1 |
| **合计** | **118** | 覆盖 19 种角色/车种：`InfantryRole` 12 种中已用 11 种（缺 `RESERVE`），`VehicleType` 9 种全部有模板 |

本轮新增模板：

| ID | 名称 | 阵营 | 角色 | 依据 |
| --- | --- | --- | --- | --- |
| `uk_para_rifle_squad` | British Para Rifle Section | BRITISH | RIFLE | 第 1 空降师伞兵步枪班，现有 `uk_rifle_section` 为一般步兵班 |
| `uk_para_mg_bren` | British Para Bren Team | BRITISH | MACHINE_GUN | 伞兵营 Bren 机枪组，与线列步兵 `uk_bren_team` 编制不同 |
| `uk_para_at_piat` | British Para PIAT Team | BRITISH | ANTI_TANK | 伞兵反坦克组，空降师无师属反坦克炮 |
| `uk_sherman_v` | Sherman V (Guards Armoured) | BRITISH | TANK_MEDIUM | 近卫装甲师 Sherman V（M4A4），英军库中原无普通 Sherman |
| `de_flak36_88` | 8.8cm Flak 36 | GERMAN | ANTI_TANK | 阿纳姆/奈梅亨德军 88 高平两用炮，`de_pak40_at_gun` 为 75mm |
| `us_gmc_cckw` | GMC CCKW 2½-ton Truck | AMERICAN | TRUCK | 红球快车补给卡车（CC2-03） |
| `uk_bedford_ql` | Bedford QL Truck | BRITISH | TRUCK | 英军 3 吨补给卡车，XXX 军团走廊（CC2-03） |
| `de_opel_blitz` | Opel Blitz Truck | GERMAN | TRUCK | 德军 3 吨制式运输卡车（CC2-03） |

---

## 表 2：武器模板数量与类别分布

总计 **69** 个 `WeaponProfile`（`get_cc2_weapons()`）。

| 类别 | 数量 | 细分（`WeaponType` → 数量） |
| --- | ---: | --- |
| 步枪/轻武器 | 17 | RIFLE 8、SUBMACHINE_GUN 5、SNIPER_RIFLE 3、PISTOL 1 |
| 机枪 | 15 | MACHINE_GUN_HEAVY 5、MACHINE_GUN_LIGHT 5、VEHICLE_MOUNTED_MG 5 |
| 反坦克 | 9 | ANTI_TANK_ROCKET 6、ANTI_TANK_GUN 3 |
| 火炮/迫击炮/坦克炮 | 23 | TANK_CANNON_MEDIUM 7、MORTAR_HEAVY 5、TANK_CANNON_HEAVY 5、MORTAR_LIGHT 4、TANK_CANNON_LIGHT 2 |
| 其他 | 5 | FLAMETHROWER 4、GRENADE 1 |
| **合计** | **69** | — |

单位对武器引用：115 个模板共 0 处悬空（`tests/unit/test_content_integrity.py::test_unit_weapon_references_exist_in_weapon_database`）。

---

## 表 3：CC2 关键机制与 PyCC2 实现位置

| CC2 机制 | 实现位置 | 说明 |
| --- | --- | --- |
| 视线（LOS） | `src/pycc2/domain/systems/los_system.py:129` | `LOSSystem.check_los()`；地形/建筑高度、天气参与计算（`los_system.py:174`） |
| 视线（地图层） | `src/pycc2/domain/entities/game_map.py:246` | `GameMap.has_line_of_sight()` |
| 射击判定 | `src/pycc2/domain/systems/ballistic.py:122` | `BallisticEngine.calculate_shot()`，按射程段与经验修正命中 |
| 攻击结算 | `src/pycc2/domain/systems/combat_resolver.py:32` | `CombatResolver.resolve_attack()`：射击→伤害→压制→事件 |
| 压制 | `src/pycc2/domain/systems/combat_mechanics_enhanced.py:81` | `SuppressionState.apply_suppression()`；恢复见 `:105` |
| 压制接入战斗 | `src/pycc2/domain/systems/combat_resolver.py:120` | `_apply_suppression()` |
| 士气 | `src/pycc2/domain/systems/morale_system.py:62` | `MoraleSystem`：溃逃判定 `:143`、命中修正 `:161`、指挥约束 `:231` |
| 士气计算 | `src/pycc2/domain/systems/morale_calculator.py:29` | `MoraleCalculator` |
| VL 胜利判定 | `src/pycc2/domain/systems/victory_conditions.py:172` | `VictoryConditionEvaluator.evaluate()`；VL 归属更新 `:266` |
| 战争迷雾 | `src/pycc2/domain/systems/fog_of_war.py:46` | `FogOfWar.update_visibility()`；射线 `:150` |
| 建筑掩体 | `src/pycc2/domain/systems/combat_resolver.py:73` | 建筑内伤害减半，楼层修正见 `:76-84` |
| 地形掩体值 | `src/pycc2/domain/value_objects/terrain_type.py:79` | `TerrainType.cover_bonus`；伤害减免 `damage.py:78` |
| 弹药消耗 | `src/pycc2/domain/components/weapon_component.py:69` | `WeaponComponent.fire()` 扣弹；换弹 `:88` 复位弹量 |
| 攻守方识别 | `src/pycc2/services/deployment_manager.py:641` | `attacker_faction` → 部署区距 VL 中心 → `defender_advantage` 兜底 |

---

## 表 4：悬空 `template_id` 处置清单

原始悬空引用：**67 处单位条目 + 39 处增援条目 = 106 处**，涉及 11 个场景、17 个旧 ID。
处置后：**0 处悬空**（单位与增援均已校验）。

| 旧 ID | 单位引用 | 增援引用 | 处置 | 新 ID / 说明 |
| --- | ---: | ---: | --- | --- |
| `uk_para_rifle_squad` | 3 | 3 | 补模板 | `uk_para_rifle_squad`（引用不变） |
| `uk_para_mg_bren` | 3 | 3 | 补模板 | `uk_para_mg_bren`（引用不变） |
| `uk_para_at_piat` | 3 | 3 | 补模板 | `uk_para_at_piat`（引用不变） |
| `uk_para_reserve_squad` | 0 | 1 | 改引用 | `uk_para_rifle_squad` |
| `uk_xxx_cors_rifle_squad` | 2 | 1 | 改引用 | `uk_rifle_section`（英军步枪班语义等价） |
| `uk_xxx_cors_mg` | 2 | 0 | 改引用 | `uk_bren_team` |
| `uk_xxx_cors_sherman` | 2 | 3 | 补模板 + 改引用 | `uk_sherman_v` |
| `uk_guards_sherman` | 3 | 3 | 补模板 + 改引用 | `uk_sherman_v` |
| `us_para_rifle_squad_101st` | 4 | 4 | 改引用 | `us_rifle_squad`（注释即「airborne rifle squad」） |
| `us_para_rifle_squad_82nd` | 4 | 4 | 改引用 | `us_rifle_squad` |
| `us_para_at_bazooka` | 6 | 0 | 改引用 | `us_at_team`（M1A1 Bazooka） |
| `us_para_mg_30cal` | 6 | 1 | 改引用 | `us_machine_gun_team_a4`（M1919A4 .30 cal） |
| `us_para_mortar_60mm` | 2 | 0 | 改引用 | `us_mortar_light_team`（M2 60mm） |
| `de_grenadier_squad` | 11 | 8 | 改引用 | `de_rifle_squad`（Grenadier = 德军步枪班） |
| `de_mg42_squad` | 11 | 3 | 改引用 | `de_mg42_team` |
| `de_flak_88` | 2 | 0 | 补模板 | `de_flak36_88` |
| `de_sp_recon` | 3 | 2 | 改引用 | `de_recon_team` |
| **合计** | **67** | **39** | — | 0 悬空 |

同一轮次内顺带修复的数据缺陷：

| 文件 | 问题 | 修复 |
| --- | --- | --- |
| `data/scenarios/eindhoven_corridor.json` | `map_id: "eindhoven"` 无对应地图 | 改为 `eindhoven_city` |
| `data/scenarios/waal_crossing.json` | VL `vl_south_bank` `[20, 36]` 超出 38×34 地图 | 改为 `[20, 32]` |
| 10 个场景 | 17 处 `deployment_zone` 坐标越过地图右/下边界 | 钳制到 `width-1` / `height-1` |

场景清单（**20** 个）：

- 原有 11 个：`arnhem_bridge_day1`、`arnhem_lz`、`corridor_defense`、`eindhoven_corridor`、
  `eindhoven_linkup`、`nijmegen_bridge`、`nijmegen_bridge_assault`、`nijmegen_landing`、
  `oosterbeek_perimeter`、`veghel_defense`、`waal_crossing`
- 本轮新增 9 个：`arnhem_rail_bridge_assault`、`nijmegen_street_fighting`、
  `eindhoven_suburbs_clearance`、`koevering_corridor_defense`、`hell_highway_ambush`、
  `waal_river_assault`、`driel_polish_crossing`、`hartenstein_night_defense`、
  `oosterbeek_last_stand`

---

## 未覆盖项与已关闭缺口（如实列出）

1. **`special_rules` 全部有运行时消费点（2026-11-10 补齐）。** 17 条规则全部生效：

| 规则 | 消费点 | 效果 |
| --- | --- | --- |
| `night_fighting` | `game_loop._apply_scenario_rules` | 战斗时钟设为 22:00 |
| `bridge_destructible` | `CombatDirector` | 工兵可炸桥 |
| `amphibious_crossing_available` | `_apply_scenario_rules` + `GameMap.is_passable_for` | 两栖单位可通行水面；步行单位仍被阻挡 |
| `airdrop_deployment` | 部署放置服务 | 中立区可空降 |
| `defender_advantage` | 部署区计算 | 防守方部署区优势 |
| `xxx_corps_linkup` | 胜利与增援 | 会师条件 |
| `supply_dwindling` | `_update_logistics` | 补给量每周期 ×0.85，最终断供 |
| `limited_reinforcements` | `_update_reinforcements` | 每方增援上限 2 |
| `fortified_positions` | `_apply_scenario_start_effects` | 轴心守军 `scenario_cover_mod=0.75` |
| `fanatic_defenders` | `_update_scenario_effects` | 轴心守军士气不低于 30 |
| `combined_arms_bonus` | `_update_scenario_effects` | 4 格内有友军装甲，命中 ×1.10 |
| `lz_must_hold_for_reinforcements` | `_update_reinforcements` | 盟军不控 LZ 时不增援 |
| `corridor_must_remain_open` | `_update_logistics` | 走廊/道路 VL 被敌方占领时断供 |
| `no_air_support` | `_update_logistics` + `configure_air_support` | 盟军补给停止；空袭次数 0 |
| `limited_air_support` | `_update_logistics` + `configure_air_support` | 盟军补给减半；空袭次数 1 |
| `initial_scatter` | `_apply_scenario_start_effects` | 开战时单位随机偏移 1 格 |
| `must_hold_all_vls` | `victory_conditions` | 时间到须占全部 VL 才算胜 |

说明：`no_air_support` / `limited_air_support` 同时控制空中补给与空袭次数。空袭见第 11 项。

2. **两栖通行已接入寻路与移动层（2026-11-10 补齐）。** `CC2UnitTemplate.is_amphibious`
   写入 `Unit.is_amphibious`。`GameMap.is_passable_for()` 按单位放行水域。
   `PathFinder`、`PathPreview`、AI 移动、旧 `AStarPathfinder` 均按单位判断。
   两栖单位跨水成本 2.0。盟军默认池与盟友池已加入 `uk_sherman_dd`，玩家可实际部署。
3. **场景 schema 校验已补齐。** `scenario_validation.py` 在加载前校验必需字段、枚举、
   部署区与胜利点；W5 已接入 `main.py`。
4. **遗留战役数据仍含旧 ID。** `src/pycc2/domain/systems/nijmegen_campaign_data.py`
   与 `eindhoven_campaign_data.py` 使用 `ger_rifle_squad` / `brit_rifle_squad` / `brit_armor` /
   `us_para_rifle_squad_82nd` 等旧命名，不在 `data/scenarios/` 校验范围内，本轮未改动。
5. **`de_flak36_88` 已用独立武器档。** （W5 修复，`flak36_88mm`）
6. **波兰伞兵未进入场景阵营。** schema 的 `faction` 枚举仅允许 BRITISH / AMERICAN / GERMAN，
   `pl_para_*` 模板（10 个）无法作为独立阵营参战，`driel_polish_crossing` 仅用英军伞兵表达。
7. **TRUCK 模板已补齐（2026-11-10）。** 新增 `us_gmc_cckw`、`uk_bedford_ql`、`de_opel_blitz`。
   模板总数 118，`VehicleType` 9 种角色全部有模板。卡车无装甲、不能占楼、不能占领。
8. **场景 VL 已成为计分依据（2026-11-09 修复）。** 此前场景 `victory_locations` 只用于部署界面显示，
   战斗计分读取地图 `objectives`，两套坐标不同。现在加载场景时用场景 VL 覆盖地图 objectives，
   半径固定 3，落点不可通行时自动扩大半径到 6。
9. **一图多场景，无选择入口（2026-11-09 登记）。** 3 个场景共用 `nijmegen` 地图。
   遭遇战只选地图，不选场景。修复后按文件名排序取第一个，结果确定但玩家无法选择。
10. **单位外观辨识度（2026-11-10 修复并增强）。** 三种视觉编码：阵营色地面底座、深色 1 px 描边、
    兵种标识。缩放 ≥0.5 时精灵正中显示兵种字母（I/G/T/A/R/E/S/M/F/O/U），
    缩放 <0.5 时回退形状徽章（圆=步兵、双点=机枪、方=装甲、三角=炮、折线=侦察）。
    见 `unit_overlay_rendering_mixin.py` 的 `unit_role_letter` / `_draw_unit_role_letter` /
    `_draw_unit_role_badge`，描边见 `unit_rendering_mixin.py` 的 `_blit_unit_sprite`。
11. **工兵架桥与空袭已补齐（2026-11-10）。**
    - 架桥：`CombatDirector._cmd_build_bridge`。工兵把相邻水域或断桥改为 `BRIDGE`，玩家按 `B`。
    - 空袭：`CombatDirector._cmd_air_strike`。按 `air_support_level` 限次（0/1/3）。
      命中 3×3 范围，每单位 45 伤害，友军同样受伤。玩家按 `K`，目标为鼠标所在格。

