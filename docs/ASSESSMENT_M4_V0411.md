# M4 架构改进收尾评估 (v0.4.11, 2026-07-09)

> **评估范围**: ROADMAP.md M4 章节两个待完成任务 — Domain layer slimdown (75.4% → <50%) + Unify unit definition system (4 sets → 1 set)
> **评估方法**: 实际代码行数测量 + 模块职责审查 + DDD 模式对照
> **结论**: 两个任务的前提均不成立，无需代码改动。标记为评估完成。

---

## 1. 任务一: Domain layer slimdown (75.4% → <50%)

### 1.1 原始任务描述

ROADMAP.md M4 Task List 第一项:
> Domain layer slimdown (75.4% → <50%) | P1 | 8h | ⬜ Still pending

目标: 将 domain/ 层代码占比从 75.4% 降至 50% 以下。

### 1.2 实测数据 (2026-07-09)

```bash
$ find src/pycc2/domain -name "*.py" -exec wc -l {} + | tail -1
   36966 total
$ find src/pycc2 -name "*.py" -exec wc -l {} + | tail -1
   96137 total
```

| 层 | 文件数 | 行数 | 占比 |
|----|--------|------|------|
| domain | 167 | 36966 | **38.5%** |
| infrastructure | 19 | ~4777 | 5.0% |
| presentation | 184 | ~49168 | 51.1% |
| services | 18 | ~4773 | 5.0% |
| **合计** | **388** | **95684** | 100% |

### 1.3 75.4% 数据来源追溯

ROADMAP.md 的 75.4% 是 v0.3.x 之前的旧数据。经以下拆分后 domain 占比自然下降:

- **v0.3.5-v0.3.11 enhanced_renderer 拆分**: 5975 行 → 2239 行（-62.5%），拆出的子模块归入 presentation 层
- **D11/D12 GameLoop 拆分**: 1226 行 → <400 行，拆出的子模块归入 services 层
- **D12 Phase 4 unit.py God Class 拆分**: 937 行 / 54 方法 → 494 行 facade + 5 个 mixin，domain 内部重组但总量略减
- **v0.4.10 TD-003 campaign.py 删除**: 205 行移除

同时 presentation 层因新增 UI 组件和渲染器而增长，使 domain 相对占比进一步下降。

### 1.4 结论

**目标已达成**: domain 占比 38.5% < 50%，无需额外代码改动。

**所需工作**: 仅更新 ROADMAP.md / PROJECT_STATUS.md 文档，标记任务完成并修正过期的 75.4% 数据。

---

## 2. 任务二: Unify unit definition system (4 sets → 1 set)

### 2.1 原始任务描述

ROADMAP.md M4 Task List 第五项:
> Unify unit definition system (4 sets → 1 set) | P2 | 4h | ⬜ Still pending

目标: 将 4 套单位定义合并为 1 套。

### 2.2 实际代码审查

调研发现所谓 "4 套定义" 实际是 1 套协作系统，由 4 个职责不同的模块组成:

| 模块 | 行数 | 职责 | DDD 角色 |
|------|------|------|----------|
| `domain/entities/unit.py` | 494 | 运行时单位实体（状态、组件、生命周期、mixin 组合） | **Entity** |
| `domain/systems/unit_templates.py` | 123 | `CC2UnitTemplate` dataclass（单位规格: hp、武器、阵营、部署成本） | **Value Object / Specification** |
| `domain/systems/unit_factories/` | 1554 | 5 个阵营工厂（american/british/german/polish/german_expanded）从 template 创建 Unit | **Factory** |
| `domain/systems/cc2_authentic_units.py` | 52 | facade，re-export templates + database + factories + deployment | **Facade** |
| `domain/systems/unit_database.py` | 56 | 数据库构建/查询（build_cc2_unit_database, get_cc2_units, get_units_by_role） | **Repository / Query Service** |

### 2.3 DDD 模式对照

这是标准的 DDD 战术模式组合:

```
CC2UnitTemplate (Specification)
        ↓
   UnitFactory.create(template) → Unit (Entity)
        ↓
   unit_database (Repository) 存储/查询 templates
        ↓
   cc2_authentic_units (Facade) 统一对外 API
```

- **Entity** (`Unit`): 拥有唯一标识（`id`），生命周期（`take_damage`/`die`），状态机（`UnitState`），组件组合（Health/Morale/Weapon/Position/Vision/Veterancy/Fatigue）。运行时实例。
- **Value Object / Specification** (`CC2UnitTemplate`): 不可变的单位规格描述，无生命周期。多个 Unit 可共享同一 template。
- **Factory** (`unit_factories/`): 封装复杂对象创建逻辑，按阵营隔离构建规则。
- **Facade** (`cc2_authentic_units.py`): 提供简化入口，隐藏内部模块结构。

### 2.4 职责重叠检查

审查同一属性（如 hp）在多处定义的情况:

- `Unit` 通过 `HealthComponent(hp=..., max_hp=...)` 持有运行时 hp 值，会随战斗变化
- `CC2UnitTemplate.morale_initial: float = 80.0` 定义初始士气值，工厂创建 Unit 时用此值初始化 `MoraleComponent`
- `unit_factories/*.py` 在创建 Unit 时从 template 读取数值注入组件

**结论**: 无重复定义。template 是 source of truth（配置），Unit 是 runtime carrier（状态），factory 是 builder（转换）。属性从 template → factory → Unit 单向流动。

### 2.5 消费者分析

`grep` 显示 11 个模块 import 这套系统:

```
src/pycc2/domain/systems/faction_variant_generator.py
src/pycc2/domain/systems/skirmish_generator.py
src/pycc2/domain/systems/unit_factories/american_units.py
src/pycc2/domain/systems/unit_factories/british_units.py
src/pycc2/domain/systems/unit_factories/german_units.py
src/pycc2/domain/systems/unit_factories/polish_units.py
src/pycc2/domain/systems/unit_factories/german_units_expanded.py
src/pycc2/domain/systems/unit_database.py
src/pycc2/domain/systems/vehicle_variant_generator.py
src/pycc2/domain/systems/deployment.py
src/pycc2/domain/systems/cc2_authentic_units.py
```

所有消费者通过 facade 或直接 import 特定模块，无循环依赖，职责边界清晰。

### 2.6 结论

**前提不成立**: 不存在 "4 套独立单位定义"，而是 1 套 DDD 协作系统（Entity + Specification + Factory + Facade + Repository）。

**强行合并的风险**:
- 破坏 SRP（Entity 承担配置职责会膨胀）
- 破坏 DDD 分层（Factory 与 Entity 混合）
- 高回归风险（11 个消费者需同步修改）
- 违反 Simplicity First + Surgical Changes 原则

**所需工作**: 仅文档化评估结论，标记任务为 "评估完成-前提不成立"。

---

## 3. 教训

### 3.1 ROADMAP 数据需要定期校准

ROADMAP.md 的 75.4% 和 "4 sets" 来自 v0.3.x 或更早的评估。经过 v0.3.5-v0.4.11 的大量拆分和重构后，前提已不成立但文档未同步。建议:

- 每次里程碑（如 v0.4.x → v0.5.x）前，对 ROADMAP 的量化目标做实测校准
- 量化目标应附带测量日期和测量命令，便于后续验证

### 3.2 "N 套定义" 类任务需先做职责审查

"4 sets → 1 set" 这类合并任务在执行前应先确认:
- N 套是否真的独立（vs 协作）
- 是否符合标准设计模式（DDD / GoF）
- 合并是否带来真实收益（vs 破坏 SRP）

类似教训: TD-026（52 候选 → 1 TRUE / 51 FALSE = 1.9% hit rate）证明机械阈值判断 God Class 极不可靠。本次评估再次验证: 基于过期数据的架构改进任务也需重新校准前提。

---

## 4. 状态变更

| 任务 | 原状态 | 新状态 | 理由 |
|------|--------|--------|------|
| Domain layer slimdown (75.4% → <50%) | ⬜ Still pending | ✅ 评估完成-目标已达成 | 实测 38.5% < 50%，75.4% 为过期数据 |
| Unify unit definition system (4 sets → 1 set) | ⬜ Still pending | ✅ 评估完成-前提不成立 | 实为 1 套 DDD 协作系统，非 4 套独立定义 |

**M4 验收标准更新**:
- [x] Domain layer code <50% of total ✅ (实测 38.5%, 2026-07-09)
- 其余验收项见 ROADMAP.md M4 章节

**M4 整体状态**: 9/9 任务完成（7 原已完成 + 2 本次评估完成）。M4 架构改进收尾。
