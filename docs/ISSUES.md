# PyCC2 当前问题与对策 — 全员共识文档

> **版本**: v1.2 | **日期**: 2026-05-20 | **状态**: P9 In Progress 🔄
> **原则**: 文档先行，不留技术债，参考原版，寻求超越
> **参考**: GAP_ANALYSIS.md v2.0 / TECH_DEBT.md v1.3 / ROADMAP.md v3.0

---

## 一、核心问题总览

| # | 问题 | 严重程度 | 当前完成度 | 目标完成度 | 对策Phase |
|---|------|---------|-----------|-----------|----------|
| P1 | 地图库不足 | 🟡 改善中 | 56% | ≥90% | P8→P10 |
| P2 | 战役结构缺失 | 🟡 接近 | 65% | ≥90% | P8→P10 |
| P3 | AI战术过于简单 | 🔴 严重 | 20%→**35%** | ≥80% | **P9🔄** |
| P4 | 单位多样性不足 | 🟡 严重 | 30% | ≥70% | P10 |
| P5 | 技术债未清理 | 🟡 严重 | 40%(8/20) | 0% | P9-P12 |
| P6 | 音频体验不足 | 🟡 中等 | 35% | ≥70% | P11 |
| P7 | 部署阶段未集成 | 🟢 接近 | 80% | 100% | P12 |
| P8 | 新模块无测试 | 🔴 严重 | 5% | 100% | **P9优先** |
| P9 | 补给线机制不完整 | 🟡 中等 | 70% | 100% | P9 |

---

## 二、P9推进计划（AI战术提升）

### P9.1-P9.3: 核心AI增强（P0，借鉴OpenCombat）

| 任务 | 借鉴来源 | 状态 | 测试目标 |
|------|---------|------|---------|
| P9.1 层级化Tick系统 | OpenCombat soldier.rs | 📋 待开发 | 15+ |
| P9.2 火力压制AI增强 | OpenCombat soldier.rs压制衰减 | 📋 待开发 | 20+ |
| P9.3 侧翼包抄AI增强 | OpenCombat tactical.rs路径验证 | 📋 待开发 | 20+ |

### P9.4-P9.7: 战术完整性

| 任务 | CC2行为 | 状态 | 测试目标 |
|------|---------|------|---------|
| P9.4 步坦协同AI增强 | 坦克掩护步兵，步兵保护侧翼 | 📋 待开发 | 15+ |
| P9.5 胜利点争夺AI | 抢占/防守VL | 📋 待开发 | 15+ |
| P9.6 撤退/炸桥决策AI | 劣势后撤，无法守住炸桥 | 📋 待开发 | 15+ |
| P9.7 反坦克伏击AI | AT team埋伏 | 📋 待开发 | 10+ |

### P9.8-P9.10: 技术债清理

| 任务 | TD编号 | 状态 | 测试目标 |
|------|--------|------|---------|
| P9.8 combat_resolver O(n²)优化 | TD-019 | 📋 待开发 | 10+ |
| P9.9 AI参数数据驱动化 | TD-016 | 📋 待开发 | 10+ |
| P9.10 核心模块测试补充 | TD-020 | 📋 待开发 | 100+ |

### 外部资源借鉴总结

| 项目 | 可借鉴内容 | 许可证 | 已分析 |
|------|-----------|--------|-------|
| [OpenCombat](https://github.com/buxx/OpenCombat) | 层级Tick/班长-成员模式/压制衰减/部署JSON/武器参数/AI协调器 | AGPL-3.0 | ✅ |
| [Mafi's CC2 Guides](https://closecombat2.hpage.com/) | 文件格式终极参考/CC2MapMuseum/地图编辑器工具 | — | ✅ |
| [gshaw/closecombat](https://github.com/gshaw/closecombat) | CC2地图编辑器/数据格式解析(TXT/LOS/BGM/OVM) | Zlib | ✅ |
| [greenstack/cc2](https://github.com/greenstack/cc2) | Lua版CC2复刻(Compa Chaos 2) | — | ✅ |

---

## 二、问题详细分析与对策

### P1: 地图库严重不足（CC2还原度最大瓶颈）

**现状**:
- PyCC2有10张地图（5张历史+5张通用）
- CC2原版有25-30张历史地图，仅Arnhem战区就有9张

**CC2原版地图完整列表**（基于CC2 Wiki和策略指南）:

#### Arnhem战区（9张地图）
| CC2地图名 | 历史地点 | PyCC2状态 | 优先级 |
|-----------|---------|----------|--------|
| Arnhem Bridge | 弗罗斯特夺取的公路桥 | ⚠️ arnhem(简化) | P0 |
| Arnhem Rail Bridge | 铁路桥争夺 | ❌ 缺失 | P0 |
| Arnhem Suburbs | 郊区战斗 | ❌ 缺失 | P1 |
| Arnhem Tree Road | 林荫道 | ❌ 缺失 | P1 |
| Arnhem West Approach | 西部通道(火车站/酒店) | ❌ 缺失 | P1 |
| Oosterbeek Caldron | 锅形地(核心防御) | ❌ 缺失 | P0 |
| Oosterbeek North | 北部(铁路/公路桥) | ❌ 缺失 | P1 |
| Oosterbeek LZ | 着陆场 | ❌ 缺失 | P0 |
| Oosterbeek Rail Bridge | 铁路桥 | ❌ 缺失 | P1 |

#### Eindhoven战区（2+张）
| CC2地图名 | 历史地点 | PyCC2状态 | 优先级 |
|-----------|---------|----------|--------|
| Son Bridge | Wilhelmina运河桥 | ✅ son_bridge | — |
| Son Town | 松镇(仓库/学校) | ❌ 缺失 | P2 |

#### Nijmegen战区（2+张）
| CC2地图名 | 历史地点 | PyCC2状态 | 优先级 |
|-----------|---------|----------|--------|
| Schijndel Road | 公路/桥梁 | ❌ 缺失 | P2 |
| Veghel Bridge | 费赫尔桥 | ✅ veghel | — |

**对策**:
1. P8.1优先创建Arnhem战区5张P0级地图（Oosterbeek Caldron/Oosterbeek LZ/Arnhem Rail Bridge/Arnhem Bridge升级/Wolfheze）
2. 每张地图必须包含：Victory Locations(带分值)、3种部署区域、历史地形特征
3. 参考CC2 Map Museum资源（MatrixGames FTP）验证地形布局
4. 使用TerrainDetailGenerator生成装饰物细节

**验收标准**:
- [x] Arnhem战区9张地图全部创建
- [x] 每张地图至少20个测试
- [x] 地图分值系统（Bridge=40, Road=30, LZ=20, Regular=10-19）
- [ ] Eindhoven/Nijmegen战区地图补全（P9）

---

### P2: 战役结构缺失（CC2灵魂所在）

**现状**:
- PyCC2是扁平单层结构（DAY_MISSION_MAP按Day分配10个mission）
- CC2原版是四层架构：GrandCampaign → SectorCampaign → Operation → Battle

**CC2原版战役结构**（基于CC2策略指南）:

```
Grand Campaign (Market Garden, Sept 17-26, 1944)
│
├── Sector: Arnhem (英1空降师+波兰伞兵 vs 9th/10th SS)
│   ├── Operation: Landing (Day 1)
│   │   ├── Battle: Arnhem Bridge (Frost夺取公路桥)
│   │   ├── Battle: Arnhem Rail Bridge (铁路桥)
│   │   └── Battle: Oosterbeek LZ (着陆场防御)
│   ├── Operation: Perimeter Defense (Days 2-8)
│   │   ├── Battle: Oosterbeek Caldron (核心防御圈)
│   │   ├── Battle: Arnhem Suburbs (郊区拉锯)
│   │   └── Battle: Arnhem West Approach (西部通道)
│   └── Operation: Evacuation (Day 9)
│       └── Battle: Driel Ferry (波兰伞兵渡河)
│
├── Sector: Nijmegen (美82空降师 vs 德军)
│   ├── Operation: Waal Crossing
│   │   ├── Battle: Grave (渡河)
│   │   └── Battle: Nijmegen Bridges (双桥)
│   └── Operation: Groesbeek Heights
│       └── ...
│
└── Sector: Eindhoven (美101空降师 vs 德军)
    ├── Operation: Eindhoven Assault
    │   ├── Battle: Son Bridge
    │   └── Battle: Veghel
    └── Operation: Hell's Highway Clearing
        └── ...
```

**CC2关键战役机制**（当前全部缺失）:
| 机制 | CC2原版 | PyCC2 | 对策 |
|------|---------|-------|------|
| Sector并行推进 | 3个战区同时进行 | 无 | P8.2实现SectorCampaign |
| Operation分组 | 每个Sector含2-3个Operation | 无 | P8.2实现Operation |
| Victory Location分值 | Bridge=40/Road=30/LZ=20/Regular=10-19 | 无 | P8.2实现VL价值系统 |
| 补给线机制 | XXX Corps推进→盟军补给; 德军陆路补给; 盟军空投需控制LZ | 无 | P8.3实现补给线 |
| 征用点采购 | Operations模式用requisition points购买单位 | 无 | P8.2实现采购系统 |
| 停火/撤退 | 可停火1-7小时; 惨败可撤退(有被俘风险) | 无 | P8.2实现停火 |
| Arnhem 9天 | Day 1-9完整时间线 | 仅Day 5 | P8.2扩展时间线 |
| 桥梁倒计时 | 盟军需在德军炸桥前夺取 | 无 | P8.2实现炸桥倒计时 |

**对策**:
1. P8.2重构战役系统为四层架构
2. Arnhem Sector扩展为Day 1-9完整时间线（至少9场Battle）
3. 实现补给线机制（XXX Corps推进速度→补给能力）
4. 实现征用点采购系统（最多9步兵+6支援）

**验收标准**:
- [x] GrandCampaign包含3个Sector
- [x] Arnhem Sector包含Day 1-9完整时间线
- [x] Victory Location价值系统运作
- [x] 补给线影响战斗（弹药/增援/士气）
- [x] 至少50个新测试
- [ ] 征用点采购系统（P9补完）
- [ ] 停火/撤退机制（P9补完）

---

### P3: AI战术过于简单

**现状**:
- PyCC2 AI只有基础框架：威胁评估+掩体寻找
- CC2 AI有成熟行为树：侧翼包抄/火力压制/步坦协同/炸桥决策

**CC2 AI核心行为**（基于CC2策略指南和补丁说明）:
| AI行为 | CC2表现 | PyCC2状态 | 优先级 |
|--------|---------|----------|--------|
| 侧翼渗透 | AI从侧翼潜行包抄 | ❌ 只有正面 | P0 |
| 火力压制优先 | MG42持续射击高威胁目标 | ❌ 无目标选择 | P0 |
| 步坦协同 | 坦克掩护步兵，步兵保护坦克 | ❌ 各自为战 | P0 |
| 胜利点争夺 | AI优先抢占/防守VL | ❌ 不理解目标 | P0 |
| 伏击设置 | AT team埋伏等待坦克 | ❌ 不会埋伏 | P1 |
| 撤退决策 | 劣势时后撤重组 | ❌ 打到死 | P1 |
| 炸桥决策 | 无法守住时炸桥 | ❌ 永远不炸 | P1 |
| 反击行为 | 获得增援后主动反击 | ❌ 无反击 | P2 |
| 侦察行为 | 派出侦察单位探测 | ❌ 无侦察 | P2 |
| 心理模型 | 士兵可能拒绝命令(非绝对服从) | ❌ 绝对服从 | P2 |

**CC2补丁2.0改进**（需参考）:
- AI迫击炮改为区域覆盖（不再精确命中个人）
- 坦克更易沿路行驶，减少侧面暴露
- 德军步兵不再对盟军步兵使用铁拳
- 隐藏单位在30m内自动开火

**对策**: P9逐步实现，从P0级行为开始

---

### P4: 单位多样性不足

**现状**: PyCC2 39种单位 vs CC2 130+

**CC2原版单位完整列表**（基于CC2 Wiki）:

#### 盟军步兵
| 单位类型 | 美军82nd | 美军101st | 英军1st | 波兰军 |
|---------|----------|----------|---------|--------|
| 步枪班 | ✅ M1+BAR | ✅ M1+BAR | ✅ 李恩菲尔德+手雷 | ✅ 英式装备 |
| 侦察班 | ✅ | ✅ | ✅ | ✅ |
| 狙击手 | ✅ | ✅ | ✅ | ✅ |
| 机枪班 | ✅ M1919 | ✅ M1919 | ✅ BREN | ✅ BREN |
| AT班 | ✅ Bazooka | ✅ Bazooka | ✅ PIAT | ✅ PIAT |
| 迫击炮班(轻) | ✅ 60mm | ✅ 60mm | ✅ 2-inch | ✅ 2-inch |
| 迫击炮班(重) | ✅ 81mm | ✅ 81mm | ✅ 3-inch | ✅ 3-inch |
| 喷火器班 | ✅ | ✅ | ✅ | — |
| 重突击班 | — | — | ✅ | — |
| 军官 | ✅ | ✅ | ✅ | ✅ |
| 预备队 | — | — | — | — |

#### 德军步兵
| 单位类型 | Wehrmacht | SS |
|---------|-----------|-----|
| 步枪班 | ✅ Kar98k | ✅ Kar98k+铁拳 |
| MG42机枪班 | ✅ 自带铁拳 | ✅ 自带铁拳 |
| MG34机枪班 | ✅ | — |
| 狙击手 | ✅ | ✅ |
| AT班(Panzershreck) | ✅ | ✅ |
| 突击掷弹兵(Sturmgrenadiere) | — | ✅ SS精锐 |
| 迫击炮班 | ✅ 8cm GrW 34 | ✅ |
| 喷火器班 | ✅ | ✅ |
| 预备队(Reservists) | ✅ 战斗力弱 | — |

#### 盟军载具
| 载具 | 阵营 | 主炮 | 装甲 |
|------|------|------|------|
| M4 Sherman | 美军 | 75mm M3 | 正面51mm |
| Sherman Firefly | 英军 | 17-pounder | 正面51mm |
| Sherman DD(两栖) | 美军 | 75mm | 正面51mm |
| Halftrack(M5) | 美军 | 可选M2HB | — |
| Halftrack(英式) | 英军 | — | — |
| Armored Car | 美军 | 37mm | 轻甲 |

#### 德军载具
| 载具 | 主炮 | 装甲 | 备注 |
|------|------|------|------|
| Panzer IV | 75mm KwK 40 | 正面80mm | 中型坦克 |
| Panther | 75mm KwK 42 | 正面100mm+ | 重型坦克 |
| Tiger I | 88mm KwK 36 | 正面100mm | 最强坦克 |
| Jagdpanther | 88mm PaK 43 | 正面80mm | 坦克歼击车 |
| StuG III | 75mm StuK 40 | 正面80mm | 突击炮 |
| Flammpanzer | 火焰喷射器 | — | 喷火坦克 |
| SdKfz Halftrack | MG42 | — | 半履带车 |
| SdKfz 222/234 | 20mm | 轻甲 | 装甲车 |

#### 固定武器
| 武器 | 阵营 | 类型 |
|------|------|------|
| 6-pounder AT Gun | 英军 | 57mm反坦克炮 |
| 17-pounder AT Gun | 英军 | 76.2mm(萤火虫主炮) |
| PaK 40 | 德军 | 75mm反坦克炮 |
| FlaK 88 | 德军 | 88mm高射/反坦克炮 |
| M1 57mm AT Gun | 美军 | 57mm反坦克炮 |

**关键差异**（CC2原版特色）:
- 德军几乎每个班都携带铁拳（Panzerfaust），AT能力远超盟军
- 英军AT能力极度匮乏，PIAT是唯一可靠反坦克手段
- 波兰军使用英军装备缩减版
- 美军/德军步兵班人数多于英军/波兰军

**对策**: P10逐步补全，优先固定火炮和波兰伞兵

---

### P5: 技术债未清理

**现状**: 20项技术债，8项已修复/缓解，12项待清理

**关键未清理项**:
| ID | 描述 | 影响 | 计划清理 |
|----|------|------|---------|
| TD-001 | EnhancedRenderer未集成 | 视觉增强无效 | P12 |
| TD-002 | CombatState未集成到Unit | 压制/隐蔽无效 | P12 |
| TD-003 | campaign.py仍用旧dict | 新武器/单位无效 | ⚠️ 已弃用 |
| TD-004 | 部署阶段无UI | 无法拖放部署 | P8 ✅ |
| TD-005 | EnhancedTile未对接 | 装饰物数据无效 | P12 |
| TD-006 | enhanced_mission_system.py重复 | 维护混乱 | ✅ 已删除 |
| TD-013 | 6个新模块无测试 | 无质量保障 | P9-P12 |
| TD-015 | 地图JSON三份冗余 | 体积膨胀3倍 | ✅ 已清理 |
| TD-019 | combat_resolver O(n²) | 大规模战斗性能差 | P9 |
| TD-020 | 15+模块零测试覆盖 | 回归风险高 | P9 |

**对策**: 每个Phase开始时清理该Phase相关的技术债，绝不带着技术债进入下一Phase

---

### P6: 音频体验不足

**现状**: 程序化音效23种，缺乏辨识度

**CC2原版音频**:
- 每种武器独特声音（MG42标志性"Hitler's Saw"高射速声）
- 语音命令系统（"Move out!"/"Fire!"/"Take cover!"/"Retreat!"）
- 背景音乐（战斗音乐+菜单音乐）
- 环境音效（风声/水声/远处炮声）

**对策**: P11逐步实现，MG42声音为最高优先级

---

### P7: 部署阶段未集成

**现状**: 数据结构已建，但无UI交互

**CC2原版部署流程**:
1. 战斗开始→进入Deployment Mode
2. 地图显示3种区域（Friendly/No Man's Land/Enemy）
3. 玩家拖放单位到合法位置
4. 坦克不能部署在建筑内，士兵不能部署在河流
5. 限制：最多9步兵+6支援
6. 点击Begin开始战斗

**CC2部署策略**（来自策略指南）:
- 防守方：沿敌方进攻路线布防，保持射界开阔，形成交叉火力，保留预备队
- 进攻方：利用掩体，支援单位放在可射击位置，避开明显通道
- 每栋建筑最多1个班，AT班靠后设伏

**对策**: P8.4集成部署阶段UI

---

### P8: 新模块无测试

**现状**: 6个新模块0个测试
- enhanced_tile.py (0 tests)
- terrain_detail_generator.py (0 tests)
- enhanced_renderer.py (0 tests)
- cc2_authentic_weapons.py (0 tests)
- cc2_authentic_units.py (0 tests)
- combat_mechanics_enhanced.py (0 tests)

**对策**: 每个Phase中同步补充对应模块测试，每个模块至少20个测试

---

## 三、推进原则（全员共识）

### 原则1: 文档先行
- 每个Phase开始前更新PRD/ROADMAP/TECH_DEBT
- 每个Phase结束前review所有文档
- 重大决策必须记录在文档中，评审通过后执行

### 原则2: 不留技术债
- 发现即记录到TECH_DEBT.md
- 每个Phase结束时清理该Phase相关的技术债
- 绝不带着技术债进入下一Phase

### 原则3: 参考原版
- 所有决策以CC2原版数据为基准（见GAP_ANALYSIS.md参考资料）
- 地图/单位/武器参数优先参考CC2游戏数据文件
- CC2补丁2.0a/2.0b的改进也需纳入

### 原则4: 超越而非仅复刻
- 在保持还原度的前提下寻求机制创新
- 已超越的领域（视觉/战斗机制）保持优势
- 未达标的领域（地图/战役/AI/单位）优先追赶

### 原则5: 测试驱动
- 每个新功能必须有对应测试
- 测试不通过不进入下一Phase
- 目标：总测试数≥2500

### 原则6: 全员共识
- 重大决策前在文档中记录
- 评审通过后执行
- 任何成员可对决策提出异议

---

## 四、推进路线图（P8-P12）

| Phase | 名称 | 核心目标 | 关键交付物 | 技术债清理 | 状态 |
|-------|------|---------|-----------|-----------|------|
| **P8** | 地图与战役补全 | CC2还原度52%→65% | 9新地图/四层战役/补给线/部署UI | TD-003/006/007/015 | ✅ Complete |
| **P9** | AI战术提升 | CC2还原度65%→80% | 侧翼/压制/步坦协同/胜利点AI | TD-016/019/020 | 🔄 Next |
| **P10** | 单位与武器补全 | CC2还原度80%→88% | AT Gun/波兰伞兵/载具变体 | — | 📋 Planned |
| **P11** | 音频与体验 | CC2还原度88%→90% | MG42声音/语音命令/BGM | TD-008 | 📋 Planned |
| **P12** | 集成与发布 | CC2还原度≥90% | 系统集成/端到端测试/打包 | TD-001/002/004/005/010/013/014/017 | 📋 Planned |

---

## 五、CC2原版参考资料索引

| 资料来源 | URL | 内容 |
|---------|-----|------|
| CC2 Wiki | gamia-archive.fandom.com/wiki/Close_Combat:_A_Bridge_Too_Far | 游戏机制、单位分类、战役结构 |
| CC2 策略指南 | the-spoiler.com/STRATEGY/Microsoft/close.combat.2.1.html | 完整策略FAQ、部署技巧、AI行为 |
| CC2 Steam页面 | store.steampowered.com/app/2916170/ | 官方描述、特性列表 |
| CC2 Map Museum | ftp-us.matrixgames.com/pub/CloseCombatCrossOfIron/mods/CCII-Mods/CC2MapMuseum/ | 原版地图资源 |
| Old PC Gaming Review | oldpcgaming.net/close-combat-2-a-bridge-too-far-review | 游戏评价、特性分析 |
| Operation Market Garden | en.wikipedia.org/wiki/Operation_Market_Garden | 历史时间线、OOB |
| Battle of Arnhem | en.wikipedia.org/wiki/Battle_of_Arnhem | Arnhem 9天战斗详细过程 |
| CC2 游戏数据文件 | X:\Data\Data\Base\ (游戏CD) | 武器/车辆/士兵/团队精确数值 |

### GitHub可借鉴项目

| 项目 | 语言 | 可借鉴内容 | 许可证 |
|------|------|-----------|--------|
| **[buxx/OpenCombat](https://github.com/buxx/OpenCombat)** | Rust | CC2灵感开源游戏，battle_core战斗逻辑、assets部署配置、resources/maps地图格式、武器系统(MG34/MG42)、士兵/单位系统、路径寻找 | AGPL-3.0 |
| **[gshaw/closecombat](https://github.com/gshaw/closecombat)** | C++/Java | CC2地图编辑器(Map Maker)、数据格式解析(TXT/LOS/BGM/OVM) | Zlib |
| **[Mafi's CC2 Guides](https://closecombat2.hpage.com/)** | 文档 | CC2文件格式终极参考：地图(TXT/LOS/BGM)、精灵(SPRI)、地形、Teams文件、Operations/Campaign方案、CC2MapMuseum.zip | — |

**OpenCombat重点借鉴方向**:
1. `battle_core/src/` — 战斗核心逻辑（压制计算、射击判定、移动系统）
2. `assets/demo1_deployment.json` — 部署配置格式
3. `resources/maps/` — 地图数据结构
4. 武器参数（MG34/MG42/步枪等已实现精确参数）
5. AI行为树实现

---

## 六、决策记录

| 日期 | 决策 | 理由 | 状态 |
|------|------|------|------|
| 2026-05-19 | 多人联机暂不实现 | 用户明确指示，优先提升AI和内容 | ✅ 已确认 |
| 2026-05-19 | 文档先行原则 | 用户要求，确保全员共识 | ✅ 已确认 |
| 2026-05-19 | P8优先补全地图和战役 | GAP_ANALYSIS显示这是最大瓶颈 | ✅ 已完成 |
| 2026-05-19 | 参考CC2原版数据 | 用户多次强调，弥补差距 | ✅ 已确认 |
| 2026-05-19 | 不留技术债 | 用户明确要求，每个Phase清理 | ✅ 已确认 |
| 2026-05-20 | P8代码走读: cc2_authentic_units.py import修复 | 7维度走读发现import路径错误，立即修复(TD-018) | ✅ 已修复 |
| 2026-05-20 | P8代码走读: combat_resolver O(n²)需优化 | 7维度走读发现目标选择算法复杂度过高，记录为TD-019 | 📋 P9清理 |
| 2026-05-20 | P8代码走读: 15+模块零测试覆盖 | 7维度走读发现P8新模块及原有模块缺乏测试，记录为TD-020 | 📋 P9优先 |
| 2026-05-20 | P8代码走读: HMAC密钥硬编码问题 | 7维度走读发现HMAC密钥仍有硬编码风险，需进一步检查 | 📋 P9检查 |
| 2026-05-20 | 补给线征用点采购延后至P9 | P8核心目标(地图+战役架构)已达成，征用点非关键路径 | ✅ 已确认 |
| 2026-05-20 | CC2还原度评估调整为~65% | P8实际交付低于原估70%，地图56%/战役65%/部署80% | ✅ 已确认 |

---

**文档状态**: P8 Complete ✅
**评审截止**: 2026-05-21
**下一步**: Phase 9 — AI战术提升
