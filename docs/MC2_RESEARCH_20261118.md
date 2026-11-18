# MechCommander 2 源码研究与 Python 可行性方案

- 日期：2026-11-18
- 来源：[videogamepreservation/mechcommander2](https://github.com/videogamepreservation/mechcommander2)（微软 2006 官方 Shared Source 发布镜像，C++ 全源码 + 资产）
- 对照项目：PyCC2（Close Combat 2 机制复刻，Python + pygame-ce）
- 结论速览：
  1. MC2 有 6 个子系统可直接启发 PyCC2 改进，按 P1/P2/P3 排期见 §3。
  2. GitHub 无 Python 版 MechCommander；用 Python 做本机可跑版本完全可行，方案见 §4。

---

## 1. MC2 核心模拟层清单（Code/ 209 文件中与玩法直接相关部分）

| 文件 | 职责 | PyCC2 对应物 |
|------|------|--------------|
| `tacordr.cpp/h` | 战术指令 DSL：25 种指令类型，三种来源（player/commander/self），可序列化 | `services` 各命令入口（散落） |
| `warrior.cpp/h` | 驾驶员模型：每技能 use/success 双计数、skillRank/skillPoints 成长、specialty 技能、brainState | `squad.py` 士气/经验（仅击杀计数） |
| `mover.cpp/movemgr.cpp` | 移动状态机：speedState/moveState/**yieldState**（互相让路协商） | `movement_controller`（已 ARCHIVE，职责在 services 层） |
| `goal.cpp/comndr.cpp` | 指挥官 AI：目标分解（GOAL_OBJECT/GOAL_REGION）+ goal link 图 | `CommanderAI`（TD-016 曾登记） |
| `trigger.cpp/h` | 事件驱动任务脚本（增援/胜利条件/剧情触发） | `reinforcement_service` + 场景 special_rules 消费点（11 处散落） |
| `Contact.cpp/h` | 传感器接触表：接触持久化与衰减 | fog of war 三态（无记忆衰减） |
| `weaponbolt.cpp/h` | 弹道实体（独立于射手存活） | `ballistic.py` |
| `carnage.cpp/h` | 伤害聚合与统计 | `combat_director.py::record_stats` |
| `artlry.cpp/turret.cpp/weather.cpp` | 火炮支援/炮塔/天气 | 已实现（W5 P1-4/P2） |
| `logistics*.cpp`（10+ 文件） | 战役整备闭环：机甲购置/改装（variant）/回收（salvage）/飞行员雇佣 | 无对应（PyCC2 无战役间整备） |
| `ABL 脚本`（ABLT/） | 数据驱动的行为/任务脚本语言 | 场景 JSON + special_rules |

## 2. 关键机制细节（读码确认）

1. **TacticalOrder 是一等公民**：指令不是函数调用而是带类型/参数/origin 的数据对象，可打包进网络包。`ORDER_ORIGIN_PLAYER/COMMANDER/SELF` 三来源让 AI 与玩家共用同一指令面。
2. **技能成长是统计驱动**：`numSkillUses[skill][stats]` + `numSkillSuccesses[skill][stats]` 双计数，rank 由成功/使用比推导——不是简单击杀数。specialty 技能独立开关表。
3. **移动有让路协商**：`yieldState` 记录"刚让路/让路已久"状态，配 `moveStateGoal`，解决单位对冲卡死。
4. **触发器统一入口**：增援、胜利检查、剧情都走 `trigger.cpp` 一套条件-动作脚本，不散落在各系统内。

## 3. 方案一：PyCC2 吸收改进排期

| 编号 | 改进 | 优先级 | 落点 | 验收 |
|------|------|--------|------|------|
| MC2-01 | 战术指令统一为类型化数据对象（枚举 + 参数 + origin），命令入口收敛到单一分发层 | P1 | `services/orders.py`（新）+ 各 director 收敛 | e2e 录制回放用例：同指令序列重放结果一致 |
| MC2-02 | 触发器统一：增援/胜利/士气事件迁入条件-动作触发器表 | P1 | `services/trigger_system.py`（新） | 11 条 special_rules 消费点改走触发器，全量回归零失败 |
| MC2-03 | 驾驶员技能成长：开火/命中/受击双计数，命中率随 rank 漂移 | P2 | `squad.py`/`unit.py` + 战役存档字段 | 单测：100 次命中后 rank 单调上升；存档读回一致 |
| MC2-04 | 接触记忆：fog 三态加"最后目击时间 + 衰减"，单位离视野保留残影 | P2 | `los_system`/fog 模块 | 单测：离视野 N tick 后残影消失 |
| MC2-05 | 让路协商状态机（拥挤地形卡位） | P3 | 路径服务 | 压力场景：8 单位对冲通道无死锁 |
| MC2-06 | 战役整备闭环（购置/改装/回收/雇佣） | P3 | 战役层（新模块） | e2e：整备→下场战斗携带变更 |

执行顺序：MC2-01 → MC2-02 为一波（同为收敛性重构，收益是后续一切的地基）；MC2-03/04 一波；05/06 视方向决策再排。

## 4. 方案二：Python MechCommander（PyMC2）

### 4.1 现状结论
- GitHub `mechcommander language:python`：0 结果；无任何 Python 版 MechCommander/MechWarrior 战术层专项目（MegaMek 为 Java）。
- 可行性：**高**。官方 C++ 源码逐系统可读，核心玩法（战术层）约 15 个 .cpp 即可覆盖；PyCC2 已验证同栈工程体系（CI 门禁链、视觉回归、UAT 脚本）可整体复用。

### 4.2 目标形态
本机可跑的单机战术游戏：任务选择 → 简报 → 战术指挥（框选/指令/火力姿态）→ 结算 → 战役间整备。不含联机。

### 4.3 技术选型
- Python 3.12 + pygame-ce（与 PyCC2 同栈，工具链零学习成本）
- 架构照搬 PyCC2 四层（domain/services/presentation/infrastructure）+ Composition Root
- 门禁照搬：ruff/mypy/radon + unit/integration/e2e + FPS 基线 + 远端 CI 强制前置
- 资产：**不复用 MC2 美术**（Shared Source 许可仅限非商业参考，再分发风险高）。数据格式可参考（.fit 机甲定义 / .abl 脚本），资产用程序化生成或自建占位（PyCC2 的精灵生成管线可直接复用）

### 4.4 里程碑（每项含门禁验收，不带时间承诺）

| 里程碑 | 内容 | 验收标准 |
|--------|------|----------|
| M1 垂直切片 | 单任务场景渲染 + 单机移动 + 直射开火 + 命中判定 | e2e：选中→移动→开火→掉血全链路截图留痕 |
| M2 指令层 | TacticalOrder DSL（MC2-01 同款设计）+ 框选/右键指令/火力姿态 | 指令回放一致性用例；UAT 真实窗口点击链路 |
| M3 机甲实体 | 部位装甲/内部结构/武器槽/热量 | 单测：部位摧毁顺序与 WeaponBolt 判定 |
| M4 AI | 驾驶员技能模型 + 指挥官 goal 分解（GOAL_OBJECT/REGION） | AI 对战压力场景不卡死；skill 成长单调性单测 |
| M5 战役 | 任务链 + 整备闭环（salvage/refit/hire） | e2e：整备变更带入下一任务 |
| M6 脚本化 | Trigger DSL + ABL 式任务脚本 | 示例任务脚本全事件触发覆盖 |

### 4.5 决策点（需用户拍板）
1. **新仓库 or PyCC2 子目录**：建议独立仓库（架构相似但玩法域不同，混仓会稀释 CI 基线与发布节奏）。
2. **是否启动**：PyCC2 当前改进方案（§3）与 PyMC2 共享 MC2-01/02 的设计产出，可先做 §3 第一波，验证指令层设计后再决定 PyMC2 启动时机。

---

## 5. 引用

- MC2 源码：https://github.com/videogamepreservation/mechcommander2
- 微软官方发布公告：https://learn.microsoft.com/en-us/archive/blogs/danielfe/mech-commander-2-source-code-available-for-download
- Close Combat 2：无官方源码（结论维持 2026-11-17 检索结果），机制对照仍以实测行为为准
