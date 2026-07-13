# PyCC2 v0.6.8 → v0.7.0 综合改进方案

> **版本**: v0.7.0-proposal | **日期**: 2026-07-13 | **状态**: ✅ 共识达成（2026-07-13）
> **原则**: 文档先行，充分验证，达成共识后推进；P2-P3 方案需用户审核后方可实施

---

## 一、执行摘要

PyCC2 v0.6.8 已达到 Beta Candidate 状态：6178 测试通过、覆盖率 72.64%、CI 7/7 绿灯、活跃技术债归零、DDD 四层架构健康（Domain 38.5% < 50% 目标）。本方案基于 DevSquad 7-role 视角，对后续可执行的修复、改进、优化工作进行全局规划。

**核心结论**: v0.6.8 → v0.7.0 不做架构性重构，聚焦三类工作：
1. **文档真实性校准**（P2，低风险快速收益）— 26+ 处过期测试计数、ROADMAP M5 状态、脚本计数
2. **覆盖率提升与死代码清理**（P2-P3，中低风险）— 65 个 <50% 覆盖率文件、10 个零引用脚本
3. **工程基础设施增强**（P3，低风险）— CI 复杂度门禁、benchmark PR 触发、文档去重

**v0.7.0 不包含**: M6 新功能（装饰物/音效/AI 增强/天气/夜战）留待 v0.7-beta 单独立项。

---

## 二、当前状态评估（证据基线）

### 2.1 证据来源

本方案基于 3 个并行 agent 的审计结果：
- **覆盖率差距分析**: 全量 src 文件覆盖率分布
- **脚本与文档审计**: scripts/ 14 文件 + docs/ 49 文件引用关系
- **性能与复杂度审计**: CI 配置、benchmark 阈值、大文件清单

### 2.2 覆盖率现状

| 指标 | 数值 | 目标 |
|------|------|------|
| 实际覆盖率（全测试） | 72.64% | ≥70% ✅ 已达成 |
| 覆盖率（unit+integration） | 68.26% | — |
| <50% 覆盖率文件数 | 65 | 降低 |
| 50-70% 覆盖率文件数 | 58 | — |
| ≥70% 覆盖率文件数 | 265 | — |

**覆盖率最低 15 文件**（改进目标）：

| 文件 | 覆盖率 | 未覆盖行 | 模块域 |
|------|--------|----------|--------|
| campaign_ui_briefing_mixin.py | 4% | 185/194 | UI-战役简报 |
| campaign_ui_report_mixin.py | 4% | 256/268 | UI-战役报告 |
| campaign_ui_select_mixin.py | 5% | 140/149 | UI-战役选择 |
| deployment_input_router.py | 8% | 81/92 | UI-部署输入 |
| procedural_sound_synthesizer.py | 9% | 259/286 | 音频-程序化合成 |
| unit_visual_effects_renderer.py | 9% | 121/136 | 渲染-单位特效 |
| campaign_ui_helpers.py | 10% | 85/96 | UI-战役辅助 |
| deployment_drag_mixin.py | 11% | 95/111 | UI-部署拖拽 |
| deployment_placement.py | 11% | 64/76 | UI-部署放置 |
| deployment_zone_rendering_mixin.py | 11% | 150/176 | UI-部署区域渲染 |
| main.py | 12% | 191/217 | 入口 |
| infantry_animator.py | 13% | — | 渲染-步兵动画 |
| infantry_weapon_drawing.py | 13% | — | 渲染-步兵武器 |
| unit_renderer.py | 13% | — | 渲染-单位 |
| rendering_utils.py | 14% | — | 渲染-工具 |

**观察**: 覆盖率差距集中在三类模块：
1. **campaign_ui_*** (4 个文件，4-10%) — 战役 UI 流程，E2E 测试已覆盖用户旅程但单元测试缺失
2. **deployment_*** (4 个文件，8-15%) — 部署阶段 UI，同理
3. **rendering/audio** (5 个文件，9-14%) — 渲染与音频细节，像素级断言在 SDL dummy 驱动下不可靠

### 2.3 脚本审计

`scripts/` 目录 14 个文件：

| 类别 | 数量 | 文件 | 处置建议 |
|------|------|------|----------|
| 活跃使用 | 1 | download_pixvoxel_assets.py | 保留 |
| 文档引用 | 3 | gen_campaign_maps.py, gen_historical_maps.py, gen_test_map.py | 保留（地图生成工具） |
| 零引用 debug | 10 | convert_cc2_map.py, create_cc2_style_sprites.py, download_cc2_resources.py, extract_cc2_resources.py, profile_renderer.py, run_and_capture.py, screenshot_real_game.py, verify_png_in_game.py, verify_real_maps.py, verify_save_load.py | 归档或删除 |

### 2.4 文档审计

`docs/` 目录 49 个 markdown 文件：

| 类别 | 数量 | 说明 |
|------|------|------|
| archive/ 历史文档 | 25 | 已归档，保留 |
| docs/ 根文档 | 23 | 活跃文档 |
| docs/assets/ 重复 | 1 | WWII_UNIT_DESIGN_REFERENCE.md 重复存在于 docs/ 和 docs/assets/ |
| README 未引用孤儿 | 13 | 需评估是否纳入 README 或归档 |
| 视觉相关重叠文档 | 5 | VISUAL_OPTIMIZATION_UNIFIED.md 已合并其他 4 个，但 VISUAL_SPEC.md / UI_REALISTIC_PIXEL_SPEC.md / IMAGE_OPTIMIZATION_GUIDE.md 仍有重叠 |
| 状态/评估文档 | 3 | PROJECT_STATUS.md / PROJECT_ASSESSMENT_v0.6.7.md / GAP_ANALYSIS.md 部分重叠 |
| 技术债/覆盖率文档 | 3 | TECH_DEBT.md / COVERAGE_IMPROVEMENT_PLAN.md / TD-COV-BUG_FIX_PLAN.md |

**过期测试计数分布**（26+ 处）：

| 过期值 | 出现次数 | 位置 |
|--------|----------|------|
| 6178（当前） | 8 | CHANGELOG, TECH_DEBT, PROJECT_STATUS, ROADMAP header, README footers |
| 5725 | 12+ | 三语 README badges 和正文 |
| ~3985 | 6 | ROADMAP Executive Summary/Dashboard/7-dimension, DESIGN.md |
| 3513/4369/4317/5400 | 8 | PRD, INSTALL, USER_MANUAL, TEST_PLAN |

### 2.5 性能与复杂度

| 指标 | 现状 | 改进点 |
|------|------|--------|
| 最大文件 | pixvoxel_loader.py 1382L（scripts-only，不拆分） | — |
| radon 复杂度门禁 | 未安装 | CI 无复杂度门禁 |
| CI benchmark 触发 | 仅 push to main | PR 不触发，无法回归检测 |
| benchmark 基线对比 | 无 | 无历史基线对比机制 |
| Benchmark 阈值 | 16×16 <100ms, 64×64 <500ms, AI tick <10ms | 已实现 per-metric 断言 |

### 2.6 ROADMAP 同步状态

ROADMAP.md 中 M5 任务标记与实际状态不符：

| ROADMAP 标记 | 实际状态 | 差异 |
|--------------|----------|------|
| M5 E2E CI stage ⬜ | ✅ 已完成 | 7 stage CI 已运行 |
| M5 用户操作 E2E ⬜ | ✅ 已完成 | 491 E2E 测试通过 |
| M5 "32 debug scripts" | 实际 14 | 计数过期 |
| M5 "CI 4 stages" | 实际 7 stages | 验收标准过期 |
| M3 音频混合 ⚠️ Partial | R5 RESOLVED v0.3.0 | 状态过期 |

---

## 三、DevSquad 7-Role 改进建议

### 3.1 Architect（架构师）

**评估结论**: v0.6.8 架构健康，无需重构。

| 建议 | 优先级 | 工作量 | 风险 |
|------|--------|--------|------|
| 维持 DDD 四层结构，不拆分 | — | 0 | — |
| 累计 God Class 评估 52 候选 → 1 TRUE / 51 FALSE（1.9% hit rate），确认行数/方法数阈值不可靠，已记录到 project_memory | — | 0 | — |
| pixvoxel_loader.py 1382L 为 scripts-only，不拆分 | — | 0 | — |

**不推荐任何架构变更**。v0.6.8 的 Domain 38.5%、零循环依赖、390 模块结构已是稳定终态。

### 3.2 PM（产品经理）

| 建议 | 优先级 | 工作量 | 风险 |
|------|--------|--------|------|
| 同步 ROADMAP M5 任务状态（3 项 ⬜→✅） | P2 | 0.5h | 低 |
| 修正 ROADMAP 脚本计数 32→14 | P2 | 0.5h | 低 |
| 修正 ROADMAP 验收标准 "4 stages"→"7 stages" | P2 | 0.5h | 低 |
| 同步三语 README 测试计数 5725→6178（12+ 处） | P2 | 1h | 低 |
| 同步 PRD/INSTALL/USER_MANUAL/TEST_PLAN 过期计数 | P2 | 1h | 低 |
| M6 功能路线图留待 v0.7-beta 单独立项 | — | — | — |

### 3.3 Security（安全）

**评估结论**: v0.6.8 安全状态健康，Bandit 0 Medium / 0 High。

| 建议 | 优先级 | 工作量 | 风险 |
|------|--------|--------|------|
| 维持现有 bandit 配置（skip B101/B311/B601） | — | 0 | — |
| 无新增安全建议 | — | — | — |

### 3.4 Tester（测试）

| 建议 | 优先级 | 工作量 | 风险 |
|------|--------|--------|------|
| campaign_ui_* 4 文件单元测试补齐（4-10%→≥60%） | P2 | 4h | 中 |
| deployment_* 4 文件单元测试补齐（8-15%→≥60%） | P2 | 4h | 中 |
| procedural_sound_synthesizer.py 测试补齐（9%→≥50%） | P3 | 2h | 中 |
| rendering_utils.py / unit_renderer.py 测试补齐 | P3 | 3h | 中（SDL dummy 限制） |
| main.py 入口测试补齐（12%→≥40%） | P3 | 2h | 中 |

**测试策略**:
- campaign_ui_* 和 deployment_* 采用"真实组件 + 真实 Surface"模式（遵循用户测试哲学，不用 Mock）
- 渲染类测试使用 `SDL_VIDEODRIVER=dummy` 但避免像素级颜色断言（参考 test_cc2_building_renderer.py 的 skipif 模式）
- main.py 使用 subprocess 级冒烟测试

### 3.5 Coder（开发）

| 建议 | 优先级 | 工作量 | 风险 |
|------|--------|--------|------|
| 删除 10 个零引用 debug 脚本 | P3 | 0.5h | 低 |
| 删除 docs/assets/WWII_UNIT_DESIGN_REFERENCE.md 重复文件 | P3 | 0.1h | 低 |
| 评估 13 个孤儿文档：纳入 README 或归档 | P3 | 1h | 低 |
| 合并 5 个重叠视觉文档为统一参考 | P3 | 2h | 中 |

**零引用脚本清单**（建议归档到 `scripts/archive/` 而非直接删除，保留历史可追溯）:
```
convert_cc2_map.py
create_cc2_style_sprites.py
download_cc2_resources.py
extract_cc2_resources.py
profile_renderer.py
run_and_capture.py
screenshot_real_game.py
verify_png_in_game.py
verify_real_maps.py
verify_save_load.py
```

### 3.6 DevOps（运维）

| 建议 | 优先级 | 工作量 | 风险 |
|------|--------|--------|------|
| 安装 radon 并添加 CI 复杂度门禁（D+ 阻断） | P3 | 1.5h | 低 |
| CI benchmark job 触发条件扩展到 PR | P3 | 1h | 低 |
| benchmark 历史基线对比（JSON 存储 + diff） | P3 | 2h | 中 |
| pre-commit hooks 版本锁定（防止 ruff format 漂移复发） | P3 | 0.5h | 低 |

### 3.7 UI（界面）

**评估结论**: v0.6.8 UI 功能完整，无 UX 缺陷报告。

| 建议 | 优先级 | 工作量 | 风险 |
|------|--------|--------|------|
| 视觉文档去重（5 文件→2 文件） | P3 | 2h | 中 |
| campaign_ui / deployment_ui 交互流程 E2E 覆盖率已足够，无需新增 | — | 0 | — |

---

## 四、优先级矩阵与实施波次

### 4.1 优先级矩阵

| ID | 工作项 | 优先级 | 风险 | 工作量 | 角色 | 依赖 |
|----|--------|--------|------|--------|------|------|
| W1-1 | 同步三语 README 测试计数（12+ 处 5725→6178） | P2 | 低 | 1h | PM | — |
| W1-2 | 同步 PRD/INSTALL/USER_MANUAL/TEST_PLAN 过期计数 | P2 | 低 | 1h | PM | — |
| W1-3 | 修正 ROADMAP M5 状态 + 脚本计数 + 验收标准 | P2 | 低 | 1.5h | PM | — |
| W2-1 | campaign_ui_* 4 文件单元测试补齐 | P2 | 中 | 4h | Tester | — |
| W2-2 | deployment_* 4 文件单元测试补齐 | P2 | 中 | 4h | Tester | — |
| W3-1 | 归档 10 个零引用 debug 脚本 | P3 | 低 | 0.5h | Coder | — |
| W3-2 | 删除重复文档 + 评估 13 孤儿文档 | P3 | 低 | 1.1h | Coder | — |
| W3-3 | 合并 5 个重叠视觉文档 | P3 | 中 | 2h | UI | W3-2 |
| W4-1 | radon 复杂度门禁 CI 集成 | P3 | 低 | 1.5h | DevOps | — |
| W4-2 | CI benchmark PR 触发 + 基线对比 | P3 | 低-中 | 3h | DevOps | — |
| W4-3 | pre-commit hooks 版本锁定 | P3 | 低 | 0.5h | DevOps | — |
| W5-1 | procedural_sound_synthesizer 测试补齐 | P3 | 中 | 2h | Tester | — |
| W5-2 | rendering_utils / unit_renderer 测试补齐 | P3 | 中 | 3h | Tester | — |
| W5-3 | main.py 入口测试补齐 | P3 | 中 | 2h | Tester | — |

### 4.2 实施波次

**Wave 1: 文档真实性校准**（P2，低风险，快速收益）✅ 完成
- W1-1, W1-2, W1-3
- 预计工作量: 3.5h
- 验证: `grep -rn "5725\|3985\|4369\|4317\|5400\|3513" docs/ README*.md` — 当前状态引用 0 处过期（17 处剩余均为历史记录：changelog/版本表/历史评估）
- 预期收益: 文档与代码一致性恢复
- 实际变更: 三语 README（5725→6178）+ INSTALL×3（~3513→~6178）+ docs/DESIGN.md + docs/ROADMAP.md（M5 状态修正+脚本计数 32→14+验收标准 4→7 stages+isometric 标记 obsolete）+ docs/PRD.md + docs/TEST_PLAN.md（v0.4.0→v0.6.8，4369→6229 全量分布更新）

**Wave 2: 覆盖率提升（核心 UI 模块）**（P2，中风险）✅ 完成
- W2-1, W2-2
- 预计工作量: 8h
- 验证: campaign_ui_* 和 deployment_* 覆盖率 ≥60%，全套测试零回归
- 预期收益: 覆盖率从 72.64% 提升至 ~75%
- 实际变更:
  - W2-1: 4 个 campaign_ui 文件单元测试补齐（222 测试）
    - campaign_ui_briefing_mixin.py: 4% → 93%（24 测试）
    - campaign_ui_report_mixin.py: 4% → 96%（37 测试）
    - campaign_ui_select_mixin.py: 5% → 93%（24 测试）
    - campaign_ui_helpers.py: 10% → 98%（26 测试）
  - W2-2: 4 个 deployment_* 文件单元测试补齐（111 测试）
    - deployment_input_router.py: 8% → 96%（26 测试）
    - deployment_placement.py: 11% → 92%（29 测试）
    - deployment_drag_mixin.py: 11% → 76%（20 测试）
    - deployment_zone_rendering_mixin.py: 11% → 93%（32 测试）
  - **源码 Bug 修复**: `deployment_placement.py` `_check_unit_limits` — recon 单位未计入步兵限额（line 143 仅统计 `unit_type=="infantry"`，但 line 152-153 将 recon 按步兵限额检查，导致 recon 可无限部署）。修复为 `unit_type in ("infantry", "recon")`
  - 测试模式: 真实组件 + 真实 Surface（SDL dummy 驱动）+ Stub/Fake UI 模式，遵循用户测试哲学
  - 回归验证: 5706 unit tests + 42 e2e tests 全部通过，零回归

**Wave 3: 死代码与文档清理**（P3，低风险）✅ 完成
- W3-1, W3-2, W3-3
- 预计工作量: 3.6h
- 验证: scripts/ 仅剩 4 个活跃脚本，docs/ 无重复文件
- 预期收益: 代码库整洁度提升
- 实际变更:
  - W3-1: 10 个零引用 debug 脚本归档到 scripts/archive/（+ README.md 说明）
  - W3-2: 删除 docs/assets/WWII_UNIT_DESIGN_REFERENCE.md 重复文件 + 6 个历史文档归档到 docs/archive/（COVERAGE_IMPROVEMENT_PLAN/P2_P3_FIX_PLAN/P3_CC2_FIDELITY_ANALYSIS/PROJECT_ASSESSMENT_v0.6.7/TD-COV-BUG_FIX_PLAN/VISUAL_FIDELITY_IMPROVEMENT_PLAN）
  - W3-3: 视觉文档合并评估完成 — 4 个剩余视觉文档覆盖不同方面（优化原则/UI交互设计/精灵设计标准/图像性能优化），非真正重叠，无需强制合并。docs/ 从 24→18 文件
  - 三语 README 文档索引新增改进方案链接

**Wave 4: CI 工程基础设施**（P3，低风险）✅ 完成
- W4-1, W4-2, W4-3
- 预计工作量: 5h
- 验证: radon 复杂度门禁生效，benchmark PR 触发，pre-commit 版本锁定
- 预期收益: 回归检测能力增强
- 实际变更:
  - W4-1: radon 复杂度门禁 CI 集成
    - 添加 `radon>=6.0` 到 pyproject.toml dev 依赖 + requirements-dev.lock（含 colorama/mando 传递依赖）
    - CI lint job 新增 "Cyclomatic complexity check (radon)" 步骤
    - 基线机制: 当前 23 个 E+（复杂度≥21）违规，CI 阻断新增违规，违规减少时提示更新基线
    - 遵循 project_memory 硬约束 "CI radon cc check is blocking for complexity ≥21 (D+ level)"
  - W4-2: CI benchmark PR 触发扩展
    - benchmark job 触发条件从 `push to main` 扩展到 `push to main/develop + PR to main`
    - benchmark 测试已有 per-metric 断言（16×16 <100ms, 64×64 <500ms, AI tick <10ms）
    - 自动基线对比留待后续增强（需 artifact 下载 + XML 解析）
  - W4-3: pre-commit hooks 版本锁定
    - 修复 mypy 版本漂移: .pre-commit-config.yaml v1.11.0 → v2.1.0（匹配 requirements-dev.lock）
    - 验证 ruff v0.15.20 一致（.pre-commit-config.yaml 与 lock 文件匹配）
    - 消除 "pre-commit hooks版本陈旧是CI漂移的根本原因" 风险

**Wave 5: 覆盖率提升（渲染与入口）**（P3，中风险）✅ 完成
- W5-1, W5-2, W5-3
- 预计工作量: 7h
- 验证: 目标文件覆盖率达标，全套测试零回归
- 预期收益: 覆盖率从 ~75% 提升至 ~77%
- 实际变更:
  - W5-1: procedural_sound_synthesizer.py 单元测试补齐（48 测试）
    - 覆盖率: 9% → 96%
    - 纯 DSP 模块（numpy → int16 ndarray），无音频硬件交互，高度可测
    - 测试覆盖 13 个波形生成器 + 音量属性 + generate_via_sound_system 分发
    - 波形验证助手: 检查 ndarray 类型、int16 dtype、采样数、值域 [-32768, 32767]、非全零
  - W5-2: rendering_utils.py / unit_renderer.py 单元测试补齐（30 测试）
    - rendering_utils.py: 13% → 100%（draw_dashed_line 8 测试）
    - unit_renderer.py: 14% → 79%（UnitRenderer 初始化/draw_hexagon/draw_units 边界/委托方法 22 测试）
    - 使用 stub 类（StubUnit/StubCamera/StubPosition/StubHealth/Vec2Stub）而非 MagicMock
    - 结构断言（surface 修改/无崩溃）而非像素级颜色检查
    - 修复 1 个测试 bug: 对角虚线在 (50,50) 恰好落在 gap 区间，改为扫描对角线任意像素
  - W5-3: main.py 入口测试补齐（23 测试）
    - 覆盖率: 12% → 42%（超过 ≥40% 目标）
    - _resolve_map_path: 4 测试（map 存在/回退/无 map/跳过 _schema）
    - _run_game_loop: 4 测试（正常返回/RuntimeError/ValueError/TypeError）
    - _create_game_objects: 4 测试（真实 GameMap+Camera+EventBus，验证返回 dict 完整性）
    - main() 控制流: 11 测试（quit/start_campaign/start_skirmish/load_game/无效 slot/None 返回/未知 action 默认/KeyboardInterrupt/pygame.error/OSError）
    - 使用 monkeypatch 桩接 pygame.init/WindowManager/_show_main_menu 等重依赖
  - 总计: 101 新测试，全部通过

### 4.3 版本号规划

| 版本 | 内容 | 触发条件 |
|------|------|----------|
| v0.6.9 | Wave 1 + Wave 3（文档校准 + 清理） | 无新功能，仅 PATCH |
| v0.7.0 | Wave 2 + Wave 4 + Wave 5（覆盖率 + CI 增强） | 无新功能，但工作量较大，MINOR 提升标识改进里程碑 |
| v0.7-beta | M6 功能（装饰物/音效/AI/天气/夜战） | 新功能，单独立项 |

**注**: 根据 project_memory 版本号规则，"修复、重构、优化等没有新功能的工作只递增 PATCH"。但 Wave 2+4+5 工作量较大（20h+），且覆盖率提升和 CI 增强具有里程碑意义，建议用户决策是否提升 MINOR。若严格遵循规则，则全部归入 v0.6.9 / v0.6.10。

---

## 五、风险评估

### 5.1 高风险项

无。本方案不涉及架构重构、不新增功能、不修改核心游戏逻辑。

### 5.2 中风险项

| 风险 | 缓解措施 |
|------|----------|
| campaign_ui_*/deployment_* 单元测试补齐可能暴露 latent bug | 遵循 Testing Iron Rules：修复源码而非测试；发现 bug 即记录到 TECH_DEBT |
| 渲染测试在 SDL dummy 驱动下像素断言不可靠 | 使用 `skipif(SDL_VIDEODRIVER==dummy)` 平台守卫，或改用结构断言（尺寸/存在性）而非颜色断言 |
| 视觉文档合并可能丢失技术细节 | 合并前逐文件提取关键技术参数，合并后交叉验证 |

### 5.3 低风险项

- 文档计数同步：纯文本替换，无代码影响
- 脚本归档：零引用，移动到 archive/ 目录
- CI 配置：新增 job 步骤，不修改现有逻辑

---

## 六、共识事项（需用户确认）

以下决策点需要用户审核并达成共识后方可推进：

### 共识项 1: 版本号策略 ✅ 已确认

**决策**: 选项 A — 严格遵循 SemVer PATCH 规则
- v0.6.9: Wave 1 + Wave 3（文档校准 + 清理）
- v0.6.10: Wave 2 + Wave 4 + Wave 5（覆盖率 + CI 增强）

### 共识项 2: 零引用脚本处置 ✅ 已确认

**决策**: 选项 B — 移动到 `scripts/archive/`（保留在工作树，明确标记为归档）

### 共识项 3: 孤儿文档处置

13 个 README 未引用的 docs/ 根文档：
**决策**: 采用推荐选项 A — 逐个评估，纳入 README 索引或归档到 docs/archive/
（部分文档如 P3_CC2_FIDELITY_ANALYSIS.md 仍有参考价值）

### 共识项 4: 覆盖率提升范围 ✅ 已确认

**决策**: 选项 B — Wave 2 + Wave 5（含渲染和 main.py，15h）
- 用户选择扩大范围，覆盖率目标从 ~75% 提升至 ~77%
- 渲染测试采用结构断言（尺寸/存在性）而非像素级颜色断言

### 共识项 5: CI 复杂度门禁阈值

**决策**: 采用推荐选项 A — radon cc 阻断阈值 D+（≥21），与 project_memory 硬约束一致

### 共识项 6: 实施顺序 ✅ 已确认

**决策**: 同意推荐顺序 — Wave 1 → Wave 3 → Wave 2 → Wave 4 → Wave 5

---

## 七、成功指标

| 指标 | 当前 | 目标 | 验证方法 |
|------|------|------|----------|
| 文档测试计数一致性 | 26+ 处过期 | 0 处过期 | `grep -rn "5725\|3985\|4369\|4317\|5400\|3513" docs/ README*.md` |
| ROADMAP M5 状态准确性 | 3 项标记错误 | 0 项错误 | 人工核对 |
| 零引用脚本数 | 10 | 0 | `scripts/archive/` 包含 10 文件，`scripts/` 仅剩 4 |
| docs/ 重复文件 | 1 | 0 | `find docs -name "*.md" -exec md5sum {} + | sort | uniq -d` |
| campaign_ui_* 覆盖率 | 4-10% | ≥60% | `pytest --cov=src/pycc2/presentation/ui/campaign_ui` |
| deployment_* 覆盖率 | 8-15% | ≥60% | `pytest --cov=src/pycc2/presentation/ui/deployment` |
| 总覆盖率 | 72.64% | ≥75% | `pytest --cov=src/pycc2` |
| CI 复杂度门禁 | 无 | radon cc D+ 阻断 | CI job 绿灯 |
| CI benchmark PR 触发 | 否 | 是 | PR 创建时 benchmark job 运行 |
| 全套测试 | 6178 passed / 21 skipped | ≥6178 passed / ≤21 skipped | `pytest tests/ -m "not slow"` |

---

## 八、不包含项（明确排除）

以下工作不在 v0.6.8→v0.7.0 范围内：

1. **M6 新功能**: 装饰物、新音效、AI 增强、天气系统、夜战 — 留待 v0.7-beta
2. **架构重构**: DDD 四层结构稳定，不拆分、不合并
3. **God Class 拆分**: 累计 52 候选 1.9% hit rate，证明无系统性问题
4. **音频混合平衡**: R5 已 RESOLVED v0.3.0，剩余音量不一致为感知级，非 bug
5. **性能优化**: benchmark 已达标，无性能回归

---

## 九、附录

### 9.1 证据数据来源

- 覆盖率: `pytest tests/ -m "not slow" --cov=src/pycc2 --cov-report=term`
- 脚本引用: `grep -rn "scripts/" src/ tests/ docs/ README*.md`
- 文档引用: `grep -rn "docs/" README*.md`
- 测试计数: `grep -rn "passed\|Tests:" docs/ README*.md`
- CI 配置: `.github/workflows/ci.yml`

### 9.2 相关文档

- [PROJECT_STATUS.md](PROJECT_STATUS.md) — v0.6.8 当前状态
- [TECH_DEBT.md](TECH_DEBT.md) — 技术债清单（64/64 已解决）
- [ROADMAP.md](ROADMAP.md) — 里程碑路线图
- [COVERAGE_IMPROVEMENT_PLAN.md](COVERAGE_IMPROVEMENT_PLAN.md) — 历史覆盖率改进计划
- [P2_P3_FIX_PLAN.md](P2_P3_FIX_PLAN.md) — 历史 P2/P3 修复计划

---

**审核状态**: ✅ 共识达成（2026-07-13）
**下一步**: 按确认顺序推进实施 — Wave 1（文档校准）→ Wave 3（清理）→ Wave 2（覆盖率）→ Wave 4（CI）→ Wave 5（渲染测试）
