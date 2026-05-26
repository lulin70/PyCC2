# PyCC2 全局系统性修复方案

> 核心原则：对照CC2原版，尽可能接近。画面、布局、机制、操作全面对齐CC2，95%接近度之前不考虑超越。
> 制定日期：2026-05-23
> 最后更新：2026-05-23（Phase 1-4已完成）
> 基于对10个核心文件的全面代码审读

---

## 一、全局问题总览

经过对渲染管线、游戏逻辑、UI布局三大系统的全面代码审读，发现以下**根因级问题**：

| 维度 | CC2原版 | 当前PyCC2 | 差距程度 |
|------|---------|-----------|----------|
| 画面 | 俯视45°等距、像素级写实、小而清晰的单位 | 纯平顶视、纯色方块地形、几何形状单位 | 70%差距 |
| 布局 | 底部统一面板（单位列表+详情+小地图+命令栏） | 面板结构存在但数据流断裂、面板点击不路由 | 40%差距 |
| 机制 | 7命令全部可操作、移动/攻击/防御完整链路 | Move/Attack部分工作、Smoke/Defend/Fast/Sneak链路断裂 | 60%差距 |
| 操作 | 点击选中→右键命令→单位执行→视觉反馈 | 选中后数据流断裂、命令回调不完整、无视觉确认 | 50%差距 |

---

## 二、修复方案（按依赖关系排序）

### 修复项 #1：统一渲染管线 — 消除双渲染器冲突

**问题根因：**
- `EnhancedRenderer` 和 `SpriteRenderer` 存在职责重叠和冲突
- `EnhancedRenderer.render()` 调用 `_draw_simple_terrain()`（纯色方块），完全绕过了 `ProceduralTextureGenerator` 的纹理生成
- `EnhancedRenderer._draw_units()` 临时替换 `SpriteRenderer._screen` 为 `_offscreen`，hack式集成
- `SpriteRenderer` 有完整的纹理/精灵缓存系统但被 `EnhancedRenderer` 的纯色方案覆盖

**修复方案：**
1. `EnhancedRenderer.render()` 中将 `_draw_simple_terrain()` 替换为 `_draw_enhanced_terrain()`（已有但被禁用）
2. 恢复纹理渲染管线：`ProceduralTextureGenerator` → `_get_cached_texture()` → `_draw_enhanced_terrain()`
3. 将 `SpriteRenderer` 作为 `EnhancedRenderer` 的子模块正式集成，而非临时替换 `_screen`
4. 消除 `_draw_units()` 中的 hack（临时替换 `_screen`）

**涉及文件：**
- `src/pycc2/presentation/rendering/enhanced_renderer.py`（主修改）
- `src/pycc2/presentation/rendering/sprite_renderer.py`（接口调整）

**依赖关系：** 无前置依赖，是所有画面修复的基础

**验证方法：**
- 启动游戏，地形应显示纹理而非纯色方块
- 单位应显示精灵而非几何形状
- 无闪烁/崩溃

---

### 修复项 #2：地形渲染 — CC2写实纹理 + 45°等距投影

**问题根因：**
- `ProceduralTextureGenerator` 已实现12种地形纹理，但被 `_draw_simple_terrain()` 绕过
- `PixelArtist3D.create_terrain_tile_isometric()` 已实现菱形等距瓦片，但未被任何渲染器调用
- 当前地形是32×32正方形纯色方块，CC2原版是等距菱形带纹理
- `Vec2` 的 `TILE_SIZE` 硬编码为16，与渲染器的 `TILE_SIZE=32` 不一致

**修复方案：**
1. 恢复 `_draw_enhanced_terrain()` 为默认地形渲染方法
2. 集成 `PixelArtist3D.create_terrain_tile_isometric()` 生成等距菱形瓦片
3. 统一 `TILE_SIZE`：`Vec2.TILE_SIZE` 和渲染器 `TILE_SIZE` 必须一致（建议32）
4. 地形边缘平滑（`_apply_terrain_edge_smoothing`）需优化性能后重新启用
5. 高度光照（`_apply_height_lighting`）需与等距投影配合

**涉及文件：**
- `src/pycc2/presentation/rendering/enhanced_renderer.py`
- `src/pycc2/presentation/rendering/pixel_artist_3d.py`
- `src/pycc2/domain/value_objects/vec2.py`（TILE_SIZE统一）

**依赖关系：** 依赖 #1（统一渲染管线）

**验证方法：**
- 地形显示等距菱形瓦片（非正方形）
- 不同地形类型有不同纹理（草地有草叶、道路有车辙、水有波纹）
- 相邻地形有自然过渡

---

### 修复项 #3：单位渲染 — CC2写实像素精灵

**问题根因：**
- `PixelArtist3D` 已实现24×24步兵精灵和36×36坦克精灵，但 `SpriteRenderer._create_unit_sprite()` 的缓存key与实际生成不匹配
- `SpriteRenderer._draw_sprite_unit()` 中缓存查找逻辑尝试多种key格式（`base_key`, `base_key_24`, `d0`, `d0_24`），说明key系统混乱
- `AssetLoader` 尝试加载PNG但路径映射不完整，fallback到程序化生成时key不匹配
- 单位渲染大小 `SPRITE_SIZE=24` 但缩放逻辑未考虑等距投影

**修复方案：**
1. 统一精灵缓存key格式：`{faction}_{unit_type}_d{direction}`（无后缀）
2. `SpriteRenderer._create_unit_sprite()` 优先调用 `PixelArtist3D`，统一返回格式
3. `AssetLoader` 的PNG加载作为可选增强，不影响核心渲染
4. 单位在等距地图上的定位需考虑菱形瓦片的偏移
5. 选中光环改为CC2风格的黄色方框（非圆形脉冲）

**涉及文件：**
- `src/pycc2/presentation/rendering/sprite_renderer.py`（缓存key统一）
- `src/pycc2/presentation/rendering/pixel_artist_3d.py`（精灵质量微调）
- `src/pycc2/presentation/rendering/asset_loader.py`（路径映射修复）

**依赖关系：** 依赖 #1（统一渲染管线）

**验证方法：**
- 步兵显示为24×24像素级写实人形（非圆形/六边形）
- 坦克显示为36×36像素级写实车辆
- 不同方向显示不同朝向的精灵
- 选中时显示CC2风格黄色方框

---

### 修复项 #4：底部面板数据流 — Unit→Panel→Screen完整链路

**问题根因：**
- `CC2BottomPanel` 的数据更新依赖 `game_loop._render_hud()` 每帧调用 `set_friendly_units()` 和 `set_selected_unit()`
- `set_friendly_units()` 每帧重建排序列表，性能浪费
- 面板点击事件（`handle_click()`）返回字符串（如 `"command:move"`），但 `game_loop` 中通过回调机制处理，两套系统并存
- `_on_unit_select` 回调直接修改 `game_state.selected_unit_ids`，但未同步到 `interaction_controller._selected_ids`
- 面板渲染时 `minimap` 参数可能为 `None`，导致小地图区域空白

**修复方案：**
1. `CC2BottomPanel` 增加增量更新：只在单位列表变化时重建，非每帧
2. 统一选择状态：面板选择→`game_state.selected_unit_ids`→`interaction_controller._selected_ids` 三者同步
3. 面板命令回调直接调用 `interaction_controller.set_mode()`，而非通过字符串路由
4. 确保小地图始终初始化并传入面板
5. 面板布局比例需根据屏幕宽度动态计算（当前硬编码宽度在小屏幕上溢出）

**涉及文件：**
- `src/pycc2/presentation/rendering/cc2_bottom_panel.py`（增量更新+布局自适应）
- `src/pycc2/services/game_loop.py`（数据流同步）
- `src/pycc2/presentation/input/interaction_controller.py`（选择状态同步）

**依赖关系：** 无画面依赖，可与 #1-#3 并行

**验证方法：**
- 点击面板单位列表，地图上对应单位被选中（黄色高亮）
- 选中地图单位，面板自动滚动到该单位并高亮
- 面板详情区显示正确的HP/士气/弹药/班组成员
- 小地图显示地图缩略图和视口框

---

### 修复项 #5：命令系统完整链路 — 7命令全部可操作

**问题根因：**
- **Move**：`execute_move()` 设置 `unit.set_move_target(tile)`，但 `tile` 坐标来自 `target.x // 32`，而 `Vec2.TILE_SIZE=16`，坐标计算错误
- **Fast**：`on_fast()` 调用 `interaction_controller.set_mode(InteractionMode.MOVE, fast=True)`，但 `set_mode()` 不接受 `fast`/`sneak` 参数
- **Sneak**：同Fast，`set_mode()` 签名不匹配
- **Attack**：部分工作，但 `attack_line_system` 的 `confirm_attack()` 后未触发 `combat_director` 的实际攻击逻辑
- **Smoke**：`on_smoke()` 发布 `PlayerCommand(command="deploy_smoke")`，但 `combat_director` 不处理此命令
- **Defend**：`on_defend()` 发布 `PlayerCommand(command="defend")`，但 `combat_director.handle_player_command()` 不识别 "defend"
- **Cancel**：`on_cancel()` 清空选择，但未取消 `interaction_controller` 的当前模式（如ATTACK模式的攻击线）

**修复方案：**
1. **Move坐标修复**：`execute_move()` 中使用 `target.x // Vec2.TILE_SIZE` 替代硬编码 `32`
2. **Fast/Sneak模式扩展**：`InteractionMode` 增加 `MOVE_FAST` 和 `MOVE_SNEAK`，或 `set_mode()` 增加 `speed` 参数
3. **Attack链路补全**：`confirm_attack()` 后调用 `combat_director.execute_attack()`
4. **Smoke实现**：`combat_director.handle_player_command()` 增加 "deploy_smoke" 处理，在目标位置创建烟雾效果
5. **Defend实现**：`combat_director.handle_player_command()` 增加 "defend" 处理，设置单位防御状态
6. **Cancel完善**：`on_cancel()` 增加 `interaction_controller.set_mode(InteractionMode.SELECT)` 和 `attack_line.cancel()`

**涉及文件：**
- `src/pycc2/presentation/input/interaction_controller.py`（模式扩展）
- `src/pycc2/services/game_loop.py`（命令回调修复）
- `src/pycc2/services/combat_director.py`（Smoke/Defend命令处理）
- `src/pycc2/domain/entities/unit.py`（防御状态）

**依赖关系：** 依赖 #4（面板数据流）

**验证方法：**
- Move：点击Move按钮→点击地图→单位移动到目标位置
- Fast：点击Fast按钮→点击地图→单位快速移动（速度×1.5）
- Sneak：点击Sneak按钮→点击地图→单位慢速移动（速度×0.5，隐蔽加成）
- Attack：点击Attack按钮→点击敌方单位→攻击线显示→确认攻击→伤害计算
- Smoke：选中单位→点击Smoke→目标区域出现烟雾效果
- Defend：选中单位→点击Defend→单位进入防御状态（不可移动，防御加成）
- Cancel：任何模式下点击Cancel→回到选择模式，清除攻击线

---

### 修复项 #6：操作反馈链路 — 事件→状态→渲染完整闭环

**问题根因：**
- 选中单位后，`game_state.selected_unit_ids` 更新了，但 `interaction_controller._selected_ids` 未同步
- `input_router.route_input()` 中左键点击调用 `interaction_controller.handle_left_click()`，返回新选择集，直接覆盖 `game_state.selected_unit_ids`，但面板的 `_selected_unit_id` 依赖 `_render_hud()` 同步
- 右键命令（`handle_right_click()`）直接发布事件到 `event_bus`，但 `combat_director` 订阅的是 `PlayerCommand` 类型事件，而右键发布的是原始dict
- 移动命令的视觉反馈缺失：`unit.set_move_target()` 后无路径预览线

**修复方案：**
1. **选择状态同步**：`game_state.selected_unit_ids` 变更时，同步更新 `interaction_controller._selected_ids` 和 `cc2_panel._selected_unit_id`
2. **右键命令统一**：`handle_right_click()` 发布 `PlayerCommand` 类型事件（非dict）
3. **移动路径预览**：选中单位+MOVE模式时，鼠标悬停位置显示路径预览线（利用现有 `path_preview.py`）
4. **命令执行确认**：每个命令执行后播放音效+视觉闪烁（利用现有 `sound_system` 和 `sprite_renderer.spawn_hit_flash()`）
5. **攻击结果反馈**：攻击命中时显示伤害数字（利用现有 `spawn_damage_number()`）

**涉及文件：**
- `src/pycc2/presentation/input/input_router.py`（选择同步）
- `src/pycc2/presentation/input/interaction_controller.py`（事件类型统一）
- `src/pycc2/services/game_loop.py`（反馈触发）
- `src/pycc2/presentation/rendering/path_preview.py`（路径预览启用）

**依赖关系：** 依赖 #4（面板数据流）和 #5（命令系统）

**验证方法：**
- 点击单位→面板立即更新→地图上单位高亮
- 右键点击空地→单位开始移动→路径线显示
- 右键点击敌方→攻击线显示→确认→伤害数字弹出
- 每个命令执行后有音效反馈

---

### 修复项 #7：移动系统修复 — 坐标一致性与平滑移动

**问题根因：**
- `Vec2.TILE_SIZE = 16`，但渲染器 `TILE_SIZE = 32`，`interaction_controller.screen_to_tile()` 硬编码 `// 32`
- `PositionComponent.pixel_position` 使用 `Vec2.TILE_SIZE`（16）计算，导致像素坐标是实际渲染坐标的一半
- `Unit.update_movement()` 的速度计算 `base_speed * speed_modifier * dt * 0.15`，`0.15` 是经验值，移动可能过快或过慢
- `Unit.set_move_target()` 设置目标后，`state_machine` 转换到 `MOVING`，但 `update_movement()` 的 `move_to_tile()` 直接跳格（`int(dx/dist*speed)` 为0时不动）

**修复方案：**
1. **统一TILE_SIZE**：`Vec2.TILE_SIZE` 改为32，或所有坐标计算统一使用渲染器的 `TILE_SIZE`
2. **平滑移动**：`update_movement()` 使用浮点数插值而非整数跳格，`pixel_offset` 用于子格平滑
3. **移动速度校准**：参考CC2原版速度（步兵约2格/秒，坦克约3格/秒），调整 `base_speed` 和缩放因子
4. **朝向更新**：移动时自动更新 `facing_rad`（利用现有 `position.set_facing_toward()`）

**涉及文件：**
- `src/pycc2/domain/value_objects/vec2.py`（TILE_SIZE统一）
- `src/pycc2/domain/components/position_component.py`（平滑移动）
- `src/pycc2/domain/entities/unit.py`（速度校准+朝向更新）
- `src/pycc2/presentation/input/interaction_controller.py`（坐标一致性）

**依赖关系：** 依赖 #1（渲染管线统一TILE_SIZE）和 #5（Move命令修复）

**验证方法：**
- 点击Move→点击地图→单位平滑移动到目标（非瞬移）
- 移动过程中单位朝向跟随移动方向
- 移动速度与CC2原版一致
- 不同地形对速度的影响正确

---

### 修复项 #8：攻击系统修复 — 完整战斗闭环

**问题根因：**
- `AttackLineSystem` 评估攻击可行性（射程/视线），但 `confirm_attack()` 后未触发实际伤害计算
- `combat_director.execute_attack()` 存在但未被攻击确认流程调用
- 攻击结果（命中/未命中/伤害）未反馈到UI（无伤害数字、无闪白效果）
- `interaction_controller.handle_right_click()` 发布的攻击事件是dict格式，与 `combat_director` 订阅的 `PlayerCommand` 类型不匹配

**修复方案：**
1. **攻击确认→执行**：`confirm_attack()` 后调用 `combat_director.execute_attack(attacker, target)`
2. **攻击结果→视觉反馈**：`combat_director` 处理攻击后调用 `sprite_renderer.spawn_hit_flash()` 和 `spawn_damage_number()`
3. **事件类型统一**：所有攻击事件使用 `PlayerCommand` 类型
4. **攻击冷却**：攻击后单位进入 `RELOADING` 状态，防止连续攻击

**涉及文件：**
- `src/pycc2/presentation/input/interaction_controller.py`（攻击确认流程）
- `src/pycc2/services/combat_director.py`（攻击执行+反馈）
- `src/pycc2/services/game_loop.py`（攻击回调连接）

**依赖关系：** 依赖 #5（命令系统）和 #6（操作反馈）

**验证方法：**
- Attack模式→点击敌方单位→攻击线变绿→确认→伤害数字弹出→敌方HP减少
- 超出射程→攻击线变红→无法攻击
- 攻击后单位短暂进入装填状态

---

## 三、修复顺序（按依赖关系）

```
Phase 1 - 基础设施（无画面依赖，可并行）✅ 已完成
├── #4 面板数据流修复 ✅
│
Phase 2 - 渲染管线（依赖Phase 1的面板集成）✅ 已完成
├── #1 统一渲染管线 ✅
├── #2 地形渲染（45°等距+纹理）✅
├── #3 单位渲染（像素精灵）✅
│
Phase 3 - 机制修复（依赖Phase 1的数据流）✅ 已完成
├── #5 命令系统（7命令完整链路）✅
├── #7 移动系统（坐标一致性+平滑移动）✅
│
Phase 4 - 操作闭环（依赖Phase 2+3）✅ 已完成
├── #6 操作反馈链路 ✅
├── #8 攻击系统修复 ✅
```

**建议执行顺序：** ~~#4 → #1 → #2 → #3 → #5 → #7 → #6 → #8~~ 全部已完成

---

## 四、每个修复项的详细验证清单

### #1 统一渲染管线 ✅ 已完成
- [x] 地形显示纹理（非纯色方块）
- [x] 单位显示精灵（非几何形状）
- [x] 无闪烁/崩溃
- [x] 帧率≥30fps

### #2 地形渲染 ✅ 已完成
- [x] 地形瓦片为等距菱形
- [x] 12种地形类型各有独特纹理
- [x] 相邻地形有自然过渡
- [x] 高度差有光照变化

### #3 单位渲染 ✅ 已完成
- [x] 步兵24×24像素级写实精灵
- [x] 坦克36×36像素级写实精灵
- [x] 8方向朝向正确
- [x] 选中时CC2风格黄色方框

### #4 面板数据流 ✅ 已完成
- [x] 面板单位列表显示所有友军
- [x] 点击列表项→地图选中对应单位
- [x] 地图选中单位→面板自动高亮
- [x] 详情区显示HP/士气/弹药/班组
- [x] 小地图正常显示

### #5 命令系统 ✅ 已完成
- [x] Move：点击→移动到目标
- [x] Fast：点击→快速移动
- [x] Sneak：点击→隐蔽移动
- [x] Attack：点击→攻击线→确认→伤害
- [x] Smoke：点击→部署烟雾
- [x] Defend：点击→防御状态
- [x] Cancel：点击→清除选择和模式

### #6 操作反馈 ✅ 已完成
- [x] 选中即时高亮
- [x] 移动路径预览
- [x] 攻击线颜色反馈（绿/红/橙）
- [x] 伤害数字弹出
- [x] 命令音效

### #7 移动系统 ✅ 已完成
- [x] TILE_SIZE统一（32）
- [x] 平滑移动（非跳格）
- [x] 速度与CC2一致
- [x] 朝向跟随移动方向

### #8 攻击系统 ✅ 已完成
- [x] 攻击确认→伤害计算
- [x] 伤害数字反馈
- [x] 射程限制正确
- [x] 攻击后装填状态

---

## 五、集成测试方案

### 5.1 冒烟测试（每个修复项完成后）
```bash
cd /Users/lin/trae_projects/PyCC2
python -m pytest tests/ -x -q --tb=short
```

### 5.2 E2E测试（模拟真实用户操作）
1. **启动游戏** → 新游戏菜单正常显示
2. **选择阵营+地图** → 进入部署阶段
3. **部署单位** → 拖放单位到友方区域
4. **开始战斗** → 进入战斗阶段
5. **选中单位** → 面板显示详情
6. **执行Move** → 单位移动到目标
7. **执行Attack** → 攻击线→确认→伤害
8. **执行Defend** → 单位进入防御
9. **执行Smoke** → 烟雾效果出现
10. **执行Cancel** → 清除选择

### 5.3 视觉回归测试
- 截图对比：每个修复项前后截图对比
- 关键场景：部署界面、战斗界面、面板展开/收起
- 性能基准：帧率不低于30fps，内存不超过500MB

### 5.4 CC2原版对比测试
- 并排运行CC2原版截图与PyCC2截图
- 对比维度：地形纹理、单位外观、面板布局、操作流程
- 目标：95%视觉接近度

---

## 六、风险与注意事项

1. **TILE_SIZE统一是高风险操作**：`Vec2.TILE_SIZE` 从16改为32会影响所有坐标计算，必须全面测试
2. **等距投影改造影响范围大**：从正方形瓦片改为菱形瓦片，地图渲染、单位定位、点击检测全部需要调整
3. **渲染管线切换可能引入闪烁**：从 `_draw_simple_terrain()` 切换到 `_draw_enhanced_terrain()` 需确保offscreen buffer正确使用
4. **命令系统扩展需向后兼容**：`InteractionMode` 增加新模式不能破坏现有SELECT/MOVE/ATTACK逻辑
5. **每个修复项必须独立可验证**：如果某个修复项导致回归，能快速定位和回滚
