# CC2 对照表（Parity Matrix）

本文件由 W2「内容与数据」轮次生成。所有数字从代码与数据文件实际读取，未手工估算。
数据基线：`build_cc2_unit_database()` / `get_cc2_weapons()` / `data/scenarios/*.json`。

---

## 表 1：单位模板按阵营与角色分布

总计 **115** 个 `CC2UnitTemplate`（本轮新增 5 个）。来源：
`src/pycc2/domain/systems/unit_factories/*.py` + `vehicle_variant_generator.py` + `faction_variant_generator.py`。

| 阵营 | 模板总数 | 角色分布 |
| --- | ---: | --- |
| AMERICAN | 35 | RIFLE 4、MACHINE_GUN 4、TANK_MEDIUM 4、ANTI_TANK 4、TANK_DESTROYER 3、HEAVY_ASSAULT 3、ENGINEER 2、OFFICER 2、HALFTRACK 2、ARMORED_CAR 1、FLAMETHROWER 1、MORTAR 1、SCOUT 1、SNIPER 1、SP_ARTILLERY 1、TANK_LIGHT 1 |
| BRITISH | 25 | TANK_MEDIUM 5、ANTI_TANK 4、MACHINE_GUN 2、RIFLE 2、ENGINEER 1、FLAMETHROWER 1、FLAME_TANK 1、HALFTRACK 1、HEAVY_ASSAULT 1、MORTAR 1、OFFICER 1、RECON 1、SCOUT 1、SNIPER 1、TANK_HEAVY 1、TANK_LIGHT 1 |
| GERMAN | 45 | RIFLE 8、ANTI_TANK 6、TANK_DESTROYER 5、MACHINE_GUN 4、TANK_MEDIUM 3、ARMORED_CAR 2、ENGINEER 2、FLAME_TANK 2、HEAVY_ASSAULT 2、OFFICER 2、TANK_HEAVY 2、FLAMETHROWER 1、HALFTRACK 1、MORTAR 1、RECON 1、SNIPER 1、SP_ARTILLERY 1、TANK_LIGHT 1 |
| POLISH | 10 | MACHINE_GUN 2、ANTI_TANK 1、ENGINEER 1、HEAVY_ASSAULT 1、MORTAR 1、OFFICER 1、RIFLE 1、SCOUT 1、SNIPER 1 |
| **合计** | **115** | 覆盖 19 种角色/车种：`InfantryRole` 12 种中已用 11 种（缺 `RESERVE`），`VehicleType` 9 种中已用 8 种（缺 `TRUCK`） |

本轮新增模板：

| ID | 名称 | 阵营 | 角色 | 依据 |
| --- | --- | --- | --- | --- |
| `uk_para_rifle_squad` | British Para Rifle Section | BRITISH | RIFLE | 第 1 空降师伞兵步枪班，现有 `uk_rifle_section` 为一般步兵班 |
| `uk_para_mg_bren` | British Para Bren Team | BRITISH | MACHINE_GUN | 伞兵营 Bren 机枪组，与线列步兵 `uk_bren_team` 编制不同 |
| `uk_para_at_piat` | British Para PIAT Team | BRITISH | ANTI_TANK | 伞兵反坦克组，空降师无师属反坦克炮 |
| `uk_sherman_v` | Sherman V (Guards Armoured) | BRITISH | TANK_MEDIUM | 近卫装甲师 Sherman V（M4A4），英军库中原无普通 Sherman |
| `de_flak36_88` | 8.8cm Flak 36 | GERMAN | ANTI_TANK | 阿纳姆/奈梅亨德军 88 高平两用炮，`de_pak40_at_gun` 为 75mm |

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

## 未覆盖项（如实列出）

1. **`special_rules` 大部分未实现。** 代码中只有 `defender_advantage` 被
   `deployment_manager.py:704` 读取；`bridge_destructible`、`amphibious_crossing_available`、
   `corridor_must_remain_open`、`airdrop_deployment`、`night_fighting`、`xxx_corps_linkup`
   等在 `src/` 内无任何消费方，仅为数据字段。
2. **两栖与架桥无运行时逻辑。** `CC2UnitTemplate.is_amphibious` 只有数据标记
   （`unit_templates.py:39`、`british_units.py:193`），移动/寻路层未读取。
3. **场景文件无 schema 校验。** `main.py:316-343` 只做 `json.load`，未按
   `data/scenarios/_schema.json` 校验；枚举、字段类型靠测试兜底。
4. **遗留战役数据仍含旧 ID。** `src/pycc2/domain/systems/nijmegen_campaign_data.py`
   与 `eindhoven_campaign_data.py` 使用 `ger_rifle_squad` / `brit_rifle_squad` / `brit_armor` /
   `us_para_rifle_squad_82nd` 等旧命名，不在 `data/scenarios/` 校验范围内，本轮未改动。
5. **`de_flak36_88` 复用 `kwk36_88mm` 武器档。** 现有武器库无独立 Flak 36 条目，
   弹道参数取自 Tiger 的 8.8cm L/56，与真实 Flak 36 的初速/射界存在差异。
6. **波兰伞兵未进入场景阵营。** schema 的 `faction` 枚举仅允许 BRITISH / AMERICAN / GERMAN，
   `pl_para_*` 模板（10 个）无法作为独立阵营参战，`driel_polish_crossing` 仅用英军伞兵表达。
7. **无卡车（TRUCK）模板。** `VehicleType.TRUCK` 已定义但 115 个模板中无对应单位。
8. **VL 与地图 `objectives` 未交叉校验。** 场景 VL 坐标与地图自带 `objectives` 字段是两套数据，
   仅校验了地图宽高范围，未校验两者一致性。
