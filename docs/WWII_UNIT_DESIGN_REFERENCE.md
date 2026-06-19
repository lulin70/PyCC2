# PyCC2 · WWII Unit Design Reference

> 导出日期：2026-06-19  
> 设计文件：`PyCC2-WWII-Unit-Design.ardot`（Ardot 画布）  
> 适用范围：PyCC2 项目 Market Garden 主题剧本

---

## 目录结构

```
docs/assets/unit-sprites/
├── PALETTE_REFERENCE.svg          # 配色参考卡
├── allies/
│   ├── rifleman-standing.svg      # 盟军步枪手 · 站姿
│   ├── rifleman-kneeling.svg      # 盟军步枪手 · 跪姿
│   ├── rifleman-prone.svg         # 盟军步枪手 · 匍匐（静态）
│   ├── rifleman-prone-f0.svg      # 匍匐爬行动画 · 帧0
│   ├── rifleman-prone-f1.svg      # 匍匐爬行动画 · 帧1
│   ├── rifleman-prone-f2.svg      # 匍匐爬行动画 · 帧2
│   ├── rifleman-prone-f3.svg      # 匍匐爬行动画 · 帧3
│   └── mg-deployed.svg            # 盟军机枪手 · 部署态 (.30 Cal M1919)
└── axis/
    ├── gegner-standing.svg        # 德军步兵 · 站姿
    ├── gegner-kneeling.svg        # 德军步兵 · 跪姿
    ├── gegner-prone.svg           # 德军步兵 · 匍匐（静态）
    ├── gegner-prone-f0.svg        # 匍匐爬行动画 · 帧0
    ├── gegner-prone-f1.svg        # 匍匐爬行动画 · 帧1
    ├── gegner-prone-f2.svg        # 匍匐爬行动画 · 帧2
    ├── gegner-prone-f3.svg        # 匍匐爬行动画 · 帧3
    └── mg42-deployed.svg          # 德军机枪手 · 部署态 (MG42)
```

---

## 像素调色板

| 颜色名 | Hex | 用途 | 阵营 |
|--------|-----|------|------|
| Olive Drab | `#5B6B3A` | 盟军制服主体色 | Allies |
| M1 Helmet | `#3D4F24` | M1 钢盔深色 | Allies |
| Helmet Highlight | `#4A5C2A` | M1 钢盔高光 | Allies |
| Boots/Gear | `#4A3C28` | 靴子、枪托 | Allies |
| Feldgrau | `#4A5040` | 德军野战灰制服 | Axis |
| Stahlhelm | `#3A4030` | Stahlhelm 钢盔 | Axis |
| Helmet Highlight | `#454A38` | Stahlhelm 高光 | Axis |
| Weapon/Metal | `#3A3020` | 武器枪管 | Both |
| Ammo Box | `#D97706` | M1919 弹药盒标记 | Allies |
| Prone Elbow | `#D97706` | 匍匐肘部锚点 | Allies |
| Prone Elbow | `#DC2626` | 匍匐肘部锚点 | Axis |

---

## 精灵规格

| 参数 | 值 |
|------|-----|
| 视角 | Top-Down 90°（完全俯视） |
| 站姿/跪姿精灵尺寸 | 24×32 px |
| 匍匐/机枪精灵尺寸 | 32×24 px（横向展开） |
| 动画帧率 | 4 帧循环（匍匐爬行） |
| 方向支持 | 8 方向旋转（建议 45° 步进） |
| 渲染方式 | SVG → 光栅化 PNG，或直接 SVG 矢量渲染 |
| 阴影规格 | `rgba(0,0,0,0.08~0.2)` 半透明椭圆，精灵图层最底端 |

---

## 设计原则

### 1. 图层顺序（从底到顶）

```
1. Ground Shadow（地面阴影 - 椭圆）
2. Body（身体 - 椭圆/矩形组合）
3. Helmet Base（头盔底 - 椭圆）
4. Helmet Highlight（头盔高光 - 小椭圆）
5. Boots/Elbows（靴子/肘部 - 小矩形）
6. Weapon（武器 - 线条/矩形）
7. Bipod/Ammo（双脚架/弹药 - 线条/小矩形）
```

### 2. 阵营区分策略

- **盟军**：暖色橄榄绿（`#5B6B3A`），M1 钢盔轮廓较圆润
- **德军**：冷色灰绿（`#4A5040`），Stahlhelm 轮廓较扁平
- **武器差异**：M1 Garand 较短较粗 → Kar98k 较长且前端有刺刀矩形标记；M1919 较短 → MG42 枪身更长方

### 3. 匍匐爬行动画周期

4 帧循环对应匍匐前进的逐个动作：

| 帧 | 描述 | 关键变化 |
|----|------|---------|
| F0 | 双臂前伸（肘部锚点前移） | 右肘锚点置前 |
| F1 | 右腿蹬地前推 | 右腿段前伸，身体延长 |
| F2 | 左臂前伸（肘部锚点前移） | 左肘锚点置前 |
| F3 | 左腿蹬地前推 | 左腿段前伸，身体延长 |

播放顺序：F0 → F1 → F2 → F3 → 循环

---

## 使用指南

### 集成到 PyCC2 精灵系统

1. **SVG 转 PNG**：用 `cairosvg` 或浏览器 headless 渲染 SVG 为 24/32px PNG
2. **精灵表生成**：将对应方向的各姿态帧拼合为 sprite sheet
3. **配色变量化**：在 `config/cc2_color_palette.py` 中引入对应的颜色常量
4. **Python SVG 渲染**：可用 `cairosvg` 或直接解析 SVG 路径在 pygame 中用 `pygame.draw` 重绘

### 典型使用场景

```python
# config/cc2_color_palette.py 中已有关联常量
# 对应关系:
# COLOR_M1_GARAND → #3A3020 → 武器金属色
# COLOR_FELDGRAU_BASE → #4A5040 → 德军野战灰
# COLOR_OLIVE_DRAB → #5B6B3A → 盟军橄榄绿
```

---

## 从当前状态到目标状态的差距

| 当前状态 | 目标状态 |
|---------|---------|
| 纯几何圆点 + 小点 | 头盔/身体/靴子/武器多组件组合 |
| 无阵营视觉区分 | 盟军暖绿 vs 德军冷灰 + 钢盔差异 |
| 无姿态 | 站立/跪姿/匍匐/机枪部署 |
| 无动画 | 4 帧匍匐爬行循环 |
| 颜色偏蓝灰 | 暖军绿色系 |
