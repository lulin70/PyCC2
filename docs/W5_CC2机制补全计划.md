# W5 CC2 机制补全计划

版本：v1.0（2026-11-08）
状态：执行中

## 1. 背景

上一轮 review 确认：系统未完全复刻 CC2。核心机制已有代码，但多处未接入运行时主路径。
本轮按 P0→P2 逐一修复，让玩家在真实运行中看到 CC2 行为。

约束：

- 不重写架构。
- 优先复用现有系统。
- 每批次有测试。
- 不破坏现有用例。

## 2. 批次与出口条件

| 批次 | 机制 | 出口条件 |
| --- | --- | --- |
| 1 | P0-1 单兵模型接线 | 成员伤亡影响命中与压制；相关测试通过 |
| 2 | P0-2 增援运行时生成 | 增援按回合到场；测试通过 |
| 3 | P0-3 换弹与补给 | 空弹自动换弹；出生点可补弹；测试通过 |
| 4 | P1-4 天气接入机制 | 天气影响 LOS 与命中；测试通过 |
| 5 | P1-5 special_rules 生效 | 夜战/空降/炸桥/两栖生效；测试通过 |
| 6 | P1-6 AP/HE 切换 | 弹种影响伤害与穿透；测试通过 |
| 7 | P1-7 停火模式 | hold/return/free 生效；测试通过 |
| 8 | P1-8 验收测试 | `tests/acceptance/test_cc2_parity.py` 通过 |
| 9 | P2 收尾 | 炮塔/乘员/迫击炮/经验生效；测试通过 |

## 3. 实施要点

1. 单兵模型：部署时挂接 Squad；伤害按比例同步成员伤亡；有效战斗力影响命中；压制使成员 PINNED。
2. 增援：`ReinforcementService` 读取场景 `forces.*.reinforcements`；1 回合 = 900 tick；地图边缘生成。
3. 换弹：`WeaponComponent.reserve_ammo` 区分旧行为、无限、有限；空弹自动换弹；出生点附近恢复储备。
4. 天气：实例化 `WeatherState`/`WeatherEffects`；注入 LOS；同步 `game_map.weather_state`。
5. special_rules：`ScenarioRules` 解析；夜战设置时钟；空降放开部署区；工程师炸桥；两栖允许过水。
6. AP/HE：主路径新增弹种枚举与切换；弹道读取修正。
7. 停火：`Unit.fire_mode` + 命令 + UI 三态按钮。
8. 验收：覆盖 13 项机制。
9. P2：炮塔朝向、乘员伤亡、迫击炮间瞄、击杀经验。

## 4. 验证

1. 目标测试：`SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -p no:randomly <目标文件>`
2. 静态检查：`.venv/bin/ruff check <改动文件>`
3. 全量回归：`SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -q -p no:randomly --ignore=tests/benchmark`
4. 真实运行：进入 `arnhem_bridge_day1`，等待增援，炸桥，切换弹种与停火，截图存 `docs/assets/w5_parity/`。

## 5. W4 验证发布合并（批次 10）

W5 机制补全完成后，直接进入 W4 发布门禁。两阶段合并执行，不分开评审。

| 顺序 | 检查项 | 命令或方法 | 通过标准 |
| --- | --- | --- | --- |
| 1 | G1-G3 机制验收 | `tests/acceptance/test_cc2_parity.py` | 全部通过；G3 四类胜利条件各有 1 条用例 |
| 2 | 全量回归 | `pytest -q -p no:randomly --ignore=tests/benchmark` | 0 failed |
| 3 | UAT | 按 `docs/test/UAT_TEMPLATE.md` 执行 T1-T5 | P0 缺陷 = 0；任务完成率 ≥80% |
| 4 | 性能回归 | `tests/benchmark/test_fps_baseline.py`、`test_perf_benchmark.py` | FPS ≥60；对比 `perf_baseline.json` 无回归 |
| 5 | 发布检查 | 新建 `docs/RELEASE_GATE_W5.md` | W1-W5 出口条件逐项有证据 |

UAT 记录写入 `docs/test/UAT_W5_20261108.md`。
UAT 覆盖：启动进战斗、部署、基础命令、完整战斗、存档读取。
性能记录写入 `docs/RELEASE_GATE_W5.md`。
发布门禁不通过时，不进入下一阶段。

## 6. 风险

- 单兵模型影响存档：新字段带默认值。
- 命中率修正改变旧断言：按 CC2 语义更新。
- 全量测试耗时约 140 秒：每批次先跑目标用例。

## 6. 执行结果（2026-11-08）

| 批次 | 状态 | 证据 |
|------|------|------|
| 1 单兵模型 | 完成 | `tests/unit/test_squad_integration.py` |
| 2 增援 | 完成 | `tests/unit/test_reinforcement_service.py` |
| 3 弹药与补给 | 完成 | `tests/unit/test_logistics.py` |
| 4 天气 | 完成 | `tests/integration/test_weather_mechanics.py` |
| 5 special_rules | 完成 | `tests/integration/test_scenario_rules.py` |
| 6 AP / HE | 完成 | `tests/unit/test_ammo_type.py` |
| 7 火力纪律 | 完成 | `tests/unit/test_fire_mode.py` |
| 8 验收 | 完成 | `tests/acceptance/test_cc2_parity.py`，25 passed |
| 9 P2 炮塔朝向 | 完成 | `test_mechanism_turret_turns_independently_of_hull` |
| 9 P2 乘员伤亡弃车 | 完成 | `test_mechanism_crew_wipe_abandons_vehicle` |
| 9 P2 迫击炮间瞄 | 完成 | `test_mechanism_mortar_fires_with_friendly_observer`、`test_mechanism_mortar_waits_without_observer` |
| 9 P2 击杀经验 | 完成 | `test_mechanism_kill_grants_experience` |
| 10 W4 验证发布 | 完成 | `docs/RELEASE_GATE_W5.md`、`docs/test/UAT_W5_20261108.md` |

全量回归：7481 passed / 4 skipped / 0 failed。
性能：`tests/benchmark` 42 passed / 6 skipped，`tests/performance` 3 passed；heavy_load 中位 FPS 76.4，最差 63.5；normal_load 中位 102.3。
真实运行截图：`docs/assets/w5_parity/`（01/02/03，共 3 张）。

## 7. P2 机制实现说明

1. 炮塔：`Unit.turret_facing` 独立于车体。`CombatDirector.execute_attack` 调用 `Unit.aim_turret_at`，按 180 度/秒转向。渲染读取 `Unit.turret_facing_rad`。
2. 乘员：`Unit.take_damage` 把 25% 伤害转给乘员。`Unit.apply_crew_damage` 可定向伤乘员。乘员全灭时 `abandon_vehicle` 弃车；车体被毁时幸存乘员撤离。
3. 迫击炮：`CombatDirector._has_indirect_observer` 查找同阵营观察员。观察员必须在视野内看见目标。无观察员时取消射击。直射武器仍用自身视线。

补充修复：
- GAP-11：确认攻击时按单位记录攻击者坐标。跟踪时刷新坐标。无坐标时跳过绘制，不再画零长度线段。测试：`tests/unit/test_attack_line_system.py`。
- GAP-12：`LOSSystem` 缓存键加入 `max_range`。短射程查询不再覆盖默认射程结果。测试：`tests/unit/test_los_system.py::test_cache_separates_results_by_max_range`。
- GAP-13：`special_rules` 的夜战、空降、两栖、可炸桥、防守方优势均有运行时消费点。测试：`tests/integration/test_scenario_rules.py`。
- GAP-14：新增 `scenario_validation.py`。场景加载前校验必需字段、枚举、部署区、胜利点。测试：`tests/unit/test_scenario_validation.py`。
- GAP-15：部署工厂与模板映射改用数据库 ID。未知模板不再回退为步枪班。测试：`tests/unit/test_deployment_factory.py`。
- GAP-16：新增 `flak36_88mm` 专属反坦克炮档案。测试：`tests/unit/test_cc2_authentic_units.py`。

## 8. PF-01 性能优化（2026-11-08）

| 优化 | 位置 | 效果 |
|------|------|------|
| 建筑屋顶缓存 | `presentation/rendering/building_renderer.py` | 去掉每帧约 2.8k 次随机像素写入 |
| 阴影视口裁剪 | `presentation/rendering/shadow_rendering_system.py` | 只处理屏幕内瓦片和单位 |
| 去饱和降采样 | `presentation/rendering/post_processing.py` | 全屏灰度 8.3 ms → 约 3 ms；原地处理，不再整帧拷贝 |
| 单位精灵缩放缓存 | `presentation/rendering/unit_rendering_mixin.py` | 同一精灵同一尺寸只缩放一次 |
| 单位视口裁剪 | `presentation/rendering/unit_rendering_mixin.py` | 屏幕外单位不再绘制 |
| 地形缓存参数修复 | `presentation/rendering/terrain_rendering_system.py` | 恢复地面纹理；去掉每帧约 432 次异常 |

实测（1024×768，SDL dummy，pytest-benchmark，10 轮 × 600 帧）：
- heavy_load：中位 76.4 FPS，最差 63.5 FPS。
- normal_load：中位 102.3 FPS。
- 视觉回归：地形修复后重建基线，7 个场景全部通过。
- 新基线：`tests/benchmark/perf_baseline.json`（normal_load 102.26、heavy_load_worst 63.48）。

本轮还修复一个隐藏缺陷：`TerrainTileCache.get_tile` 的参数名不匹配，导致增强地形缓存为空。修复前地面只有纯色背景，并且每帧抛出约 432 次异常。修复后地面纹理正常，性能同时提升。
