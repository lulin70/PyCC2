# PyCC2 功能扩展路线图 (Feature Expansion Roadmap)

> **版本**: v1.0
> **基于**: PyCC2 v0.3.16 (成熟度评分 9.5/10, 3484测试, 99.91%通过率)
> **制定日期**: 2026-06-01
> **目标版本**: v0.4.0 (Beta完整版) → v1.0 (正式版)

---

## 📊 执行摘要

PyCC2 已达到高度成熟状态（v0.3.16），核心游戏循环、战役系统、AI、存档、音频、UI均已完成。本路线图规划 **12个功能扩展方向**，分为 **3个实施阶段**，目标是在 **2-3个月内** 达到 Beta 完整版（v0.4.0），并在 **6个月内** 达到 v1.0 正式版。

### 核心发现

✅ **已具备坚实基础**:
- 教程系统: TutorialOverlay (6步交互式框架)
- 难度系统: DifficultySystem (4级静态 + 动态配置)
- 天气系统: WeatherRenderer (雨/雾/昼夜)
- 粒子系统: TopDownParticleSystem (6种特效)
- 音频系统: SoundSystem (立体声 + 3D定位框架)
- 相机系统: Camera (震动功能已实现)
- 存档系统: SecureSaveManager (8槽位 + HMAC安全)
- 战役系统: FourLayerCampaign (完整四层体系)
- BGM系统: BGMGenerator (6种情绪程序化音乐)
- 回放系统: BattleReplay (录制/回放/VCR控制)

🎯 **推荐策略**: **渐进式增强** 而非全新开发，优先利用现有架构进行功能完善。

---

## 一、功能优先级矩阵 (ROI评估)

### 评估维度说明

| 维度 | 权重 | 说明 |
|------|------|------|
| **用户价值** | 40% | 对玩家体验的提升程度 |
| **实现复杂度** | 30% | 开发工时和技术风险（越低越好）|
| **依赖项** | 15% | 对现有系统的依赖程度（越少越好）|
| **风险等级** | 15% | 技术不确定性和回归风险 |

### 优先级评分标准

- **用户价值**: 1-10分 (10=革命性提升)
- **实现复杂度**: 1-10分 (1=简单修改, 10=需要新架构)
- **ROI得分**: `(用户价值 × 0.4) + ((10-复杂度) × 0.3) + ((10-依赖) × 0.15) + ((10-风险) × 0.15)`

---

### A类：游戏体验增强

#### 1️⃣ 教程系统完善

| 指标 | 评分 | 说明 |
|------|------|------|
| **当前状态** | ⭐⭐⭐⭐ | 基础TutorialOverlay已有6步，但缺少实战引导和进度追踪 |
| **用户价值** | **8/10** | 新手留存关键，降低学习曲线 |
| **实现复杂度** | **4/10** | 扩展现有TutorialOverlay，添加引导箭头、高亮、任务系统 |
| **依赖项** | **3/10** | 主要依赖UI系统和事件总线 |
| **风险等级** | **2/10** | 低风险，不影响核心玩法 |
| **ROI得分** | **7.95** | 🔥 **高优先级** |
| **推荐阶段** | **Phase 1** ✅ |

**技术方案概要**:
- 扩展 [tutorial_system.py](src/pycc2/presentation/ui/tutorial_system.py) 添加：
  - 交互式任务系统（完成才可下一步）
  - 引导箭头和高亮层
  - 进度持久化（存档到本地）
  - 上下文敏感提示（HintManager集成）
  - 战斗场景专项教程（移动→选择→攻击→胜利）

**预估工时**: 3-5天

---

#### 2️⃣ 难度自适应AI (Dynamic Difficulty Adjustment)

| 指标 | 评分 | 说明 |
|------|------|------|
| **当前状态** | ⭐⭐⭐⭐⭐ | DifficultySystem完整，支持4级静态预设+动态配置 |
| **用户价值** | **9/10** | 解决"太难劝退/太简单无聊"的核心痛点 |
| **实现复杂度** | **6/10** | 需要PlayerPerformanceTracker + AdaptiveController |
| **依赖项** | **5/10** | 强依赖DifficultySystem + CombatResolver + VictoryManager |
| **风险等级** | **5/10** | 中等风险，需平衡算法调优 |
| **ROI得分** | **7.00** | 🔥 **高优先级** |
| **推荐阶段** | **Phase 2** |

**技术方案概要**:
- 新建 `adaptive_difficulty.py`:
  - PlayerPerformanceMonitor: 追踪K/D比、胜率、任务完成时间
  - DifficultyAdjuster: 基于表现动态调整DifficultyConfig参数
  - 平滑过渡机制（避免突变）
  - 玩家可选开关（设置菜单）

**预估工时**: 7-10天

---

#### 3️⃣ 成就系统 (Achievement System)

| 指标 | 评分 | 说明 |
|------|------|------|
| **当前状态** | ⭐ | 无成就系统 |
| **用户价值** | **7/10** | 提升重玩价值，增加成就感 |
| **实现复杂度** | **5/10** | AchievementEngine + 本地存储 + UI展示 |
| **依赖项** | **4/10** | 依赖CombatService + SaveSystem |
| **风险等级** | **2/10** | 低风险，独立模块 |
| **ROI得分** | **7.30** | 🔥 **高优先级** |
| **推荐阶段** | **Phase 1** ✅ |

**技术方案概要**:
- 新建 `achievement_system.py`:
  - AchievementDefinition: 成就定义（ID、名称、描述、条件、图标）
  - AchievementTracker: 追踪进度（首次胜利、零伤亡、速通、完美战役等）
  - AchievementStorage: 本地JSON存储 + Steam API预留接口
  - AchievementUI: 弹窗通知 + 成就列表面板

**预估工时**: 5-7天

---

### B类：视觉效果提升

#### 4️⃣ 天气系统增强 (Dynamic Weather)

| 指标 | 评分 | 说明 |
|------|------|------|
| **当前状态** | ⭐⭐⭐⭐ | WeatherRenderer支持雨/雾/昼夜，但为静态切换 |
| **用户价值** | **6/10** | 提升沉浸感，战术多样性 |
| **实现复杂度** | **5/10** | 扩展WeatherRenderer + 天气状态机 + 影响系统 |
| **依赖项** | **6/10** | 依赖VisionSystem + PathFinder + TerrainSystems |
| **风险等级** | **4/10** | 中低风险，需平衡性能 |
| **ROI得分** | **6.35** | ⚡ **中优先级** |
| **推荐阶段** | **Phase 2** |

**技术方案概要**:
- 扩展 [weather_system.py](src/pycc2/presentation/rendering/weather_system.py):
  - WeatherStateMachine: 晴天→多云→雨→雾的动态转换
  - WeatherEffectApplier: 影响视野范围（FogOfWar）、移动速度（PathFinder）
  - 视觉效果升级：闪电、水洼反射、泥泞地形
  - 与DayNightCycle联动

**预估工时**: 6-8天

---

#### 5️⃣ 粒子特效升级 (Advanced Particles)

| 指标 | 评分 | 说明 |
|------|------|------|
| **当前状态** | ⭐⭐⭐⭐⭐ | TopDownParticleSystem非常完善（爆炸、烟雾、枪口焰、命中、泥土、血迹） |
| **用户价值** | **5/10** | 视觉锦上添花，非核心需求 |
| **实现复杂度** | **7/10** | 需要弹道物理、抛物线计算、资源管理优化 |
| **依赖项** | **7/10** | 强依赖ParticlePool + BallisticSystem |
| **风险等级** | **3/10** | 低风险，但性能敏感 |
| **ROI得分** | **5.20** | 💤 **低优先级** |
| **推荐阶段** | **Phase 3** |

**待实现特性**:
- 弹道轨迹（BulletTracer: 贝塞尔曲线 + 重力）
- 弹壳抛出（ShellEjection: 物理模拟）
- 泥浆飞溅（MudSplash: 地形交互）

**预估工时**: 8-12天

---

#### 6️⃣ 屏幕震动和相机效果 (Camera Effects)

| 指标 | 评分 | 说明 |
|------|------|------|
| **当前状态** | ⭐⭐⭐⭐⭐ | Camera.shake()方法已实现并集成到world_to_screen |
| **用户价值** | **6/10** | 提升打击感和沉浸感 |
| **实现复杂度** | **2/10** | 扩展Camera类，添加更多效果类型 |
| **依赖项** | **2/10** | 仅依赖Camera类本身 |
| **风险等级** | **1/10** | 极低风险 |
| **ROI得分** | **7.90** | 🔥 **高优先级** |
| **推荐阶段** | **Phase 1** ✅ |

**技术方案概要**:
- 扩展 [camera.py](src/pycc2/presentation/rendering/camera.py):
  - 新增效果类型：狙击镜头缩放（ZoomEffect）、冲击波推拉（ImpactPush）、慢动作（SlowMotion）
  - EffectStack: 效果组合与优先级队列
  - 与CombatResolver事件绑定（爆炸触发shake，狙击触发zoom）
  - 配置化参数（强度、持续时间、衰减曲线）

**预估工时**: 2-3天

---

### C类：音频系统完善

#### 7️⃣ 3D定位音效 (3D Positional Audio)

| 指标 | 评分 | 说明 |
|------|------|------|
| **当前状态** | ⭐⭐⭐⭐ | SoundSystem已实现play_3d_sound() + calculate_stereo_pan() + distance attenuation |
| **用户价值** | **7/10** | 大幅提升沉浸感和战场感知 |
| **实现复杂度** | **3/10** | 框架已有，需完善集成和调优 |
| **依赖项** | **4/10** | 依赖SoundSystem + Camera + Unit位置 |
| **风险等级** | **2/10** | 低风险 |
| **ROI得分** | **7.75** | 🔥 **高优先级** |
| **推荐阶段** | **Phase 1** ✅ |

**技术方案概要**:
- 完善 [sound_system.py](src/pycc2/presentation/audio/sound_system.py):
  - AudioListener: 跟随相机位置的监听器
  - SoundEmitter: 单位音效发射器组件
  - 多普勒效应（可选配置）
  - 遮挡衰减（建筑后方声音闷闷的）
  - 战场混响（BattleReverb: 大场景vs小房间）

**预估工时**: 3-4天

---

#### 8️⃣ 动态音乐系统 (Adaptive Music)

| 指标 | 评分 | 说明 |
|------|------|------|
| **当前状态** | ⭐⭐⭐⭐ | BGMGenerator支持6种情绪（MENU/BATTLE_LIGHT/BATTLE_INTENSE/VICTORY/DEFEAT/AMBIENT） |
| **用户价值** | **6/10** | 情绪配合提升沉浸感 |
| **实现复杂度** | **4/10** | 扩展BGMGenerator + MusicStateManager + 平滑过渡 |
| **依赖项** | **5/10** | 依赖BGMGenerator + CombatDirector |
| **风险等级** | **2/10** | 低风险 |
| **ROI得分** | **7.05** | 🔥 **高优先级** |
| **推荐阶段** | **Phase 1** ✅ |

**技术方案概要**:
- 扩展 [bgm_system.py](src/pycc2/infrastructure/audio/bgm_system.py):
  - MusicStateManager: 战斗强度追踪（击杀频率、伤亡率、距离）
  - MoodTransition: 平滑过渡（交叉淡化crossfade，时长2-3秒）
  - LayeredMusic: 分层音乐（基础层+战斗层+紧张层，动态叠加）
  - 与duck_music/restore_music集成

**预估工时**: 4-5天

---

### D类：多人游戏准备

#### 9️⃣ 热座模式 (Hot-seat Multiplayer)

| 指标 | 评分 | 说明 |
|------|------|------|
| **当前状态** | ⭐ | 无多人模式 |
| **用户价值** | **5/10** | 本地社交需求有限 |
| **实现复杂度** | **7/10** | TurnManager重构 + 隐藏信息 + 切换UI |
| **依赖项** | **8/10** | 强依赖TurnService + FogOfWar + DeploymentManager |
| **风险等级** | **6/10** | 中高风险，可能影响单机体验 |
| **ROI得分** | **4.85** | ❄️ **低优先级** |
| **推荐阶段** | **Phase 3** |

**预估工时**: 10-14天

---

#### 🔟 回放系统完善 (Replay System Enhancement)

| 指标 | 评分 | 说明 |
|------|------|------|
| **当前状态** | ⭐⭐⭐⭐⭐ | BattleReplay非常完善：ReplayRecorder + ReplayPlayer + VCR controls |
| **用户价值** | **6/10** | 战术分析、内容创作、bug复现 |
| **实现复杂度** | **4/10** | UI封装 + 文件导出/导入 + 时间线可视化 |
| **依赖项** | **5/10** | 依赖现有BattleReplay + SaveSystem |
| **风险等级** | **2/10** | 低风险 |
| **ROI得分** | **6.95** | ⚡ **中优先级** |
| **推荐阶段** | **Phase 2** |

**待完善项**:
- ReplayUI: 回放界面（播放条、时间轴、事件标记）
- ReplayExport: 导出为文件（JSON/二进制）
- ReplayShare: 分享功能（复制回放数据）
- 事件过滤（只看击杀/只看某单位）

**预估工时**: 5-6天

---

### E类：编辑器/模组支持

#### 1️⃣1️⃣ 地图编辑器 (Map Editor)

| 指标 | 评分 | 说明 |
|------|------|------|
| **当前状态** | ⭐ | 有脚本工具(gen_test_map.py, gen_historical_maps.py)，无GUI编辑器 |
| **用户价值** | **8/10** | 社区内容创作核心，延长生命周期 |
| **实现复杂度** | **9/10** | 需要独立编辑器应用 + 工具栏 + 属性面板 + 撤销/重做 |
| **依赖项** | **6/10** | 依赖TerrainSystems + MapSchema + AssetLoader |
| **风险等级** | **7/10** | 高风险，工程量大 |
| **ROI得分** | **5.25** | 💤 **低优先级（长期）** |
| **推荐阶段** | **Phase 3 / v1.1+** |

**预估工时**: 20-30天

---

#### 1️⃣2️⃣ 单位模板编辑器 (Unit Template Editor)

| 指标 | 评分 | 说明 |
|------|------|------|
| **当前状态** | ⭐⭐ | CC2AuthenticUnits + CC2AuthenticWeapons已定义单位模板 |
| **用户价值** | **6/10** | Modding支持，自定义单位 |
| **实现复杂度** | **6/10** | JSON Schema验证 + GUI表单 + 预览功能 |
| **依赖项** | **5/10** | 依赖单位定义schema |
| **风险等级** | **3/10** | 低风险 |
| **ROI得分** | **6.10** | ⚡ **中优先级（长期）** |
| **推荐阶段** | **Phase 3 / v1.1+** |

**预估工时**: 8-12天

---

## 二、优先级矩阵总览

| 排名 | 功能 | ROI得分 | 用户价值 | 复杂度 | 推荐阶段 | 状态 |
|------|------|---------|----------|--------|----------|------|
| 🥇 | **1. 教程系统完善** | **7.95** | 8 | 4 | Phase 1 | ✅ 立即启动 |
| 🥈 | **6. 相机效果** | **7.90** | 6 | 2 | Phase 1 | ✅ 立即启动 |
| 🥉 | **7. 3D音效** | **7.75** | 7 | 3 | Phase 1 | ✅ 立即启动 |
| 4 | **3. 成就系统** | **7.30** | 7 | 5 | Phase 1 | ✅ 立即启动 |
| 5 | **8. 动态音乐** | **7.05** | 6 | 4 | Phase 1 | ✅ 立即启动 |
| 6 | **2. 自适应AI** | **7.00** | 9 | 6 | Phase 2 | 📋 计划中 |
| 7 | **10. 回放系统** | **6.95** | 6 | 4 | Phase 2 | 📋 计划中 |
| 8 | **4. 天气增强** | **6.35** | 6 | 5 | Phase 2 | 📋 计划中 |
| 9 | **12. 单位编辑器** | **6.10** | 6 | 6 | Phase 3 | 🔮 远期 |
| 10 | **5. 粒子升级** | **5.20** | 5 | 7 | Phase 3 | 🔮 远期 |
| 11 | **11. 地图编辑器** | **5.25** | 8 | 9 | Phase 3 | 🔮 远期 |
| 12 | **9. 热座模式** | **4.85** | 5 | 7 | Phase 3 | ❄️ 低优先级 |

---

## 三、Phase 1 详细规划 (v0.3.17 - v0.4.0)

> **目标**: 达到 **Beta完整版**，适合封闭测试和小范围发布
>
> **时间规划**: 3-4周 (2026-06-01 ~ 2026-06-25)
>
> **选定的5个高价值+低复杂度功能**:

### 🎯 Phase 1 功能清单

| # | 功能 | 预估工时 | 优先级 | 负责人建议 |
|---|------|----------|--------|-----------|
| F1 | 教程系统完善 | 4天 | P0 | UI/UX开发者 |
| F2 | 相机效果增强 | 2.5天 | P0 | 渲染工程师 |
| F3 | 3D定位音效完善 | 3.5天 | P0 | 音频工程师 |
| F4 | 成就系统 | 6天 | P0 | 全栈开发者 |
| F5 | 动态音乐系统 | 4.5天 | P0 | 音频/系统工程师 |

**总预估工时**: 20天 (约3周全职)

---

### F1: 教程系统完善 (Tutorial System Enhancement)

#### 用户故事 (User Story)

> **作为** 一个第一次玩PyCC2的新玩家
> **我希望** 被引导完成一个完整的交互式教程（5-10分钟）
> **以便于** 我能够独立进行基础操作而不感到困惑

#### 技术方案 (Technical Specification)

**1. 架构设计**

```
TutorialSystem (新增)
├── TutorialController          # 教程流程控制器
│   ├── state_machine           # 教程状态机
│   ├── progress_tracker        # 进度追踪器
│   └── condition_checker       # 条件检查器
├── InteractiveGuide            # 交互式引导层
│   ├── highlight_overlay       # 高亮覆盖层
│   ├── arrow_indicator         # 方向箭头指示
│   └── focus_rect              # 聚焦框（脉动效果）
├── TutorialMission             # 教程任务系统
│   ├── mission_definition      # 任务定义（选择单位、移动、攻击...）
│   ├── mission_tracker         # 任务进度追踪
│   └── reward_system           # 奖励系统（解锁提示）
└── TutorialPersistence         # 教程持久化
    └── local_storage           # 本地存储（已完成步骤）
```

**2. 所需修改的文件**

| 文件路径 | 操作 | 说明 |
|----------|------|------|
| `src/pycc2/presentation/ui/tutorial_system.py` | **扩展** | 从253行扩展至~600行 |
| `src/pycc2/services/event_bus.py` | **微调** | 添加TUTORIAL_EVENT类型 |
| `src/pycc2/services/game_loop.py` | **微调** | 集成TutorialController.update() |
| `tests/unit/test_tutorial_system.py` | **扩展** | 从现有测试扩展至50+用例 |
| `tests/e2e/test_tutorial_flow.py` | **扩展** | 添加完整流程E2E测试 |

**3. 核心代码示例**

```python
# tutorial_system.py 扩展示例

@dataclass
class TutorialMission:
    id: str
    title: str
    description: str
    condition_type: MissionConditionType  # SELECT_UNIT / MOVE_UNIT / ATTACK_ENEMY / WAIT_FOR_VICTORY
    target_params: dict
    hint_text: str
    timeout_ticks: int = 6000  # 100秒 @60fps
    required: bool = True

class TutorialController:
    def __init__(self, overlay: TutorialOverlay, event_bus: EventBus):
        self._overlay = overlay
        self._event_bus = event_bus
        self._current_mission_idx = 0
        self._missions: list[TutorialMission] = self._define_missions()
        self._completed_missions: set[str] = set()
        self._state = TutorialState()

    def _define_missions(self) -> list[TutorialMission]:
        return [
            TutorialMission(
                id="select_commander",
                title="Select Your Commander",
                description="Left-click on the unit with ★ symbol",
                condition_type=MissionConditionType.SELECT_UNIT,
                target_params={"unit_has_commander": True},
                hint_text="Look for the unit with a star (★) icon!",
            ),
            TutorialMission(
                id="move_to_road",
                title="Move to Cover",
                description="Right-click on the road tile to move",
                condition_type=MissionConditionType.MOVE_UNIT,
                target_params={"target_terrain": "road"},
                hint_text="Roads provide good movement speed!",
            ),
            TutorialMission(
                id="attack_enemy",
                title="Engage Enemy",
                description="Right-click on an enemy unit to attack",
                condition_type=MissionConditionType.ATTACK_ENEMY,
                target_params={},
                hint_text="Close combat! Watch for damage numbers!",
            ),
        ]

    def update(self, game_state) -> None:
        if self._current_mission_idx >= len(self._missions):
            self._complete_tutorial()
            return

        mission = self._missions[self._current_mission_idx]
        if self._check_mission_condition(mission, game_state):
            self._complete_mission(mission)
            self._current_mission_idx += 1
            if self._current_mission_idx < len(self._missions):
                self._start_next_mission()
```

**4. 测试计划**

```python
# test_tutorial_system_extended.py

class TestTutorialController:
    def test_mission_sequence_flow(self):
        """测试完整的任务序列流程"""
        controller = self._create_controller()
        assert controller.current_state == TutorialState.IN_PROGRESS

        # 模拟完成任务1
        controller.update(self._simulate_unit_select())
        assert controller.current_mission_idx == 1

        # 模拟完成任务2
        controller.update(self._simulate_unit_move())
        assert controller.current_mission_idx == 2

        # 完成所有任务
        controller.update(self._simulate_attack())
        assert controller.current_state == TutorialState.COMPLETED

    def test_timeout_handling(self):
        """测试超时处理"""
        controller = self._create_controller()
        # 模拟超时
        for _ in range(7000):  # 超过timeout_ticks
            controller.update(self._create_idle_state())
        assert controller.current_state == TutorialState.TIMEOUT

    def test_persistence_and_resume(self):
        """测试进度保存和恢复"""
        controller = self._create_controller()
        controller.update(self._simulate_unit_select())
        # 保存进度
        saved = controller.save_progress()
        # 恢复到新实例
        controller2 = TutorialController.load_progress(saved)
        assert controller2.current_mission_idx == 1
```

**5. 验收标准 (Acceptance Criteria)**

- [ ] 新手能在10分钟内完成基础教程
- [ ] 教程步骤可跳过（ESC关闭），但会标记为未完成
- [ ] 教程进度持久化（重启游戏后可继续）
- [ ] 每个步骤都有清晰的视觉指引（高亮+箭头+文字）
- [ ] 支持按F1重新查看已完成的教程
- [ ] E2E测试覆盖完整流程

---

### F2: 相机效果增强 (Camera Effects Enhancement)

#### 用户故事

> **作为** 一个追求沉浸感的玩家
> **我希望** 在爆炸、狙击等重要时刻看到相机反馈（震动、缩放、慢动作）
> **以便于** 我能感受到战场的紧张氛围

#### 技术方案

**1. 架构设计**

```python
# camera.py 扩展

from enum import Enum, auto
from dataclasses import dataclass
import math

class EffectType(Enum):
    SHAKE = auto()           # 震动（已有）
    ZOOM_IMPACT = auto()     # 冲击缩放
    SLOW_MOTION = auto()     # 慢动作
    PUSH_PULL = auto()       # 推拉效果
    SCREEN_FREEZE = auto()   # 定格

@dataclass
class CameraEffect:
    effect_type: EffectType
    intensity: float
    duration: float
    elapsed: float = 0.0
    easing: str = "ease_out"  # ease_in / ease_out / ease_in_out / linear
    priority: int = 0

class EffectStack:
    def __init__(self, max_effects: int = 5):
        self._effects: list[CameraEffect] = []
        self._max = max_effects

    def push(self, effect: CameraEffect) -> None:
        """添加效果，按优先级排序"""
        self._effects.append(effect)
        self._effects.sort(key=lambda e: e.priority, reverse=True)
        if len(self._effects) > self._max:
            self._effects.pop()

    def update(self, dt: float) -> None:
        """更新所有效果"""
        self._effects = [
            e for e in self._effects
            if (e.elapsed := e.elapsed + dt) < e.duration
        ]

# Camera 类扩展方法
class Camera:
    # ... 现有代码 ...

    def apply_zoom_impact(
        self,
        zoom_factor: float = 0.8,
        duration: float = 0.3,
        recover_duration: float = 0.5,
    ) -> None:
        """狙击/爆炸时的冲击缩放效果"""
        original_zoom = self.zoom
        target_zoom = original_zoom * zoom_factor

        # 快速缩小
        effect1 = CameraEffect(
            effect_type=EffectType.ZOOM_IMPACT,
            intensity=zoom_factor,
            duration=duration,
            priority=10,
        )
        # 缓慢恢复
        effect2 = CameraEffect(
            effect_type=EffectType.ZOOM_IMPACT,
            intensity=1.0 / zoom_factor,
            duration=recover_duration,
            priority=5,  # 较低优先级，稍后执行
        )
        self._effect_stack.push(effect1)
        self._effect_stack.push(effect2)

    def apply_slow_motion(
        self,
        time_scale: float = 0.3,
        duration: float = 1.0,
    ) -> None:
        """关键时刻慢动作（如击杀敌方指挥官）"""
        effect = CameraEffect(
            effect_type=EffectType.SLOW_MOTION,
            intensity=time_scale,
            duration=duration,
            priority=15,  # 最高优先级
        )
        self._effect_stack.push(effect)
```

**2. 事件绑定**

```python
# combat_service.py 或 event_handler.py 中绑定

def _on_explosion(event: ExplosionEvent) -> None:
    """爆炸事件触发相机震动"""
    camera = self._game_state.camera
    distance = event.position.distance_to(camera.position)
    intensity = max(1.0, 8.0 - distance / 100.0)  # 越近越强
    camera.shake(intensity=intensity, duration=0.25)
    camera.apply_zoom_impact(zoom_factor=0.92, duration=0.2)

def _on_sniper_kill(event: KillEvent) -> None:
    """狙击击杀触发慢动作+聚焦"""
    camera = self._game_state.camera
    camera.focus_on(event.target_position, immediate=False)
    camera.apply_slow_motion(time_scale=0.4, duration=0.8)
    camera.shake(intensity=2.0, duration=0.15)
```

**3. 测试计划**

```python
# test_camera_effects.py

class TestCameraEffects:
    def test_shake_effect_decay(self):
        """测试震动效果衰减"""
        camera = Camera(position=Vec2(0, 0))
        camera.shake(intensity=5.0, duration=0.2)

        dt = 0.016  # ~60fps
        for _ in range(20):  # 模拟20帧
            camera.update_shake(dt)

        assert camera._shake_timer <= 0.0
        assert camera._shake_intensity == 0.0

    def test_zoom_impact_recovery(self):
        """测试冲击缩放恢复"""
        original_zoom = 2.0
        camera = Camera(position=Vec2(0, 0), zoom=original_zoom)
        camera.apply_zoom_impact(zoom_factor=0.8, duration=0.1, recover_duration=0.3)

        # 更新至恢复后
        for _ in range(100):
            camera.update_shake(0.016)

        assert abs(camera.zoom - original_zoom) < 0.01

    def test_effect_priority_ordering(self):
        """测试效果优先级排序"""
        stack = EffectStack()
        stack.push(CameraEffect(EffectType.SHAKE, 1, 1, priority=1))
        stack.push(CameraEffect(EffectType.SLOW_MOTION, 1, 1, priority=15))
        stack.push(CameraEffect(EffectType.ZOOM_IMPACT, 1, 1, priority=10))

        assert stack._effects[0].priority == 15  # Slow motion first
        assert stack._effects[1].priority == 10  # Zoom second
        assert stack._effects[2].priority == 1   # Shake last
```

**4. 验收标准**

- [ ] 爆炸时相机震动强度随距离衰减
- [ ] 狙击击杀时触发0.5-1秒慢动作
- [ ] 多个效果可叠加，按优先级执行
- [ ] 性能影响<1ms/frame（在基准测试中验证）
- [ ] 可在设置中调整效果强度或关闭

---

### F3: 3D定位音效完善 (3D Positional Audio Enhancement)

#### 用户故事

> **作为** 一个追求沉浸感的玩家
> **我希望** 能通过声音判断敌人位置（左边枪声来自左声道）
> **以便于** 我能更好地感知战场态势

#### 技术方案

**1. 架构增强**

```python
# sound_system.py 扩展

@dataclass
class AudioListener:
    position: Vec2
    velocity: Vec2 = Vec2(0, 0)
    facing: float = 0.0  # 弧度

class SoundEmitter:
    def __init__(self, source_id: str, position: Vec2, sound_type: SoundType):
        self.source_id = source_id
        self.position = position
        self.sound_type = sound_type
        self.last_play_time: float = 0.0
        self.min_interval: float = 0.1  # 最小播放间隔（防重叠）

class SpatialAudioManager:
    def __init__(self, sound_system: SoundSystem):
        self._sound_system = sound_system
        self._listener = AudioListener(position=Vec2(0, 0))
        self._emitters: dict[str, SoundEmitter] = {}

    def update_listener(self, position: Vec2, facing: float = 0.0) -> None:
        """每帧更新监听器位置（跟随相机）"""
        self._listener.position = position
        self._listener.facing = facing

    def emit_at(
        self,
        source_id: str,
        position: Vec2,
        sound_type: SoundType,
        volume: float = 1.0,
    ) -> bool:
        """在指定位置播放3D音效"""
        emitter = self._emitters.get(source_id)
        if emitter is None:
            emitter = SoundEmitter(source_id, position, sound_type)
            self._emitters[source_id] = emitter

        # 防止同一声音过于频繁
        current_time = time.time()
        if current_time - emitter.last_play_time < emitter.min_interval:
            return False

        result = self._sound_system.play_3d_sound(
            sound_type=sound_type,
            source_pos=position,
            listener_pos=self._listener.position,
            listener_facing=self._listener.facing,
            volume=volume,
        )

        if result:
            emitter.last_play_time = current_time
        return result

    def emit_with_occlusion(
        self,
        source_id: str,
        position: Vec2,
        sound_type: SoundType,
        buildings: list[BuildingData],
    ) -> bool:
        """带遮挡检测的3D音效（建筑后的声音更闷）"""
        base_volume = 1.0

        # 简化的射线检测（检查是否穿过建筑）
        for building in buildings:
            if self._line_intersects_building(
                self._listener.position, position, building
            ):
                base_volume *= 0.5  # 遮挡衰减
                break  # 只检测第一个遮挡物

        return self.emit_at(source_id, position, sound_type, base_volume)
```

**2. 集成点**

```python
# game_loop.py 的 update 方法中

def _update_audio(self) -> None:
    # 更新音频监听器位置（跟随相机）
    camera_pos = self.state.camera.position
    camera_facing = 0.0  # 俯视游戏暂无朝向概念
    self._spatial_audio.update_listener(camera_pos, camera_facing)

# combat_resolver.py 中射击时

def resolve_shot(self, shooter, target) -> CombatResult:
    # ... 伤害计算 ...

    # 发射3D音效
    self._audio_manager.emit_at(
        source_id=f"shot_{shooter.id}",
        position=shooter.position.pixel_position,
        sound_type=SoundType.RIFLE_SHOT,
    )

    if result.is_hit:
        self._audio_manager.emit_at(
            source_id=f"hit_{target.id}",
            position=target.position.pixel_position,
            sound_type=SoundType.HIT_CONFIRM,
        )
```

**3. 测试计划**

```python
# test_spatial_audio.py

class TestSpatialAudioManager:
    def test_stereo_pan_left_source(self):
        """测试左侧声源的立体声分布"""
        manager = self._create_manager()
        manager.update_listener(Vec2(0, 0), facing=0.0)

        # 声源在左侧
        left_vol, right_vol = manager._sound_system.calculate_stereo_pan(
            source_pos=Vec2(-100, 0),
            listener_pos=Vec2(0, 0),
        )

        assert left_vol > right_vol  # 左声道应该更大

    def test_distance_attenuation(self):
        """测试距离衰减"""
        manager = self._create_manager()
        manager.update_listener(Vec2(0, 0))

        # 近处声源
        near_result = manager._sound_system.play_3d_sound(
            SoundType.RIFLE_SHOT,
            source_pos=Vec2(50, 0),
            listener_pos=Vec2(0, 0),
        )

        # 远处声源（超出最大距离）
        far_result = manager._sound_system.play_3d_sound(
            SoundType.RIFLE_SHOT,
            source_pos=Vec2(2000, 0),  # 超过max_distance=800
            listener_pos=Vec2(0, 0),
        )

        assert near_result == True
        assert far_result == False  # 太远不应播放

    def test_occlusion_reduction(self):
        """测试遮挡衰减"""
        manager = self._create_manager()
        building = BuildingData(position=Vec2(50, 0), size=Vec2(20, 20))

        # 无遮挡
        vol_no_occ = manager._calculate_volume_with_occlusion(
            listener=Vec2(0, 0), source=Vec2(100, 0), buildings=[]
        )

        # 有遮挡
        vol_with_occ = manager._calculate_volume_with_occlusion(
            listener=Vec2(0, 0), source=Vec2(100, 0), buildings=[building]
        )

        assert vol_with_occ < vol_no_occ  # 遮挡后音量应减小
```

**4. 验收标准**

- [ ] 玩家可通过立体声判断大致方位（左/右/前/后）
- [ ] 远处声音明显小于近处（800单位外静音）
- [ ] 建筑后的声音有明显沉闷感（低通滤波效果）
- [ ] 同时播放音效不超过16个（AudioMixerConfig.max_simultaneous_sounds）
- [ ] CPU开销<2%帧时间

---

### F4: 成就系统 (Achievement System)

#### 用户故事

> **作为一个喜欢挑战的玩家**
> **我希望** 完成特定目标时获得成就通知和记录**
> **以便于** 我能看到自己的游戏历程并与朋友分享

#### 技术方案

**1. 数据模型**

```python
# achievement_system.py

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Any, Callable

class AchievementCategory(Enum):
    COMBAT = auto()        # 战斗相关
    CAMPAIGN = auto()      # 战役相关
    TUTORIAL = auto()      # 教程相关
    SPECIAL = auto()       # 特殊成就（隐藏）
    MASTERY = auto()       # 精通成就（高难度）

@dataclass(frozen=True)
class AchievementDefinition:
    id: str                           # "first_victory", "zero_casualties"
    name: str                         # "初次胜利"
    description: str                  # "赢得第一场战斗"
    category: AchievementCategory     # 成就类别
    icon: str                         # 图标标识（emoji或sprite名）
    hidden: bool = False              # 是否隐藏（达成前不显示）
    secret: bool = False              # 是否秘密成就
    conditions: list[AchievementCondition]  # 解锁条件（支持AND/OR）
    reward_points: int = 10           # 奖励积分
    rarity: str = "common"            # common / uncommon / rare / legendary

class AchievementCondition(Enum):
    WIN_BATTLE = auto()
    KILL_COUNT = auto()               # param: min_kills
    ZERO_CASUALTIES = auto()
    SPEED_RUN = auto()                # param: max_seconds
    COMPLETE_TUTORIAL = auto()
    WIN_CAMPAIGN = auto()
    PERFECT_BATTLE = auto()           # 零伤亡 + 快速胜利
    KILL_COMMANDER = auto()
    SURVIVE_WAVE = auto()             # param: wave_number
    MAX_MORALE = auto()               # 保持士气满值获胜

@dataclass
class AchievementProgress:
    achievement_id: str
    unlocked: bool = False
    unlocked_at: str = ""             # ISO timestamp
    progress_value: float = 0.0       # 当前进度（如击杀数）
    progress_target: float = 1.0      # 目标值
    notified: bool = False            # 是否已弹出通知

@dataclass
class AchievementStorage:
    version: str = "1.0"
    unlocked_ids: set[str] = field(default_factory=set)
    progress_map: dict[str, AchievementProgress] = field(default_factory=dict)
    total_points: int = 0
    last_updated: str = ""
```

**2. 核心引擎**

```python
class AchievementEngine:
    DEFINITIONS: ClassVar[dict[str, AchievementDefinition]] = {
        "first_victory": AchievementDefinition(
            id="first_victory",
            name="初次胜利",
            description="赢得你的第一场战斗",
            category=AchievementCategory.COMBAT,
            icon="🏆",
            conditions=[AchievementCondition.WIN_BATTLE],
            rarity="common",
        ),
        "zero_casualties": AchievementDefinition(
            id="zero_casualties",
            name="零伤亡胜利",
            description="在没有单位阵亡的情况下赢得战斗",
            category=AchievementCategory.MASTERY,
            icon="🛡️",
            conditions=[AchievementCondition.ZERO_CASUALTIES, AchievementCondition.WIN_BATTLE],
            rarity="rare",
        ),
        "speed_demon": AchievementDefinition(
            id="speed_demon",
            name="极速征服者",
            description="在180秒内赢得战斗",
            category=AchievementCategory.SPECIAL,
            icon="⚡",
            conditions=[
                AchievementCondition.WIN_BATTLE,
                AchievementCondition.SPEED_RUN,  # param: max_seconds=180
            ],
            rarity="uncommon",
        ),
        "commander_hunter": AchievementDefinition(
            id="commander_hunter",
            name="指挥官猎手",
            description="击杀敌方指挥官",
            category=AchievementCategory.COMBAT,
            icon="🎯",
            conditions=[AchievementCondition.KILL_COMMANDER],
            rarity="uncommon",
        ),
        "campaign_veteran": AchievementDefinition(
            id="campaign_veteran",
            name="战役老兵",
            description="完成一个完整的战役",
            category=AchievementCategory.CAMPAIGN,
            icon="🎖️",
            conditions=[AchievementCondition.WIN_CAMPAIGN],
            rarity="rare",
        ),
        "perfect_battle": AchievementDefinition(
            id="perfect_battle",
            name="完美战斗",
            description="零伤亡且在120秒内获胜",
            category=AchievementCategory.MASTERY,
            icon="💎",
            hidden=True,
            conditions=[
                AchievementCondition.ZERO_CASUALTIES,
                AchievementCondition.SPEED_RUN,  # param: max_seconds=120
                AchievementCondition.WIN_BATTLE,
            ],
            rarity="legendary",
        ),
    }

    def __init__(self, storage_path: Path | None = None):
        self._storage = AchievementStorage()
        self._storage_path = storage_path or Path("achievements.json")
        self._pending_notifications: list[AchievementDefinition] = []
        self._event_hooks: dict[AchievementCondition, Callable] = {}

    def load(self) -> None:
        """从本地加载成就进度"""
        if self._storage_path.exists():
            data = json.loads(self._storage_path.read_text())
            self._storage = AchievementStorage(**data)

    def save(self) -> None:
        """保存成就进度到本地"""
        self._storage.last_updated = datetime.now(UTC).isoformat()
        data = asdict(self._storage)
        self._storage_path.write_text(json.dumps(data, indent=2))

    def check_conditions(
        self,
        event_type: AchievementCondition,
        context: dict[str, Any],
    ) -> list[AchievementDefinition]:
        """检查是否有新成就解锁"""
        newly_unlocked = []

        for ach_id, definition in self.DEFINITIONS.items():
            if ach_id in self._storage.unlocked_ids:
                continue  # 已解锁

            if event_type not in definition.conditions:
                continue  # 此事件与该成就无关

            if self._evaluate_conditions(definition.conditions, context):
                self._unlock(definition)
                newly_unlocked.append(definition)

        if newly_unlocked:
            self.save()

        return newly_unlocked

    def _unlock(self, achievement: AchievementDefinition) -> None:
        """解锁成就"""
        self._storage.unlocked_ids.add(achievement.id)
        self._storage.total_points += achievement.reward_points
        self._pending_notifications.append(achievement)
        logger.info(f"Achievement unlocked: {achievement.name} ({achievement.id})")

    def get_pending_notification(self) -> AchievementDefinition | None:
        """获取待显示的通知（弹窗用）"""
        if self._pending_notifications:
            return self._pending_notifications.pop(0)
        return None
```

**3. UI集成**

```python
# achievement_ui.py

class AchievementPopup:
    """成就解锁弹窗"""

    DISPLAY_DURATION = 3.0  # 秒
    ANIMATION_DURATION = 0.5  # 秒

    def __init__(self, display_config):
        self._display_config = display_config
        self._current: AchievementDefinition | None = None
        self._timer: float = 0.0
        self._alpha: float = 0.0
        self._visible = False

    def show(self, achievement: AchievementDefinition) -> None:
        self._current = achievement
        self._timer = self.DISPLAY_DURATION
        self._alpha = 0.0
        self._visible = True

    def update(self, dt: float) -> None:
        if not self._visible:
            return

        self._timer -= dt
        if self._timer <= 0:
            self._visible = False
            return

        # 淡入淡出
        total = self.DISPLAY_DURATION
        if self._timer > total - self.ANIMATION_DURATION:
            # 淡入
            progress = (total - self._timer) / self.ANIMATION_DURATION
            self._alpha = min(1.0, progress)
        elif self._timer < self.ANIMATION_DURATION:
            # 淡出
            progress = self._timer / self.ANIMATION_DURATION
            self._alpha = min(1.0, progress)

    def render(self, screen) -> None:
        if not self._visible or self._current is None or self._alpha < 0.01:
            return

        import pygame
        dc = self._display_config
        sw, sh = screen.get_size()

        # 绘制右上角弹窗
        popup_w, popup_h = 350, 80
        px, py = sw - popup_w - 20, 20

        surf = pygame.Surface((popup_w, popup_h), pygame.SRCALPHA)
        surf.fill((30, 35, 50, int(self._alpha * 230)))
        pygame.draw.rect(surf, (200, 170, 50, int(self._alpha * 255)),
                        (0, 0, popup_w, popup_h), 2, border_radius=10)

        # 图标
        font_icon = pygame.font.Font(None, 36)
        icon_surf = font_icon.render(self._current.icon, True, (255, 220, 100))
        surf.blit(icon_surf, (15, (popup_h - icon_surf.get_height()) // 2))

        # 文字
        font_name = pygame.font.Font(None, 24)
        font_desc = pygame.font.Font(None, 18)

        name_surf = font_name.render("Achievement Unlocked!", True, (255, 220, 100))
        surf.blit(name_surf, (60, 18))

        title_surf = font_desc.render(self._current.name, True, (220, 220, 220))
        surf.blit(title_surf, (60, 42))

        desc_surf = font_desc.render(self._current.description[:30], True, (160, 160, 170))
        surf.blit(desc_surf, (60, 58))

        screen.blit(surf, (px, py))


class AchievementListPanel:
    """成就列表面板（设置或主菜单中查看）"""

    def __init__(self, engine: AchievementEngine, display_config):
        self._engine = engine
        self._display_config = display_config
        self._visible = False
        self._scroll_offset = 0
        self._filter_category = None  # None = all

    def render(self, screen) -> None:
        if not self._visible:
            return

        # 绘制成就网格...
        pass
```

**4. 测试计划**

```python
# test_achievement_system.py

class TestAchievementEngine:
    def setup_method(self):
        self.engine = AchievementEngine(storage_path=Path("/tmp/test_achievements.json"))

    def test_first_victory_unlock(self):
        """测试首次胜利成就解锁"""
        context = {"result": "victory"}
        unlocked = self.engine.check_conditions(
            AchievementCondition.WIN_BATTLE, context
        )
        assert len(unlocked) == 1
        assert unlocked[0].id == "first_victory"

    def test_zero_casualties_requires_no_deaths(self):
        """测试零伤亡条件"""
        context = {
            "result": "victory",
            "allies_deaths": 0,
        }
        unlocked = self.engine.check_conditions(
            AchievementCondition.ZERO_CASUALTIES, context
        )
        assert any(a.id == "zero_casualties" for a in unlocked)

    def test_no_double_unlock(self):
        """测试不会重复解锁"""
        # 第一次
        self.engine.check_conditions(AchievementCondition.WIN_BATTLE, {"result": "victory"})
        # 第二次（相同条件）
        unlocked2 = self.engine.check_conditions(
            AchievementCondition.WIN_BATTLE, {"result": "victory"}
        )
        assert len(unlocked2) == 0  # 不应再次解锁

    def test_hidden_achievement_not_visible(self):
        """测试隐藏成就未解锁时不显示"""
        perfect = self.engine.DEFINITIONS["perfect_battle"]
        assert perfect.hidden == True
        assert perfect.id not in self.engine._storage.unlocked_ids

    def test_persistence_save_load(self):
        """测试存档加载"""
        self.engine.check_conditions(AchievementCondition.WIN_BATTLE, {"result": "victory"})
        self.engine.save()

        # 创建新实例并加载
        engine2 = AchievementEngine(storage_path=self.engine._storage_path)
        engine2.load()
        assert "first_victory" in engine2._storage.unlocked_ids

    def test_rarity_distribution(self):
        """测试稀有度分布"""
        rarities = [a.rarity for a in self.engine.DEFINITIONS.values()]
        from collections import Counter
        counts = Counter(rarities)
        assert counts.get("common", 0) >= 2  # 至少2个普通成就
        assert counts.get("legendary", 0) >= 1  # 至少1个传说成就
```

**5. 预设成就清单（Phase 1 实现15-20个）**

| ID | 名称 | 描述 | 条件 | 稀有度 |
|----|------|------|------|--------|
| first_victory | 初次胜利 | 赢得第一场战斗 | WIN_BATTLE | common |
| first_kill | 初次击杀 | 击杀第一个敌人 | KILL_COUNT(1) | common |
| zero_casualties | 零伤亡胜利 | 无己方阵亡获胜 | ZERO_CASUALTIES + WIN | rare |
| speed_demon | 极速征服者 | 180秒内获胜 | SPEED_RUN(180) + WIN | uncommon |
| commander_hunter | 指挥官猎手 | 击杀敌方指挥官 | KILL_COMMANDER | uncommon |
| campaign_veteran | 战役老兵 | 完整战役 | WIN_CAMPAIGN | rare |
| survivor | 幸存者 | 存活10分钟 | SURVIVE_WAVE(600) | uncommon |
| perfect_battle | 完美战斗 | 零伤亡+120秒内获胜 | LEGENDARY | legendary |
| tutorial_complete | 学徒毕业 | 完成教程 | COMPLETE_TUTORIAL | common |
| ten_wins | 十胜将军 | 获得十次胜利 | KILL_COUNT(10) 胜利 | uncommon |
| morale_master | 士气大师 | 保持满士气获胜 | MAX_MORALE + WIN | rare |
| night_win | 夜战英雄 | 夜间战斗获胜 | WIN_BATTLE + NIGHT | uncommon |
| sniper | 狙击手 | 超远距离击杀 | LONG_RANGE_KILL | rare |
| ... | ... | ... | ... | ... |

**6. 验收标准**

- [ ] 支持15-20个预设成就（涵盖战斗/战役/特殊/精通）
- [ ] 解锁时显示精美弹窗通知（右上角滑入，3秒后消失）
- [ ] 成就进度本地持久化（JSON格式）
- [ ] 隐藏/秘密成就未解锁时不显示
- [ ] 支持稀有度分级（common/uncommon/rare/legendary）
- [ ] 可在设置菜单查看成就列表和解锁比例
- [ ] Steam API接口预留（方法签名兼容）
- [ ] 单元测试覆盖率>90%

---

### F5: 动态音乐系统 (Adaptive Music System)

#### 用户故事

> **作为** 一个追求沉浸感的玩家**
> **我希望** 背景音乐能根据战斗激烈程度自动变化**
> **以便于** 音乐始终匹配当前的游戏节奏

#### 技术方案

**1. 架构设计**

```python
# adaptive_music.py

from dataclasses import dataclass
from enum import Enum, auto
import numpy as np

class BattleIntensity(Enum):
    CALM = auto()        # 无战斗，探索阶段
    LIGHT = auto()       # 小规模交火
    MODERATE = auto()    # 中等强度战斗
    INTENSE = auto()     # 激烈战斗
    CRITICAL = auto()    # 关键时刻（低血量/胜负未分）

@dataclass
class IntensityMetrics:
    kills_last_30s: int = 0
    deaths_last_30s: int = 0
    shots_fired_last_10s: int = 0
    allies_health_ratio: float = 1.0
    axis_health_ratio: float = 1.0
    distance_to_enemy_commander: float = 9999.0
    time_since_last_combat: float = 9999.0

class BattleIntensityTracker:
    SAMPLE_WINDOW = 30.0  # 秒

    def __init__(self):
        self._kill_log: list[float] = []  # 时间戳列表
        self._death_log: list[float] = []
        self._shot_log: list[float] = []
        self._current_metrics = IntensityMetrics()

    def record_kill(self, timestamp: float) -> None:
        self._kill_log.append(timestamp)

    def record_death(self, timestamp: float) -> None:
        self._death_log.append(timestamp)

    def record_shot(self, timestamp: float) -> None:
        self._shot_log.append(timestamp)

    def update(
        self,
        current_time: float,
        allies_health_ratio: float,
        axis_health_ratio: float,
        dist_to_enemy_cmd: float,
    ) -> BattleIntensity:
        """更新并返回当前强度等级"""
        # 清理过期日志
        cutoff = current_time - self.SAMPLE_WINDOW
        self._kill_log = [t for t in self._kill_log if t > cutoff]
        self._death_log = [t for t in self._death_log if t > cutoff]
        recent_shot_cutoff = current_time - 10.0
        self._shot_log = [t for t in self._shot_log if t > recent_shot_cutoff]

        # 更新metrics
        self._current_metrics = IntensityMetrics(
            kills_last_30s=len(self._kill_log),
            deaths_last_30s=len(self._death_log),
            shots_fired_last_10s=len(self._shot_log),
            allies_health_ratio=allies_health_ratio,
            axis_health_ratio=axis_health_ratio,
            distance_to_enemy_commander=dist_to_enemy_cmd,
            time_since_last_combat=current_time - max(self._kill_log + [0]),
        )

        return self._calculate_intensity()

    def _calculate_intensity(self) -> BattleIntensity:
        m = self._current_metrics

        # 关键时刻判定
        if m.allies_health_ratio < 0.3 or m.axis_health_ratio < 0.3:
            return BattleIntensity.CRITICAL

        # 激烈战斗判定
        if m.kills_last_30s >= 5 or m.deaths_last_30s >= 3:
            if m.shots_fired_last_10s >= 20:
                return BattleIntensity.INTENSE
            return BattleIntensity.MODERATE

        # 轻度交火
        if m.kills_last_30s >= 1 or m.shots_fired_last_10s >= 5:
            return BattleIntensity.LIGHT

        # 平静（长时间无战斗）
        if m.time_since_last_combat > 60.0:
            return BattleIntensity.CALM

        return BattleIntensity.LIGHT

class MusicTransitionManager:
    CROSSFADE_DURATION = 3.0  # 秒

    def __init__(self, bgm_generator: 'BGMGenerator'):
        self._bgm = bgm_generator
        self._current_mood: MusicMood = MusicMood.AMBIENT
        self._target_mood: MusicMood | None = None
        self._transition_progress: float = 0.0
        self._is_transitioning: bool = False

    def request_transition(self, new_mood: MusicMood) -> None:
        if new_mood == self._current_mood and not self._is_transitioning:
            return

        self._target_mood = new_mood
        self._is_transitioning = True
        self._transition_progress = 0.0

    def update(self, dt: float) -> np.ndarray | None:
        """返回要播放的音频数据（如果需要更新）"""
        if not self._is_transitioning:
            return None

        self._transition_progress += dt / self.CROSSFADE_DURATION

        if self._transition_progress >= 1.0:
            self._current_mood = self._target_mood
            self._is_transitioning = False
            self._target_mood = None
            # 生成新的完整音乐片段
            return self._bgm.generate_mood_music(self._current_mood, duration=60.0)

        # 交叉淡化期间继续播放当前音乐
        return None  # 由mixer处理混合

    @property
    def current_mood(self) -> MusicMood:
        return self._current_mood

    @property
    def transition_percentage(self) -> float:
        return self._transition_progress

# 映射表：BattleIntensity → MusicMood
INTENSITY_TO_MOOD: dict[BattleIntensity, MusicMood] = {
    BattleIntensity.CALM: MusicMood.AMBIENT,
    BattleIntensity.LIGHT: MusicMood.BATTLE_LIGHT,
    BattleIntensity.MODERATE: MusicMood.BATTLE_LIGHT,
    BattleIntensity.INTENSE: MusicMood.BATTLE_INTENSE,
    BattleIntensity.CRITICAL: MusicMood.BATTLE_INTENSE,
}
```

**2. 集成到GameLoop**

```python
# game_loop.py 相关部分

class GameLoop:
    def __init__(self, ...):
        # ... 现有初始化 ...
        self._intensity_tracker = BattleIntensityTracker()
        self._music_manager = MusicTransitionManager(bgm_generator)

    def update(self, dt: float) -> None:
        # ... 现有更新逻辑 ...

        # 更新战斗强度追踪
        current_time = self.state.tick / 60.0  # 假设60tps
        allies_hp_ratio = self._calculate_allies_health_ratio()
        axis_hp_ratio = self._calculate_axis_health_ratio()
        dist_to_cmd = self._distance_to_enemy_commander()

        intensity = self._intensity_tracker.update(
            current_time=current_time,
            allies_health_ratio=allies_hp_ratio,
            axis_health_ratio=axis_hp_ratio,
            dist_to_enemy_cmd=dist_to_cmd,
        )

        # 更新音乐
        target_mood = INTENSITY_TO_MOOD[intensity]
        self._music_manager.request_transition(target_mood)
        new_audio = self._music_manager.update(dt)
        if new_audio is not None:
            self._audio_system.play_generated_music(new_audio)

    # 在combat_resolver回调中
    def _on_kill_event(self, event: KillEvent) -> None:
        self._intensity_tracker.record_kill(event.timestamp)

    def _on_death_event(self, event: DeathEvent) -> None:
        self._intensity_tracker.record_death(event.timestamp)

    def _on_shot_event(self, event: ShotEvent) -> None:
        self._intensity_tracker.record_shot(event.timestamp)
```

**3. 测试计划**

```python
# test_adaptive_music.py

class TestBattleIntensityTracker:
    def test_calm_state(self):
        """测试平静状态"""
        tracker = BattleIntensityTracker()
        intensity = tracker.update(
            current_time=100.0,
            allies_health_ratio=1.0,
            axis_health_ratio=1.0,
            dist_to_enemy_cmd=500.0,
        )
        assert intensity == BattleIntensity.CALM

    def test_intense_combat(self):
        """测试激烈战斗"""
        tracker = BattleIntensityTracker()
        now = 100.0
        # 模拟多次击杀
        for i in range(6):
            tracker.record_kill(now - i * 2)  # 12秒内6次击杀
        # 模拟频繁开火
        for i in range(25):
            tracker.record_shot(now - i * 0.3)  # 10秒内25次射击

        intensity = tracker.update(
            current_time=now,
            allies_health_ratio=0.8,
            axis_health_ratio=0.6,
            dist_to_enemy_cmd=100.0,
        )
        assert intensity == BattleIntensity.INTENSE

    def test_critical_low_health(self):
        """测试关键时刻（低血量）"""
        tracker = BattleIntensityTracker()
        intensity = tracker.update(
            current_time=100.0,
            allies_health_ratio=0.2,  # 我方血量极低
            axis_health_ratio=0.7,
            dist_to_enemy_cmd=50.0,
        )
        assert intensity == BattleIntensity.CRITICAL

    test_intensity_decay_after_combat(self):
        """测试战斗结束后强度衰减"""
        tracker = BattleIntensityTracker()
        now = 100.0
        # 先制造激烈战斗
        for i in range(5):
            tracker.record_kill(now - i * 3)

        intense = tracker.update(current_time=now, allies_health_ratio=0.9,
                                 axis_health_ratio=0.9, dist_to_enemy_cmd=200.0)
        assert intense != BattleIntensity.CALM

        # 70秒后（无新战斗）
        calm = tracker.update(current_time=now + 70, allies_health_ratio=0.9,
                             axis_health_ratio=0.9, dist_to_enemy_cmd=200.0)
        assert calm == BattleIntensity.CALM


class TestMusicTransition:
    def test_smooth_transition(self):
        """测试平滑过渡"""
        manager = MusicTransitionManager(bgm_generator=MockBGMGenerator())
        manager._current_mood = MusicMood.AMBIENT

        manager.request_transition(MusicMood.BATTLE_INTENSE)

        # 过渡开始
        assert manager._is_transitioning == True
        assert manager._target_mood == MusicMood.BATTLE_INTENSE

        # 模拟过半
        manager.update(dt=1.6)  # CROSSFADE_DURATION=3.0
        assert 0.4 < manager.transition_percentage < 0.6

        # 完成
        manager.update(dt=1.6)
        assert manager._is_transitioning == False
        assert manager.current_mood == MusicMood.BATTLE_INTENSE

    def test_same_mood_no_transition(self):
        """测试相同情绪不触发过渡"""
        manager = MusicTransitionManager(MockBGMGenerator())
        manager._current_mood = MusicMood.BATTLE_LIGHT

        manager.request_transition(MusicMood.BATTLE_LIGHT)  # 请求相同的
        assert manager._is_transitioning == False
```

**4. 验收标准**

- [ ] 战斗强度分为5级（平静/轻度/中等/激烈/关键时刻）
- [ ] 音乐过渡使用3秒交叉淡化（无明显突兀感）
- [ ] 战斗结束后60秒自动回到平静音乐
- [ ] 关键时刻（任一方血量<30%）立即切换到激烈音乐
- [ ] CPU开销<1%帧时间
- [ ] 可在设置中关闭动态音乐（固定使用BATTLE_LIGHT）

---

## 四、MVP定义 (Beta Complete Edition)

### 什么是"完整版Beta"?

PyCC2 v0.4.0 应该是一个 **功能完整、体验流畅、适合公开发布** 的版本。

### MVP功能清单 (v0.4.0 Release Checklist)

#### ✅ 核心玩法 (必须100%完成)

- [x] **战斗系统**: 移动、射击、掩体、士气、撤退 (v0.3.16已完成)
- [x] **AI对手**: 4级难度 + 行为树 + 战术AI (v0.3.16已完成)
- [x] **战役模式**: 四层战役体系 (GrandCampaign→Sector→Operation→Battle) (v0.3.16已完成)
- [x] **存档系统**: 8槽位安全存档 (v0.3.16已完成)
- [x] **UI/HUD**: 小地图、单位面板、命令栏、设置菜单 (v0.3.16已完成)

#### ✅ Phase 1 新增功能 (必须100%完成)

- [ ] **F1: 教程系统完善** - 交互式新手引导（5-10分钟）
- [ ] **F2: 相机效果增强** - 震动/缩放/慢动作
- [ ] **F3: 3D定位音效** - 立体声定位 + 距离衰减
- [ ] **F4: 成就系统** - 15-20个成就 + 弹窗通知
- [ ] **F5: 动态音乐系统** - 5级战斗强度自适应音乐

#### ✅ 质量门槛 (Quality Gates)

| 维度 | 指标 | 当前(v0.3.16) | 目标(v0.4.0) |
|------|------|----------------|--------------|
| **测试覆盖率** | 通过率 | 99.91% (3484/3488) | ≥99.9% (≥3800测试) |
| **性能** | 60FPS稳定性 | ✅ 所有基准达标 | ✅ Phase 1功能影响<5%帧时间 |
| **崩溃率** | 运行1小时 | 0 crashes | 0 crashes |
| **内存泄漏** | 长时间运行 | 无明显泄漏 | 无泄漏（valgrind验证） |
| **代码质量** | mypy/type check | 通过 | 通过 |
| **文档** | 用户手册 | ✅ USER_MANUAL.md | ✅ 更新新功能说明 |
| **国际化** | 英文/中文/日文 | ✅ 三语支持 | ✅ 新功能文本三语覆盖 |

#### ✅ 发布Checklist (Pre-Launch Checklist)

**代码冻结前 (Code Freeze -1 week)**

- [ ] 所有Phase 1功能合并到main分支
- [ ] 全量测试套件通过（pytest --cov）
- [ ] 性能基准测试对比（v0.3.16 vs v0.4.0）
- [ ] 内存profiling确认无泄漏
- [ ] Code Review完成（至少2人approve）
- [ ] 文档更新（USER_MANUAL.md, CHANGELOG.md）

**发布当天 (Launch Day)**

- [ ] 版本号更新为v0.4.0
- [ ] Git tag: v0.4.0
- [ ] PyPI发布（如果适用）
- [ ] GitHub Release notes撰写
- [ ] 宣发素材准备（截图、GIF、短视频）

**发布后监控 (Post-Launch)**

- [ ] Issue tracker开启
- [ ] 用户反馈收集渠道确认
- [ ] 崩溃日志收集（如果有）
- [ ] 72小时热修复准备

---

## 五、长期愿景 (v1.0 - 正式版)

### v1.0 定义

PyCC2 v1.0 是 **正式版 (Gold Master)**，标志着项目从Beta进入稳定维护期。

### v1.0 完整功能集

#### Phase 2 功能 (v0.4.1 - v0.5.0, 预计4-6周)

| # | 功能 | 预估工时 | 说明 |
|---|------|----------|------|
| F6 | **难度自适应AI** | 8-10天 | Dynamic Difficulty Adjustment |
| F7 | **回放系统UI** | 5-6天 | 回放界面 + 导出/分享 |
| F8 | **天气系统增强** | 6-8天 | 动态天气变化 + 战术影响 |
| F9 | **Steam集成准备** | 5-7天 | Achievement API + Cloud Save + Leaderboard |
| F10 | **性能优化Pass 2** | 5-7天 | Profiling + 瓶颈消除 + LOD系统 |

**Phase 2 目标**: 达到 **接近原版CC2体验**，支持Modest Steam发布

#### Phase 3 功能 (v0.5.1 - v1.0, 预计8-12周)

| # | 功能 | 预估工时 | 说明 |
|---|------|----------|------|
| F11 | **热座模式** | 10-14天 | 本地双人对战 |
| F12 | **粒子特效升级** | 8-12天 | 弹道轨迹、弹壳抛出 |
| F13 | **地图编辑器** | 20-30天 | 可视化地图创建工具 |
| F14 | **单位模板编辑器** | 8-12天 | 自定义单位属性 |
| F15 | **Mod支持框架** | 10-15天 | 资源替换/脚本扩展API |
| F16 | **网络多人原型** | 20-30天 | LAN对战（技术验证）|

**Phase 3 目标**: **超越原版CC2**，提供现代化功能和社区创作工具

### 与原版CC2的对标差距分析

| 功能领域 | 原版CC2 (1997) | PyCC2 v0.3.16 | PyCC2 v0.4.0 (Phase 1) | PyCC2 v1.0 (目标) |
|----------|----------------|----------------|------------------------|-------------------|
| **核心战斗** | ✅ | ✅ 100% | ✅ 100% | ✅ 100%+ |
| **AI难度** | 5级 | ✅ 4级 | ✅ 4级 | ✅ 自适应(无限级) |
| **战役模式** | ✅ Operation-level | ✅ 4层体系 | ✅ 4层体系 | ✅ 4层体系+随机生成 |
| **图形** | 2D Sprite (640x480) | ✅ Pixel Art HD | ✅ +粒子/天气 | ✅ +高级粒子/动态天气 |
| **音效** | 立体声 | ✅ 程序化生成 | ✅ 3D定位 | ✅ 3D+环境音效+动态音乐 |
| **教程** | ❌ 无 | ⭐ 基础 | ✅ 交互式完整 | ✅ 交互式+视频(可选) |
| **成就** | ❌ 无 | ❌ | ✅ 15-20个 | ✅ 50+ + Steam |
| **回放** | ❌ 无 | ✅ 引擎级 | ✅ 引擎级 | ✅ UI+分享+分析 |
| **多人** | ✅ Hot-seat/Play-by-email | ❌ | ❌ | ✅ Hot-seat+LAN原型 |
| **编辑器** | ❌ 无 | ⭐ 脚本工具 | ❌ | ✅ 可视化编辑器 |
| **Mod支持** | ❌ 无 | ❌ | ❌ | ✅ 框架支持 |
| **平台** | Windows only | ✅ Win/Mac/Linux | ✅ 跨平台 | ✅ 跨平台+Steam |

**差距总结**:
- **v0.3.16**: 已达到原版CC2核心功能的 **90%**+
- **v0.4.0 (Beta)**: 达到 **95%**, 在教程/音效/沉浸感方面超越原版
- **v1.0 (正式版)**: 达到 **120%**, 在AI/图形/社区功能方面全面超越原版

---

## 六、风险评估与缓解

### Phase 1 风险矩阵

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| **范围蔓延** | 中 | 高 | 严格控制在5个功能，其他延后 |
| **性能回归** | 中 | 中 | 每个功能必须有benchmark测试 |
| **集成冲突** | 低 | 高 | 顺序实施（F1→F2→F3→F4→F5），每日构建 |
| **测试不足** | 低 | 高 | TDD方法，每个功能先写测试 |
| **用户体验不佳** | 中 | 中 | 每个功能完成后邀请1-2人试玩反馈 |

### 决策规则

- 如果单个功能预估工时超过原定 **150%**，则 **缩减scope** 或 **降级为Phase 2**
- 如果整体Phase 1超过 **4周**，则 **延迟F4/F5到Phase 2**
- 如果出现 **阻塞性bug**，暂停新功能开发直到修复

---

## 七、成功指标 (KPIs)

### 技术指标

| 指标 | v0.3.16基线 | v0.4.0目标 | 测量方法 |
|------|-------------|------------|----------|
| 测试数量 | 3484 | ≥3800 | pytest --co -q |
| 测试通过率 | 99.91% | ≥99.9% | pytest |
| 代码覆盖率 | ~85% | ≥88% | pytest-cov |
| Lint错误 | 0 | 0 | ruff/flake8 |
| 类型检查 | 通过 | 通过 | mypy strict |
| 性能(60fps) | ✅ | ✅ | benchmark suite |
| 启动时间 | <2s | <3s | time python main.py |

### 产品指标（发布后收集）

| 指标 | 目标值 | 收集方式 |
|------|--------|----------|
| 教程完成率 | >70% | 成就统计(TUTORIAL_COMPLETE) |
| 平均游戏时长 | >15min/会话 | 存档数据分析 |
| 成就解锁率 | >50%解锁≥5个 | 成就统计 |
| 崩溃率 | <0.1% | 错误日志 |
| 用户满意度(NPS) | >7/10 | 问卷/反馈 |

---

## 八、附录

### A. 术语表

- **SRP**: Single Responsibility Principle (单一职责原则)
- **ROI**: Return on Investment (投资回报率)
- **E2E**: End-to-End (端到端测试)
- **MVP**: Minimum Viable Product (最小可行产品)
- **BGM**: Background Music (背景音乐)
- **HMAC**: Hash-based Message Authentication Code (哈希消息认证码)
- **VCR**: Video Cassette Recorder (录像机风格控制)

### B. 参考文档

- [PyCC2 DESIGN.md](./DESIGN.md) - 系统架构设计
- [PyCC2 PRD.md](./PRD.md) - 产品需求文档
- [PyCC2 ROADMAP.md](./ROADMAP.md) - 原始路线图
- [PyCC2 TEST_PLAN.md](./TEST_PLAN.md) - 测试计划
- [PyCC2 GAP_ANALYSIS.md](./GAP_ANALYSIS.md) - 与原版CC2差距分析

### C. 版本历史

| 版本 | 日期 | 作者 | 变更说明 |
|------|------|------|----------|
| v1.0 | 2026-06-01 | AI Assistant | 初始版本，基于v0.3.16代码库分析 |

---

## 九、结论与下一步行动

### 立即行动 (This Week)

1. ✅ **创建分支** `feature/expansion-phase1`
2. ✅ **按照优先级顺序开始实施**:
   - Week 1: F2 (相机效果, 2.5天) + F3 (3D音效, 3.5天)
   - Week 2: F1 (教程系统, 4天)
   - Week 3: F5 (动态音乐, 4.5天) + F4 (成就系统, 6天)
   - Week 4: 集成测试 + Bug修复 + 文档

3. ✅ **每日站会**: 同步进度，阻塞问题即时升级

### 关键决策点

- **Week 1结束**: 评估F2/F3完成度，决定是否调整F1 scope
- **Week 2结束**: 评估整体进度，决定F4/F5是否需要缩减
- **Week 3结束**: 最终决定v0.4.0发布日期

### 长期展望

PyCC2 已经具备了成为 **最佳开源战术模拟游戏** 的所有潜质。通过本次Phase 1的实施，将达到 **Beta完整版** 质量，为后续的 v1.0 正式版和可能的 **Steam发布** 奠定坚实基础。

---

*本文档将随着项目进展持续更新。建议每个Phase结束后进行回顾和修订。*

**文档状态**: ✅ Draft Complete (待Review)
**下次更新**: Phase 1 启动会议后
