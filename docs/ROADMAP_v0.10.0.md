# PyCC2 v0.10.0 — v1.0 RC 准备 (A Bridge Too Far 前奏)

> **版本**: v0.10.0-plan-rev1 | **创建日期**: 2026-07-25 | **最后更新**: 2026-07-25 | **状态**: 📋 规划中 (待用户审核)
> **方法**: DevSquad V4.1.7 7-Role 共识 | **SemVer**: MINOR (用户可见新功能 + 性能优化)
> **来源**: [PRD.md](PRD.md) L28-33 四层目标 + [ROADMAP.md](ROADMAP.md) L301 v1.0-beta 目标

---

## 一、版本定位

### 1.1 路线图坐标

```
v0.9.0 (Oosterbeek) ──→ v0.10.0 (v1.0 RC 准备) ──→ v1.0-beta (A Bridge Too Far)
   视觉打磨完成              v1.0 发布候选准备            Full release candidate
   6819 tests                7500+ tests                 ≥8000 tests
   72.64% coverage           75%+ coverage               ≥80% coverage
   ~75% CC2 fidelity         ~85% CC2 fidelity           ≥95% CC2 fidelity
```

### 1.2 v0.10.0 核心目标

| 目标 | 当前 (v0.9.0) | v0.10.0 目标 | v1.0 目标 | 差距分析 |
|------|---------------|--------------|-----------|----------|
| CC2 保真度 | ~75% | ~85% | ≥95% | Mechanics 80%→90% / Visual 70%→85% |
| 测试用例数 | 6819 | 7500+ | ≥8000 | +681 新测试 (覆盖 Should 项 + 边界) |
| 覆盖率 | 72.64% | 75%+ | ≥80% | +2.36% (Should 项补全) |
| Should 项完成度 | 待评估 | 9/9 | 9/9 | 补全剩余 Should 项 |
| NFR-PERF 验证 | 部分 | 8/8 | 8/8 | 完整验证 8 条性能需求 |
| 打包分发 | 无 | .app/.dmg | .app/.dmg + 签名 | macOS 打包 + 安装器 |

### 1.3 不在 v0.10.0 范围

- **Won't 项** (8项, PRD L323): 多人联机、3D渲染、物理引擎、语音聊天、Steam成就、云存档、编辑器工具、Linux/Windows支持
- **Could 项** (5项, PRD L321): 回放系统、Mod支持、载具系统完整、物理 debris、天气系统 (推迟到 v1.1/v2.0)
- **新战役**: Market Garden 之外的战役 (推迟到 v1.0+)

---

## 二、7-Role 共识表

| 角色 | 投票 | 置信度 | 关键意见 |
|------|------|--------|----------|
| Architect | APPROVE | 高 | v1.0 RC 准备定位清晰,聚焦 Should 项 + 保真度提升,无架构重写 |
| PM | APPROVE | 高 | 基于 PRD MoSCoW 矩阵,Should 项是 v1.0 必备,v0.10.0 补全合理 |
| Security | APPROVE | 高 | 打包分发需注意代码签名 + 公证 (macOS notarization) |
| Tester | APPROVE | 高 | 7500+ tests 目标合理 (+681 新测试),NFR-PERF 8 条验证补全 |
| Coder | APPROVE | 高 | Should 项实现工作量中等,无高风险技术点 |
| DevOps | APPROVE | 高 | .app/.dmg 打包需 py2app/pyinstaller + CI 集成 |
| UI Designer | APPROVE | 高 | Visual fidelity 70%→85% 需对照 CC2 原作像素级校准 |

**共识结论**: ✅ 通过 (7/7 APPROVE) → 推进 v0.10.0 规划

---

## 三、Wave 推进计划

### Wave A: CC2 保真度提升 (Mechanics 80%→90%, Visual 70%→85%)

| 子项 | 优先级 | 说明 | 验证 |
|------|--------|------|------|
| A1: 武器数据校准 | P1 | 对照 CC2 原作校准 69 种武器的伤害/射程/精度/装弹时间 | 单元测试 + 数据对比 |
| A2: 单位属性校准 | P1 | 对照 CC2 原作校准 277 个单位模板的 HP/装甲/移动速度/视野 | 单元测试 + 数据对比 |
| A3: AI 行为校准 | P1 | 对照 CC2 原作校准 AI 决策树/反应时间/战术选择 | E2E + 行为对比测试 |
| A4: 视觉细节校准 | P2 | 对照 CC2 原作校准单位立绘/地形纹理/UI 配色 | 视觉回归测试 |
| A5: 音效校准 | P2 | 对照 CC2 原作校准武器/环境/操作音效 | 音频回放测试 |

### Wave B: Should 项补全 (PRD L320, 9 项)

| 子项 | 优先级 | 说明 | 当前状态 |
|------|--------|------|----------|
| B1: 支援火力(迫击炮) | P1 | 实现迫击炮单位 + 弹道 + 支援请求 UI | 待评估 |
| B2: 载具乘员 | P1 | 实现载具乘员上下车 + 载具损毁 + 乘员伤亡 | 待评估 |
| B3: 战役模式(多关/继承) | P1 | 实现多关卡战役 + 单位继承 + 战役进度保存 | 待评估 |
| B4: 音效反馈(操作/事件) | P1 | 实现操作音效 + 事件音效 + 音量控制 | 待评估 |
| B5: A*路径平滑 | P2 | 实现 A* 路径平滑算法 (catmull-rom / bezier) | 待评估 |
| B6: Debug Overlay 三级 | P2 | 实现 Debug Overlay 三级切换 (简洁/详细/完整) | 待评估 |
| B7: 小地图 | P2 | 实现小地图 (V-11 已完成基础,需增强) | ✅ 部分完成 |
| B8: 快捷键完整 | P2 | 实现完整快捷键系统 (V-08 已完成基础,需增强) | ✅ 部分完成 |
| B9: 单位面板详细信息 | P2 | 实现单位面板详细信息 (武器/属性/状态) | 待评估 |

### Wave C: 性能优化 (NFR-PERF 8 条验证)

| 子项 | NFR | 目标 | 验证方法 |
|------|------|------|----------|
| C1: PERF-01 | 64x64+20单位 ≥30FPS 逻辑帧率 | ≥30 FPS | benchmark + FPS 计数器 |
| C2: PERF-02 | 128x128+50单位 ≥20FPS | ≥20 FPS | benchmark + FPS 计数器 |
| C3: PERF-03 | 启动时间 ≤3秒 | ≤3s | cold start benchmark |
| C4: PERF-04 | 内存占用 ≤500MB | ≤500MB | memory profiler |
| C5: PERF-05 | FPS 渲染帧率 60FPS | ≥60 FPS | FPS 计数器 |
| C6: PERF-06 | A*寻路(128x128) ≤50ms | ≤50ms | pathfinding benchmark |
| C7: PERF-07 | FoW更新(50单位) ≤10ms/次 | ≤10ms | FoW benchmark |
| C8: PERF-08 | 存档写入 ≤1s / 读取 ≤500ms | ≤1s/500ms | save/load benchmark |

### Wave D: 测试覆盖扩展 (6819 → 7500+)

| 子项 | 优先级 | 说明 | 目标 |
|------|--------|------|------|
| D1: Should 项测试 | P1 | Wave B 每个子项配套单元/集成测试 | +400 tests |
| D2: 保真度测试 | P1 | Wave A 数据校准配套对比测试 | +150 tests |
| D3: 性能基准测试 | P2 | Wave C NFR-PERF 配套基准测试 | +80 tests |
| D4: E2E 扩展 | P2 | 真实玩家旅程扩展 (Should 项场景) | +50 tests |
| D5: 边界/异常测试 | P2 | 边界条件 + 异常输入测试 | +50 tests |

### Wave E: 打包分发准备 (.app/.dmg)

| 子项 | 优先级 | 说明 |
|------|--------|------|
| E1: py2app/pyinstaller 配置 | P1 | 配置打包脚本 + 资源打包 |
| E2: macOS 代码签名 | P1 | Developer ID 代码签名 |
| E3: macOS 公证 (notarization) | P1 | Apple 公证流程 |
| E4: .dmg 安装器 | P2 | create-dmg 生成 .dmg 安装器 |
| E5: GitHub Release 集成 | P2 | CI 自动生成 Release + 上传 .dmg |

### Wave F: 验证与发布

| 子项 | 说明 |
|------|------|
| F1: ruff + mypy + radon + check_doc_consistency 全绿 | 含 P3-1 增强 |
| F2: 全量 pytest 零回归 + e2e 真实用户旅程 | 目标 7500+ passed |
| F3: 版本号 0.9.0 → 0.10.0 + 文档同步 (MINOR) | SemVer MINOR |
| F4: Git commit + push + GitHub Release | feat + chore 模式 |
| F5: CarryMem 记录 v0.10.0 完成 | 教训强化 |

---

## 四、11-Phase 生命周期映射

| Phase | 名称 | 负责角色 | 状态 | 说明 |
|-------|------|----------|------|------|
| P1 | 需求分析 | PM | 📋 规划中 | 基于 PRD MoSCoW Should 项 |
| P2 | 架构设计 | Architect | 📋 规划中 | 无架构重写,扩展实现 |
| P3 | 技术设计 | Architect+Coder | 📋 规划中 | 待 Wave A/B 细化 |
| P5 | 交互设计 | UI | 📋 规划中 | Visual fidelity 校准方案 |
| P7 | 测试计划 | Tester | 📋 规划中 | +681 新测试分布 |
| P8 | 实施 | Coder | 📋 规划中 | Wave A/B/C/D/E |
| P9 | 测试执行 | Tester | 📋 规划中 | Wave F1-F2 |
| P10 | 部署发布 | DevOps | 📋 规划中 | Wave F3-F4 + GitHub Release |
| P11 | 运维保障 | DevOps+Sec | 📋 规划中 | Wave F5 |

---

## 五、验收标准

### 5.1 功能验收 (Wave A + B)

- [ ] A1-A5: CC2 保真度提升至 ~85% (Mechanics 90% / Visual 85%)
- [ ] B1-B9: Should 项 9/9 全部完成 (含 B7/B8 增强完成)

### 5.2 质量验收

- [ ] ruff check: 0 errors
- [ ] mypy: 0 errors
- [ ] radon cc: 0 D+ 新增函数 (baseline=18)
- [ ] check_doc_consistency.sh: 全部 PASS (含 P3-1 增强)
- [ ] pytest: 7500+ passed 零回归
- [ ] e2e: 全部通过 (含 Should 项场景)
- [ ] NFR-PERF 8/8 全部达标

### 5.3 文档验收 (活文档原则)

- [ ] VERSION / pyproject.toml / __init__.py: 0.10.0
- [ ] README.md / README_zh.md / README_ja.md: 0.10.0 + 新特性描述
- [ ] docs/PRD.md / DESIGN.md / ROADMAP.md / TECH_DEBT.md / TEST_PLAN.md / PROJECT_STATUS.md: 0.10.0 同步
- [ ] CHANGELOG.md: v0.10.0 完整条目
- [ ] docs/ROADMAP_v0.10.0.md: 状态改为 ✅ 完成 + 完成总结
- [ ] docs/archive/CONSENSUS_V0_10_0.md: 7-Role 共识归档

### 5.4 发布验收

- [ ] macOS .app 包生成成功
- [ ] macOS 代码签名 + 公证完成
- [ ] .dmg 安装器生成成功
- [ ] GitHub Release 发布 + .dmg 上传

---

## 六、风险与缓解

| 风险 | 概率 | 影响 | 缓解策略 |
|------|------|------|----------|
| CC2 原作数据获取困难 | 中 | 高 | 优先使用已有数据 + 社区资源 + 用户提供的 CC2 数据 |
| Should 项工作量超预期 | 中 | 中 | 按 P1/P2 优先级分批实施,必要时推迟 P2 到 v1.0 |
| macOS 打包签名问题 | 中 | 中 | 提前申请 Developer ID + 测试公证流程 |
| 性能优化引入回归 | 低 | 中 | benchmark 前后对比 + 性能回归测试 |
| 测试覆盖扩展导致 CI 变慢 | 中 | 低 | 标记 @slow + 调整 CI 超时 |

---

## 七、下一步行动

1. **用户审核本规划文档** — 确认 v0.10.0 范围与优先级
2. **Should 项现状评估** — B1-B9 逐项评估当前完成度 (待评估 → 已完成/部分完成/未开始)
3. **CC2 原作数据收集** — 确认数据来源与获取方式
4. **Wave A/B 细化技术设计** — P3 阶段细化实施方案
5. **启动 Wave A** — CC2 保真度提升 (P1 优先)

---

> **注**: 本规划基于 [PRD.md](PRD.md) L28-33 四层目标 + [ROADMAP.md](ROADMAP.md) L301 v1.0-beta 目标。
> v0.10.0 是 v1.0 RC 准备版本,聚焦 Should 项补全 + 保真度提升 + 打包分发准备。
> 详细的 Wave 实施方案需在 P3 技术设计阶段细化。
