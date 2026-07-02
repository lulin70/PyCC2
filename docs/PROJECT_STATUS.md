# PyCC2 项目状态

> **最后更新**: 2026-07-02
> **版本**: v0.4.0
> **状态**: Beta Candidate — 完全可玩

## 核心指标

| 指标 | 数值 | 来源 |
|------|------|------|
| 版本号 | 0.4.0 | `pyproject.toml` / `src/pycc2/__init__.py` / `VERSION` |
| 源码模块数 | 380 个 `.py` 文件 | `find src/pycc2 -name "*.py" \| wc -l` |
| 测试文件数 | 163 个 `.py` 文件 | `find tests -name "*.py" \| wc -l` |
| 测试用例数 | 4424 collected / 4398 passed / 25 skipped | `pytest --collect-only` + 全量回归 |
| 覆盖率门禁 | 60% (pyproject.toml `fail_under=60` + CI `--cov-fail-under=60`) | `.github/workflows/ci.yml` |
| 实际覆盖率 | 52.66% (未达 60% 门禁，CI unit-tests job 红色) | `pytest tests/unit/ --cov=src/pycc2 --cov-report=term` |
| ruff | 0 errors | `ruff check .` |
| mypy | 0 errors (382 files) | `MYPYPATH=src mypy -p pycc2` |
| Bandit | 0 Medium / 0 High | `bandit -r src/ -ll --skip B101,B311,B601` |

## 架构

DDD 4 层结构（domain / infrastructure / presentation / services），364+ 模块零循环依赖。

| 层 | 文件数 | 行数 | 职责 |
|----|--------|------|------|
| domain | 160 | ~39000 | 核心游戏逻辑（纯 Python，零向上依赖） |
| infrastructure | 19 | ~4800 | 事件总线/解析器/配置 |
| presentation | 164 | ~49000 | 渲染/UI/输入 |
| services | 18 | ~4800 | 战斗/AI/补给等跨层协调 |

## 最近评估

| 评估 | 日期 | 评分 | 报告 |
|------|------|------|------|
| D12 | 2026-07-02 | 5.9/10 (D+) | [ASSESSMENT_D12_MATURITY.md](ASSESSMENT_D12_MATURITY.md) |
| D9 | 2026-06-29 | 8.2/10 (B) | [ASSESSMENT_D9_MATURITY.md](ASSESSMENT_D9_MATURITY.md) |
| D8 | 2026-06-27 | 8.0/10 (B-) | [ASSESSMENT_D8_MATURITY.md](ASSESSMENT_D8_MATURITY.md) |

**D12 评分下降原因**: 检查更严格，暴露硬约束违反（PROJECT_STATUS/SKILL/VERSION 缺失、SKIP_E2E 缺失、覆盖率门禁未配置文件级）。D11 拆分质量高但仅处理 3/8 大文件。

## 最近变更

### D11 SRP 大文件拆分 (2026-07-02)
- `cc2_building_renderer.py` 1215→46L facade + 4 子模块
- `sprite_renderer.py` 1178→47L facade + 5 mixin
- `tactic_executor.py` 1346→包结构 9 文件（facade + 7 mixin）
- 回归: 3734 unit + 483 e2e = 4217 passed / 0 failed

详见 [CHANGELOG.md](../CHANGELOG.md)

## 已知技术债

- 5 个 >1000 行文件待拆分（terrain_tile_generator / deployment_renderer / pixvoxel_loader / infantry_pixel_renderer / campaign_ui_rendering）
- `unit.py` God Class（54 方法）待拆分
- 12 个 ghost 模块（有测试无生产引用）待清理
- 事件名大小写不匹配致部分事件丢失（unit_attacked vs UnitAttacked）

详见 [TECH_DEBT.md](TECH_DEBT.md)

## 发布检查清单

- [x] 版本号三处一致（pyproject.toml / __init__.py / VERSION）
- [x] 三语 README 测试数同步
- [x] ruff / mypy / bandit 全绿
- [x] 全量回归测试通过
- [ ] CI 全绿（Lint 已修复 ruff format，但 unit-tests 因覆盖率 52.66% < 60% 门禁失败，待提升覆盖率）
- [x] 覆盖率 ≥60% fail_under 门禁已配置（pyproject.toml + ci.yml，但实际 52.66% 未达标）
- [ ] 5 个 >1000L 文件拆分（P0-1 待修复）
- [ ] unit.py God Class 拆分（P0-2 待修复）
