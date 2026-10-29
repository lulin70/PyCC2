# PyCC2 与 CC2 原版差距修复方案

> **版本**: v1.0
> **创建日期**: 2026-08-01
> **评审团队**: Product Manager + Architect + Tester（DevSquad 7-Role 协作）
> **评审原则**: 用户体验权重优先 + 投入产出比 + 分阶段落地

---

## 执行摘要

PyCC2 当前状态：v0.9.0（~75% 还原度），6894 测试全绿，Beta Candidate。

**核心问题**：不是功能不够多，而是**已有功能不够健壮**（9/63 地图渲染失败 / 音频崩溃 / 无战斗日志）。

**策略**：先修复破坏性缺陷（阶段 1，16h），再补齐核心玩法（阶段 2，64h），延后打磨型功能（阶段 3，待用户反馈决定）。

---

## 一、差距重新分级（按用户体验影响）

### 🔴 Tier 1: 破坏性体验缺陷（立即修复）

| 差距 | 用户痛点 | 影响范围 | PM 评分 | 修复成本 | ROI |
|------|----------|----------|---------|----------|-----|
| **地图装饰渲染 bug** | 9 张关键地图（arnhem 桥梁战/night_map 夜战）渲染不完整，玩家打开地图直接失败 | 14% 地图（含战役核心关卡） | ⚠️ 10/10 | 1h | ⭐⭐⭐⭐⭐ |
| **CombatLog 缺失** | 玩家无法复盘"为什么我输了"——无法看到伤亡明细/射击记录/命令历史 | 100% 战斗场景 | ⚠️ 9/10 | 8h | ⭐⭐⭐⭐⭐ |
| **音频 bug（3 处）** | 射击无声/环境音崩溃，沉浸感归零（CC2 玩家核心诉求是"二战氛围"） | 100% 战斗场景 | ⚠️ 8/10 | 5h | ⭐⭐⭐⭐ |

**技术细节**：
- 地图装饰 bug: `decoration_renderer.py:60` 访问 dict 属性失败（9 张地图含 `tiles_enhanced` 字段）
- CombatLog: v0.6.x 归档到 `_archive/`，需重新设计订阅 EventBus
- 音频 bug: 
  1. `voice_command_system.py:56` VoiceCommandSystem + SoundSystem API 不匹配
  2. `environmental_audio.py:578` mono array vs 2D 立体声不兼容
  3. `tooltip.py` HIDE_DELAY 死代码

### 🟡 Tier 2: 核心玩法完整性缺陷（1 个月内补齐）

| 差距 | 用户痛点 | 影响战术深度 | PM 评分 | 修复成本 | ROI |
|------|----------|--------------|---------|----------|-----|
| **建筑驻守无加成** | 驻守单位承伤与空地一样，违反 CC2 核心战术（驻守 = 防御 +50%） | 城市战/建筑防御战术失效 | ⚠️ 8/10 | 2h | ⭐⭐⭐⭐⭐ |
| **AI 战术单调** | AI 只会正面冲锋，玩家打 10 场后感觉"AI 是傻子" | 重复可玩性暴降 | ⚠️ 9/10 | 22h | ⭐⭐⭐⭐ |
| **战役剧情缺失** | 玩家不知道"为什么打这场仗"，战役模式变成"无脑刷关" | 战役模式价值减半 | ⚠️ 7/10 | 36h | ⭐⭐⭐ |
| **单位疲劳缺失** | 长距离奔袭后单位仍满速移动，破坏真实感 | 机动战术深度受损 | ⚠️ 6/10 | 4h | ⭐⭐⭐ |

### 🟢 Tier 3: 打磨型差距（3-12 个月，待用户反馈）

| 差距 | PM 评分 | 修复成本 | 优先级判断 |
|------|---------|----------|------------|
| **视觉质量（精灵/地形）** | 6/10 | 80-300h 外包 + $1000 | **延后**（先验证留存率） |
| **多人对战** | 7/10 | 热座 20h / LAN 80h | **延后**（先做热座验证需求） |
| **Mod 支持** | 5/10 | 84h | **延后**（等社区出现） |
| **地图内容调优** | 6/10 | 40h（10 张） | **中期**（调优 10 张代表性地图） |

---

## 二、三阶段落地方案

### 阶段 1: 紧急修复（1-2 周，16h）— 达到真正的 Beta Candidate

**目标**: 修复 Tier 1 破坏性缺陷，确保"玩家能正常玩完一场完整战役"

| 任务 | 工时 | 验收标准 |
|------|------|----------|
| 1. 地图装饰渲染 bug 修复 | 1h | 9 张问题地图全部渲染成功，E2E 测试 2 xfail → pass |
| 2. CombatLog 恢复 | 8h | 右下角日志面板显示伤亡/射击/命令记录，可滚动查看历史 |
| 3. 音频 3 bug 修复 | 5h | 武器音效播放成功，环境音不崩溃，E2E 测试通过 |
| 4. 回归测试 | 2h | 618 E2E 全绿，ruff 0 errors，doc_consistency PASS |

**交付物**: v0.9.1 hotfix 版本
**风险**: 低（修复范围小，E2E 测试覆盖充分）

**实施模式**: DevSquad 11-Phase 项目生命周期
- Phase 1: 需求澄清（确认 3 个 bug 的准确症状）
- Phase 2-3: 架构设计（CombatLog 重新设计）
- Phase 4-5: 开发实现（修复 3 个 bug）
- Phase 6-8: 测试验证（E2E 回归 + 新增测试）
- Phase 9: 文档同步（CHANGELOG + PROJECT_STATUS）
- Phase 10-11: 发布与复盘

---

### 阶段 2: 核心补齐（1 个月，64h）— 达到 85% 还原度

**目标**: 补齐 Tier 2 核心玩法，提升战术深度到"可与原版媲美"

| 任务 | 工时 | 验收标准 |
|------|------|----------|
| 1. 建筑驻守加成 | 2h | 驻守单位 defense_modifier=1.5，E2E 测试验证承伤减少 |
| 2. AI 战术深度提升 | 22h | FlankingAI 调优（2h）+ ReserveManagementAI（8h）+ AdaptiveTacticsAI（12h） |
| 3. 战役剧情系统 | 36h | 16 场战役 briefing/debriefing + S/A/B/C/D 评级 |
| 4. 单位疲劳系统 | 4h | FatigueComponent 累积疲劳，影响移动速度/射击准度 |

**交付物**: v0.10.0 核心完整版
**风险**: 中（AI 战术调优可能需要多次迭代平衡）

---

### 阶段 3: 长期打磨（3-12 个月，视用户反馈决定）

**策略**: 延后所有 Tier 3 任务，先验证留存率和社区反馈

| 条件 | 触发任务 | 投入 |
|------|----------|------|
| 用户反馈"精灵太丑"占比 >30% | 启动视觉打磨 | $1000 + 40h |
| 单人模式周留存率 >60% | 启动热座多人模式 | 20h |
| 社区出现 >10 个自制地图 | 启动 Mod 加载器 | 24h |
| 10 张核心地图评分 >4/5 | 调优其余 53 张地图 | 200h |

---

## 三、关键指标（验收标准）

| 指标 | v0.9.0 基线 | v0.9.1 目标（阶段 1） | v0.10.0 目标（阶段 2） |
|------|-------------|----------------------|------------------------|
| 还原度 | 75% | 78%（修复破坏性缺陷） | 85%（核心机制完整） |
| E2E 测试 | 621 passed / 1 skip / 2 xfail | 624 passed（+3 新测试） | 636 passed（+12 新测试） |
| 玩家可玩地图 | 54/63（9 张渲染失败） | 63/63（100%） | 63/63 + 10 张精调 |
| AI 战术多样性 | 低（仅正面冲锋） | 低 | 高（包抄/预备队/适应） |
| 战役代入感 | 无剧情 | 无剧情 | 有 briefing/debriefing |

---

## 四、风险管理

### 技术风险

| 任务 | 风险 | 缓解措施 |
|------|------|----------|
| CombatLog 恢复 | archive 代码可能与 v0.9.0 EventBus 不兼容 | 重新设计 CombatLogPanel 订阅 EventBus，不复用 archive 代码 |
| AI 战术深度提升 | 新 AI 可能破坏现有平衡性 | 分批上线（先调优 FlankingAI，验证后再加 ReserveAI） |
| 战役剧情系统 | UI 渲染可能影响性能 | briefing/debriefing 用独立 Screen，不与战斗 GameLoop 共用帧 |

### 回归测试保障

所有 Tier 1/2 修复必须有对应 E2E 测试覆盖：

```bash
# 阶段 1 新增测试
pytest tests/e2e/test_combat_log_e2e.py -x -q
pytest tests/e2e/test_map_decoration_rendering_e2e.py -x -q
pytest tests/e2e/test_audio_bugfix_e2e.py -x -q

# 阶段 2 新增测试
pytest tests/e2e/test_building_garrison_bonus_e2e.py -x -q
pytest tests/e2e/test_ai_reserve_management_e2e.py -x -q
pytest tests/e2e/test_campaign_briefing_e2e.py -x -q
pytest tests/e2e/test_unit_fatigue_e2e.py -x -q

# 全量回归
pytest tests/e2e/ -q --timeout=300
```

---

## 五、项目组织

### DevSquad 11-Phase 项目生命周期（阶段 1 应用）

1. **Phase 1: 需求澄清** — 确认 3 个 bug 的准确症状（PM + Tester）
2. **Phase 2: 架构设计** — CombatLog 重新设计（Architect）
3. **Phase 3: 技术方案** — 修复方案详细设计（Architect + Coder）
4. **Phase 4: 开发实现** — 修复 3 个 bug（Coder）
5. **Phase 5: 代码审查** — 代码审查（Architect + Security）
6. **Phase 6: 单元测试** — 单元测试编写（Tester + Coder）
7. **Phase 7: 集成测试** — 集成测试编写（Tester）
8. **Phase 8: E2E 测试** — E2E 测试编写与验证（Tester）
9. **Phase 9: 文档同步** — 更新 CHANGELOG + PROJECT_STATUS（PM + Coder）
10. **Phase 10: 发布** — Git tag v0.9.1（DevOps）
11. **Phase 11: 复盘** — 总结经验教训（All）

### 角色分工（阶段 1）

| 角色 | 职责 | 工时 |
|------|------|------|
| PM | 需求澄清 + 验收标准 + 文档同步 | 2h |
| Architect | 架构设计 + 技术方案审查 | 3h |
| Coder | Bug 修复实现（3 个 bug） | 9h |
| Tester | 测试编写 + 回归验证 | 2h |

---

## 六、后续计划

### 立即行动（本周内）

1. **启动阶段 1**（DevSquad 11-Phase 生命周期）
2. **建立用户反馈渠道**（Discord 服务器 / GitHub Discussions）

### 1 个月内

3. **交付 v0.9.1** — 修复 Tier 1 破坏性缺陷
4. **启动阶段 2** — 补齐 Tier 2 核心玩法

### 延后决策

5. **视觉打磨 / 多人对战 / Mod 支持** — 全部暂缓，待用户反馈

---

## 附录：参考文档

- [PROJECT_STATUS.md](PROJECT_STATUS.md) — 当前项目状态（v0.9.0）
- [ROADMAP.md](ROADMAP.md) — 历史版本演进
- [PRD.md](PRD.md) — 产品需求规格书
- [E2E_REAL_USER_SCENARIOS.md](../tests/e2e/E2E_REAL_USER_SCENARIOS.md) — E2E 测试场景（91 用例）
- [TC_MAPPING.md](../tests/e2e/TC_MAPPING.md) — TC 编号映射表

---

**最后更新**: 2026-08-01
**下次评审**: 阶段 1 完成后（预计 2026-08-08）
