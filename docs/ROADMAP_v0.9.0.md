# PyCC2 v0.9.0 推进计划 — 视觉打磨与 UI 提升

> **版本**: v0.9.0-plan-rev2 | **创建日期**: 2026-07-18 | **最后更新**: 2026-07-20 | **状态**: 🚧 Wave C5 完成 (V-03 战后报告 + PostBattleReportRenderer + calculate_mvp + 62 测试)
> **前置版本**: v0.8.0 (P3-3 难度曲线已完成, 2026-07-18 推送)
> **目标**: 14 项视觉/UI 提升 (含 V-13/V-14 新增) + God Class SRP 评估 + 收束到 v0.9.0 发布
> **修订记录**:
> - 2026-07-20 Wave B 首轮共识: 7/7 APPROVE_WITH_CONCERNS, 5 P0 + 15 P1, 扩展 V-13/V-14 (rev1)
> - 2026-07-20 Wave B-rev 二次共识: 7/7 APPROVE_WITH_CONCERNS, 发现 11 新 P0 + 13 新 P1, 工作量 88h → 92-95h (rev2)

## Wave B-rev 二次共识关键决策 (2026-07-20)

**共识门**: ✅ 通过 (7/7 APPROVE_WITH_CONCERNS, 无否决) → 可进入 Wave C

**Wave C 启动前必修 (5 P0, 24h 内)**:
1. P0-4: 修改 `scripts/check_doc_consistency.sh:13-23` 追加 3 项 v0.9.0 文档
2. P0-NEW-5: 同步 VISUAL_POLISH_PLAN (105) 与 ROADMAP (95) 测试数量为 105
3. P0-NEW-6: 统一 V-13 暴击阈值为绝对值 `damage.amount >= 75`
4. P0-NEW-3: 将 `pip-compile dev > requirements-dev.lock` 列入 V-04 Wave C4
5. P0-NEW-4: 补 `scripts/update_perf_baseline.py` 设计或 inline 实现

**实施时修复 (Wave C5/D3/D4/D6/D7/E)**: 13 项 (详见 [CONSENSUS_V090_WAVE_B_REV.md](archive/CONSENSUS_V090_WAVE_B_REV.md) 第五节)

**工作量调整**: 88h → 92-95h (+4-7h, P1-13)
- V-01 +2h (ThemeManager register 所有渲染器)
- V-03 -1-2h (复用 UnitBattleRecord 而非新增 UnitBattleStats)
- V-08 +1h (state.paused 替代 pause()/resume())
- V-09 -2h (功能已存在, 仅需补日志)
- V-13 +2h (重构 add_popup API + 6 个调用方)
- V-14 +1-2h (新增 ROUTING 检测逻辑)

**新增教训** (在首轮 5 条基础上):
- 教训 6: 文档设计的 API 调用必须基于实际代码签名核对 (9 个不存在 API)
- 教训 7: 色彩命名需要校验饱和度, 高饱和度色彩不是莫兰迪色 (S < 50% 才算莫兰迪)

---

## 一、推进背景

### 1.1 v0.8.0 现状

- **测试**: 6301 passed / 2 skipped / 0 failed (零回归)
- **质量门禁**: ruff 0 errors / mypy 0 errors / radon cc E+ baseline=18 / check_doc_consistency 11/11 PASS
- **覆盖率**: 72.64% (42764 stmts, 10107 missed, 含 branch coverage)
- **架构**: DDD 4 层, 385 模块零循环依赖, Domain 占比 38.5%
- **v0.7.6 评估结论**: "可进入 v0.8.0 视觉打磨+平衡性调整阶段"

### 1.2 用户决策 (2026-07-18 + 2026-07-20 Wave B 共识)

**2026-07-18 初始决策**:
- **推进范围**: D — 全部 12 项 P0/P1/P2 推进
- **God Class 处理**: 先 SRP 评估再决定
- **版本收束**: 全部完成后收束到 v0.9.0

**2026-07-20 Wave B 共识后追加决策**:
- **扩展到 14 项**: 新增 V-13 伤害飘字 + V-14 士气视觉化 (P1)
- **V-07 基线前移 Wave C**: V-01 配置化迁移需视觉安全网先行
- **工作量上调**: 72h → 80-88h (V-01/V-03/V-12 各 +2-4h + V-13/V-14 各 ~6h)
- **用户额外指示**: 先做方案，让 DevSquad 团队达成共识后推进

### 1.3 DevSquad 7-Role 综合评估输出

| 角色 | 关注点 | 关键发现 |
|------|--------|----------|
| Architect | 渲染管线/模块化 | facade 模式成熟, RenderPass 模式属过度设计, 不采纳 |
| PM | 用户旅程/ROI | 战后报告是核心痛点, 快捷键提示实用价值高 |
| Security | 资源加载安全 | 无新增风险 (内部资源加载) |
| Tester | 视觉回归/FPS 基准 | 缺 FPS 实测, 缺视觉回归基线 |
| Coder | 代码可维护性 | 视觉参数硬编码严重, 需集中配置化 |
| DevOps | CI/资源/性能 | CI 缺视觉回归步骤, SpriteCache 预热缺失 |
| UI Designer | 色彩/布局/反馈 | 1280×720 固定布局在 1920×1080+ 失衡, 缺微动画 |

---

## 二、14 项提升清单

### 🟢 P0 — 高 ROI 必做 (4 项)

| # | 项目 | 影响 | 工作量 | ROI | 关联文件 |
|---|------|------|--------|-----|----------|
| **V-01** | 视觉参数集中配置化 | 可维护性 | 10-12h ↑ | 8 | enhanced_renderer.py / terrain_renderer.py / unit_renderer.py / cc2_combat_effects.py |
| **V-02** | VISUAL_OPTIMIZATION_UNIFIED.md 文档同步 | 文档准确性 | 3h | 7-8 ↓ | docs/VISUAL_OPTIMIZATION_UNIFIED.md |
| **V-03** | 战后报告与伤亡统计可视化 | 玩家体验 | 8-10h ↑ | 9 | campaign_ui_report_mixin.py / 新增 post_battle_report.py |
| **V-04** | FPS 性能基准测试 | 性能保障 | 4h | 7 | tests/benchmark/test_performance_baseline.py / ci.yml (复用现有 benchmark job) |

### 🟡 P1 — 应该做 (7 项, 含 V-13/V-14 新增)

| # | 项目 | 影响 | 工作量 | ROI | 关联文件 |
|---|------|------|--------|-----|----------|
| **V-05** | 现代屏幕响应式布局 | 玩家体验 | 8h | 6 | camera.py / cc2_bottom_panel.py / squad_panel.py |
| **V-06** | 操作反馈微动画 | 玩家体验 | 6h | 7 | button.py / selection_system.py / animation_system.py |
| **V-07** | 视觉回归测试基线 | 质量保障 | 10h (基线 4h 前移 Wave C + CI 6h Wave D) | 6 | 新建 tests/visual_regression/ + ci.yml |
| **V-08** | 快捷键完整性与 in-game 提示 | 玩家体验 | 4h | 8 | command_bar.py / hud.py / 新增 keybindings_overlay.py |
| **V-09** | SpriteCacheManager 预热策略 | 性能 | 5h | 6 | sprite_cache_manager.py / game_loop_assembler.py |
| **V-13** | 伤害飘字 (具体数值显示) | 战斗反馈 | 6h | 8 | presentation/ui/combat_popup.py (扩展现有) |
| **V-14** | 单位士气视觉化指示 | 战术可读性 | 6h | 7 | 新增 morale_indicator.py / morale_system.py / morale_types.py |

### 🔵 P2 — 可以做 (3 项)

| # | 项目 | 影响 | 工作量 | ROI | 关联文件 |
|---|------|------|--------|-----|----------|
| **V-10** | Morandi 色调可选 Skin | 美学 | 6h | 5 | pixel_artist.py / 新建 palette_morandi.py |
| **V-11** | 小地图地形细节 | 战术可读性 | 4h | 6 | minimap.py |
| **V-12** | 可访问性 (色盲/字体可调) | 可访问性 | 10-12h ↑ | 5-6 ↑ | 新建 accessibility.py / 各 UI 组件 |

**总计**: 14 项 / **~88h** 工作量 (含 V-13/V-14 新增 12h + V-01/V-03/V-12 各 +2-4h 上调)

### 2.1 V-13/V-14 现有代码现状 (Wave B-rev 调研结论)

**V-13 伤害飘字**:
- `src/pycc2/presentation/ui/combat_popup.py` 已存在 `CombatPopup` (dataclass) + `CombatPopupManager` 类
- 已实现状态文字飘字: `add_taking_fire` / `add_breaking` / `add_pinned` / `add_out_of_ammo` / `add_kia` / `add_surrender`
- 已有 alpha 渐变 (最后 0.5s 渐隐) + 上浮动画 (15px/s) + 阴影描边 + surface pool
- **缺**: 具体伤害数字显示 (如 "-25") — V-13 是扩展而非新建
- **可复用**: animation_system.py 的 ParticleEmitter (blood_hit preset) 已有粒子反馈

**V-14 士气视觉化**:
- `src/pycc2/domain/systems/morale_system.py` + `morale_types.py` + `morale_calculator.py` + `morale_effects.py` + `morale_routing.py` 已完整实现
- `MoraleState` 5 状态: RALLYED (>70) / WAVERING (40-70) / PINNED (20-40) / BROKEN (<20) / ROUTING (active fleeing)
- `MoraleSystem.get_state()` / `get_accuracy_modifier()` / `get_movement_modifier()` / `can_move()` / `can_accept_orders()` 等接口已就绪
- **缺**: 单位精灵上无士气状态视觉指示 — V-14 新增 `morale_indicator.py` 在精灵旁叠加士气指示

---

## 三、God Class SRP 评估结论 (Wave A3 已完成)

### 3.1 评估结果

| # | 文件 | 实际行数 | 实际路径 | 判定 | 建议 |
|---|------|---------|---------|------|------|
| 1 | terrain_rendering_system.py | 896L | presentation/rendering/ | **FALSE** | REFACTOR_LIGHT (提取 _resolve_tile_texture 消除 ~100L 重复) |
| 2 | hud_renderer.py | 886L | **_archive/** (已归档) | **FALSE** | 跳过 (无活跃引用) |
| 3 | environmental_audio.py | 811L | infrastructure/audio/ | **FALSE** | KEEP_AS_IS (已正确分为 2 类) |

### 3.2 累计统计

- **本次**: 3 候选 → 0 TRUE / 3 FALSE (0% 命中率)
- **累计**: 55 候选 → 1 TRUE / 54 FALSE (1.8% 命中率, 98.2% 误判率)
- **教训再次验证**: 行数阈值 >800L 极不可靠, 必须基于 SRP 分析

### 3.3 行动决策

- ❌ **不拆分** terrain_rendering_system.py / environmental_audio.py (SRP 分析确认非 God Class)
- ✅ **V-01 配置化时附带** terrain_rendering_system.py 提取 `_resolve_tile_texture` 私有方法消除重复 (低风险内部重构)
- ✅ **D14 候选清单需更新** 移除 _archive/hud_renderer.py, 修正 environmental_audio.py 路径

详见: [docs/archive/ASSESSMENT_GODCLASS_V090.md](archive/ASSESSMENT_GODCLASS_V090.md)

---

## 四、Wave 推进时间表

### Wave A: 文档先行 (✅ 完成)

| 子项 | 状态 | 说明 |
|------|------|------|
| A1: 创建 ROADMAP_v0.9.0.md | ✅ 完成 | 本文档 |
| A2: 创建 VISUAL_POLISH_PLAN.md | ✅ 完成 | 14 项视觉打磨详细设计 |
| A3: SRP 评估 3 个 God Class 候选 | ✅ 完成 | 3/3 FALSE, 输出 ASSESSMENT_GODCLASS_V090.md |

### Wave B: DevSquad 7-Role 共识评估 (✅ 完成 + 🚧 Wave B-rev 进行中)

**Wave B (首轮, ✅ 完成)**: 7/7 APPROVE_WITH_CONCERNS, 5 P0 Blocker + 15 P1 修改建议。详见 [CONSENSUS_V090_WAVE_B.md](archive/CONSENSUS_V090_WAVE_B.md)。

| 角色 | 投票 | 置信度 | 否决权 |
|------|------|--------|--------|
| Architect | APPROVE_WITH_CONCERNS | 高 | 否 |
| Coder | APPROVE_WITH_CONCERNS | 高 | 否 |
| PM | APPROVE_WITH_CONCERNS | 中 | 否 |
| UI Designer | APPROVE_WITH_CONCERNS | 中 | 否 |
| Security | APPROVE_WITH_CONCERNS | 高 | 否 |
| DevOps | APPROVE_WITH_CONCERNS | 高 | 否 |
| Tester | APPROVE_WITH_CONCERNS | 中 | 否 |

**Wave B-rev (修订版, 🚧 进行中)**: 整合 P0/P1 修改建议 + 新增 V-13/V-14 后进行 7-Role 二次共识评估。

### Wave C: P0 实施 (4 项, ~25-29h, 含 V-07 基线前移)

| 子项 | 项目 | 工作量 | 依赖 | 状态 |
|------|------|--------|------|------|
| C1: V-02 文档同步 | VISUAL_OPTIMIZATION_UNIFIED.md 更新到 v0.9.0 现状 | 3h | 无 | ✅ 完成 (1.0→2.0) |
| C2: V-07 视觉回归基线建立 (前移) | 5 核心场景截图基线 + SDL_VIDEODRIVER=dummy 统一渲染 | 4h | 无 (前置 gate) | ✅ 完成 (7 测试通过) |
| C3a: V-01 visual_config.py 创建 | 5 frozen dataclass (57 参数 ≥40) + ThemeManager + 25 测试 | 3h | C1, C2 | ✅ 完成 |
| C3b: V-01 迁移硬编码到 DEFAULT_VISUAL_CONFIG | 6 文件 TILE_SIZE=48 → DEFAULT_VISUAL_CONFIG.dimensions.TILE_SIZE | 2h | C3a | ✅ 完成 (282+7 测试通过) |
| C3c: V-01 附带提取 _resolve_tile_texture | terrain_rendering_system.py 消除 ~100L 重复 (SRP) | 2h | C3b | ✅ 评估后无需提取 (重复代码不足 ~100L) |
| C3d: V-01 接口冻结 + 截图对比 | 字段名/类型/默认值锁定 + 4 地形场景手动截图对比 | 1h | C3b, C3c | ✅ 完成 (接口冻结 12 测试 + V-07 视觉回归 0% 差异替代手动截图) |
| C4: V-04 FPS 性能基准 | 复用现有 benchmark job + pytest-benchmark + 相对基线 (下降 >15% 失败) | 4h | 无 | ✅ 完成 (test_fps_baseline.py 8 测试 + CI 集成 + scripts/update_perf_baseline.py) |
| C5: V-03 战后报告 | 创建 post_battle_report.py + 集成到 campaign_ui + BattleResult schema 强类型化 | 8-10h ↑ | 无 | ✅ 完成 (PostBattleReportRenderer 4 渲染方法 + calculate_mvp + BattleEvent @dataclass + 62 测试 + factory pattern) |

**Wave C3b 迁移范围调整说明 (2026-07-20)**:

V-01 设计文档原列 "9 个文件", 实际迁移 6 个文件:
- ✅ 迁移: texture_basic / texture_water_bridge / texture_structures / texture_vegetation / procedural_texture_generator / enhanced_renderer (共 6 个, 均为 `TILE_SIZE = 48` 硬编码)
- ❌ 不迁移: `sprite_generator.py` — `TILE_SIZE = 32` 是该模块的 icon canvas 设计尺寸 (注释明确 "icons at small sizes (up to 32x32 pixels)"), 不是地形 TILE_SIZE, 修改会破坏所有 icon 绘图函数
- ❌ 不迁移: `input_router.py` — 经 Grep 搜索确认无视觉硬编码 (仅按键映射 `_SQUAD_DIGIT_KEYS`), V-01 文档列入是错误
- ⏳ 推迟: `cc2_combat_effects.py` / `terrain_renderer.py` / `unit_renderer.py` — Grep 搜索未发现明确的 EXPLOSION/MUZZLE/UNIT_SIZE 等硬编码常量, 推迟到 Wave C3d 接口冻结检查时再评估
- ⏳ 推迟: `CC2_TERRAIN_PALETTE` 颜色字典 (terrain_tile_cache.py) — 与 ColorPalette 默认值不一致 (grass_base=(64,96,32) vs GRASS_PRIMARY=Color(76,124,35)), 迁移会破坏视觉等价, 推迟到 V-10 Morandi skin 实施时统一处理

### Wave D: P1 实施 (7 项, ~39h, 含 V-13/V-14)

| 子项 | 项目 | 工作量 | 依赖 |
|------|------|--------|------|
| D1: V-05 响应式布局 | scale_factor 自适应 + 三栏比例调整 + pygame.transform.scale 最近邻 | 8h | C3 |
| D2: V-06 操作反馈微动画 | hover/click(120-150ms)/选中/错误 4 类微动画 + ease_out_cubic | 6h | C3 |
| D3: V-08 快捷键提示 | keybindings_overlay.py (透明度 60-70% + 联动暂停 + 任意键关闭) + 命令栏完善 | 4h | 无 |
| D4: V-09 SpriteCache 预热 | 启动时预加载常用精灵 (logger.info 替代进度条) | 5h | 无 |
| D5: V-07 视觉回归 CI 集成 | Pillow ImageChops 阈值 3-5% + 平台差异化基线目录 + 每周 schedule 触发 | 6h | C2 |
| D6: V-13 伤害飘字扩展 | combat_popup.py 新增 add_damage_number() + 数字飘字动画 | 6h | C3 |
| D7: V-14 士气视觉化 | morale_indicator.py (5 状态色彩 + 图标 + 选中详情) | 6h | C3 |

### Wave E: P2 实施 (3 项, ~20-22h)

| 子项 | 项目 | 工作量 | 依赖 |
|------|------|--------|------|
| E1: V-10 Morandi 色调 | palette_morandi.py + 可选 skin 切换 (含确认弹窗 + 进度条 + 淡入淡出过渡) | 6h | C3 |
| E2: V-11 小地图地形细节 | minimap.py 添加地形色彩 + 单位朝向 (仅选中) + 伤亡标记 (暂停延长) + legend toggle | 4h | C3 |
| E3: V-12 可访问性 | accessibility.py + 色盲模式 (仅 UI+地形) + 字体 4 档 (12/14/16/20pt) | 10-12h ↑ | C3 |

### Wave F: 验证与发布 (⏳ 待开始)

| 子项 | 状态 | 说明 |
|------|------|------|
| F1: ruff + mypy + radon + check_doc_consistency (扩展 REQUIRED_DOCS) | ⏳ | 全绿 + bandit.yaml exclude _archive + verify_d14_candidates.py |
| F2: 全量 pytest 零回归 + e2e 真实用户旅程扩展 | ⏳ | 目标: 6301+N passed (N=~105 新增, Wave B-rev P0-NEW-5 同步) + test_pre_release_full_journey.py 扩展 3 验证点 + 5-8 真实玩家旅程 e2e |
| F3: 版本号 0.8.0 → 0.9.0 + 文档同步 (MINOR) | ⏳ | SemVer MINOR: 14 项用户可见新功能 |
| F4: Git commit + push (拆分多个 commit) | ⏳ | feat + chore 模式 |
| F5: CarryMem 记录 v0.9.0 完成 + playtest_v090_accessibility.md | ⏳ | 总结 + 教训强化 + V-12 playtest 记录 |

---

## 五、11-Phase 生命周期映射

按 DevSquad V3.6.0 11-Phase 模型,本次推进采用 `frontend` 模板 (无 P4/P6):

| Phase | 名称 | 责任人 | 状态 | 备注 |
|-------|------|--------|------|------|
| P1 | 需求分析 | PM | ✅ 完成 | 12 项需求已明确 |
| P2 | 架构设计 | Architect | ✅ 完成 | facade 模式保留, 无架构重写 |
| P3 | 技术设计 | Architect+Coder | ⏳ 进行中 | VISUAL_POLISH_PLAN.md 编写中 |
| P5 | 交互设计 | UI | ⏳ 进行中 | 12 项视觉规格定义中 |
| P7 | 测试计划 | Tester | ⏳ 待开始 | 视觉回归测试策略待定 |
| P8 | 实施 | Coder | ⏳ 待开始 | Wave C/D/E |
| P9 | 测试执行 | Tester | ⏳ 待开始 | Wave F1-F2 |
| P10 | 部署发布 | DevOps | ⏳ 待开始 | Wave F3-F4 |
| P11 | 运维保障 | DevOps+Sec | ⏳ 待开始 | Wave F5 CarryMem 记录 |

---

## 六、验收标准

### 6.1 功能验收 (14 项全部完成)

- [ ] V-01 视觉参数集中配置化 (visual_config.py 创建, ≥20 项参数, 硬编码迁移, 接口冻结)
- [ ] V-02 VISUAL_OPTIMIZATION_UNIFIED.md 同步到 v0.9.0 现状
- [ ] V-03 战后报告可视化 (post_battle_report.py 创建, BattleResult 强类型, 集成到 campaign_ui, 字段缺失降级)
- [ ] V-04 FPS 性能基准 (复用现有 benchmark job, pytest-benchmark, 相对基线)
- [ ] V-05 响应式布局 (scale_factor 自适应, pygame.transform.scale 最近邻, 1280×720/1920×1080/2560×1440 三档验证)
- [ ] V-06 操作反馈微动画 (4 类微动画: hover/click(120-150ms)/选中/错误 + ease_out_cubic)
- [ ] V-07 视觉回归测试 (4 核心基线 + 1 天气 sanity = 5 基线, Pillow ImageChops 阈值 3-5%, SDL_VIDEODRIVER=dummy 统一)
- [ ] V-08 快捷键提示 (keybindings_overlay.py, 透明度 60-70%, 联动暂停, 任意键关闭, 位置偏下)
- [ ] V-09 SpriteCache 预热 (启动时预加载常用精灵, logger.info 替代进度条)
- [ ] V-10 Morandi 色调可选 Skin (palette_morandi.py, 确认弹窗 + 进度条 + 淡入淡出过渡, 战斗中禁用切换)
- [ ] V-11 小地图地形细节 (地形色彩 + 单位朝向仅选中 + 伤亡标记暂停延长 + legend toggle)
- [ ] V-12 可访问性 (色盲模式仅 UI+地形 + 字体 4 档 12/14/16/20pt, playtest 验证)
- [ ] V-13 伤害飘字 (combat_popup.py 扩展 add_damage_number(), 具体数值显示)
- [ ] V-14 士气视觉化 (morale_indicator.py, 5 状态色彩 + 图标 + 选中详情)

### 6.2 质量验收

- [ ] ruff check: 0 errors
- [ ] mypy: 0 errors
- [ ] radon cc: 0 D+ 新增函数 (baseline=18)
- [ ] check_doc_consistency.sh: 全部 PASS (REQUIRED_DOCS 扩展含 v0.9.0 文档, 版本号 0.9.0 一致)
- [ ] bandit.yaml: exclude_dirs 含 src/pycc2/_archive/
- [ ] pytest: 6301+N passed 零回归 (N=~105 新增, Wave B-rev P0-NEW-5 同步)
- [ ] e2e: 全部通过 (含 test_pre_release_full_journey.py 扩展 3 验证点 + 5-8 真实玩家旅程)
- [ ] V-12 playtest: 3 名测试人员各 1 局, 产出 docs/qa/playtest_v090_accessibility.md
- [ ] verify_d14_candidates.py: 全部路径验证通过

### 6.3 文档验收 (活文档原则)

- [ ] VERSION / pyproject.toml / __init__.py: 0.9.0
- [ ] README.md / README_zh.md / README_ja.md: 0.9.0 + 新特性描述
- [ ] SKILL.md: 0.9.0
- [ ] docs/PRD.md / DESIGN.md / ROADMAP.md / TECH_DEBT.md / TEST_PLAN.md / PROJECT_STATUS.md: 0.9.0 同步
- [ ] CHANGELOG.md: v0.9.0 完整条目
- [ ] docs/VISUAL_OPTIMIZATION_UNIFIED.md: 同步到 v0.9.0 现状
- [ ] docs/VISUAL_POLISH_PLAN.md: 实施完成标记
- [ ] docs/ROADMAP_v0.9.0.md: 状态改为 ✅ 完成 + 完成总结
- [ ] docs/archive/CONSENSUS_V090_WAVE_B.md: Wave B 共识归档
- [ ] docs/qa/playtest_v090_accessibility.md: V-12 playtest 记录

---

## 七、文档同步清单 (Wave F3 必更)

按 DevSquad Meta Iron Rule "文档先行, 万事留痕", Wave F3 必须同步以下文档:

| # | 文档 | 更新内容 |
|---|------|----------|
| 1 | VERSION | 0.8.0 → 0.9.0 |
| 2 | src/pycc2/__init__.py | __version__ = "0.9.0" |
| 3 | pyproject.toml | version = "0.9.0" |
| 4 | README.md | L3 版本号 + 新特性描述 |
| 5 | README_zh.md | L3 版本号 + 新特性描述 |
| 6 | README_ja.md | L3 版本号 + 新特性描述 |
| 7 | SKILL.md | L3 版本号 |
| 8 | docs/PRD.md | L1 + L3 版本号 + v0.9.0 用户故事 |
| 9 | docs/DESIGN.md | L1 + L5 版本号 + 视觉打磨架构 |
| 10 | docs/ROADMAP.md | L3 版本号 + v0.9.0 里程碑 |
| 11 | docs/TECH_DEBT.md | L3 版本号 + God Class 评估结论 |
| 12 | docs/TEST_PLAN.md | L1 版本号 + 测试数 6321 → 6321+N |
| 13 | docs/PROJECT_STATUS.md | L4 + L11 版本号 + 视觉打磨完成 |
| 14 | CHANGELOG.md | 新增 v0.9.0 完整条目 |
| 15 | docs/VISUAL_OPTIMIZATION_UNIFIED.md | 同步到 v0.9.0 现状 |
| 16 | docs/VISUAL_POLISH_PLAN.md | 标记 ✅ 完成 |
| 17 | docs/ROADMAP_v0.9.0.md | 状态改为 ✅ 完成 + 完成总结 |

---

## 八、教训预防 (10 条, 含 Wave B 共识新增 5 条)

按 project_memory 教训强化 + Wave B 共识新增教训:

### 8.1 原有教训 (5 条)

1. **不机械拆分 God Class**: 本次 3 个 >800L 候选全部 FALSE, 累计 1.8% 命中率, 严格基于 SRP 分析
2. **文档同步是活文档原则的核心**: V-02 优先推进, 避免后续工作基于过期文档
3. **视觉参数配置化先行 (V-01)**: 后续 V-05/V-06/V-10/V-11/V-12/V-13/V-14 均依赖配置化基础
4. **视觉回归测试 ROI 评估**: V-07 工作量 10h, 需评估对 pygame 单机项目是否过度, 若 ROI 低可降级
5. **路径偏差暴露元数据陈旧**: D14 候选清单需与当前代码树同步, _archive 文件不应在候选清单中

### 8.2 Wave B 共识新增教训 (5 条)

6. **视觉回归测试应与视觉改动同步建立**: V-01 配置化迁移硬编码值时，V-07 视觉回归测试尚未建立 — 经典"测试滞后"反模式。视觉安全网必须先于视觉改动建立 (Wave B-rev 已修正: V-07 基线前移 Wave C2)
7. **CI 设计应核对现有 job 避免冗余**: V-04 提议新建 benchmark job，但现有 ci.yml:239-271 已有 benchmark job — 设计前必须核查现有 CI 配置 (Wave B-rev 已修正: V-04 复用现有 job)
8. **文档类型签名必须与代码一致**: V-03 文档 `battle_result: dict` 与代码 `BattleResult @dataclass` 不一致 — 文档设计前必须读取实际代码签名 (Wave B-rev 已修正: V-03 改用 BattleResult 强类型)
9. **跨平台视觉测试必须有平台差异化基线策略**: V-07 设定 1% 阈值但未考虑 macOS/Linux/Windows 字体渲染差异 — 跨平台视觉测试必须明示平台基线策略 (Wave B-rev 已修正: 采用 SDL_VIDEODRIVER=dummy 统一渲染 + 阈值 3-5%)
10. **PM 评估应主动识别缺失功能**: PM 识别出 12 项之外的两个高价值视觉痛点 (V-13 伤害飘字 + V-14 士气视觉化) — PM 评估不应仅评估现有清单，还应主动识别缺失功能 (Wave B-rev 已扩展: 14 项清单)

---

## 九、参考文档

- [docs/VISUAL_POLISH_PLAN.md](VISUAL_POLISH_PLAN.md) — 14 项视觉打磨详细设计
- [docs/archive/ASSESSMENT_GODCLASS_V090.md](archive/ASSESSMENT_GODCLASS_V090.md) — God Class SRP 评估报告
- [docs/archive/CONSENSUS_V090_WAVE_B.md](archive/CONSENSUS_V090_WAVE_B.md) — Wave B 7-Role 共识评估报告
- [docs/VISUAL_OPTIMIZATION_UNIFIED.md](VISUAL_OPTIMIZATION_UNIFIED.md) — 视觉优化统一规范 (待 V-02 同步)
- [docs/ROADMAP_v0.8.0.md](ROADMAP_v0.8.0.md) — 前置版本 P3-3 难度曲线推进计划
- [docs/TECH_DEBT.md](TECH_DEBT.md) — 技术债清单
- [docs/PROJECT_STATUS.md](PROJECT_STATUS.md) — 项目状态

---

**最后更新**: 2026-07-20 | **状态**: 🚧 Wave C5 完成 (V-03 战后报告 + PostBattleReportRenderer + calculate_mvp + 62 测试) | **下一步**: Wave D (P1 实施: V-05/V-06/V-07 CI/V-08/V-09 + V-13/V-14)
