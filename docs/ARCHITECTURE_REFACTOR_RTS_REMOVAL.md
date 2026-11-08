# PyCC2架构重构：删除RTS系统，回归CC2

**日期**: 2026-11-07  
**任务**: 清除RTS资源/建造系统，回归纯正Close Combat 2战术模拟器  
**优先级**: P0 - 架构级重构

---

## 📋 重构背景

### 问题诊断
PyCC2项目混合了两种不同的游戏机制：
1. ❌ **RTS机制**：资源采集、建筑建造、资源管理（类似星际争霸）
2. ✅ **CC2机制**：士气系统、掩体、地形、真实弹道、部署点数

### 重构目标
**删除所有RTS系统，回归纯正CC2战术模拟器**

---

## 🗑️ 待删除文件清单

### 1. RTS资源系统 (3个文件)

| 文件路径 | 功能 | 状态 |
|---------|------|------|
| `src/pycc2/domain/systems/resource_manager.py` | 资源管理器（金矿/木材） | ⏳ 待删除 |
| `src/pycc2/domain/systems/resource_collection_system.py` | 资源采集系统 | ⏳ 待删除 |
| `src/pycc2/presentation/ui/resource_bar_ui.py` | 资源UI显示条 | ⏳ 待删除 |

### 2. RTS建造系统 (2个文件)

| 文件路径 | 功能 | 状态 |
|---------|------|------|
| `src/pycc2/domain/systems/building_placement_system.py` | 建筑放置系统 | ⏳ 待删除 |
| `src/pycc2/presentation/ui/construction_menu_ui.py` | 建造菜单UI | ⏳ 待删除 |

### 3. RTS相关测试 (12个文件)

| 测试文件 | 测试内容 | 状态 |
|---------|---------|------|
| `tests/unit/test_sprint3_day11.py` | 建造系统测试（18测试） | ⏳ 待删除 |
| `tests/unit/test_sprint3_day12.py` | 建造集成测试（13测试） | ⏳ 待删除 |
| `test_sprint2_day8.py` | 资源系统测试 | ⏳ 待删除 |
| `tests/e2e/test_complete_game_loop_e2e.py` | RTS游戏循环E2E | ⏳ 需修改 |
| `tests/e2e/test_complete_game_loop_e2e_simplified.py` | 简化游戏循环 | ⏳ 需修改 |
| `tests/e2e/test_boundary_exception_e2e.py` | 边界测试（含资源） | ⏳ 需修改 |
| `tests/performance/test_performance_regression.py` | 性能测试（含资源） | ⏳ 需修改 |
| `scripts/profile_performance.py` | 性能分析脚本 | ⏳ 需修改 |

### 4. Sprint 2-4文档 (8个文件)

| 文档 | 内容 | 处理方式 |
|------|------|----------|
| `docs/SPRINT2_DAY8_SUMMARY.md` | 资源系统开发 | ⏳ 归档 |
| `docs/SPRINT3_DAY11_SUMMARY.md` | 建造系统开发 | ⏳ 归档 |
| `docs/SPRINT3_DAY12_SUMMARY.md` | 建造集成测试 | ⏳ 归档 |
| `docs/SPRINT4_DAY16_SUMMARY.md` | RTS游戏循环E2E | ⏳ 归档 |
| `docs/SPRINT2_4_PLAN.md` | Sprint 2-4规划 | ⏳ 归档 |
| `docs/SPRINT4_SUMMARY.md` | Sprint 4总结 | ⏳ 归档 |
| `docs/E2E_TESTING_GUIDE.md` | E2E测试指南 | ⏳ 归档 |
| `docs/PERFORMANCE_REPORT.md` | 性能报告 | ⏳ 归档 |

---

## ✅ 保留的CC2核心系统

### 1. 士气与心理系统 ✅
- `src/pycc2/domain/systems/morale_system.py`
- `src/pycc2/domain/systems/morale_calculator.py`
- `src/pycc2/domain/systems/morale_routing.py`
- `src/pycc2/domain/systems/psychology_system.py`

### 2. 部署系统 ✅
- `src/pycc2/services/deployment_manager.py`
- `src/pycc2/services/deployment_factory.py`
- `src/pycc2/domain/value_objects/deployment_types.py`
- `src/pycc2/presentation/ui/deployment_ui.py`

### 3. 战斗系统 ✅
- `src/pycc2/services/combat_service.py`
- `src/pycc2/services/combat_director.py`
- `src/pycc2/domain/systems/swiss_cheese_damage.py`
- `src/pycc2/domain/systems/ballistic.py`

### 4. 地形与掩体 ✅
- `src/pycc2/domain/value_objects/terrain_type.py`
- `src/pycc2/domain/systems/los_system.py`
- `src/pycc2/domain/ai/cover_seek_ai.py`

### 5. 战术AI ✅
- `src/pycc2/domain/ai/tactical_orchestrator.py`
- `src/pycc2/domain/ai/commander_ai.py`
- `src/pycc2/domain/ai/ambush_ai.py`
- `src/pycc2/domain/ai/engineer_assault.py`

### 6. 战役系统 ✅
- `src/pycc2/domain/systems/campaign_persistence.py`
- 战役数据（Eindhoven/Nijmegen/Arnhem）

---

## 🔍 依赖关系检查

### 需要检查的潜在依赖

1. **游戏循环**：是否依赖ResourceManager?
2. **UI系统**：HUD是否显示资源条？
3. **测试框架**：conftest.py是否初始化资源系统？
4. **关卡数据**：地图JSON是否包含资源点？

---

## 📝 重构执行计划

### Phase 1: 依赖关系分析 (10分钟)
1. 检查游戏循环对RTS系统的引用
2. 检查UI系统对资源显示的依赖
3. 检查测试fixture对RTS系统的依赖

### Phase 2: 删除生产代码 (5分钟)
1. 删除5个RTS系统文件
2. 删除相关UI组件
3. 更新import语句

### Phase 3: 清理测试代码 (10分钟)
1. 删除31个RTS相关测试（Sprint 3 Day 11-12）
2. 修改E2E测试（移除资源/建造部分）
3. 更新conftest.py

### Phase 4: 归档文档 (5分钟)
1. 创建`docs/_archive/RTS_REMOVAL/`目录
2. 移动Sprint 2-4文档到归档
3. 创建重构说明文档

### Phase 5: 验证CC2系统 (10分钟)
1. 运行现有CC2相关测试
2. 验证部署系统工作
3. 验证士气系统工作
4. 验证战斗系统工作

---

## 🎯 重构后的项目状态

### 预期改变

| 指标 | 重构前 | 重构后 | 变化 |
|------|--------|--------|------|
| **代码行数** | 210,133 | ~200,000 | -5% |
| **测试数量** | 181 | ~150 | -31个RTS测试 |
| **游戏类型** | 混合RTS/战术 | 纯战术模拟 | ✅ 明确 |
| **核心机制** | 资源采集+CC2 | 纯CC2部署 | ✅ 聚焦 |

### 技术债清理

| 技术债 | 状态 |
|--------|------|
| 游戏定位不清 | ✅ 解决 |
| RTS/CC2混合 | ✅ 移除RTS |
| 测试覆盖错位 | ✅ 重构测试 |

---

## ⚠️ 风险与缓解

### 风险1: 删除后的代码引用错误
**缓解**: 逐个文件检查import，使用IDE查找引用

### 风险2: E2E测试全部失败
**缓解**: 先注释测试，后续重写CC2风格的E2E

### 风险3: 主游戏循环崩溃
**缓解**: 先备份，然后逐步删除并测试

---

## ✅ 验收标准

### 必须满足
1. ✅ 所有RTS系统文件已删除
2. ✅ 所有RTS测试已删除/修改
3. ✅ 游戏可启动（无import错误）
4. ✅ CC2核心系统功能正常

### 可选
1. ⏳ 新的CC2风格E2E测试
2. ⏳ 用户文档更新（游戏手册）

---

## 📚 后续任务（重构后）

### Sprint 5规划建议

1. **P0: 补充CC2核心功能**
   - 胜利条件系统（占领目标点）
   - 战争迷雾完善
   - 单位自主AI增强

2. **P1: UI/UX提升**
   - 游戏设置菜单
   - CC2风格HUD
   - 战术地图

3. **P2: 用户文档**
   - 游戏手册
   - 单位图鉴
   - 战役攻略

---

**创建日期**: 2026-11-07  
**预计执行时间**: 40分钟  
**执行者**: AI Assistant  
**审核者**: 用户

---

**下一步**: 执行Phase 1依赖关系分析
