# PyCC2 项目成熟度评估 D14 (2026-07-05)

## 评估概览

| 维度 | D14 评分 | D14 等级 | D13 对比 |
|------|----------|----------|----------|
| 1. 架构 | 7/10 | B- | → (D13: 7/B-) |
| 2. 安全 | 7/10 | B- | → (D13: 7/B-) |
| 3. 测试 | 8/10 | B | ↑ (D13: 7.5/B) |
| 4. 性能 | 8/10 | B+ | → (D13: 8/B+) |
| 5. 可维护性 | 7.5/10 | B- | ↑ (D13: 7/B-) |
| 6. 文档 | 7.5/10 | B- | ↑ (D13: 7/B-) |
| 7. 集成 | 8/10 | B+ | → (D13: 8/B+) |
| CI/CD | 7.5/10 | B- | ↓ (D13: 8/B+) |
| 目录 | 7.5/10 | B | → (D13: 7.5/B) |
| **总分** | **7.6/10** | **B-** | ↑ (D13: 7.4/B-) |

**评估方法**: DevSquad V3.8 "项目整理评估" — 7 维度代码走读 + 文档一致性 + 技术债清理 + 测试完整性 + CI/CD 检查 + 目录清理 + 诚实成熟度评分。

**评估基线**: v0.4.3, commit d248cf4 (batch 4b 完成), 2026-07-05

**评分变动原因**: +100 TacticExecutor 单测提升测试维度；3 个幽灵模块清理提升可维护性；版本号三处同步提升文档维度；CI ruff format 漂移导致 CI/CD 降分（pre-commit hooks 陈旧）。

---

## D14 修复清单（本次评估期间完成）

| # | 问题 | 优先级 | 修复 | 验证 |
|---|------|--------|------|------|
| F-1 | CI ruff format --check 漂移（7 文件需重格式化） | P0 | `ruff format` 应用 7 文件 | `ruff format --check .` 585 files already formatted ✅ |
| F-2 | xfail strict=False 隐藏 XPASS 测试（test_vl_flag_rendering.py:334） | P1 | 移除 `@pytest.mark.xfail` 装饰器 | 测试在 combined suite 正常通过 ✅ |
| F-3 | 文档测试计数陈旧（4473 vs 实际 4573） | P1 | README/zh/ja + SKILL + CHANGELOG 同步 4473→4573 | `grep 4473 README*.md SKILL.md` 无残留 ✅ |
| F-4 | 3 个幽灵模块残留（command_bar.py / visual_effects.py / command.py） | P1 | DeleteFile 删除 3 文件 | `grep -r "from ...command_bar\|visual_effects\|input.command" src/` 无匹配 ✅ |
| F-5 | E2E 文档引用断链（E2E_REAL_USER_SCENARIOS.md:1128 引用不存在的 VisualEffects 类） | P2 | 更新 import 为 `cc2_combat_effects.CC2ExplosionEffect, EnhancedParticleSystem` | 文档引用类真实存在 ✅ |
| F-6 | 版本号三处不一致（VERSION/pyproject.toml/__init__.py = 0.4.0 vs 实际 0.4.3） | P1 | 三处同步为 0.4.3 | `cat VERSION` = 0.4.3 ✅ |

---

## 维度1: 架构 (7/10) — 持平

### 状态
- ✅ 390 模块零循环依赖，DDD 4 层结构清晰
- ✅ TacticExecutor facade + 7 mixin 拆分完成（v0.4.3 batch 1-4b 单测补齐后安全网就绪）
- ✅ 3 个幽灵模块清理（command_bar.py / visual_effects.py / command.py — 累计 14 个 ghost 已全部清理）

### 残留技术债（未变动）
- ⚠️ **5 个 God Class >800L**: enhanced_sound_bridge.py (949L) / terrain_rendering_system.py (896L) / vehicle_weapon_profiles.py (826L) / hud_renderer.py (886L) / environmental_audio.py (811L) — v0.5+ 按真实职责评估
- ⚠️ TYPE_CHECKING 守卫 182 文件（mixin 模式必要 workaround）

---

## 维度2: 安全 (7/10) — 持平

### 状态
- ✅ 存档完整性: HMAC-SHA256 + hmac.compare_digest
- ✅ bandit 0 Medium / 0 High（bandit.yaml 独立配置 v0.4.1 上线）
- ✅ 依赖锁文件: requirements.lock + requirements-dev.lock

### 残留
- 无新增，无变动

---

## 维度3: 测试 (8/10) — ↑0.5

### 提升
- ✅ **v0.4.3 TacticExecutor 单测补齐完成**: 19/19 handler + DEMOLISH_BRIDGE 额外，100 新测试（Happy/Error/Boundary 三维度），test_tactic_executor.py 127 tests
- ✅ **xfail strict=False 不诚实标记移除**: test_vl_points_value_rendered_on_map 不再被静默接受 XPASS
- ✅ 实际测试数: 4573 passed / 2 skipped（D13 基线 4459 passed / 1 failed）

### 当前数据
- **单元测试**: 4573 passed / 2 skipped / 0 failed (13.80s)
- **ruff check**: 0 errors
- **ruff format**: 585 files already formatted
- **mypy**: 0 errors (392 files)

### 残留
- ⚠️ **5 个 e2e skip 偷懒**（违反用户测试哲学 "Skip tests are不合理"）
- ⚠️ **12 个零覆盖文件**（含 main.py P0 — 入口点无测试）
- ⚠️ mypy 非严格 (check_untyped_defs=false)
- ⚠️ tests/acceptance/ 仅 1 文件 4 测试

---

## 维度4: 性能 (8/10) — 持平

### 状态
- ✅ slow tests + benchmark 全过
- ✅ PERF_THRESHOLDS.md 定义 4 组件阈值
- ✅ Surface 对象池 LRU + 脏矩形优化 + 地形缓存

### 残留
- 无新增，无变动

---

## 维度5: 可维护性 (7.5/10) — ↑0.5

### 提升
- ✅ **3 个幽灵模块清理**: command_bar.py (CommandBar 类零导入) / visual_effects.py (backward-compat shim 零导入) / command.py (GameCommand/CommandType/CommandResult 零导入) — 累计 14 ghost 全部清理
- ✅ TacticExecutor 100 单测为 v0.5+ 拆分提供安全网

### 残留
- ⚠️ 5 个 God Class >800L 待评估
- ⚠️ TYPE_CHECKING 守卫 182 文件

---

## 维度6: 文档 (7.5/10) — ↑0.5

### 提升
- ✅ **版本号三处同步**: VERSION / pyproject.toml / __init__.py = 0.4.3（D13 仍为 0.4.0）
- ✅ **测试计数三语同步**: README.md / README_zh.md / README_ja.md / SKILL.md / CHANGELOG.md 全部 4573
- ✅ E2E 文档引用断链修复（visual_effects.VisualEffects → cc2_combat_effects.CC2ExplosionEffect）

### 残留
- ⚠️ docs/ 历史评估文档保留（D7/D8/D9 + remediation）
- ⚠️ INSTALL 三语结构略有差异

---

## 维度7: 集成 (8/10) — 持平

### 状态
- ✅ 事件名全部 PascalCase 统一
- ✅ tactic_executor 包结构完整: facade + 7 mixin
- ✅ TacticType 枚举 32 项完整

### 残留
- 无新增，无变动

---

## CI/CD (7.5/10) — ↓0.5

### 降分原因
- ⚠️ **CI ruff format 漂移（P0）**: pre-commit hooks 版本严重陈旧（ruff v0.5.0 vs lock 0.15.20），导致本地格式化与 CI 不一致，CI 连续失败
- ⚠️ **pre-commit hooks 未维护**: 配置文件存在但版本锁未更新，形同虚设

### 状态
- ✅ SKIP_E2E=0 默认值
- ✅ 独立 publish-pypi job
- ✅ 9/9 job 全部 timeout-minutes
- ✅ 覆盖率门禁 60%

### 修复后验证
- `ruff check .` All checks passed ✅
- `ruff format --check .` 585 files already formatted ✅

---

## 目录 (7.5/10) — 持平

### 状态
- ✅ 3 个幽灵模块文件删除（command_bar.py / visual_effects.py / command.py）
- ✅ 无临时文件（.tmp/.bak/_draft/_old）
- ✅ .gitignore 覆盖完整

### 残留
- ⚠️ docs/ 28+ 个 .md 文件，历史评估文档保留
- ⚠️ scripts/ 16 个脚本无 src 引用（工具脚本，保留合理）

---

## D14 新发现问题汇总

| # | 问题 | 优先级 | 状态 |
|---|------|--------|------|
| N-1 | 5 个 God Class >800L（enhanced_sound_bridge 949L / terrain_rendering_system 896L / hud_renderer 886L / vehicle_weapon_profiles 826L / environmental_audio 811L） | P2 | 记录为技术债，v0.5+ 评估 |
| N-2 | 5 个 e2e skip 偷懒（违反测试哲学） | P2 | 记录为技术债 |
| N-3 | 12 个零覆盖文件（含 main.py P0 入口点） | P2 | 记录为技术债 |
| N-4 | mypy 非严格（check_untyped_defs=false） | P3 | 记录 |
| N-5 | pre-commit hooks 版本陈旧（ruff v0.5.0 vs lock 0.15.20） | P2 | 记录为技术债，导致 CI 漂移 |
| N-6 | xfail strict=False 隐藏 XPASS（已修复） | P1 | ✅ 已修复 |
| N-7 | 文档测试计数陈旧 4473 vs 4573（已修复） | P1 | ✅ 已修复 |
| N-8 | 3 个幽灵模块残留（已修复） | P1 | ✅ 已修复 |
| N-9 | E2E 文档引用断链（已修复） | P2 | ✅ 已修复 |
| N-10 | 版本号三处不一致 0.4.0 vs 0.4.3（已修复） | P1 | ✅ 已修复 |

---

## 下一步建议

### 短期（v0.4.4 维护版本）
1. **修复 pre-commit hooks 版本陈旧**（N-5）: 更新 .pre-commit-config.yaml ruff 版本至 0.15.20，与 lock 一致，防止 CI 漂移复发
2. **消除 5 个 e2e skip**（N-2）: 按 "Skip tests are不合理" 哲学，要么修复测试要么删除 skip 标记
3. **main.py 零覆盖**（N-3 子项）: 入口点应有 smoke test 验证启动流程

### 中期（v0.5.0 功能版本）
1. **TacticExecutor 拆分**: TD-064 单测安全网已就绪，可按 mixin 边界进一步拆分
2. **5 个 God Class >800L 评估**（N-1）: 按真实职责（非方法数）判断是否需拆分
3. **12 零覆盖文件补测**（N-3）: 优先 P0 main.py，其次 P1 业务模块

### 长期（v0.6.0+）
1. mypy 启用 check_untyped_defs=true（N-4）
2. 性能阈值组件数从 4 扩展到 8+
3. 考虑 pixvoxel_loader.py 迁移至 scripts/

---

## 评估方法学说明

- **评估命令**: DevSquad V3.8 "项目整理评估"（7 维度 + CI/CD + 目录清理）
- **数据采集**: 5 个并行 Explore subagent（架构+技术债 / 安全+CI/CD+目录 / 测试+集成 / 文档一致性 / E2E 用户旅程）
- **独立验证**: 所有修复经直接命令验证（pytest / ruff check / ruff format --check / grep）
- **基线对比**: D13 报告 docs/ASSESSMENT_D13_MATURITY.md（v0.4.0, commit c736055, 2026-07-05）
- **本次基线**: v0.4.3, commit d248cf4 (batch 4b 完成), 2026-07-05
- **回归测试**: 4573 unit passed / 2 skipped / 0 failed — 零回归
- **诚实评价**: D14 是增量维护版本，非变革性提升。CI 漂移暴露 pre-commit 维护缺失；xfail strict=False 是测试哲学违规；版本号 0.4.0→0.4.3 跨 3 个小版本未同步是文档纪律松懈。这些问题本不应存在。
