# ROADMAP v0.7.7 — P2 技术债清理: F 级函数重构 + radon baseline 配置化 (PATCH)

**Status**: ✅ 完成
**Created**: 2026-07-18
**Completed**: 2026-07-18
**Version**: 0.7.7 (PATCH — 重构 4 个高复杂度函数 + CI 配置化，无新功能)
**Prev**: v0.7.6 TD-077 ORPHAN 全清 (75 集成测试, 6291 passed)

## 完成总结

v0.7.7 完成 P2 技术债清理: 4 个 F 级圈复杂度函数重构 (cc 降幅 72-95%) + radon baseline 配置化 (CI 硬编码迁移至 pyproject.toml)。DevSquad 7-Role 共识 7/7 通过，全量 6291 passed 零回归。

### Wave C: P2-1 重构 4 个高复杂度函数 (Coder) — ✅ 完成

| 函数 | 文件 | cc 前 | cc 后 | 降幅 | 测试 |
|------|------|-------|-------|------|------|
| `generate_road` | terrain_tiles_road.py | 115 | 6 | -94.8% | 348 passed |
| `handle_player_command` | combat_director.py | 73 | 4 | -94.5% | 933 passed |
| `generate_orders` | commander_ai.py | 68 | 19 | -72% | 73 passed |
| `draw_units` | unit_renderer.py | 63 | 14 | -78% | 257 passed |

### Wave D: P2-2 radon baseline 配置化 (DevOps) — ✅ 完成

- `pyproject.toml` 新增 `[tool.radon] cc_baseline = 18` + `min_grade = "C"`
- `.github/workflows/ci.yml` L61 改为从 pyproject.toml 读取 (单点维护)
- E+ violations 22→18 (减少 4 个正好是重构的函数)

### Wave F: 全量验证 (Tester/DevOps) — ✅ 完成

- `pytest tests/ -m "not slow"`: 6291 passed, 2 skipped, 18 deselected (60.01s) 零回归
- `pytest` 4 重构文件 + E2E: 697 passed (38.56s) 行为保持一致
- `pytest tests/benchmark/`: 21 passed (7.92s) 性能无回归
- `ruff check .`: All checks passed
- `ruff format --check .`: 4 重构文件 reformat 后通过
- `mypy -p pycc2`: Success: no issues found in 374 source files (清理 .mypy_cache 后真实结果)
- `radon cc src/ -n E`: 18 E+ violations (匹配 pyproject.toml cc_baseline=18)
- `check_doc_consistency.sh`: 11/11 PASS

### Wave E: P3 项方案设计 — ⬜ 待用户决策 (P3 项需产品决策，非 v0.7.7 范围)

P3 项 (视觉/平衡/难度) 需要产品决策与用户反馈，不属于 v0.7.7 P2 技术债清理范围。后续将基于用户反馈单独推进。

## 1. 背景与目标

### 1.1 触发原因

v0.7.6 项目整理评估发现 13 个 F 级复杂度函数（radon cc F），其中 4 个 cc >= 60 属于高优先级技术债：
- `generate_road` (cc=115) — 像素艺术道路生成
- `handle_player_command` (cc=73) — 玩家命令分发
- `generate_orders` (cc=68) — AI 指挥官命令生成
- `draw_units` (cc=63) — 单位渲染

### 1.2 SemVer 偏离说明

按用户决策，v0.7.7 定位为 PATCH（仅第三位递增）。理由：纯重构无新功能，行为不变，有测试保障。

### 1.3 7-Role 共识

| Role | 立场 | 关键意见 |
|------|------|----------|
| Architect | ✅ 同意 | dispatch 模式 + 辅助方法提取符合 SRP，不破坏 DDD 4 层 |
| PM | ✅ 同意 | 无用户可见变化，风险可控 |
| Security | ✅ 同意 | 纯重构无安全影响 |
| Tester | ✅ 同意 | 行为不变，现有测试保障回归，新增单元测试保障辅助方法 |
| Coder | ✅ 同意 | Surgical Changes，每个函数独立重构可回滚 |
| DevOps | ✅ 同意 | radon baseline 配置化降低 CI 维护成本 |
| UI | ⚠️ 关注 | generate_road/draw_units 是渲染函数，需视觉回归验证 |

**共识结论**: 7/7 通过（UI 关注点通过视觉回归测试保障）

## 2. 执行清单

### Wave C: P2-1 重构 4 个高复杂度函数 (Coder)

#### C1: `generate_road` (cc=115 → 目标 <30)

- **文件**: `src/pycc2/presentation/rendering/terrain_tiles_road.py`
- **方案**: 提取 `_generate_horizontal_road(size, neighbors)` + `_generate_vertical_road(size, neighbors)` 两个辅助函数；每个内部提取 `_draw_curbs()`, `_draw_edge_fade()`, `_draw_tire_tracks()` 等私有方法
- **风险**: 渲染输出可能变化 → 用 `tests/unit/test_terrain_tile_generator.py` 现有测试 + 新增像素采样测试保障
- **验证**: 像素采样对比重构前后输出

#### C2: `handle_player_command` (cc=73 → 目标 <20)

- **文件**: `src/pycc2/services/combat_director.py`
- **方案**: 10 个 elif 分支提取为 `_cmd_attack()`, `_cmd_move()`, `_cmd_take_cover()`, `_cmd_stop()`, `_cmd_defend()`, `_cmd_fast_move()`, `_cmd_sneak()`, `_cmd_hide()`, `_cmd_deploy_smoke()` 私有方法；用 dispatch 字典路由
- **风险**: 低（纯重构，行为不变）
- **验证**: `tests/unit/test_combat_director.py` + `tests/e2e/test_battle_flow_e2e.py`

#### C3: `generate_orders` (cc=68 → 目标 <25)

- **文件**: `src/pycc2/domain/ai/commander_ai.py`
- **方案**: 3 个 threat level 分支提取为 `_orders_for_critical()`, `_orders_for_high()`, `_orders_for_medium()` 方法
- **风险**: 中（AI 决策逻辑）
- **验证**: `tests/unit/test_commander_ai.py` + `tests/e2e/test_ai_behaviors_e2e.py`

#### C4: `draw_units` (cc=63 → 目标 <25)

- **文件**: `src/pycc2/presentation/rendering/unit_renderer.py`
- **方案**: 提取 `_compute_unit_screen_position(unit, camera, position_overrides, idx)` + `_draw_unit_by_type(unit, cx, cy, ...)` 方法
- **风险**: 中（渲染逻辑）
- **验证**: `tests/unit/test_unit_renderer.py` + `tests/e2e/test_visual_smoke.py`

### Wave D: P2-2 radon baseline 配置化 (DevOps)

- **文件**: `.github/workflows/ci.yml` L61 + `pyproject.toml`
- **方案**: 在 `pyproject.toml` 新增 `[tool.radon]` 段 `cc_baseline = 23`；ci.yml 从 pyproject.toml 读取
- **验证**: CI 本地模拟运行

### Wave E: P3 项方案设计 (PM + Architect)

P3 项（视觉/音频打磨、平衡性调整、难度曲线优化）需要产品决策，给方案不实施：
- **P3-1 视觉/音频打磨**: 基于用户反馈的视觉问题清单 + 音频缺失清单
- **P3-2 平衡性调整**: 基于E2E测试数据的平衡性报告
- **P3-3 难度曲线**: 新手引导设计 + 难度递进方案

### Wave F: 全量验证 + Git push (Tester/DevOps)

- `pytest tests/ -m "not slow"`: 确认 6291+ passed 零回归
- `pytest tests/e2e/`: 确认 503+ passed
- `pytest tests/benchmark/test_performance_baseline.py`: 性能无回归
- `ruff check .` + `ruff format --check .`
- `mypy -p pycc2`
- `radon cc src/ -n F`: 确认 F 级函数数减少
- `check_doc_consistency.sh`: 11/11 PASS
- 版本号 0.7.6 → 0.7.7 + 文档同步
- Git commit + push

## 3. 11-Phase 生命周期映射

| Phase | 状态 | 备注 |
|-------|------|------|
| 1. Discover | ✅ | v0.7.6 评估发现 |
| 2. Plan | ✅ | 本文档 |
| 3. Design | ✅ | 重构方案已定 |
| 4. Consensus | ✅ | 7/7 通过 |
| 5. Document | ✅ | 本文档 |
| 6. Implement | 🚧 | Wave C + D |
| 7. Test | ⬜ | Wave F |
| 8. Review | ⬜ | Wave F |
| 9. Document | ⬜ | Wave F 文档同步 |
| 10. Deploy | ⬜ | Wave F Git push |
| 11. Learn | ⬜ | Wave F CarryMem |

## 4. 验收标准

- 4 个高复杂度函数 cc 降至目标值以下
- radon F 级函数总数从 13 降至 9 以下（4 个重构 + 其他不变）
- 全量测试 6291+ passed 零回归
- E2E 503+ passed
- 性能测试 13 passed 无回归
- ruff 0 + mypy 0 + check_doc_consistency 11/11
- 版本号 0.7.7 + 文档同步
