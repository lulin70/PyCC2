# PyCC2 Skill 描述

> **版本**: v0.4.0
> **最后更新**: 2026-07-02

## 模块统计

| 类别 | 数量 | 来源 |
|------|------|------|
| 源码模块 | 380 个 `.py` 文件 | `find src/pycc2 -name "*.py" \| wc -l` |
| 测试模块 | 163 个 `.py` 文件 | `find tests -name "*.py" \| wc -l` |
| 测试用例 | 4424 collected | `pytest --collect-only` |

## 项目能力

PyCC2 是 Close Combat 2 的 Python 复刻，战术步兵战斗模拟器。

### 核心技能域

| 域 | 模块数 | 能力 |
|----|--------|------|
| domain | 160 | 实体/战斗/AI/地形/补给核心逻辑 |
| infrastructure | 19 | 事件总线/地图解析/配置 |
| presentation | 164 | 渲染/UI/输入/音效 |
| services | 18 | 战斗裁决/AI 决策/补给协调 |

### 架构约束

- DDD 4 层，domain 层零向上依赖
- 零循环依赖（`python -c "import pycc2"` 验证）
- Facade + Mixin 拆分模式（D11 落地 3 个大文件）

## 质量门禁

| 门禁 | 阈值 | 状态 |
|------|------|------|
| ruff | 0 errors | ✅ |
| mypy | 0 errors (382 files) | ✅ |
| Bandit | 0 M/H | ✅ |
| 覆盖率 | 70% (CI) | ✅ |
| 测试回归 | 4398 passed / 0 failed | ✅ |
