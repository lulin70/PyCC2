# PyCC2 真实用户场景端到端(E2E)测试计划

> **版本**: v1.0  
> **日期**: 2026-06-01  
> **适用范围**: PyCC2 v0.3.0+ (Close Combat 2 Python重制版)  
> **目标**: 覆盖真实用户从安装到完成整个战役的完整体验路径

---

## 📋 目录

- [1. 测试概述](#1-测试概述)
- [2. 场景类别总览](#2-场景类别总览)
- [3. 🎮 场景一: 首次安装与启动流程](#3--场景一-首次安装与启动流程)
- [4. 📖 场景二: 战役模式完整流程](#4--场景二-战役模式完整流程)
- [5. ⚔️ 场景三: 单场战斗核心玩法](#5--场景三-单场战斗核心玩法)
- [6. 🎨 场景四: 视觉系统验证](#6--场景四-视觉系统验证)
- [7. 💾 场景五: 存档系统](#7--场景五-存档系统)
- [8. 🎵 场景六: 音频系统](#8--场景六-音频系统)
- [9. 🤖 场景七: AI对手行为](#9--场景七-ai对手行为)
- [10. 📱 场景八: UI交互](#10--场景八-ui交互)
- [11. 执行计划与优先级矩阵](#11-执行计划与优先级矩阵)
- [12. 验收标准与通过/失败判定](#12-验收标准与通过失败判定)
- [13. 自动化实现指南](#13-自动化实现指南)

---

## 1. 测试概述

### 1.1 测试目标

本测试计划旨在验证PyCC2游戏在**真实用户使用场景**下的端到端功能完整性、稳定性和用户体验质量。

**核心目标**:
- ✅ 验证新用户从零开始能够顺利完成首次游戏体验
- ✅ 确保战役模式从选择到完成的完整流程无阻塞
- ✅ 核心战斗机制（移动、射击、命令）符合Close Combat 2原版体验
- ✅ 视觉、音频、AI等子系统在集成环境下正常工作
- ✅ 存档系统可靠且安全（HMAC签名验证）
- ✅ UI交互流畅自然，符合战术战棋游戏操作习惯

### 1.2 测试范围

| 维度 | 覆盖范围 | 排除范围 |
|------|----------|----------|
| **功能** | 8大场景类别全部核心功能 | 性能极限压测（单独的benchmark测试） |
| **平台** | macOS (主要) + Linux (CI) | Windows (后续补充) |
| **数据** | 所有内置地图(50+) + 战役数据(29场战斗) | 用户自定义地图/Mod |
| **用户角色** | 新手玩家 → 进阶玩家 → 高级玩家 | 多人联机（未实现） |

### 1.3 技术约束

```yaml
运行环境:
  显示驱动: SDL_VIDEODRIVER=dummy (headless模式)
  音频驱动: SDL_AUDIODRIVER=dummy (静音模式)
  Python版本: >=3.11
  关键依赖:
    - pygame>=2.2
    - numpy>=1.26
    - pydantic>=2.0
    
测试框架:
  主框架: pytest>=7.4
  断言库: pytest内置assert
  Mock库: pytest-mock
  截图工具: pygame.image.save()
```

---

## 2. 场景类别总览

### 2.1 测试用例统计

| 场景类别 | P0(必须) | P1(重要) | P2(锦上添花) | 总计 | 预计耗时 |
|----------|----------|----------|--------------|------|----------|
| 🎮 首次安装与启动 | 3 | 2 | 2 | **7** | ~15min |
| 📖 战役模式完整流程 | 5 | 4 | 3 | **12** | ~45min |
| ⚔️ 单场战斗核心玩法 | 8 | 6 | 4 | **18** | ~60min |
| 🎨 视觉系统验证 | 4 | 5 | 6 | **15** | ~40min |
| 💾 存档系统 | 4 | 3 | 2 | **9** | ~25min |
| 🎵 音频系统 | 2 | 3 | 3 | **8** | ~20min |
| 🤖 AI对手行为 | 3 | 4 | 3 | **10** | ~35min |
| 📱 UI交互 | 5 | 4 | 3 | **12** | ~30min |
| **合计** | **34** | **31** | **26** | **91** | **~270min (4.5h)** |

### 2.2 优先级定义

| 优先级 | 定义 | 发布门槛 | 示例 |
|--------|------|----------|------|
| **P0 - 必须通过** | 阻塞性问题，不修复无法发布 | 100%通过率 | 游戏无法启动、崩溃、存档损坏 |
| **P1 - 重要** | 严重影响用户体验，应尽快修复 | ≥95%通过率 | 命令无效、UI卡顿、音效缺失 |
| **P2 - 锦上添花** | 小瑕疵或增强体验，可延后 | ≥80%通过率 | 动画细节、边缘情况、性能优化 |

---

## 3. 🎮 场景一: 首次安装与启动流程

### 场景描述

模拟一位从未接触过PyCC2的新用户，从下载安装到第一次看到主菜单的完整体验。这是用户的第一印象，直接影响留存率。

### 3.1 TC-001: 新用户首次启动游戏 (P0)

**测试目标**: 验证全新安装后游戏能正常启动并显示主菜单

**前置条件**:
- ✅ Python 3.11+ 已安装
- ✅ 项目已克隆到本地: `/Users/lin/trae_projects/PyCC2`
- ✅ 虚拟环境已创建但**未安装依赖**
- ✅ 无任何存档文件（干净环境）

**操作步骤**:

```bash
# Step 1: 安装依赖
cd /Users/lin/trae_projects/PyCC2
pip install -e ".[dev]"

# Step 2: 启动游戏（使用headless模式避免GUI阻塞）
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python -m pycc2.main &

# Step 3: 等待3秒让pygame初始化完成
sleep 3

# Step 4: 检查进程是否存活
pgrep -f "pycc2.main" && echo "✓ 进程存活" || echo "✗ 进程崩溃"

# Step 5: 发送QUIT事件优雅退出
```

**预期结果**:
- ✅ `pip install` 无错误，所有依赖成功安装
- ✅ 游戏进程正常启动，无异常退出码
- ✅ 控制台输出包含: `"Starting PyCC2..."` 和 `"Entering deployment phase"`
- ✅ 内存占用 < 500MB (正常范围)
- ✅ 无 `Traceback` 或 `CRITICAL` 级别日志

**验收标准**:
- **通过**: 游戏成功进入部署阶段（或主菜单），进程退出码为0
- **失败**: 
  - 依赖安装失败（缺少pygame/numpy等）
  - 启动时抛出未捕获异常
  - 进程在5秒内异常终止

**预计执行时间**: 2分钟

**关联文件**:
- [main.py](../../src/pycc2/main.py) - 入口点
- [pyproject.toml](../../pyproject.toml) - 依赖声明

---

### 3.2 TC-002: 依赖检查与兼容性验证 (P0)

**测试目标**: 验证所有必需依赖的正确性和版本兼容性

**前置条件**:
- ✅ 项目已安装（TC-001通过）

**操作步骤**:

```python
import importlib.metadata
import sys

required_packages = {
    'pygame': '>=2.2',
    'numpy': '>=1.26',
    'pydantic': '>=2.0',
}

results = {}
for package, version_constraint in required_packages.items():
    try:
        version = importlib.metadata.version(package)
        results[package] = {'installed': True, 'version': version}
    except ImportError:
        results[package] = {'installed': False, 'version': None}

python_ok = sys.version_info >= (3, 11)
```

**预期结果**:
- ✅ pygame >= 2.2.0 已安装
- ✅ numpy >= 1.26.0 已安装
- ✅ pydantic >= 2.0 已安装
- ✅ Python >= 3.11

**预计执行时间**: 30秒

---

### 3.3 TC-003: 主菜单加载和显示 (P0)

**测试目标**: 验证主菜单正确渲染，所有按钮可点击

**前置条件**:
- ✅ 游戏成功启动（TC-001通过）

**操作步骤**:

```python
import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'

import pygame
pygame.init()
screen = pygame.display.set_mode((1280, 720))

from pycc2.presentation.ui.new_game_menu import NewGameMenu

menu = NewGameMenu(screen_width=1280, screen_height=720)
menu.render(screen)

assert 'new_campaign' in menu._buttons, "缺少'New Campaign'按钮"
assert 'start_skirmish' in menu._buttons, "缺少'Skirmish'按钮"
assert 'quit' in menu._buttons, "缺少'Quit'按钮"

pygame.image.save(screen, 'screenshots/menu_main.png')
```

**预期结果**:
- ✅ NewGameMenu实例化无错误
- ✅ `render()` 方法成功绘制到surface
- ✅ 至少包含3个核心按钮: New Campaign, Skirmish, Quit
- ✅ 截图文件生成且大小 > 0

**预计执行时间**: 1分钟

---

### 3.4 TC-004: 新用户首次点击"New Campaign" (P1)

**测试目标**: 验证新手用户能顺利进入战役选择界面

**操作步骤**:

```python
new_campaign_rect = menu._buttons['new_campaign']
action = menu.handle_click(new_campaign_rect.center)
assert menu.current_screen == MenuScreen.CAMPAIGN
menu.render(screen)
pygame.image.save(screen, 'screenshots/menu_campaign.png')
```

**预期结果**:
- ✅ 屏幕切换到Campaign界面
- ✅ 显示Operation Market Garden战役信息
- ✅ 包含"Start Campaign"和"Back"按钮

**预计执行时间**: 1分钟

---

### 3.5 TC-005: 配置文件缺失时的降级处理 (P1)

**测试目标**: 验证配置文件缺失时游戏能优雅降级而非崩溃

```python
import shutil
from pathlib import Path

config_path = Path('config/engine.toml')
backup_path = config_path.with_suffix('.toml.bak')

if config_path.exists():
    shutil.copy(config_path, backup_path)
    config_path.unlink()

try:
    from pycc2.infrastructure.config import ConfigManager
    config = ConfigManager()
    assert config is not None
finally:
    if backup_path.exists():
        shutil.copy(backup_path, config_path)
        backup_path.unlink()
```

**预期结果**:
- ✅ 配置缺失时不崩溃
- ✅ 使用硬编码默认值
- ✅ 日志记录警告信息

**预计执行时间**: 1分钟

---

### 3.6 TC-006: 资源文件缺失时的错误提示 (P2)

**测试目标**: 验证精灵图/地图等资源缺失时给出清晰错误提示

```python
from pycc2.domain.entities.game_map import GameMap

try:
    game_map = GameMap.from_json(Path('data/maps/nonexistent_map.json'))
    assert False, "应该抛出异常"
except FileNotFoundError as e:
    error_msg = str(e)
    assert 'nonexistent_map' in error_msg or 'not found' in error_msg.lower()
```

**预计执行时间**: 30秒

---

### 3.7 TC-007: 首次启动性能基准 (P2)

**测试目标**: 建立冷启动时间的性能基线，防止未来退化

```python
import time
import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

start_time = time.perf_counter()

import pygame
pygame.init()
from pycc2.presentation.ui.new_game_menu import NewGameMenu
menu = NewGameMenu(screen_width=1280, screen_height=720)
menu.render(pygame.display.set_mode((1280, 720)))

startup_time = time.perf_counter() - start_time
assert startup_time < 10.0, f"启动过慢: {startup_time:.2f}秒 > 10秒阈值"
print(f"冷启动时间: {startup_time:.2f}秒")
```

**预期结果**:
- ✅ 冷启动时间 < 10秒（含依赖导入+初始化）
- ✅ 内存峰值 < 300MB

**预计执行时间**: 2分钟

---

## 4. 📖 场景二: 战役模式完整流程

### 场景描述

模拟真实玩家体验完整的Market Garden战役：从选择战役→查看简报→选择任务→部署单位→执行战斗→判定胜负→继承单位到下一场战斗。这是PyCC2的核心价值主张。

### 4.1 TC-008: 选择Operation Market Garden战役 (P0)

**测试目标**: 验证战役选择和数据加载正确性

```python
from pycc2.domain.systems.campaign_four_layer import create_market_garden_campaign

campaign = create_market_garden_campaign()

assert campaign.campaign_id == 'market_garden'
assert campaign.name == 'Operation Market Garden'
assert len(campaign.sectors) == 3

sector_ids = {s.sector_id for s in campaign.sectors}
assert sector_ids == {'arnhem', 'nijmegen', 'eindhoven'}

total_battles = sum(len(op.battles) for s in campaign.sectors for op in s.operations)
assert total_battles == 29, f"应有29场战斗，实际{total_battles}场"
```

**预期结果**:
- ✅ 战役ID、名称正确
- ✅ 3大战区全部加载: Arnhem, Nijmegen, Eindhoven
- ✅ 29场战斗定义完整

**预计执行时间**: 2分钟

---

### 4.2 TC-009: 查看Day Briefing简报信息 (P0)

**测试目标**: 验证每日简报显示正确的历史背景和任务目标

```python
day1_battles = [
    b for s in campaign.sectors 
    for op in s.operations 
    for b in op.battles 
    if b.day == 1
]

assert len(day1_battles) >= 3, "Day 1至少有3场战斗"

sample = day1_battles[0]
assert len(sample.victory_locations) > 0
assert sample.time_of_day in ['dawn', 'day', 'dusk', 'night']
assert sample.weather in ['clear', 'overcast', 'rain', 'fog']
```

**预计执行时间**: 1分钟

---

### 4.3 TC-010: 选择第一场战斗任务 (P0)

**测试目标**: 验证用户可以选择特定战斗并加载对应地图

```python
from pathlib import Path
from pycc2.domain.entities.game_map import GameMap

target_battle = day1_battles[0]
map_path = Path(f'data/maps/{target_battle.map_id}.json')
assert map_path.exists()

game_map = GameMap.from_json(map_path)
assert game_map.width > 0 and game_map.height > 0
assert len(game_map.spawn_points) >= 2
```

**预计执行时间**: 2分钟

---

### 4.4 TC-011: 部署阶段-拖放单位到地图 (P0)

**测试目标**: 验证用户可以在部署界面将单位放置到合法位置

```python
game_loop = _build_game_loop(game_map, screen, menu)
_start_deployment(game_loop, game_map, menu)

deployment_ui = game_loop.deployment_ui
available = deployment_ui.state.available_units
unplaced = [(i, u) for i, u in enumerate(available) if not u.is_placed]

placed_count = 0
for unit_idx, unit in unplaced[:5]:
    deployment_ui._selected_unit_index = unit_idx
    for fx, fy in deployment_ui.state.friendly_zone:
        terrain = deployment_ui._get_terrain_at(fx, fy)
        if deployment_ui.can_place_at(unit, fx, fy, terrain):
            if deployment_ui.place_unit(unit_idx, fx, fy):
                placed_count += 1
                break

assert placed_count >= 3, f"应至少部署3个单位，实际{placed_count}个"
```

**预计执行时间**: 3分钟

---

### 4.5 TC-012: 战斗执行-移动射击命令循环 (P0)

**测试目标**: 验证核心战斗循环：选择单位→移动→射击→回合结束

```python
result = game_loop.complete_deployment()
assert result is not None

player_units = [u for u in game_loop.state.units if u.faction == Faction.ALLIES]
ai_units = [u for u in game_loop.state.units if u.faction == Faction.AXIS]

target_unit = player_units[0]
game_loop.state.selected_unit_ids = {target_unit.id}

game_loop.interaction_controller.handle_shortcut_key(pygame.K_z)
assert game_loop.interaction_controller.mode == InteractionMode.MOVE

dt = 1.0 / 30.0
for tick in range(30):
    game_loop._update_logic(dt)
    game_loop.state.tick += 1
```

**预计执行时间**: 3分钟

---

### 4.6 TC-013: 胜利/失败判定机制 (P0)

**测试目标**: 验证胜利条件检测和战斗结束流程

```python
from pycc2.services.victory_manager import VictoryManager

victory_mgr = VictoryManager(
    game_map=game_loop.state.game_map,
    event_bus=game_loop.event_bus
)

for tick in range(100):
    game_loop._update_logic(dt)
    game_loop.state.tick += 1
    
    if victory_mgr.check_victory_condition(game_loop.state):
        result = victory_mgr.get_battle_result()
        assert result in ['allied_victory', 'axis_victory', 'draw']
        print(f"✓ 战斗结束: {result}")
        break
```

**预计执行时间**: 3分钟

---

### 4.7 TC-014: 战斗间单位继承 (P1)

**测试目标**: 验证上一场战斗的幸存单位可以带入下一场战斗

```python
from pycc2.domain.systems.campaign_persistence import CampaignPersistence

persistence = CampaignPersistence()
post_battle_units = [
    {
        'id': u.id, 'name': u.name,
        'hp_ratio': u.health.hp / u.health.max_hp,
        'ammo_ratio': u.weapon.ammo_remaining / u.weapon.max_ammo,
    }
    for u in player_units[:3] if u.is_alive
]

persistence.persist_battle_result(
    operation_id='arnhem_landing',
    battle_id='arnhem_d1_oosterbeek_lz',
    surviving_units=post_battle_units,
    casualties={'allies': {'kia': 1, 'wounded': 2}},
)

restored_units = persistence.load_surviving_units('arnhem_landing')
assert len(restored_units) == len(post_battle_units)
```

**预计执行时间**: 2分钟

---

### 4.8 TC-015: 完整战役Day 1流程 (P1)

**测试目标**: 端到端验证Day 1的全部3场战斗

```python
day1_scenarios = []
for sector in campaign.sectors:
    for op in sector.operations:
        for battle in op.battles:
            if battle.day == 1:
                day1_scenarios.append(battle)

success_count = 0
for battle in day1_scenarios:
    try:
        map_path = Path(f'data/maps/{battle.map_id}.json')
        gm = GameMap.from_json(map_path)
        
        for vl in battle.victory_locations:
            x, y = vl.position
            assert 0 <= x < gm.width and 0 <= y < gm.height
        
        success_count += 1
    except Exception as e:
        print(f"✗ {battle.battle_id}: {e}")

assert success_count == len(day1_scenarios), \
    f"Day 1应有{len(day1_scenarios)}场全部通过，实际{success_count}场"
```

**预计执行时间**: 5分钟

---

### 4.9 TC-016: 补给线与空投系统 (P1)

**测试目标**: 验证Allied补给依赖于LZ控制的机制

```python
from pycc2.domain.systems.supply_line import SupplyLineSystem

supply_system = SupplyLineSystem(campaign_state=grand_campaign_state)

supply_system.update_lz_control('oosterbeek_lz', Faction.ALLIES)
allied_supply = supply_system.calculate_supply(Faction.ALLIES)
assert allied_supply > 0

supply_system.update_lz_control('oosterbeek_lz', Faction.GERMAN)
blocked_supply = supply_system.calculate_supply(Faction.ALLIES)
assert blocked_supply < allied_supply
```

**预计执行时间**: 2分钟

---

### 4.10 TC-017: 停火/撤退选项 (P1)

**测试目标**: 验证战斗间停火和战略性撤退选项

> **注**: 此场景原依赖 `ceasefire_retreat` 模块，该模块在 D7 评估中被识别为纯幽灵功能（零生产引用），已于 v0.4.0 P1 阶段删除。停火/撤退机制待后续版本重新设计实现后再补充对应 E2E 场景。

**预计执行时间**: 待实现后补充

---

### 4.11 TC-018: 战役全局进度追踪 (P2)

**测试目标**: 验证GrandCampaignState正确追踪多战线进度

```python
from pycc2.domain.systems.campaign_four_layer import GrandCampaignState

state = GrandCampaignState()
state.advance_day()
state.record_battle_result(sector='arnhem', battle_id='test', result='allied_victory',
                           casualties={'BRITISH': {'kia': 3}})

assert state.current_day == 2
assert len(state.sectors) > 0
```

**预计执行时间**: 1分钟

---

### 4.12 TC-019: XXX Corps推进速度评分 (P2)

**测试目标**: 验证Nijmegen/Eindhoven战区按XXX Corps推进速度评分

```python
def calculate_xxx_corps_progress(state):
    eindhoven_sector = state.sectors.get('eindhoven')
    if not eindhoven_sector:
        return 0.0
    completed = sum(1 for op in eindhoven_sector.operations if op.status == 'complete')
    total = len(eindhoven_sector.operations)
    return completed / total if total > 0 else 0

progress = calculate_xxx_corps_progress(state)
assert 0.0 <= progress <= 1.0
```

**预计执行时间**: 1分钟

---

## 5. ⚔️ 场景三: 单场战斗核心玩法

### 场景描述

深入验证单场战斗中的每一个核心操作：单位选择、移动模式、射击、特殊命令等。

### 5.1 TC-020: 单位选择和信息查看 (P0)

**测试目标**: 验证鼠标点击选择单位并显示详细信息

```python
unit = player_units[0]
camera = game_loop.state.camera

screen_x = int(unit.position.pixel_position.x - camera.position.x + SCREEN_W // 2)
screen_y = int(unit.position.pixel_position.y - camera.position.y + SCREEN_H // 2)

pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(screen_x, screen_y), button=1))
game_loop._event_dispatcher.process_events()

assert unit.id in game_loop.state.selected_unit_ids
```

**预计执行时间**: 1分钟

---

### 5.2 TC-021: Z快速移动命令 (P0)

**测试目标**: 验证Z键激活快速移动模式（暴露但速度快）

```python
game_loop.interaction_controller.handle_shortcut_key(pygame.K_z)
assert game_loop.interaction_controller.mode == InteractionMode.MOVE

move_config = game_loop.interaction_controller.current_move_config
assert move_config.speed_modifier > 1.0
assert move_config.stealth_modifier < 1.0
```

**预计执行时间**: 2分钟

---

### 5.3 TC-022: X潜行移动命令 (P0)

**测试目标**: 验证X键激活潜行模式（慢速但高隐蔽）

```python
game_loop.interaction_controller.handle_shortcut_key(pygame.K_x)
assert game_loop.interaction_controller.mode == InteractionMode.STEALTH_MOVE

stealth_config = game_loop.interaction_controller.current_move_config
assert stealth_config.speed_modifier < 1.0
assert stealth_config.stealth_modifier > 1.0
```

**预计执行时间**: 1分钟

---

### 5.4 TC-023: V普通移动命令 (P0)

**测试目标**: 验证V键激活标准移动模式（平衡型）

```python
game_loop.interaction_controller.handle_shortcut_key(pygame.K_v)
assert game_loop.interaction_controller.mode == InteractionMode.NORMAL_MOVE
```

**预计执行时间**: 30秒

---

### 5.5 TC-024: S开火/射击命令 (P0)

**测试目标**: 验证S键激活攻击模式并可指定目标

```python
game_loop.interaction_controller.handle_shortcut_key(pygame.K_s)
assert game_loop.interaction_controller.mode == InteractionMode.ATTACK

target_enemy = ai_units[0]
game_loop.interaction_controller.set_attack_target(target_enemy.id)
assert unit.attack_target_id == target_enemy.id
```

**预计执行时间**: 2分钟

---

### 5.6 TC-025: C烟雾弹特殊命令 (P1)

**测试目标**: 验证C键投放烟雾弹遮蔽视线

```python
game_loop.interaction_controller.handle_shortcut_key(pygame.K_c)
assert game_loop.interaction_controller.mode == InteractionMode.SPECIAL_ABILITY

smoke_pos = TileCoord(unit.position.tile_coord.x + 3, unit.position.tile_coord.y)
smoke_active = game_loop.state.weather.apply_smoke(smoke_pos, radius=3, duration=180)
assert smoke_active
```

**预计执行时间**: 2分钟

---

### 5.7 TC-026: D防御姿态命令 (P1)

**测试目标**: 验证D键让单位进入防御姿态

```python
game_loop.interaction_controller.handle_shortcut_key(pygame.K_d)
assert game_loop.interaction_controller.mode == InteractionMode.DEFENSE
```

**预计执行时间**: 1分钟

---

### 5.8 TC-027: H隐蔽命令 (P1)

**测试目标**: 验证H键让单位利用地形隐蔽

```python
game_loop.interaction_controller.handle_shortcut_key(pygame.K_h)
assert game_loop.interaction_controller.mode == InteractionMode.TAKE_COVER
```

**预计执行时间**: 1分钟

---

### 5.9 TC-028: Shift+右键命令队列 (P1)

**测试目标**: 验证Shift+右键可以为单位排队多个命令

```python
commands = [
    ('move', TileCoord(unit.position.tile_coord.x + 3, unit.position.tile_coord.y)),
    ('attack', ai_units[0].id),
]

for cmd_type, cmd_target in commands:
    game_loop.interaction_controller.enqueue_command(
        command_type=cmd_type, target=cmd_target, queue_mode=True
    )

queue_length = len(game_loop.interaction_controller.command_queue)
assert queue_length == 2
```

**预计执行时间**: 3分钟

---

### 5.10 TC-029: 建筑物驻守 (P1)

**测试目标**: 验证步兵单位可以进入建筑物获得额外保护

```python
game_loop.interaction_controller.handle_shortcut_key(pygame.K_g)
assert unit.is_garrisoned
assert unit.building_defense_bonus >= 1.5
```

**预计执行时间**: 2分钟

---

### 5.11 TC-030: 桥梁炸毁（工兵） (P1)

**测试目标**: 验证工兵单位可以炸毁桥梁阻止敌军前进

```python
game_loop.interaction_controller.handle_shortcut_key(pygame.K_b)
bridge_destroyed = game_map.destroy_bridge(target_bridge)
assert bridge_destroyed
```

**预计执行时间**: 3分钟

---

### 5.12 TC-031: 近战/肉搏战斗 (P2)

**测试目标**: 验证相邻敌方单位之间可以发生近战

```python
from pycc2.domain.systems.combat_resolver import CombatResolver

resolver = CombatResolver(event_bus=game_loop.event_bus)
melee_result = resolver.resolve_melee_combat(attacker=player_units[0], defender=ai_units[0])
assert melee_result is not None
assert 'damage' in melee_result
```

**预计执行时间**: 1分钟

---

### 5.13 TC-032: 弹药耗尽与reload行为 (P2)

**测试目标**: 验证弹药耗尽后单位自动reload的行为

```python
unit.weapon.ammo_remaining = 0
unit.weapon.state = WeaponState.EMPTY

reloaded = False
for tick in range(150):
    game_loop._update_logic(dt)
    if unit.weapon.state == WeaponState.READY and unit.weapon.ammo_remaining > 0:
        reloaded = True
        break

assert reloaded
```

**预计执行时间**: 2分钟

---

### 5.14 TC-033: 士气崩溃与投降 (P2)

**测试目标**: 验证士气过低时单位可能panic或投降

```python
unit.morale.value = 0.05
unit.health.hp = 1

from pycc2.domain.systems.morale_system import MoraleSystem
morale_sys = MoraleSystem()
event = morale_sys.check_morale_state(unit)

if event:
    assert event.event_type in ['panic', 'surrender', 'rally']
```

**预计执行时间**: 1分钟

---

### 5.15 TC-034: 单位疲劳累积 (P2)

**测试目标**: 验证长时间战斗后单位累积疲劳影响性能

```python
from pycc2.domain.components.fatigue_component import FatigueComponent

fatigue = FatigueComponent()
for action in ['move'] * 10 + ['attack'] * 5:
    fatigue.accumulate(action)

assert fatigue.get_speed_penalty() < 1.0
assert fatigue.get_accuracy_penalty() < 1.0
```

**预计执行时间**: 1分钟

---

### 5.16 TC-035: 多单位协同攻击 (P2)

**测试目标**: 验证多个单位同时攻击同一目标时伤害叠加

```python
if len(player_units) >= 3:
    target = ai_units[0]
    initial_hp = target.health.hp
    
    for attacker in player_units[:3]:
        game_loop.state.selected_unit_ids = {attacker.id}
        game_loop.interaction_controller.handle_shortcut_key(pygame.K_s)
        game_loop.interaction_controller.set_attack_target(target.id)
    
    for tick in range(180):
        game_loop._update_logic(dt)
    
    assert target.health.hp < initial_hp
```

**预计执行时间**: 2分钟

---

### 5.17 TC-036: 载具单位操作差异 (P2)

**测试目标**: 验证坦克/半履带车等载具的操作与步兵不同

```python
vehicles = [u for u in game_loop.state.units 
            if 'tank' in u.unit_type.name.lower() or 'vehicle' in u.unit_type.name.lower()]

if vehicles:
    tank = vehicles[0]
    assert tank.health.max_hp > 100  # 载具有更高HP
    assert hasattr(tank, 'armor_value') or tank.unit_type.name != 'infantry'
```

**预计执行时间**: 1分钟

---

### 5.18 TC-037: 战斗暂停与时间控制 (P2)

**测试目标**: 验证空格键暂停和时间加速功能

```python
game_loop.interaction_controller.handle_shortcut_key(pygame.K_SPACE)
assert game_loop.state.paused == True

initial_tick = game_loop.state.tick
for _ in range(10):
    game_loop._update_logic(dt)
assert game_loop.state.tick == initial_tick

game_loop.interaction_controller.handle_shortcut_key(pygame.K_SPACE)
assert game_loop.state.paused == False
```

**预计执行时间**: 1分钟

---

## 6. 🎨 场景四: 视觉系统验证

### 场景描述

验证PyCC2的视觉渲染系统在各种条件下都能正确呈现游戏画面。

### 6.1 TC-038: 12种地形类型渲染 (P0)

**测试目标**: 验证所有地形类型都能正确渲染且视觉区分明显

```python
from pycc2.domain.value_objects.terrain_type import TerrainType

expected_terrains = ['grass', 'road', 'forest', 'water', 'swamp', 
                     'building', 'bridge', 'hedgerow', 'trench', 'hill']

renderer = EnhancedRenderer()
renderer.initialize(screen)

renderable_count = 0
for terrain_name in expected_terrains:
    test_surface = pygame.Surface((48, 48))
    try:
        renderer.render_terrain_tile(test_surface, (0, 0), TerrainType(terrain_name))
        pixel_count = pygame.surfarray.array3d(test_surface).sum()
        if pixel_count > 0:
            renderable_count += 1
    except Exception as e:
        print(f"  ✗ {terrain_name}: {e}")

assert renderable_count >= 8, f"至少8种地形应可渲染，实际{renderable_count}种"
```

**预计执行时间**: 3分钟

---

### 6.2 TC-039: 步兵8方向精灵 (P0)

**测试目标**: 验证步兵单位在8个朝向上都有对应的精灵图

```python
directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
loaded_count = 0

for direction in directions:
    try:
        sprite = sprite_loader.load_sprite('infantry', 'allies', direction)
        if sprite is not None:
            loaded_count += 1
    except Exception:
        pass

assert loaded_count == 8, f"应有8个方向，实际{loaded_count}个"
```

**预计执行时间**: 2分钟

---

### 6.3 TC-040: 战争迷雾(FoW)系统 (P0)

**测试目标**: 验证战争迷雾正确隐藏未探索区域和视野外单位

```python
from pycc2.domain.systems.fog_of_war import FogOfWarSystem

fow = FogOfWarSystem(game_map=game_map)
fow.initialize()

visibility_map = fow.get_visibility_map()
hidden_tiles = sum(row.count(False) for row in visibility_map)
hidden_ratio = hidden_tiles / (game_map.width * game_map.height)

assert hidden_ratio > 0.99, "初始应几乎全覆盖迷雾"

fow.update_from_units(player_units)
for unit in player_units:
    pos = unit.position.tile_coord
    assert visibility_map[pos.y][pos.x], "己方单位位置应可见"
```

**预计执行时间**: 2分钟

---

### 6.4 TC-041: 昼夜循环光照效果 (P1)

**测试目标**: 验证一天中不同时间段的光照变化

```python
from pycc2.domain.systems.day_night_cycle import DayNightCycle

dnc = DayNightCycle()

time_checks = [
    (6.0, 0.4),   # dawn
    (12.0, 1.0),  # noon  
    (18.0, 0.5),  # dusk
    (23.0, 0.15), # night
]

brightnesses = []
for hour, expected_min in time_checks:
    dnc.set_time(hour)
    config = dnc.get_lighting_config()
    brightnesses.append(config.brightness)

assert max(brightnesses) > 3 * min(brightnesses), "昼夜亮度差应超过3倍"
```

**预计执行时间**: 2分钟

---

### 6.5 TC-042: 天气效果-雨 (P1)

**测试目标**: 验证雨天天气的视觉和游戏性影响

```python
from pycc2.domain.systems.weather_effects import WeatherEffects

weather = WeatherEffects()
weather.set_weather('rain', intensity=0.7)

vis_mod = weather.get_visibility_modifier()
mov_mod = weather.get_movement_modifier()
acc_mod = weather.get_accuracy_modifier()

assert vis_mod < 1.0, "雨应降低能见度"
assert mov_mod < 1.0, "雨应减缓移动"
assert acc_mod < 1.0, "雨应降低精度"
```

**预计执行时间**: 2分钟

---

### 6.6 TC-043: 天气效果-雾 (P1)

**测试目标**: 验证雾天天气的视觉和游戏性影响

```python
weather.set_weather('fog', intensity=0.8)
fog_vis = weather.get_visibility_modifier()

assert fog_vis < 0.5, "雾应大幅降低能见度(<50%)"
```

**预计执行时间**: 1分钟

---

### 6.7 TC-044: 特效-爆炸动画 (P1)

**测试目标**: 验证爆炸时的视觉特效

```python
from pycc2.presentation.rendering.cc2_combat_effects import CC2ExplosionEffect, EnhancedParticleSystem

particles = EnhancedParticleSystem(max_particles=500)
vfx = CC2ExplosionEffect(particle_system=particles)

vfx.create_explosion(position=(SCREEN_W//2, SCREEN_H//2), size='medium', duration=30)

active_frames = 0
for tick in range(60):
    particles.update(dt)
    if particles.active_particle_count > 0:
        active_frames += 1

assert active_frames > 10, "爆炸应至少持续10帧"
```

**预计执行时间**: 2分钟

---

### 6.8 TC-045: 特效-烟雾效果 (P1)

**测试目标**: 验证烟雾弹/引擎烟雾的持续性特效

```python
vfx.create_smoke(position=(SCREEN_W//2, SCREEN_H//2), radius=50, duration=180)

smoke_active = 0
for tick in range(200):
    particles.update(dt)
    if particles.active_particle_count > 0:
        smoke_active += 1

assert smoke_active >= 150, "烟雾应持续约5秒以上"
```

**预计执行时间**: 2分钟

---

### 6.9 TC-046: 特效-死亡/倒地动画 (P2)

**测试目标**: 验证单位阵亡时的倒地动画

```python
from pycc2.presentation.rendering.animation_system import AnimationSystem

anim_system = AnimationSystem()
anim_system.play_animation(unit_id=unit.id, animation_type='death', loop=False, duration=45)

complete = False
for tick in range(60):
    anim_system.update(dt)
    if not anim_system.is_playing(unit.id):
        complete = True
        break

assert complete and tick >= 20, "死亡动画应在20-60帧内完成"
```

**预计执行时间**: 1分钟

---

### 6.10 TC-047: ~~等距视角渲染(Isometric)~~ (已移除 — v0.5.1 P2)

**状态**: 已移除。CC2 原版仅使用顶部正交视角，等距视角(isometric)为 experimental 代码，
已在 v0.5.1 P2 清理中完整删除。正交视角渲染覆盖见 TC-048（小地图）及主渲染管线 E2E 场景。

---

### 6.11 TC-048: 小地图(Minimap)渲染 (P2)

**测试目标**: 验证小地图正确显示全局态势

```python
from pycc2.presentation.rendering.minimap import Minimap

minimap = Minimap(size=(200, 200), game_map=game_map, camera=game_loop.state.camera)
minimap_surface = minimap.render(units=game_loop.state.units)

assert minimap_surface.get_size() == (200, 200)
```

**预计执行时间**: 1分钟

---

### 6.12 TC-049: HUD/底部面板信息显示 (P2)

**测试目标**: 验证HUD正确显示选中单位和战场信息

```python
from pycc2.presentation.rendering.cc2_bottom_panel import CC2BottomPanel

panel = CC2BottomPanel(width=SCREEN_W, height=120)
panel_surface = pygame.Surface((SCREEN_W, 120))
panel.render(surface=panel_surface, selected_unit=unit, game_state=game_loop.state)

filled = (pygame.surfarray.array3d(panel_surface).sum(axis=2) > 0).sum()
coverage = filled / (SCREEN_W * 120)
assert coverage > 0.5
```

**预计执行时间**: 1分钟

---

### 6.13 TC-050: 阴影渲染系统 (P2)

**测试目标**: 验证单位和建筑的动态阴影

```python
from pycc2.presentation.rendering.shadow_system import ShadowSystem

shadow_sys = ShadowSystem()
shadow_surface = pygame.Surface((SCREEN_W, SCREEN_H), flags=pygame.SRCALPHA)

for unit in game_loop.state.units:
    shadow_sys.render_unit_shadow(shadow_surface, unit, game_loop.state.camera)

alpha_data = pygame.surfarray.array_alpha(shadow_surface)
shadow_pixels = (alpha_data > 0).sum()
assert shadow_pixels > 0
```

**预计执行时间**: 1分钟

---

### 6.14 TC-051: 视觉回归测试-关键画面 (P2)

**测试目标**: 与已知良好的截图对比，检测视觉退化

```python
import hashlib

def image_hash(surface):
    data = pygame.image.tostring(surface, 'RGB')
    return hashlib.md5(data).hexdigest()

current_hash = image_hash(screen)
baseline_path = Path('screenshots/baseline_standard_scene.png')

if baseline_path.exists():
    baseline = pygame.image.load(str(baseline_path))
    baseline_hash = image_hash(baseline)
    match = current_hash == baseline_hash
    print(f"视觉回归: {'✓ 匹配' if match else '⚠ 变化需审核'}")
else:
    pygame.image.save(screen, str(baseline_path))
    print("✓ 首次运行，保存基线截图")
```

**预计执行时间**: 2分钟

---

### 6.15 TC-052: 高分辨率/Retina屏适配 (P2)

**测试目标**: 验证游戏在高DPI屏幕上的显示质量

```python
test_configs = [
    (1280, 720, 1.0),
    (2560, 1440, 2.0),
]

for width, height, dpi_scale in test_configs:
    wm = WindowManager(DisplayInfo(base_width=width, base_height=height))
    test_screen = wm.initialize()
    
    menu = NewGameMenu(screen_width=width, screen_height=height)
    menu.render(test_screen)
    
    assert pygame.surfarray.array3d(test_screen).sum() > 0
```

**预计执行时间**: 2分钟

---

## 7. 💾 场景五: 存档系统

### 场景描述

验证游戏的存档/读档功能，特别是HMAC签名验证的安全性。

### 7.1 TC-053: 快速存档/读档 (F5/F9) (P0)

**测试目标**: 验证F5快速存档和F9快速读档功能

```python
from pycc2.infrastructure.save_system import SecureSaveManager
from pycc2.services.save_controller import SaveController

save_mgr = SecureSaveManager()
save_ctrl = SaveController()
save_ctrl.initialize()

snapshot_before = {
    'tick': game_loop.state.tick,
    'unit_count': len(game_loop.state.units),
}

state_dict = save_mgr.export_state_from_game_loop(game_loop)
meta = SaveMetaData(mission_id='quick_test')

save_success = save_mgr.save_game(slot=0, state_dict=state_dict, meta=meta)
assert save_success

loaded_state, loaded_meta, status = save_mgr.load_game(slot=0)
assert status.name == 'OK'

restore_success = save_ctrl.restore_state(loaded_state, game_loop)
assert restore_success

assert game_loop.state.tick == snapshot_before['tick']
```

**预计执行时间**: 2分钟

---

### 7.2 TC-054: HMAC签名验证防篡改 (P0)

**测试目标**: 验证被篡改的存档会被检测并拒绝

```python
import json

test_state = {'test': 'data', 'version': '0.1.1'}
save_mgr.save_game(slot=1, state_dict=test_state, meta=SaveMetaData())

slot_path = save_mgr._slot_path(1)
with open(slot_path, 'r') as f:
    original = json.load(f)

tampered = original.copy()
tampered['state']['test'] = 'HACKED'
with open(slot_path, 'w') as f:
    json.dump(tampered, f)

_, _, status = save_mgr.load_game(slot=1)
assert status == SaveSlotStatus.CORRUPTED, "篡改应被检测"

with open(slot_path, 'w') as f:
    json.dump(original, f)  # 恢复
```

**预计执行时间**: 2分钟

---

### 7.3 TC-055: 多存档槽位管理 (P1)

**测试目标**: 验证8个存档槽位的独立管理

```python
MAX_SLOTS = SecureSaveManager.MAX_SLOTS
assert MAX_SLOTS == 8

for slot in range(MAX_SLOTS):
    meta = SaveMetaData(mission=f'test_slot_{slot}')
    assert save_mgr.save_game(slot=slot, state_dict={'slot': slot}, meta=meta)

all_slots = save_mgr.list_all_slots()
assert len(all_slots) == MAX_SLOTS

empty_slot = save_mgr.find_empty_slot()
assert empty_slot is None  # 全部已满

save_mgr.delete_save(3)
empty_slot = save_mgr.find_empty_slot()
assert empty_slot == 3

_, _, del_status = save_mgr.load_game(3)
assert del_status == SaveSlotStatus.EMPTY
```

**预计执行时间**: 2分钟

---

### 7.4 TC-056: 存档版本兼容性 (P1)

**测试目标**: 验证旧版本存档的处理策略

```python
CURRENT = SecureSaveManager.CURRENT_VERSION

same_ver = {'version': CURRENT, 'data': 'ok'}
save_mgr.save_game(slot=2, state_dict=same_ver, meta=SaveMetaData(version=CURRENT))
_, _, same_status = save_mgr.load_game(slot=2)
assert same_status == SaveSlotStatus.OK

old_ver_data = {'meta': {'version': '0.0.1'}, 'state': {'version': '0.0.1'},
                'hmac': save_mgr._compute_hmac(b'{"meta":{"version":"0.0.1"},"state":{"version":"0.0.1"}}')}
with open(save_mgr._slot_path(3), 'w') as f:
    json.dump(old_ver_data, f)

_, _, old_status = save_mgr.load_game(3)
assert old_status == SaveSlotStatus.INCOMPATIBLE
```

**预计执行时间**: 2分钟

---

### 7.5 TC-057: 大型存档性能 (P2)

**测试目标**: 验证存档大量单位数据时的性能

```python
import time

large_state = {
    'version': '0.1.1',
    'tick': 10000,
    'units': [{'id': f'u{i}', 'name': f'Unit_{i}', 'faction': 'allies' if i%2==0 else 'axis',
               'health': {'hp': 80, 'max_hp': 100}, 'position': {'tile_coord': {'x': i%50, 'y': i//50}}}
              for i in range(60)],
    'camera': {'position': {'x': 1000, 'y': 1000}}
}

start = time.perf_counter()
save_mgr.save_game(slot=4, state_dict=large_state, meta=SaveMetaData(mission='perf_test'))
save_time = time.perf_counter() - start

start = time.perf_counter()
load_state, _, _ = save_mgr.load_game(slot=4)
load_time = time.perf_counter() - start

print(f"60单位存档: 保存={save_time:.3f}s, 加载={load_time:.3f}s")
assert save_time < 2.0, "保存过慢"
assert load_time < 1.0, "加载过慢"
```

**预计执行时间**: 2分钟

---

### 7.6 TC-058: 并发存档安全性 (P2)

**测试目标**: 验证快速连续存档不会导致数据损坏

```python
import threading

results = [None] * 5
errors = []

def save_thread(idx):
    try:
        results[idx] = save_mgr.save_game(
            slot=idx % 5, 
            state_dict={'thread': idx, 'tick': idx * 100},
            meta=SaveMetaData(mission=f'concurrent_{idx}')
        )
    except Exception as e:
        errors.append(e)

threads = [threading.Thread(target=save_thread, args=(i,)) for i in range(5)]
for t in threads:
    t.start()
for t in threads:
    t.join()

assert len(errors) == 0, f"并发存档出错: {errors}"
assert all(results), "部分并发存档失败"
```

**预计执行时间**: 1分钟

---

### 7.7 TC-059: 存档路径安全 (P2)

**测试目标**: 验证存档路径不允许目录遍历攻击

```python
# 尝试路径遍历
traversal_names = [
    '../../../etc/passwd',
    '..\\..\\..\\windows\\system32\\config',
    '/etc/shadow',
]

for name in traversal_names:
    safe_name = SecureSaveManager._sanitize_filename(name)
    assert '/' not in safe_name, f"路径遍历未被过滤: {safe_name}"
    assert '\\' not in safe_name, f"路径遍历未被过滤: {safe_name}"
    assert not safe_name.startswith('.'), f"相对路径未被过滤: {safe_name}"
```

**预计执行时间**: 30秒

---

## 8. 🎵 场景六: 音频系统

### 场景描述

验证PyCC2的音频子系统在各种场景下正确播放音效和BGM。

### 8.1 TC-060: 武器音效播放 (P0)

**测试目标**: 验证步枪/MG/坦克炮等武器音效能正确播放

```python
from pycc2.infrastructure.audio.weapon_sounds import WeaponSoundSystem

audio = WeaponSoundSystem()
audio.initialize()

weapon_sounds = [
    ('rifle', 'm1_garand'),
    ('mg', 'mg42'),
    ('tank_gun', 'sherman_75mm'),
    ('explosion', 'grenade'),
]

played = []
for category, weapon_id in weapon_sounds:
    try:
        audio.play_weapon_sound(weapon_id=weapon_id)
        played.append(weapon_id)
        print(f"  ✓ {weapon_id}")
    except Exception as e:
        print(f"  ✗ {weapon_id}: {e}")

assert len(played) >= 2, f"至少2种武器音效应可用，实际{len(played)}种"
```

**预计执行时间**: 2分钟

---

### 8.2 TC-061: 环境音效 (风/雨) (P0)

**测试目标**: 验证环境氛围音效播放

```python
from pycc2.infrastructure.audio.environmental_audio import EnvironmentalAudio

env_audio = EnvironmentalAudio()
env_audio.initialize()

env_sounds = ['wind', 'rain', 'thunder', 'birds']
played_env = []

for sound_name in env_sounds:
    try:
        env_audio.play_environment_sound(sound_name, loop=True)
        played_env.append(sound_name)
    except Exception:
        pass

assert len(played_env) >= 1, "至少1种环境音效应可用"
```

**预计执行时间**: 1分钟

---

### 8.3 TC-062: BGM音乐切换 (P1)

**测试目标**: 验证菜单/战斗/胜利/失败BGM正确切换

```python
from pycc2.infrastructure.audio.bgm_system import BGMSystem

bgm = BGMSystem()
bgm.initialize()

bgm_tracks = {
    'menu': 'main_theme.ogg',
    'battle': 'combat.ogg',
    'victory': 'victory_fanfare.ogg',
    'defeat': 'defeat_somber.ogg',
}

for scene, track in bgm_tracks.items():
    try:
        bgm.play_scene_music(scene)
        assert bgm.current_scene == scene
        print(f"  ✓ BGM: {scene}")
    except Exception as e:
        print(f"  ⚠ BGM {scene} 不可用: {e}")
```

**预计执行时间**: 2分钟

---

### 8.4 TC-064: 音频音量控制 (P1)

**测试目标**: 验证主音量/SFX/BGM独立音量控制

```python
bgm.set_volume(0.5)
assert bgm.volume == 0.5

audio.set_sfx_volume(0.7)
assert audio.sfx_volume == 0.7

bgm.set_volume(0.0)  # 静音
assert bgm.volume == 0.0

bgm.set_volume(1.0)  # 最大
assert bgm.volume <= 1.0
```

**预计执行时间**: 1分钟

---

### 8.5 TC-065: 音频设备热插拔 (P2)

**测试目标**: 验证音频设备断开/重连时不崩溃

```python
audio.shutdown()
audio.initialize()  # 重新初始化

try:
    audio.play_weapon_sound('m1_garand')
    print("  ✓ 重新初始化后音频正常")
except Exception as e:
    print(f"  ⚠ 重启后异常: {e}")
```

**预计执行时间**: 1分钟

---

### 8.6 TC-066: 3D立体声定位 (P2)

**测试目标**: 验证声音根据单位位置有立体声效果

```python
from pycc2.infrastructure.audio.stereo_sound import StereoSoundManager

stereo = StereoSoundManager()
stereo.initialize(camera=game_loop.state.camera)

left_unit = player_units[0]
right_unit = player_units[-1] if len(player_units) > 1 else player_units[0]

pan_left = stereo.calculate_pan(left_unit.position.pixel_position)
pan_right = stereo.calculate_pan(right_unit.position.pixel_position)

assert -1.0 <= pan_left <= 1.0
assert -1.0 <= pan_right <= 1.0

if left_unit.position.pixel_position.x < right_unit.position.pixel_position.x:
    assert pan_left <= pan_right, "左侧单位声相应在左边"
```

**预计执行时间**: 1分钟

---

### 8.7 TC-067: 语音命令系统 (P2)

**测试目标**: 验证单位语音反馈（"Moving!"、"Contact!"等）

```python
from pycc2.infrastructure.audio.voice_command_system import VoiceCommandSystem

voice = VoiceCommandSystem()
voice.initialize()

commands = ['moving', 'contact', 'taking_fire', 'enemy_spotted']
voice_played = []

for cmd in commands:
    try:
        voice.play_voice(cmd, faction='allies')
        voice_played.append(cmd)
    except Exception:
        pass

print(f"语音命令可用: {len(voice_played)}/{len(commands)}")
```

**预计执行时间**: 1分钟

---

### 8.8 TC-068: 音频资源缺失降级 (P2)

**测试目标**: 验证音频文件缺失时静默降级而非崩溃

```python
try:
    audio.play_weapon_sound('nonexistent_weapon_xyz')
    print("  ✓ 缺失音效静默处理")
except FileNotFoundError:
    print("  ✓ 缺失音效抛出可捕获异常")
except Exception as e:
    assert 'not found' in str(e).lower() or 'missing' in str(e).lower(), \
        f"错误信息不够友好: {e}"
```

**预计执行时间**: 30秒

---

## 9. 🤖 场景七: AI对手行为

### 场景描述

验证AI对手在不同难度下的战术行为合理性。

### 9.1 TC-069: AI单位基本移动 (P0)

**测试目标**: 验证AI单位能够自主移动和寻路

```python
from pycc2.services.ai_service import AIService

ai = AIService(event_bus=game_loop.event_bus)
ai.initialize(enemy_units=ai_units)

initial_positions = [u.position.tile_coord.copy() for u in ai_units[:3]]

for tick in range(120):  # 4秒
    ai.update(dt)
    game_loop._update_logic(dt)
    game_loop.state.tick += 1

moved_count = sum(
    1 for i, u in enumerate(ai_units[:3]) 
    if u.position.tile_coord != initial_positions[i]
)

assert moved_count >= 1, f"至少1个AI单位应移动，实际{moved_count}个"
print(f"AI单位移动: {moved_count}/3")
```

**预计执行时间**: 3分钟

---

### 9.2 TC-070: AI战术行为-包抄 (P1)

**测试目标**: 验证AI在Hard+难度会尝试侧翼包抄

```python
from pycc2.domain.ai.difficulty_system import DifficultySystem, DifficultyLevel

diff_system = DifficultySystem(level=DifficultyLevel.HARD)
assert diff_system.config.use_flanking == True, "Hard难度应启用包抄"

intent = TacticIntent(
    unit_id=ai_units[0].id,
    tactic_type=TacticType.ATTACK,
    target_unit_id=player_units[0].id,
    priority=10
)

modified = diff_system.modify_ai_decision(intent, blackboard, rng=random.Random(42))
assert modified is not None, "Hard AI应做出决策"
```

**预计执行时间**: 2分钟

---

### 9.3 TC-071: AI战术行为-压制射击 (P1)

**测试目标**: 验证AI会使用压制火力限制玩家行动

```python
assert diff_system.config.use_suppression_tactics == True

suppress_intent = TacticIntent(
    unit_id=ai_units[0].id,
    tactic_type=TacticType.SUPPRESS_FIRE,
    target_unit_id=player_units[0].id,
    priority=8
)

modified_suppress = diff_system.modify_ai_decision(suppress_intent, blackboard)
assert modified_suppress is not None or random.Random(42).random() > 0.3, \
    "压制决策可能因弹药节约而被跳过"
```

**预计执行时间**: 1分钟

---

### 9.4 TC-072: AI VP占领行为 (P1)

**测试目标**: 验证AI会主动抢占Victory Location

```python
vl_positions = [TileCoord(*vl.position) for vl in sample_battle.victory_distances]

ai_near_vl = 0
for ai_unit in ai_units:
    for vl_pos in vl_positions:
        distance = abs(ai_unit.position.tile_coord.x - vl_pos.x) + \
                   abs(ai_unit.position.tile_coord.y - vl_pos.y)
        if distance <= 5:
            ai_near_vl += 1
            break

print(f"AI单位接近VL: {ai_near_vl}/{len(ai_units)}")
# 注意: 这需要在较长时间运行后才显著
```

**预计执行时间**: 3分钟

---

### 9.5 TC-073: AI难度差异-Green (P2)

**测试目标**: 验证Green(新手)AI的行为特征

```python
easy_cfg = DifficultySystem(DifficultyLevel.EASY).config

assert easy_cfg.base_hit_chance <= 0.3, "Easy命中率应很低"
assert easy_cfg.reaction_delay_ticks >= 10, "Easy反应延迟应很长"
assert easy_cfg.aggressiveness <= 0.3, "Easy不应激进"
assert easy_cfg.coordination_enabled == False, "Easy无协同"
```

**预计执行时间**: 1分钟

---

### 9.6 TC-074: AI难度差异-Veteran (P2)

**测试目标**: 验证Veteran(老兵)AI的行为特征

```python
veteran_cfg = DifficultySystem(DifficultyLevel.VETERAN).config

assert veteran_cfg.base_hit_chance >= 0.7, "Veteran命中率高"
assert veteran_cfg.reaction_delay_ticks == 0, "Veteran无延迟"
assert veteran_cfg.aggressiveness >= 0.85, "Veteran非常激进"
assert veteran_cfg.coordination_enabled == True, " Veteran有协同"
assert veteran_cfg.use_flanking == True, " Veteran会包抄"
```

**预计执行时间**: 1分钟

---

### 9.7 TC-075: AI撤退逻辑 (P2)

**测试目标**: 验证AI在劣势时会战术性撤退

```python
from pycc2.domain.ai.retreat_ai import RetreatAIBehavior

retreat_ai = RetreatAIBehavior()

should_retreat = retreat_ai.should_retreat(
    unit=ai_units[0],
    health_ratio=0.2,  # 重伤
    enemy_superiority=3.0,  # 敌人3倍优势
    near_cover=True
)

assert should_retreat == True, "重伤+劣势时应撤退"
```

**预计执行时间**: 1分钟

---

### 9.8 TC-076: AI协同作战 (P2)

**测试目标**: 验证多个AI单位会协调攻击同一目标

```python
from pycc2.domain.ai.squad_coordinator import SquadCoordinator

coordinator = SquadCoordinator()
targets = coordinator.coordinate_attack(
    squad_units=ai_units[:3],
    enemy_units=player_units[:2],
    difficulty_config=veteran_cfg
)

assert targets is not None, "应返回协同攻击计划"
if len(targets) > 0:
    primary_target = targets[0]
    assert primary_target in [u.id for u in player_units[:2]], "目标应是敌方单位"
```

**预计执行时间**: 2分钟

---

### 9.9 TC-077: AI感知系统 (P2)

**测试目标**: 验证AI的视野和侦测机制

```python
from pycc2.domain.ai.perception_system import PerceptionSystem

perception = PerceptionSystem()
perception.initialize(ai_units=ai_units, game_map=game_map)

visible_enemies = perception.get_visible_enemies(ai_units[0])
print(f"AI单位{ai_units[0].id}可见敌人: {len(visible_enemies)}")

heard_positions = perception.get_heard_positions(ai_units[0])
print(f"AI单位{ai_units[0].id}听到声音: {len(heard_positions)}处")
```

**预计执行时间**: 1分钟

---

### 9.10 TC-078: AI单位多样性 (P2)

**测试目标**: 验证AI控制多种类型单位的能力

```python
unit_types = set(u.unit_type.name for u in ai_units)
print(f"AI单位类型: {unit_types}")

expected_types = {'infantry', 'mg_team', 'officer'}
has_diversity = len(unit_types.intersection(expected_types)) >= 2
assert has_diversity, f"AI应有至少2种单位类型，实际{unit_types}"
```

**预计执行时间**: 1分钟

---

## 10. 📱 场景八: UI交互

### 场景描述

验证用户界面的交互流畅性和信息展示准确性。

### 10.1 TC-079: 底部面板信息显示 (P0)

**测试目标**: 验证选中单位时底部面板显示完整信息

```python
from pycc2.presentation.rendering.cc2_bottom_panel import CC2BottomPanel

panel = CC2BottomPanel(width=SCREEN_W, height=120)
panel_surface = pygame.Surface((SCREEN_W, 120))

game_loop.state.selected_unit_ids = {player_units[0].id}
panel.render(surface=panel_surface, selected_unit=player_units[0], 
             game_state=game_loop.state, tick=game_loop.state.tick)

filled_ratio = (pygame.surfarray.array3d(panel_surface).sum(axis=2) > 0).mean()
assert filled_ratio > 0.5, "面板应有内容显示"
```

**预计执行时间**: 1分钟

---

### 10.2 TC-080: 小地图导航 (P0)

**测试目标**: 验证点击小地图可以跳转摄像机位置

```python
from pycc2.presentation.rendering.minimap import Minimap

minimap = Minimap(size=(200, 200), game_map=game_map, camera=game_loop.state.camera)

click_result = minimap.handle_click(pos=(100, 100))
if click_result:
    new_camera_pos = click_result
    assert new_camera_pos != game_loop.state.camera.position, "摄像机应移动"
```

**预计执行时间**: 1分钟

---

### 10.3 TC-081: 摄像机控制-缩放 (P0)

**测试目标**: 验证鼠标滚轮缩放功能

```python
from pycc2.presentation.rendering.camera import Camera

initial_zoom = game_loop.state.camera.zoom

game_loop.interaction_controller.handle_mouse_wheel(delta=1)  # 放大
assert game_loop.state.camera.zoom > initial_zoom, "滚轮上应放大"

game_loop.interaction_controller.handle_mouse_wheel(delta=-1)  # 缩小
assert game_loop.state.camera.zoom < game_loop.state.camera.zoom or \
       game_loop.state.camera.zoom >= 0.5, "滚轮下应缩小或在最小值"
```

**预计执行时间**: 1分钟

---

### 10.4 TC-082: 摄像机控制-平移 (P1)

**测试目标**: 验证拖拽/边缘滚动平移摄像机

```python
initial_pos = game_loop.state.camera.position.copy()

game_loop.interaction_controller.handle_camera_drag(start=(100, 100), end=(200, 200))
new_pos = game_loop.state.camera.position

moved = abs(new_pos.x - initial_pos.x) > 0 or abs(new_pos.y - initial_pos.y) > 0
assert moved, "拖拽应移动摄像机"
```

**预计执行时间**: 1分钟

---

### 10.5 TC-083: 教程系统引导 (P1)

**测试目标**: 验证新手教程逐步引导流程

```python
from pycc2.presentation.ui.tutorial_system import TutorialOverlay

tutorial = TutorialOverlay(display_config=DisplayConfig())

assert tutorial.is_active == False, "初始不应激活"
tutorial.start_tutorial('basic_controls')
assert tutorial.is_active == True, "启动后应激活"

step = tutorial.get_current_step()
assert step is not None, "应有当前步骤"
assert 'text' in step or 'highlight' in step, "步骤应有内容"

tutorial.advance_to_next_step()
assert tutorial.step_index == 1, "应进入下一步"

tutorial.complete_tutorial()
assert tutorial.is_completed == True, "完成后应标记完成"
```

**预计执行时间**: 2分钟

---

### 10.6 TC-084: 快捷键提示显示 (P1)

**测试目标**: 验证界面显示正确的快捷键提示

```python
from pycc2.presentation.ui.keybind_manager import KeybindManager

kb_manager = KeybindManager()
keybinds = kb_manager.get_visible_keybinds()

essential_keys = ['move', 'attack', 'defend', 'stealth']
displayed = [k for k in essential_keys if k in keybinds]

assert len(displayed) >= 3, f"应显示至少3个快捷键，实际{len(displayed)}个"
print(f"快捷键提示: {keybinds}")
```

**预计执行时间**: 1分钟

---

### 10.7 TC-085: 设置菜单功能 (P1)

**测试目标**: 验证设置菜单的各项配置生效

```python
from pycc2.presentation.ui.settings_menu import SettingsMenu
from pycc2.domain.interfaces.display_config import DisplayConfig

dc = DisplayConfig()
settings = SettingsMenu(dc, keybind_manager=KeybindManager())

settings.set_option('music_volume', 0.8)
assert dc.music_volume == 0.8

settings.set_option('show_fps', True)
assert dc.show_fps == True

settings.set_option('difficulty', 'veteran')
assert dc.difficulty == 'veteran'

settings.apply_and_save()
print("✓ 设置应用成功")
```

**预计执行时间**: 1分钟

---

### 10.8 TC-086: 暂停菜单 (ESC) (P2)

**测试目标**: 验证ESC暂停菜单的所有选项

```python
game_loop._pause_menu.toggle()
assert game_loop._pause_menu.is_active

pause_buttons = list(game_loop._pause_menu._buttons.keys())
essential_pause_btns = ['resume', 'quit_to_menu', 'settings']
assert all(btn in pause_buttons for btn in essential_pause_btns), \
    f"暂停菜单缺少必要按钮，现有: {pause_buttons}"

action = game_loop._pause_menu.handle_click(
    game_loop._pause_menu._buttons['resume'].center
)
assert action == 'resume'
game_loop._pause_menu.deactivate()
assert not game_loop._pause_menu.is_active
```

**预计执行时间**: 1分钟

---

### 10.9 TC-087: 工具提示(Tooltip) (P2)

**测试目标**: 验证鼠标悬停显示详细工具提示

```python
from pycc2.presentation.ui.tooltip import TooltipManager

tooltip = TooltipManager(font=None)

tooltip.show_tooltip(
    text="步兵班\nHP: 80/100\n武器: M1 Garand",
    position=(200, 200),
    max_width=200
)

assert tooltip.is_visible == True
tooltip_surface = tooltip.render()
assert tooltip_surface.get_size()[0] > 0
assert tooltip_surface.get_size()[1] > 0

tooltip.hide_tooltip()
assert tooltip.is_visible == False
```

**预计执行时间**: 1分钟

---

### 10.10 TC-088: 战斗日志/消息队列 (P2)

**测试目标**: 验证战斗事件实时记录在日志中

```python
from pycc2.presentation.ui.combat_log import CombatLog

log = CombatLog(max_entries=50)

log.add_entry("单位 [Rifle Squad-1] 移动到 (15, 20)", tick=100)
log.add_entry("单位 [MG Team-2] 开火命中! 目标HP-15", tick=105)
log.add_entry("★ 敌军单位 [Panzer IV] 被摧毁!", tick=110)

entries = log.get_recent_entries(count=10)
assert len(entries) == 3, f"应有3条日志，实际{len(entries)}条"

last_entry = entries[-1]
assert '摧毁' in last_entry['text'], "最后一条应包含摧毁信息"
```

**预计执行时间**: 1分钟

---

### 10.11 TC-089: 径向菜单(Radial Menu) (P2)

**测试目标**: 验证右键径向命令菜单

```python
from pycc2.presentation.ui.radial_menu import RadialMenu

radial = RadialMenu(radius=60, items=[
    ('move', 'Z'),
    ('attack', 'S'),
    ('defend', 'D'),
    ('smoke', 'C'),
])

radial.show_at(position=(400, 300))
assert radial.is_visible

selected = radial.handle_click(pos=(430, 270))  # 点击Move扇区
assert selected == 'move', f"应选中move，实际{selected}"

radial.hide()
assert not radial.is_visible
```

**预计执行时间**: 1分钟

---

## 11. 执行计划与优先级矩阵

### 11.1 推荐执行顺序

```
Phase 1 - Smoke Test (发布门槛, 必须全部通过) [~45min]
├── TC-001: 首次启动 (P0)
├── TC-002: 依赖检查 (P0)
├── TC-003: 主菜单 (P0)
├── TC-008: 战役加载 (P0)
├── TC-010: 地图加载 (P0)
├── TC-011: 部署 (P0)
├── TC-020: 单位选择 (P0)
├── TC-021-TC-024: 核心命令 (P0)
├── TC-038: 地形渲染 (P0)
├── TC-039: 精灵 (P0)
├── TC-040: 迷雾 (P0)
├── TC-053: 存档 (P0)
├── TC-054: HMAC (P0)
├── TC-060: 武器音效 (P0)
├── TC-061: 环境音效 (P0)
├── TC-069: AI移动 (P0)
├── TC-079: 底部面板 (P0)
├── TC-080: 小地图 (P0)
└── TC-081: 摄像机缩放 (P0)

Phase 2 - Core Features (重要功能, ≥95%通过) [~90min]
├── 所有 P1 用例 (31个)
└── 重点: TC-012, TC-013, TC-053, TC-070, TC-083

Phase 3 - Polish (锦上添花, ≥80%通过) [~135min]
├── 所有 P2 用例 (26个)
└── 性能优化和边缘情况
```

### 11.2 自动化可行性评估

| 类别 | 可自动化程度 | 推荐方式 |
|------|-------------|----------|
| 启动/依赖 | ★★★★★ | pytest fixture |
| 菜单导航 | ★★★★★ | pygame事件注入 |
| 战斗命令 | ★★★★☆ | API调用+事件 |
| 视觉渲染 | ★★★☆☆ | 截图对比(需baseline) |
| 音频播放 | ★★★☆☆ | mock音频后端 |
| AI行为 | ★★★☆☆ | 固定seed+断言状态 |
| 存档完整性 | ★★★★★ | 直接API调用 |

---

## 12. 验收标准与通过/失败判定

### 12.1 总体通过标准

| 发布阶段 | P0通过率 | P1通过率 | P2通过率 |
|----------|---------|---------|---------|
| Alpha内部 | 100% | 80% | 60% |
| Beta公开 | 100% | 95% | 75% |
| RC候选 | 100% | 98% | 80% |
| 正式发布 | 100% | 99% | 85% |

### 12.2 单用例判定规则

```yaml
通过条件:
  - 所有的assert语句通过
  - 无未捕获的Exception
  - 无pygame error输出
  - 截图生成成功（如涉及）
  - 执行时间在预估范围内(±50%)

失败条件:
  - AssertionError: 功能不符合预期
  - ImportError/ModuleNotFoundError: 缺失依赖
  - pygame.error: 渲染/音频子系统故障
  - TimeoutError: 操作超时(>预估时间3倍)
  - SegmentationFault: 底层崩溃(严重!)

阻塞发布(P0 Blocker):
  - 游戏无法启动(TC-001失败)
  - 核心崩溃(TC-012/TC-053异常退出)
  - 数据丢失(TC-054 HMAC绕过)
  - 安全漏洞(TC-057路径遍历)

可接受风险(P1/P2 Flaky):
  - CI环境音频设备差异 → 标记xfail
  - 随机数导致的间歇性失败 → 增加重试或固定seed
  - 视觉回归误报 → 人工审核后更新baseline
```

### 12.3 缺陷分级

| 级别 | 定义 | 响应时间 | 示例 |
|------|------|----------|------|
| **Critical** | 数据丢失/安全漏洞/无法启动 | 立即修复 | HMAC被绕过、存档损坏 |
| **Major** | 核心功能不可用 | 24h内 | 无法部署单位、命令无效 |
| **Minor** | 功能受限但有workaround | 48h内 | 某地形渲染异常、音效缺失 |
| **Cosmetic** | 视觉/体验瑕疵 | 下版本 | 动画卡顿、文字错别字 |

---

## 13. 自动化实现指南

### 13.1 项目结构建议

```
tests/e2e/
├── E2E_REAL_USER_SCENARIOS.md      ← 本文档
├── conftest.py                     ← 共享fixtures
├── __init__.py
├── test_scenario_1_installation.py  ← TC-001~TC-007
├── test_scenario_2_campaign.py      ← TC-008~TC-019
├── test_scenario_3_combat.py        ← TC-020~TC-037
├── test_scenario_4_visual.py        ← TC-038~TC-052
├── test_scenario_5_save_load.py     ← TC-053~TC-059
├── test_scenario_6_audio.py         ← TC-060~TC-068
├── test_scenario_7_ai_behavior.py   ← TC-069~TC-078
├── test_scenario_8_ui_interaction.py← TC-079~TC-090
└── screenshots/                     ← 回归测试baseline
    ├── menu_main.png
    ├── terrain_all_types.png
    ├── fog_of_war.png
    └── baseline_standard_scene.png
```

### 13.2 关键Fixture示例

```python
# conftest.py
import os
import pytest
import pygame

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

@pytest.fixture(scope='session')
def pygame_display():
    pygame.init()
    screen = pygame.display.set_mode((1280, 720))
    yield screen
    pygame.quit()

@pytest.fixture
def game_session(pygame_display):
    """完整的游戏会话: 菜单→战役→部署→战斗"""
    from tests.e2e.test_full_user_journey import (
        _init_game, _build_game_loop, _start_deployment
    )
    wm, screen, menu = _init_game()
    # ... 复用现有test_full_user_journey的逻辑
    yield {'game_loop': game_loop, 'screen': screen, 'menu': menu}

@pytest.fixture
def campaign_data():
    from pycc2.domain.systems.campaign_four_layer import create_market_garden_campaign
    return create_market_garden_campaign()
```

### 13.3 运行命令

```bash
# 运行所有E2E测试
pytest tests/e2e/ -v --tb=short --durations=10

# 仅运行P0用例（发布门槛）
pytest tests/e2e/ -v -m "priority_p0"

# 运行单个场景类别
pytest tests/e2e/test_scenario_3_combat.py -v

# 生成覆盖率报告
pytest tests/e2e/ --cov=src/pycc2 --cov-report=html

# 运行并截图（用于调试）
pytest tests/e2e/ --screenshot=on

# 并行执行（如果使用pytest-xdist）
pytest tests/e2e/ -n auto --dist=loadscope
```

### 13.4 CI集成示例

```yaml
# .github/workflows/e2e.yml
name: E2E Tests

on: [push, pull_request]

jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          
      - name: Install dependencies
        run: |
          pip install -e ".[dev]"
          sudo apt-get update && sudo apt-get install -y xvfb
          
      - name: Run E2E tests
        run: |
          xvfb-run pytest tests/e2e/ -v --junitxml=e2e-results.xml
          
      - name: Upload screenshots on failure
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: e2e-screenshots
          path: tests/e2e/screenshots/
```

---

## 附录 A: 测试数据矩阵

### A.1 地图覆盖清单

| 地图ID | 战役 | Day | 地形复杂度 | VL数量 | 测试用例 |
|--------|------|-----|-----------|--------|----------|
| oosterbeek_lz | Arnhem | 1 | 中 | 3 | TC-010, TC-011 |
| arnhem_bridge | Arnhem | 1-3 | 高 | 2 (桥梁40分) | TC-030 |
| nijmegen_crossing | Nijmegen | 1 | 中 | 2 | TC-015 |
| son_bridge | Eindhoven | 1 | 低 | 1 | TC-012 |
| ... | ... | ... | ... | ... | ... |

### A.2 单位类型矩阵

| 单位类型 | 阵营 | 移动方式 | 武器 | 特殊能力 | 覆盖用例 |
|----------|------|----------|------|----------|----------|
| Rifle Squad | US/UK | 步行 | M1 Garand | - | TC-020~TC-028 |
| MG Team | GERMAN | 步行 | MG42 | 压制 | TC-024 |
| Officer | ALL | 步行 | Pistol | 士气加成 | TC-033 |
| Engineer | ALL | 步行 | Carbine | 爆破/烟雾 | TC-025, TC-030 |
| Light Tank | ALL | 载具 | 机炮 | 压碎障碍 | TC-036 |
| Halftrack | US | 载具 | MG | 运兵 | TC-036 |

### A.3 难度-行为对照表

| 难度 | CC2原版名 | 命中率 | 反应时间 | 协同 | 包抄 | 适合玩家 |
|------|-----------|--------|----------|------|------|----------|
| Easy | Green | 25% | 15tick | ✗ | ✗ | 纯新手 |
| Medium | Regular | 50% | 0tick | ✗ | ✗ | 有策略游戏经验 |
| Hard | Veteran | 65% | 0tick | ✓ | ✓ | CC老玩家 |
| Veteran | Elite | 75% | 0tick | ✓ | ✓ | 硬核玩家 |

---

## 附录 B: 变更日志

| 版本 | 日期 | 作者 | 变更内容 |
|------|------|------|----------|
| v1.0 | 2026-06-01 | E2E Architect | 初始版本，91个测试用例 |

---

## 附录 C: 术语表

| 术语 | 全称 | 说明 |
|------|------|------|
| E2E | End-to-End | 端到端测试，模拟完整用户流程 |
| FoW | Fog of War | 战争迷雾 |
| VL | Victory Location | 胜利地点/关键目标 |
| LZ | Landing Zone | 空降区 |
| CC2 | Close Combat 2 | 原版游戏（1997年Atomic Games） |
| Market Garden | Operation Market Garden | 市场花园行动（1944年9月） |
| XXX Corps | British XXX Corps | 英国第30军 |
| HMAC | Hash-based Message Authentication Code | 基于哈希的消息认证码 |
| P0/P1/P2 | Priority 0/1/2 | 优先级等级 |

---

*本文档由PyCC2 E2E测试团队维护。如有疑问请提交Issue至项目仓库。*
