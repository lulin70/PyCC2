# PyCC2 vs CC2 原版差距分析报告

> **版本**: v0.1.0 | **日期**: 2026-05-23 | **状态**: DevSquad批判性Review后诚实重估
> **参考来源**: CC2 Wiki (gamia-archive.fandom.com), CC2 策略指南 (the-spoiler.com), CC2 Steam, 用户反馈, OpenCombat (GitHub), DevSquad 7角色交叉Review
> **目的**: 诚实记录当前PyCC2与原版CC2的所有差距，包括运行时验证结果
> **关联文档**: ROADMAP.md v0.1.0 / DEVSQUAD_CRITICAL_REVIEW.md v0.1.0 / TECH_DEBT.md

---

## 一、总体评估

| 维度 | CC2原版 (1997) | PyCC2当前 | 文档声称完成度 | 实际验证完成度 | 评级 | 差距说明 |
|------|---------------|----------|---------------|---------------|------|----------|
| **地图库** | 25-30张历史地图 | 28张(22历史+6通用) | 100% | **68%** | 🟡 | 数据完整但纹理粗糙，程序化色块vs CC2像素艺术 |
| **战役结构** | 四层架构 | 四层架构+3Sector+7Op+29Battle | 95% | **80%** | 🟡 | 数据结构正确，征用点采购UI未实现 |
| **武器系统** | ~50种武器 | 69种武器+射击参数 | 98% | **70%** | 🟡 | 数据定义有，战斗中武器效果未完全验证 |
| **单位多样性** | 130+单位 | 277种单位模板 | 41% | **30%** | 🔴 | 数据定义有，但渲染管线断裂，单位显示几何形状 |
| **AI战术** | 成熟行为树 | 6大战术AI类 | 90% | **25%** | 🔴 | 代码有但行为树断裂(AttackNearestAI不存在)，AI无法启动 |
| **部署阶段** | 完整拖放部署 | DeploymentUI 1983行 | 90% | **40%** | 🔴 | 代码有但非CC2风格，缺少部队列表+地图拖放 |
| **视觉质量** | 1997像素艺术 | 增强像素艺术+纹理 | 120% | **35%** | 🔴 | 面板崩溃、单位几何形状、地图色块，远不如原版 |
| **战斗机制** | 基础压制+士气 | 6级压制+隐蔽+姿态 | 140% | **45%** | 🔴 | 机制代码有但组件属性不匹配导致面板崩溃，无法验证 |
| **补给线** | XXX Corps+空投+LZ | SupplyLineManager | 70% | **50%** | 🟡 | 基础功能有，征用点采购缺失 |
| **音频** | 完整音效+语音+BGM | 12种武器音效+10语音+6BGM | 75% | **30%** | 🔴 | 代码有但stereo播放失败，实际效果未验证 |
| **命令系统** | 7命令完整可操作 | CC2BottomPanel 7命令 | 100% | **57%** | 🔴 | 3/7命令不可操作(Fast/Sneak参数错误, Smoke/Defend无模式) |
| **综合还原度** | — | — | **~97%** | **~45%** | 🔴 | 严重虚高，大量功能停留在数据/代码层未运行 |

### 文档声称 vs 实际验证对比

| 维度 | 文档声称 | 实际验证 | 虚高幅度 |
|------|----------|----------|----------|
| 视觉 | 120% | 35% | **+85%** |
| 战斗机制 | 140% | 45% | **+95%** |
| AI战术 | 90% | 25% | **+65%** |
| 音频 | 75% | 30% | **+45%** |
| 命令系统 | 100% | 57% | **+43%** |
| 单位多样性 | 41% | 30% | **+11%** |
| **综合** | **~97%** | **~45%** | **+52%** |

---

## 二、运行时差距（DevSquad Review发现）

> ⚠️ 以下差距均为运行时实际验证发现的问题，非代码审查或测试报告。

### 2.1 战斗界面崩溃（P0-致命）

**现象**: 启动游戏进入战斗后，CC2BottomPanel每帧崩溃，HUD完全不可用

**根因**:
1. `Unit` dataclass缺少`display_name`属性 — `cc2_bottom_panel.py` L280/L329、`game_loop.py` L188/269/384/714均访问`unit.display_name`，但`display_name`仅存在于`UnitTemplate`，未传递到`Unit`实例
2. `HealthComponent`使用`hp`/`max_hp`，面板访问`health.current`/`health.max`（不存在）
3. `MoraleComponent`使用`value`，面板访问`morale.current`（不存在）
4. `WeaponComponent`使用`ammo_remaining`/`max_ammo`，面板访问`ammo`/`max_ammo`

**影响**: 用户看不到任何单位信息（名称、血量、士气、弹药），游戏基本不可玩

### 2.2 7命令系统3个不可操作（P1-严重）

**现象**: CC2BottomPanel定义了7个命令(Move/Fast/Sneak/Attack/Smoke/Defend/Cancel)，但3个不可操作

**根因**:
1. **Fast命令**: 调用`set_mode(MOVE, fast=True)`，但`InteractionController.set_mode(self, mode: InteractionMode)`不接受`fast`参数 → TypeError
2. **Sneak命令**: 调用`set_mode(MOVE, sneak=True)`，同样参数不匹配 → TypeError
3. **Smoke命令**: 无对应`InteractionMode`枚举值，无法进入交互模式
4. **Defend命令**: 无对应`InteractionMode`枚举值，无法进入交互模式

**影响**: 用户只能使用Move/Attack/Cancel，无法执行快速移动、潜行、烟雾、防御等核心战术操作

### 2.3 单位精灵未正确渲染（P1-严重）

**现象**: 单位显示为彩色几何形状（方块/圆形），而非PNG像素精灵

**根因**:
1. PNG精灵资源已存在于`assets/sprites/`
2. `AssetLoader`可加载PNG
3. 但`SpriteRenderer.initialize()`依赖`self._asset_loader._sprite_cache`（双层私有属性直接访问）
4. 加载时机和缓存键映射存在断裂

**影响**: 视觉效果远不如CC2原版1997年的像素艺术

### 2.4 AI行为树断裂（P0-致命）

**现象**: 敌方单位无智能行为，不移动不攻击

**根因**:
1. `game_loop.py`导入`AttackNearestAI`和`MoveToObjectiveAI`
2. 但`tactical_ai.py`中不存在这两个类（该文件定义的是FlankingAI/SuppressionAI/InfantryTankCoordAI/VictoryPointAI）
3. 导入失败导致AI行为树初始化失败

**影响**: 游戏无对抗性，敌方无任何智能行为

### 2.5 地图视觉粗糙（P2-改善）

**现象**: 地图纹理为程序化生成的简单色块

**根因**: tile纹理生成器产出简单色块，缺乏CC2原版的草地/泥土/建筑纹理细节

**影响**: 视觉体验差，与CC2原版像素艺术差距大

### 2.6 音频stereo失败（P1-严重）

**现象**: 音效播放失败或仅单声道

**根因**: stereo播放配置问题，具体待排查

**影响**: 无法听到武器差异化音效，MG42标志性声音缺失

---

## 三、P0致命Bug清单

> 以下5个Bug阻塞游戏基本可玩性，必须在任何新功能开发前修复。

| 编号 | Bug | 影响范围 | 修复复杂度 | 修复方案 |
|------|-----|----------|------------|----------|
| P0-1 | Unit缺少display_name属性 | CC2BottomPanel、GameLoop、EnhancedRenderer全部崩溃 | 低 | 在Unit dataclass添加display_name字段，从UnitTemplate赋值 |
| P0-2 | HealthComponent属性名不匹配 | CC2BottomPanel访问health.current/max不存在 | 低 | 添加current/max property别名映射到hp/max_hp |
| P0-3 | MoraleComponent属性名不匹配 | CC2BottomPanel访问morale.current不存在 | 低 | 添加current property别名映射到value |
| P0-4 | AttackNearestAI/MoveToObjectiveAI不存在 | AI行为树初始化失败，敌方无智能 | 中 | 在tactical_ai.py中实现这两个类 |
| P0-5 | 致命bug未被测试捕获 | 信心危机，无法保证后续开发质量 | 中 | 补充关键路径冒烟测试 |

---

## 四、地图库差距

### 4.1 CC2原版地图体系

根据CC2 Wiki和CC2策略指南(Kasey Chang FAQ)，原版地图按三个战区(Sector)组织：

#### Arnhem Sector（阿纳姆战区）— 最关键，9张地图
| 地图 | 历史地点 | 地形特征 | PyCC2状态 | 运行时验证 |
|------|---------|---------|----------|------------|
| **Arnhem Bridge** | 弗罗斯特夺取的公路桥 | 桥梁居中，城镇提供伏击点 | ✅ 数据 | 🟡 纹理粗糙 |
| **Arnhem Rail Bridge** | 铁路桥争夺 | 桥梁居中，几乎无掩体 | ✅ 数据 | 🟡 纹理粗糙 |
| **Arnhem Suburbs** | 郊区战斗 | 城镇建筑密集 | ✅ 数据 | 🟡 纹理粗糙 |
| **Arnhem Tree Road** | 林荫道 | 河流分割战场 | ✅ 数据 | 🟡 纹理粗糙 |
| **Arnhem West Approach** | 西部通道 | 大量房屋 | ✅ 数据 | 🟡 纹理粗糙 |
| **Oosterbeek Caldron** | 锅形地(核心防御圈) | 半城半野 | ✅ 数据 | 🟡 纹理粗糙 |
| **Oosterbeek North** | 北部 | 铁路/公路交汇桥 | ✅ 数据 | 🟡 纹理粗糙 |
| **Oosterbeek LZ** | 着陆场 | 开阔地带 | ✅ 数据 | 🟡 纹理粗糙 |
| **Oosterbeek Rail Bridge** | 铁路桥 | 类似阿纳姆铁路桥 | ✅ 数据 | 🟡 纹理粗糙 |

#### Arnhem Sector 扩展地图
| 地图 | 历史地点 | PyCC2状态 | 运行时验证 |
|------|---------|----------|------------|
| **Arnhem Zoo** | 动物园厚墙防御 | ✅ 数据 | 🟡 纹理粗糙 |
| **Arnhem Koepel** | Koepel教堂区 | ✅ 数据 | 🟡 纹理粗糙 |
| **Arnhem Best** | Best运河桥 | ✅ 数据 | 🟡 纹理粗糙 |
| **Arnhem St Elizabeth** | 圣伊丽莎白医院 | ✅ 数据 | 🟡 纹理粗糙 |
| **Oosterbeek Perimeter** | 收缩防御圈 | ✅ 数据 | 🟡 纹理粗糙 |
| **Oosterbeek Last Stand** | 最后据守 | ✅ 数据 | 🟡 纹理粗糙 |
| **Driel Ferry** | Driel渡口撤退 | ✅ 数据 | 🟡 纹理粗糙 |

#### Eindhoven Sector
| 地图 | 历史地点 | PyCC2状态 | 运行时验证 |
|------|---------|----------|------------|
| Son Bridge | Wilhelmina运河桥 | ✅ 数据 | 🟡 纹理粗糙 |
| Son Town | 松镇 | ✅ 数据 | 🟡 纹理粗糙 |
| Eindhoven City | 埃因霍温市区 | ✅ 数据 | 🟡 纹理粗糙 |

#### Nijmegen Sector
| 地图 | 历史地点 | PyCC2状态 | 运行时验证 |
|------|---------|----------|------------|
| Schijndel Road | 公路/桥梁 | ✅ 数据 | 🟡 纹理粗糙 |
| Veghel Bridge | 费赫尔桥 | ✅ 数据 | 🟡 纹理粗糙 |
| Grave | Waal河渡口 | ✅ 数据 | 🟡 纹理粗糙 |
| Nijmegen | Waal公路桥+铁路桥 | ✅ 数据 | 🟡 纹理粗糙 |

### 4.2 地图数据层状态（已全部补全 ✅）

所有CC2原版地图和历史补充地图均有JSON数据文件，共28张（22张历史+6张通用）。

### 4.3 CC2地形系统特色（运行时差距）

| 地形特色 | CC2原版 | PyCC2当前 | 差距 |
|---------|---------|----------|------|
| 丘陵地形 | 高度差影响LOS | ❌ 无高度系统 | 🔴 缺失 |
| 散兵坑/战壕 | 专用掩体类型 | ❌ 无专用掩体 | 🔴 缺失 |
| 多层建筑 | 顶层更好LOS，底层AT | ❌ 无多层系统 | 🔴 缺失 |
| 高架地形 | 铁路/公路高架桥 | ❌ 无高架系统 | 🔴 缺失 |
| 地图纹理 | 像素艺术草地/泥土/建筑 | 🟡 程序化色块 | 🔴 视觉差距大 |

---

## 五、战役结构

### 5.1 CC2原版四层架构

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

### 5.2 当前PyCC2实现

- ✅ 四层架构: GrandCampaign→Sector→Operation→Battle（数据层）
- ✅ 3个战区: Arnhem/Nijmegen/Eindhoven
- ✅ 7个Operations
- ✅ 29个Battles
- ✅ 22张战役地图全部有对应JSON文件
- ✅ Victory Location价值系统 (Bridge=40, Road=30, LZ=20, Regular=10-19)
- ⚠️ 补给线机制 (SupplyLineManager存在，征用点采购UI缺失)
- ⚠️ 部署阶段 (DeploymentUI存在但非CC2风格)

### 5.3 剩余战役机制差距

| 机制 | CC2原版 | PyCC2 | 差距 |
|------|---------|-------|------|
| **Sector概念** | 3个战区并行推进 | ✅ 数据层已实现 | — |
| **Operation分组** | 每个Sector含2-3个Operation | ✅ 7个Operation已实现 | — |
| **Victory Location价值** | Bridge=40pts等 | ✅ 已实现 | — |
| **补给线机制** | XXX Corps推进+空投+LZ控制 | ⚠️ 基础有，采购UI缺失 | 🟡 P2 |
| **停火/撤退** | 可宣布停火1-7小时 | ❌ 未实现 | 🟡 P2 |
| **采购系统** | Operations模式可用requisition points | ⚠️ 数据结构有，UI未实现 | 🟡 P2 |
| **单位恢复** | 受损单位自动补充 | ✅ 基础恢复已实现 | — |

---

## 六、AI战术差距

### 6.1 当前AI能力（代码层 vs 运行时）

| AI能力 | 代码层 | 运行时 | 说明 |
|--------|--------|--------|------|
| BattlefieldPicture态势感知 | ✅ | ❓ | 未验证是否在GameLoop中运行 |
| 5级威胁判断 | ✅ | ❓ | 同上 |
| 关键地形识别 | ✅ | ❓ | 同上 |
| FlankingAI侧翼包抄 | ✅ | ❌ | 行为树断裂，AI无法启动 |
| SuppressionAI火力压制 | ✅ | ❌ | 同上 |
| InfantryTankCoordAI步坦协同 | ✅ | ❌ | 同上 |
| VictoryPointAI胜利点争夺 | ✅ | ❌ | 同上 |
| AttackNearestAI最近攻击 | ❌ | ❌ | 类不存在，导入失败 |
| MoveToObjectiveAI目标移动 | ❌ | ❌ | 类不存在，导入失败 |

### 6.2 缺失的CC2核心AI行为

| AI行为 | CC2表现 | PyCC2状态 | 优先级 |
|--------|---------|----------|--------|
| **基础攻击** | AI攻击最近敌人 | ❌ AttackNearestAI不存在 | P0 |
| **目标移动** | AI向目标移动 | ❌ MoveToObjectiveAI不存在 | P0 |
| **侧翼渗透** | AI从侧翼包抄 | ⚠️ 代码有，运行时断裂 | P0 |
| **火力压制优先** | MG42持续压制 | ⚠️ 代码有，运行时断裂 | P0 |
| **步坦协同** | 坦克掩护步兵 | ⚠️ 代码有，运行时断裂 | P0 |
| **胜利点争夺** | AI抢占VL | ⚠️ 代码有，运行时断裂 | P0 |
| **伏击设置** | AT team埋伏 | ❌ 未实现 | P1 |
| **撤退决策** | 劣势时后撤 | ❌ 未实现 | P1 |
| **炸桥决策** | 无法守住时炸桥 | ❌ 未实现 | P1 |
| **反击行为** | 获得增援后反击 | ❌ 未实现 | P2 |
| **侦察行为** | 派出侦察单位 | ❌ 未实现 | P2 |
| **心理模型** | 士兵可能拒绝命令 | ❌ 未实现 | P2 |
| **士气链式反应** | 指挥官阵亡→崩溃 | ⚠️ 有基础无连锁 | P2 |
| **补给线意识** | 保护/切断补给 | ❌ 未实现 | P2 |

---

## 七、武器与单位差距

### 7.1 武器库对比

| 类别 | CC2原版(约) | PyCC2当前 | 差距 |
|------|------------|----------|------|
| 步兵轻武器 | ~12种 | 10种 | 🟡 接近 |
| 机枪 | 4种 | 4种 | ✅ 完整 |
| 反坦克武器 | 4种 | 4种 | ✅ 完整 |
| 迫击炮 | 6种 | 6种 | ✅ 完整 |
| 喷火器 | 3种 | 3种 | ✅ 完整 |
| 坦克炮 | ~10种 | 8种 | 🟡 接近 |
| 车载MG | 3种 | 3种 | ✅ 完整 |
| 固定火炮(AT Gun) | ~4种 | 3种(数据层) | 🟡 数据有，渲染未验证 |
| **合计** | **~50种** | **69种(数据层)** | 🟡 数据量够，运行时效果待验证 |

### 7.2 单位多样性对比

| 类别 | CC2原版 | PyCC2当前(数据层) | 运行时验证 |
|------|---------|-------------------|------------|
| 步兵类型 | ~60种 | 26种 | 🟡 数据有，精灵未渲染 |
| 载具类型 | ~24种 | 13种 | 🟡 同上 |
| 载具变体 | 多种涂装/改装 | 有变体定义 | 🟡 同上 |
| 固定武器 | ~6种 | 3种 | 🟡 同上 |
| **合计** | **130+** | **277种模板** | 🔴 数据量大但渲染管线断裂 |

### 7.3 关键缺失（运行时层面）

| 缺失 | CC2中的角色 | 优先级 |
|------|-----------|--------|
| PNG精灵渲染接入 | 所有单位视觉呈现 | P1 |
| 统一单位定义系统 | 4套定义并存(UNIT_TEMPLATES/UNIT_ARMOR_PROFILES/cc2_authentic_units/unit_diversity_expansion) | P2 |
| AT Gun固定武器渲染 | 固定反坦克炮视觉 | P2 |

---

## 八、部署阶段差距

### 8.1 CC2原版部署流程

1. 战斗开始进入Deployment Mode
2. 地图显示三种区域:
   - **Friendly**(无阴影): 玩家可部署区域
   - **No Man's Land**(浅灰): 争议区
   - **Enemy Controlled**(深灰): 敌方区域
3. 玩家拖放单位到合法位置
4. 坦克不能部署在建筑内,士兵不能部署在河流中
5. 部署完成后点击Begin开始战斗
6. 限制: 最多9个步兵+6个支援单位

### 8.2 当前PyCC2状态

- ✅ `DeploymentPhase`类已实现(数据结构层)
- ✅ 三种区域类型已定义(ZoneType)
- ✅ 部署限制已实现(9步兵+6支援)
- ⚠️ `deployment_ui.py` 1983行巨型文件（需拆分）
- ❌ **非CC2风格** — 缺少左侧部队列表+右侧地图拖放交互
- ❌ **地形合法性检查未完整** — 坦克不能进建筑等

---

## 九、音频差距

| 音频类别 | CC2原版 | PyCC2代码层 | 运行时验证 |
|---------|---------|------------|------------|
| 武器音效 | 每种武器独特声音 | 12种差异化音效代码 | 🔴 stereo播放失败 |
| 语音命令 | "Move out!"/"Fire!"等 | 10种语音代码 | ❓ 未验证 |
| 背景音乐 | 战斗音乐+菜单音乐 | 6种BGM代码 | ❓ 未验证 |
| 环境音效 | 风声/水声/远处炮声 | 3种环境音代码 | ❓ 未验证 |
| MG42标志性声音 | "Hitler's Saw" | 差异化代码 | 🔴 stereo失败，无法辨识 |

---

## 十、对策与优先级

> 基于DevSquad批判性Review，优先级调整为：先修P0让游戏可玩，再做架构和视觉提升。

### 10.1 M1: 紧急修复（1-2天）

| 任务 | 内容 | 优先级 |
|------|------|--------|
| P0-1 | Unit添加display_name属性 | P0 |
| P0-2/3 | 组件属性别名(health.current/max, morale.current) | P0 |
| P0-4 | 实现AttackNearestAI/MoveToObjectiveAI | P0 |
| P0-5 | 补充冒烟测试 | P0 |
| P1-1 | set_mode签名扩展 | P1 |

### 10.2 M2: 核心功能完善（3-5天）

| 任务 | 内容 | 优先级 |
|------|------|--------|
| P1-2 | Smoke/Defend交互模式 | P1 |
| P1-3 | 修复精灵渲染管线 | P1 |
| P1-6 | 补充集成测试 | P1 |
| P2-8 | 存档数据校验 | P2 |

### 10.3 M3: 架构重构（5-7天）

| 任务 | 内容 | 优先级 |
|------|------|--------|
| P1-4 | domain层瘦身 | P1 |
| P1-5 | 巨型文件拆分 | P1 |
| P1-7 | GameLoop拆分 | P1 |
| P2-1 | 合并infra/ | P2 |
| P2-9 | 统一单位定义 | P2 |

### 10.4 M4: 质量提升（3-5天）

| 任务 | 内容 | 优先级 |
|------|------|--------|
| P2-2 | 清理scripts/ | P2 |
| P2-3/4 | 文档整理 | P2 |
| P2-7 | CI添加e2e | P2 |
| — | 补充用户操作E2E测试 | P2 |

### 10.5 M5: 视觉打磨（5-7天）

| 任务 | 内容 | 优先级 |
|------|------|--------|
| P2-5 | 地图纹理优化 | P2 |
| P2-6 | CC2风格部署界面 | P2 |
| — | UI像素级对齐CC2原版 | P2 |

---

## 十一、CC2原版参考资料索引

| 资料来源 | URL | 内容 |
|---------|-----|------|
| CC2 Wiki | gamia-archive.fandom.com/wiki/Close_Combat:_A_Bridge_Too_Far | 游戏机制、单位分类、战役结构 |
| CC2 用户手册 | manualsdir.com/manuals/124140/microsoft-close-combat.html | 部署阶段、胜利条件、操作说明 |
| Operation Market Garden 历史 | en.wikipedia.org/wiki/Operation_Market_Garden | 历史时间线、OOB、战役进程 |
| Battle of Arnhem | en.wikipedia.org/wiki/Battle_of_Arhnhem | Arnhem 9天战斗详细过程 |
| CC2 游戏文件 | (需获取原版数据) | qtab/weap数据、地图数据、AI参数 |
| DevSquad批判性Review | DEVSQUAD_CRITICAL_REVIEW.md | 7角色交叉Review发现 |

---

**文档状态**: v0.1.0 DevSquad批判性Review后诚实重估
**关键变化**: 综合还原度从~97%修正为~45%，新增运行时差距和P0致命Bug章节
**下一步**: M1紧急修复（让游戏可玩）
