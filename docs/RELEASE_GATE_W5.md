# PyCC2 W5 发布门禁记录

- 日期：2026-11-08
- 版本：W5（CC2 机制补全 + W4 验证发布合并）
- 代码基线：commit `3bdbd7b` + 本轮改动；已提交并推送为 `4eaa123`
- 环境：macOS 26.6.2 / Apple M1 / Python 3.12.13 / SDL dummy 驱动
- 关联文档：`docs/W5_CC2机制补全计划.md`、`docs/test/UAT_W5_20261108.md`、`docs/CC2_PARITY_ROADMAP.md`

## 1. 门禁总表

| 门禁 | 条件 | 证据 | 结果 |
|------|------|------|------|
| G1 视线与射击门控 | 墙体阻挡视线；无视线不射击 | `tests/acceptance/test_cc2_parity.py::test_g1_wall_blocks_line_of_sight` | 通过 |
| G2 战争迷雾三态 | 未探索 / 已探索 / 可见 | `test_g2_fog_has_hidden_explored_visible_states` | 通过 |
| G3 四类胜利条件 | 歼灭、据点、限时、士气崩溃 | `test_g3_*`（4 个用例） | 通过 |
| 全量回归 | 0 失败 | 7481 passed, 4 skipped | 通过 |
| 验收测试 | 每类机制至少 1 条 | `tests/acceptance/test_cc2_parity.py` 25 passed | 通过 |
| UAT | 5 条主路径无阻塞 | `docs/test/UAT_W5_20261108.md`，69 个 e2e 用例通过 | 通过（自动化） |
| 性能回归 | 不低于基线 75%；目标 FPS ≥ 60 | `tests/benchmark` 42 passed / 6 skipped；`tests/performance` 3 passed；heavy 中位 76.4，最差 63.5 | 通过 |
| 视觉回归 | 5 个场景不超阈值 | `tests/visual_regression` 7 passed（基线按地形修复重建） | 通过 |
| 代码规范 | Ruff 无告警 | 本批次改动文件 | 通过 |

## 2. W5 机制完成度

| 编号 | 机制 | 实现位置 | 状态 |
|------|------|---------|------|
| P0-1 | 单兵模型接线 | `domain/entities/squad.py`、`domain/entities/unit.py`、`services/deployment_manager.py` | 完成 |
| P0-2 | 增援运行时生成 | `services/reinforcement_service.py`、`services/game_loop*.py` | 完成 |
| P0-3 | 有限弹药、换弹、补给 | `components/weapon_component.py`、`services/combat_director.py` | 完成 |
| P1-4 | 天气接入战斗与渲染 | `systems/weather_effects.py`、`services/game_loop*.py` | 完成 |
| P1-5 | special_rules 生效 | `value_objects/scenario_rules.py`、`game_loop.py`、`deployment_ui.py` | 完成 |
| P1-6 | AP / HE 切换 | `value_objects/ammo_type.py`、`weapon_component.py`、`systems/ballistic.py` | 完成 |
| P1-7 | 火力纪律三态 | `domain/entities/unit.py`、`services/combat_director.py`、HUD | 完成 |
| P1-8 | G1-G3 验收与真实运行截图 | `tests/acceptance/test_cc2_parity.py`、`docs/assets/w5_parity/` | 完成 |
| P2 | 击杀经验 | `services/combat_director.py::record_stats` | 完成 |
| P2 | 炮塔独立朝向 | `domain/entities/unit.py::aim_turret_at`、`presentation/rendering/unit_rendering_mixin.py` | 完成 |
| P2 | 乘员伤亡弃车 | `domain/entities/unit.py::apply_crew_damage`、`abandon_vehicle` | 完成 |
| P2 | 迫击炮间瞄 | `services/combat_director.py::_has_indirect_observer` | 完成 |
| PF-01 | 渲染性能 | 建筑屋顶缓存、阴影视口裁剪、去饱和降采样、精灵缩放缓存、单位视口裁剪、地形缓存参数修复 | 完成 |
| GAP-11 | 攻击线坐标 | 确认攻击时按单位记录攻击者坐标；跟踪时刷新；无坐标时跳过绘制 | 完成 |
| GAP-12 | LOS 缓存键缺 `max_range` | `domain/systems/los_system.py`；缓存键加入 `max_range`，不同射程结果互不覆盖 | 完成 |
| GAP-13 | `special_rules` 运行时入口 | 夜战、空降、两栖、可炸桥、防守方优势均有消费点（W5 P1-5） | 完成 |
| GAP-14 | 场景加载无校验 | 新增 `domain/value_objects/scenario_validation.py`；加载前校验字段、枚举、部署区、胜利点 | 完成 |
| GAP-15 | 部署旧 ID | `services/deployment_factory.py`、`deployment_manager.py` 改用数据库 ID；未知模板不再回退为步枪班 | 完成 |
| GAP-16 | Flak 36 弹道 | 新增专属 `flak36_88mm` 反坦克炮档案 | 完成 |

## 3. 性能数据

| 场景 | 指标 | 基线（优化前） | 本次 | 判定 |
|------|------|------|------|------|
| normal_load | 中位 FPS | 50.1 | 102.3 | 通过 |
| heavy_load | 中位 FPS | 45.1 | 76.4 | 通过（≥60） |
| heavy_load | 最差 FPS | 52.1 | 63.5 | 通过（≥60） |

说明：
- 测量条件：1024×768，SDL dummy 驱动，pytest-benchmark，10 轮 × 600 帧。
- 优化前后：heavy_load 中位 33 FPS → 76.4 FPS。
- 新基线已写入 `tests/benchmark/perf_baseline.json`：normal_load 102.26、heavy_load_worst 63.48。
- 首次复测受一个失控临时脚本干扰（占满一个 CPU 核心）。清理后单独重跑，得到上表数据。
- 同时修复地形缓存参数错误。修复前地面无纹理，且每帧抛出约 432 次异常。
- 地形修复改变了画面。已重建 macOS 视觉基线，7 个场景全部通过。
- 数据来自无窗口 SDL 驱动。真实窗口模式需要用户复测。
- 推送前复测：`tests/benchmark` 47 passed；`test_fps_normal_load` 首次 75.9 FPS，低于阈值 76.7。当时系统负载高（WebKit + IDE 占约 2.4 个核心，load average 5.67）。隔离重跑通过（中位 6.17 ms/帧）。判定为环境噪声，不改基线。

### 3.1 真实窗口性能（PF-03，2026-11-08）

测量对象：`scripts/real_window_perf.py`。窗口由 `WindowManager` 创建：cocoa 驱动，SCALED + DOUBLEBUF + vsync，1280×720。10 轮 × 600 帧。

| 场景 | 中位 FPS | 最差 FPS | 最好 FPS | 判定 |
|------|---------|---------|---------|------|
| normal_load（50 单位） | 60.2 | 59.6 | 72.5 | 通过（vsync 上限 60） |
| heavy_load（200 单位） | 56.6 | 52.1 | 59.4 | 未达 60（PF-04） |

说明：
1. normal_load 受 vsync 限制，帧率稳定在 60。不能与无窗口基线 102.3 直接比较。
2. heavy_load 中位 56.6 FPS，比无窗口结果低 19.8 FPS。
3. cProfile 显示重载帧的主要成本：blit 约 8.7 ms/帧（约 735 次/帧），smoothscale 约 2.6 ms/帧。
4. **测量环境有干扰**：当时系统负载 12.3（另一项目的 pytest 全量测试 + WebKit + IDE 共占约 3 个核心）。因此 heavy 数据偏低，是下界，不是稳态值。
5. 结论：normal 达标；heavy 需在空闲机器复测后判定。登记 PF-04。

## 4. 真实运行证据

| 截图 | 内容 | 路径 |
|------|------|------|
| 01 | 步兵班伤亡 4 人；HUD 显示 HP 60/100；FIRE: HOLD；工兵炸桥后地面单位可通行 | `docs/assets/w5_parity/01_battle_squad_fire_mode.png` |
| 02 | 西侧增援进入战场；部队列表出现新单位 | `docs/assets/w5_parity/02_reinforcement_arrived.png` |
| 03 | 坦克炮塔朝北、车体朝东；迫击炮在观察员支援下开火；墙体阻挡直射视线 | `docs/assets/w5_parity/03_turret_mortar.png` |
| 04 | 真实窗口主菜单（PF-02） | `docs/assets/uat_pf02/T1_main_menu.png` |
| 05 | 真实窗口遭遇战设置（PF-02） | `docs/assets/uat_pf02/T1_skirmish_setup.png` |
| 06 | 真实窗口部署界面（PF-02） | `docs/assets/uat_pf02/T2_deployment_placed.png` |
| 07 | 真实窗口战斗点击结果（PF-02） | `docs/assets/uat_pf02/T3_T4_battle_clicks.png` |

PF-02 点击链路 UAT（`scripts/uat_real_window.py`，cocoa 1280×720）：

| 步骤 | 结果 |
|------|------|
| T1.1 点击 Skirmish | PASS：进入遭遇战设置 |
| T1.2 点击 Start Skirmish | PASS：返回 `start_skirmish` |
| T2.1 点击名册 | PASS：`select_unit:0` |
| T2.2 点击地图 | PASS：`place_unit` |
| T2.3 点击 Begin Battle | PASS：`begin_battle` |
| T3.1 左键选中 | PASS：`uk_1` |
| T3.2 右键移动 | PASS：1 条移动命令 |
| T3.3 热键 F/D | PASS：`fire_mode=free` |
| T3.4 右键攻击 | PASS：目标 `de_1` |
| T4 战斗伤害 | PASS：HP 100 → 82 |
| T5 存档读取 | PASS：HP 88 读回一致 |

限制：无 macOS 辅助功能权限，`CGEventPost` 被系统丢弃。点击事件进入真实 pygame 事件队列，走同一条处理链路，但不是物理鼠标点击。画质与手感仍需人工确认。

运行时验证值：
- `bridge: BRIDGE_DESTROYED`
- `squad wounded: 4`
- `fire mode: hold`
- `units: 9`
- `turret facing: 90.0`，`hull facing: 0.0`（炮塔与车体独立）
- `mortar ammo: 119`（迫击炮经观察员开火 1 次）
- `crew abandoned: True`（乘员全灭后弃车）

## 5. 遗留问题

| ID | 级别 | 描述 | 处理建议 |
|----|------|------|---------|
| PF-02 | P2 | UAT 缺人工点击验证。已补真实窗口点击链路 UAT，11/11 通过。 | 仅剩画面观感需人工确认 |
| PF-03 | P3 | 真实窗口性能未复测。已执行，见 §3.1。 | 关闭 |
| PF-04 | P2 | 真实窗口 heavy 场景中位 56.6 FPS、最差 52.1 FPS，低于 60 FPS 目标。测量时系统负载 12.3，数据偏低。 | 在空闲机器复跑 `scripts/real_window_perf.py` 后判定 |

已关闭：
- PF-01：heavy_load 中位 76.4 FPS，最差 63.5 FPS；normal_load 中位 102.3 FPS。
- PF-03：真实窗口复测完成。
- GAP-08：基准运行稳定，未再超时。
- GAP-11：攻击线记录攻击者坐标。
- GAP-12：LOS 缓存键加入 `max_range`。
- GAP-13：`special_rules` 运行时入口补全。
- GAP-14：场景文件加载前校验。
- GAP-15：部署工厂旧 ID 改为数据库 ID。
- GAP-16：Flak 36 使用专属武器档案。
- GAP-21：炮塔独立朝向。
- GAP-22：乘员伤亡弃车。
- GAP-23：迫击炮间瞄。

## 6. 放行决定

| 项目 | 结论 |
|------|------|
| 功能与机制 | 放行 |
| 回归与验收 | 放行 |
| 性能（无窗口） | 放行（heavy_load 中位与最差均 ≥60） |
| 性能（真实窗口） | 有条件放行（heavy 56.6 FPS，PF-04 待优化） |
| 点击链路 UAT | 通过（11/11，真实窗口） |
| 发布范围 | 内部里程碑版本；不作为正式对外发布 |
| 正式发布前置条件 | 人工确认画面与手感；PF-04 优化 |

## 7. 签署

| 角色 | 姓名 | 日期 | 结论 |
|------|------|------|------|
| 开发（AI 代理） | Trae | 2026-11-08 | 提交门禁 |
| 产品负责人 | 待填 | 待填 | 待审批 |

## 8. 推送记录

| 项目 | 值 |
|------|-----|
| 分支 | `main` |
| 远端 | `origin`（`git@github.com:lulin70/PyCC2.git`） |
| 提交 | `4eaa123` feat(cc2): complete W1-W5 parity work and fix runtime mechanism defects |
| 范围 | 912 个文件（源码、测试、场景、文档、基线、素材） |
| 排除 | 仓库根目录临时脚本与生成物（`test_sprint*.py`、`coverage_audit.json`、`*.diff/`、对比截图） |

