# PyCC2 v0.7.1 推进计划 — TD-077 19 个孤立原型决策与清理

> **版本**: v0.7.0 → v0.7.1 (PATCH, 纯清理无新功能) + v0.8.0+ (MINOR, INTEGRATE 接入)
> **日期**: 2026-07-17 | **状态**: 🚧 执行中
> **来源**: DevSquad 7-Role 架构师评估 (2026-07-17 session 4) + 深度扫描确认 19 模块 0 src 引用
> **原则**: 文档先行，活文档时刻更新；PATCH 版本只做清理不接入新功能

## 📋 执行摘要

v0.7.0 完成后，TD-077（19 个孤立原型决策）是下一步。通过 3 个并行 subagent（架构师/UI 设计师/架构师）对 19 个模块进行 7-Role 评估，决策分布：

| 决策 | 数量 | 版本 | 理由 |
|------|------|------|------|
| **DELETE** | 4 | v0.7.1 | 被活跃模块完全取代 + 无专属测试或 schema 脱节 |
| **ARCHIVE** | 7 | v0.7.1 | 有参考价值但实现有缺陷或需整体重构，移到 `_archive/` |
| **INTEGRATE** | 8 | v0.8.0+ | CC2 原版核心功能 + 代码完整 + 无活跃取代者，标记 ORPHAN 待接入 |

**版本号决策**：
- v0.7.1 (PATCH): DELETE 4 + ARCHIVE 7 + ORPHAN 标记 8 — 纯清理，无新功能，遵循"功能没有更新时版本不变前两位"
- v0.8.0+ (MINOR): INTEGRATE 8 个模块 — 新功能接入，分多个版本推进

---

## 🗂️ 19 个模块决策矩阵

### DELETE (4 个) — v0.7.1 执行

| # | 模块 | 行数 | 决策理由 | 取代者 |
|---|------|------|---------|--------|
| 1 | `presentation/ui/strategic_map_view.py` | 216 | 6 个 sector 坐标硬编码 PLACEHOLDER + 无真实数据接入 | `campaign_ui_helpers.draw_strategic_map()` |
| 2 | `presentation/ui/strategic_map.py` | 150 | 与 #1 互相重复造轮子 + 5 bridge 硬编码 | `campaign_ui_helpers.draw_strategic_map()` |
| 3 | `presentation/ui/aar_panel.py` | 170 | BattleResult 字段与活跃 report dict 接口不匹配 (schema 脱节) | `CampaignUIReportMixin._render_report()` |
| 4 | `presentation/rendering/weather_visual_effects.py` | 180 | 完全冗余 + 无专属测试 (test_weather_effects.py 测试的是活跃 weather_effects.py) | `weather_effects.py` + `weather_renderer.py` |

**DELETE 总行数**: 716 行 + 对应测试 0 行（均无专属测试）

### ARCHIVE (7 个) — v0.7.1 执行，移到 `src/pycc2/_archive/`

| # | 模块 | 行数 | 决策理由 | 测试 |
|---|------|------|---------|------|
| 1 | `domain/ai/ai_config.py` | 193 | 数据驱动方向正确，但需所有 AI 模块整体重构才有意义 | 无 |
| 2 | `domain/systems/casualty_system.py` | 459 | 实现有缺陷 (setattr 反射/perf_counter 计时/morale_bonus 不一致) + 无测试 | 无 |
| 3 | `domain/systems/ammo_type_system.py` | 341 | 实现不足 (perf_counter cooldown/smoke 用 dict 而非 dataclass) + 无测试 | 无 |
| 4 | `presentation/ui/combat_log.py` | 284 | 渲染与数据耦合 + pygame.Surface 做 field 默认值 + 无测试 | 无 |
| 5 | `presentation/ui/cc2_hud.py` | 432 | 活跃 CC2BottomPanel 已完全覆盖，但架构清晰可作重构参考 | test_cc2_hud.py (归档) |
| 6 | `presentation/ui/enhanced_ui_renderer.py` | 346 | 通用绘制工具库，活跃系统无等价工具集，保留备用 | test_enhanced_ui_renderer.py (归档) |
| 7 | `presentation/rendering/enhanced_post_processing.py` | 267 | 逐像素 Python 循环致性能不可用 + 核心功能已被 post_processing.py 覆盖 | test_enhanced_post_processing.py (归档) |

**ARCHIVE 总行数**: 2322 行 + 对应测试 3 个文件

### INTEGRATE (8 个) — v0.8.0+ 执行，v0.7.1 标记 ORPHAN

| # | 模块 | 行数 | CC2 符合度 | 接入工作量 | 决策理由 | 测试 |
|---|------|------|-----------|-----------|---------|------|
| 1 | `domain/ai/cover_seek_ai.py` | 540 | HIGH | MEDIUM (2-5h) | CC2 标志性压制找掩体行为 + 已对齐 TacticIntent 体系 | test_cover_seek_ai.py |
| 2 | `domain/systems/psychology_system.py` | 369 | HIGH | LOW (<2h) | 现有 MoraleSystem.can_accept_orders 的精细化升级 | test_psychology_system.py |
| 3 | `presentation/ui/squad_group_manager.py` | 149 | HIGH | MEDIUM (2-5h) | CC2 标志性 Ctrl+数字编组操作 + 用户感知强 | 无 |
| 4 | `domain/systems/day_night_cycle.py` | 214 | HIGH | MEDIUM (2-5h) | ⚠️ 前置: 需解决与 IDayNightCycle 接口签名不兼容 | test_day_night_cycle.py |
| 5 | `presentation/rendering/path_preview.py` | 309 | HIGH | MEDIUM (2-5h) | CC2 核心移动路径预览 + 无活跃取代者 | 无 |
| 6 | `presentation/rendering/range_indicator.py` | 192 | HIGH | MEDIUM (2-5h) | CC2 核心射程圈 + 无活跃取代者 | 无 |
| 7 | `domain/systems/vehicle_variant_generator.py` | 388 | HIGH | MEDIUM (2-5h) | 市场花园真实载具 + 模板不在活跃系统 | test_variant_generators.py (共享) |
| 8 | `domain/systems/faction_variant_generator.py` | 366 | HIGH | MEDIUM (2-5h) | 精英单位+波兰伞兵旅 + 模板不在活跃系统 | test_variant_generators.py (共享) |

**INTEGRATE 总行数**: 2527 行 + 对应测试 4 个文件

---

## 📅 推进时间表

| 版本 | 内容 | 优先级 | 类型 |
|------|------|--------|------|
| **v0.7.1 (本次)** | DELETE 4 + ARCHIVE 7 + ORPHAN 标记 8 + 测试同步 | P1 | 纯清理 |
| **v0.8.0** | INTEGRATE psychology_system (最低工作量 <2h) + squad_group_manager | P1 | 新功能 |
| **v0.8.1** | INTEGRATE cover_seek_ai + path_preview + range_indicator | P1 | 新功能 |
| **v0.8.2** | INTEGRATE day_night_cycle (需先解决接口兼容) + variant generators | P2 | 新功能 |

---

## 🔒 v0.7.1 执行清单

### Step 1: DELETE (4 个模块) ✅ 完成

- [x] 删除 `src/pycc2/presentation/ui/strategic_map_view.py` (216 行)
- [x] 删除 `src/pycc2/presentation/ui/strategic_map.py` (150 行)
- [x] 删除 `src/pycc2/presentation/ui/aar_panel.py` (170 行)
- [x] 删除 `src/pycc2/presentation/rendering/weather_visual_effects.py` (180 行)
- [x] 确认无测试文件需要删除（4 个均无专属测试）
- [x] 附带: 删除 test_zero_coverage_smoke.py::TestWeatherVisualEffects (7 tests)

### Step 2: ARCHIVE (10 个模块 + 4 个测试文件) ✅ 完成

- [x] 创建 `src/pycc2/_archive/` 目录
- [x] 创建 `tests/_archive/` 目录
- [x] 移动 7 个模块到 `src/pycc2/_archive/` (ai_config/casualty_system/ammo_type_system/combat_log/cc2_hud/enhanced_ui_renderer/enhanced_post_processing)
- [x] 移动 3 个连带模块 (hud_constants/hud_input/hud_renderer — cc2_hud 自闭合死代码群)
- [x] 移动 4 个测试文件到 `tests/_archive/` (test_cc2_hud/test_enhanced_ui_renderer/test_enhanced_post_processing/test_ai_config)
- [x] 在 `src/pycc2/_archive/__init__.py` 添加说明 docstring
- [x] 确认 ARCHIVE 模块的依赖链 — cc2_hud + hud_constants + hud_input + hud_renderer 4 个文件仅互相引用，一并归档
- [x] 分离清理 4 个测试文件 (test_aar_and_timecontrol/test_phase_b_final_sprint/test_phase_c_p1_and_d_core/test_strategic_ui) — 删除归档模块的测试类，保留活跃模块测试

### Step 3: ORPHAN 标记 (8 个 INTEGRATE 模块) ✅ 完成

- [x] 在 8 个模块 docstring 顶部添加 `STATUS: ORPHAN — pending v0.8.0+ integration (TD-077)` (cover_seek_ai/psychology_system/squad_group_manager/day_night_cycle/path_preview/range_indicator/vehicle_variant_generator/faction_variant_generator)
- [x] 不删除、不移动，仅标记状态

### Step 4: 验证 + 文档同步

- [x] 全量测试验证 (6157 collected / 6138 passed / 2 skipped; 1 flaky benchmark `test_render_16x16_map_time` median 112ms > 100ms threshold, 2/5 runs below 100ms — 非功能回归, 待后续追踪)
- [x] ruff 0 errors
- [x] mypy (v0.7.0 基线 2 pre-existing errors, 无新增)
- [x] check_doc_consistency 11/11 PASS (VERSION=0.7.1)
- [x] 更新 TECH_DEBT.md (TD-077 ✅ RESOLVED + 总览表 0 活跃)
- [x] 更新 CHANGELOG.md (v0.7.1 条目 + 教训 3 条)
- [x] 更新 README 三语 + SKILL.md (版本号 v0.7.1 + 测试数 6509→6138)
- [x] 更新 PROJECT_STATUS.md + TEST_PLAN.md (版本号 + 测试数 6157)
- [ ] Git commit + push

---

## ⚠️ 风险提示

1. **ARCHIVE 连带清理**: `cc2_hud.py` 依赖 `hud_constants.py`/`hud_input.py`/`hud_renderer.py`，这三个模块如果仅被 cc2_hud 引用，也应一并归档
2. **test_variant_generators.py**: 同时测试 vehicle + faction 两个 generator，两者都 INTEGRATE，测试保留原位
3. **test_weather_effects.py**: 测试的是活跃 `weather_effects.py`，非被删除的 `weather_visual_effects.py`，保留原位
4. **INTEGRATE 前置条件**: day_night_cycle 需先解决与 IDayNightCycle 接口签名不兼容 (TimeOfDay enum vs float)
5. **INTEGRATE weapon_id 验证**: variant_generator 引用的 weapon_id (us_76mm_sherman/de_fg42/pl_enfield_no4 等) 必须在活跃武器系统中存在

---

> **文档先行，万事留痕** — 本决策文档先于代码执行，7-Role 评估共识后将作为执行依据。
> **活文档原则** — 本文档随 v0.7.1 推进实时更新，每个 Step 完成后同步状态。
