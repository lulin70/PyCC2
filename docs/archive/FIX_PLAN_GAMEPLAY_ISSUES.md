# PyCC2 画面与交互问题 — 修复方案文档

> **版本**: v1.0 | **日期**: 2026-06-19  
> **范围**: 基于E2E诊断发现的所有画面/交互问题  
> **前置条件**: LOS系统修复已完成（22/22 E2E测试通过，3642+单元测试全绿）

---

## 一、问题总览

| # | 用户反馈 | 严重度 | 根因分类 | 修复状态 |
|---|---------|--------|---------|---------|
| P1 | 没有HUD | **高** | 实际无bug（GameLoop调用正确） | 需验证完整流程 |
| P2 | 不能Save/Load | **中** | 待验证完整流程 | 待修复 |
| P3 | 士兵形象不是顶部视角 | **中** | sprite缺失+回退形状太小 | 待修复 |
| P4 | 右键命令选择后不执行 | **高** | 交互回调链可能断裂 | 待修复 |
| P5 | 敌军进入射程不开火 | **关键** | AI单位未注册到AIService | 待修复 |

---

## 二、P1: HUD显示问题

### 2.1 诊断结论

**代码层面无bug**。`GameLoop.run()` 第331行正确调用:
```python
self._hud_manager.render(screen, self.state.camera, self.state.state)
```

HUDManager.render() 签名:
```python
def render(self, screen: pygame.Surface, camera: Camera, game_state: GameState) -> None
```

### 2.2 可能的真实原因

| 假设 | 可能性 | 验证方法 |
|------|--------|---------|
| HUD在部署阶段不显示（仅战斗阶段显示） | **高** | 检查 `_render_scene()` 中 deployment vs battle 分支 |
| CC2 Panel初始化失败（minimap/cc2_panel注入为None） | 中 | 检查 GameLoopAssembler._init_hud() 是否正确传入依赖 |
| DisplayConfig 缩放导致HUD画到屏幕外 | 低 | 检查 `dc.compute_default_zoom()` 返回值 |

### 2.3 修复方案

**文件**: `src/pycc2/services/game_loop_assembler.py`  
**位置**: `_init_hud()` 方法 (约L188)

```python
# 当前代码（需确认）
def _init_hud(self):
    self._loop._hud_manager.initialize(
        screen=...,          # ← 确认此参数
        ...
    )
```

**修复步骤**:
1. 确认 `_init_hud()` 传入了正确的 minimap 和 cc2_panel 实例
2. 确认部署阶段也有基本HUD（至少显示小地图和当前阶段提示）
3. 在 `renderer.render()` 的 `_render_hud()` 方法（enhanced_renderer.py L741）中加防御性检查

**验证方法**: 截图对比部署阶段和战斗阶段的画面，确认HUD元素出现

---

## 三、P2: Save/Load 功能

### 3.1 当前架构

```
用户按 F5 / 点击 Save
    → GameLoop._handle_quick_save()
        → SaveController.save_game(slot)
            → SecureSaveManager.save_game(slot, state_dict)
                → JSON序列化 + HMAC签名 + 写入文件
```

### 3.2 已知问题

| 问题 | 详情 | 影响 |
|------|------|------|
| HMAC Key 警告 | "No HMAC key configured. Using project-derived key" | 开发环境非阻塞，但跨机器读档会失败 |
| 快捷键绑定 | 需确认 F5/F9 是否正确绑定到 save/load handler | 用户可能不知道怎么触发 |
| Load Game 流程 | 选择slot后 → _load_saved_game() → SaveController.restore_state() | 需验证完整反序列化 |

### 3.3 修复方案

**3.3.1 快捷键确认**
- 文件: `src/pycc2/presentation/input/handler.py` 或 `keybind_manager.py`
- 确认 F5=QuickSave, F9=QuickLoad, F11/L=LoadMenu 存在且绑定

**3.3.2 HUD中加入Save/Load按钮**
- 文件: `src/pycc2/presentation/ui/cc2_hud.py`
- 在底部面板添加 Save/Load 图标按钮（如CC2原版）

**3.3.3 存档兼容性加固**
```python
# SecureSaveManager.__init__() 中
if not PYCC2_SAVE_HMAC_KEY:
    # 写入持久化key到 ~/.pycc2/hmac_key
    self._ensure_persistent_key()
```

**验证方法**: 
1. 新游戏 → F5存档 → 退出 → 重新启动 → F9读档 → 确认单位/状态恢复

---

## 四、P3: 单位视觉（精灵/顶部视角）

### 4.1 诊断数据

来自 `diagnose_units.py` 的实测结果:

```
sprite for allies/infantry_squad: None     ← 无预缓存
create_unit_sprite result: <Surface(32x32)> ← 可动态创建（回退）
TILE_SIZE = 48, SPRITE_SIZE = 32
fallback shape radius = max(12, int(15 * zoom)) ≈ 14px
```

### 4.2 问题分析

**问题A: PNG Sprite未预缓存**
- `SpriteCacheManager.get_unit_sprite()` 对 `allies/infantry_squad` 返回 None
- 每次渲染都调用 `create_unit_sprite()` 动态创建 → 性能浪费
- 原因: sprite资源路径可能不存在或格式不匹配

**问题B: 回退几何形状太小**
- 14px半径的圆形在48px地形块上只占很小比例
- 颜色可能与地形接近（灰绿背景上的蓝绿色圆）

**问题C: 非"顶部视角"**
- CC2原版使用类似顶部视角的步兵精灵图
- 当前回退是纯色圆形→多边形，没有方向感

### 4.3 修复方案

**4.3.1 短期：增强回退渲染（立即见效）**

文件: `src/pycc2/presentation/rendering/unit_renderer.py`  
位置: `draw_units()` fallback 分支 (L66+)

```python
# 当前 (L131)
base_radius = max(12, int(15 * camera.zoom))

# 修改为: 更大更明显的单位标记
base_radius = max(20, int(24 * camera.zoom))  # 增大40%
# 添加白色边框增强可见性
border_width = max(2, int(3 * camera.zoom))
```

同时在 `draw_hexagon()` (L348+) 中增加：
- 方向指示箭头（根据 `unit.position.facing_rad`）
- 阵营颜色外圈（Allies=蓝, Axis=红）

**4.3.2 中期：预缓存常用sprite**

文件: `src/pycc2/presentation/rendering/sprite_cache_manager.py`

在 `SpriteCacheManager.__init__()` 或 `EnhancedRenderer.initialize()` 中:
```python
# 预缓存6种常用单位×4方向×2阵营 = 48个sprite
COMMON_UNITS = [
    ("allies", "infantry_squad"), ("axis", "infantry_squad"),
    ("allies", "machine_gun_squad"), ("axis", "machine_gun_squad"),
    ("allies", "tank"), ("axis", "tank"),
]
for faction, utype in COMMON_UNITS:
    for dir_idx in range(4):
        self.get_unit_sprite(faction, utype, dir_idx, SPRITE_SIZE)
```

**4.3.3 长期：制作CC2风格顶部视角精灵**

- 32×32 PNG, 8方向旋转
- Allies: 绿色钢盔轮廓, Axis: 灰色钢盔轮廓
- 含idle/run/prone/dead状态

**验证方法**: 
1. 放置单位后截图，确认单位清晰可见
2. 不同阵营单位颜色不同
3. 单位有朝向指示

---

## 五、P4: 右键命令菜单

### 5.1 当前架构

```
用户右键点击地面/单位
    → PygameInputHandler.handle_event()
        → InteractionController.handle_right_click(pos)
            → 显示 RadialMenu 或 ContextMenu
                → 用户拖拽/点击选择命令
                    → 触发回调 (_on_move_command / _on_attack_command / ...)
                        → EventBus 发布 PlayerCommand 事件
                            → CombatDirector / PathFinder 执行
```

### 5.2 关键代码位置

| 组件 | 文件 | 关键方法 |
|------|------|---------|
| 输入捕获 | `presentation/input/handler.py` | `handle_event()` |
| 交互控制 | `presentation/input/interaction_controller.py` | `handle_right_click()`, `handle_right_drag()` |
| 径向菜单 | `presentation/ui/radial_menu.py` | `show()`, `handle_input()` |
| 命令绑定 | `services/hud_manager.py` | `_bind_command_callbacks()` L134+ |
| 命令执行 | `services/event_bus.py` | `publish(PlayerCommand(...))` |

### 5.3 可能断点

| 断点位置 | 检查内容 |
|---------|---------|
| PygameInputHandler | 右键事件是否传递给 InteractionController? |
| InteractionController | `_on_move_command` 等回调是否被设置? |
| RadialMenu | 菜单是否正确渲染在鼠标位置? |
| HUDManager | `_bind_command_callbacks()` 中的 lambda 是否正确闭包? |
| EventBus | PlayerCommand 事件是否有订阅者处理? |

### 5.4 修复方案

**5.4.1 添加调试日志链**

在每个关键节点加临时日志:
```python
# interaction_controller.py - handle_right_click
logger.debug("Right-click at %s, mode=%s", pos, self._mode)

# radial_menu.py - handle_input
logger.debug("Radial menu selection: %s", selected_cmd)

# hud_manager.py - _bind_command_callbacks
def on_move():
    logger.debug("MOVE command executed for units: %s", selected_ids)
```

**5.4.2 验证回调注册**

在 GameLoopAssembler 中确认:
```python
# assembler 应该调用
interaction_controller.set_on_move_command(self._on_move)
interaction_controller.set_on_attack_command(self._on_attack)
```

**5.4.3 如果回调确实断裂**

修复 GameLoopAssembler:
```python
def _wire_interaction_callbacks(self):
    ic = self._loop.interaction_controller
    ic._on_move_command = self._handle_move_order
    ic._on_attack_command = self._handle_attack_order
    ic._on_deselect = self._handle_deselect
```

**验证方法**: 
1. 启动游戏 → 部署单位 → 右键地面 → 确认径向菜单出现
2. 选择Move命令 → 确认目标单位移动到点击位置
3. 选择Attack命令 → 选择目标 → 确认攻击执行

---

## 六、P5: 敌军AI不开火（最关键）

### 6.1 根因定位

**核心代码** (`game_loop.py` L496-L507):

```python
def _update_ai(self, dt: float) -> None:
    if self.ai_service is not None and self.ai_service.managed_unit_count > 0:
        # ... AI tick logic ...
```

**两个前置条件必须同时满足**:
1. `ai_service is not None` — AIService实例存在
2. `managed_unit_count > 0` — 有AI单位被注册

### 6.2 AI注册流程

```
部署阶段完成 / 游戏初始化
    → 需要调用 ai_service.register_ai_unit(unit, behavior_tree)
        → managed_unit_count += 1
```

**关键问题**: 谁负责注册Axis单位?

### 6.3 修复方案

**6.3.1 在部署完成后自动注册敌方单位**

文件: `src/pycc2/services/game_loop.py` 或 `deployment_manager.py`

```python
def _register_ai_units(self):
    """Register all non-player units with the AI service."""
    if self.ai_service is None:
        return
    
    player_faction = self.state.player_faction  # e.g., Faction.ALLIES
    from pycc2.domain.ai.behavior_tree import InfantryBehaviorTree
    
    for unit in self.state.units:
        if unit.faction != player_faction and unit.is_alive:
            # 为每个敌方单位创建行为树
            tree = InfantryBehaviorTree(unit)
            self.ai_service.register_ai_unit(unit, tree)
            logger.info(f"Registered AI unit: {unit.name} [{unit.id}]")
```

**调用时机**: 
- `start_deployment()` 完成后（进入战斗阶段前）
- 或在 `_start_battle_phase()` 中

**6.3.2 AIService.tick() 行为验证**

确保 tick() 产生有效的 TacticIntent:

```python
# ai_service.py - tick() 方法
def tick(self, dt, game_map, all_units) -> list[TacticIntent]:
    intents = []
    for unit_id, tree in self._unit_trees.items():
        unit = self._unit_entities[unit_id]
        blackboard = self._blackboards[unit_id]
        
        # 更新感知（检测敌人）
        self._perception.update(unit, all_units, game_map, blackboard)
        
        # 执行行为树
        status = tree.tick(blackboard)
        if status == NodeStatus.SUCCESS:
            intent = blackboard.chosen_intent
            if intent:
                intents.append(intent)
    
    return intents
```

**6.3.3 感知系统确认**

PerceptionSystem 必须能检测到:
- 视野内的敌人（通过LOS系统）
- 射程内的敌人（通过武器射程）
- 威胁优先级（距离/血量/武器类型）

**验证方法**:
1. 部署 Allied 单位和 Axis 单位，间距在武器射程内
2. 进入战斗阶段后等待几个tick（AI有更新间隔）
3. 确认Axis单位转向并攻击Allied单位
4. 检查日志: `[AI service] Registered AI unit: ...`

---

## 七、修复优先级与依赖关系

```
P5: AI注册（最关键，影响核心玩法）
 └─ 依赖: 无，可立即修复
 
P4: 右键命令（影响操作）
 └─ 依赖: P1（HUD面板包含命令栏参考）
 
P3: 单位视觉（影响体验）
 └─ 依赖: 无，可独立修复
 
P2: Save/Load（影响留存）
 └─ 依赖: P5（需要能正常游戏才能验证存档）
 
P1: HUD显示（影响信息获取）
 └─ 依赖: 无，主要是验证工作
```

**推荐修复顺序**: P5 → P3 → P4 → P1 → P2

---

## 八、验收标准

每个修复完成后，必须通过以下E2E验收:

| # | 验收场景 | 通过标准 |
|---|---------|---------|
| E2E-1 | 完整游戏流程 | 主菜单→遭遇战→部署→战斗→HUD显示→单位可见 |
| E2E-2 | 敌军AI响应 | Axis单位在射程内自动转向并攻击Allied单位 |
| E2E-3 | 右键命令 | 右键→选Move→单位移动到目标点；右键→选Attack→发起攻击 |
| E2E-4 | 存档读档 | F5存档→F9读档→状态完全恢复 |
| E2E-5 | 单位识别 | 不同阵营单位颜色不同；单位大小适中(≥20px)；有朝向指示 |

---

## 九、风险与注意事项

1. **回归防护**: 每个修复后运行完整测试套件（3642+测试）
2. **性能监控**: AI注册和感知系统每tick运行，注意O(n²)复杂度
3. **Sprite资源**: 如添加PNG sprite，需确认 `data/sprites/` 目录结构
4. **Dummy驱动限制**: SDL_VIDEODRIVER=dummy 下无法测试真实鼠标交互，需真机验证P4
