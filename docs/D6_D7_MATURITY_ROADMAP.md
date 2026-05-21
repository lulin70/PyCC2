# PyCC2 项目成熟度评估与路线图 (D6 + D7)

> **文档版本**: v1.0 | **评估日期**: 2026-05-18 | **项目版本**: v0.4-fix1
> **评估方法**: 基于代码库实际审计、静态分析、测试运行、架构审查
> **性质**: 内部规划文档 — 直面问题，诚实评估

---

## 第一部分：成熟度评估 (Dimension 6)

---

### A. 技术就绪等级 (TRL) 评估

| TRL | 定义 | PyCC2 状态 | 判定依据 |
|-----|------|-----------|----------|
| TRL 1 | 基本原理观察 | ✅ PASSED | CC2 核心机制（弹道/士气/FoW/A*）理论验证 |
| TRL 2 | 技术概念形成 | ✅ PASSED | PRD v1.3 完成，33 User Stories，MoSCoW 优先级矩阵 |
| TRL 3 | 实验性概念验证 | ✅ PASSED | P0 垂直切片完成，~85 测试通过 |
| TRL 4 | 实验室技术验证 | ✅ PASSED | 完整测试套件 1088 tests passed，覆盖率 ~70% |
| TRL 5 | 相关环境验证 | ✅ PASSED | 可运行的游戏 Demo，pygame 渲染管线可用 |
| **TRL 6** | **运行环境技术演示** | **📍 CURRENT** | **全功能可玩游戏，P0-P3 全部完成，4 项关键 Bug 已修复** |
| TRL 7 | 运行环境系统原型演示 | ⏳ NEAR | 距离约 3 周 (P4 完成) |
| TRL 8 | 系统完整并合格 | 🔮 FUTURE | 预计 v0.6-v1.0 |
| TRL 9 | 实际系统在运行环境中验证 | 🔮 FUTURE | 用户反馈驱动 |

**当前 TRL 判定: TRL 6 (Beta 阶段)**

判定理由：
- 核心战斗循环端到端可用（PlayerCommand → BallisticEngine → damage → death → VFX）
- AI 对手具备完整行为树决策链路
- 存档系统含 HMAC 完整性保护
- 视觉渲染包含像素画/动画/粒子/HUD 全套
- 音效系统程序化生成 23 种音效类型
- **但缺少**: 设置菜单、平台打包、教程引导

---

### B. 功能完整度矩阵

| 功能域 | 计划功能 | 已完成功能 | 完成度 | 说明 |
|--------|---------|------------|--------|------|
| **核心战斗** | 弹道计算、伤害结算、死亡机制、移动系统 | 弹道引擎(BallisticEngine)、伤害浮动±20%、死亡移除、A*寻路移动、压制累积 | **95%** | 缺：掩体穿透计算细化 |
| **单位名册** | 8 种单位类型 + 独立属性模板 | 8 种全部实现 (Rifle/MG/AT/Commander/Mortar/Tank/Sniper/Medic)，UNIT_TEMPLATES 含完整属性 | **100%** | ✅ 完整 |
| **地形系统** | 14 种地形 + 属性体系 | 14 种 TerrainType 全部实现，含 movement_cost/cover_bonus/concealment/blocks_los/is_passable/height/color | **100%** | ✅ 完整 |
| **AI 对手** | 行为树 + 指挥官 AI + 小队协调 + 难度系统 | BehaviorTree(4节点类型) + CommanderAI(662行) + SquadCoordinator(495行) + DifficultySystem(4级预设) + CombatEngagement + PerceptionSystem | **90%** | 缺：AI 热座/回放支持 |
| **视觉渲染** | 像素画、动画、粒子、HUD | PixelArtist(1266行) + SpriteRenderer(549行) + AnimationSystem(6种动画) + ParticleEmitter(8种) + HUD/CommandBar/UnitPanel/Minimap + ScreenShake | **85%** | 缺：天气效果、昼夜变化 |
| **音频系统** | 程序化音效 + 音乐占位 | SoundSystem(298行) + 23种SoundType + ProceduralSoundGenerator(8波形) + UI/战斗/脚步分类音效 | **75%** | 缺：BGM音乐文件(仅有占位接口) |
| **输入/交互** | 鼠标+键盘+相机控制 | InputHandler + InteractionController(左键选/右键令) + Shortcuts + Camera(拖拽/滚轮缩放) + CommandBar按钮交互 | **90%** | 缺：键位重绑定UI |
| **游戏系统** | 胜负/统计/战役/存档 | VictoryConditionEvaluator(5种条件) + BattleStats + CampaignManager(3关) + SecureSaveManager(HMAC+8槽位) + quick_save/load | **80%** | 缺：仅3个任务地图 |
| **内容资源** | 地图/任务/单位模板数据 | 1张地图(tutorial.json) + 1个单位模板JSON + Schema定义 | **25%** | ⚠️ 严重不足：需5-8张地图 |
| **UX/打磨** | 设置菜单/教程/提示 | Tooltip组件(基础hover提示) + Debug Overlay(F3三级) + DisplayConfig(分辨率/UI缩放) | **30%** | ⚠️ 无设置UI、无教程、无首启动引导 |
| **多人游戏** | 网络/热座/回放 | 仅 command.py 中有 replay 关键字提及 | **5%** | ❌ Won't 级别，本期不做 |
| **Modding API** | 自定义单位/地形/地图 | SECURITY.md 中有完整的沙箱设计文档(v2.0计划)，代码层面无可用的 API | **10%** | 📋 设计文档完备，代码未开始 |
| **平台支持** | .app/.exe 构建/安装包 | pyproject.toml 有 entry_points(pycc2 CLI)，无 pyinstaller/spec/dmg 构建脚本 | **10%** | ❌ 仅源码分发 |

#### 功能域加权汇总

| 权重类别 | 包含域 | 平均完成度 | 权重 | 加权分 |
|----------|--------|-----------|------|--------|
| 核心玩法 (Must) | 核心战斗+单位+地形+AI+输入 | 96.25% | 35% | 33.69 |
| 表现层 (Should) | 视觉渲染+音频+UX | 63.33% | 25% | 15.83 |
| 系统完整性 (Should) | 游戏系统+内容 | 52.50% | 20% | 10.50 |
| 扩展性 (Could) | 多人+Modding+平台 | 8.33% | 20% | 1.67 |
| **总计** | | | 100% | **61.69%** |

---

### C. 质量指标仪表板

| 指标 | 当前值 | 目标值 | 状态 | 备注 |
|------|--------|--------|------|------|
| **测试数量** | **1088** | ≥1000 | ✅ 通过 | 48 个测试文件，34s 运行 |
| **测试通过率** | **100%** (1088/1088) | >99% | ✅ 通过 | 2 个 warnings (无害) |
| **代码覆盖率(估)** | **~70%** (domain 层) | >80% | ⚠️ 注意 | domain 层覆盖良好，game_loop 集成测试偏少 |
| **Ruff Lint** | **67 errors (src)** / **121 (tests)** | 0 | ⚠️ 注意 | 大量 E501(行宽) 和 import 排序；38+55 可自动修复 |
| **Mypy 类型检查** | 配置存在 | strict | ⚠️ 待验证 | mypy.ini 已配置，需跑一次确认 |
| **文档数量** | **18 份** (9内+9外) | ≥10 | ✅ 通过 | EN/ZH/JA 三语；含PRD/DESIGN/SECURITY/TEST_PLAN等 |
| **外部文档语言** | **3 种** (EN/ZH/JA) | ≥2 | ✅ 通过 | README + INSTALL + MANUAL 各三语 |
| **已知关键 Bug** | **0** | 0 | ✅ 通过 | 武器属性/存档状态/AI循环/入口点 4 项已修复 |
| **God Objects** | **1 个** (GameLoop 880行) | 0 | ⚠️ 注意 | 见下方详细分析 |
| **循环依赖** | **0 确认** | 0 | ✅ 通过 | 分层架构清晰：domain → services → presentation → infra |
| **安全漏洞** | **1 项** (HMAC硬编码密钥) | 0 | ⚠️ 注意 | `save_system.py:44` 明文密钥 |
| **总源码行数** | **13,249 行** (84 文件) | — | 📊 参考 | game_loop 占 6.6%，pixel_artist 占 9.6% |
| **CI/CD** | GitHub Actions (ci.yml) | 自动化 | ✅ 通过 | 已配置 workflow |

---

### D. 风险矩阵 (审计后更新)

#### D.1 技术债务风险

| # | 风险项 | 严重度 | 概率 | 得分 | 缓解方案 | P4 优先级 |
|---|--------|--------|------|------|----------|-----------|
| R-01 | **GameLoop 上帝对象 (880行)** | 🔴 高 | 🔴 高 | **9** | 拆分为 RenderPipeline / CombatDirector / InputRouter 三个子控制器 | P4.1 必做 |
| R-02 | **HMAC 密钥硬编码** | 🟡 中 | 🟡 中 | **4** | 移至环境变量或 `.env` 文件，运行时加载 | P4.1 必做 |
| R-03 | **Ruff Lint 错误 (67+121)** | 🟢 低 | 🔴 高 | **3** | 执行 `ruff --fix` 自动修复大部分，剩余手动处理 | P4.1 应做 |
| R-04 | **设置/选项菜单缺失** | 🟡 中 | 🔴 高 | **6** | 实现 SettingsUI：音量/画质/键位/难度选择 | P4.1 必做 |
| R-05 | **GameLoop 内联 pygame 渲染** | 🟡 中 | 🟡 中 | **4** | `_render_post_battle_screen` 和 `_render_hud` 含直接 pygame 调用，应抽取到 presentation 层 | P4.2 应做 |
| R-06 | **存档恢复异常吞没** | 🟢 低 | 🟡 中 | **2** | `quick_load` 中 `except Exception: pass` 吞掉所有异常，应细分处理并记录日志 | P4.2 应做 |
| R-07 | **性能未 profiling** | 🟢 低 | 🟡 中 | **3** | 128x128 地图 + 50 单位场景下 FPS 未基准测试 | P4.2 选做 |
| R-08 | **内容资产匮乏** | 🟡 中 | 🔴 高 | **6** | 仅 1 张地图/1 个单位模板 JSON，需要至少 5 张地图 | P4.2-P4.3 必做 |

#### D.2 GameLoop 上帝对象详细分析

[game_loop.py](file:///Users/lin/trae_projects/PyCC2/src/pycc2/services/game_loop.py) 当前承担了以下 **7 个职责**：

| # | 职责 | 涉及方法 | 行数估算 | 应归属模块 |
|---|------|---------|---------|-----------|
| 1 | **主循环调度** | `run()`, `_update_logic()` | ~60 行 | GameLoop (保留) |
| 2 | **渲染编排** | `_render_hud()`, `_render_post_battle_screen()`, `_render_debug_ai()` | ~140 行 | RenderPipeline (新) |
| 3 | **战斗执行** | `_execute_attack()`, `_process_combat_effects()`, `_process_deaths()` | ~120 行 | CombatDirector (新) |
| 4 | **输入路由** | `_handle_input()`, `_handle_player_command()` | ~80 行 | InputRouter (新) |
| 5 | **移动管理** | `_process_unit_movements()` | ~55 行 | MovementController (新) |
| 6 | **存档集成** | `quick_save()`, `quick_load()`, `_restore_state_from_dict()` | ~150 行 | SaveController (新) |
| 7 | **HUD 初始化** | `_init_hud_system()` 及回调注册 | ~75 行 | HUDFactory (新) |

**推荐拆分策略**：

```
GameLoop (精简至 ~200 行)
├── RenderPipeline     (~150 行)  ← _render_hud, _render_post_battle, _render_debug_ai
├── CombatDirector     (~130 行)  ← _execute_attack, _process_combat_effects, _process_deaths
├── InputRouter        (~85 行)   ← _handle_input, _handle_player_command
├── MovementController (~60 行)   ← _process_unit_movements
└── SaveController     (~155 行)  ← quick_save/load, _restore_state_from_dict
```

#### D.3 安全风险详情

**HMAC 硬编码密钥** ([save_system.py:44](file:///Users/lin/trae_projects/PyCC2/src/pycc2/infrastructure/save_system.py#L44))：

```python
# 当前 (不安全)
HMAC_KEY = b"PyCC2_SecureSave_v1_HMAC_Key_2025"

# 建议 (安全)
import os
HMAC_KEY = os.environ.get("PYCC2_HMAC_KEY", "").encode()
if not HMAC_KEY:
    raise RuntimeError("PYCC2_HMAC_KEY environment variable required")
```

影响评估：
- 单机游戏场景下风险为 **中等**（攻击者需本地访问）
- 但密钥随源码分发意味着任何人都可以伪造存档
- 与 [SECURITY.md](file:///Users/lin/trae_projects/PyCC2/docs/SECURITY.md) 中描述的 PBKDF2 设备绑定方案不一致（文档描述了更安全的方案但代码使用了简化版本）

---

### E. 综合成熟度评分

#### E.1 评分模型 (加权法)

| 维度 | 权重 | 原始得分 | 加权得分 | 满分 |
|------|------|---------|---------|------|
| 功能完整度 | 35% | 61.69% | 21.59 | 35.00 |
| 质量指标 | 30% | 72.00%* | 21.60 | 30.00 |
| 技术架构 | 20% | 78.00%** | 15.60 | 20.00 |
| 安全与风险 | 15% | 65.00%*** | 9.75 | 15.00 |
| **总分** | **100%** | | **68.54** | **100** |

\* 质量指标原始分 = (测试满分 + 通过率满分 + 覆盖率70/80 + lint有缺 + 文档满分 + 安全有缺) / 6 ≈ 72%
\*\* 技术架构 = 分层清晰(满分) - god object扣分(-12) + 类型注解良好(+5) + CI配置(+5) ≈ 78%
\*\*\* 安全 = STRIDE评级B+(75) - HMAC扣分(-15) + 输入验证完善(+5) ≈ 65%

#### E.2 成熟度等级

| 等级 | 分数范围 | PyCC2 得分 | 判定 |
|------|---------|-----------|------|
| **A - 生产就绪** | 90-100% | — | 未达到 |
| **B - Beta** | 75-89% | — | 未达到 |
| **C - Alpha** | 60-74% | **68.54%** | **📍 当前** |
| **D - Pre-alpha** | 40-59% | — | 已超越 |

## 最终成熟度等级: **C (Alpha)** — 接近 Beta 门槛

### 差距分析 (距 Beta 的 6.46 分缺口)

| 缺口项 | 分值贡献 | 修复难度 |
|--------|---------|----------|
| 内容资产不足 (25%→60%) | +1.8 | 中 (需制作 5-8 张地图) |
| 设置菜单缺失 (30%→70%) | +1.2 | 中 (标准 UI 工作) |
| UX 打磨不足 | +1.0 | 中 (教程/引导) |
| Ruff 清理 | +0.8 | 低 (自动修复为主) |
| GameLoop 重构 | +0.8 | 中-低 (拆分明确) |
| HMAC 安全修复 | +0.5 | 低 (改动小) |
| 平台打包 | +0.4 | 中 (pyinstaller 配置) |

---

## 第二部分：路线图规划 (Dimension 7)

---

### P4 开发计划总览

**目标**: 将 PyCC2 从 **C (Alpha)/68.5%** 提升至 **B (Beta)/78%+**
**工期**: 3 周 (建议)
**核心主题**: **"Polish & Ship"** — 打磨体验，准备分发

---

### P4 候选任务池 (按 影响/投入 比 排序)

| ID | 任务 | 影响程度 | 投入规模 | I/E 比 | 依赖 |
|----|------|---------|---------|-------|------|
| **T4-01** | GameLoop 拆分重构 | 🔴 高 | 🟢 低 | **9.0** | 无 |
| **T4-02** | 设置/选项菜单 UI | 🔴 高 | 🟡 中 | **7.0** | 无 |
| **T4-03** | 安全加固 (HMAC env key) | 🟡 中 | 🟢 低 | **7.0** | 无 |
| **T4-04** | 平台打包 (.app/.exe) | 🔴 高 | 🟡 中 | **6.5** | T4-03 |
| **T4-05** | 性能优化 (tile缓存/AI节流/粒子池) | 🟡 中 | 🟡 中 | **5.0** | T4-01 |
| **T4-06** | 教程/提示系统 | 🟡 中 | 🟡 中 | **5.0** | T4-02 |
| **T4-07** | 更多战役任务 (Mission 4-6) | 🟡 中 | 🟡 中 | **5.0** | 无 |
| **T4-08** | Ruff Lint 全面清零 | 🟢 低 | 🟢 低 | **8.0** | 无 |
| **T4-09** | 额外单位类型 (Flamethrower/AT Rifle/Recon/Officer) | 🟢低-中 | 🟡 中 | **3.5** | 无 |
| **T4-10** | 存档边缘 case 集成测试增强 | 🟢 低 | 🟢 低 | **5.0** | T4-01 |

---

### P4 Sprint 详细计划

```
╔══════════════════════════════════════════════════════════════════════╗
║                    PyCC2 P4 "Polish & Ship" Roadmap                  ║
║                         v0.4-fix1 → v0.5-beta                       ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  Week 1: P4.1 — Critical Path (基础夯实)                             ║
║  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ║
║                                                                      ║
║  ▶ T4-01  GameLoop Decomposition    [████████░░] 80%               ║
║    ├─ 提取 RenderPipeline           (Day 1-2)                        ║
║    │   └─ _render_hud / _render_post_battle / _render_debug_ai      ║
║    ├─ 提取 CombatDirector           (Day 2-3)                        ║
║    │   └─ _execute_attack / _process_combat_effects / _deaths       ║
║    ├─ 提取 InputRouter              (Day 3)                          ║
║    │   └─ _handle_input / _handle_player_command                   ║
║    └─ 提取 SaveController           (Day 3-4)                        ║
║        └─ quick_save/load / _restore_state_from_dict                ║
║                                                                      ║
║  ▶ T4-02  Settings Menu                 [██████░░░] 60%             ║
║    ├─ SettingsScene class            (Day 2-4)                       ║
║    │   ├─ Volume sliders (Master/SFX/Music)                         ║
║    │   ├─ Quality presets (Low/Med/High/Ultra)                      ║
║    │   ├─ Difficulty selector (EASY/MED/HARD/VET)                   ║
║    │   └─ Key rebinding grid (basic keys only)                      ║
║    └─ Persist to engine.toml          (Day 4)                        ║
║                                                                      ║
║  ▶ T4-03  Security Hardening             [█████████] 95%            ║
║    ├─ Move HMAC_KEY to env/config   (Day 1)  ← 30min task           ║
║    ├─ Add PYCC2_HMAC_KEY to .env.example                            ║
║    └─ Fallback: generate+cache per-install key                      ║
║                                                                      ║
║  ▶ T4-08  Ruff Lint Cleanup               [█████████] 95%            ║
║    ├─ ruff --fix src/ tests/          (Day 1)  ← 1hr task           ║
║    └─ Manual fix remaining ~10 errors                                ║
║                                                                      ║
║  📊 Milestone: God object eliminated, settings usable, lint clean   ║
║  🧪 Target: 1120+ tests passing                                      ║
║                                                                      ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  Week 2: P4.2 — Polish (体验打磨)                                    ║
║  ━━━━━━━━━══━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ║
║                                                                      ║
║  ▶ T4-05  Performance Optimization       [█████░░░░] 50%            ║
║    ├─ Tile surface cache              (Day 1-2)                      ║
║    │   └─ Cache rendered tile Surfaces, invalidate on zoom           ║
║    ├─ AI update throttle              (Day 2)                        ║
║    │   └─ Cap AI updates to 10Hz max, stagger per-unit              ║
║    └─ Particle pool allocator         (Day 2-3)                      ║
║        └─ Pre-allocate particle objects, reuse instead of create    ║
║                                                                      ║
║  ▶ T4-06  Tutorial/Hint System           [████░░░░░] 40%            ║
║    ├─ First-launch overlay            (Day 3-4)                      ║
║    │   ├─ "Welcome to PyCC2" splash with 3-step intro              ║
║    │   ├─ Highlight: Left-click select, Right-click command         ║
║    │   └─ Dismissable permanently ("Don't show again")              ║
║    ├─ Context-sensitive help         (Day 4)                        ║
║    │   └─ ? button on panels shows relevant tooltip                 ║
║    └─ Extend existing Tooltip component                               ║
║                                                                      ║
║  ▶ T4-07  Additional Missions             [████░░░░░] 40%            ║
║    ├─ Mission 4: Night Assault        (Day 1-2)                      ║
║    │   └─ Night map, reduced vision, stealth bonus for snipers      ║
║    ├─ Mission 5: Breakout             (Day 3-4)                      ║
║    │   └─ Escort mission, protect convoy unit                       ║
║    └─ New map JSON files + briefings                                 ║
║                                                                      ║
║  ▶ T4-10  Save/Load Edge Case Tests      [█████░░░░] 50%            ║
║    ├─ Corrupted save recovery test                                     ║
║    ├─ Version mismatch handling test                                   ║
║    └─ Mid-combat save/restore integration test                         ║
║                                                                      ║
║  📊 Milestone: 60fps stable on 64x64, tutorial works, 5 missions    ║
║  🧪 Target: 1160+ tests passing                                      ║
║                                                                      ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  Week 3: P4.3 — Ship It (发布准备)                                   ║
║  ━━━━━━━━━══━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ║
║                                                                      ║
║  ▶ T4-04  Platform Packaging              [████░░░░░] 40%            ║
║    ├─ PyInstaller .spec file           (Day 1-2)                     ║
║    │   ├─ macOS .app bundle with icon + plist                       ║
║    │   ├─ Windows .exe (cross-compile or CI)                        ║
║    │   └─ Data files auto-included (maps/units/sounds)              ║
║    ├─ DMG/Installer creation           (Day 2-3)                     ║
║    └─ Code signing prep (optional)                                     ║
║                                                                      ║
║  ▶ T4-07  More Content (cont.)            [████░░░░░] 40%            ║
║    ├─ Mission 6: Last Stand           (Day 1-2)                      ║
║    │   └─ Defense mission, hold until reinforcements               ║
║    └─ Bridge assault + defense line maps                              ║
║                                                                      ║
║  ▶ Final Regression                                                      ║
║    ├─ Full test suite run             (Day 3)                        ║
║    │   └─ Target: 1200+ tests, 0 failures                           ║
║    ├─ Manual playtest session          (Day 3-4)                     ║
║    │   └─ Complete all 6 missions on MEDIUM difficulty               ║
║    └─ Performance benchmark            (Day 4)                        ║
║        └─ Document FPS at 32x32/64x64/128x128 with N units          ║
║                                                                      ║
║  ▶ Documentation Polish                                                   ║
║    ├─ Update README with v0.5 features                                  ║
║    ├─ Update INSTALL guides for .app distribution                     ║
║    ├─ Add CHANGELOG.md for v0.4→v0.5                                 ║
║    └─ Update USER_MANUAL with new mission briefings                   ║
║                                                                      ║
║  📊 Milestone: Distributable builds available, docs updated          ║
║  🧪 Target: 1200+ tests passing, 0 known bugs                        ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

### P4 交付物清单

| 交付物 | 标准 | 验证方式 |
|--------|------|----------|
| 重构后 GameLoop < 300 行 | `wc -l game_loop.py` |
| Settings 菜单可从暂停界面打开 | 手动测试 |
| HMAC 密钥不在源码中 | `grep -r "HMAC_KEY.*=" src/` 返回空 |
| Ruff 0 errors | `ruff check src/ tests/` |
| macOS .app 可双击启动 | `open PyCC2.app` |
| 5+ 张地图文件 | `ls data/maps/*.json \| wc -l` ≥ 6 |
| 教程首次启动显示 | 首次运行 + 检查 overlay |
| 测试数 ≥ 1200 | `pytest --tb=no -q` |
| 更新后的 README/CHANGELOG | 文件存在且内容正确 |

---

### 风险缓解与应急方案

| 风险 | 概率 | 影响 | 缓解措施 | Plan B |
|------|------|------|----------|--------|
| GameLoop 拆分引入回归 | 中 | 高 | 每提取一个子控制器立即跑全量测试 | 回退 git，增量式拆分 |
| 设置菜单开发超预期 | 低 | 中 | 先做 MVP（仅音量+分辨率） | 复用 debug_overlay 的配置面板 |
| pyinstaller 打包失败 | 中 | 中 | 使用 alternative: cx_Freeze / nuitka | 仅提供源码 + venv 安装脚本 |
| 新地图平衡性问题 | 中 | 低 | 复用 tutorial 地图的单位配比作为基线 | 发布时标注 "Experimental" |

---

### 成熟度提升预测

| 时间点 | 版本 | 预计成熟度分 | 等级 | 关键标志 |
|--------|------|-------------|------|----------|
| 现在 | v0.4-fix1 | **68.5%** | C (Alpha) | 1088 tests, 4 bugs fixed |
| P4.1 结束 | v0.5-dev1 | **73%** | C+ | GameLoop 拆分, Settings 可用, Lint 清洁 |
| P4.2 结束 | v0.5-dev2 | **77%** | B- (Beta) | 性能优化, 教程, 5 个任务 |
| P4.3 结束 | **v0.5.0** | **81%** | **B (Beta)** | **可分发的 .app, 1200+ tests** |

---

### 附录：关键文件索引

| 类别 | 文件路径 | 行数 | 说明 |
|------|---------|------|------|
| 主循环 | [game_loop.py](file:///Users/lin/trae_projects/PyCC2/src/pycc2/services/game_loop.py) | 880 | ⚠️ God Object，P4 重点重构目标 |
| 存档系统 | [save_system.py](file:///Users/lin/trae_projects/PyCC2/src/pycc2/infrastructure/save_system.py) | 231 | ⚠️ 含硬编码 HMAC 密钥 (L44) |
| 像素渲染 | [pixel_artist.py](file:///Users/lin/trae_projects/PyCC2/src/pycc2/presentation/rendering/pixel_artist.py) | 1266 | 最大单文件 |
| AI 指挥官 | [commander_ai.py](file:///Users/lin/trae_projects/PyCC2/src/pycc2/domain/ai/commander_ai.py) | 662 | AI 核心 |
| 战役系统 | [campaign.py](file:///Users/lin/trae_projects/PyCC2/src/pycc2/domain/systems/campaign.py) | 196 | 3 个任务定义 |
| 地形定义 | [terrain_type.py](file:///Users/lin/trae_projects/PyCC2/src/pycc2/domain/value_objects/terrain_type.py) | 188 | 14 种地形完整实现 |
| 单位定义 | [unit.py](file:///Users/lin/trae_projects/PyCC2/src/pycc2/domain/entities/unit.py) | 187 | 8 种单位 + UNIT_TEMPLATES |
| 难度系统 | [difficulty_system.py](file:///Users/lin/trae_projects/PyCC2/src/pycc2/domain/ai/difficulty_system.py) | 212 | 4 级难度预设 |
| 音效系统 | [sound_system.py](file:///Users/lin/trae_projects/PyCC2/src/pycc2/presentation/audio/sound_system.py) | 298 | 23 种音效类型 |
| 提示组件 | [tooltip.py](file:///Users/lin/trae_projects/PyCC2/src/pycc2/presentation/ui/tooltip.py) | 134 | 基础 hover 提示 |
| 安全设计 | [SECURITY.md](file:///Users/lin/trae_projects/PyCC2/docs/SECURITY.md) | 1684 | STRIDE 分析 + Mod 沙箱设计 |
| 产品需求 | [PRD.md](file:///Users/lin/trae_projects/PyCC2/docs/PRD.md) | 1468 | 33 US + MoSCoW + Gate 条件 |

---

> **文档结束** — 本评估基于 2026-05-18 代码库快照。建议每 Sprint 结束后重新评估。
