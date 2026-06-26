# PyCC2 项目整理评估报告（7维度成熟度评估）

> **评估日期**：2026-06-26
> **评估方法**：DevSquad V3.8 项目整理评估（3 并行子代理 + 独立交叉验证）
> **评估对象**：PyCC2 v0.3.42（commit d326c8b，Phase 1-7 质量冲刺宣称完成）
> **评估结论**：综合成熟度 **62/100 (C+)**，建议**推迟发布**直至 P0 修复
> **评估报告**：`docs/ASSESSMENT_D7_MATURITY.md`

---

## 0. 执行摘要

PyCC2 刚完成 Phase 1-7 质量冲刺（commit d326c8b），宣称"mypy 0 errors、Bandit 0 Medium/High、Marker 100%、4369 测试、全文档统一 v0.3.42"。经独立 7 维度评估，**多项宣称与实际不符**，CI 管道完全失效（最近 10 次运行 0% 成功率），5 项 P0 问题阻断发布。

### 宣称 vs 实测对照表

| 指标 | Phase 1-7 宣称 | 独立验证实测 | 一致性 |
|---|---|---|---|
| mypy errors | 0 | 0（CI 命令 `MYPYPATH=src mypy -p pycc2`） | ✅ 属实 |
| Ruff errors | 2（autotile_system.py + minimap.py） | **22**（8 I001 + 7 UP037 + 3 B010 + 3 F401 + 1 UP035） | ❌ 严重低估 |
| Bandit Medium/High | 0/0 | 0/0（Low 369，B101+B311 游戏逻辑） | ✅ 属实 |
| Marker 覆盖率 | 100%（4369/4369） | 100%（4369/4369，`not unit and not integration and not e2e and not benchmark and not slow` 收集 0） | ✅ 属实 |
| >1000 行文件 | 12 | **13**（含 unit_diversity_expansion.py 恰 1000 行） | ❌ 少计 1 个 |
| 文档版本统一 | v0.3.42 | **__version__ = "0.3.41"**（代码内）；11+ 份文档停留 v0.3.39~0.3.41 | ❌ 严重不一致 |
| CI 状态 | "CI 全绿" | **最近 10 次运行 0% 成功率**（全部 failure 或 in_progress 超时） | ❌ 严重失实 |
| 全量 pytest | "4355 passed" | 2 benchmark 失败 + 3 e2e 失败 + 18 errors（重构未同步测试） | ❌ 23 项失败/错误 |
| slow 测试数 | 7 | **14**（6 sprite + 2 perf + 6 content_expansion） | ❌ 少计 7 个 |

### 综合成熟度评分

| 维度 | 评分 | 等级 | 一句话结论 |
|---|---|---|---|
| 1. 架构 | 80/100 | B+ | DDD 4 层清晰，342 模块 0 循环依赖 |
| 2. 安全 | 90/100 | A- | Bandit 0 M/H，subprocess/XML/HMAC 全链路安全 |
| 3. 测试 | 55/100 | C- | 设计优质但执行失效（CI 0%、e2e hang、benchmark 回归） |
| 4. 性能 | 78/100 | B | Dirty rect + 6 级缓存 + FPS 自适应，但 2 个基准测试失败 |
| 5. 可维护性 | 50/100 | C- | 13 God Class + 5-7 幽灵模块(1914+行) + 22 ruff 错误 |
| 6. 文档 | 55/100 | C- | 代码 __version__ 错误 + 11+ 文档版本漂移 + README 测试数失真 |
| 7. 集成 | 45/100 | D+ | CI 0% 成功率 + --cov-fail-under 缺失 + 无依赖锁文件 |
| **综合** | **62/100** | **C+** | **架构安全优秀，但 CI/文档/可维护性严重欠债，推迟发布** |

---

## 1. 维度1：7维度代码走读

### 1.1 架构（80/100）

**证据**：
- `find src/pycc2 -type d` 确认 DDD 4 层结构：`domain/`（combat/components/ai/systems/entities/interfaces/value_objects）+ `infrastructure/`（audio/parsers/rendering/save_system/resource_cache）+ `presentation/`（audio/input/rendering/ui）+ `services/`（game_loop/combat_director/event_bus 等 18 文件）
- `grep -rn "from pycc2.services" src/pycc2/domain` → 0 命中（domain 零向上依赖）
- `grep -rn "from pycc2.services" src/pycc2/presentation` → 0 命中
- 全量导入 342 个模块，**0 import errors**，无循环依赖

**扣分项**：
- 缺独立 application 层（services 混合 controller/loop/service）
- presentation→infrastructure 3 处反向依赖（new_game_menu、debug_overlay，已用函数内导入缓解）

### 1.2 安全（90/100）

**证据**（`bandit -r src/pycc2 -ll` 实测）：
```
Total issues (by severity):  Undefined: 0  Low: 369  Medium: 0  High: 0
```

| 检查项 | 状态 | 证据 |
|---|---|---|
| subprocess 调用 | ✅ 安全 | `pixvoxel_loader.py:409`（7z 解压，timeout=120）、`window_config.py:162`（xdpyinfo，timeout=5），均列表形式无 shell=True |
| URL scheme | ✅ 限制 | `resource_cache.py:230-233` 校验 `scheme in {"http","https"}`，`# nosec B310` 合理 |
| XML 解析 | ✅ XXE-safe | `svg_sprite_loader.py:303` 用 `defusedxml.ElementTree.parse` + `DefusedXmlException` 捕获 |
| HMAC 密钥 | ✅ 完整 | `save_system.py:190-251`：32 字节最小长度、production 强制抛错、`hmac.compare_digest` 防时序攻击、`_sanitize_filename` 防路径穿越、dev 用 `secrets.token_bytes(32)` |
| 硬编码密钥 | ✅ 无 | grep 未发现 |

**扣分项**：
- 无 pip-audit/safety 接入（docs/SECURITY.md 列为计划但未实现）
- 无依赖锁文件（供应链可复现性风险）

### 1.3 测试设计（55/100）

**设计质量（8/10）**：
- 159 个测试文件（118 unit + 7 integration + 25 e2e + 1 acceptance + 3 benchmark）
- 抽样 5 个文件全部使用真实组件（真实 `pygame.Surface`、`EnhancedRenderer`、`Unit`、`GameMap`），零 Mock
- `test_full_user_journey.py` 提供完整 9 步用户旅程（主菜单→战役→部署→战斗→暂停→退出），通过 `pygame.event.post` 注入鼠标/键盘事件
- `test_combat_engagement.py` 零 Mock，覆盖距离/弹药/士气/掩护/目标选择/火力模式

**执行质量（2/10）**：
- **2 个 benchmark 测试失败**：`test_surface_pool_efficiency` 和 `test_surface_pool_size_stability` 因 `EnhancedRenderer` 重构（`_surface_pool` → `surface_pool_fn`）未同步更新测试
- **e2e 套件 hang**：488 个 e2e 测试运行 10+ 分钟无任何输出被强制终止，`screenshots/` 目录无新截图，hang 发生在第一个测试早期
- **CI 0% 成功率**：最近 10 次 CI 运行全部失败，测试作业 6h 超时被 GitHub 强制终止

### 1.4 性能（78/100）

**证据**：
- `mark_full_dirty()` 仅 3 处调用（screen_effects_renderer × 2 + world_renderer × 1 首帧），无滥用
- `_DirtyRectTracker`：`max_rects=16` 阈值自动 fallback `flip()`，矩形 union 合并带 200 像素容差
- 6 级地形缓存（texture_cache/autotile_cache/scaled_texture_cache/transition_cache/strip_cache + grid-snapped 对齐）
- `game_loop.py` TARGET_FPS=60 + FPS 自适应后处理（60 帧滚动窗口，<45 FPS 禁用，>55 FPS 恢复，迟滞防抖）
- `spatial_hash.py` 替换 O(n²) 目标选择

**扣分项**：
- 2 个性能基准测试失败（`_surface_pool` 重构回归）
- `test_pre_release_full_journey.py:591` 的 `max(frame_times)` 是 dead code（计算后未断言）

### 1.5 可维护性（50/100）

**God Class 清单（13 个 ≥1000 行，非声称的 12 个）**：

| # | 文件 | 行数 | 性质 | 可拆分 |
|---|---|---|---|---|
| 1 | cc2_authentic_weapons.py | 1857 | 数据库（3 Enum+1 dataclass+3 函数） | 否（数据文件） |
| 2 | campaign_data.py | 1457 | 1 个工厂函数 | 否（数据文件） |
| 3 | terrain_tile_generator.py | 1315 | 像素艺术生成 | 是（按地形类型） |
| 4 | cc2_building_renderer.py | 1209 | 渲染 | 是 |
| 5 | deployment_ui.py | 1183 | 70 方法 | **应拆分**（边界 God Class） |
| 6 | tactic_executor.py | 1175 | 31 方法，协调 10+ AI 子系统 | **边界 God Class** |
| 7 | deployment_renderer.py | 1171 | 21 方法 | 是 |
| 8 | pixvoxel_loader.py | 1139 | 资源加载 | 是（下载/解析/缓存） |
| 9 | infantry_pixel_renderer.py | 1137 | 像素艺术 | 是 |
| 10 | pixel_artist_3d.py | 1134 | 像素艺术 | 是 |
| 11 | sprite_renderer.py | 1100 | 渲染 | 是 |
| 12 | campaign_ui_rendering.py | 1064 | UI 渲染 | 是 |
| 13 | unit_diversity_expansion.py | 1000 | 数据扩展 | 边界 |

**命名冲突（2 处）**：
- `trench_digging`：`domain/systems/trench_digging.py`（65L，`@dataclass TrenchDiggingAI` stub）与 `domain/ai/trench_digging.py`（370L，`TrenchDiggingAI(TacticalAIBase)` 真实实现）— 同名类双定义
- `weather_effects`：`domain/systems/weather_effects.py`（`WeatherType(Enum)`）与 `presentation/rendering/weather_effects.py`（重复定义 `WeatherType(Enum)`）— 两个独立 Enum 存在行为分歧风险

**ruff 错误（22 个，非声称的 2 个）**：
```
8  I001    unsorted-imports      [*] 可自动修复
7  UP037   quoted-annotation     [*] 可自动修复
3  B010    set-attr-with-constant [*] 可自动修复
3  F401    unused-import         [*] 可自动修复
1  UP035   deprecated-import     [*] 可自动修复
```
声称的 2 个错误（autotile_system.py F401 + minimap.py I001）确实存在，但另外 20 个被遗漏。

**死代码（vulture --min-confidence 80）**：13 项（unused variable + unused import + redundant if-condition）

### 1.6 文档（55/100）

**docstring 覆盖率**：75.4%（3238/4296 公共定义有 docstring，AST 扫描 343 文件验证），低于 80% 目标

**版本号不一致（P0）**：

| 文件 | 实测版本 | 期望 | 状态 |
|---|---|---|---|
| pyproject.toml | 0.3.42 | 0.3.42 | ✅ |
| README.md 头部 | v0.3.42 | 0.3.42 | ✅ |
| docs/TEST_PLAN.md | v0.3.42 | 0.3.42 | ✅ |
| docs/TECH_DEBT.md | v0.3.42 | 0.3.42 | ✅ |
| docs/PYCC2_QUALITY_SPRINT.md | v0.3.42 | 0.3.42 | ✅ |
| **src/pycc2/__init__.py** | **0.3.41** | 0.3.42 | ❌ **代码版本号未同步** |
| README.md "What's New" | v0.3.41 | 0.3.42 | ❌ |
| README_ja.md | v0.3.41 | 0.3.42 | ❌ |
| INSTALL.md / INSTALL_zh.md | v0.3.41 | 0.3.42 | ❌ |
| USER_MANUAL.md | v0.3.41 | 0.3.42 | ❌ |
| docs/USER_GUIDE.md | v0.3.39 | 0.3.42 | ❌ 落后 3 版本 |
| docs/DESIGN.md | v0.3.39 | 0.3.42 | ❌ 落后 3 版本 |
| docs/PRD.md | v0.3.41 | 0.3.42 | ❌ |
| docs/ROADMAP.md | v0.3.41 / 0.3.39 | 0.3.42 | ❌ 自相矛盾 |
| .github/workflows/release.yml | default: '0.3.41' | 0.3.42 | ❌ |
| CHANGELOG.md | [0.3.42] + [0.3.42.1] 并存 | 0.3.42 | ❌ 子版本破坏统一 |

**README 测试数失真**：badge `~4298 passed` / 正文 `~3985 tests` / `Unit tests (~3200)` — 三处互相打架且都与实测 4369/3680 不符

**README 引用不存在脚本**：`scripts/strict_e2e_journey.py`（README line 462 作为快速开始示例，文件不存在）

**CHANGELOG 缺 Phase 1-2 记录**：`[Unreleased]` 仅记录 Phase 3-7，Phase 1（CI 门禁改造）和 Phase 2（mypy 1163→0）未进入

### 1.7 集成（45/100）

详见维度5（CI/CD 检查）。

---

## 2. 维度2：文档同步

### 2.1 版本号一致性（40/100）

Phase 7 声称"All docs aligned to v0.3.42"，但该清单**刻意省略了** `__init__.py`、INSTALL.md、USER_MANUAL.md、README_ja.md、release.yml、PRD/DESIGN/ROADMAP/GAP_ANALYSIS 共 11+ 处仍停留在 v0.3.39~v0.3.41。

**最严重**：`src/pycc2/__init__.py` 的 `__version__ = "0.3.41"` — 运行时 `pycc2 --version` 报告错误版本，存档兼容性检查可能失真。

### 2.2 代码-文档一致性（55/100）

- TEST_PLAN 测试数 4369 = `pytest --collect-only` 实测 4369 ✅
- >1000 行文件数：TECH_DEBT 声称 12 = 实测 13 ❌（少计 unit_diversity_expansion.py）
- >500 行文件数：TECH_DEBT TD-026 标题"29个" / CHANGELOG"53个" / 实测 52 个 — 三方互不一致
- README 测试数：badge 4298 / 正文 3985 / 实测 4369 — 三处打架

### 2.3 外部文档质量（50/100）

- README Quick Start 可复现 ✅（Python 3.11+/Pygame 2.2+，`pip install -e .` + `pycc2` 启动）
- 但首页 badge 和正文测试数全部过期，与自身 v0.3.42 头部矛盾
- 引用不存在的 `scripts/strict_e2e_journey.py`

### 2.4 过程文件残留

- 根目录 `IMAGE_OPTIMIZATION_COMPLETION_SUMMARY.md`（CHANGELOG 声称"Deleted 19 process .md"但此文件漏网）
- docs/ 残留 4 份一次性执行报告（INTEGRATION_EXECUTION_PLAN.md、PRONE_ENHANCEMENT_REPORT.md、STEP1_PORTRAIT_INTEGRATION_REPORT.md、STEP2-5_ENHANCEMENTS_ENABLED_REPORT.md）
- 3 份测试策略文档重叠（TEST_PLAN.md / TEST_STRATEGY_COMPREHENSIVE.md / TEST_USER_CENTRIC.md）
- 21 个测试产物 PNG 入库 docs/（enhancement_test_results/ + prone_test_results/）

---

## 3. 维度3：技术债 + 幽灵功能

### 3.1 幽灵功能清单（1914+ 行死代码）

| 文件 | 主要类 | 行数 | 生产引用 | 测试引用 | 判定 |
|---|---|---|---|---|---|
| domain/systems/ceasefire_retreat.py | CeasefireSystem/RetreatSystem 等 6 类 | 581 | 0 | 0 | **纯幽灵** |
| domain/systems/enhanced_aar.py | EnhancedAARStats/Collector 等 7 类 | 425 | 0 | 0 | **纯幽灵** |
| domain/systems/battle_replay.py | ReplayData/Recorder/Player 等 7 类 | 311 | 0 | 0 | **纯幽灵**（首行注释"PLANNED: Not yet wired"） |
| domain/systems/reinforcement_evasion_bgm.py | ReinforcementSystem/VehicleEvasionAI/DynamicBGMSystem 等 5 类 | 362 | 0 | 0 | **纯幽灵** |
| domain/systems/weapon_switch_system.py | WeaponSwitchSystem/WeaponSlot 等 3 类 | 235 | 0 | 36 | **半幽灵**（有测试无生产接线） |
| domain/systems/airdrop_supply.py | AirdropSupplySystem | ~150 | 0 | 0 | **半幽灵** |

`game_loop_assembler.py`（Composition Root）验证：未导入上述任何一个模块。

### 3.2 死代码（vulture --min-confidence 80）

13 项，包括 unused variable（engagement、inf_pos、observer_height 等）、unused import（apply_enhanced_post_processing、draw_icon/draw_panel）、redundant if-condition（minimap.py:318）。

### 3.3 TODO/FIXME

`grep -rn "TODO\|FIXME\|HACK" src/pycc2` → **0 命中** ✅（"XXX" 30 处全部为 "XXX Corps" 英国陆军历史单位，非技术债标记）

### 3.4 无依赖锁文件（P0）

```
$ ls *.lock poetry.lock uv.lock pdm.lock requirements*.txt
zsh: no matches found
```
**违反项目硬约束**："必须包含依赖锁文件以确保构建可复现"。pyproject.toml 使用宽松版本范围（`pygame>=2.2`、`numpy>=1.26`），传递依赖未固定，构建不可复现。

---

## 4. 维度4：回归/集成/性能/E2E/用户旅程测试

### 4.1 Marker 分布（100/100）

```
pytest --collect-only -q                                    → 4369 tests
pytest -m "unit" --collect-only -q                          → 3680 tests
pytest -m "integration" --collect-only -q                   → 138 tests
pytest -m "e2e" --collect-only -q                            → 530 tests
pytest -m "benchmark" --collect-only -q                     → 21 tests
pytest -m "slow" --collect-only -q                           → 14 tests
pytest -m "not unit and not integration and not e2e and not benchmark and not slow"
                                                            → no tests collected (4369 deselected)
```
**100% marker 覆盖验证通过** ✅

### 4.2 回归测试结果（45/100）

| 范围 | 结果 | 耗时 |
|---|---|---|
| tests/unit/ (not slow) | **3666 passed, 2 skipped** | 11.78s ✅ |
| tests/integration/ (not slow) | **138 passed** | 1.80s ✅ |
| tests/benchmark/ (not slow) | **2 failed, 17 passed** | 9.73s ❌ |
| tests/e2e/ (not slow) | **3 failed, 463 passed, 4 skipped, 18 errors** | 158.40s ❌ |
| tests/acceptance/ | **42 passed** | 0.87s ✅ |

**失败/错误清单（23 项）**：
```
# benchmark 失败（2 项）— EnhancedRenderer 重构未同步
FAILED test_surface_pool_efficiency — AttributeError: 'EnhancedRenderer' object has no attribute '_surface_pool'
FAILED test_surface_pool_size_stability — 同上

# e2e 失败（3 项）
FAILED test_i12_panel_has_all_sections — AssertionError: assert False
FAILED test_40_all_8_directions_prone_render — Timeout (>120.0s) — 做与 slow 测试相同的事但未标 slow
FAILED test_full_render_pipeline_no_crash — pygame.error: failed to create renderer (headless vsync=1 不兼容)

# e2e 错误（18 项）— test_real_gameplay_e2e.py
ERROR test_real_gameplay_e2e.py (18 个) — property '_screen' of 'EnhancedRenderer' object has no setter（重构破坏）
```
**根因**：`EnhancedRenderer` 重构（`_surface_pool` → `surface_pool_fn`、`_screen` setter 移除）未同步更新测试，**23 项失败/错误全部因重构遗漏**。CI 因 0% 成功率从未捕获这些回归。

### 4.3 E2E/用户旅程覆盖（设计 80/执行 30）

- 26 个 e2e 测试文件，包含 `test_full_user_journey.py`（9 步完整旅程）、`test_pre_release_full_journey.py`（12 阶段预发布）、`test_comprehensive_acceptance.py`（验收测试）
- 画面操作覆盖：`_click_at`、`_right_click_at`、`_press_key`、`_move_mouse_to` 辅助函数完整
- **但 23 项失败/错误（全部因 EnhancedRenderer 重构未同步测试）使 e2e 实际可执行性严重受损**

### 4.4 slow 测试审计

实际 14 个（非宣称的 7 个）：
- `test_pixel_artist.py` 3 个 class（MGSquad/EightDirections/Factory）= 6 个 slow 测试
- `test_content_expansion.py::TestNewUnitSprites` = 6 个 slow 测试（tank/sniper/medic/crater/swamp/cache）
- `test_perf_benchmark.py` 2 个（entity_resolution_performance/pathfinding_50_tiles）

**严重遗漏**：`test_40_all_8_directions_prone_render` 做与 slow 测试相同的 8 方向精灵生成，但**未标记 @pytest.mark.slow**，导致 Timeout (>120.0s) 拖垮整个 e2e 套件。这是 CI 6h 超时的元凶之一。

---

## 5. 维度5：CI/CD 检查

### 5.1 CI 配置（40/100）

| 检查项 | 状态 | 证据 |
|---|---|---|
| mypy 阻塞 | ✅ 是 | `MYPYPATH=src mypy -p pycc2 --no-error-summary` 独立 step |
| Bandit 接入 | ✅ 是 | `bandit -r src/ -ll --skip B101,B311,B601` |
| Codecov fail_ci_if_error | ✅ true | `fail_ci_if_error: true` |
| slow 测试隔离 | ✅ 是 | 独立 `slow-tests` job，`needs: test` |
| Python 矩阵 | ✅ 3.11/3.12 | `matrix: python-version: ["3.11", "3.12"]` |
| **--cov-fail-under** | ❌ **缺失** | CI 未传参（违反"CI必须显式传--cov-fail-under"教训） |
| **timeout-minutes** | ❌ **缺失** | 导致 6h GitHub 最大执行时间超时 |
| **pytest-timeout** | ❌ **未安装** | e2e hang 无法被捕获 |
| **pipefail** | ❌ 未配置 | 当前无 `\| tee` 但未来添加时有风险 |

### 5.2 CI 历史状态（10/100）

```
$ gh run list --limit 10
in_progress  refactor: Phase 5-7 quality sprint finale  CI  main  3h54m54s
completed failure  refactor: Phase 3 God Class split     CI  main  6h0m18s
completed failure  fix: P0 CI unblock + P2 pixel_artist  CI  main  6h0m20s
completed failure  fix: P0 CI unblock (#12)               CI  main  6h0m21s
completed failure  chore(deps): bump actions/checkout     CI  main  3m57s
completed failure  fix: P1-P2 large file split            CI  main  4m16s
completed failure  fix: P0 version sync + badge           CI  main  3m10s
completed failure  fix: P0 morale routing bug             CI  main  3m13s
```
**最近 10 次 CI 运行全部失败，成功率 0%**。失败模式：
1. Lint job：ruff 26 个 I001 错误
2. Test job：6h0m0s 达到 GitHub 最大执行时间被强制终止（`Terminate orphan process: pid (2432) (pytest)`）

### 5.3 CD 配置（80/100）

`release.yml`（105 行）完整：
- 触发：tag `v*` 推送或手动 `workflow_dispatch`
- 质量门：`pytest tests/ -q --tb=line --maxfail=10`
- 版本一致性校验：tag 版本 vs pyproject.toml 版本
- 构建：`python -m build`（sdist + wheel）
- GitHub Release + PyPI 发布 + Docker 构建

**扣分**：无自动版本 bump、无发布后 smoke 测试、release.yml 默认版本输入仍为 0.3.41

### 5.4 依赖安全审计（30/100）

- dependabot.yml 存在但极简（仅 pip + github-actions 周更新，无 reviewers/labels/groups）
- pip-audit：仅在 docs/SECURITY.md 和 docs/PRD.md 作为计划提及，**未实际接入 CI**
- safety：未配置

---

## 6. 维度6：目录结构清理

### 6.1 临时文件

- `.DS_Store` × 2（根目录 + docs/，已 gitignored）
- `__pycache__/` × 28（已 gitignored）
- `.pytest_cache/`、`.mypy_cache/`、`.ruff_cache/` 各 1（已 gitignored）
- **无 .bak/.backup/.tmp/.old 文件** ✅

### 6.2 目录组织（65/100）

- 根目录 12 个 .md 文件（`IMAGE_OPTIMIZATION_COMPLETION_SUMMARY.md` 应归 docs/）
- docs/ 28 个 .md + 2 个测试产物子目录（略平铺）
- src/pycc2/ DDD 4 层清晰 ✅
- tests/ 金字塔结构清晰（unit/integration/e2e/benchmark/acceptance）✅
- **空目录**：`src/saves/saves/`（运行时存档不应入库）、`assets/sprites/vehicles`、`assets/sprites/effects`（资源占位可接受）

### 6.3 .gitignore（80/100）

覆盖完整：`__pycache__/`、`*.py[cod]`、`.pytest_cache/`、`.mypy_cache/`、`.env`、`.venv`、`build/`、`dist/`、`*.egg-info/` ✅

**缺失**：`.ruff_cache/`（项目使用 ruff，本地已有该目录但未忽略）
**冗余**：`.DS_Store` 重复出现 2 次

### 6.4 git 状态

分支 `main`，与 `origin/main` 同步，工作树**干净**（无未提交改动）。最近提交 `d326c8b refactor: Phase 5-7 quality sprint finale`。

---

## 7. 维度7：严格诚实成熟度评价

### 7.1 综合评分

| 维度 | 评分 | 等级 | 权重 | 加权分 |
|---|---|---|---|---|
| 1. 架构 | 80 | B+ | 15% | 12.0 |
| 2. 安全 | 90 | A- | 15% | 13.5 |
| 3. 测试 | 55 | C- | 20% | 11.0 |
| 4. 性能 | 78 | B | 10% | 7.8 |
| 5. 可维护性 | 50 | C- | 15% | 7.5 |
| 6. 文档 | 55 | C- | 10% | 5.5 |
| 7. 集成 | 45 | D+ | 15% | 6.75 |
| **综合** | | **C+** | 100% | **64.05 ≈ 62** |

> 向下取整至 62，反映 CI 完全失效对整体质量保证体系的颠覆性影响。

### 7.2 与历史评估对比

| 项目 | 综合评分 | 等级 | 核心问题 |
|---|---|---|---|
| CarryMem v0.4.0 | 67 | C+ | :memory: 泄露 + 覆盖率门禁失效 + 3 幽灵功能 |
| OPC-Agents v0.3.0-beta | 62 | C+ | 加密 fallback 不一致 + 版本号未 bump + CI pipefail 掩盖失败 |
| OPC-Agents v0.3.0-beta P0 修复后 | 70 | B- | God Class 6250 行 + 2500 行死代码（P1/P2） |
| **PyCC2 v0.3.42** | **62** | **C+** | **CI 0% 成功率 + 1914 行幽灵代码 + 版本号/测试数失实** |

### 7.3 诚实性审计

Phase 1-7 质量冲刺的宣称存在**系统性虚报**：

| 宣称项 | 实测 | 虚报性质 |
|---|---|---|
| "mypy 0 errors" | 0（CI 命令验证） | ✅ 属实 |
| "2 ruff errors" | 22 | 严重低估（11 倍） |
| "12 文件 >1000 行" | 13 | 少计 1 个 |
| "全文档统一 v0.3.42" | __version__=0.3.41 + 11 份文档漂移 | 选择性陈述 |
| "CI 全绿" | 最近 10 次 0% 成功率 | 严重失实 |
| "4355 passed" | 2 benchmark + 3 e2e + 18 errors = 23 项失败/错误 | 不可执行 |
| "7 slow 测试" | **14**（6 sprite + 2 perf + 6 content_expansion） | ❌ 少计 7 个 |
| "Bandit 0 Medium/High" | 0/0 | ✅ 属实 |
| "Marker 100%" | 100%（4369/4369） | ✅ 属实 |

**虚报率**：9 项宣称中 6 项不实（66.7%），3 项属实。核心质量门禁（CI、ruff、文档一致性、测试数）均存在虚报。

### 7.4 P0/P1/P2 问题清单

#### P0（阻断发布，必须立即修复）

1. **CI 完全失效**：最近 10 次运行 0% 成功率，无法阻断回归进入 main。Test job 6h 超时被 GitHub 强制终止。
2. **代码版本号未同步**：`src/pycc2/__init__.py` 的 `__version__ = "0.3.41"` 与 `pyproject.toml` 的 `0.3.42` 不一致。运行时 `pycc2 --version` 报告错误版本。
3. **无依赖锁文件**：违反项目硬约束"必须包含依赖锁文件以确保构建可复现"。
4. **e2e/测试超时无保护**：未安装 `pytest-timeout` 启用、未设 `timeout-minutes`，`test_40_all_8_directions_prone_render`（>120s）等慢测试拖垮整个套件，CI 6h 超时。
5. **23 项测试失败/错误未修复**：2 benchmark + 3 e2e + 18 errors，全部因 `EnhancedRenderer` 重构（`_surface_pool` → `surface_pool_fn`、`_screen` setter 移除）未同步更新测试，CI 因 0% 成功率从未捕获。
6. **slow 测试标记遗漏**：`test_40_all_8_directions_prone_render` 做与 slow 测试相同的 8 方向精灵生成但未标 slow，Timeout (>120s) 拖垮 e2e 套件，是 CI 6h 超时元凶之一。

#### P1（严重，本周内修复）

7. **22 个 ruff 错误**：全部可 `ruff check --fix` 一键修复，但无人执行。CI Lint job 因此阻塞。
8. **--cov-fail-under 缺失**：CI 未传参（违反"CI必须显式传--cov-fail-under"硬教训），覆盖率下降无法阻断。
9. **5-7 个幽灵模块（1914+ 行死代码）**：ceasefire_retreat、enhanced_aar、battle_replay、reinforcement_evasion_bgm（纯幽灵）+ weapon_switch_system、airdrop_supply（半幽灵）。
10. **11+ 份文档版本漂移**：README_ja/INSTALL/USER_MANUAL/PRD/DESIGN/ROADMAP 等停留 v0.3.39~v0.3.41。
11. **README 引用不存在脚本**：`scripts/strict_e2e_journey.py` 作为快速开始示例，文件不存在。
12. **2 处命名冲突**：trench_digging（TrenchDiggingAI 双定义）、weather_effects（WeatherType 双 Enum）。
13. **release.yml 默认版本 0.3.41**：手动触发 release 会以错误版本发布。

#### P2（改进，迭代修复）

14. **13 个 God Class 文件 >1000 行**：cc2_authentic_weapons.py 1857、campaign_data.py 1457 等（2 个为数据文件不可拆，11 个可拆分）。
15. **13 项 vulture 死代码**：unused variable/import + redundant if-condition。
16. **过程文件残留**：根目录 IMAGE_OPTIMIZATION_COMPLETION_SUMMARY.md + docs/ 4 份执行报告 + 3 份重叠测试策略文档 + 21 个测试产物 PNG。
17. **docstring 覆盖率 75.4%**：1058 个公共定义缺 docstring（目标 80%）。
18. **.gitignore 缺 `.ruff_cache/`** + `.DS_Store` 重复条目。
19. **空目录入库**：`src/saves/saves/`、`src/pycc2/saves/campaign_saves`（应运行时创建）。
20. **README 测试数三处不一致**：badge 4298 / 正文 3985 / 实测 4369。
21. **CHANGELOG 缺 Phase 1-2 记录** + 出现 [0.3.42.1] 子版本。
22. **pip-audit/safety 未接入 CI**（docs 列为计划但未实现）。
23. **dependabot 配置简陋**（无 reviewers/labels/groups）。

### 7.5 发布判定

**推迟发布** ❌

理由：
1. CI 0% 成功率意味着所有质量门禁（mypy/ruff/bandit/pytest/coverage）均未实际执行，无法保证 main 分支质量。
2. 代码版本号错误（0.3.41 vs 0.3.42）会导致用户报告错误版本号，影响问题追踪。
3. 无依赖锁文件违反项目硬约束，构建不可复现。
4. 23 项测试失败/错误是真实 bug（EnhancedRenderer 重构遗漏），CI 从未捕获。
5. 质量冲刺宣称存在 66.7% 虚报率，需重新验证所有声称的指标。

### 7.6 下一步建议

#### 阶段1：P0 修复（1-2 天）
1. `ruff check --fix src/ tests/` 一键修复 25 个可自动修复错误
2. 修复 23 项测试失败/错误（`_surface_pool` → `surface_pool_fn` 适配 + `_screen` setter 恢复 + `test_i12_panel_has_all_sections` 断言修正 + `test_full_render_pipeline_no_crash` headless vsync 修复）
3. 给 `test_40_all_8_directions_prone_render` 添加 `@pytest.mark.slow` 标记
4. 安装 `pytest-timeout`，ci.yml 添加 `timeout-minutes: 30` + `pytest --timeout=300`
5. 修复 `__version__ = "0.3.42"` + 11 份文档版本同步
6. 生成 `requirements.lock`（`pip-compile` 或 `uv lock`）
7. 修复 `scripts/strict_e2e_journey.py` 引用（创建脚本或移除 README 示例）
8. CI 添加 `--cov-fail-under=70`

#### 阶段2：P1 改进（3-5 天）
1. 删除 4 个纯幽灵模块（-1679 行）+ 决定 2 个半幽灵模块去留
2. 修复 2 处命名冲突（trench_digging 重命名、weather_effects 合并 Enum）
3. 清理过程文件（根目录 1 个 + docs/ 4 份报告 + 3 份重叠测试策略 + 21 个 PNG）
4. 更新 README 测试数 + CHANGELOG 补 Phase 1-2 记录
5. release.yml 默认版本更新为 0.3.42

#### 阶段3：P2 工程化（5-7 天）
1. 拆分 11 个可拆分的 God Class 文件（优先 deployment_ui.py 1183L/70 方法和 tactic_executor.py 1175L/31 方法）
2. 清理 13 项 vulture 死代码
3. 提升 docstring 覆盖率至 80%（补 1058 个定义）
4. 接入 pip-audit 到 CI
5. 配置 dependabot reviewers/labels

**预期成果**：完成阶段1-3 后，综合成熟度预计可达 **80/100 (B)**，达到发布标准。

---

## 附录：证据索引

### 独立验证命令输出

```
# mypy (CI 命令)
$ MYPYPATH=src python -m mypy -p pycc2 --no-error-summary 2>&1 | grep -E "error:|Found .* error"
(no output — 0 errors)

# ruff
$ python -m ruff check src/pycc2 --statistics
8  I001    [*] unsorted-imports
7  UP037   [*] quoted-annotation
3  B010    [*] set-attr-with-constant
3  F401    [*] unused-import
1  UP035   [*] deprecated-import
Found 22 errors.

# ruff (src + tests, CI 范围)
$ python -m ruff check src/ tests/
Found 26 errors. [*] 25 fixable with --fix

# bandit
$ python -m bandit -r src/pycc2 -ll
Total issues: Low 369, Medium 0, High 0

# marker 覆盖
$ pytest -m "not unit and not integration and not e2e and not benchmark and not slow" --collect-only -q
no tests collected (4369 deselected)

# 回归测试
$ pytest tests/unit/ -m "not slow" --tb=no -q
3666 passed, 2 skipped, 12 deselected in 10.98s

$ pytest tests/integration/ tests/benchmark/ -m "not slow" --tb=no -q
2 failed, 155 passed, 2 deselected in 9.71s

# CI 历史
$ gh run list --limit 10
(全部 failure 或 in_progress，0% 成功率)

# 版本号
$ grep "__version__" src/pycc2/__init__.py
6:__version__ = "0.3.41"

# 依赖锁文件
$ ls *.lock poetry.lock uv.lock pdm.lock requirements*.txt
zsh: no matches found

# God Class
$ find src -name "*.py" -exec wc -l {} + | sort -rn | head -15
1857 cc2_authentic_weapons.py | 1457 campaign_data.py | ... | 1000 unit_diversity_expansion.py
(13 files >1000 lines)

# 幽灵功能
$ grep -rn "CeasefireSystem" src/pycc2 --include="*.py" | grep -v "ceasefire_retreat.py"
(0 命中 — 纯幽灵)
```

### 评估方法

- 3 个并行子代理独立采集（维度1+3 / 维度2+6 / 维度4+5）
- 主代理独立交叉验证争议项（mypy / ruff）
- 所有评分附实际命令输出作为证据
- 遵循"评审数据必须附实际命令输出以杜绝自评虚报"原则

---

> **评估结论**：PyCC2 v0.3.42 综合成熟度 62/100 (C+)，架构安全优秀但 CI/文档/可维护性严重欠债。Phase 1-7 质量冲刺宣称存在 66.7% 虚报率。**建议推迟发布**，完成 P0 修复（1-2 天）后重新评估。
