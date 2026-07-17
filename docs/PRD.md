# PyCC2 产品需求规格书 (PRD) v0.7.2

> **本文档已更新至 v0.7.2，早期版本信息见 Git 历史**

## 一、项目概述

- **项目名称**: PyCC2 (Python Close Combat 2)
- **目标**: 用 Python 从零重写经典 RTT 游戏 Close Combat 2: A Bridge Too Far
- **平台**: macOS Apple M1 (ARM64) / Linux / Windows
- **技术栈**: Python 3.11+ / Pygame 2 (SDL2) / numpy / pydantic
- **美术路线**: 几何原型 → 像素画渐进
- **愿景**: 单人即时战术(RTT)游戏，二战"市场花园行动"背景

**文档版本**: v0.7.2
**创建日期**: 2026-05-15
**最后更新**: 2026-07-17
**作者**: PyCC2 项目组
**状态**: ✅ Beta Candidate — 全部P0 Bug已修复，游戏可玩，AI 可对战
**当前版本**: v0.7.2
**测试总数**: ~6486 tests (100% pass rate, 含 490 E2E + 181 integration + 37 acceptance)
**CC2还原度**: ~75%（视觉70% / 机制80%，v0.4.16 诚实修正，详见 ROADMAP.md）
**P0 Bug数**: 0
**地图数**: 63
**单位模板数**: 277
**源码模块数**: 388
**下一步**: M5 质量可持续 + M6 内容增强（见 ROADMAP.md）

### L1 MVP → L4 v1.0 四层目标:

- **L1 (MVP)**: 可玩的最小战斗场景 — 10x10地图 + 2v2步兵班 + 选单位/移动/AI反击/射击伤害/胜负
- **L2 (Alpha)**: 完整战斗系统 — 多兵种/支援火力/士气/FoW/多地图
- **L3 (Beta)**: 战役模式 — 多关卡继承/存档读档/音效/UI打磨
- **L4 (v1.0)**: 发布版 — 打包分发/.app/.dmg/性能优化

### 产品愿景:

让 CC2 的核心战术体验在 macOS M1 上重生——连级指挥、真实弹道、士气建模、地形战术，全部用 Python 实现。

### 目标用户:

- **Primary**: 开发者本人（CC2 怀旧玩家）
- **Secondary**: RTT 游戏爱好者社区
- **Tertiary**: Python 游戏开发学习者

### 与原版 CC2 关系:

还原度目标 ≥90% 的核心机制，参考 [GAP_ANALYSIS.md](GAP_ANALYSIS.md) 和 [ISSUES.md](ISSUES.md)

**当前还原度**: ~75%（视觉70% / 机制80%，v0.4.16 诚实修正后数据，详见 [ROADMAP.md](ROADMAP.md) 和 [GAP_ANALYSIS.md](GAP_ANALYSIS.md)）

> **⚠️ v0.4.16 诚实修正说明**: 原声称 ~88% 还原度经代码审核严重高估。问题：(1) 11维度简单平均无权重；(2) isometric_renderer/isometric_transform 文件不存在（幽灵功能）；(3) PixVoxel 精灵加载器1143行完整但完全未接入游戏循环。基于代码证据修正为视觉~70%/机制~80%/综合~75%。v0.5.0~v0.6.10 已修复幽灵功能并持续提升还原度。

---

## 一点五、P0 Bug 状态（全部已修复 ✅）

> **原5个P0 Bug已全部修复，当前P0 Bug数为0。**

| P0 ID | Bug描述 | 状态 |
|-------|---------|------|
| ~~P0-001~~ | ~~Unit缺少display_name属性~~ | ✅ 已修复 (v0.1.1) |
| ~~P0-002~~ | ~~HealthComponent/MoraleComponent属性名不匹配~~ | ✅ 已修复 (v0.1.1) |
| ~~P0-003~~ | ~~AttackNearestAI/MoveToObjectiveAI导入失败~~ | ✅ 已修复 (v0.1.1) |
| ~~P0-004~~ | ~~set_mode()不支持fast/sneak参数~~ | ✅ 已修复 (v0.2.0) |
| ~~P0-005~~ | ~~旧UI组件文件未清理~~ | ✅ 已修复 (v0.2.0) |

**当前状态**: 0个P0 Bug，游戏完全可玩。

---

## 一点六、CC2还原度评估（v0.6.10 更新）

> **基于DevSquad 7维度审查 + 代码证据审核 + 490 E2E 验证的真实评估。**
> **v0.4.16 诚实修正**: 原 ~88% 还原度数据经代码审核严重高估，已修正为 ~75%。

| 维度 | v0.1.1评估值 | v0.4.0评估值 | v0.6.10评估值 | 说明 |
|------|-------------|-------------|---------------|------|
| **地图库** | 50% | 95% | **95%** | 63张地图，纹理已增强 |
| **战役结构** | 30% | 98% | **98%** | 四层架构+日简报+继承+结束画面 |
| **武器系统** | 70% | 95% | **95%** | 69种武器，效果已验证 |
| **单位多样性** | 40% | 90% | **90%** | 277种模板，精灵渲染+炮塔旋转 |
| **AI战术** | 15% | 85% | **80%** | 8+ AI类型（含ReconAI、SupplyAwarenessAI、心理模型） |
| **部署阶段** | 20% | 90% | **90%** | CC2风格拖放+LOS预览 |
| **视觉质量** | 25% | 85% | **70%** | 增强像素艺术+阴影+粒子+三面板HUD+CC2色调（v0.4.16修正） |
| **战斗机制** | 20% | 95% | **80%** | 6级压制+隐蔽+姿态+驻守+建筑窗户弧度（v0.4.16修正） |
| **游戏设置** | 60% | 95% | **95%** | 5预设+独立经验/补给等级 |
| **音频** | 10% | 92% | **75%** | 18种武器音效+11环境音+6种BGM（v0.4.16修正） |
| **综合还原度** | **~45%** | **~88%**（高估） | **~75%** | 视觉70% / 机制80%，详见 [GAP_ANALYSIS.md](GAP_ANALYSIS.md) |

**核心进展**: v0.3.x 完成M1+M2全部修复、架构重构（DDD+模块化）、幽灵功能审计、视觉打磨。v0.4.x 完成视觉打磨、架构优化（GameLoop拆分、Domain层瘦身38.5%）。v0.5.x 完成 PixVoxel 精灵接入、isometric 清理、调色板修正、LOS/烟雾/天气/窗户射击弧/散兵坑战壕/AI侦察/AI心理模型/AI补给线意识。v0.6.x 完成 P0-P3 全部修复、9项源码bug修复、幽灵功能接入（ReconAI+SupplyAwarenessAI）、覆盖率提升（323新测试）、CI增强（radon复杂度门禁）。~6536个测试100%通过，490 E2E 验证在真实SDL环境下通过。

---

## 二、User Stories (33 条)

> **标注说明**: ✅ = 可用 | ⚠️ = 部分可用（部分 AC 未实现）| ❌ = 未实现
>
> **v0.6.10 核实更新**: P0 Bug (TD-021~025) 已在 v0.3.x 全部修复。GAP_ANALYSIS 确认 G1-G8/I1-I3/M1-M6/R1-R10/V-01~V-05 全部 RESOLVED ✅。v0.6.10 新增：8+ AI类型（含ReconAI、SupplyAwarenessAI、心理模型、补给线意识），幽灵功能全部接入，323新测试，CI radon复杂度门禁。原标注 "❌ 因 P0 Bug 阻塞" 已过时，本次同步为 ✅。

### 2.1 核心战斗系统 (US-COMBAT-001 ~ 005)

**US-COMBAT-001**: 作为玩家，我希望命令单位移动到指定位置，以便调整战术部署。 ✅
- AC1: 右键点击可通行地面显示移动路径预览
- AC2: 确认后单位沿A*路径移动
- AC3: 移动中单位无法攻击
- AC4: 不同地形移动速度不同

**US-COMBAT-002**: 作为玩家，我希望命令单位攻击敌方单位，以便消灭敌人。 ✅
- AC1: 右键点击敌方单位显示攻击锁定框
- AC2: 确认后单位自动开火
- AC3: 在射程外攻击时提示"超出射程"
- AC4: 命中时目标HP减少
- AC5: 未命中时产生压制效果

**US-COMBAT-003**: 作为玩家，我希望看到真实的弹道结算结果，以便理解战斗过程。 ✅
- AC1: 每次射击有命中/未命中判定
- AC2: 命中时有伤害浮动(±20%)
- AC3: 距离越远精度越低
- AC4: 掩体降低被击中概率
- AC5: 穿透力影响对掩体后目标的伤害

**US-COMBAT-004**: 作为玩家，我希望单位受伤后有明确的视觉反馈，以便掌握战场态势。 ✅
- AC1: HP条实时下降
- AC2: 受伤时单位闪白(1帧)
- AC3: 重伤时单位缩小
- AC4: 死亡时有消失动画
- AC5: 死亡后单位从游戏中移除

**US-COMBAT-005**: 作为玩家，我希望压制系统能影响敌方行动，以便在不歼灭敌人时也能获得战术优势。 ✅
- AC1: 未命中射击产生压制值
- AC2: 压制累积导致敌方进入SUPPRESSED状态
- AC3: SUPPRESSED状态下敌方命中率下降
- AC4: 压制随时间衰减
- AC5: 高压制可能导致敌方恐慌

### 2.2 单位与编组 (US-UNIT-001 ~ 005)

**US-UNIT-001**: 作为玩家，我希望创建和管理步兵班单位，以便构建战术基础。 ✅
- AC1: 步兵班默认10人
- AC2: 有HP/武器/士气属性
- AC3: 可以分配到不同Squad
- AC4: 班长阵亡时其他成员士气大幅下降

**US-UNIT-002**: 作为玩家，我希望管理机枪组单位，以便提供火力支援。 ✅
- AC1: 机枪组射速高于步枪班
- AC2: 机枪组需要2人操作
- AC3: 射击精度低于步枪(连发散大)
- AC4: 机枪组对步兵压制效果显著

**US-UNIT-003**: 作为玩家，我希望指挥官单位提供士气加成，以便维持部队凝聚力。 ✅
- AC1: 指挥官在附近时友军士气恢复+10
- AC2: 指挥官阵亡导致全squad额外-25士气
- AC3: 指挥官可以执行"集结"命令加速友军恢复

**US-UNIT-004**: 作为玩家，我希望通过编组(Squad)管理多个单位，以便高效指挥。 ✅
- AC1: 一个Squad包含2-6个单位
- AC2: Squad有统一的状态(交战/撤退/防御)
- AC3: 可以选择整个Squad下达命令
- AC4: Squad全员阵亡则Squad被歼灭

**US-UNIT-005**: 作为玩家，我希望载具单位(坦克)有乘员组系统，以便更真实地模拟装甲战。 ✅
- AC1: 坦克有车长/炮手/驾驶员
- AC2: 乘员伤亡影响坦克能力
- AC3: 坦克被毁时乘员可能幸存逃生(P3 Should)

### 2.3 AI 对手 (US-AI-001 ~ 004)

**US-AI-001**: 作为玩家，我希望敌方AI能自动做出合理的战术决策，以便获得有挑战性的游戏体验。 ✅
- AC1: AI使用行为树(BT)做决策
- AC2: AI会优先攻击视野内威胁最高的目标
- AC3: AI在劣势时会寻找掩体或撤退
- AC4: AI不会瞬间知道玩家位置(受FoW限制)

**US-AI-002**: 作为玩家，我希望AI的追击和攻击行为合理，以便感觉在与真人对战。 ✅
- AC1: AI追击时会沿路径移动而非穿墙
- AC2: AI进入射程后会开火并保持距离
- AC3: AI同时控制多个单位时有协同(不重叠站位)
- AC4: AI不会每帧改变决策(有决策冷却)

**US-AI-003**: 作为玩家，我希望AI会受到士气系统的影响，以便AI也有人性化弱点。 ✅
- AC1: AI单位同样受士气规则约束
- AC2: AI单位恐慌时会溃逃
- AC3: AI单位 routing时脱离AI控制
- AC4: AI指挥官阵亡会影响AI squad 行为

**US-AI-004**: 作为玩家，我希望AI有支援火力呼叫能力(迫击炮)，以便AI拥有完整的战术手段。 ✅
- AC1: AI可以呼叫间接火力打击玩家遮蔽位置
- AC2: 迫击炮有落弹延迟(非即时命中)
- AC3: 迫击炮弹药有限
- AC4: 迫击炮组需要暴露位置才能开火(P3 Should)

### 2.4 地形与地图 (US-MAP-001 ~ 004)

**US-MAP-001**: 作为玩家，我希望地图由不同类型的地形瓦片组成，以便产生丰富的战术变化。 ✅
- AC1: 至少支持12种地形类型(开阔地/道路/草地/林地/建筑/水域/树篱/墙等)
- AC2: 每种地形有不同的移动代价
- AC3: 林地和建筑提供掩体
- AC4: 水域和实心建筑不可通行

**US-MAP-002**: 作为玩家，我希望地形影响视线(LOS)，以便利用地形进行伏击。 ✅
- AC1: 林地和建筑阻挡视线
- AC2: 开阔地视线无遮挡
- AC3: 地形高度差影响视线(未来)
- AC4: 可以查看任意tile的LOS状态(debug)

**US-MAP-003**: 作为玩家，我希望加载自定义地图文件，以便扩展游戏内容。 ✅
- AC1: 地图数据存储为JSON格式
- AC2: JSON包含地形网格/出生点/目标点
- AC3: 加载时进行Schema校验
- AC4: 格式错误时给出明确错误信息

**US-MAP-004**: 作为玩家，我希望地图上有胜利目标点(Objective)，以便有明确的任务目标。 ✅
- AC1: 支持占领型目标(停留一定时间占领)
- AC2: 支援歼灭型目标(消灭区域内敌人)
- AC3: 目标点在HUD上清晰标识
- AC4: 占领进度可视化

### 2.5 UI / HUD (US-UI-001 ~ 005)

**US-UI-001**: 作为玩家，我希望有清晰的单位信息面板，以便了解选中单位的详细状态。 ✅
- AC1: 左侧面板显示单位名称/类型/HP条
- AC2: HP条颜色随血量变化(绿→黄→红)
- AC3: 显示当前士气值和状态
- AC4: 显示武器信息和剩余弹药
- AC5: 未选中时显示占位提示

**US-UI-002**: 作为玩家，我希望有小地图(Minimap)显示全局态势，以便掌握战场全局。 ✅
- AC1: 右上角显示140x140小地图
- AC2: 显示已探索区域和当前视野
- AC3: 友军蓝点/敌军红点
- AC4: 视野范围半透明覆盖
- AC5: 可按M键切换显示/隐藏

**US-UI-003**: 作为玩家，我希望底部有命令栏快速下达常用命令，以便高效操作。 ✅
- AC1: 显示[移动][攻击][停止][烟雾][防御]按钮
- AC2: 每个按钮有快捷键(M/A/S/K/D)
- AC3: 当前不可用的命令置灰
- AC4: 按钮有hover高亮效果
- AC5: 命令栏固定在屏幕底部

**US-UI-004**: 作为玩家，我希望顶部有状态栏显示任务信息，以便了解当前进度。 ✅
- AC1: 左侧显示任务名称
- AC2: 中间显示游戏时间和日期
- AC3: 右侧显示暂停/菜单按钮
- AC4: 暂停时游戏时间冻结
- AC5: 菜单可返回主菜单

**US-UI-005**: 作为玩家，我希望有Debug Overlay辅助开发调试，以便快速定位问题。 ✅
- AC1: 按~键切换三级debug信息
- AC2: Level 1显示FPS/UPS/Tile坐标/单位数
- AC3: Level 2增加单位状态标签/网格线/A*路径
- AC4: Level 3增加子系统耗时柱状图/内存用量

### 2.6 战役模式 (US-CAMP-001 ~ 003)

**US-CAMP-001**: 作为玩家，我希望有多关卡战役模式，以便体验连续的军事行动。 ✅
- AC1: 战役由多个连续关卡组成
- AC2: 每关结束后单位经验/损失继承到下一关
- AC3: 有战役总进度跟踪
- AC4: 关卡间可选择修整装备(P3 Should)

**US-CAMP-002**: 作为玩家，我希望可以保存和读取游戏存档，以便随时中断和恢复。 ✅
- AC1: 存档保存完整运行时状态
- AC2: 存档文件防篡改(HMAC签名)
- AC3: 读档时验证完整性
- AC4: 支持多个存档槽位
- AC5: 存档列表显示时间/关卡/进度摘要

**US-CAMP-003**: 作为玩家，我希望战役有关卡胜负条件判定，以便有明确的任务完成标准。 ✅
- AC1: 全歼敌军触发胜利
- AC2: 占领所有目标点触发胜利
- AC3: 我方全军覆没触发失败
- AC4: 超时未完成任务触发失败(P3 Should)

### 2.7 音效与反馈 (US-AUDIO-001 ~ 003)

**US-AUDIO-001**: 作为玩家，我希望关键操作有音效反馈，以便获得操作确认感。 ✅
- AC1: 选中单位时有短促音效
- AC2: 下达命令时有确认音效
- AC3: 射击时有开火音效
- AC4: 命中/未命中有不同音效
- AC5: 单位死亡有特殊音效

**US-AUDIO-002**: 作为玩家，我希望重要事件有视觉+听觉双重反馈，以便不会错过关键信息。 ✅
- AC1: 士气恐慌时显示"!"图标+警报声
- AC2: 胜利时显示大字VICTORY+胜利音乐
- AC3: 敌方发现时FoW边缘闪烁(P2 Should)

**US-AUDIO-003**: 作为玩家，我希望背景音乐增强沉浸感，以便更有氛围。 ✅
- AC1: 菜单/暂停界面有BGM
- AC2: 战斗中有紧张BGM
- AC3: BGM音量独立可控(P3 Should)

### 2.8 士气系统 (US-MORALE-001)

**US-MORALE-001**: 作为玩家，我希望士气系统影响单位行为，以便体现心理战要素。 ✅
- AC1: 士气正常值0-100
- AC2: <30进入恐慌状态(无法控制)
- AC3: <10进入溃逃状态(脱离指挥)
- AC4: 友军阵亡/受重创/指挥官 nearby 影响士气
- AC5: 士气自然恢复(远离战斗后)

### 2.9 视野系统 (US-FOW-001)

**US-FOW-001**: 作为玩家，我希望战争迷雾隐藏敌方位置，以便实现侦察战术。 ✅
- AC1: 仅显示己方视野内的敌方单位
- AC2: 已探索但不在视野的区域灰暗显示(可见地形但不见动态)
- AC3: 未探索区域完全黑暗
- AC4: 敌方同样受FoW限制(对称)
- AC5: FoW 每3-5帧更新一次(性能优化)

---

## 三、MoSCoW 优先级矩阵

> **数量说明**: MoSCoW 矩阵共 40 项（18 Must + 9 Should + 5 Could + 8 Won't），与 §二 33 User Stories 不一一对应。差异原因：MoSCoW 矩阵除了涵盖 §二 的 33 个 User Stories 外，还包含 §四 NFRs 中的功能性需求（如存档读档、快捷键、小地图）以及架构/基础设施层面的需求（如 LOS 系统、A*寻路）。这是 MoSCoW 优先级分析的标准实践——对需求全集（User Stories + NFRs + 架构需求）进行优先级分类，而非仅对 User Stories 分类。

| 优先级 | 含义 | 功能列表 |
|--------|------|---------|
| **Must** | v1.0 必须有 (18项) | 核心战斗(移动/射击/命中/伤害/死亡)、单位编组(选/分组/指挥)、基础AI(追踪/攻击/寻路)、地形地图(12种/加载/LOS)、HUD骨架(面板/命令栏/顶栏)、视野系统、士气系统、存档读档、胜负判定 |
| **Should** | v1.0 应该有 (9项) | 支援火力(迫击炮)、载具乘员、战役模式(多关/继承)、音效反馈(操作/事件)、A*路径平滑、Debug Overlay三级、小地图、快捷键完整、单位面板详细信息 |
| **Could** | v1.1/v2.0 候选 (5项) | 回放系统、Mod支持、载具系统完整、物理 debris、天气系统 |
| **Won't** | 本期不做 (8项) | 多人联机、3D渲染、物理引擎(Physix)、语音聊天、Steam成就、云存档、编辑器工具、Linux/Windows支持 |

---

## 四、非功能需求 NFRs (25 条)

### NFR-PERF 性能 (8条)

- **PERF-01**: 64x64地图+20单位稳定≥30FPS逻辑帧率
- **PERF-02**: 128x128地图+50单位稳定≥20FPS
- **PERF-03**: 启动时间≤3秒(冷启动)
- **PERF-04**: 内存占用≤500MB
- **PERF-05**: FPS渲染帧率目标60FPS
- **PERF-06**: A*寻路(128x128)单次调用≤50ms
- **PERF-07**: FoW更新(50单位)≤10ms/次
- **PERF-08**: 存档写入≤1秒/读取≤500ms

### NFR-USA 可用性 (5条)

- **USA-01**: 操作响应时间<100ms(输入→视觉反馈)
- **USA-02**: 新手可在30分钟内学会基本操作
- **USA-03**: 所有错误有明确的文字/视觉提示
- **USA-04**: ESC键可随时暂停/退出
- **USA-05**: HUD信息密度适中(不过载也不缺失)

### NFR-MAINT 可维护性 (6条)

- **MAINT-01**: PEP 8 编码规范
- **MAINT-02**: 所有公共API有类型注解(type hints)
- **MAINT-03**: 测试覆盖率≥70%
- **MAINT-04**: 文档覆盖所有公开接口
- **MAINT-05**: 依赖版本锁定(requirements.lock/pyproject.toml hashes)
- **MAINT-06**: CI流水线自动跑测试+lint

### NFR-SEC 安全性 (5条)

- **SEC-01**: 存档文件HMAC-SHA256签名防篡改
- **SEC-02**: 所有外部JSON输入Pydantic校验
- **SEC-03**: 地图尺寸上限防止OOM(≤256x256)
- **SEC-04**: dev-mode参数跳过安全检查用于调试
- **SEC-05**: 依赖库定期扫描CVE(pip-audit)

### NFR-COMP 兼容性 (5条)

- **COMP-01**: macOS 12+ (Monterey及以后)
- **COMP-02**: Python 3.11+
- **COMP-03**: Pygame 2.2+
- **COMP-04**: 分辨率支持 720p 到 4K
- **COMP-05**: ARM64 (Apple Silicon) 原生运行

---

## 五、约束条件

- **技术**: Python 3.11+ / Pygame 2 / numpy / 最少外部依赖
- **时间**: 18-20 周单人开发
- **资源**: 单人 / 无美术资源 / 无音效素材 / M1 Mac硬件
- **美术**: 几何原型起步 → 32x32像素画渐进 → 精灵完善
- **内容**: 仅二战欧洲战场 "市场花园行动" (1944.9)

---

## 六、Gate 门禁文档 (P1→P2 评审基准 20 条)

列出所有 Must 级功能的量化验收标准：

### 核心战斗系统验收标准 (5条)

1. **GATE-COMBAT-01**: 单位移动功能 — 单位能响应右键点击沿A*路径移动到目标位置，路径预览正确显示，不同地形移动速度差异可测（开阔地1.0x / 林地0.6x / 道路1.3x）
2. **GATE-COMBAT-02**: 攻击与命中判定 — 单位能在射程内自动开火，命中率公式可复现（基础命中率 - 距离衰减 + 掩体修正），命中时HP正确减少，伤害浮动范围±20%可验证
3. **GATE-COMBAT-03**: 弹道结算可视化 — 每次射击事件记录完整日志（射手/目标/距离/命中结果/伤害值/是否穿透），未命中时压制值正确累积
4. **GATE-COMBAT-04**: 单位状态反馈 — HP条实时更新<100ms延迟，受伤闪白效果1帧时长，死亡动画200ms内完成，死亡后实体从游戏循环移除无残留
5. **GATE-COMBAT-05**: 压制系统运作 — 连续未命中射击累积压制值>50触发SUPPRESSED状态，该状态下命中率下降30%，压制值每秒衰减10点

### 单位与编组验收标准 (3条)

6. **GATE-UNIT-01**: 步兵班创建与管理 — 步兵班默认10人配置正确加载，HP/武器/士气属性可查询，班长阵亡事件触发全队士气-30
7. **GATE-UNIT-02**: Squad编组功能 — 单个Squad可容纳2-6个单位，Squad统一状态切换（交战/撤退/防御）生效，批量命令下发到所有成员
8. **GATE-UNIT-03**: 指挥官士气加成 — 指挥官半径3格内友军每tick士气恢复+1（等效+10/s），指挥官死亡广播事件触发全局-25士气惩罚

### AI 对手验收标准 (3条)

9. **GATE-AI-01**: 行为树决策 — AI行为树至少包含Selector/Sequence/Condition/Action四种节点类型，决策输出日志可追踪，AI不违反FoW规则（不攻击未发现的敌人）
10. **GATE-AI-02**: 寻路与追击 — AI单位使用A*算法寻路，路径不穿越不可通行地形，追击行为持续至目标离开视野或AI进入射程
11. **GATE-AI-03**: 决策冷却机制 — AI决策间隔≥500ms（不每帧重新评估），多单位协同站位间距≥2格避免重叠

### 地形与地图验收标准 (4条)

12. **GATE-MAP-01**: 地形瓦片系统 — 至少12种地形类型实现，每种地形移动代价配置可查，掩体等级影响命中率公式参数化
13. **GATE-MAP-02**: LOS视线计算 — Bresenham射线投射算法实现正确，林地/建筑完全阻挡视线（透射率0%），开阔地无遮挡（透射率100%）
14. **GATE-MAP-03**: JSON地图加载 — 地图JSON通过Schema校验（使用data/maps/_schema.json），格式错误时抛出明确异常含行列号，加载失败不崩溃
15. **GATE-MAP-04**: 胜利目标点 — Objective组件支持CAPTURE/ELIMINATE两种类型，占领计时器正确累加（友军在场时+1/tick），HUD显示当前占领百分比

### UI/HUD 验收标准 (3条)

16. **GATE-UI-01**: 单位信息面板 — 左侧面板实时显示选中单位属性（名称/类型/HP/士气/武器），HP条颜色阈值：>70%绿 / 30-70%黄 / <30%红，未选中时显示"Select a unit"占位文本
17. **GATE-UI-02**: 命令栏交互 — 底部固定5个命令按钮（Move/Attack/Stop/Smoke/Defend），快捷键M/A/S/K/D绑定正确，禁用态置灰且不可点击，hover高亮色差明显
18. **GATE-UI-03**: 顶部状态栏 — 任务名左对齐，游戏时间居中显示格式HH:MM，暂停按钮点击后game_loop.freeze()调用成功，菜单按钮弹出确认对话框

### 视野系统验收标准 (1条)

19. **GATE-FOW-01**: 战争迷雾实现 — 仅渲染视野内敌方单位（visibility_check通过），已探索区域alpha=128半透明，未探索区域alpha=255全黑，FoW更新频率≤5帧/次（性能达标）

### 存档与胜负验收标准 (1条)

20. **GATE-SAVE-01**: 存档读写完整性 — 存档JSON包含完整运行时快照（units/map/time/state），HMAC-SHA256签名验证通过，读取后游戏状态与保存时刻一致（误差<1tick），支持≥3个存档槽位独立存储

---

## 七、风险清单 (15 条)

识别需求层面的主要风险及缓解措施：

### 技术风险 (5条)

| ID | 风险描述 | 概率 | 影响 | 缓解措施 |
|----|---------|------|------|---------|
| RISK-TECH-01 | Pygame性能瓶颈导致大地图掉帧 | 中 | 高 | 提前做prototype benchmark；关键路径用numpy/numba加速；降级策略：减小地图尺寸或单位数量 |
| RISK-TECH-02 | A*寻路在大地图上耗时超标 | 中 | 中 | 实现分层寻路（Hierarchical Pathfinding）；缓存常用路径；限制同时寻路请求数 |
| RISK-TECH-03 | FoW实时计算开销过大 | 低 | 高 | 采用分块更新（Chunked Update）；降低更新频率至3-5帧；预计算静态遮挡 |
| RISK-TECH-04 | 存档文件体积膨胀导致IO慢 | 低 | 中 | 使用增量存档（Delta Save）；压缩JSON（gzip）；清理历史存档 |
| RISK-TECH-05 | numpy/numba在ARM64上的兼容性问题 | 低 | 中 | 锁定依赖版本；提前在M1 Mac上验证CI；准备纯Python fallback |

### 资源风险 (3条)

| ID | 风险描述 | 概率 | 影响 | 缓解措施 |
|----|---------|------|------|---------|
| RISK-RES-01 | 无美术素材导致视觉效果差 | 高 | 中 | 几何原型阶段接受简陋外观；逐步迭代像素画；开源CC2 sprite资源（如有） |
| RISK-RES-02 | 无音效素材导致沉浸感不足 | 中 | 低 | 使用合成音效（pygame生成）；P2阶段再引入真实音效；优先保证核心玩法 |
| RISK-RES-03 | 单人开发工期延误 | 高 | 高 | MoSCoW优先级严格排序；Must功能优先砍Could/Won't；每周复盘进度调整计划 |

### 需求风险 (4条)

| ID | 风险描述 | 概率 | 影响 | 缓解措施 |
|----|---------|------|------|---------|
| RISK-REQ-01 | CC2原版机制理解偏差导致还原度不足 | 中 | 高 | 反复观看原版 gameplay 视频；参考CC2 mod社区文档；保留设计决策记录（ADR） |
| RISK-REQ-02 | 士气系统参数调优困难 | 中 | 中 | 设计可配置的参数表（toml/yaml）；提供debug模式实时调参；A/B测试不同参数组合 |
| RISK-REQ-03 | AI行为树复杂度失控 | 中 | 中 | 从最小 viable BT开始（3-4个节点）；逐步扩展；单元测试每个BT节点 |
| RISK-REQ-04 | 地形类型扩展需求蔓延 | 低 | 中 | 严格控制在12种以内（Must）；新增地形走Could流程；地图编辑器延后 |

### 进度风险 (3条)

| ID | 风险描述 | 概率 | 影响 | 缓解措施 |
|----|---------|------|------|---------|
| RISK-SCHED-01 | L1 MVP延期导致后续阶段压缩 | 中 | 高 | L1设定硬截止日（Week 4）；MVP scope严格冻结；每日站会跟踪阻塞项 |
| RISK-SCHED-02 | Bug修复占用过多开发时间 | 中 | 中 | TDD先行写测试；Code Review自检；预留20%缓冲时间给bug fix |
| RISK-SCHED-03 | 功能镀金（Gold Plating）导致范围膨胀 | 中 | 中 | 每个User Story明确定义Done标准；PR前对照MoSCoW审查；拒绝非优先级需求 |

---

## 八、Implementation Progress / 阶段进度

| 阶段 | 状态 | 说明 | 测试数 |
|------|------|------|--------|
| P0-Foundation | ✅ Complete | 基础设施: Vec2/TileCoord/TerrainType/StateMachine/RandomContext/EventBus | ~85 tests |
| P1-Core | ✅ Complete | 核心系统: BallisticEngine/MoraleCalculator/PathFinder/FogOfWar/CombatResolver/BehaviorTree | ~180 tests |
| P1-AI | ✅ Complete | AI对手系统: 行为树决策/寻路追击/决策冷却/FoW限制 | ~45 tests |
| P1-VM | ✅ Complete | 视野与地图: 战争迷雾/LOS视线/12种地形/JSON地图加载/Objective目标点 | ~40 tests |
| P1-HD | ✅ Complete | HUD骨架: 单位信息面板/命令栏/顶部状态栏/Debug Overlay三级 | ~35 tests |
| P1-PixelArt | ✅ Complete | 像素画渲染: 32x32精灵/地形瓦片/单位动画/特效原型 | ~25 tests |
| P1-Integration | ✅ Complete | 集成测试: 存档读写/HMAC签名/完整战斗流程/E2E场景 | ~48 tests |
| P1-SaveLoad | ✅ Complete | 存档系统: SecureIO/HMAC-SHA256/多槽位/防篡改校验 | ~32 tests |
| P1-UIInput | ✅ Complete | 输入系统: InputHandler/CommandBus/鼠标指挥/快捷键绑定 | ~28 tests |
| P1-Campaign | ✅ Complete | 战役模式: 多关卡继承/胜负判定/任务目标/占领计时器 | ~22 tests |
| P1-MoraleFull | ✅ Complete | 士气全量: 事件权重/状态转换(4态)/恐慌传染/tick恢复/clamping | ~30 tests |
| P2-CombatLoop | ✅ Complete | 完整战斗循环: PlayerCommand→_execute_attack→BallisticEngine→UnitAttacked→health.take_damage→pending_effects→spawn_hit_flash/damage_number/muzzle_flash/death_effect | 13 integration tests |
| P2-Audio | ✅ Complete | 程序化音效系统: ProceduralSoundGenerator(8种波形) + SoundSystem(23种SoundType) + UI/战斗/脚步音效 | 21 tests |
| P3-A-Systems   | ✅ Complete | 胜利条件评估(VictoryConditionEvaluator 5种条件) + BattleStats战斗统计 + 战后统计面板 + GameLoop集成(9处修改) | 39 tests |
| P3-B-Visual    | ✅ Complete | 6种单位动画(UnitAnimator IDLE/WALK/SHOOT/DEATH/HIT_REACT/RELOAD) + ScreenShake屏幕震动 + 增强粒子系统(8种ParticleEmitter类型) + 伤害数字分级渲染 | 52 tests |
| P3-C-Content   | ✅ Complete | 3种新单位(TANK/SNIPER/MEDIC含像素精灵+属性模板UNIT_TEMPLATES) + 2种新地形(CRATER/SWAMP含瓦片生成器) + 战役系统(CampaignManager+3关任务定义) | 31 tests |
| P3-D-Save      | ✅ Complete | SecureSaveManager(HMAC-SHA256防篡改) + 8槽位JSON存档 + SaveMetaData + GameLoop集成(quick_save/quick_load/list_saves) | 26 tests |
| P3-Fix-Bugs    | ✅ Complete | 4个关键Bug修复: BallisticEngine武器补全(3种tank_cannon/sniper_rifle/mortar) + quick_load状态恢复(_restore_state_from_dict) + AI循环边界修复(2处CommanderAI+TacticalAdvisor) + main.py入口点重写(GameLoop无参构造) | 0 new tests (1088 total) |
| P4.1-Decompose | ✅ Complete | GameLoop God Object拆分(880→356行/-59%): RenderPipeline+CombatDirector+InputRouter+SaveController | ~75 new tests |
| P4.1-Settings   | ✅ Complete | Settings菜单(4Tab: General/Audio/Controls/Gameplay) + 62测试 | 62 tests |
| P4.1-Security   | ✅ Complete | HMAC密钥环境变量化 + 输入边界校验 + secrets.toml模板 | 13 tests |
| P4.2-A-Perf     | ✅ Complete | 性能优化: TileCache地形瓦片预缓存 + AI节流10Hz + 粒子对象池 | ~45 tests |
| P4.2-B-Tutorial | ✅ Complete | 教程/提示系统: 首次启动引导TutorialOverlay + 上下文提示HintManager | ~28 tests |
| P4.2-C-Missions | ✅ Complete | 新任务内容: Mission 4 Night Assault夜战 + Mission 5 Armored Column反坦克 | ~35 tests |
| P4.2-D-Maps     | ✅ Complete | 新地图数据: night_map.json + road_ambush.json + bridge_assault.json + defense_line.json | ~12 tests |
| P4.3-A-Night    | ✅ Complete | 夜战机制: Environment+FogOfWar夜间修正+照明弹+潜行加成 | ~8 tests |
| P4.3-B-Armor    | ✅ Complete | 反坦克装甲: 装甲剖面(正/侧/后)+角度穿透计算 | ~19 tests |
| P4.3-C-Visual   | ✅ Complete | 视觉增强: WeatherRenderer(雨/雾/夜)+粒子预设(爆炸/血液) | ~15 tests |
| QG-Docs         | ✅ Complete | 质量门禁: 文档统一v1.6(14文件三语)+代码质量修复+E2E(+61) | +61 tests |
| P8-MapsCampaign | ✅ Complete | 9+Arnhem战区新地图/四层战役架构(campaign_four_layer.py)/补给线机制(SupplySystem 70%)/部署阶段UI集成 | ~334 tests |
| P9-AI-P0        | ✅ Complete | P0 AI行为(7项): 弹药拾取/武器搜刮/投降/武器卡壳/烟雾部署/班降解/NCO集结 | ~180 tests |
| P9-GameSettings | ✅ Complete | 新游戏设置系统: 5预设(RECRUIT/EASY/NORMAL/HARD/VETERAN)+独立经验/补给等级每方 | ~85 tests |
| P9-Campaign     | ✅ Complete | 战役完成: 3 Sectors/7 Operations/29 Battles/63 Maps(全部战役引用已解决) | ~65 tests |

**当前版本**: v0.7.2
**测试总数**: ~6138 tests
**最后更新**: 2026-07-17

---

## 八点五、任务列表 (Missions)

| Mission ID | 任务名称 | 地图文件 | 难度 | 玩家阵营 | 敌方阵营 | 胜利条件 | 状态 |
|------------|----------|----------|------|----------|----------|----------|------|
| M1 | Tutorial Training | tutorial.json | ⭐ Easy | Allies (US) | Axis (GE) | 占领中心建筑 | ✅ Complete |
| M2 | Bridge Assault | bridge_assault.json | ⭐⭐ Medium | Allies (US) | Axis (GE) | 控制桥梁 + 歼灭敌军 | ✅ Complete |
| M3 | Road Ambush | road_ambush.json | ⭐⭐⭐ Hard | Allies (US) | Axis (GE) | 伏击敌军车队 | ✅ Complete |
| M4 | Night Assault | night_map.json | ⭐⭐⭐ Hard | Allies (US) | Axis (GE) | 夜间突袭占领目标 | ✅ Complete (P4.2-C) |
| M5 | Armored Column | defense_line.json | ⭐⭐⭐⭐ Expert | Allies (US) | Axis (GE) | 反坦克防御战 | ✅ Complete (P4.2-C) |
| M6 | Son | son.json | ⭐⭐⭐ Hard | Allies (US) | Axis (GE) | 占领Son桥梁 | ✅ Complete (P7) |
| M7 | Veghel | veghel.json | ⭐⭐⭐ Hard | Allies (US) | Axis (GE) | 突破Veghel防线 | ✅ Complete (P7) |
| M8 | Grave | grave.json | ⭐⭐⭐⭐ Expert | Allies (US) | Axis (GE) | Grave渡河战 | ✅ Complete (P7) |
| M9 | Nijmegen | nijmegen.json | ⭐⭐⭐⭐ Expert | Allies (US) | Axis (GE) | Waal河强渡 | ✅ Complete (P7) |
| M10 | Arnhem | arnhem.json | ⭐⭐⭐⭐⭐ Legend | Allies (US) | Axis (GE) | Arnhem最后突击 | ✅ Complete (P7) |

### 任务详细说明

**Mission 1 - Tutorial Training**
- **目标**: 新手教学任务，学习基本操作
- **单位**: 2x Rifle Squad, 1x MG Team vs 2x Rifle Squad
- **特色**: 引导提示系统，逐步教学

**Mission 2 - Bridge Assault**
- **目标**: 攻占并控制战略桥梁
- **单位**: 3x Rifle Squad, 1x Sniper, 1x MG Team vs 4x Rifle Squad, 1x MG Team
- **特色**: 桥梁控制机制，时间压力

**Mission 3 - Road Ambush**
- **目标**: 在道路伏击敌方补给车队
- **单位**: 2x Rifle Squad, 1x Bazooka Team vs 3x Truck Convoy, 2x Escort
- **特色**: 伏击战术，动态目标

**Mission 4 - Night Assault** (P4.2-C 新增)
- **目标**: 夜间条件下突袭并占领敌方指挥部
- **单位**: 4x Rifle Squad, 2x MG Team, 1x Medic vs 5x Rifle Squad, 2x MG Bunker
- **特色**: 视野受限(夜战)，潜行机制，照明弹效果
- **测试覆盖**: 35 tests (夜战逻辑/视野系统/AI夜间行为)

**Mission 5 - Armored Column** (P4.2-C 新增)
- **目标**: 防御防线抵御敌方装甲部队进攻
- **单位**: 3x Rifle Squad, 2x AT Team, 1x Tank vs 4x Tank, 3x Infantry
- **特色**: 反坦克战术，载具战斗，阵地防御
- **测试覆盖**: 35 tests (反坦克逻辑/载具AI/防御阵型)

---

## 八点六、地图列表 (Maps) — 63 Maps

> **注**: v0.6.10 实际地图数为 63 张（含历史+通用+战役引用），由 `find src/pycc2/data/maps -name "*.json" | wc -l` 验证。下表展示代表性地图；完整列表见 `src/pycc2/data/maps/`。

| 地图ID | 文件名 | 尺寸 | 地形类型数 | 使用任务 | 特色 | 状态 |
|--------|--------|------|-----------|----------|------|------|
| MAP-01 | tutorial.json | 20×20 | 8 | M1 Training | 开阔地形，简单布局，教学用 | ✅ Complete |
| MAP-02 | bridge_assault.json | 32×32 | 10 | M2 Bridge Assault | 河流+桥梁，城市废墟 | ✅ Complete |
| MAP-03 | road_ambush.json | 40×24 | 11 | M3 Road Ambush | 林地+道路，伏击地形 | ✅ Complete |
| MAP-04 | night_map.json | 36×36 | 12 | M4 Night Assault | 夜间战场，建筑物密集 | ✅ Complete |
| MAP-05 | defense_line.json | 48×32 | 12 | M5 Armored Column | 开阔平原+防御工事 | ✅ Complete |
| MAP-06 | son.json | 44×36 | 12 | M6 Son | Son小镇+桥梁争夺 | ✅ Complete |
| MAP-07 | veghel.json | 52×40 | 12 | M7 Veghel | Veghel十字路口防御战 | ✅ Complete |
| MAP-08 | grave.json | 48×48 | 12 | M8 Grave | Grave渡河+铁路桥 | ✅ Complete |
| MAP-09 | nijmegen.json | 64×48 | 12 | M9 Nijmegen | Waal河强渡+城市巷战 | ✅ Complete |
| MAP-10 | arnhem.json | 64×64 | 12 | M10 Arnhem | Arnhem最终突击+复杂地形 | ✅ Complete |
| MAP-11~28 | (P8新增18张) | 32×32~64×64 | 12 | 战役各Battle | Arnhem战区地图+战役引用地图(P8补全) | ✅ Complete |

### 地图技术规格

**通用特性:**
- JSON格式存储，Schema校验通过 `_schema.json`
- 支持12种地形类型 (GRASS/ROAD/WATER/TREE/HEDGE/WALL/BUILDING/SOLID_BUILDING/CRATER/SWAMP/BRIDGE/RUBBLE)
- 每个tile包含：地形类型、移动代价、掩体等级、通行性
- 出生点和目标点预定义

**P4.2-D 新增地图详情:**

*night_map.json (夜战地图)*
- 尺寸: 36×36 tiles
- 特色地形: 密集建筑群(30%)，狭窄街道，照明区域
- 视野设置: 基础视野-40%，照明弹临时+60%
- AI行为: 巡逻模式，听觉侦测增强

*road_ambush.json (道路伏击)*
- 尺寸: 40×24 tiles
- 特色地形: 林地走廊(50%)，道路贯穿，伏击点
- 战术要素: 高地优势，隐蔽位置

*bridge_assault.json (桥梁突击)*
- 尺寸: 32×32 tiles
- 特色地形: 河流分割，桥梁瓶颈，两岸建筑
- 战术要素: 桥梁控制，渡河战术

*defense_line.json (防御战线)*
- 尺寸: 48×32 tiles
- 特色地形: 开阔平原(60%)，战壕网络，掩体分布
- 战术要素: 防御纵深，反坦克位置，火力覆盖

---

## 九、CC2 Fidelity Gap Analysis (CC2还原度差距分析)

基于对原版 Close Combat 2: A Bridge Too Far 的全面对比分析（详见 [GAP_ANALYSIS.md](GAP_ANALYSIS.md)）：

### 系统还原度总览 (v0.6.10 更新 — 与文档头部一致)

> **⚠️ v0.4.16 诚实修正后数据**：原 ~88% 还原度经代码审核严重高估。下表已与 PRD 头部 "~75%（视觉70% / 机制80%）" 对齐。详细差距分析见 [GAP_ANALYSIS.md](GAP_ANALYSIS.md)。

| 维度 | CC2原版 (1997) | PyCC2当前 | 评级 |
|------|---------------|----------|------|
| **地图库** | 25-30张历史地图 | 63张地图，纹理增强 | ✅ 95% |
| **战役结构** | 四层架构 | 四层架构+日简报+继承+结束画面 | ✅ 98% |
| **武器系统** | ~50种武器 | 69种武器，效果已验证 | ✅ 95% |
| **单位多样性** | 130+单位 | 277种模板+精灵渲染+炮塔旋转 | ✅ 90% |
| **AI战术** | 成熟行为树 | 8+ AI类型（含ReconAI、SupplyAwarenessAI、心理模型） | 🟡 80% |
| **部署阶段** | 完整拖放部署 | CC2风格拖放+LOS预览 | ✅ 90% |
| **视觉质量** | 1997像素艺术 | 增强像素艺术+阴影+粒子+三面板HUD+CC2色调（v0.4.16修正） | 🟡 70% |
| **战斗机制** | 基础压制+士气 | 5级士气+压制+隐蔽+姿态+驻守+建筑窗户弧度（v0.4.16修正） | 🟡 80% |
| **游戏设置** | 基础难度选择 | 5预设+独立经验/补给等级 | ✅ 95% |
| **音频** | 完整音效+语音+BGM | 18种武器音效+11环境音+6种BGM（v0.4.16修正） | 🟡 75% |
| **综合还原度** | — | **~75%** | 🟡 视觉70% / 机制80%（v0.4.16 诚实修正） |

### v0.3.x 关键进展

1. **P0 Bug清零** — 全部5个P0 Bug已修复，游戏完全可玩
2. **幽灵功能审计** — 发现并修复3个幽灵功能（PostProcessingEffects/WeatherOverlay/FadeTransition），所有关键渲染管线已激活
3. **架构重构** — EnhancedRenderer拆分(2243→943行)、GameLoop拆分(880→356行)、DDD层解耦(违规-39%)
4. **视觉打磨** — 死亡淡出、屏幕闪光、移动平滑、UI过渡动画、天气叠加、弹壳弹出、按钮反馈
5. **性能优化** — SurfacePool统一(6/6)、脏矩形渲染、地形缓存、坦克旋转缓存、视口裁剪
6. **AI战斗修复** — AI单位现在通过CombatDirector正确执行攻击，游戏可对AI进行战斗
7. **音频激活** — EnvironmentalAudioSystem 11种环境音效已激活，程序化武器音效扩展至7种

### 推进计划（详见 [ROADMAP.md](ROADMAP.md)）

| Phase | 名称 | 目标还原度 | 关键交付物 | 状态 |
|-------|------|-----------|-----------|------|
| P0-Fix | P0致命Bug修复 | 45%→55% | 修复5个P0 Bug使游戏可玩 | ✅ 5/5 已修复 (v0.3.x, TD-021~025) |
| P8 | 地图与战役补全 | 55%→70% | 9+新地图/四层战役/补给线/部署UI | ✅ 已完成 (v0.3.x, G1-G8/I1-I3/M1-M6 RESOLVED) |
| P9 | AI战术提升+新游戏设置 | 70%→80% | P0 AI行为(7项)/5预设游戏设置/战役完成 | ✅ 已完成 (v0.3.x, TD-023 AI导入修复) |
| P10 | P1 AI行为 | 80%→85% | 战壕挖掘/建筑清理/炮兵呼叫/医疗AI/MG接管/命令服从/夜间潜行/刺刀近战 | ✅ 已完成 (v0.4.3, TacticExecutor 32 handler) |
| P11 | 音频与体验 | 85%→90% | MG42声音/语音命令/BGM | ✅ 已完成 (v0.3.x, TD-030 音频修复) |
| P12 | 集成与发布 | ≥90% | 系统集成/端到端测试/打包 | ✅ 已完成 (v0.3.11, TD-033 E2E 425 tests) |

---

## 十、Revised Roadmap (修订路线图 P0-Fix→P12)

基于DevSquad批判性Review，项目路线图已修订。核心变化：新增P0-Fix阶段，还原度从~97%修正为~45%。

### 阶段概览

| 阶段 | 名称 | 目标 | 关键交付物 | 状态 |
|------|------|------|-----------|------|
| **P0-Fix** | P0致命Bug修复 | 游戏可玩 | 修复5个P0 Bug(display_name/属性名/AI导入/set_mode/旧UI清理) | ✅ 5/5 已修复 (v0.3.x) |
| **P8** | 地图与战役补全 | CC2还原度 55%→70% | 9+新地图/四层战役/补给线/部署UI | ✅ 已完成 (v0.3.x) |
| **P9** | AI战术提升+新游戏设置 | CC2还原度 70%→80% | P0 AI行为(7项)/5预设游戏设置/战役完成 | ✅ 已完成 (v0.3.x) |
| **P10** | P1 AI行为 | CC2还原度 80%→85% | 战壕挖掘/建筑清理/炮兵呼叫/医疗AI/MG接管/命令服从/夜间潜行/刺刀近战 | ✅ 已完成 (v0.4.3) |
| **P11** | 音频与体验 | CC2还原度 85%→90% | MG42声音/语音命令/BGM | ✅ 已完成 (v0.3.x) |
| **P12** | 集成与发布 | CC2还原度 ≥90% | 系统集成/端到端测试/打包 | ✅ 已完成 (v0.3.11) |

### 依赖关系

```
P0-Fix (5个P0 Bug) ──→ P8 (地图+战役集成验证) ──→ P9 (AI+游戏设置集成验证) ──→ P10 (P1 AI) ──→ P11 (音频) ──→ P12 (集成)
  ✅ 已完成 (v0.3.x)          ✅ 已验证                    ✅ 已验证
```

**关键路径**: P0-Fix → P8(验证) → P9(验证) → P10 → P11 → P12 (顺序执行)

### 版本目标

| 版本 | 代号 | 阶段完成 | 测试目标 | CC2还原度 | 状态 |
|------|------|----------|----------|-----------|------|
| v0.5 | **Honest Baseline** | P0-Fix完成 | ~2770 | ~55% | ✅ 5/5 已修复 (v0.3.x, TD-021~025) |
| v0.6.10 | **Beta Candidate** | P0-Fix→P12全部完成 | ~6536 | ~75% | ✅ Current (v0.5.0~v0.6.10) |
| v0.9 | **Oosterbeek** | 视觉打磨+内容扩展 | ~7000 | ~80% | 待开始 |
| v1.0 | **A Bridge Too Far** | 集成+发布 | ~7500 | ≥90% | 待开始 |

> **注**: 原 v0.5 "🟡 3/5已修复" 状态已过时——P0-Fix 5/5 全部在 v0.3.x 完成。原 v1.0 测试目标 "~3200" 已被 v0.6.10 实际 6536 超越。详见 [ROADMAP.md](ROADMAP.md)。

→ See [ROADMAP.md](ROADMAP.md) for full details (phase deliverables, gate criteria, risk register)
→ See [ISSUES.md](ISSUES.md) for current problems and countermeasures
→ See [TECH_DEBT.md](TECH_DEBT.md) for technical debt tracking

---

## 附录：术语表

| 术语 | 全称 | 定义 |
|------|------|------|
| RTT | Real-Time Tactics | 即时战术游戏 genre，强调实时指挥而非动作操作 |
| MVP | Minimum Viable Product | 最小可行产品，具备核心可玩性的最早版本 |
| FoW | Fog of War | 战争迷雾，隐藏未探索区域的游戏机制 |
| LOS | Line of Sight | 视线，单位能否看到目标的几何计算 |
| A* | A-Star Algorithm | 启发式寻路算法 |
| BT | Behavior Tree | 行为树，AI决策的层次化结构 |
| Squad | 编组 | 多个单位的战术集合，统一指挥 |
| Suppression | 压制 | 未命中火力造成的心理压力效果 |
| Morale | 士气 | 单位心理状态数值，影响行为可靠性 |
| AC | Acceptance Criteria | 验收标准，User Story的完成定义 |
| NFR | Non-Functional Requirement | 非功能性需求（性能/安全/可用性等） |
| PRD | Product Requirements Document | 产品需求规格说明书 |
| Gate | 门禁 | 阶段评审的量化准入标准 |
| MoSCoW | Must/Should/Could/Won't | 优先级分类方法 |
| HMAC | Hash-based Message Authentication Code | 基于哈希的消息认证码，用于防篡改 |
| PEP 8 | Python Enhancement Proposal 8 | Python编码风格指南 |
| Schema | 数据模式 | JSON结构定义与校验规范 |

---

## 十一、CC2 Fidelity Update (v0.6.10 进展总结)

### P5 Campaign Core 完成情况

| 组件 | 状态 | 测试数 | 说明 |
|------|------|--------|------|
| CampaignState | ✅ Complete | ~45 | 跨战斗状态容器，单位名册/经验/弹药/作战日 |
| BattleResult | ✅ Complete | ~30 | 战斗结果记录: KIA/WIA/弹药消耗/目标占领 |
| UnitVeterancy | ✅ Complete | ~55 | 经验等级: Green→Veteran→Elite→Crack |
| StrategicMap | ✅ Complete | ~40 | Market Garden走廊可视化 |
| OperationTimeline | ✅ Complete | ~35 | Day 1-6作战时间线 |
| **P5 合计** | **✅ Complete** | **~205** | Campaign系统达到60%还原度 |

### P6 Combat Depth 完成情况

| 组件 | 状态 | 测试数 | 说明 |
|------|------|--------|------|
| Swiss Cheese Damage | ✅ Complete | ~60 | 概率性伤亡模型(SquadMember) |
| FatigueSystem | ✅ Complete | ~45 | 战斗疲劳衰减与恢复 |
| ExperienceComponent | ✅ Complete | ~40 | 长期经验追踪与老兵加成 |
| AfterActionReport | ✅ Complete | ~35 | 战后统计AAR UI |
| TimeControl | ✅ Complete | ~25 | 暂停/0.5x/1x/2x 速度控制 |
| **P6 合计** | **✅ Complete** | **~205** | Combat系统达到85%还原度 |

### P7 Content Expansion 完成情况

| 内容 | 状态 | 数量 | 说明 |
|------|------|------|------|
| 新任务 M6-M10 | ✅ Complete | 5 missions | Son/Veghel/Grave/Nijmegen/Arnhem |
| 新地图 MAP-06~10 | ✅ Complete | 5 maps | 44×44 到 64×64 尺寸 |
| 历史真实性增强 | ✅ Complete | — | OOB/武器规格/任务简报 |
| **P7 合计** | **✅ Complete** | **~189 tests** | 内容扩展完成 |

### 整体进度（v0.6.10 更新 — 与 §一点六 对齐）

> **⚠️ v0.4.16 诚实修正后数据**：原声称 "Combat 65%→140%, Overall 47%→97%" 严重高估（>100% 不合逻辑）。已修正为基于代码证据的真实数据。

- **Campaign 还原度**: 30% → **98%** (+68%, 四层架构+继承+日简报+结束画面)
- **Combat 还原度**: 20% → **80%** (+60%, 5级士气+压制+隐蔽+姿态+驻守，v0.4.16修正)
- **AI 还原度**: 15% → **80%** (+65%, 8+ AI类型含ReconAI/SupplyAwarenessAI/心理模型)
- **Overall CC2 Fidelity**: ~45% → **~75%** (+30%, 视觉70% / 机制80%，v0.4.16诚实修正)
- **测试数增量**: +3769 (v0.1.1的2767 → v0.6.10的6536)

---

## 十一点五、P9 新特性详细说明 (AI深度提升+新游戏设置)

### P0 AI 行为系统 (7项)

| 行为ID | 行为名称 | 描述 | 触发条件 | 效果 | 测试数 |
|--------|----------|------|----------|------|--------|
| AI-P0-01 | 弹药拾取 (Ammo Pickup) | AI单位在弹药耗尽时主动搜索并拾取附近弹药 | ammo_remaining == 0 且附近有弹药箱/阵亡单位 | 单位移动到弹药源并补充弹药 | ~30 |
| AI-P0-02 | 武器搜刮 (Weapon Scavenging) | AI单位在主武器失效时搜刮阵亡单位的武器 | weapon_state == JAMMED/OUT_OF_AMMO 且附近有阵亡单位 | 单位拾取替代武器，战斗力恢复 | ~25 |
| AI-P0-03 | 投降 (Surrender) | AI单位在极端劣势下选择投降 | morale < 5 且 无友军支援 且 被包围 | 单位进入SURRENDERED状态，从战斗中移除 | ~20 |
| AI-P0-04 | 武器卡壳 (Weapon Jam) | 武器有概率在射击时卡壳 | 每次射击 jam_chance 概率触发 | 武器进入JAMMED状态，需要清除故障时间 | ~30 |
| AI-P0-05 | 烟雾部署 (Smoke Deployment) | AI在受压制时部署烟雾掩护 | suppression > 50 且 有烟雾弹 | 在单位位置生成烟雾区域，阻挡LOS | ~25 |
| AI-P0-06 | 班降解 (Squad Degradation) | 班组伤亡导致战斗力非线性下降 | 班组存活率 < 50% | 命中率/士气/移动速度额外惩罚 | ~25 |
| AI-P0-07 | NCO集结 (NCO Rally) | 士官/军士长在附近单位恐慌时执行集结 | 附近有PANIC状态单位 且 NCO存活 | 范围内友军士气恢复+15，恐慌状态解除 | ~25 |

### 新游戏设置系统

| 设置项 | 类型 | 可选值 | 说明 |
|--------|------|--------|------|
| 难度预设 | Enum | RECRUIT/EASY/NORMAL/HARD/VETERAN | 5级预设，影响以下所有参数 |
| 盟军经验等级 | Enum | GREEN/VETERAN/ELITE/CRACK | 独立于德军设置 |
| 德军经验等级 | Enum | GREEN/VETERAN/ELITE/CRACK | 独立于盟军设置 |
| 盟军补给等级 | Enum | SCARCE/LIMITED/NORMAL/ABUNDANT | 影响弹药/医疗/增援 |
| 德军补给等级 | Enum | SCARCE/LIMITED/NORMAL/ABUNDANT | 影响弹药/医疗/增援 |

**预设对应表:**

| 预设 | 盟军经验 | 德军经验 | 盟军补给 | 德军补给 |
|------|----------|----------|----------|----------|
| RECRUIT | GREEN | GREEN | ABUNDANT | SCARCE |
| EASY | VETERAN | GREEN | NORMAL | LIMITED |
| NORMAL | VETERAN | VETERAN | NORMAL | NORMAL |
| HARD | VETERAN | ELITE | LIMITED | NORMAL |
| VETERAN | ELITE | CRACK | SCARCE | ABUNDANT |

### 战役完成情况

| 维度 | 数量 | 说明 |
|------|------|------|
| Sectors | 3 | Allied Airborne / XXX Corps / German Defense |
| Operations | 7 | 覆盖Day 1-Day 6全部作战行动 |
| Battles | 29 | 每个Operation含3-5场Battle |
| Maps | 63 | 全部战役引用地图已解决（v0.6.10 验证） |
| Weapons | 69 | 含步兵/车载/固定武器 |
| Units | 80 | 含步兵/装甲/支援/特种单位 |

---

## 十二、Full Mission List (完整任务列表 M1-M10)

| Mission | 名称 | 历史事件 | Day | 地图尺寸 | 玩家兵力 | 敌方兵力 | 胜利条件 | 状态 |
|---------|------|----------|-----|----------|----------|----------|----------|------|
| M1 | Tutorial Training | 基础训练(虚构) | — | 20×20 | 2× Rifle, 1× MG | 2× Rifle | 占领建筑 | ✅ Complete |
| M2 | Bridge Assault | Son桥梁突击(9.17) | D1 | 32×32 | 3× Rifle, 1× Sniper, 1× MG | 4× Rifle, 1× MG | 控制桥梁+歼敌 | ✅ Complete |
| M3 | Road Ambush | Eindhoven伏击(9.17) | D1 | 40×24 | 2× Rifle, 1× AT | 3× Truck, 2× Escort | 歼灭车队 | ✅ Complete |
| M4 | Night Assault | 夜间空降(9.17夜) | D1/N | 36×36 | 4× Rifle, 2× MG, 1× Medic | 5× Rifle, 2× MG Bunker | 潜行占领HQ | ✅ Complete |
| M5 | Armored Column | 反坦克防御(9.18) | D2 | 48×32 | 3× Rifle, 2× AT, 1× Tank | 4× Tank, 3× Infantry | 防线坚守20min | ✅ Complete |
| M6 | **Son** | **Son镇争夺(9.17)** | **D1** | **44×36** | **5× Rifle, 2× MG, 1× Sniper** | **6× Rifle, 3× MG, 2× AT** | **占领Son桥梁** | **✅ Complete (P7)** |
| M7 | **Veghel** | **Veghel突破(9.18)** | **D2** | **52×40** | **4× Rifle, 2× Tank, 1× AT, 1× Medic** | **8× Rifle, 4× MG, 2× AT, 1× Tank** | **突破防线** | **✅ Complete (P7)** |
| M8 | **Grave** | **Grave渡河(9.20)** | **D4** | **48×48** | **3× Rifle, 1× MG, 1× Medic** | **10× Rifle, 5× MG, 3× Tank** | **渡河生存** | **✅ Complete (P7)** |
| M9 | **Nijmegen** | **Waal强渡(9.20)** | **D4** | **64×48** | **6× Rifle, 3× MG, 2× Tank, 1× Mortar** | **12× Rifle, 6× MG, 4× Tank, 2× AT** | **夺取北岸** | **✅ Complete (P7)** |
| M10 | **Arnhem** | **Arnhem最后突击(9.24-26)** | **D6** | **64×64** | **8× Rifle, 4× MG, 3× Tank, 2× Mortar** | **8× Rifle, 4× MG, 3× Tank** | **夺取Arnhem桥** | **✅ Complete (P7)** |

---

**文档版本**: v0.6.10
**创建日期**: 2026-05-18
**作者**: PyCC2 项目组
**状态**: ✅ Beta Candidate — 全部P0 Bug已修复，游戏可玩，AI 可对战
**当前版本**: v0.7.2
**测试总数**: ~6138 tests (含 503 E2E + 181 integration + 37 acceptance)
**下一步**: M5 质量可持续 + M6 内容增强（见 ROADMAP.md）

## 附录 A: 版本历史

| 版本 | 日期 | 作者 | 变更内容 |
|------|------|------|----------|
| v1.0 | 2026-05-15 | PM | 初始版本，33 User Stories, MoSCoW优先级矩阵 |
| v1.1 | 2026-05-18 | PM + 7 Roles | Consensus Review修订: Smoke快捷键X→K, Gate条件对齐 |
| v1.2 | 2026-05-18 | DevSquad | P2阶段完成: 新增Implementation Progress表(13阶段), Combat Loop + Audio System完成, 测试总数940 |
| v1.3 | 2026-05-18 | DevSquad | P3阶段全部完成(4子阶段): Systems+Visual+Content+Save, 新增17个进度条目, 测试总数1088, 版本升级v0.4-complete-edition |
| v1.4 | 2026-05-18 | DocSync | P3-Fix: 4个关键Bug修复, 版本号v0.4-fix1, 文档同步更新 |
| v1.5 | 2026-05-18 | Integration | P4 Week 1 完成: GameLoop Decomposition(4组件) + Settings Menu(4Tab) + Security Hardening, 测试总数1163, 版本升级v0.5-p4w1 |
| v1.6 | 2026-05-19 | Integration | P4 Week 2 完成: 性能优化(TileCache/AI节流/粒子池) + 教程系统(TutorialOverlay/HintManager) + 新任务(Mission 4夜战/Mission 5反坦克) + 新地图(4张), 测试总数1270, 版本升级v0.6-p4w2 |
| v1.7 | 2026-05-19 | PM+CC2 Analysis | CC2差距分析完成: Campaign~5%/Combat~65%, 新增ROADMAP.md, 测试1377, 路线图修订为P5(Pampaign Core)→P8(Release), 版本保持v0.6-p4w2 |
| v1.8 | 2026-05-19 | P5/P6/P7 Complete | **P5 Campaign Core完成**: CampaignState/BattleResult/UnitVeterancy/StrategicMap/OperationTimeline (~205 tests). **P6 Combat Depth完成**: Swiss Cheese伤害/Fatigue/AAR/TimeControl (~205 tests). **P7 Content Expansion完成**: M6-M10新任务(5个) + MAP-06~10新地图(5张) + 历史真实性增强 (~189 tests). CC2 Fidelity: Campaign ~60%, Combat ~85%, Overall ~71%. 测试总数1566, 任务10个, 地图10张. 版本保持v0.6-p4w2 |
| v2.0 | 2026-05-19 | DocSync+CC2 Analysis | **重大更新**: 基于CC2 Wiki和策略指南(Kasey Chang FAQ)重新评估还原度为~52%(原~71%高估). 新增GAP_ANALYSIS.md v1.1/ISSUES.md/TECH_DEBT.md v1.1. 路线图修订为P8-P12(地图补全→AI提升→单位补全→音频→集成). CC2原版参考: Arnhem战区9张地图(非原估计5张), 130+单位(非原估计60种), AI心理模型(Dr. Steven Silver设计). 技术债3项已修复/14项待清理. 版本升级v0.8-p7 |
| v2.1 | 2026-05-20 | P8 Complete | **P8 地图与战役补全完成**: 9张Arnhem战区新地图(Oosterbeek Caldron/Oosterbeek LZ/Arnhem Rail Bridge等)/四层战役架构(campaign_four_layer.py)/补给线机制(SupplySystem 70%)/部署阶段UI集成(3区域渲染+拖放). CC2还原度从~52%提升至~65%. 地图库10→19张, 战役结构25%→65%, 部署阶段40%→80%. 技术债8/20已修复/缓解. 版本升级v0.9-p8 |
| v3.0 | 2026-05-23 | DevSquad Critical Review | **诚实评估版**: 基于DevSquad批判性Review，还原度从声称~97%修正为~45%。游戏当前不可玩（5个P0致命Bug）。新增"当前P0问题"和"诚实还原度评估"章节。User Stories标注可用性状态（28/33不可用）。测试总数2762(6 failed)。路线图新增P0-Fix阶段。技术债5个P0+7个P1+9个P2未解决。状态降级为Pre-MVP |
| v0.1.1 | 2026-05-23 | M1修复更新 | **M1紧急修复进展**: P0-1(display_name)/P0-2(属性别名)/P0-3(AI导入)/P0-4(set_mode)已修复。测试总数2767(1 failed)。剩余P0-5(旧UI清理)待修复。版本号统一为v0.1.1 |
| v0.4.0 | 2026-06-14 | 文档同步至v0.4.0 | **全面更新**: 版本号→v0.4.0, CC2还原度→~88%, 测试数→~3513, P0 Bug→0, 地图→63, 单位模板→277。P0 Bug全部已修复。添加v0.3.x功能列表（幽灵功能审计、架构重构、视觉打磨、性能优化、AI战斗修复、音频激活）。还原度评估从v0.1.1的~45%更新为~88% |
| v0.4.16 | 2026-07-04 | 诚实代码审核 | **诚实修正**: 经逐文件代码证据核实，~88% 还原度严重高估。问题：(1) 11维度简单平均无权重；(2) isometric_renderer等5文件为experimental代码（v0.5.1 P2已删除）；(3) PixVoxel加载器1143行完整但完全未接入游戏循环。基于代码证据修正为视觉~70%/机制~80%/综合~75% |
| v0.5.0 | 2026-07-08 | PixVoxel P0接入 | **PixVoxel正交版精灵接入游戏循环** (3968精灵, 14/18单位类型覆盖, 索引调色板替换)。视觉还原度 52%→70%，综合 65%→75%。新增490 E2E测试 |
| v0.5.1 | 2026-07-09 | Isometric P2清理 | **完整删除experimental isometric代码** (5源文件+3测试+1脚本), 修复interaction_controller.py ProjectionMode.ISOMETRIC引用bug。CC2原版仅使用顶部正交视角 |
| v0.5.2~v0.5.5 | 2026-07-09~10 | P1调色板+纹理调优+P3机制补全 | 调色板修正(更接近CC2暗沉低饱和度) + 纹理调优 + LOS/烟雾/天气 + 窗户射击弧 + 散兵坑战壕 + AI侦察行为(ReconAI) + AI心理模型 + AI补给线意识(SupplyAwarenessAI) |
| v0.6.0~v0.6.5 | 2026-07-11 | P0-P3全部修复+TD-COV-BUG | 9项源码bug修复(TD-COV-BUG) + 幽灵功能接入(ReconAI+SupplyAwarenessAI) + flaky测试修复 + CI安全增强 |
| v0.6.10 | 2026-07-13 | 覆盖率提升+CI增强 | **当前版本**: 323新测试(覆盖率提升), radon复杂度门禁集成CI, 文档校准(本次审核), 脚本归档。测试总数6536, 源码模块388, 测试文件202。CC2还原度~75%(视觉70%/机制80%) |
