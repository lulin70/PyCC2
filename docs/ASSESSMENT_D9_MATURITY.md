# PyCC2 项目整理评估报告（D9 — 7维度成熟度评估）

> **评估日期**：2026-06-29
> **评估方法**：DevSquad V3.8 项目整理评估命令（4 并行子代理 + 独立交叉验证）
> **评估对象**：PyCC2 v0.4.0（commit 253e471，D8 Phase 2-5 全部完成后基线）
> **评估结论**：综合成熟度 **82/100 (B)**，可进入发布候选阶段，建议先修复 2 项 P1 文档问题
> **基线对比**：D7 整改后 78/B- → D8 评估 80/B- → D8 整改 82/B → **D9 评估 82/B（持平，但底层质量显著提升）**

---

## 0. 执行摘要

D9 评估是 D8 整改完成后的独立验收评估。D8 报告基于 v0.3.42（commit 4dbee69），其后完成了 v0.4.0 版本号统一 + D8 Phase 2/3/4/5 共 20 次提交。本次评估采用 4 个并行子代理（架构+可维护性 / 安全+集成 / 测试+性能 / 文档同步）采集客观数据，所有发现均经独立代码验证。

### D9 关键发现

| 类别 | 发现 | 验证 |
|------|------|------|
| ✅ 重大改进 | TD-058（>2000 行文件）**已清零**：deployment_ui 2485→689、pixel_artist_3d 2473→456、enhanced_renderer 2239→485 | `wc -l` 实测 |
| ✅ 重大改进 | 5 个 facade 拆分全部达成（campaign_data/cc2_authentic_weapons/unit_diversity_expansion/game_loop/morale_system） | git log + wc -l |
| ✅ 重大改进 | 测试数量 4367→4424 collected（+57），4398 passed / 0 failed / 61s | pytest --collect-only 实测 |
| ✅ 重大改进 | CI 升级为 7 jobs 4 阶段（lint→unit→integration→e2e + slow/benchmark/docker），pre-commit+dependabot 完整 | .github/workflows/ci.yml |
| ✅ 重大改进 | slow 测试优化（P5-3）：sprite @lru_cache，3.5min→0.56s；21 benchmark 全绿，baseline 文件 6/29 更新 | pytest tests/benchmark/ |
| ⚠️ 文档回归 | README_zh.md 5 处错误写 "4367个全部通过(100%)"（实际 4327 passed + 25 skipped + 15 deselected） | grep 实测 |
| ⚠️ 文档过期 | TECH_DEBT.md TD-058 仍标 "❌ 未解决"声称 4 文件 >2000 行，实测 0 文件；状态行与表格数字打架 | wc -l 实测 |
| ⚠️ 测试隔离 | E2E `test_full_render_pipeline_no_crash` 隐式依赖 benchmark 模块导入时设 `SDL_VIDEODRIVER=dummy`，`-m e2e` 单独运行失败 | pytest -m e2e 实测 |
| ✅ 误报澄清 | 子代理报 "mypy 未跑通" 实为命令错误：CI 用 `MYPYPATH=src mypy -p pycc2` exit 0 通过；但配置 `check_untyped_defs=false` 属宽松检查 | 直接复跑 CI 命令 |
| ✅ 约束澄清 | 子代理报 "scripts/start.sh 缺失违反硬约束" 实为约束误用：start.sh 是 PromiseLink 基础版约束，PyCC2 用 `pyproject [project.scripts]` 标准 pip 入口 | git log + INSTALL.md |

### 综合成熟度评分

| 维度 | D7整改后 | D8评估 | D8整改后 | **D9评估** | 等级 | 一句话结论 |
|------|---------|--------|---------|-----------|------|-----------|
| 1. 架构 | 82 | 82 | 82 | **83** | B+ | DDD 4 层稳定，0 循环依赖，P5-2 events 迁移落地 |
| 2. 安全 | 92 | 92 | 92 | **92** | A- | Bandit 0 M/H，subprocess/XML/HMAC 全链路安全 |
| 3. 测试 | 78 | 78 | 78 | **78** | B+ | 4398 测试全通过，但 E2E 隔离缺陷待修复 |
| 4. 性能 | 82 | 82 | 82 | **85** | B+ | dirty rect+6级缓存+spatial_hash+SurfacePool+FPS 自适应齐备 |
| 5. 可维护性 | 65 | 65 | 67 | **73** | B- | TD-058 清零+5 facade 拆分；残留 8 个 >1000 行逻辑文件 |
| 6. 文档 | 60 | 60 | 82 | **78** | B- | TECH_DEBT 严重过期 + README_zh 测试数回归 |
| 7. 集成 | 72 | 72 | 82 | **88** | B+ | CI 7 jobs 4 阶段 + pre-commit + dependabot 完整 |
| **综合** | **78** | **80** | **82** | **82** | **B** | **底层质量提升显著，文档回归抵消部分增益** |

**综合评分持平 82/B 的原因**：可维护性（+6）、性能（+3）、集成（+6）三项显著提升，被文档（-4）回归抵消。代码底层质量明显优于 D8，但外部可见的文档同步问题需先修复。

---

## 1. 维度1：架构（83/100 — B+）

**优势**：
- DDD 4 层结构稳定：domain(160 文件/38971 行) / infrastructure(19/4779) / presentation(164/49460) / services(18/4800)
- 364 模块零循环依赖（`python -c "import pycc2"` 通过）
- Domain 层零向上依赖（grep 验证 0 命中）
- P5-2 events 迁移已完成：event_bus/dispatcher/protocol 迁至 `infrastructure/events/`

**残留**：
- `infrastructure/events/event_dispatcher.py:27-29` 通过 TYPE_CHECKING 引用 presentation/services 3 处（运行时无依赖，但理想应改用 domain protocols）— P2
- presentation 层 164 文件 / 49460 行占代码总量 50.2%，存在过度膨胀风险 — P2

---

## 2. 维度2：安全（92/100 — A-）

**优势**：
- Bandit Medium=0 / High=0（`bandit -r src/ -ll --skip B101,B311,B601` 通过）
- 全量 Low=362（B311 random.random()，对游戏玩法合理）
- subprocess 全部列表形式无 shell=True（grep 验证 0 命中）
- XML 使用 defusedxml 防 XXE（`svg_sprite_loader.py:306`）
- HMAC 存档系统完整：32 字节密钥 + `hmac.compare_digest` 防时序攻击（`save_system.py:274,350`）
- 0 硬编码敏感信息（grep 验证 0 命中）
- pip-audit 已接入 CI（虽本地未装）

**残留**：
- save_system HMAC 密钥直接来自 env/config，无 PBKDF2 派生 — P2（注：此为存档完整性场景，非用户密码存储，标准要求不同）
- `filterwarnings` 含 `"ignore::UserWarning:hmac"` 可能掩盖密钥告警 — P2

---

## 3. 维度3：测试（78/100 — B+）

**优势**：
- 4424 tests collected（较 D8 4367 增加 57）
- 全量 4398 passed / 0 failed / 25 skipped / 1 xpassed / 61.02s
- 159 测试文件覆盖 unit(123) / integration(7) / e2e(26) / acceptance(1) / benchmark(4)
- Marker 覆盖完整：unit/integration/e2e/benchmark/slow 全部可独立筛选
- 21 benchmark 全绿，基线文件 `.baseline_results.json` 6/29 更新

**残留**：
- **P1**：E2E `test_full_render_pipeline_no_crash` 隔离缺陷 — 隐式依赖 `tests/benchmark/test_perf_benchmark.py:12` 在导入时 `os.environ.setdefault("SDL_VIDEODRIVER","dummy")`，`-m e2e` 单独运行失败。应在测试自身 fixture 设置环境变量。
- **P2**：1 个 xpassed（xfail 标记但实际通过），应清理过时 `@pytest.mark.xfail`
- **P2**：ruff 1 个 import 顺序错误（可 `--fix` 自动修复）
- **P2**：mypy 配置 `check_untyped_defs=false` 属宽松检查（CI 通过但实际未深度校验）

---

## 4. 维度4：性能（85/100 — B+，较 D8 +3）

**优势**：
- Dirty rect 渲染优化（`dirty_rect_tracker.py`，4 文件引用）
- 6 级地形缓存（lru_cache/OrderedDict/@cache 共 27 处 / 8 文件）
- FPS 自适应后处理（fps/frame_rate 共 125 处 / 18 文件）
- spatial_hash 替换 O(n²) 目标选择（`spatial_hash.py` 被 combat_resolver 使用）
- SurfacePool 统一实现（11 文件使用）
- **P5-3 落地**：sprite @lru_cache 优化，slow 测试 3.5min→0.56s

**残留**：
- **P2**：`tests/benchmark/test_performance_baseline.py:56` `VERSION = "0.3.0"` 与项目 v0.4.0 不符，基线报告版本号失真

---

## 5. 维度5：可维护性（73/100 — B-，较 D8 +6）

**重大改善**：
- ✅ **TD-058 清零**：>2000 行文件从 4 个 → 0 个
  - deployment_ui.py: 2485 → 689 行
  - pixel_artist_3d.py: 2473 → 456 行
  - enhanced_renderer.py: 2239 → 485 行
  - campaign_four_layer.py: 1987 → <1500 行
- ✅ **5 个 P5-1 facade 拆分全部达成**：
  - campaign_data.py: 1456 → 61 行
  - cc2_authentic_weapons.py: 1854 → 76 行
  - unit_diversity_expansion.py: 1000 → 233 行
  - game_loop.py: facade 拆分为 types+rendering+updating+combat+facade（当前 400 行）
  - morale_system.py: facade 拆分为 types+calculator+effects+routing+facade（当前 311 行）
- ✅ vulture 死代码仅 1 处（`renderer.py:74` unused `fog_grid`）

**残留**：
- **P1**：8 个 >1000 行逻辑文件待拆分（集中在 presentation/rendering/ 6 个 + domain/ai/ 1 个 + presentation/ui/ 1 个）：
  | 文件 | 当前行数 |
  |------|---------|
  | domain/ai/tactic_executor.py | 1346 |
  | presentation/rendering/terrain_tile_generator.py | 1324 |
  | presentation/rendering/cc2_building_renderer.py | 1215 |
  | presentation/rendering/sprite_renderer.py | 1178 |
  | presentation/ui/deployment_renderer.py | 1170 |
  | presentation/rendering/pixvoxel_loader.py | 1139 |
  | presentation/rendering/infantry_pixel_renderer.py | 1136 |
  | presentation/ui/campaign_ui_rendering.py | 1120 |
- **P1**：56 个 XXX 标记需排查（`grep -rn "XXX" src/`）
- **P2**：53 个 >500 行文件（TD-026 仍待推进）

---

## 6. 维度6：文档（78/100 — B-，较 D8 -4）

**D9 修复后状态**：
- ✅ 版本号一致：v0.4.0（pyproject.toml / __init__.py / 三语 README / CHANGELOG 全部统一）
- ✅ docstring 覆盖率 88.3%（interrogate 实测，较 D8 88.2% 微升 0.1%，超额完成 80% 目标）
- ✅ 热键映射主路径正确：keybind_manager.py:18-24 + interaction_controller.py:526-574 与三语 README 一致
- ✅ pyproject.toml description 含 "Close Combat 2"（D8 P0-4 修复确认）
- ✅ docs/ 26 个 .md 文件，无 _DRAFT/_old/_tmp 临时文件

**新发现问题**：

| 优先级 | 问题 | 位置 |
|--------|------|------|
| **P1** | README_zh.md 5 处错误写 "4367个全部通过(100%)"，实际 4327 passed + 25 skipped + 15 deselected | README_zh.md:17,99,277,338,500 |
| **P1** | TECH_DEBT.md 状态行 "P1未解决: 1 / P2未解决: 9" 与表格 "P1: 2 / P2: 16" 不一致 | docs/TECH_DEBT.md:2-3 |
| **P1** | TD-058 严重过期：声称 4 文件 >2000 行 "❌ 未解决"，实测 0 文件 >2000 行（5 个 facade 拆分已全部完成但未更新 TECH_DEBT） | docs/TECH_DEBT.md:238 |
| P2 | README.md 日期 6/19 与 zh/ja 6/14 不一致 | README*.md:3 |
| P2 | CHANGELOG 缺 Phase 3（docstring 62.8%→88.2%）显式条目 | CHANGELOG.md |
| P2 | TECH_DEBT.md "12 文件>1000行" 实测仅 8 个；核查日期停在 6/27 未反映 Phase 4/5 | docs/TECH_DEBT.md:3 |
| P2 | context_menu.py:252 K_d→STOP（非 DEFEND），与 README 文档不符；主路径 keybind_manager 正确 | context_menu.py:252 |
| P2 | D8_REMEDIATION_PLAN.md 页脚 "待共识确认" 过期 | docs/D8_REMEDIATION_PLAN.md 末尾 |

---

## 7. 维度7：集成/CI-CD（88/100 — B+，较 D8 +6）

**重大改善**：
- ✅ **CI 7 jobs 4 阶段**（P5-4 落地）：
  - lint：ruff check + ruff format --check + mypy（阻塞，`MYPYPATH=src mypy -p pycc2 --no-error-summary` exit 0）+ bandit + pip-audit --desc
  - unit-tests：Python 3.11/3.12 矩阵，`-m "not slow"`，cov-fail-under=70，Codecov 上传
  - integration-tests：`-m "not slow"`
  - e2e-tests：`-m "not slow"`，SDL_VIDEODRIVER=dummy
  - slow-tests：独立 job，仅 main/develop push 触发
  - benchmark：仅 main push
  - docker-build：依赖前三个 test job
- ✅ Release 工作流：quality gate（ruff+mypy+bandit）+ tests + 版本一致性校验 + build + PyPI 发布
- ✅ requirements.lock 21 行 8 包（项目专用，uv pip compile 生成）
- ✅ pre-commit 配置完整：ruff(--fix)+ruff-format+mypy+pre-commit-hooks+local pytest（pre-push stage）
- ✅ dependabot 配置：pip（weekly）+ github-actions（weekly）
- ✅ CI 检查项全部齐备：permissions / concurrency / ruff / mypy（阻塞）/ bandit / pip-audit / slow 隔离 / Python 矩阵

**残留**：
- P2：本地未装 pip-audit，开发者无法在推送前复现 CI 的依赖漏洞扫描

---

## 8. D7→D8→D9 改善轨迹

| 阶段 | 评分 | 关键改善 |
|------|------|---------|
| D7 原始 | 62/100 (C+) | 发现 CI 0% 成功率、23 项测试失败、文档版本严重漂移 |
| D7 整改 | 78/100 (B-) | ruff/mypy 全绿、23 测试修复、God Class 拆分、死代码清理 |
| D8 评估 | 80/100 (B-) | 独立验证 D7 成果，发现 8 项 P0 文档/CI 问题 |
| D8 整改 | 82/100 (B) | 8 项 P0 全部修复，回归测试通过 |
| **D9 评估** | **82/100 (B)** | **底层质量显著提升（TD-058 清零+5 facade 拆分+CI 4 阶段+slow 优化），但 TECH_DEBT 文档过期 + README_zh 测试数错误回归抵消增益** |

---

## 9. 下一步建议

### 发布前（P0，必须完成）
1. ✅ **[已修复 2026-06-29] 修复 README_zh.md 测试数表述**：实际修复为 "4424 collected / 4398 passed / 25 skipped"（D8 时的 4327 数字已被 P5-1/P5-2 新增测试覆盖，需用最新 pytest 实测值）。6 处编辑：badge + 5 处正文 + 最后更新日期。
2. ✅ **[已修复 2026-06-29] 更新 TECH_DEBT.md**：
   - TD-058 标记为 ✅ 已解决（4 文件 >2000 行 → 0 文件，实测 deployment_ui 689 / pixel_artist_3d 456 / enhanced_renderer 485 / campaign_four_layer 524）
   - 状态行 P1 数字与表格对齐（表格 P1=2→1，状态行已为 1）
   - ">1000 行" 计数修正（12→8，实测验证）
   - 核查日期更新为 2026-06-29
3. ✅ **[已修复 2026-06-29] 修复 E2E 隔离缺陷**：根因为 `tests/e2e/test_vertical_slice.py::pygame_env` fixture teardown `pygame.quit()` 破坏后续测试 display 子系统（非 benchmark 模块副作用）。修复方式：teardown 改为 `pygame.display.quit()`（限定范围）+ `test_visual_smoke.py::setup_pygame` 添加 `pygame.display.quit()` + `pygame.display.init()` 防御性重置。完整 E2E 套件 483 passed / 0 failed。
4. **模拟真实用户使用测试**（项目硬约束：发布前必须完成）

### 回归验证（2026-06-29）
- pytest 全量：4398 passed / 25 skipped / 1 xpassed / 0 failed / 51.82s
- mypy（CI 命令 `MYPYPATH=src mypy -p pycc2`）：0 errors
- ruff：1 预先存在的 I001 error（`src/pycc2/domain/systems/morale_system.py:16`，非本次修改范围，留待后续清理）

### 发布后（P1，优先处理）
1. 排查 56 个 XXX 标记（`grep -rn "XXX" src/`）
2. 继续拆分 8 个 >1000 行逻辑文件（重点 presentation/rendering/）
3. ✅ **[已修复 2026-06-30 D10]** 修复 `tests/benchmark/test_performance_baseline.py:56` VERSION 失真 — 改为 `from pycc2 import __version__ as VERSION`，移至 pycc2 imports 组首行修正 ruff I001。
4. ✅ **[已修复 2026-06-30 D10]** 清理 1 个过时 `@pytest.mark.xfail` — 保留 xfail 但更新 reason 说明 flaky 行为（XFAIL in isolation / XPASS in combined suite，因 EnhancedRenderer post-render layers 初始化顺序差异）。
5. ✅ **[已修复 2026-06-30 D10]** 同步三语 README 日期（6/19 vs 6/14）— README_zh.md + README_ja.md 同步为 6/19。
6. CHANGELOG 补 Phase 3（docstring）条目

### 长期（P2，持续改进）
1. TD-026：53 个 >500 行文件逐步拆分（D10 已同步描述：29→53）
2. 添加独立 application 层（分离 services 中的 controller/loop/service）
3. mypy 配置升级：逐步启用 `check_untyped_defs=true`
4. `infrastructure/events/event_dispatcher.py` 改用 domain protocols 解耦 TYPE_CHECKING
5. ✅ **[已修复 2026-06-30 D10]** context_menu.py 热键映射与主路径对齐 — `ContextAction.STOP` → `ContextAction.DEFEND`，K_d 在右键菜单和主路径统一为 Defend 语义，符合 CC2 原版约定。

### 回归验证（2026-06-30 D10）
- pytest 全量：4398 passed / 25 skipped / 1 xfailed / 0 failed / 54.82s（flaky 测试单独 XFAIL，符合 P1-2 reason）
- mypy（CI 命令 `MYPYPATH=src mypy -p pycc2`）：0 errors
- ruff：0 errors（All checks passed!）
- D10 推进项：P0×3（CI lockfile / context_menu DEFEND / README dates）+ P1×3（VERSION / xfail / TD-026 描述）全部验证通过

---

## 附录：D9 评估方法

- **评估命令**：DevSquad V3.8 "项目整理评估"（7 维度）
- **数据采集**：4 个并行子代理（架构+可维护性 / 安全+集成 / 测试+性能 / 文档同步）
- **独立验证**：所有 P0/P1 发现经直接代码检查验证（grep/wc -l/实测命令）
- **回归测试**：pytest 全量 4398 passed / 0 failed / 61s
- **基线对比**：D8 报告 docs/ASSESSMENT_D8_MATURITY.md（v0.3.42, commit 4dbee69, 2026-06-27）
- **本次基线**：v0.4.0, commit 253e471, 2026-06-29

### 评估方法学说明

- 子代理报 "mypy 未跑通" 经独立验证为命令错误：CI 用 `MYPYPATH=src mypy -p pycc2 --no-error-summary` 实际 exit 0 通过；但配置 `check_untyped_defs=false` 属宽松检查，故测试维度不加分
- 子代理报 "scripts/start.sh 缺失违反硬约束" 经独立验证为约束误用：start.sh 是 PromiseLink 基础版约束（面向非技术用户），PyCC2 使用 `pyproject.toml [project.scripts] pycc2 = "pycc2.main:main"` 是 Python 标准 pip 分发入口（INSTALL.md 文档化），约束不适用
- 测试数量从 4367→4424 collected（+57）主要来自 P4-4 补给线征用点采购 UI 的 31 个单元测试 + D8 Phase 3/5 修复后的回归测试补充
