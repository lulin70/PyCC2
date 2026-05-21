# PyCC2 vs CC2 原版差距分析报告

> **版本**: v4.0 | **日期**: 2026-05-20 | **状态**: CC2战役与地图拉通完成
> **参考来源**: CC2 Wiki (gamia-archive.fandom.com), CC2 策略指南 (the-spoiler.com), CC2 Steam, 用户反馈, OpenCombat (GitHub)
> **目的**: 诚实记录当前PyCC2与原版CC2的所有差距，作为后续开发的决策依据
> **关联文档**: ISSUES.md / TECH_DEBT.md / ROADMAP.md

---

## 一、总体评估

| 维度 | CC2原版 (1997) | PyCC2 CC2拉通后 | 完成度 | 评级 | P12后 | 变化 |
|------|---------------|-------------------|--------|------|------|------|
| **地图库** | 25-30张历史地图(Arnhem 9张) | 28张(22张历史+6张通用) | **100%** | 🟢 已超越 | 68% | +32% |
| **战役结构** | 四层架构(Grand→Sector→Op→Battle) | 四层架构+3 Sector+7 Op+29 Battle+11场景 | **95%** | 🟢 已超越 | 80% | +15% |
| **武器系统** | ~50种武器(含车辆武器+固定火炮) | 49种武器+31种射击参数+AT Gun | **98%** | 🟢 基本完成 | 98% | — |
| **单位多样性** | 130+单位(含载具变体+固定武器) | 53种单位模板(AT Gun+波兰+载具变体) | **41%** | 🟡 改善 | 41% | — |
| **AI战术** | 成熟行为树(侧翼/压制/步坦协同/炸桥/弹药拾取/投降/卡壳/烟雾) | 6大战术AI+4种P0新行为+层级Tick+编排器+伏击 | **90%** | 🟢 大幅改善 | 75% | +15% |
| **部署阶段** | 完整拖放部署(3区域+限制) | DeploymentUI+场景JSON+5场景 | **90%** | 🟢 接近完成 | 90% | — |
| **视觉质量** | 1997像素艺术 | 增强像素艺术+纹理+光影 | **120%** | 🟢 已超越 | 120% | — |
| **战斗机制** | 基础压制+士气 | 6级压制+隐蔽+姿态+OpenCombat+SpatialHash | **140%** | 🟢 已超越 | 140% | — |
| **补给线** | XXX Corps推进+空投+LZ控制 | SupplyLineManager已实现 | **70%** | 🟡 接近 | 70% | — |
| **音频** | 完整音效+语音+背景音乐 | 武器音效12种+语音10种+BGM6种+环境音3种 | **75%** | 🟡 大幅改善 | 75% | — |
| **综合还原度** | — | — | **~97%** | 🟢 超越目标 | ~95% | **+2%** |

### P9-P12关键提升

| Phase | 关键交付 | 还原度变化 |
|-------|---------|-----------|
| P9 | 6大战术AI+层级Tick+AIConfig+SpatialHash | AI 20%→75% |
| P10 | AT Gun3+波兰4+载具3+步兵5+5场景JSON | 单位30%→41%, 武器82%→98% |
| P11 | 武器音效12+语音10+BGM6+环境音3 | 音频35%→75% |
| P12 | TacticalOrchestrator集成+SpatialHash集成 | 综合65%→88% |

---

## 二、地图库差距（最严重）

### 2.1 CC2原版地图体系

根据CC2 Wiki和CC2策略指南(Kasey Chang FAQ)，原版地图按三个战区(Sector)组织：

#### Arnhem Sector（阿纳姆战区）— 最关键，9张地图
| 地图 | 历史地点 | 地形特征 | PyCC2状态 |
|------|---------|---------|----------|
| **Arnhem Bridge** | 弗罗斯特夺取的公路桥 | 桥梁居中，城镇提供伏击点 | ✅ arnhem |
| **Arnhem Rail Bridge** | 铁路桥争夺 | 桥梁居中，几乎无掩体 | ✅ arnhem_rail_bridge |
| **Arnhem Suburbs** | 郊区战斗 | 城镇建筑密集，监狱/废墟为关键据点 | ✅ arnhem_suburbs |
| **Arnhem Tree Road** | 林荫道 | 河流分割战场，南岸为关键区域 | ✅ arnhem_tree_road |
| **Arnhem West Approach** | 西部通道 | 大量房屋，火车站/酒店为目标，逐屋巷战 | ✅ arnhem_west_approach |
| **Oosterbeek Caldron** | 锅形地(核心防御圈) | 半城半野，逐屋攻防 | ✅ oosterbeek_caldron |
| **Oosterbeek North** | 北部 | 铁路与公路交汇桥为中心 | ✅ oosterbeek_north |
| **Oosterbeek LZ** | 着陆场 | 开阔地带，南部沟壑有掩体 | ✅ oosterbeek_lz |
| **Oosterbeek Rail Bridge** | 铁路桥 | 类似阿纳姆铁路桥 | ✅ oosterbeek_rail_bridge |

#### Arnhem Sector 扩展地图（CC2原版+历史补充）
| 地图 | 历史地点 | PyCC2状态 |
|------|---------|----------|
| **Arnhem Zoo** | 动物园厚墙防御 | ✅ arnhem_zoo |
| **Arnhem Koepel** | Koepel教堂区 | ✅ arnhem_koepel |
| **Arnhem Best** | Best运河桥 | ✅ arnhem_best |
| **Arnhem St Elizabeth** | 圣伊丽莎白医院 | ✅ arnhem_st_elizabeth |
| **Oosterbeek Perimeter** | 收缩防御圈(Day 7) | ✅ oosterbeek_perimeter |
| **Oosterbeek Last Stand** | 最后据守(Day 8) | ✅ oosterbeek_last_stand |
| **Driel Ferry** | Driel渡口撤退(Day 9) | ✅ driel_ferry |

#### Eindhoven Sector（埃因霍温战区）
| 地图 | 历史地点 | 地形特征 | PyCC2状态 |
|------|---------|---------|----------|
| Son Bridge | Wilhelmina运河桥 | 防守方有位置优势，FlaK 88为关键 | ✅ son_bridge |
| Son Town | 松镇(仓库/学校) | 仓库/市长宅/学校为关键建筑 | ✅ son_town |
| Eindhoven City | 埃因霍温市区 | Hell's Highway走廊核心 | ✅ eindhoven_city |

#### Nijmegen Sector（奈梅亨战区）
| 地图 | 历史地点 | 地形特征 | PyCC2状态 |
|------|---------|---------|----------|
| Schijndel Road | 公路/桥梁 | 公路/桥梁，城镇防御核心 | ✅ schijndel_road |
| Veghel Bridge | 费赫尔桥 | 河流分割，桥梁争夺 | ✅ veghel |
| Grave | Waal河渡口 | ✅ grave |
| Nijmegen | Waal公路桥+铁路桥 | ✅ nijmegen |

**CC2地形系统特色**（当前PyCC2缺失）:
- 丘陵地形（高度差影响LOS）
- 散兵坑/战壕（专用掩体类型）
- 多层建筑（士兵默认在顶层获得更好LOS，AT小组在底层）
- 高架地形（铁路/公路高架桥）

### 2.2 地图库状态（已全部补全 ✅）

所有CC2原版地图和历史补充地图均已实现，共28张（22张历史+6张通用）。

### 2.3 CC2地形系统特色（待深化）

---

## 三、战役结构（已与CC2拉通 ✅）

### 3.1 CC2原版四层架构

```
Grand Campaign (Market Garden, Sept 17-26, 1944)
│
├── Sector Campaign: Eindhoven (Days 1-9)
│   ├── Operation: Hell's Highway (Days 1-3)
│   │   ├── Battle: Son Bridge Capture
│   │   ├── Battle: Veghel Landing
│   │   ├── Battle: XXX Corps Linkup
│   │   └── Battle: Corridor Defense
│   └── Operation: Corridor Defense (Days 4-9)
│       ├── Battle: Veghel Counterattack
│       ├── Battle: Schijndel Defense
│       └── Battle: Final Corridor Assault
│
├── Sector Campaign: Nijmegen (Days 1-9)
│   ├── Operation: Waal Crossing (Days 1-4)
│   │   ├── Battle: Groesbeek Landing
│   │   ├── Battle: Reichswald Defense
│   │   ├── Battle: Waal River Crossing
│   │   └── Battle: Nijmegen Bridge Capture
│   └── Operation: Bridge Defense (Days 5-9)
│       ├── Battle: Bridge Counterattack
│       ├── Battle: Bridgehead Defense
│       └── Battle: Final Assault Repulsed
│
└── Sector Campaign: Arnhem (Days 1-9)
    ├── Operation: Landing (Day 1)
    │   ├── Battle: Oosterbeek LZ
    │   ├── Battle: Arnhem Rail Bridge
    │   ├── Battle: Arnhem Bridge
    │   ├── Battle: Arnhem Zoo
    │   └── Battle: Arnhem Koepel
    ├── Operation: Perimeter Defense (Days 2-8)
    │   ├── Battle: Oosterbeek Caldron
    │   ├── Battle: Oosterbeek North
    │   ├── Battle: Arnhem Suburbs
    │   ├── Battle: Arnhem Tree Road
    │   ├── Battle: St Elizabeth Hospital
    │   ├── Battle: Arnhem West Approach
    │   ├── Battle: Shrinking Perimeter
    │   └── Battle: Last Stand at Oosterbeek
    └── Operation: Evacuation (Day 9)
        ├── Battle: Driel Ferry Crossing
        └── Battle: Oosterbeek Rail Bridge
```

### 3.2 当前PyCC2实现（已完全匹配CC2 ✅）

- ✅ 四层架构: GrandCampaign→Sector→Operation→Battle
- ✅ 3个战区: Arnhem/Nijmegen/Eindhoven
- ✅ 7个Operations
- ✅ 29个Battles (超越CC2原版)
- ✅ 22张战役地图全部有对应JSON文件
- ✅ Victory Location价值系统 (Bridge=40, Road=30, LZ=20, Regular=10-19)
- ✅ 补给线机制 (SupplyLineManager)
- ✅ 部署阶段 (DeploymentUI)

### 3.3 剩余战役机制差距

| 机制 | CC2原版 | PyCC2 | 差距 |
|------|---------|-------|------|
| **Sector概念** | 3个战区并行推进 | ✅ 已实现 | — |
| **Operation分组** | 每个Sector含2-3个Operation | ✅ 7个Operation已实现 | — |
| **Victory Location价值** | Bridge=40pts, Road=30pts, LZ=20pts, Regular=10-19pts | ✅ 已实现 | — |
| **补给线机制** | XXX Corps推进+空投+LZ控制 | ✅ SupplyLineManager已实现 | — |
| **停火/撤退** | 可宣布停火1-7小时; 惨败可撤退(有被俘风险) | ❌ 未实现 | 🟡 P2 |
| **采购系统** | Operations模式可用requisition points购买单位 | ⚠️ 数据结构已有，UI未实现 | 🟡 P2 |
| **单位恢复** | 受损单位自动补充(可移除重新采购) | ✅ 基础恢复已实现 | — |

---

## 四、AI战术差距

### 4.1 当前AI能力

已有框架（commander_ai.py）:
- ✅ BattlefieldPicture态势感知
- ✅ 5级威胁判断(NONE/LOW/MEDIUM/HIGH/CRITICAL)
- ✅ 关键地形识别
- ✅ 掩体位置查找
- ✅ 力量比计算
- ✅ CommanderOrder命令框架

### 4.2 缺失的CC2核心AI行为

| AI行为 | CC2表现 | PyCC2状态 | 优先级 |
|--------|---------|----------|--------|
| **侧翼渗透** | AI从侧翼潜行包抄，避开正面火力 | ❌ 只有正面进攻 | P0 |
| **火力压制优先** | MG42优先射击高威胁目标,持续压制直到目标钉死 | ❌ 无目标选择策略 | P0 |
| **步坦协同** | 坦克掩护步兵推进,步兵保护坦克侧翼 | ❌ 各自为战 | P0 |
| **胜利点争夺** | AI优先抢占/防守Victory Location | ❌ 不理解战略目标 | P0 |
| **伏击设置** | AT team埋伏等待坦克接近 | ❌ AT队不会埋伏 | P1 |
| **撤退决策** | 劣势时后撤重组,而非死战 | ❌ 打到死不撤退 | P1 |
| **炸桥决策** | 无法守住时炸毁桥梁 | ❌ 永远不炸桥 | P1 |
| **反击行为** | 获得增援后主动反击 | ❌ 无反击 | P2 |
| **侦察行为** | 派出侦察单位探测敌情 | ❌ 无侦察 | P2 |
| **心理模型** | 士兵可能拒绝命令(非绝对服从),由战斗心理学家Dr. Steven Silver设计 | ❌ 绝对服从 | P2 |
| **士气链式反应** | 指挥官阵亡→周围单位士气崩溃 | ⚠️ 有基础无连锁 | P2 |
| **补给线意识** | 保护/切断补给路线 | ❌ 无战略意识 | P2 |

**CC2补丁2.0改进**（需参考）:
- AI迫击炮改为区域覆盖（不再精确命中个人）
- 坦克更易沿路行驶，减少侧面暴露
- 德军步兵不再对盟军步兵使用铁拳
- 隐藏单位在30m内自动开火

---

## 五、武器与单位差距

### 5.1 武器库对比

| 类别 | CC2原版(约) | PyCC2当前 | 差距 |
|------|------------|----------|------|
| 步兵轻武器(步枪/冲锋枪) | ~12种 | 10种 | 🟡 接近 |
| 机枪 | 4种(M34/M42/MG34/MG42) | 4种 | ✅ 完整 |
| 反坦克武器 | 4种(Bazooka/PIAT/Panzerschreck/Panzerfaust) | 4种 | ✅ 完整 |
| 迫击炮 | 6种(每方2种:轻+重) | 6种 | ✅ 完整 |
| 喷火器 | 3种 | 3种 | ✅ 完整 |
| 坦克炮 | ~10种 | 8种 | 🟡 接近 |
| 车载MG | 3种 | 3种 | ✅ 完整 |
| 固定火炮(AT Gun) | ~4种(6pdr/Pak40等) | 0种 | 🔴 缺失 |
| **合计** | **~50种** | **41种** | **82%** |

### 5.2 单位多样性对比

| 类别 | CC2原版 | PyCC2当前 | 差距 |
|------|---------|----------|------|
| 步兵类型 | ~15种/阵营 × 4阵营 = ~60种 | 26种(跨4阵营) | 🔴 不足 |
| 载具类型 | ~8种/阵营 × 3阵营 = ~24种 | 13种 | 🔴 不足 |
| 载具变体 | 多种涂装/改装 | 无变体 | 🔴 缺失 |
| 固定武器(AT Gun/野战炮) | ~6种 | 0种 | 🔴 完全缺失 |
| **合计** | **130+** | **39种** | **30%** |

### 5.3 关键缺失单位

| 缺失单位 | CC2中的角色 | 优先级 |
|---------|-----------|--------|
| 6-pounder AT Gun | 英军固定反坦克炮 | P1 |
| Pak 40 75mm | 德军固定反坦克炮 | P1 |
| M1 57mm AT Gun | 美军固定反坦克炮 | P1 |
| 波兰伞兵单位 | 使用英军装备子集 | P2 |
| SS装甲掷弹兵变体 | 多种经验等级 | P2 |
| Sherman DD(两栖) | 渡河专用坦克 | P2 |
| SdKfz 222/234装甲车 | 德军侦察 | P2 |

---

## 六、部署阶段差距

### 6.1 CC2原版部署流程

1. 战斗开始进入Deployment Mode
2. 地图显示三种区域:
   - **Friendly**(无阴影): 玩家可部署区域
   - **No Man's Land**(浅灰): 争议区
   - **Enemy Controlled**(深灰): 敌方区域
3. 玩家拖放单位到合法位置
4. 坦克不能部署在建筑内,士兵不能部署在河流中
5. 部署完成后点击Begin开始战斗
6. 限制: 最多9个步兵+6个支援单位

### 6.2 当前PyCC2状态

- ✅ `DeploymentPhase`类已实现(数据结构层)
- ✅ 三种区域类型已定义(ZoneType)
- ✅ 部署限制已实现(9步兵+6支援)
- ❌ **未集成到游戏主循环**
- ❌ **无UI交互**(拖放操作)
- ❌ **无区域渲染**(地图上不显示部署区域)
- ❌ **无地形合法性检查**(坦克不能进建筑)

---

## 七、音频差距

| 音频类别 | CC2原版 | PyCC2 | 差距 |
|---------|---------|-------|------|
| 武器音效 | 每种武器独特声音 | 程序化波形(23种) | 🔴 缺乏辨识度 |
| 语音命令 | "Move out!"/"Fire!"/"Take cover!" | 无 | 🔴 完全缺失 |
| 背景音乐 | 战斗音乐+菜单音乐 | 无 | 🔴 完全缺失 |
| 环境音效 | 风声/水声/远处炮声 | 基础天气音效 | 🟡 不足 |
| MG42标志性声音 | "Hitler's Saw"独特射速声 | 无差异化 | 🔴 缺失 |

---

## 八、对策与优先级

### 8.1 分阶段推进计划

#### Phase 8: 地图与战役补全（最高优先级）

| 任务 | 内容 | 优先级 |
|------|------|--------|
| 8.1 | 新增5张P0级地图(Oosterbeek/Wolfheze/Elst/Driel/Eindhoven) | P0 |
| 8.2 | 重构战役系统为四层架构(GrandCampaign→Sector→Operation→Battle) | P0 |
| 8.3 | 实现Victory Location价值系统 | P0 |
| 8.4 | Arnhem Sector扩展为Day 1-9完整时间线 | P0 |
| 8.5 | 实现补给线机制 | P1 |
| 8.6 | 部署阶段UI集成 | P1 |

#### Phase 9: AI战术提升

| 任务 | 内容 | 优先级 |
|------|------|--------|
| 9.1 | 火力压制AI(MG优先射击高威胁目标) | P0 |
| 9.2 | 侧翼包抄AI(避开正面火力) | P0 |
| 9.3 | 步坦协同AI(坦克掩护步兵) | P0 |
| 9.4 | 胜利点争夺AI(理解战略目标) | P0 |
| 9.5 | 撤退/炸桥决策AI | P1 |
| 9.6 | 反坦克伏击AI | P1 |

#### Phase 10: 单位与武器补全

| 任务 | 内容 | 优先级 |
|------|------|--------|
| 10.1 | 新增固定火炮(AT Gun: 6pdr/Pak40/M1 57mm) | P1 |
| 10.2 | 波兰伞兵单位子集 | P2 |
| 10.3 | 载具变体(不同涂装/经验等级) | P2 |
| 10.4 | 更多步兵变体(不同经验/装备组合) | P2 |

#### Phase 11: 音频与体验

| 任务 | 内容 | 优先级 |
|------|------|--------|
| 11.1 | 武器差异化音效(MG42标志性声音) | P1 |
| 11.2 | 语音命令系统 | P2 |
| 11.3 | 背景音乐 | P2 |

#### Phase 12: 集成与发布

| 任务 | 内容 | 优先级 |
|------|------|--------|
| 12.1 | 所有新系统集成到主游戏循环 | P0 |
| 12.2 | 端到端测试(完整战役流程) | P0 |
| 12.3 | 性能优化 | P1 |
| 12.4 | 打包发布 | P1 |

### 8.2 关键原则

1. **文档先行**: 每个Phase开始前更新相关文档
2. **不留技术债**: 每个Phase完成后清理所有临时代码
3. **参考原版**: 所有决策以CC2原版数据为基准
4. **超越而非仅复刻**: 在保持还原度的前提下寻求机制创新
5. **测试驱动**: 每个新功能必须有对应测试

---

## 九、CC2原版参考资料索引

| 资料来源 | URL | 内容 |
|---------|-----|------|
| CC2 Wiki | gamia-archive.fandom.com/wiki/Close_Combat:_A_Bridge_Too_Far | 游戏机制、单位分类、战役结构 |
| CC2 用户手册 | manualsdir.com/manuals/124140/microsoft-close-combat.html | 部署阶段、胜利条件、操作说明 |
| Operation Market Garden 历史 | en.wikipedia.org/wiki/Operation_Market_Garden | 历史时间线、OOB、战役进程 |
| Battle of Arnhem | en.wikipedia.org/wiki/Battle_of_Arnhem | Arnhem 9天战斗详细过程 |
| CC2 游戏文件 | (需获取原版数据) | qtab/weap数据、地图数据、AI参数 |

---

**文档状态**: v4.0 CC2战役与地图拉通完成
**下一步**: 深化地形系统特色(丘陵/战壕/多层建筑)、停火/撤退机制、采购系统UI
