# PyCC2 交互设计规范 **v1.6** (P5)

> **文档版本**: v1.6 | **日期**: 2026-05-19 | **基于产品版本**: v0.6-p4w2

## 1. 屏幕布局 (1280x720 精确像素坐标)

### 1.1 整体布局架构

```
┌─────────────────────────────────────────────────────────────┐
│ TOP_BAR (0, 0, 1280, 28)                                   │
│ Mission: Tutorial | Day 1 06:30 | ⏸ Pause | ☰ Menu       │
├──────────┬─────────────────────────────────┬───────────────┤
│ LEFT     │                                 │ RIGHT         │
│ PANEL    │      GAME VIEWPORT              │ PANEL         │
│ (0,28,   │     (200,28, 879,569)          │ (1080,28,     │
│ 200,617) │                                 │ 200,618)      │
│          │                                 │               │
│ 单位信息  │        Camera 视口区域           │ Squad 列表     │
│ 面板     │                                 │ 面板          │
│          ├─────────────────────────────────┤               │
│          │ COMMAND BAR                     │               │
│          │ (200,597,1080,48)              │               │
│          │ [Move][Attack][Stop][Smoke][Defend]             │
│          └─────────────────────────────────┴───────────────┤
│                                              MINIMAP        │
│                                         (1140,580,140,140) │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 区域详细规格

#### TOP_BAR - 顶部状态栏

| 属性 | 值 |
|------|-----|
| **位置** | (x=0, y=0) |
| **尺寸** | 宽度=1280px, 高度=28px |
| **背景色** | #2C3E50 (深蓝灰) |
| **文字颜色** | #ECF0F1 (浅白) |
| **字体** | Consolas, 12px |
| **元素布局** | 左: 任务名 \| 中: 游戏时间 \| 右: 控制按钮 |

**内部元素：**

```
[任务名: Tutorial Mission]  [Day 1 06:30]  [⏸ Pause]  [☰ Menu]
 ↑ 左对齐 x=10              ↑ 居中          ↑ 右对齐     ↑ 最右 x=1250
```

**交互行为：**
- **Pause按钮**: 切换游戏暂停/继续，显示图标变化 ⏸/▶
- **Menu按钮**: 打开主菜单（设置/退出/存档）

---

#### LEFT_PANEL - 左侧单位信息面板

| 属性 | 值 |
|------|-----|
| **位置** | (x=0, y=28) |
| **尺寸** | 宽度=200px, 高度=589px (617-28) |
| **背景色** | #34495E (深灰蓝) |
| **边框** | 右边框 1px solid #7F8C8D |
| **内边距** | padding: 8px |

**内部子分区（从上到下）：**

```
┌─────────────────────┐
│ 📋 单位基本信息      │ ← 高度: 120px
│ Name: Rifle Squad   │
│ Type: Infantry      │
│ HP: ████░░ 85/100   │
│ Morale: █████ 90    │
├─────────────────────┤
│ 🔫 武器信息          │ ← 高度: 100px
│ M1 Garand (8/8)     │
│ Range: 400m         │
│ Acc: 75%            │
├─────────────────────┤
│ 📊 状态效果          │ ← 高度: 80px
│ • In Cover (+5%)    │
│ • Suppressed (-10%) │
├─────────────────────┤
│ 👥 班组成员          │ ← 自适应高度
│ [■] [■] [■] [□] ... │
└─────────────────────┘
```

**子分区详细：**

1. **单位基本信息区** (y=36, height=120)
   - 单位名称（粗体, 14px）
   - 单位类型标签（灰色, 11px）
   - HP条（绿色渐变, 背景红色）
   - 士气条（蓝色渐变）

2. **武器信息区** (y=164, height=100)
   - 武器名称 + 弹药计数
   - 有效射程
   - 当前精度百分比
   - 重装填进度条（如正在装填）

3. **状态效果区** (y=272, height=80)
   - 正面效果（绿色文字）
   - 负面效果（红色文字）
   - 持续时间倒计时

4. **班组成员区** (y=360, height=auto)
   - 成员头像网格（每个16x16）
   - 存活: ■ 绿色 / 阵亡: □ 灰色
   - 悬停显示成员详情tooltip

---

#### GAME_VIEWPORT - 游戏视口

| 属性 | 值 |
|------|-----|
| **位置** | (x=200, y=28) |
| **尺寸** | 宽度=679px, 高度=541px (879-200, 569-28) |
| **背景色** | 动态（根据地形渲染） |
| **功能** | Camera投影的游戏世界渲染区域 |

**视口特性：**
- 支持Camera平移和缩放
- 渲染地形、单位、特效、UI覆盖层
- 支持拖拽选择框
- 显示射击线、移动路径等反馈

---

#### RIGHT_PANEL - 右侧Squad列表面板

| 属性 | 值 |
|------|-----|
| **位置** | (x=1080, y=栏) |
| **尺寸** | 宽度=200px, 高度=590px (618-28) |
| **背景色** | #34495E (深灰蓝) |
| **边框** | 左边框 1px solid #7F8C8D |
| **内边距** | padding: 8px |

**列表项结构：**

```
┌─────────────────────┐
│ SQUAD LIST          │ 标题行
├─────────────────────┤
│ ▶ Alpha Squad       │ 可展开
│   [Rifle] 10人 85HP │ 详情
├─────────────────────┤
│ ▶ Bravo Squad       │
│   [MG] 4人 72HP     │
├─────────────────────┤
│ ▶ Charlie Squad     │
│   [AT] 3人 60HP     │
└─────────────────────┘
```

**交互特性：**
- 点击小队名称 → 选中该队 → Game Viewport聚焦
- 展开/折叠箭头 (▶/▼)
- 双击 → Camera聚焦到该队位置
- 右键 → 上下文菜单（命令/解散）

---

#### COMMAND_BAR - 命令栏

| 属性 | 值 |
|------|-----|
| **位置** | (x=200, y=597) |
| **尺寸** | 宽度=880px, 高度=48px (1080-200) |
| **背景色** | #2C3E50 (深蓝灰) |
| **上边框** | 1px solid #7F8C8D |
| **按钮间距** | 16px |
| **按钮大小** | 100x36 px |

**5个命令按钮：**

```
┌─────────────────────────────────────────────────────────────┐
│  [🚶 Move]  [🎯 Attack]  [✋ Stop]  [💨 Smoke]  [🛡 Defend]  │
│    ↑            ↑           ↑          ↑           ↑        │
│  x=220       x=340       x=460     x=580       x=700       │
│  快捷键:M     快捷键:A     快捷键:S   快捷键:K    快捷键:D    │
└─────────────────────────────────────────────────────────────┘
```

**按钮状态样式：**

| 状态 | 背景色 | 文字色 | 边框 |
|------|--------|--------|------|
| Normal | #3498DB | #FFFFFF | 无 |
| Hover | #2980B9 | #FFFFFF | 2px solid #5DADE2 |
| Active/Selected | #1ABC9C | #FFFFFF | 2px solid #48C9B0 |
| Disabled | #7F8C8D | #BDC3C7 | 无 |
| Cooldown | #E67E22 | #FFFFFF | 进度环 |

---

#### MINIMAP - 小地图

| 属性 | 值 |
|------|-----|
| **位置** | (x=1140, y=580) |
| **尺寸** | 宽度=140px, 高度=140px |
| **背景色** | #1A1A1A (近黑) |
| **边框** | 2px solid #7F8C8D |
| **透明度** | 地形半透明渲染 |

**小地图功能：**
- 显示完整地图缩略图（按比例缩小）
- 显示所有单位位置（盟军蓝点/德军红点）
- 显示当前Camera视野矩形框（白色半透明）
- 点击 → Camera跳转到对应位置
- 滚轮 → 缩放（可选）

---

### 1.3 布局响应式规则

虽然固定分辨率 1280×720，但需考虑以下情况：

| 场景 | 处理策略 |
|------|----------|
| 全屏模式 | 保持逻辑分辨率，黑边或拉伸 |
| UI缩放 | 支持0.8x~1.25x缩放因子 |
| 面板隐藏 | LEFT/RIGHT PANEL可收起，GAME_VIEWPORT扩展 |
| 命令栏折叠 | 小屏幕时命令改为图标+tooltip |

---

## 2. 几何原型视觉规范表 (20+元素)

### 2.1 单位视觉原型

#### 步兵单位 (Infantry Units)

| 单位类型 | 形状 | 尺寸 | 盟军颜色 | 德军颜色 | 描边 |
|----------|------|------|----------|----------|------|
| 步兵班 (rifle squad) | Circle | r=12px | #4A90D9 (蓝) | #D94A4A (红) | 2px 白 |
| 机枪组 (MG team) | Circle | r=14px | #4A90D9 (蓝) | #D94A4A (红) | 2px 白 |
| 反坦克组 (AT team) | Circle | r=11px | #5BA3EC (浅蓝) | #E05A5A (浅红) | 2px 白 |
| 指挥官 (Commander) | Diamond | r=10px | #FFD700 (金) | #FF4500 (橙红) | 2px 黑 |
| 迫击炮组 (Mortar) | Triangle | r=13px | #4A90D9 (蓝) | #D94A4A (红) | 2px 白 |

**视觉示例代码（伪代码）：**

```python
# 步兵班绘制
def draw_infantry_squad(screen, pos, faction):
    color = ALLIES_COLOR if faction == "allies" else AXIS_COLOR
    pygame.draw.circle(screen, color, pos, radius=12)
    pygame.draw.circle(screen, WHITE, pos, radius=12, width=2)

# 指挥官绘制
def draw_commander(screen, pos, faction):
    color = COMMANDER_COLOR if faction == "allies" else AXIS_COMMANDER_COLOR
    points = [
        (pos[0], pos[1] - 10),      # 上顶点
        (pos[0] + 10, pos[1]),       # 右顶点
        (pos[0], pos[1] + 10),      # 下顶点
        (pos[0] - 10, pos[1])       # 左顶点
    ]
    pygame.draw.polygon(screen, color, points)
    pygame.draw.polygon(screen, BLACK, points, width=2)
```

---

#### 载具单位 (Vehicle Units)

| 载具类型 | 形状 | 尺寸 | 方向指示 | 颜色方案 |
|----------|------|------|----------|----------|
| 轻型载具 (Light Vehicle) | Rectangle | 24×16px | 前端箭头 | 盟军: #5DADE2 / 德军: #EC7063 |
| 中型载具 (Medium Vehicle) | Rectangle | 28×18px | 前端炮管 | 盟军: #3498DB / 德军: #E74C3C |
| 重型载具 (Heavy Vehicle) | Rectangle | 32×20px | 前端主炮 | 盟军: #2874A6 / 德军: #C0392B |

**载具方向示意：**

```
轻型载具 (朝右):
  ┌──────────┐
  │          │→
  └──────────┘

中型载具 (朝右):
  ┌────────────┐
  │            │→●
  └────────────┘
  (● = 炮管)
```

---

### 2.2 选择与高亮系统

#### 选中框 (Selection Box)

| 属性 | 规范值 |
|------|--------|
| **形状** | 虚线圆 (dashed circle) |
| **半径** | r=18px (包围单位) |
| **颜色** | #FFFFFF (白色) |
| **线宽** | 2px |
| **虚线样式** | dash=8px, gap=4px |
| **动画** | 闪烁周期 300ms (α: 1.0↔0.6) |
| **层级** | 在单位之上，特效之下 |

**多选选择框 (Drag Selection):**

| 属性 | 规范值 |
|------|--------|
| **形状** | 矩形虚线框 |
| **颜色** | #00FFFF (青色) + α=0.5填充 |
| **线宽** | 1px |
| **最小尺寸** | 10×10px 才触发选择 |
| **包含判定** | 单位中心点在框内 |

---

### 2.3 移动与路径反馈

#### 移动路径 (Movement Path)

| 属性 | 规范值 |
|------|--------|
| **线条样式** | 虚线 (dashed line) |
| **颜色** | #F1C40F (黄色) |
| **线宽** | 2px |
| **节点标记** | 小圆点 r=3px, #F39C12 |
| **目标标记** | 圆圈 r=6px, #E67E22 (空心) |
| **预计时间** | 目标旁显示 ticks 数 |

**路径点序列可视化：**

```
起点 ● - - - ○ - - - ○ - - - ○ - - - ⊙ 目标
     (当前位置)  (途经点)  (途经点)  (目的地)
     黄虚线连接，每段显示移动代价
```

---

### 2.4 战斗视觉效果

#### 射击线 (Fire Line)

| 类型 | 颜色 | 线宽 | 样式 | 持续时间 |
|------|------|------|------|----------|
| **命中** (Hit) | #FF0000 (红) | 2px | 实线 (solid) | 200ms |
| **未中** (Miss) | #FF6666 (浅红) | 1px | 虚线 (dash) | 150ms |
| **压制射击** (Suppressing) | #FFA500 (橙) | 2px | 点划线 | 500ms |

**弹道轨迹 (Bullet Trajectory):**

| 属性 | 规范值 |
|------|--------|
| **形状** | 小圆点序列 |
| **半径** | r=2px |
| **颜色** | #FFD700 (金黄) |
| **速度** | 16px/frame |
| **持续时间** | 3-5帧 (取决于距离) |
| **淡出** | α线性衰减至0 |

---

### 2.5 地形渲染规范

#### 基础地形颜色表

| 地形类型 | 颜色代码 | RGB | 说明 |
|----------|----------|-----|------|
| OPEN (开阔地) | #8BC34A | (139, 195, 74) | 浅绿，草地感 |
| ROAD (道路) | #C4A06A | (196, 160, 106) | 土黄，泥土路 |
| GRASS (草地) | #7CB342 | (124, 179, 66) | 深绿，茂密草 |
| WOODS (林地) | #2E7D32 | (46, 125, 50) | 深绿，森林 |
| BUILDING_ENTERABLE (可进入建筑) | #757575 | (117, 117, 117) | 中灰，可交互 |
| BUILDING_SOLID (实心建筑) | #424242 | (66, 66, 66) | 深灰，不可通行 |
| WATER (水域) | #1E88E5 | (30, 136, 229) | 蓝色，水面 |
| HEDGE (树篱) | #558B2F | (85, 139, 47) | 橄榄绿 |
| WALL (墙壁) | #616161 | (97, 97, 97) | 灰色砖墙 |
| ROUGH (粗糙地形) | #A1887F | (161, 127, 127) | 棕褐色 |
| SHALLOW (浅水) | #4FC3F7 | (79, 195, 247) | 浅蓝色 |
| BRIDGE (桥梁) | #8D6E63 | (141, 110, 99) | 棕色木桥 |

**地形纹理细节：**

```python
TERRAIN_TEXTURES = {
    TerrainType.OPEN: {
        "base_color": "#8BC34A",
        "pattern": "noise_grass",
        "variation": 0.1,  # 颜色随机变化范围
        "detail": None
    },
    TerrainType.WOODS: {
        "base_color": "#2E7D32",
        "pattern": "tree_scatter",
        "density": 0.3,  # 树木密度
        "detail": "tree_icons_8x8"
    },
    TerrainType.BUILDING_SOLID: {
        "base_color": "#424242",
        "pattern": "brick_grid",
        "outline": True,
        "roof_color": "#616161"
    }
}
```

---

### 2.6 战争迷雾 (Fog of War)

| FoW状态 | 颜色 | 透明度(α) | 渲染方式 | 行为 |
|---------|------|-----------|----------|------|
| **未探索** (Unexplored) | #000000 (纯黑) | α=0.85 | 完全不透明 | 不显示任何内容 |
| **已探索** (Explored) | #000000 (纯黑) | α=0.55 | 半透明遮罩 | 显示静态快照，不更新 |
| **可见** (Visible) | 无 | α=0.0 | 完全透明 | 正常渲染，实时更新 |

**FoW边缘过渡效果：**

```
可见区域 ──平滑过渡(32px)── 已探索区域 ──硬边界── 未探索区域
  α=0.0                      α=0.55                 α=0.85
```

**FoW更新规则：**
- 每 tick 更新一次（跟随UPS频率）
- 使用圆形视野（vision_range为半径）
- 建筑/高地可延伸视野
- 低洼地缩减视野

---

### 2.7 特效系统 (Visual Effects)

#### HitFlash (命中闪光)

| 属性 | 值 |
|------|-----|
| **触发条件** | 单位被命中 |
| **效果** | 单位整体闪白 |
| **颜色** | #FFFFFF (纯白) |
| **持续时间** | 1帧 (~33.3ms @ 30UPS) |
| **混合模式** | Additive (叠加) |
| **实现** | 临时将单位color设为white，下一帧恢复 |

#### DeathShrink (死亡收缩)

| 属性 | 值 |
|------|-----|
| **触发条件** | 单位HP≤0死亡 |
| **效果** | 单位图形缩小至消失 |
| **收缩时长** | 0.5秒 (15 ticks @ 30UPS) |
| **动画曲线** | ease-out (先快后慢) |
| **最终状态** | scale=0, alpha=0 |
| **后续动作** | 从渲染列表移除 |

**时间轴：**

```
Tick 0:  scale=1.0, alpha=1.0  (正常)
Tick 2:  scale=0.8, alpha=0.8  (开始缩小)
Tick 5:  scale=0.5, alpha=0.5  (快速缩小)
Tick 8:  scale=0.2, alpha=0.2  (接近消失)
Tick 10: scale=0.0, alpha=0.0  (完全消失)
```

#### Explosion (爆炸效果)

| 属性 | 值 |
|------|-----|
| **触发条件** | 迫击炮命中/车辆摧毁 |
| **核心颜色** | #FF6600 (橙色) |
| **外圈颜色** | #FFCC00 (黄色) |
| **持续时间** | 0.3秒 (6 ticks) |
| **最大半径** | r=30px |
| **帧序列** | 3帧关键帧动画 |

**爆炸帧序列：**

```
Frame 1 (tick 0):  内圈 r=5, 外圈 r=15  (初始爆发)
Frame 2 (tick 2):  内圈 r=15, 外圈 r=25 (扩散)
Frame 3 (tick 4):  内圈 r=8, 外圈 r=30  (消散)
Frame 4 (tick 6):  完全消失
```

#### PanicIcon (恐慌图标)

| 属性 | 值 |
|------|-----|
| **触发条件** | 单位士气≤30 进入panic状态 |
| **图标** | 红色感叹号 "!" |
| **颜色** | #FF0000 (鲜红) |
| **字体大小** | Bold 20px |
| **位置** | 单位正上方偏移 (0, -20) |
| **动画** | 上下跳动 ±3px, 周期300ms |
| **持续显示** | 直到panic状态结束 |

**Panic状态视觉链：**

```
Normal (士气>50)
    ↓ 士气降至≤20
Panic Active
    ├── 单位颜色变暗 (saturation -50%)
    ├── PanicIcon "!" 显示并跳动
    └── 单位无法响应命令 (灰色半透明)
    ↓ 士气恢复>35
Recovering
    ├── PanicIcon 消失
    └── 颜色渐变恢复 (1秒)
```

---

### 2.8 UI元素汇总表

| 元素ID | 名称 | 类型 | 默认可见 | Z-index | 备注 |
|--------|------|------|----------|---------|------|
| UI-001 | TOP_BAR | 固定面板 | Always | 100 | 最高层 |
| UI-002 | LEFT_PANEL | 固定面板 | OnSelect | 90 | 选中有单位时显示 |
| UI-003 | RIGHT_PANEL | 固定面板 | Always | 90 | Squad列表 |
| UI-004 | GAME_VIEWPORT | 渲染区域 | Always | 0 | 游戏世界 |
| UI-005 | COMMAND_BAR | 固定面板 | OnSelect | 95 | 选中后可用 |
| UI-006 | MINIMAP | 小地图 | Toggle | 85 | 可开关 |
| UI-007 | SelectionBox | 临时效果 | OnSelect | 80 | 选中框 |
| UI-008 | DragSelection | 临时效果 | OnDrag | 75 | 框选 |
| UI-009 | MovementPath | 临时效果 | OnMove | 70 | 移动路径 |
| UI-010 | FireLine | 临时效果 | OnAttack | 65 | 射击线 |
| UI-011 | BulletTrail | 临时效果 | OnShoot | 60 | 弹道 |
| UI-012 | HitFlash | 特效 | OnHit | 55 | 命中闪光 |
| UI-013 | DeathShrink | 特效 | OnDeath | 50 | 死亡动画 |
| UI-014 | Explosion | 特效 | OnExplode | 45 | 爆炸 |
| UI-015 | PanicIcon | 状态指示 | OnPanic | 40 | 恐慌标志 |
| UI-016 | FogOfWar | 环境效果 | Always | 30 | 战争迷雾 |
| UI-017 | Tooltip | 悬浮提示 | OnHover | 110 | 信息提示 |
| UI-018 | DebugOverlay | 调试层 | DevMode | 120 | 调试信息 |
| UI-019 | ContextMenu | 右键菜单 | OnRightClick | 105 | 上下文菜单 |
| UI-020 | Notification | 通知横幅 | OnEvent | 115 | 事件通知 |

---

## 3. 操作反馈清单 (鼠标/键盘/事件驱动)

### 3.1 鼠标操作

#### HOVER (悬停)

| 目标对象 | 反馈效果 | 触发延迟 | Tooltip内容 |
|----------|----------|----------|-------------|
| 单位 | 高亮边框（金色2px） | 0ms | 名称/类型/HP简述 |
| 地形tile | 半透明高亮 | 0ms | 地形类型/移动代价 |
| UI按钮 | 颜色变亮 + 轻微放大 | 0ms | 按钮功能描述 |
| Minimap区域 | 对应Game Viewport区域高亮 | 0ms | 坐标信息 |
| Squad列表项 | 背景色加深 | 0ms | 小队详细信息 |

**Cursor样式映射：**

| Context | Cursor Shape | 说明 |
|---------|--------------|------|
| Default | Arrow (→) | 默认状态 |
| Over Unit | Hand (👆) | 可选中单位 |
| Over Terrain | Crosshair (+) | 可交互地形 |
| Over Button | Pointer (👆) | 可点击按钮 |
| Moving (dragging) | Closed Hand (✊) | 拖拽中 |
| Attacking | Target (◎) | 攻击模式下 |
| Forbidden | Forbidden (🚫) | 不可操作区域 |

---

#### CLICK_SELECT (左键单击选择)

**操作流程：**

```
鼠标左键按下 (MOUSEBUTTONDOWN)
    ↓
检测点击位置是否在单位碰撞箱内
    ↓
├── 是 → 选中该单位
│   ├── 清除之前的选择
│   ├── 设置新选择 (SelectionBox显示)
│   ├── 更新LEFT_PANEL内容
│   ├── 启用COMMAND_BAR
│   └── 播放选中音效 (如果启用)
│
└── 否 → 检查是否在空地
    ├── 是 → 取消当前选择 (Deselect)
    │   ├── 隐藏SelectionBox
    │   ├── 清空LEFT_PANEL
    │   └── 禁用COMMAND_BAR
    └── 否 → 忽略 (可能在UI上)
```

**多选支持 (Shift+Click):**
- Shift + 左键 → 添加到选择集（不取消之前选择）
- Ctrl + 左键 → 从选择集移除
- 最大选择数: 12 个单位

---

#### RIGHT_CLICK_MOVE (右键移动)

**前提条件:** 已选中单位 + 未处于攻击命令模式

**操作流程：**

```
鼠标右键按下 (MOUSEBUTTONDOWN, button=RIGHT)
    ↓
获取点击的世界坐标 (screen_to_world转换)
    ↓
验证目标位置:
    ├── 是否在地图范围内? ✅/❌
    ├── 是否可通过地形? ✅/❌
    └── 是否无其他单位阻挡? ✅/❌ (允许重叠或排队)
    ↓
全部通过:
    ├── 计算路径 (PathFinder.A*)
    ├── 显示移动路径预览 (MovementPath)
    ├── 发送MoveCommand到EventBus
    └── 单位开始移动
```

**视觉反馈时间线：**

```
T+0ms:   右键点击 → 显示目标标记 (⊙)
T+50ms:  路径计算完成 → 绘制路径虚线
T+100ms: 单位收到命令 → 开始转向目标方向
T+200ms: 开始沿路径移动 → 每tick更新位置
T+End:   到达目标 → 清除路径显示, 播放到达音效
```

---

#### RIGHT_CLICK_ATTACK (右键攻击)

**前提条件:** 已选中单位 + 目标是敌方单位

**操作流程：**

```
右键点击敌方单位
    ↓
验证攻击可行性:
    ├── 是否在武器射程内? ✅/❌
    ├── 是否有LOS (视线)? ✅/❌
    ├── 是否有弹药? ✅/❌
    └── 目标是否存活? ✅/❌
    ↓
可行:
    ├── 发送AttackCommand
    ├── 显示红色射击线预览 (短暂)
    ├── 单位转向目标
    └── 开始攻击循环 (按ROF)
```

**攻击模式切换:**
- 点击COMMAND_BAR的[Attack]按钮 → 进入攻击模式
- 攻击模式下光标变为Target (◎)
- 此时左键也可指定攻击目标（不仅限右键）
- ESC 或 右键空地 → 退出攻击模式

---

#### DRAG_SELECTION (框选)

**操作流程：**

```
鼠标左键按下 (在空地)
    ↓
记录起始点 (start_pos)
    ↓
鼠标移动 (MOUSEMOTION, button held)
    ↓
实时更新选择框:
    ├── 计算当前矩形区域 (start_pos → current_pos)
    ├── 绘制DragSelection框 (青色半透明)
    └── 实时高亮框内单位 (半透明白)
    ↓
鼠标左键释放 (MOUSEBUTTONUP)
    ↓
收集框内所有单位中心点:
    ├── 符合条件的加入选择集
    ├── 更新SelectionBox (多选时显示多个框)
    ├── 更新LEFT_PANEL (显示多单位摘要)
    └── 播放框选音效
```

**框选约束：**

| 约束 | 值 | 说明 |
|------|-----|------|
| 最小框尺寸 | 10×10px | 太小的框忽略 |
| 最大框尺寸 | 无限制 | 可全屏框选 |
| 包含判定 | 中心点在框内 | 不是完全包含 |
| 跨阵营框选 | 允许 | 但只执行有效命令 |
| 框选延迟 | 100ms后才开始 | 防止误触单击 |

---

### 3.2 键盘快捷键

#### PAUSE (暂停)

| 按键 | 功能 | 反馈 | 全局? |
|------|------|------|-------|
| SPACE / P | 切换暂停状态 | TOP_BAR显示⏸/▶, 游戏冻结/恢复 | ✅ Yes |
| ESC | 取消当前操作/退出菜单 | 取消选择框/关闭菜单 | ✅ Yes |

**暂停时的UI状态：**
- 游戏世界冻结（不再更新）
- UI仍然可交互
- 显示半透明遮罩 α=0.3 (黑色)
- 中央显示 "PAUSED" 文字 (48px, 白色)
- 底部提示 "Press SPACE to resume"

---

#### DEBUG_OVERLAY (调试覆盖层)

| 按键组合 | 功能 | 切换循环 |
|----------|------|----------|
| F11 (或 ` + Shift+D) | 切换Debug Overlay | Off → Level 1 → Level 2 → Level 3 → Off |
| ` (反引号) | 快速切换 Level 1 | On/Off toggle |

**Debug Overlay 详细定义见第4节**

---

#### CAMERA_RESET (相机重置)

| 按键 | 功能 | 行为 |
|------|------|------|
| HOME | 重置相机到默认位置 | 回到地图中心, zoom=1.0 |
| END | 重置相机到选中单位 | 如果有选中, 聚焦到该单位 |

---

#### FOCUS_SELECTED (聚焦选中)

| 按键 | 功能 | 行为 |
|------|------|------|
| F | 聚焦当前选中的单位 | Camera平滑移动到单位位置, 居中显示 |
| F (双击) | 聚焦 + 缩放到最佳视角 | 自动调整zoom使单位清晰可见 |

**平滑移动算法：**

```python
def focus_selected(camera, target_pos, duration_ticks=15):
    start_pos = camera.position.copy()
    end_pos = target_pos - viewport_center

    for t in range(duration_ticks):
        progress = t / duration_ticks
        eased = ease_out_cubic(progress)  # 缓出曲线
        camera.position = lerp(start_pos, end_pos, eased)
        yield  # 等待下一个tick
```

---

#### TOGGLE_MINIMAP (切换小地图)

| 按键 | 功能 | 反馈 |
|------|------|------|
| M | 显示/隐藏Minimap | MINIMAP区域出现/消失, 布局调整 |
| Tab | 临时显示Minimap (按住显示) | 松开后隐藏 |

---

#### EDGE_SCROLLING (边缘滚动)

**激活条件：** 鼠标在Game Viewport边缘区域

| 边缘区域 | 宽度 | 触发滚动方向 | 滚动速度 |
|----------|------|-------------|----------|
| Top edge | 8px | 向上 (Y-) | 4 px/tick |
| Bottom edge | 8px | 向下 (Y+) | 4 px/tick |
| Left edge | 8px | 向左 (X-) | 4 px/tick |
| Right edge | 8px | 向右 (X+) | 4 px/tick |
| Corner (角) | 8px | 对角线方向 | √(4²+4²) ≈ 5.66 px/tick |

**配置选项（可在engine.toml中调整）：**

```toml
[camera]
edge_scroll_enabled = true
edge_scroll_zone = 8          # 边缘触发区宽度(px)
edge_scroll_speed = 4.0       # 滚动速度(px/tick)
edge_scroll_enabled_in_pause = false  # 暂停时不滚动
```

---

### 3.3 事件驱动反馈

#### 通用事件反馈清单

| 事件类别 | 触发时机 | 视觉反馈 | 音效反馈 | UI反馈 | 持续时间 |
|----------|----------|----------|----------|--------|----------|
| **Unit Selected** | 左键点击单位 | SelectionBox出现 | UI_Click | LEFT_PANEL更新 | 直到取消选择 |
| **Unit Deselected** | 点击空地/ESC | SelectionBox消失 | - | LEFT_PANEL清空 | 即时 |
| **Move Command Issued** | 右键空地 | MovementPath显示 | Command_Move | - | 路径显示直到到达 |
| **Attack Command Issued** | 右键敌军 | FireLine预览 | Command_Attack | - | 200ms |
| **Weapon Fired** | 开火时刻 | BulletTrail + MuzzleFlash | Weapon_Fire (按武器类型) | 弹药数-1 | 100-200ms |
| **Hit Confirmed** | 命中判定成功 | HitFlash + DamageNumber飘字 | Impact_Hit | HP条减少 | HitFlash: 1帧 |
| **Miss Occurred** | 命中判定失败 | MissIndicator (地面标记) | Impact_Miss | - | 300ms |
| **Unit Killed** | HP≤0 | DeathShrink + DeathRipple | Unit_Death | 从列表移除 | 0.5s |
| **Morale Change** | 士气值变化 | MoraleBar动画 | - | Morale数值更新 | 300ms渐变 |
| **Panic Start** | 士气≤20 | PanicIcon出现 + 单位变暗 | Alarm_Panic | 状态标签"PANIC" | 持续 |
| **Panic End** | 声气恢复>35 | PanicIcon消失 + 颜色恢复 | Recovery | 状态清除 | 1s过渡 |
| **Reload Start** | 弹药耗尽 | WeaponBar显示进度 | Reload_Start | 状态"RELOADING" | 按reload_time |
| **Reload Complete** | 装填完毕 | 进度条满 + 闪光 | Reload_Complete | 弹药数重置 | 200ms |
| **Suppression Applied** | 受到压制 fire | ScreenShake(轻微) + SuppressionOverlay | - | SuppressionBar增加 | 500ms |
| **Objective Captured** | 占领目标达成 | ObjectiveFlag变色 + ParticleCelebration | Victory_Fanfare | Notification横幅 | 3s |
| **Mission Complete** | 所有目标完成 | VictoryScreen全屏 | Victory_Theme | 结果统计面板 | 手动关闭 |
| **Mission Failed** | 失败条件触发 | FailureScreen (红色调) | Failure_Sting | 失败原因面板 | 手动关闭 |
| **Save Completed** | 存档成功 | SaveIcon闪烁 | UI_Save | Toast通知"Saved" | 1s |
| **Load Completed** | 读档完成 | FadeIn过渡 | - | 状态恢复 | 0.5s |

---

## 4. Debug Overlay 三级设计

### 4.1 Level 1: 基础调试信息

**适用场景:** 性能监控、基础状态查看

**显示内容：**

| 信息项 | 位置 | 格式 | 更新频率 | 说明 |
|--------|------|------|----------|------|
| FPS (帧率) | 左上角 (10, 40) | "FPS: 60" | 每帧 | 渲染帧率 |
| UPS (逻辑更新率) | 左上角 (10, 58) | "UPS: 20" | 每tick | 逻辑更新频率 |
| Tile坐标 (鼠标) | 左上角 (10, 76) | "Tile: (15, 23)" | 鼠标移动时 | 当前鼠标指向的地图格子 |
| 存活统计 | 左上角 (10, 94) | "Allies: 12 | Axis: 8" | 每tick | 双方存活单位数 |
| Game Tick | 左上角 (10, 112) | "Tick: 12345" | 每tick | 游戏时间戳 |
| Memory Usage | 左上角 (10, 130) | "Mem: 145MB" | 每5s | 内存占用估算 |

**渲染代码示例：**

```python
def render_debug_level1(screen, font, game_state):
    y_offset = 40
    lines = [
        f"FPS: {game_state.fps:.1f}",
        f"UPS: {game_state.ups}",
        f"Tile: ({game_state.hover_tile.x}, {game_state.hover_tile.y})",
        f"Allies: {game_state.allies_alive} | Axis: {game_state.axis_alive}",
        f"Tick: {game_state.tick}",
        f"Mem: {get_memory_usage()}MB"
    ]

    for i, line in enumerate(lines):
        text_surface = font.render(line, True, (255, 255, 0))  # 黄色
        screen.blit(text_surface, (10, y_offset + i * 18))
```

**视觉样式：**
- 字体: Monospace (Consolas/Courier), 12px
- 颜色: #FFFF00 (黄色) 半透明背景 rgba(0,0,0,0.6)
- 背景: 圆角矩形面板, padding 5px

---

### 4.2 Level 2: 详细调试信息

**在Level 1基础上增加以下内容：**

| 信息分类 | 具体内容 | 显示方式 | 说明 |
|----------|----------|----------|------|
| **单位状态标签** | 每个单位头顶显示: ID/HP/Morale/Status | 文字标签 | 小字号, 带背景 |
| **网格线** | 在地形上绘制网格线 | 半透明线条 | 便于定位 |
| **A*路径** | 显示单位的A*搜索过程 | 彩色路径 | open=closed=不同颜色 |
| **碰撞箱** | 显示所有单位的精确碰撞区域 | 矩形框 | 红色空心 |
| **视线射线** | 从单位发射到各方向的射线 | 细线 | 用于调试LOS |
| **视野范围** | 显示单位视野圆形区域 | 圆形轮廓 | 半透明填充 |

**新增渲染函数：**

```python
def render_debug_level2(screen, font, units, pathfinder):
    # 单位状态标签
    for unit in units:
        label = f"{unit.id[:4]} HP:{unit.hp} M:{unit.morale}"
        draw_text_with_bg(screen, unit.screen_pos + (0, -20),
                         label, font, (0, 255, 0), (0, 0, 0, 180))

    # 网格线
    for x in range(0, map_width, tile_size):
        pygame.draw.line(screen, (100, 100, 100), (x, 0), (x, map_height), 1)
    for y in range(0, map_height, tile_size):
        pygame.draw.line(screen, (100, 100, 100), (0, y), (map_width, y), 1)

    # A*路径可视化 (如果有正在计算的路径)
    if pathfinder.debug_path:
        draw_astar_debug(screen, pathfinder.debug_path)

    # 碰撞箱
    for unit in units:
        rect = unit.get_collision_rect()
        pygame.draw.rect(screen, (255, 0, 0), rect, 1)
```

**性能影响评估：**
- 额外CPU开销: ~5-8% (取决于单位数量)
- 额外GPU开销: ~10-15% (额外draw calls)
- 建议: 仅在开发/调试时开启

---

### 4.3 Level 3: 性能分析器

**在Level 1+2基础上增加高级诊断工具：**

| 分析模块 | 内容 | 可视化形式 | 更新频率 |
|----------|------|------------|----------|
| **子系统耗时柱状图** | 各子系统每tick耗时(ms) | 实时柱状图 | 每tick |
| **内存使用详情** | 各模块内存占用 | 饼图/数值 | 每5s |
| **事件队列积压** | EventBus待处理事件数量 | 数字+警告阈值 | 每tick |
| **路径查找统计** | A*调用次数/平均耗时/最长耗时 | 统计面板 | 每秒聚合 |
| **渲染管线分析** | Draw call数量/三角形数/纹理切换 | 实时计数器 | 每帧 |
| **实体数量追踪** | 各类实体当前数量 | 表格 | 每tick |
| **GC/GC pauses** | Python垃圾回收暂停时间和频率 | 时间线图表 | GC时 |

**柱状图渲染示例：**

```python
import pygame.gfxdraw

def render_performance_bars(screen, subsystem_times, x, y, width=300, max_height=100):
    subsystems = list(subsystems_times.keys())
    max_time = max(subsystem_times.values()) if subsystems_times else 1.0
    bar_width = width // len(subsystems) - 2

    for i, (name, time_ms) in enumerate(subsystems_times.items()):
        bar_height = int((time_ms / max_time) * max_height)
        bar_x = x + i * (bar_width + 2)
        bar_y = y + max_height - bar_height

        color = get_subsystem_color(name)  # 每个子系统不同颜色
        pygame.draw.rect(screen, color, (bar_x, bar_y, bar_width, bar_height))
        pygame.draw.rect(screen, (255, 255, 255), (bar_x, bar_y, bar_width, bar_height), 1)

        # 标签
        font_small = pygame.font.SysFont('consolas', 10)
        label = font_small.render(f"{name[:4]}:{time_ms:.1f}ms", True, (255, 255, 255))
        screen.blit(label, (bar_x, bar_y - 15))

# 子系统颜色映射
SUBSYSTEM_COLORS = {
    'input': (255, 100, 100),      # 红 - 输入处理
    'update': (100, 255, 100),      # 绿 - 逻辑更新
    'pathfinding': (100, 100, 255), # 蓝 - 寻路
    'combat': (255, 255, 100),      # 黄 - 战斗
    'render': (255, 100, 255),      # 品红 - 渲染
    'ai': (100, 255, 255),          # 青 - AI决策
    'fog': (255, 180, 100),         # 橙 - 迷雾
}
```

**内存饼图示例：**

```python
def render_memory_pie(screen, memory_breakdown, center, radius=80):
    total = sum(memory_breakdown.values())
    start_angle = 0

    for module, mem_mb in memory_breakdown.items():
        angle_span = (mem_mb / total) * 360
        end_angle = start_angle + angle_span
        color = get_module_color(module)

        pygame.draw.arc(screen, color,
                       (center[0]-radius, center[1]-radius, radius*2, radius*2),
                       math.radians(start_angle), math.radians(end_angle), 3)

        # 标签 (在扇区中间角度)
        mid_angle = math.radians(start_angle + angle_span / 2)
        label_radius = radius * 0.7
        label_x = center[0] + int(label_radius * math.cos(mid_angle))
        label_y = center[1] + int(label_radius * math.sin(mid_angle))

        font_tiny = pygame.font.SysFont('consolas', 9)
        label = font_tiny.render(f"{module[:6]}:{mem_mb}MB", True, (255, 255, 255))
        screen.blit(label, (label_x - 20, label_y - 5))

        start_angle = end_angle
```

**Level 3 性能开销：**
- CPU: +15-25% (大量文本渲染和绘图)
- 仅建议在严重性能问题时短时间使用

---

### 4.4 Debug Overlay 切换逻辑

```python
class DebugOverlayManager:
    def __init__(self):
        self.level = 0  # 0=Off, 1, 2, 3
        self.enabled = False

    def toggle(self):
        self.level = (self.level + 1) % 4
        self.enabled = self.level > 0
        return self.level

    def set_level(self, new_level):
        self.level = max(0, min(3, new_level))
        self.enabled = self.level > 0

    def render(self, screen, fonts, game_state):
        if not self.enabled:
            return

        if self.level >= 1:
            self._render_level1(screen, fonts['mono'], game_state)
        if self.level >= 2:
            self._render_level2(screen, fonts['mono'], game_state)
        if self.level >= 3:
            self._render_level3(screen, fonts['mono'], game_state)
```

---

## 5. Camera 控制方案

### 5.1 键盘控制

| 按键 | 功能 | 移动量/帧 | 说明 |
|------|------|------------|------|
| W / ↑ | 向上移动 | -8px Y | 视口向上平移 |
| S / ↓ | 向下移动 | +8px Y | 视口向下平移 |
| A / ← | 向左移动 | -8px X | 视口向左平移 |
| D / → | 向右移动 | +8px X | 视口向右平移 |
| W+A / W+← | 左上对角 | (-8, -8) | 同时按下两个方向 |
| W+D / W+→ | 右上对角 | (+8, -8) | - |
| S+A / S+← | 左下对角 | (-8, +8) | - |
| S+D / S+→ | 右下对角 | (+8, +8) | - |

**速度配置：**

```toml
[camera]
keyboard_speed = 8.0          # 键盘移动速度 (pixels per tick)
keyboard_diagonal_factor = 0.707  # 对角线归一化因子 (√2/2)
```

---

### 5.2 鼠标滚轮缩放

| 操作 | 效果 | 步进值 | 范围限制 |
|------|------|--------|----------|
| Scroll Up | 放大 (Zoom In) | ×0.25 | 最大 3.0x |
| Scroll Down | 缩小 (Zoom Out) | ÷0.25 | 最小 0.5x |
| Ctrl+Scroll Up | 微调放大 | ×0.1 | 同上 |
| Ctrl+Scroll Down | 微调缩小 | ÷0.1 | 同上 |

**缩放步进表：**

| 当前缩放 | Scroll Up | Scroll Down |
|----------|-----------|-------------|
| 0.50x | → 0.75x | (最小,不变) |
| 0.75x | → 1.00x | → 0.50x |
| 1.00x | → 1.25x | → 0.75x |
| 1.25x | → 1.50x | → 1.00x |
| 1.50x | → 1.75x | → 1.25x |
| 1.75x | → 2.00x | → 1.50x |
| 2.00x | → 2.25x | → 1.75x |
| 2.25x | → 2.50x | → 2.00x |
| 2.50x | → 2.75x | → 2.25x |
| 2.75x | → 3.00x | → 2.50x |
| 3.00x | (最大,不变) | → 2.75x |

**缩放锚点（Zoom Anchor）：**
- 以鼠标指针位置为中心进行缩放
- 公式: `new_camera_pos = mouse_world_pos - (mouse_screen_pos - viewport_center) / new_zoom`

---

### 5.3 相机特殊控制

| 按键 | 功能 | 行为描述 |
|------|------|----------|
| HOME | 重置相机 | 回到地图中心, zoom=1.0, 平滑过渡 0.5s |
| F | 聚焦选中单位 | 平滑移动相机使选中单位居中 |
| 双击F | 聚焦+最佳缩放 | 自动调整zoom使单位及其周围环境可见 |
| Middle Mouse Button | 拖拽相机 | 按住中键拖拽来平移相机 (类似RTS游戏) |

**HOME重置详细流程：**

```python
def reset_camera(camera, map_config, duration_ticks=10):
    target_position = Vec2(
        (map_config.width * TILE_SIZE) / 2,
        (map_config.height * TILE_SIZE) / 2
    )
    target_zoom = 1.0

    start_pos = camera.position.copy()
    start_zoom = camera.zoom

    for tick in range(duration_ticks):
        progress = tick / duration_ticks
        eased = ease_in_out_quad(progress)  # 缓入缓出

        camera.position = lerp(start_pos, target_position, eased)
        camera.zoom = lerp(start_zoom, target_zoom, eased)
        yield
```

**F聚焦算法：**

```python
def focus_on_unit(camera, unit, viewport_size, smoothness=0.15):
    target_pos = unit.position - (viewport_size / 2)

    # 平滑插值 (lerp with smoothing factor)
    camera.position += (target_pos - camera.position) * smoothness

    # 可选: 自动调整zoom以适应
    if auto_adjust_zoom:
        optimal_zoom = calculate_optimal_zoom(unit, viewport_size)
        camera.zoom += (optimal_zoom - camera.zoom) * smoothness
```

---

### 5.4 Edge Scrolling (边缘滚动)

详见第3.2节，此处补充实现细节：

```python
class EdgeScroller:
    ZONE_WIDTH = 8  # pixels from edge
    SCROLL_SPEED = 4.0  # pixels per tick

    def update(self, mouse_pos, viewport_rect, camera):
        if not self.enabled:
            return

        scroll_x, scroll_y = 0, 0
        mx, my = mouse_pos

        # Check each edge
        if mx < viewport_rect.x + self.ZONE_WIDTH:
            scroll_x = -self.SCROLL_SPEED
        elif mx > viewport_rect.x + viewport_rect.width - self.ZONE_WIDTH:
            scroll_x = self.SCROLL_SPEED

        if my < viewport_rect.y + self.ZONE_WIDTH:
            scroll_y = -self.SCROLL_SPEED
        elif my > viewport_rect.y + viewport_rect.height - self.ZONE_WIDTH:
            scroll_y = self.SCROLL_SPEED

        # Apply diagonal normalization
        if scroll_x != 0 and scroll_y != 0:
            factor = 0.7071  # √2/2
            scroll_x *= factor
            scroll_y *= factor

        camera.position += Vec2(scroll_x, scroll_y)
```

---

### 5.5 View Matrix 投影公式

Camera使用正交投影（Orthographic Projection）将世界坐标转换为屏幕坐标。

**数学公式：**

$$
\begin{aligned}
\text{screen}_x &= (\text{world}_x - \text{camera}_x) \times \text{zoom} + \frac{\text{viewport\_width}}{2} \\
\text{screen}_y &= (\text{world}_y - \text{camera}_y) \times \text{zoom} + \frac{\text{viewport\_height}}{2}
\end{aligned}
$$

**逆变换（屏幕→世界）：**

$$
\begin{aligned}
\text{world}_x &= \frac{\text{screen}_x - \frac{\text{viewport\_width}}{2}}{\text{zoom}} + \text{camera}_x \\
\text{world}_y &= \frac{\text{screen}_y - \frac{\text{viewport\_height}}{2}}{\text{zoom}} + \text{camera}_y
\end{aligned}
$$

**Python实现：**

```python
class Camera:
    def __init__(self, viewport_size: tuple):
        self.position = Vec2(0, 0)
        self.zoom = 1.0
        self.viewport_width, self.viewport_height = viewport_size

    def world_to_screen(self, world_pos: Vec2) -> tuple:
        sx = (world_pos.x - self.position.x) * self.zoom + self.viewport_width / 2
        sy = (world_pos.y - self.position.y) * self.zoom + self.viewport_height / 2
        return (int(sx), int(sy))

    def screen_to_world(self, screen_pos: tuple) -> Vec2:
        wx = (screen_pos[0] - self.viewport_width / 2) / self.zoom + self.position.x
        wy = (screen_pos[1] - self.viewport_height / 2) / self.zoom + self.position.y
        return Vec2(wx, wy)

    def get_viewport_bounds(self) -> tuple:
        """返回当前视口在世界坐标系中的边界"""
        top_left = self.screen_to_world((0, 0))
        bottom_right = self.screen_to_world((self.viewport_width, self.viewport_height))
        return (top_left, bottom_right)
```

---

### 5.6 边界约束算法

防止Camera移出地图范围。

```python
def clamp_camera(camera, map_width_pixels, map_height_pixels):
    """
    约束Camera位置使其不会显示地图外的空白区域。
    当地图小于视口时，居中显示地图。
    """

    # 计算可视范围（世界坐标）
    visible_width = camera.viewport_width / camera.zoom
    visible_height = camera.viewport_height / camera.zoom

    min_x, min_y = 0, 0
    max_x = map_width_pixels - visible_width
    max_y = map_height_pixels - visible_height

    if max_x < min_x:
        # 地图比视口窄，水平居中
        camera.position.x = map_width_pixels / 2
    else:
        camera.position.x = clamp(camera.position.x, min_x, max_x)

    if max_y < min_y:
        # 地图比视口矮，垂直居中
        camera.position.y = map_height_pixels / 2
    else:
        camera.position.y = clamp(camera.position.y, min_y, max_y)
```

**特殊情况处理：**

| 场景 | 处理策略 | 示例 |
|------|----------|------|
| 地图大于视口 | 正常边界约束 | 256×256地图, 679×541视口 |
| 地图小于视口 | 居中显示, 禁止平移 | 16×16教学地图 |
| 地图等于视口 | 固定位置, 禁止缩放<1x | - |
| 极端缩放(3x) | 可能看到地图外, 需要加黑边 | 可选: letterboxing |

---

## 附录 A: 颜色参考表

### 主色调 (Primary Colors)

| 用途 | Hex | RGB | 说明 |
|------|-----|-----|------|
| 盟军主色 | #4A90D9 | (74, 144, 217) | 蓝色系 |
| 德军主色 | #D94A4A | (217, 74, 74) | 红色系 |
| 背景深色 | #2C3E50 | (44, 62, 80) | 面板背景 |
| 背景次深 | #34495E | (52, 73, 94) | 次级面板 |
| 强调色 | #F1C40F | (241, 196, 15) | 黄色（警告/路径） |
| 成功色 | #2ECC71 | (46, 204, 113) | 绿色（确认/友军） |
| 危险色 | #E74C3C | (231, 76, 60) | 红色（危险/敌军） |
| 信息色 | #3498DB | (52, 152, 219) | 蓝色（信息/链接） |

### 状态颜色 (Status Colors)

| 状态 | Hex | 应用场景 |
|------|-----|----------|
| 正常 | #2ECC71 | HP>70%, 士气>60% |
| 警告 | #F39C12 | HP 30-70%, 士气 30-60% |
| 危险 | #E74C3C | HP<30%, 士气<30% |
| 恐慌 | #C0392B | 士气≤20%, Panic状态 |
| 选中 | #F1C40F | 当前选中单位 |
| 禁用 | #95A5A6 | 不可用的按钮/命令 |

## 附录 B: 字体规范

| 用途 | 字体族 | 大小 | 字重 | 颜色 |
|------|--------|------|------|------|
| 标题 | Consolas/Bold | 16px | Bold | #ECF0F1 |
| 面板标题 | Consolas/Semibold | 14px | Semibold | #ECF0F1 |
| 正文 | Consolas/Regular | 12px | Regular | #BDC3C7 |
| 小字 | Consolas/Regular | 10px | Regular | #95A5A6 |
| Debug | Courier New/Mono | 12px | Regular | #FFFF00 |
| 数字/数据 | Consolas/Bold | 12px | Bold | #FFFFFF |
| 按钮 | Consolas/Semibold | 13px | Semibold | #FFFFFF |
| 通知横幅 | Consolas/Bold | 18px | Bold | #FFFFFF |

## 附录 C: 图标资源清单

| 图标ID | 名称 | 尺寸 | 格式 | 用途 |
|--------|------|------|------|------|
| ICON-MOVE | Move/移动 | 24×24 | PNG/SVG | Move按钮 |
| ICON-ATTACK | Attack/攻击 | 24×24 | PNG/SVG | Attack按钮 |
| ICON-STOP | Stop/停止 | 24×24 | PNG/SVG | Stop按钮 |
| ICON-SMOKE | Smoke/烟雾 | 24×24 | PNG/SVG | Smoke按钮 |
| ICON-DEFEND | Defend/防御 | 24×24 | PNG/SVG | Defend按钮 |
| ICON-PAUSE | Pause/暂停 | 16×16 | PNG/SVG | Pause状态 |
| ICON-PLAY | Play/播放 | 16×16 | PNG/SVG | Resume状态 |
| ICON-MENU | Menu/菜单 | 16×16 | PNG/SVG | Menu按钮 |
| ICON-SETTINGS | Settings/设置 | 16×16 | PNG/SVG | 设置入口 |
| ICON-SAVE | Save/保存 | 16×16 | PNG/SVG | 存档按钮 |
| ICON-LOAD | Load/读取 | 16×16 | PNG/SVG | 读档按钮 |

## 附录 D: 版本历史

| 版本 | 日期 | 作者 | 变更内容 |
|------|------|------|----------|
| v1.0 | 2024-01 | PyCC2 Team | 初始版本，定义完整UI布局和视觉规范 |
| v1.1 | 2026-05-18 | UI Designer | Consensus修订: UPS引用修正为30, Panic阈值统一为30, Smoke键K |
| v1.2 | 2025-05-18 | UI Designer | P3-Fix文档同步: 版本号对齐v0.4-fix1, 无视觉规范变更 |

## 附录 E: 相关文档

- [数据设计文档](./DATA_DESIGN.md) - Pydantic模型和数据文件格式
- [安全评审报告](./SECURITY.md) - 安全威胁分析与缓解措施
- [测试计划](./TEST_PLAN.md) - 测试策略与覆盖率目标
