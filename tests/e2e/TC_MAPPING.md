# E2E TC 映射表 (v0.9.0)

> **目的**: 建立 `E2E_REAL_USER_SCENARIOS.md` 的 TC 编号 ↔ 实际测试文件的映射，
> 便于评估真实用户场景覆盖率与识别缺口。
> **数据基准**: 2026-08-01，v0.9.0，基于重命名后的实际文件名。
> **状态图例**: ✅ 已实现 / ✅ 部分 (部分覆盖) / ❌ 未实现 / ⚠️ 已移除

---

## 场景一: 安装启动 (TC-001~007)

| TC | 描述 | 实现文件 | 状态 |
|----|------|----------|------|
| TC-001 | 新用户首次启动游戏 | test_vertical_slice.py (TestVerticalSlice01_InitChain) | ✅ 部分 |
| TC-002 | 依赖检查与兼容性验证 | - | ❌ 未实现 |
| TC-003 | 主菜单加载和显示 | test_vertical_slice.py / test_interactive_smoke.py | ✅ 部分 |
| TC-004 | 点击 New Campaign 进入战役选择 | test_campaign_ui_e2e.py | ✅ 部分 |
| TC-005 | 配置文件缺失降级处理 | - | ❌ 未实现 |
| TC-006 | 资源文件缺失错误提示 | - | ❌ 未实现 |
| TC-007 | 首次启动性能基准 | - | ❌ 未实现 (benchmark 层) |

---

## 场景二: 战役模式完整流程 (TC-008~019)

| TC | 描述 | 实现文件 | 状态 |
|----|------|----------|------|
| TC-008 | 选择 Operation Market Garden 战役 | test_campaign_flow_e2e.py (TestCampaignCreation) | ✅ |
| TC-009 | Day Briefing 简报信息 | test_campaign_flow_e2e.py / test_campaign_ui_e2e.py | ✅ 部分 |
| TC-010 | 选择第一场战斗任务 (地图加载) | test_campaign_flow_e2e.py (TestBattleMapResolution, TestMapLoading) | ✅ |
| TC-011 | 部署阶段拖放单位 | test_deployment_e2e.py / test_e2e_full_coverage.py | ✅ |
| TC-012 | 战斗执行移动射击循环 | test_combat_e2e.py / test_user_journey.py | ✅ |
| TC-013 | 胜利/失败判定机制 | test_combat_e2e.py (TestVictoryWhenAllEnemiesEliminated, TestDefeatWhenCommanderKilled) | ✅ |
| TC-014 | 战斗间单位继承 | test_ghost_module_integration_e2e.py / test_campaign_flow_e2e.py (TestBattleResultPersistence) | ✅ |
| TC-015 | 完整战役 Day 1 流程 | test_campaign_flow_e2e.py (TestCampaignDayCoverage) | ✅ 部分 |
| TC-016 | 补给线与空投系统 | test_game_settings_e2e.py (TestSupplyEffects*) | ✅ 部分 |
| TC-017 | 停火/撤退选项 | - | ❌ 未实现 (模块已于 v0.4.0 删除，待重新设计) |
| TC-018 | 战役全局进度追踪 | test_campaign_flow_e2e.py (TestCampaignStateInitialization, TestSectorStateTransitions) | ✅ 部分 |
| TC-019 | XXX Corps 推进速度评分 | - | ❌ 未实现 |

---

## 场景三: 单场战斗核心玩法 (TC-020~037)

| TC | 描述 | 实现文件 | 状态 |
|----|------|----------|------|
| TC-020 | 单位选择和信息查看 | test_e2e_full_coverage.py (test_11) / test_user_journey.py (TestUnitSelection) | ✅ |
| TC-021 | Z 快速移动命令 | test_e2e_full_coverage.py (test_26) / test_user_journey.py (TestSevenActions) | ✅ 部分 |
| TC-022 | X 潜行移动命令 | test_e2e_full_coverage.py (test_19 sneak) | ✅ 部分 |
| TC-023 | V 普通移动命令 | test_unit_movement.py | ✅ 部分 |
| TC-024 | S 开火/射击命令 | test_combat_e2e.py / test_e2e_full_coverage.py | ✅ |
| TC-025 | C 烟雾弹特殊命令 | test_ai_behaviors_e2e.py (TestSmokeSystem) | ✅ 部分 |
| TC-026 | D 防御姿态命令 | test_e2e_full_coverage.py (test_21 defend) | ✅ 部分 |
| TC-027 | H 隐蔽命令 | test_e2e_full_coverage.py (test_20 hide) | ✅ 部分 |
| TC-028 | Shift+右键命令队列 | - | ❌ 未实现 |
| TC-029 | 建筑物驻守 | - | ❌ 未实现 |
| TC-030 | 桥梁炸毁 (工兵) | - | ❌ 未实现 |
| TC-031 | 近战/肉搏战斗 | - | ❌ 未实现 |
| TC-032 | 弹药耗尽与 reload | test_ai_behaviors_e2e.py (TestAmmoPickup) | ✅ 部分 |
| TC-033 | 士气崩溃与投降 | test_combat_e2e.py (TestForceMoraleCollapseCausesRout) / test_ai_behaviors_e2e.py (TestSurrender) / test_ghost_module_integration_e2e.py | ✅ |
| TC-034 | 单位疲劳累积 | - | ❌ 未实现 |
| TC-035 | 多单位协同攻击 | test_combat_e2e.py | ✅ 部分 |
| TC-036 | 载具单位操作差异 | - | ❌ 未实现 |
| TC-037 | 战斗暂停与时间控制 | test_e2e_full_coverage.py (test_24) / test_vertical_slice.py (TestVerticalSlice06_PauseResume) | ✅ |

---

## 场景四: 视觉系统验证 (TC-038~052)

| TC | 描述 | 实现文件 | 状态 |
|----|------|----------|------|
| TC-038 | 12 种地形类型渲染 | test_visual_polish_e2e.py / test_visual_smoke.py | ✅ 部分 |
| TC-039 | 步兵 8 方向精灵 | test_e2e_full_coverage.py (test_40_all_8_directions) | ✅ |
| TC-040 | 战争迷雾 (FoW) 系统 | test_los_battlefield_e2e.py | ✅ 部分 |
| TC-041 | 昼夜循环光照效果 | test_visual_journey_e2e.py | ✅ 部分 |
| TC-042 | 天气效果-雨 | test_visual_journey_e2e.py | ✅ 部分 |
| TC-043 | 天气效果-雾 | test_los_battlefield_e2e.py | ✅ 部分 |
| TC-044 | 特效-爆炸动画 | test_visual_smoke.py | ✅ 部分 |
| TC-045 | 特效-烟雾效果 | test_visual_smoke.py / test_ai_behaviors_e2e.py (TestSmokeSystem) | ✅ 部分 |
| TC-046 | 特效-死亡/倒地动画 | - | ❌ 未实现 |
| TC-047 | 等距视角渲染 (Isometric) | - | ⚠️ 已移除 (v0.5.1 P2 清理) |
| TC-048 | 小地图 (Minimap) 渲染 | test_e2e_full_coverage.py (test_34) / test_visual_journey_e2e.py (TestV11MinimapTerrainJourney) | ✅ |
| TC-049 | HUD/底部面板信息显示 | test_e2e_full_coverage.py (test_18, test_37) | ✅ |
| TC-050 | 阴影渲染系统 | test_e2e_full_coverage.py (test_38_shadow_system) | ✅ 部分 |
| TC-051 | 视觉回归测试-关键画面 | test_visual_polish_e2e.py (V-07 基线) | ✅ |
| TC-052 | 高分辨率/Retina 屏适配 | test_visual_journey_e2e.py (TestV05ResponsiveLayoutJourney) | ✅ 部分 |

---

## 场景五: 存档系统 (TC-053~059)

| TC | 描述 | 实现文件 | 状态 |
|----|------|----------|------|
| TC-053 | 快速存档/读档 (F5/F9) | test_save_load_e2e.py / test_ghost_module_integration_e2e.py | ✅ |
| TC-054 | HMAC 签名验证防篡改 | test_save_security_e2e.py (TestSaveSecurityE2E, 显式 TC-054) | ✅ |
| TC-055 | 多存档槽位管理 | test_save_load_e2e.py | ✅ 部分 |
| TC-056 | 存档版本兼容性 | test_save_load_e2e.py | ✅ 部分 |
| TC-057 | 大型存档性能 | - | ❌ 未实现 (benchmark 层) |
| TC-058 | 并发存档安全性 | - | ❌ 未实现 |
| TC-059 | 存档路径安全 (目录遍历) | test_save_security_e2e.py (TestSaveSecurityE2E, 显式 TC-059) | ✅ |

---

## 场景六: 音频系统 (TC-060~068)

> 注: E2E_REAL_USER_SCENARIOS.md 中 TC-063 编号缺失，本表按原文档编号保留。

| TC | 描述 | 实现文件 | 状态 |
|----|------|----------|------|
| TC-060 | 武器音效播放 | test_audio_e2e.py | ✅ |
| TC-061 | 环境音效 (风/雨) | test_audio_e2e.py | ✅ |
| TC-062 | BGM 音乐切换 | test_audio_e2e.py | ✅ |
| TC-064 | 音频音量控制 | test_audio_e2e.py | ✅ 部分 |
| TC-065 | 音频设备热插拔 | - | ❌ 未实现 |
| TC-066 | 3D 立体声定位 | - | ❌ 未实现 |
| TC-067 | 语音命令系统 | - | ❌ 未实现 |
| TC-068 | 音频资源缺失降级 | test_audio_e2e.py | ✅ 部分 |

---

## 场景七: AI 对手行为 (TC-069~078)

| TC | 描述 | 实现文件 | 状态 |
|----|------|----------|------|
| TC-069 | AI 单位基本移动 | test_ai_integration_e2e.py / test_e2e_full_coverage.py (test_30) | ✅ |
| TC-070 | AI 战术行为-包抄 | test_ai_integration_e2e.py (FlankingAI 注册验证) | ✅ 部分 |
| TC-071 | AI 战术行为-压制射击 | test_ai_integration_e2e.py (SuppressionAI) | ✅ 部分 |
| TC-072 | AI VP 占领行为 | test_ai_integration_e2e.py (VictoryPointAI) | ✅ 部分 |
| TC-073 | AI 难度差异-Green | test_game_settings_e2e.py (TestGamePresetRecruit) | ✅ 部分 |
| TC-074 | AI 难度差异-Veteran | test_game_settings_e2e.py (TestGamePresetVeteran) | ✅ 部分 |
| TC-075 | AI 撤退逻辑 | test_ai_integration_e2e.py (RetreatDecisionAI) / test_ai_behaviors_e2e.py | ✅ 部分 |
| TC-076 | AI 协同作战 | test_ai_integration_e2e.py (InfantryTankCoordAI) | ✅ 部分 |
| TC-077 | AI 感知系统 | - | ❌ 未实现 |
| TC-078 | AI 单位多样性 | test_ai_behaviors_e2e.py | ✅ 部分 |

---

## 场景八: UI 交互 (TC-079~089)

| TC | 描述 | 实现文件 | 状态 |
|----|------|----------|------|
| TC-079 | 底部面板信息显示 | test_e2e_full_coverage.py (test_37) / test_ui_buttons_e2e.py | ✅ |
| TC-080 | 小地图导航 | test_e2e_full_coverage.py (test_34) | ✅ 部分 |
| TC-081 | 摄像机控制-缩放 | test_e2e_full_coverage.py (test_08/09) / test_vertical_slice.py (TestVerticalSlice05_Zoom) | ✅ |
| TC-082 | 摄像机控制-平移 | test_e2e_full_coverage.py (test_07) / test_vertical_slice.py (TestVerticalSlice04_CameraMovement) | ✅ |
| TC-083 | 教程系统引导 | test_tutorial_flow.py | ✅ |
| TC-084 | 快捷键提示显示 | test_e2e_full_coverage.py (keyboard shortcuts) | ✅ 部分 |
| TC-085 | 设置菜单功能 | test_game_settings_e2e.py | ✅ |
| TC-086 | 暂停菜单 (ESC) | test_e2e_full_coverage.py (test_25) | ✅ 部分 |
| TC-087 | 工具提示 (Tooltip) | test_e2e_full_coverage.py (test_35) | ✅ 部分 |
| TC-088 | 战斗日志/消息队列 | - | ❌ 未实现 |
| TC-089 | 径向菜单 (Radial Menu) | - | ❌ 未实现 |

---

## 覆盖率汇总

| 场景 | TC 总数 | ✅ 已实现 | ✅ 部分 | ❌ 未实现 | ⚠️ 已移除 |
|------|---------|-----------|---------|-----------|-----------|
| 一、安装启动 | 7 | 0 | 3 | 4 | 0 |
| 二、战役模式 | 12 | 4 | 5 | 3 | 0 |
| 三、单场战斗 | 18 | 3 | 7 | 8 | 0 |
| 四、视觉系统 | 15 | 3 | 8 | 3 | 1 |
| 五、存档系统 | 7 | 3 | 2 | 2 | 0 |
| 六、音频系统 | 8 | 3 | 1 | 4 | 0 |
| 七、AI 对手 | 10 | 1 | 8 | 1 | 0 |
| 八、UI 交互 | 11 | 3 | 5 | 3 | 0 |
| **合计** | **88** | **20** | **39** | **28** | **1** |

> **说明**: "✅ 部分" 表示该 TC 的核心场景已被相关测试文件部分覆盖，但未严格按
> E2E_REAL_USER_SCENARIOS.md 中的步骤逐条验证。后续版本可基于本表识别的 28 个 ❌ 未实现
> 缺口补充 E2E 用例，优先补齐 P0 级别的 TC-002/TC-005/TC-028/TC-077 等。
