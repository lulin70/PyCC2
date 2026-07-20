# PyCC2 v0.9.0 Wave B 共识评估报告

> **版本**: 1.0 | **评估日期**: 2026-07-20 | **评估者**: DevSquad 7-Role
> **评估对象**: ROADMAP_v0.9.0.md (v1.0) + VISUAL_POLISH_PLAN.md (v1.0) + ASSESSMENT_GODCLASS_V090.md (v1.0)
> **关联**: [ROADMAP_v0.9.0.md](../ROADMAP_v0.9.0.md) | [VISUAL_POLISH_PLAN.md](../VISUAL_POLISH_PLAN.md)

---

## 一、共识投票结果

| # | 角色 | 投票 | 置信度 | 否决权 | 关键关注点 |
|---|------|------|--------|--------|------------|
| 1 | Architect | APPROVE_WITH_CONCERNS | 高 | 否 | V-01 扇入风险 + V-03 职责边界 + V-05 多分辨率 |
| 2 | Coder | APPROVE_WITH_CONCERNS | 高 | 否 | 工作量估计 + V-01 迁移风险 + V-03 schema 兼容 |
| 3 | PM | APPROVE_WITH_CONCERNS | 中 | 否 | 用户旅程 + V-12 ROI + 新增 V-13/V-14 |
| 4 | UI Designer | APPROVE_WITH_CONCERNS | 中 | 否 | 视觉一致性 + V-05 像素模糊 + V-06 动画时长 |
| 5 | Security | APPROVE_WITH_CONCERNS | 高 | 否 | V-03 类型安全 + bandit 盲区 |
| 6 | DevOps | APPROVE_WITH_CONCERNS | 高 | 否 | V-04 CI 冗余 + V-07 阈值过严 + 依赖缺失 |
| 7 | Tester | APPROVE_WITH_CONCERNS | 中 | 否 | V-01 视觉安全网时序 + F2 e2e 扩展 |

**共识门状态**: ✅ **7/7 通过 (无否决)**，但附带 5 项 P0 Blocker + 15 项 P1 修改建议。

---

## 二、P0 Blocker 修改建议 (5 项，必做)

### P0-1 (Tester): V-01 视觉安全网时序问题

**问题**: V-01 配置化迁移硬编码时，V-07 视觉回归测试尚未建立 (V-07 在 Wave D5)，V-01 迁移无自动化安全网。

**修复**: V-07 "基线建立"部分前移到 Wave C (V-01 实施前先建立 4 个核心场景截图对比基线)，V-07 "CI 集成"部分保留 Wave D5。

### P0-2 (Tester): F2 e2e 真实用户旅程扩展

**问题**: ROADMAP F2 仅写 "e2e 全部通过"，未明确扩展 `test_pre_release_full_journey.py` 加入 v0.9.0 新特性验证。违反用户规则 3 "发布前一定要做模拟真实用户使用的测试"。

**修复**: F2 验收清单明确增加 3 项验证点: (1) 战后报告显示伤亡图+MVP; (2) 按 `?` 键弹出快捷键 overlay; (3) 切换色盲模式后画面正确重渲染。补充 PM 建议的 5-8 条真实玩家旅程 e2e。

### P0-3 (DevOps): V-04 CI 设计冗余 + 依赖缺失

**问题**: 
1. VISUAL_POLISH_PLAN.md 提议新建 `benchmark` job 与现有 `.github/workflows/ci.yml:239-271` 的 `benchmark` job 重复
2. `pyproject.toml [project.optional-dependencies] dev` 未包含 `pytest-benchmark`，CI 会直接失败
3. `requirements-dev.lock` 未重新生成

**修复**: 
1. V-04 复用现有 `benchmark` job，不新建
2. `pyproject.toml` 增加 `pytest-benchmark>=4.0` 到 dev 依赖
3. 重新生成 `requirements-dev.lock` 与 `requirements.lock`

### P0-4 (DevOps): check_doc_consistency.sh 遗漏 v0.9.0 文档

**问题**: `scripts/check_doc_consistency.sh:13-23` 的 `REQUIRED_DOCS` 数组仅含 9 个文档，遗漏 3 个 v0.9.0 核心文档:
- `docs/VISUAL_POLISH_PLAN.md`
- `docs/ROADMAP_v0.9.0.md`
- `docs/VISUAL_OPTIMIZATION_UNIFIED.md`

Wave F3 文档同步后，check_doc_consistency 仍会 PASS 但实际遗漏 3 个 v0.9.0 关键文档。

**修复**: `REQUIRED_DOCS` 数组追加 3 项 v0.9.0 文档。

### P0-5 (Security): V-03 BattleResult 类型安全

**问题**: 
1. VISUAL_POLISH_PLAN.md V-03 设计 `render_enhanced_report(self, surface: Surface, battle_result: dict)` — 但实际代码 `src/pycc2/domain/systems/battle_result.py:66` 中 `BattleResult` 是 `@dataclass`，不是 dict
2. 文档新增字段 `events: list[dict]` / `unit_stats: dict[str, UnitBattleStats]` 使用裸 `dict` 而非 `@dataclass`，会导致 mypy 类型流失

**修复**: 
1. V-03 文档签名修正为 `battle_result: BattleResult`
2. 新增字段改用 `@dataclass(frozen=True, slots=True)`，如 `events: list[BattleEvent]`

---

## 三、P1 修改建议 (15 项，强烈建议)

### Architect (4 项)

| # | 建议 | 实施时机 |
|---|------|----------|
| A1 | V-01 完成后增加"接口冻结检查"前置 gate，再启动 Wave D (V-01 被 V-05/V-06/V-10/V-11/V-12 5 项强依赖) | Wave C2 → Wave D 之间 |
| A2 | V-03 章节增加 `PostBattleReportRenderer` vs 现有 `_render_report` 的替换/并存决策段落 | Wave A-rev 文档更新 |
| A3 | V-05 验收增加 1280×720 / 1920×1080 / 2560×1440 三档分辨率视觉验证矩阵 | Wave D1 验收 |
| A4 | `_resolve_tile_texture` 提取 PR 描述中显式声明"两处 blit 坐标差异"为不变量 | Wave C2 实施时 |

### Coder (5 项)

| # | 建议 | 实施时机 |
|---|------|----------|
| C1 | V-01 工作量 8h→10-12h，V-03 6h→8-10h，V-12 8h→10-12h，总预算 72h→80-88h | Wave A-rev 文档更新 |
| C2 | `visual_config.py` 模块 docstring 显式说明 "Color 字段内部可变，调用方只读" | Wave C2 实施时 |
| C3 | V-01 实施步骤增加"迁移前后手动截图对比"前置验收 (4 地形场景)，不等 V-07 自动化 | Wave C2 实施时 |
| C4 | V-03 设计补充 "新字段缺失时 PostBattleReportRenderer 降级到现有 _render_report 行为" | Wave A-rev 文档更新 |
| C5 | V-07 章节内部矛盾统一为 "8 地形时段基线 + 1 天气 sanity check = 9 基线" | Wave A-rev 文档更新 |

### PM (5 项)

| # | 建议 | 实施时机 |
|---|------|----------|
| P1 | V-12 ROI 从 4 上调至 5-6 (色盲男性 8% + 老花眼用户)，维持 P2 优先级 | Wave A-rev 文档更新 |
| P2 | V-02 ROI 从 9 下调至 7-8 (纯文档同步用户感知低) | Wave A-rev 文档更新 |
| P3 | **新增 V-13 伤害飘字 (P1)** + **V-14 士气视觉化 (P1)** — 用户已确认扩展到 14 项 | Wave A-rev 文档更新 |
| P4 | V-08 快捷键 overlay 必须联动游戏暂停 (P 键状态)，避免沉浸感破坏变为战术劣势 | Wave D3 实施时 |
| P5 | V-03 MVP 算法权重 (命中率/击杀/生存) 在详细设计中明示 | Wave A-rev 文档更新 |

### UI Designer (9 项)

| # | 建议 | 实施时机 |
|---|------|----------|
| U1 | V-01 补充"主题热更新"机制设计 (V-10 Morandi skin 切换时通知所有渲染器重读配置) | Wave A-rev 文档更新 |
| U2 | V-01 完整视觉参数清单 (≥20 项，含 shadow alpha / particle counts / line thickness) | Wave A-rev 文档更新 |
| U3 | V-05 明示使用 `pygame.transform.scale` (最近邻) 而非 smoothscale，引入 max_panel_width 与 capped font scale | Wave D1 实施时 |
| U4 | V-06 click 动画 100ms→120-150ms，统一定义 `ease_out_cubic` 缓动 | Wave D2 实施时 |
| U5 | V-03 战后报告：伤亡图与时间线改为 tab 切换；明示字号层级 (banner 32pt / 段标题 18pt / 正文 14pt)；MVP 卡支持横向滚动 | Wave A-rev 文档更新 |
| U6 | V-12 明示"色盲模式仅覆盖 UI + 地形，单位精灵保留原色"；字体改为 4 档 (12/14/16/20pt) 或连续滑块 (10-24pt) | Wave A-rev 文档更新 |
| U7 | V-11 小地图：单位朝向仅选中单位显示，伤亡标记暂停时延长，增加 legend toggle | Wave E2 实施时 |
| U8 | V-08 overlay 强制联动暂停；透明度 60-70%；任意键关闭；位置偏下 | Wave D3 实施时 |
| U9 | V-10 skin 切换补充确认弹窗 + 进度条 + 淡入淡出过渡；战斗中禁用切换 | Wave E1 实施时 |

### Security (2 项)

| # | 建议 | 实施时机 |
|---|------|----------|
| S1 | `bandit.yaml` 的 `exclude_dirs` 增加 `src/pycc2/_archive/`，与 mypy 配置对齐 | Wave F3 配置同步 |
| S2 | V-09 prewarm 失败 fallback 已设计 (懒加载)，需补 unit test 验证 fallback 路径不会因单文件缺失导致全游戏崩溃 | Wave D4 实施时 |

### DevOps (5 项)

| # | 建议 | 实施时机 |
|---|------|----------|
| D1 | V-04 FPS 测试加 `@pytest.mark.slow` 标记，移至 `slow-tests` job 或独立 schedule 触发；阈值从 10% 放宽到 20% 或改为软门禁 | Wave C3 实施时 |
| D2 | V-07 视觉回归阈值从 1% 放宽到 3-5%；增加平台差异化基线目录 `tests/visual_regression/.platform-baseline/{linux-dummy,macos-cocoa}/` | Wave D5 实施时 |
| D3 | V-09 进度条降级为可选 (100ms 启动延迟 < 200ms 感知阈值，logger.info 即可) | Wave D4 实施时 |
| D4 | 明确 `perf_baseline.json` 持久化策略：提交到 `tests/benchmark/baselines/` + 仅 `workflow_dispatch` 允许更新 | Wave C3 实施时 |
| D5 | 新增 `scripts/verify_d14_candidates.py` CI 步骤，检测 D14 候选清单路径偏差 | Wave F3 CI 加固 |

### Tester (5 项)

| # | 建议 | 实施时机 |
|---|------|----------|
| T1 | V-04 修正基线文件命名: `perf_baseline.json` → `.baseline_results.json` (复用现有)；FPS 阈值改用相对基线 (下降 >10%) 而非绝对值 | Wave C3 实施时 |
| T2 | V-07 视觉回归阈值 1% → 2%，并明确采用 `SDL_VIDEODRIVER=dummy` 统一渲染 (仅维护 1 套基线) | Wave D5 实施时 |
| T3 | V-03 创建 `tests/fixtures/battle_result_factory.py` 工厂，规范新 schema 测试数据创建 | Wave C4 实施时 |
| T4 | V-12 playtest 验证清单加入 Wave F1 验收项，产出 `docs/qa/playtest_v090_accessibility.md` | Wave F1 实施时 |
| T5 | 测试金字塔微调: 单元测试从 ~40 提升到 ~50 (补 visual_config 字段全覆盖 + post_battle_report 各分支 + accessibility 色彩矩阵)，总数 78 → 88 | Wave C-E 实施时 |

---

## 四、用户决策 (2026-07-20)

针对 Wave B 评估结果，用户做出以下决策:

| # | 决策项 | 用户选择 |
|---|--------|----------|
| 1 | PM 新增 V-13/V-14 是否扩展 v0.9.0 范围 | **扩展到 14 项** (V-13 伤害飘字 + V-14 士气视觉化) |
| 2 | Tester V-01 视觉安全网时序问题 | **V-07 基线前移 Wave C** (推荐方案) |
| 3 | Coder 工作量上调建议 | **上调到 80-88h** (推荐方案) |

用户额外指示: **先做方案，让 DevSquad 团队达成共识后推进**。

---

## 五、Wave B-rev 行动计划

基于用户决策，需要执行 Wave B-rev (修订版共识评估):

| 子项 | 行动 | 状态 |
|------|------|------|
| B-rev-1 | 创建本报告 (CONSENSUS_V090_WAVE_B.md) 归档 Wave B 结果 | ✅ 完成 |
| B-rev-2 | 整合 P0/P1 修改建议到 ROADMAP_v0.9.0.md | ⏳ 进行中 |
| B-rev-3 | 整合 P0/P1 修改建议到 VISUAL_POLISH_PLAN.md + 新增 V-13/V-14 详细设计 | ⏳ 进行中 |
| B-rev-4 | 7-Role 二次共识评估 (针对 14 项修订版方案) | ⏳ 待开始 |
| B-rev-5 | 7/7 通过 → 进入 Wave C | ⏳ 待开始 |

---

## 六、关键证据链

### 6.1 V-04 依赖缺失证据

- `.github/workflows/ci.yml:34` 运行 `pip install -r requirements-dev.lock`
- `pyproject.toml:34-48` `[project.optional-dependencies] dev` 未包含 `pytest-benchmark`
- VISUAL_POLISH_PLAN.md:244-254 提议使用 `--benchmark-only` flag (pytest-benchmark 专属)

### 6.2 V-07 阈值过严证据

- macOS CoreText vs Linux FreeType 字体渲染差异通常 2-5% 像素级差异
- V-07 文档设定 1% 阈值会必然产生 false positive
- 现有 e2e job 已设 `SDL_VIDEODRIVER: dummy` (ci.yml:169)，dummy driver 下字体抗锯齿与真实显示不同

### 6.3 V-01 视觉安全网时序证据

- V-01 在 Wave C2 实施 (VISUAL_POLISH_PLAN.md)
- V-07 在 Wave D5 实施，CI 集成部分更晚
- V-01 修改 4 个 renderer 文件 (enhanced_renderer / terrain_renderer / unit_renderer / cc2_combat_effects)，实际硬编码散布 9 个文件
- V-01 完成时 V-07 基线尚未建立，无法自动捕获视觉差异

### 6.4 V-03 类型安全证据

- `src/pycc2/domain/systems/battle_result.py:66` 中 `BattleResult` 是 `@dataclass`
- VISUAL_POLISH_PLAN.md V-03 设计 `render_enhanced_report(self, surface: Surface, battle_result: dict)` — 类型不匹配
- 新增字段 `events: list[dict]` 使用裸 dict 会丢失 mypy 类型检查

### 6.5 check_doc_consistency.sh 遗漏证据

- `scripts/check_doc_consistency.sh:13-23` 的 `REQUIRED_DOCS` 数组当前含 9 个文档
- ROADMAP_v0.9.0.md 第七节列出 17 项必更文档
- 遗漏: `docs/VISUAL_POLISH_PLAN.md` / `docs/ROADMAP_v0.9.0.md` / `docs/VISUAL_OPTIMIZATION_UNIFIED.md`

---

## 七、教训强化

### 教训 1: 视觉回归测试应与视觉改动同步建立，而非延后

V-01 配置化迁移硬编码值时，V-07 视觉回归测试尚未建立 — 这是经典的"测试滞后"反模式。视觉安全网必须先于视觉改动建立，否则迁移无自动化保障。

### 教训 2: CI 设计应核对现有 job，避免冗余

V-04 提议新建 `benchmark` job，但现有 `ci.yml:239-271` 已有 `benchmark` job — 设计前未充分核查现有 CI 配置。

### 教训 3: 文档类型签名必须与代码一致

V-03 文档 `battle_result: dict` 与代码 `BattleResult @dataclass` 不一致 — 文档设计前必须读取实际代码签名。

### 教训 4: 跨平台视觉测试必须有平台差异化基线策略

V-07 设定 1% 阈值但未考虑 macOS/Linux/Windows 字体渲染差异 — 跨平台视觉测试必须明示平台基线策略 (建议 `SDL_VIDEODRIVER=dummy` 统一渲染管线)。

### 教训 5: PM 评估应主动识别缺失功能

PM 识别出 12 项之外的两个高价值视觉痛点 (V-13 伤害飘字 + V-14 士气视觉化)，这是 CC2 类游戏的核心反馈机制 — PM 评估不应仅评估现有清单，还应主动识别缺失功能。

---

**评估完成日期**: 2026-07-20 | **评估者**: DevSquad 7-Role | **下一步**: Wave B-rev 整合修改建议 + 7-Role 二次共识评估
