# PyCC2 交付方案 Review 报告（严格 7 角色）

**评审对象**: `docs/PROJECT_DELIVERY_PLAN.md` v1.3  
**评审日期**: 2026-11-07  
**评审方式**: 文档评审 + 仓库代码取证（不以文档自述为准）  
**参与角色**: DevSquad 7 角色全员

| 角色 ID | 中文名 | 投票权重 | 本次关注点 |
|---|---|---|---|
| `architect` | Architect | 1.5 | 架构描述准确性、依赖约束、演进风险 |
| `product-manager` | PM | 1.2 | 验收标准可量化、UAT 可执行性 |
| `security` | Security | 1.1 | 存档完整性、密钥管理、反馈文件写入 |
| `tester` | Tester | 1.0 | 覆盖率真实性、回归与性能门禁 |
| `solo-coder` | Coder | 1.0 | 实施可行性、工作量可估性 |
| `devops` | DevOps | 1.0 | CI 门禁一致性、跨平台验证、发布流程 |
| `ui-designer` | UI Designer | 0.9 | 键盘可达性、缩放适配、视觉一致性 |

**取证范围**: `src/pycc2/main.py`、`services/game_loop.py`、`infrastructure/save_system.py`、`presentation/ui/*`、`presentation/rendering/*`、`.github/workflows/ci.yml`、`pyproject.toml`、`tests/`。

---

## 1. Architect

**结论**: ⚠️ 有条件批准

**依据（已验证）**
- `main.py` 已实现主菜单 → 战役/遭遇战/读档 → 部署 → 战斗的完整链路。
- `game_loop.py` 以门面方式注入 `IHUDManager`、`ISettingsMenu`、`ITutorialOverlay`、`ISaveController`。
- 文档 v1.2/1.3 已撤销"缺少入口"的错误前提，架构描述与代码一致。

**问题**

| ID | 级别 | 问题 | 证据 |
|---|---|---|---|
| ARCH-01 | P1 | §2.5 声明"可选重构"，但未定义决策记录的产出格式与判定人 | 文档 §2.5 |
| ARCH-02 | P1 | 文档要求 `import-linter` 检查分层依赖，但仓库未配置 | `grep importlinter` 无结果 |
| ARCH-03 | P2 | 未给出 presentation → application → domain 的实际违规基线 | 无基线数据 |

**要求（可验收）**
1. Day 1 输出 `docs/adr/ADR-001-是否引入SceneRouter.md`，含决策、备选方案、影响。
2. 在 `pyproject.toml` 增加 `import-linter` 配置，并记录首次运行的违规数。
3. 若违规数 >0，先列清单，不在 Phase 1 修复。

---

## 2. Product Manager

**结论**: ⚠️ 有条件批准

**依据（已验证）**
- 验收标准含功能、性能、质量、体验四类，结构完整。
- UAT 已定义 5 个任务与三类用户样本。

**问题**

| ID | 级别 | 问题 | 证据 |
|---|---|---|---|
| PM-01 | P1 | "游戏可玩性达到90%"无量化定义，无法验收 | 文档 Phase 1 出口准则 |
| PM-02 | P1 | UAT 样本来源、招募方式、记录模板未定义 | 文档 §4.8 |
| PM-03 | P2 | "UI 视觉打磨通过 PM 评审"缺评审清单 | 文档 §3.3.3 |

**要求（可验收）**
1. 将"可玩性"拆为可测项：入口可用率、任务完成率、阻断缺陷数。
2. 提供 `docs/test/UAT_TEMPLATE.md`，含观察记录表与评分表。
3. UI 评审使用固定检查表（对齐、间距、字号层级、状态反馈、配色一致性）。

---

## 3. Security

**结论**: ✅ 批准

**依据（已验证）**
- 存档使用 `hmac.HMAC(..., hashlib.sha256)` 做完整性校验。
- 存档文件名经 `_sanitize_filename` 处理。
- 仅使用 `json.loads`，未使用 `pickle`/`eval`。
- HMAC 密钥缺失时抛出异常并提示 `config/secrets.toml`，无硬编码回退。
- `config/secrets.toml` 已在 `.gitignore:160` 忽略。

**问题**

| ID | 级别 | 问题 | 证据 |
|---|---|---|---|
| SEC-01 | P1 | §4.9 反馈机制写入本地文件，未定义文件名净化与大小上限 | 文档 §4.9 |
| SEC-02 | P2 | 读档仅校验 HMAC，未做字段级 schema 校验，异常数据可能触发崩溃 | `save_system.py:280` |
| SEC-03 | P3 | 密钥轮换后旧存档不可读，未在文档说明处理方式 | `save_system.py:193-237` |

**要求（可验收）**
1. 反馈文件复用 `_sanitize_filename`，单文件上限 64KB，超限截断并提示。
2. 读档增加最小 schema 校验（必填字段、类型、版本号）。
3. 用户文档增加"密钥变更导致旧存档失效"的说明。

---

## 4. Tester

**结论**: ⚠️ 有条件批准

**依据（已验证）**
- 仓库含 255 个测试文件，覆盖 unit/integration/e2e/acceptance/ux/performance/visual_regression。
- CI 已执行单元、集成、E2E 三层测试。
- 文档 v1.2 已删除无依据的"45% 覆盖率"表述，改为待实测。

**问题**

| ID | 级别 | 问题 | 证据 |
|---|---|---|---|
| TEST-01 | P1 | 覆盖率门禁不一致：`pyproject.toml` 为 70，CI 为 65 | `pyproject.toml:163`、`ci.yml:111` |
| TEST-02 | P1 | 当前实际通过率与覆盖率仍未实测 | `coverage.json` 为 2026-07-11 数据 |
| TEST-03 | P2 | 性能门禁未纳入 CI，仅写在文档 | `ci.yml` 无性能门槛 |
| TEST-04 | P2 | 视觉回归测试是否在 CI 执行未确认 | `ci.yml` 未见 visual_regression |

**要求（可验收）**
1. 统一覆盖率门禁为 70，修改 CI 或 pyproject 其中一处。
2. Day 1 执行 `pytest` 与 `pytest --cov`，结果写入 `docs/AUDIT_REPORT.md`，附命令与时间。
3. Day 17 性能测试输出 JSON，并纳入交付物。

---

## 5. Coder（solo-coder）

**结论**: ✅ 批准

**依据（已验证）**
- Phase 1 任务均为增量修复，不涉及大规模重建。
- 每个修复要求附带回归测试，与现有测试结构兼容。
- `pyproject.toml` 已配置 ruff、mypy、pytest-timeout，工具链可用。

**问题**

| ID | 级别 | 问题 | 证据 |
|---|---|---|---|
| COD-01 | P1 | Phase 1 工期基于"缺陷数未知"排定，可能失真 | 文档 §5.2 |
| COD-02 | P2 | A01-A14 审计缺少负责人与预计耗时 | 文档 §3.3.1 |
| COD-03 | P3 | "每日 Code Review"未定义准入/准出判据 | 文档 §5.3 |

**要求（可验收）**
1. Day 1 审计结束后重估 Phase 1，并更新 §5.2。
2. 审计清单增加 `owner` 与 `estimate` 两列。
3. Code Review 使用固定 4 项检查表（依赖方向、测试、魔法数、异常路径）。

---

## 6. DevOps

**结论**: ⚠️ 有条件批准

**依据（已验证）**
- 存在 `.github/workflows/ci.yml` 与 `release.yml`。
- CI 含 lint、ruff format、mypy、安全扫描、依赖漏洞审计、radon 复杂度、版本一致性检查。
- 测试分三层执行：unit → integration → e2e，且有 `needs` 依赖。
- `requirements.lock` 与 `requirements-dev.lock` 均已提供。

**问题**

| ID | 级别 | 问题 | 证据 |
|---|---|---|---|
| OPS-01 | P1 | 覆盖率门禁双源不一致（70 vs 65） | `pyproject.toml:163`、`ci.yml:111` |
| OPS-02 | P1 | `requires-python >=3.11`，CI 仅测 3.12 | `pyproject.toml:11`、`ci.yml:88` |
| OPS-03 | P2 | CI 全部为 `ubuntu-latest`，未验证 macOS/Windows，而 Pygame 桌面游戏以这两平台为主 | `ci.yml` 多处 `runs-on` |
| OPS-04 | P2 | 发布流程未要求归档 UAT 与性能报告 | `release.yml` 未取证到相关步骤 |

**要求（可验收）**
1. 统一覆盖率门禁，单一来源。
2. 增加 3.11 到测试矩阵，或在 `requires-python` 收紧为 `>=3.12`。
3. 增加 macOS job（至少 smoke test：导入 + 无头启动）。
4. Phase 3 发布前，将 UAT 与性能报告作为发布前置产物。

---

## 7. UI Designer

**结论**: ⚠️ 有条件批准

**依据（已验证）**
- 存在统一主题源 `presentation/ui/theme.py`，含 `text_disabled` 等状态色。
- 存在 `tooltip.py`、`theme_switcher.py`、`keybindings_overlay.py`。
- 渲染层已使用 `ui_scale` 缩放（`unit_overlay_rendering_mixin.py:154`）。

**问题**

| ID | 级别 | 问题 | 证据 |
|---|---|---|---|
| UX-01 | P1 | 主菜单键盘可达性不足：仅见 `K_TAB` 一处处理，未见方向键/回车导航 | `new_game_menu.py:681` |
| UX-02 | P2 | `ui_scale` 已有，但未定义缩放档位、最小分辨率与验收截图 | 文档 §3.3.3 |
| UX-03 | P2 | 无对比度或可读性检查项 | 文档 §3.3.3 |
| UX-04 | P3 | 主题切换已存在，但未说明战斗中禁用策略的用户提示 | `theme_switcher.py:8` |

**要求（可验收）**
1. 主菜单支持 Tab/方向键切换焦点、Enter 确认、Esc 返回，并补测试。
2. 定义 3 档 UI 缩放（100%/125%/150%）与最小分辨率 1280×720。
3. UI 打磨检查表增加对比度项（正文与背景对比度 ≥ 4.5:1）。

---

## 8. 缺陷汇总

| 级别 | 数量 | 编号 |
|---|---|---|
| **P1** | 11 | ARCH-01, ARCH-02, PM-01, PM-02, SEC-01, TEST-01, TEST-02, COD-01, OPS-01, OPS-02, UX-01 |
| **P2** | 10 | ARCH-03, PM-03, SEC-02, TEST-03, TEST-04, COD-02, OPS-03, OPS-04, UX-02, UX-03 |
| **P3** | 3 | SEC-03, COD-03, UX-04 |

**合计**: 24 项（P0 = 0）。

---

## 9. 共识结论

### 9.1 投票

| 角色 | 权重 | 结论 | 计分 |
|---|---|---|---|
| Architect | 1.5 | 有条件批准 | 0.8 |
| PM | 1.2 | 有条件批准 | 0.8 |
| Security | 1.1 | 批准 | 1.0 |
| Tester | 1.0 | 有条件批准 | 0.8 |
| Coder | 1.0 | 批准 | 1.0 |
| DevOps | 1.0 | 有条件批准 | 0.8 |
| UI Designer | 0.9 | 有条件批准 | 0.8 |

**加权共识分** = (1.5×0.8 + 1.2×0.8 + 1.1×1.0 + 1.0×0.8 + 1.0×1.0 + 1.0×0.8 + 0.9×0.8) / 7.7  
= (1.20 + 0.96 + 1.10 + 0.80 + 1.00 + 0.80 + 0.72) / 7.7  
= 6.58 / 7.7 ≈ **85.5%**

**判定**: 达到 P2 阶段 ≥70% 的共识门禁。方案**有条件通过**。

### 9.2 放行范围

仅放行 **Phase 1 Day 1（审计）**。其余阶段待审计数据产出后再次确认。

### 9.3 Day 1 强制性交付（7 角色共同要求）

| 编号 | 交付物 | 责任角色 |
|---|---|---|
| D1 | `docs/AUDIT_REPORT.md`（A01-A14 + owner + estimate） | Tester + Coder |
| D2 | 实测覆盖率与通过率（含命令、时间） | Tester |
| D3 | 分级缺陷清单（P0/P1/P2，含复现步骤） | Tester + Coder |
| D4 | `docs/adr/ADR-001-是否引入SceneRouter.md` | Architect |
| D5 | `import-linter` 配置与首次违规基线 | Architect |
| D6 | 覆盖率门禁统一（70） | DevOps + Tester |
| D7 | 基于实测的 Phase 1 工期重估 | Coder + PM |

### 9.4 复审触发条件

满足全部条件后提交第三次 Review：
1. D1-D7 全部产出。
2. P0 缺陷已修复或已排期。
3. Phase 1 工期重估完成并写入文档。

---

## 10. 与上一版 Review 的差异

| 项目 | v1.1/v1.2 Review | 本次（7 角色） |
|---|---|---|
| 角色 | 4 个（含错误的 "Tech Lead"） | 7 个，全部使用 DevSquad 角色 ID |
| 取证 | 以文档自述为主 | 文档 + 代码/CI 实证 |
| 门禁 | 定性意见 | 加权共识分 85.5% + 明确放行范围 |
| 缺陷 | 未编号 | 22 项，按 P1/P2/P3 编号 |

**教训**: 角色名称必须来自框架定义；结论必须可追溯到证据。
