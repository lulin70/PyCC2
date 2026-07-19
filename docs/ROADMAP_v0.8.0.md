# ROADMAP v0.8.0 — P3-3 难度曲线: AI 难度缩放全覆盖 + 新手引导增强 (MINOR)

**Status**: ✅ 完成
**Created**: 2026-07-18
**Completed**: 2026-07-18
**Version**: 0.8.0 (MINOR — 新增战术教学引导 + AI 难度缩放覆盖 9/9 模块，向后兼容)
**Prev**: v0.7.7 P2 技术债清理 (4 F 级函数重构 + radon baseline 配置化, 6291 passed)

## 完成总结

v0.8.0 完成 P3-3 难度曲线推进: AI 难度缩放覆盖率 7/9 → 9/9 模块 + TutorialStep 6→10 步 (新增 4 步战术教学) + 新增 10 个难度缩放测试。DevSquad 7-Role 共识 7/7 通过，全量 6301 passed 零回归。

### Wave C: AI 难度缩放全覆盖 (Coder) — ✅ 完成

| 模块 | 文件 | 接入参数 | 测试 |
|------|------|---------|------|
| recon_ai | recon_ai.py | perception_accuracy, tactical_variety, aggressiveness | 57 passed |
| supply_awareness_ai | supply_awareness_ai.py | perception_accuracy, aggressiveness, vision_range_multiplier, tactical_variety | 42 passed |

### Wave D: 新手引导系统增强 (Coder + UI) — ✅ 完成

- `tutorial_system.py` 新增 4 步战术教学: USE_COVER / SMOKE_GRENADE / FLANKING / SUPPRESSION
- 51 unit tests + 26 e2e tests 全通过

### Wave E: AI 难度缩放测试套件 (Tester) — ✅ 完成

- 新增 `tests/unit/ai/test_difficulty_scaling.py` (10 测试用例)
- 覆盖: recon_ai 难度响应 + supply_awareness_ai 难度响应 + 4 级难度参数递进

### Wave F: 全量验证 (Tester/DevOps) — ✅ 完成

- `pytest tests/ -m "not slow"`: 6301 passed, 2 skipped, 18 deselected (108.72s) 零回归
- `ruff check .`: All checks passed
- `ruff format --check .`: 623 files already formatted
- `mypy -p pycc2`: Success: no issues found in 374 source files
- `radon cc src/ -n E`: 18 E+ violations (与 baseline 一致，无新增)
- `check_doc_consistency.sh`: 11/11 PASS

## 1. 背景与目标

### 1.1 触发原因

v0.7.7 项目评估发现 P3-3 难度曲线缺口:
- AI 行为模块对 DifficultySystem 的集成覆盖 7/9 (recon_ai + supply_awareness_ai 未接入)
- 新手引导仅 6 步基础操作 (选/移/攻/胜利)，缺少战术教学 (掩体/烟雾/侧翼/压制)
- 缺少难度曲线设计文档 (每级学习目标 + 参数递进逻辑)

### 1.2 SemVer 说明

v0.8.0 定位为 MINOR（第二位递增）。理由:
1. 新增 TutorialStep 4 步战术教学引导 (用户可见新功能)
2. 新增 AI 难度缩放覆盖 (影响游戏行为)
3. 向后兼容: 现有 savegame/API 不受影响，仅参数化扩展

### 1.3 现状调研 (2026-07-18)

#### AI 模块 DifficultySystem 集成现状

| 模块 | 文件 | 已接入参数 | 缺口 |
|------|------|-----------|------|
| tactical_flanking | tactical_flanking.py | use_flanking, aggressiveness | - |
| tactical_suppression | tactical_suppression.py | use_suppression_tactics, suppress_effectiveness | - |
| tactical_coordination | tactical_coordination.py | coordination_enabled, aggressiveness | - |
| smoke_tactical_ai | smoke_tactical_ai.py | aggressiveness | - |
| at_ambush_ai | at_ambush_ai.py | aggressiveness | - |
| combat_engagement | combat_engagement.py | aggressiveness, base_hit_chance, ammo_conservation | - |
| commander_ai | commander_ai.py | (通过 TacticalContext) | - |
| **recon_ai** | recon_ai.py | ❌ 未接入 | _MIN_EXPECTED_ENEMY_FACTOR=0.5, _MAX_RECON_PER_TICK=3 硬编码 |
| **supply_awareness_ai** | supply_awareness_ai.py | ❌ 未接入 | _THREAT_THRESHOLD=0.3, _ATTACK_ADVANTAGE_THRESHOLD=1.5, _SUPPLY_SCAN_RADIUS=8 硬编码 |

#### 新手引导现状

- `TutorialStep` 6 步: WELCOME / SELECT_UNIT / MOVE_UNIT / ATTACK_ENEMY / VICTORY_CONDITIONS / COMPLETE
- 缺少战术教学: 掩体使用、烟雾弹、侧翼包抄、压制火力

### 1.4 7-Role 共识 (2026-07-18 评估)

| Role | 立场 | 关键意见 |
|------|------|----------|
| Architect | ✅ 同意 | recon/supply_awareness 接入方式与已接入模块一致 (context.difficulty_config)，符合 DDD 4 层架构 |
| PM | ✅ 同意 | 新手引导扩展影响新用户留存，AI 难度差异化提升游戏深度，价值高 |
| Security | ✅ 同意 | 无安全影响 (纯游戏逻辑，无外部输入) |
| Tester | ✅ 同意 | 新增 test_difficulty_scaling.py 验证每级 AI 行为差异，现有测试 fallback 兼容 |
| Coder | ✅ 同意 | Surgical Changes: 仅修改 2 个 AI 模块 + tutorial_system.py，可回滚 |
| DevOps | ✅ 同意 | 无部署影响，无 CI 配置变化 |
| UI | ✅ 同意 | TutorialStep 扩展仅新增 STEPS 字典条目，渲染逻辑不变，视觉回归保障 |

**共识结论**: 7/7 通过

## 2. 执行清单

### Wave A: 创建设计文档 (Architect + PM)

- **A1**: 创建 `docs/DIFFICULTY_CURVE.md` — 难度曲线设计文档
  - 4 级难度 (EASY/MEDIUM/HARD/VETERAN) 学习目标
  - DifficultyConfig 参数递进逻辑
  - 新手引导扩展规划 (6→10 步)
- **A2**: 创建 `docs/ROADMAP_v0.8.0.md` — 本推进计划

### Wave B: DevSquad 7-Role 共识评估 (All Roles)

- 调用 DevSquad 7-Role 并行评估 v0.8.0 方案
- 共识结论记录到 ROADMAP_v0.8.0.md

### Wave C: AI 难度缩放全覆盖 (Coder)

#### C1: recon_ai.py 接入 DifficultyConfig

- **文件**: `src/pycc2/domain/ai/recon_ai.py`
- **方案**:
  - `evaluate()` 中通过 `context.difficulty_config` 获取参数
  - `_MIN_EXPECTED_ENEMY_FACTOR` 根据 `perception_accuracy` 调整 (低难度 → 期望敌人更少)
  - `_MAX_RECON_PER_TICK` 根据 `tactical_variety` 调整 (低难度 → 更少侦察)
  - 评分权重根据 `aggressiveness` 调整 (低 aggressiveness → 更重视防御姿态)
- **风险**: 低 (仅影响 AI 侦察频率，不影响战斗)
- **验证**: `tests/unit/test_recon_ai.py` + 新增 `test_difficulty_scaling.py`

#### C2: supply_awareness_ai.py 接入 DifficultyConfig

- **文件**: `src/pycc2/domain/ai/supply_awareness_ai.py`
- **方案**:
  - `_THREAT_THRESHOLD` 根据 `perception_accuracy` 调整 (低难度 → 阈值更高，反应更慢)
  - `_ATTACK_ADVANTAGE_THRESHOLD` 根据 `aggressiveness` 调整 (低难度 → 需要更大优势才攻击)
  - `_SUPPLY_SCAN_RADIUS` 根据 `vision_range_multiplier` 调整
  - `_MAX_SUPPLY_ORDERS_PER_TICK` 根据 `tactical_variety` 调整
- **风险**: 中 (影响补给防御决策)
- **验证**: `tests/unit/test_supply_awareness_ai.py` + 新增 `test_difficulty_scaling.py`

### Wave D: 新手引导系统增强 (Coder + UI)

#### D1: 扩展 TutorialStep 从 6 步到 10 步

- **文件**: `src/pycc2/presentation/ui/tutorial_system.py`
- **新增步骤** (在 ATTACK_ENEMY 和 VICTORY_CONDITIONS 之间):
  - `USE_COVER` — 教学掩体使用 (树林/建筑提供掩护但减速)
  - `SMOKE_GRENADE` — 教学烟雾弹 (按 G 部署烟雾遮蔽视线)
  - `FLANKING` — 教学侧翼包抄 (从侧面攻击敌人效果更好)
  - `SUPPRESSION` — 教学压制火力 (MG 单位可压制敌人降低其还击精度)
- **风险**: 低 (仅扩展 STEPS 字典，渲染逻辑不变)
- **验证**: `tests/unit/test_tutorial_system.py` + 视觉回归

### Wave E: AI 难度缩放测试套件 (Tester)

#### E1: 新增 tests/unit/ai/test_difficulty_scaling.py

- **文件**: `tests/unit/ai/test_difficulty_scaling.py`
- **测试用例**:
  - `test_easy_ai_recon_frequency_lower` — EASY 难度侦察频率 < VETERAN
  - `test_easy_ai_supply_threshold_higher` — EASY 难度补给威胁阈值 > VETERAN
  - `test_easy_ai_attack_advantage_threshold_higher` — EASY 难度攻击优势阈值 > VETERAN
  - `test_veteran_ai_recon_scan_wider` — VETERAN 难度补给扫描半径 > EASY
  - `test_difficulty_levels_progressive` — 4 级难度参数递进验证
  - `test_recon_ai_respects_perception_accuracy` — 侦察 AI 响应 perception_accuracy
  - `test_supply_ai_respects_vision_range` — 补给 AI 响应 vision_range_multiplier
- **验证**: pytest tests/unit/ai/test_difficulty_scaling.py

### Wave F: 全量验证 + Git push (Tester + DevOps)

- `pytest tests/ -m "not slow"`: 确认 6291+ passed 零回归 (允许新增测试增加总数)
- `pytest tests/unit/ai/test_difficulty_scaling.py`: 新增测试全通过
- `pytest tests/e2e/`: E2E 行为一致
- `pytest tests/benchmark/`: 性能无回归
- `ruff check .` + `ruff format --check .`
- `mypy -p pycc2`
- `radon cc src/ -n E`: 确认无新增 E+ 违规
- `check_doc_consistency.sh`: 11/11 PASS
- 版本号 0.7.7 → 0.8.0 + 文档同步
- Git commit + push

### Wave G: CarryMem 记录

- 记录 v0.8.0 完成总结到 CarryMem
- 更新 project_memory.md (如有新教训)

## 3. 11-Phase 生命周期映射

| Phase | 状态 | 备注 |
|-------|------|------|
| 1. Discover | ✅ | v0.7.7 评估发现 P3-3 缺口 |
| 2. Plan | ✅ | 本文档 |
| 3. Design | ✅ | DIFFICULTY_CURVE.md |
| 4. Consensus | ⏳ | Wave B 7-Role 评估 |
| 5. Document | ✅ | 本文档 + DIFFICULTY_CURVE.md |
| 6. Implement | ⏳ | Wave C + D |
| 7. Test | ⏳ | Wave E + F |
| 8. Review | ⏳ | Wave F |
| 9. Document | ⏳ | Wave F 文档同步 |
| 10. Deploy | ⏳ | Wave F Git push |
| 11. Learn | ⏳ | Wave G CarryMem |

## 4. 验收标准

- AI 难度缩放覆盖率从 7/9 提升到 9/9 模块
- TutorialStep 从 6 步扩展到 10 步 (新增 4 步战术教学)
- 新增 test_difficulty_scaling.py ≥7 个测试用例全通过
- 全量测试 6291+ passed 零回归
- ruff 0 + mypy 0 + check_doc_consistency 11/11
- 版本号 0.8.0 + 文档同步 (16+ 文件)
- DIFFICULTY_CURVE.md 设计文档完整 (4 级难度学习目标 + 参数递进)
