# TD-COV-BUG 修复方案

> **版本**: v0.6.8
> **创建日期**: 2026-07-12
> **执行人**: DevSquad (coder + tester)
> **状态**: ✅ 完成
> **关联**: [TECH_DEBT.md](TECH_DEBT.md) §七 TD-COV-BUG

---

## 一、背景

覆盖率提升过程中（commit 8dcdeb7），按 DevSquad Testing Iron Rules "失败即报告" 原则记录了 8 项源码 bug。本方案修复全部 8 项，修复过程中发现第 9 项（lighting_effects Vec2 不支持下标），一并修复。

## 二、修复方案

### 简单修复（4 项）

#### #3 game_loop_combat "EMPTY"→"OUT_OF_AMMO"

- **文件**: `src/pycc2/services/game_loop_combat.py` L117, L122
- **问题**: 检查 `weapon_state.name == "EMPTY"` 但 WeaponState 枚举成员为 READY/RELOADING/JAMMED/OUT_OF_AMMO，无 EMPTY
- **影响**: add_out_of_ammo popup 在生产中永不触发
- **修复**: `"EMPTY"` → `"OUT_OF_AMMO"`（2 处）

#### #6 combat_director Vec2 死代码

- **文件**: `src/pycc2/services/combat_director.py` L572
- **问题**: `Vec2(new_x, new_y)` 创建后未赋值
- **修复**: 删除该行

#### #7 hud_manager on_hold/on_dig_in 死代码

- **文件**: `src/pycc2/services/hud_manager.py` L184-202
- **问题**: on_hold 和 on_dig_in 定义但从未通过 register_callback() 注册，已被 on_defend 替代
- **修复**: 删除 on_hold 和 on_dig_in 函数定义

#### #8 combat_service "Front-Frontal" 笔误

- **文件**: `src/pycc2/services/combat_service.py` L282
- **问题**: FRONT_FLANK 返回 "Front-Frontal"（应为 "Front-Flank"）
- **修复**: `"Front-Frontal"` → `"Front-Flank"`

### 中等修复（3 项）

#### #1/#2 deployment_manager 阵营硬编码

- **文件**: `src/pycc2/services/deployment_manager.py`
- **问题**:
  - L316-317: `player_faction = Faction.ALLIES` / `ai_faction = Faction.AXIS` 硬编码
  - L607: `_pre_create_ai_units` 中 `ai_faction = Faction.AXIS` 硬编码
  - 若玩家选 axis 阵营，complete() 仍将玩家单位创建为 ALLIES
- **修复**:
  - 添加 `player_faction: str = "ally"` dataclass 字段
  - start() 中设置 `self.player_faction = faction`
  - complete() 中根据 `self.player_faction` 解析 player_faction 和 ai_faction
  - _pre_create_ai_units 根据 enemy_faction 解析 ai_faction

#### #4 turn_service 事件发布顺序

- **文件**: `src/pycc2/services/turn_service.py` L120-135
- **问题**: _advance_turn 在 `current_turn > max_turns` 时提前 return，导致最后一回合不发布 TurnEndedEvent
- **修复**: 将 TurnEndedEvent 发布移到 max_turns 检查之前
- **修复后逻辑**:
  1. current_turn += 1
  2. 调用 turn_end_callbacks
  3. publish TurnEndedEvent
  4. 如果超 max_turns → return（不发布 TurnStartedEvent）
  5. 推进 faction + publish TurnStartedEvent + 调用 turn_start_callbacks

### 复杂修复（1 项）

#### #5 combat_director deploy_smoke 参数错位

- **文件**: `src/pycc2/services/combat_director.py` L226-241
- **问题**: `AmmoInventory.deploy_smoke(unit, self._game_map)` 把 unit 当 self，game_map 当 position 元组
- **根因**: AmmoInventory.deploy_smoke 是实例方法，需要 AmmoInventory 实例；Unit 不持有 AmmoInventory
- **修复**: 改为检查 unit 是否有 ammo_inventory 属性，有则正确调用 `unit.ammo_inventory.deploy_smoke((x, y))`，无则跳过并 log warning
- **影响**: 当前功能靠 except 兜底，视觉烟雾效果仍生成；修复后不再尝试错误调用，行为更清晰

## 三、测试影响分析

修复源码后，部分测试断言（之前按错误行为断言）需要更新为断言正确行为：

| 修复项 | 受影响测试 | 更新内容 |
|--------|-----------|---------|
| #3 | test_game_loop_combat.py | OUT_OF_AMMO 弹药 popup 测试（之前用 Mock state.name="EMPTY"，改为 "OUT_OF_AMMO"） |
| #4 | test_turn_service.py | max_turns 最后一回合测试（之前断言不发布 TurnEndedEvent，改为断言发布） |
| #1/#2 | test_deployment_manager.py | 阵营相关测试（之前断言硬编码 ALLIES/AXIS，改为断言根据 faction 参数） |
| #5 | test_combat_director_extended.py | deploy_smoke 测试（之前断言错误调用，改为断言正确行为） |
| #6/#7/#8 | 无影响 | 死代码删除不影响测试 |

## 四、验证方法

```bash
# ruff
.venv/bin/ruff check src/pycc2/ tests/unit/

# 全量测试
.venv/bin/pytest tests/ -m "not slow" --tb=short

# 覆盖率（确保不回退）
.venv/bin/pytest tests/ -m "not slow" --cov=src/pycc2 --cov-report=term
```

**通过标准**: ruff 0 errors，pytest 0 failures，覆盖率 ≥ 70%

## 五、执行记录

### Phase 1: 创建方案文档
- **状态**: ✅ 完成

### Phase 2: 修复源码
（待执行）

### Phase 3: 更新测试断言
（待执行）

### Phase 4: 验证 + Git 推送
（待执行）
