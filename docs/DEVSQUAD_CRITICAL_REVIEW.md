# PyCC2 DevSquad 批判性Review报告

> **审计日期**: 2026-05-23
> **审计范围**: PyCC2全项目代码、架构、测试、文档
> **审计方法**: 7角色交叉Review（Architect/PM/Security/Tester/Coder/DevOps/UI Designer）

---

## 一、各角色关键发现

### 1. Architect（架构师）

| # | 发现 | 严重性 | 详情 |
|---|------|--------|------|
| A1 | **Unit实体缺少display_name属性** | P0-致命 | `Unit` dataclass仅有`name`字段，但`cc2_bottom_panel.py`（L280/L329）、`game_loop.py`（L188/269/384/714）均访问`unit.display_name`，导致`AttributeError`崩溃。`display_name`仅存在于`UnitTemplate`上，未传递到`Unit`实例 |
| A2 | **infra/与infrastructure/职责重叠** | P2 | `infra/config.py`仅10行（Settings dataclass），`infrastructure/`包含audio/parsers/save_system。两者命名混淆，违反DDD清晰分层原则 |
| A3 | **domain层严重膨胀（75.4%代码量）** | P1 | domain层包含32个AI子模块、35个system文件，其中大量属于应用服务层（如campaign_persistence、battle_replay）或基础设施层（如cc2_map_parser），违反DDD限界上下文原则 |
| A4 | **巨型文件集中** | P1 | 8个文件超过1000行（最大1983行deployment_ui.py），违反单一职责。deployment_ui.py 1983行同时包含数据模型、渲染逻辑、事件处理 |
| A5 | **组件属性访问不一致** | P0-致命 | `HealthComponent`使用`hp`/`max_hp`，但`cc2_bottom_panel.py`访问`health.current`/`health.max`（不存在），导致面板渲染崩溃。`MoraleComponent`使用`value`，面板访问`morale.current`（也不存在） |

### 2. PM（产品经理）

| # | 发现 | 严重性 | 详情 |
|---|------|--------|------|
| P1 | **战斗界面完全不可用** | P0 | display_name + health属性访问bug导致CC2BottomPanel每帧崩溃，HUD无法显示，游戏基本不可玩 |
| P2 | **AI行为树导入失败** | P0 | `AttackNearestAI`和`MoveToObjectiveAI`在`tactical_ai.py`中不存在（该文件定义的是FlankingAI/SuppressionAI/InfantryTankCoordAI/VictoryPointAI），导致AI无法使用行为树，敌方单位无智能行为 |
| P3 | **7命令系统回调未完整实现** | P1 | CC2BottomPanel定义了Move/Fast/Sneak/Attack/Smoke/Defend/Cancel，但：Fast/Sneak调用`set_mode(MOVE, fast=True)`/`set_mode(MOVE, sneak=True)`，而`set_mode`签名不接受这些参数；Smoke/Defend无对应InteractionMode |
| P4 | **单位仍显示几何形状** | P1 | PNG精灵已存在于assets/sprites/，AssetLoader可加载，但SpriteRenderer.initialize()依赖`_asset_loader._sprite_cache`属性（私有属性直接访问），且加载时机和缓存键映射存在断裂 |
| P5 | **部署界面非CC2风格** | P2 | deployment_ui.py 1983行但视觉风格与CC2原版部署界面差距大，缺少CC2原版的部队选择列表+地图拖放交互 |

### 3. Security（安全专家）

| # | 发现 | 严重性 | 详情 |
|---|------|--------|------|
| S1 | **secrets.toml.example存在但无.gitignore保护** | P1 | `config/secrets.toml.example`存在，但需确认实际secrets.toml是否被gitignore排除，存在凭证泄露风险 |
| S2 | **存档系统无数据校验** | P1 | `infrastructure/save_system.py`加载JSON存档时缺乏schema验证和完整性检查，恶意存档可注入异常数据 |
| S3 | **GameCommand.__post_init__存在bug** | P2 | L56: `object.__setattr__(self, timestamp=time.time())`中`timestamp`未加引号，应为`"timestamp"`，这会导致`NameError`而非安全问题，但说明代码未经基本测试 |
| S4 | **无输入边界验证** | P2 | 地图坐标、单位ID等输入未做边界检查，恶意输入可能导致越界访问 |

### 4. Tester（测试专家）

| # | 发现 | 严重性 | 详情 |
|---|------|--------|------|
| T1 | **integration测试仅1个** | P1 | `tests/integration/`仅有`test_combat_loop.py`，无法验证模块间交互 |
| T2 | **e2e测试8个但无用户操作视角** | P1 | 8个e2e测试均为自动化系统验证（AI行为、战役流程、战斗等），无模拟真实用户操作（选单位→下命令→观察结果）的端到端测试 |
| T3 | **32个调试脚本散落scripts/** | P2 | scripts/目录有32个.py文件，多数为临时调试脚本（debug_*/test_*/verify_*），无测试框架集成，不可回归 |
| T4 | **致命bug未被测试捕获** | P0 | display_name缺失、health属性不匹配、AttackNearestAI不存在——这些本应由单元测试或集成测试捕获，说明测试覆盖存在严重盲区 |
| T5 | **CI未包含e2e测试** | P2 | ci.yml仅运行`pytest tests/`，但e2e测试需要pygame显示环境，CI中可能被跳过 |

### 5. Coder（开发者）

| # | 发现 | 严重性 | 详情 |
|---|------|--------|------|
| C1 | **组件属性命名不一致** | P0 | HealthComponent: `hp`/`max_hp` vs 面板访问: `current`/`max`；MoraleComponent: `value` vs 面板访问: `current`；WeaponComponent: `ammo_remaining`/`max_ammo` vs 面板访问: `ammo`/`max_ammo`。需要统一接口 |
| C2 | **set_mode签名不匹配调用** | P1 | `InteractionController.set_mode(self, mode: InteractionMode)`不接受`fast`/`sneak`参数，但game_loop.py L303/L311传入这些参数，会TypeError |
| C3 | **私有属性直接访问** | P2 | `SpriteRenderer.initialize()`访问`self._asset_loader._sprite_cache`（双层私有属性），违反封装原则 |
| C4 | **game_loop.py 1226行上帝类** | P1 | GameLoop承担了游戏状态管理、单位创建、AI初始化、输入处理、渲染调度等过多职责 |
| C5 | **重复的单位定义系统** | P2 | `UNIT_TEMPLATES`(unit.py)、`UNIT_ARMOR_PROFILES`(unit.py)、`cc2_authentic_units.py`(1805行)、`unit_diversity_expansion.py`(891行)四套单位定义并存 |

### 6. DevOps（运维）

| # | 发现 | 严重性 | 详情 |
|---|------|--------|------|
| D1 | **CI缺少e2e测试阶段** | P1 | ci.yml仅有lint+unit test，无e2e测试job，无法在CI中捕获界面级回归 |
| D2 | **无发布流程** | P2 | 无版本号管理、无changelog生成、无发布自动化 |
| D3 | **Codecov action版本过旧** | P2 | 使用codecov-action@v3，当前最新为v4 |
| D4 | **无Docker化** | P2 | 游戏项目虽不强制容器化，但无环境一致性保障，依赖pygame显示环境 |

### 7. UI Designer（UI设计师）

| # | 发现 | 严重性 | 详情 |
|---|------|--------|------|
| U1 | **CC2面板崩溃→HUD完全不可用** | P0 | 因display_name和health属性bug，CC2风格底部面板无法渲染，用户看不到任何单位信息 |
| U2 | **单位精灵仍为几何形状** | P1 | PNG精灵资源已就位但未正确接入渲染管线，单位显示为彩色方块/圆形，与CC2原版像素士兵差距巨大 |
| U3 | **地图纹理粗糙** | P2 | tile纹理为程序化生成的简单色块，缺乏CC2原版的草地/泥土/建筑纹理细节 |
| U4 | **部署界面与CC2原版差距大** | P2 | CC2原版部署界面为左侧部队列表+右侧地图拖放，当前实现为简单点击放置 |
| U5 | **4份视觉优化文档重叠** | P2 | VISUAL_OPTIMIZATION_PLAN/SUMMARY/COMPLETE/SPEC四份文档内容重叠，无统一执行标准 |

---

## 二、统一问题优先级排序

### P0 - 致命（阻塞游戏基本可玩性）

| 编号 | 问题 | 影响范围 | 修复复杂度 | 状态 |
|------|------|----------|------------|------|
| ~~P0-1~~ | ~~Unit缺少display_name属性~~ | ~~CC2BottomPanel、GameLoop、EnhancedRenderer全部崩溃~~ | ~~低~~ | ✅ 已修复 |
| ~~P0-2~~ | ~~HealthComponent属性名不匹配~~ | ~~CC2BottomPanel访问health.current/max不存在~~ | ~~低~~ | ✅ 已修复 |
| ~~P0-3~~ | ~~MoraleComponent属性名不匹配~~ | ~~CC2BottomPanel访问morale.current不存在~~ | ~~低~~ | ✅ 已修复 |
| ~~P0-4~~ | ~~AttackNearestAI/MoveToObjectiveAI不存在~~ | ~~AI行为树初始化失败，敌方无智能~~ | ~~中~~ | ✅ 已修复 |
| P0-5 | 测试未捕获致命bug | 信心危机，无法保证后续开发质量 | 中 | ❌ 未解决 |

### P1 - 严重（影响核心功能完整性）

| 编号 | 问题 | 影响范围 | 修复复杂度 |
|------|------|----------|------------|
| P1-1 | set_mode不接受fast/sneak参数 | Fast/Sneak命令不可操作 | 低：扩展set_mode签名 |
| P1-2 | Smoke/Defend无InteractionMode | 两个命令无法进入对应交互模式 | 中：添加SMOKE/DEFEND模式 |
| P1-3 | PNG精灵未正确接入渲染管线 | 单位显示几何形状 | 中：修复AssetLoader→SpriteRenderer缓存传递 |
| P1-4 | domain层严重膨胀 | 维护困难、编译慢、职责混乱 | 高：需重构分层 |
| P1-5 | 巨型文件（8个>1000行） | 可读性差、修改风险高 | 高：需拆分 |
| P1-6 | integration测试严重不足 | 模块间交互无保障 | 中：补充集成测试 |
| P1-7 | GameLoop上帝类 | 修改任何功能都影响全局 | 高：需拆分职责 |

### P2 - 改善（影响开发效率和代码质量）

| 编号 | 问题 | 影响范围 | 修复复杂度 |
|------|------|----------|------------|
| P2-1 | infra/与infrastructure/重叠 | 命名混淆 | 低：合并 |
| P2-2 | 32个调试脚本散落 | 代码库混乱 | 低：清理或迁移 |
| P2-3 | 4份视觉优化文档重叠 | 执行标准不统一 | 低：合并为1份 |
| P2-4 | 根目录11个.md文件 | 项目根目录混乱 | 低：迁移到docs/ |
| P2-5 | 地图纹理粗糙 | 视觉体验差 | 中：需美术资源 |
| P2-6 | 部署界面非CC2风格 | 用户体验差距 | 中：需重写UI |
| P2-7 | CI缺少e2e阶段 | 无法自动捕获界面回归 | 中：配置headless测试 |
| P2-8 | 存档无数据校验 | 安全风险 | 低：添加schema验证 |
| P2-9 | 重复单位定义系统 | 维护成本高 | 中：统一数据源 |

---

## 三、具体修复方案

### P0修复方案

**~~P0-1: Unit添加display_name属性~~ ✅ 已修复**
- 在`Unit` dataclass中添加了`display_name: str`字段
- 在`GameLoop._create_unit_from_template()`中，从`UnitTemplate.display_name`赋值

**~~P0-2/P0-3: 统一组件属性访问~~ ✅ 已修复**
- 在HealthComponent/MoraleComponent上添加了`current`/`max` property别名，映射到实际字段

**~~P0-4: 修复AI行为树导入~~ ✅ 已修复**
- 实现了`AttackNearestAI`和`MoveToObjectiveAI`类

**P0-5: 补充关键路径测试** ❌ 未解决
- 添加Unit实体属性访问的单元测试
- 添加CC2BottomPanel渲染的集成测试（mock Unit对象）
- 添加AI行为树导入的冒烟测试

### P1修复方案

**P1-1/P1-2: 完善命令系统**
- 扩展`InteractionMode`枚举：添加FAST/SNEAK/SMOKE/DEFEND
- 扩展`set_mode`签名：`set_mode(self, mode: InteractionMode, **kwargs)`
- 在InteractionController中实现各模式的handle_click逻辑

**P1-3: 修复精灵渲染管线**
- AssetLoader添加公共方法`get_sprite_cache()`替代私有属性访问
- SpriteRenderer.initialize()改用公共API获取PNG精灵
- 确保UNIT_TYPE_MAP的键与Unit.unit_type.name匹配

**P1-4/P1-5: 架构重构**
- 将campaign相关系统从domain/systems移至services层
- 将persistence/replay从domain移至infrastructure层
- 拆分deployment_ui.py为：DeploymentModel + DeploymentRenderer + DeploymentController
- 拆分game_loop.py为：GameState + InputHandler + BattleController

**P1-6: 补充集成测试**
- 添加Unit→Panel渲染集成测试
- 添加Command→InteractionController集成测试
- 添加AI→BehaviorTree集成测试

**P1-7: 拆分GameLoop**
- 提取GameState管理到独立类
- 提取UnitFactory到独立类
- 提取BattleController到独立类
- GameLoop仅保留主循环调度

### P2修复方案

**P2-1: 合并infra/到infrastructure/**
- 将infra/config.py的Settings移至infrastructure/config.py
- 删除infra/目录
- 更新所有导入路径

**P2-2: 清理scripts/目录**
- 有用的脚本（convert_cc2_map.py等）保留并添加文档
- 调试脚本（debug_*）移至scripts/debug/子目录
- 临时测试脚本（test_*）评估后迁移到tests/或删除

**P2-3/P2-4: 文档整理**
- 合并4份视觉优化文档为1份VISUAL_SPEC.md
- 根目录.md文件迁移到docs/（保留README.md和INSTALL.md）
- 删除过时的BUG_FIX_REPORT等临时文档

**P2-8: 存档数据校验**
- 添加save file schema验证
- 对关键字段添加类型和范围检查
- 添加版本号字段支持向前兼容

**P2-9: 统一单位定义**
- 以cc2_authentic_units.py为权威数据源
- UNIT_TEMPLATES改为从cc2_authentic_units动态生成
- 删除unit_diversity_expansion.py中的重复定义

---

## 四、里程碑计划

### M1: 紧急修复（1-2天）— 让游戏可玩

| 任务 | 优先级 | 预估工时 |
|------|--------|----------|
| ~~P0-1: Unit添加display_name~~ | ~~P0~~ | ~~0.5h~~ ✅ |
| ~~P0-2/3: 组件属性别名~~ | ~~P0~~ | ~~1h~~ ✅ |
| ~~P0-4: 实现AttackNearestAI~~ | ~~P0~~ | ~~2h~~ ✅ |
| P0-5: 补充冒烟测试 | P0 | 2h |
| P1-1: set_mode签名扩展 | P1 | 1h |
| **验收标准** | | 游戏可启动、面板可显示、AI可行动、Fast/Sneak命令可触发 |

### M2: 核心功能完善（3-5天）— 让游戏好玩

| 任务 | 优先级 | 预估工时 |
|------|--------|----------|
| P1-2: Smoke/Defend交互模式 | P1 | 4h |
| P1-3: 修复精灵渲染管线 | P1 | 4h |
| P1-6: 补充集成测试 | P1 | 4h |
| P2-8: 存档数据校验 | P2 | 2h |
| **验收标准** | | 7命令全部可操作、单位显示PNG精灵、集成测试通过 |

### M3: 架构重构（5-7天）— 让代码可维护

| 任务 | 优先级 | 预估工时 |
|------|--------|----------|
| P1-4: domain层瘦身 | P1 | 8h |
| P1-5: 巨型文件拆分 | P1 | 8h |
| P1-7: GameLoop拆分 | P1 | 6h |
| P2-1: 合并infra/ | P2 | 1h |
| P2-9: 统一单位定义 | P2 | 4h |
| **验收标准** | | 无文件超800行、domain层<50%代码量、所有测试通过 |

### M4: 质量提升（3-5天）— 让项目可持续

| 任务 | 优先级 | 预估工时 |
|------|--------|----------|
| P2-2: 清理scripts/ | P2 | 2h |
| P2-3/4: 文档整理 | P2 | 3h |
| P2-7: CI添加e2e阶段 | P2 | 4h |
| 补充用户操作E2E测试 | P2 | 6h |
| **验收标准** | | CI全绿、文档无重叠、scripts/整洁 |

### M5: 视觉打磨（5-7天）— 让游戏好看

| 任务 | 优先级 | 预估工时 |
|------|--------|----------|
| P2-5: 地图纹理优化 | P2 | 8h |
| P2-6: CC2风格部署界面 | P2 | 8h |
| UI像素级对齐CC2原版 | P2 | 6h |
| **验收标准** | | 截图对比CC2原版，视觉还原度>80% |

---

## 五、验收标准

### M1验收标准（最小可玩版本）

- [ ] 游戏可正常启动，无崩溃
- [ ] CC2BottomPanel正确显示选中单位的名称、血量、士气、弹药
- [ ] AI单位在战场上自主移动和攻击
- [ ] Move/Fast/Sneak/Attack/Cancel命令可触发对应交互模式
- [ ] 冒烟测试全部通过

### M2验收标准（功能完整版本）

- [ ] 7命令（Move/Fast/Sneak/Attack/Smoke/Defend/Cancel）全部可操作
- [ ] 单位使用PNG精灵渲染，非几何形状
- [ ] 集成测试覆盖核心交互路径
- [ ] 存档加载有数据校验

### M3验收标准（架构健康版本）

- [ ] 无Python文件超过800行
- [ ] domain层代码量<50%
- [ ] GameLoop<400行
- [ ] 所有现有测试通过
- [ ] 无循环依赖

### M4验收标准（质量达标版本）

- [ ] CI包含lint + unit + integration + e2e四阶段
- [ ] scripts/目录仅保留有用工具脚本
- [ ] docs/无重叠文档
- [ ] 用户操作E2E测试覆盖：选单位→下命令→观察结果

### M5验收标准（视觉还原版本）

- [ ] 与CC2原版截图对比，底部面板还原度>85%
- [ ] 单位精灵还原度>80%
- [ ] 地图纹理还原度>70%
- [ ] 部署界面还原度>75%

---

## 六、风险与建议

### 高风险项

1. **重构可能引入新bug**：M3的架构重构涉及大量文件移动和导入修改，建议每步重构后立即运行全量测试
2. **PNG精灵加载时机**：SpriteRenderer的initialize()依赖pygame display已初始化，需确保调用顺序正确
3. **AI行为树接口兼容**：AttackNearestAI需兼容现有BehaviorTree的Node接口，需先确认接口定义

### 建议

1. **先修P0再动架构**：不要在致命bug未修的情况下做重构
2. **每完成一个Milestone做一次E2E验证**：模拟真实用户操作流程
3. **建立代码审查checklist**：新增代码必须包含对应测试，组件属性访问必须与定义一致
4. **冻结新功能开发**：在M1-M2完成前，不接受新功能PR

---

> 本文档由DevSquad 7角色交叉Review生成，各角色发现已交叉验证。
> 下一步：按M1计划执行紧急修复。
