# Acceptance Tests

## 覆盖范围

当前 acceptance 测试覆盖 Phase A 的 7 个核心功能验收场景，共 37 个测试用例：

| 模块 | 测试类 | 覆盖点 |
|------|--------|--------|
| A1 Audio System | `TestA1AudioSystem` | 立体声初始化 / 单声道降级 / 优雅禁用 / 程序化音效生成 / 播放返回值 |
| A2 LOS System | `TestA2LOSSystem` | 清晰视线 / 地形阻挡 / 超出范围 / 高度优势 / Bresenham 算法 / 攻击线集成 |
| A3 Direction Sprite | `TestA3DirectionSprite` | 8 方向枚举 / 角度转换 / 往返转换 / 8 变体生成 |
| A5 Flank Damage | `TestA5FlankDamage` | 攻击角度枚举 / 正面 1x / 侧翼 1.5x / 后方 2x / 士气影响 |
| A6 Multi-Level Buildings | `TestA6MultiLevelBuildings` | 高度属性 / LOS 阻挡 / 移动成本 / 序列化 / 掩体加成 |
| A7 Campaign Persistence | `TestA7CampaignPersistence` | 战斗结果 / 战役进度聚合 / 存档加载 / 增援奖励 / 单位状态继承 |
| A8 Terrain Elevation | `TestA8TerrainElevation` | 高度支持 / 高度阻挡 / 移动成本 / 序列化 |
| Phase A Integration | `TestPhaseAIntegration` | 跨模块集成场景 |

## 与 E2E 用户旅程的关系

- **acceptance 层**：验证"功能是否满足需求"（功能点级别）
- **e2e 层**：验证"用户旅程是否通畅"（端到端流程，见 `tests/e2e/test_full_user_journey.py` 的 8 步完整流程）

两层互补，不重复覆盖。

## D13 N-4 评估 (2026-07-05)

D13 评估报告 N-4 评价"覆盖偏薄"。经复核：
- 37 个测试覆盖 7 个核心功能 + 1 个集成场景，覆盖密度合理
- 用户旅程已由 `tests/e2e/test_full_user_journey.py` 覆盖（4 个 E2E 测试）
- 不为扩充数量而扩充，遵循 Simplicity First 原则

**未来扩充方向**（当新功能加入时）：
- Phase B/C 功能验收（待对应需求实现后补充）
- 多人游戏模式验收（待实现）
- 模组系统验收（待实现）

## 运行方式

```bash
# 运行全部 acceptance 测试
pytest tests/acceptance/ -v

# 运行特定模块
pytest tests/acceptance/test_phase_a.py::TestA2LOSSystem -v
```
