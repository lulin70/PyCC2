# PyCC2 像素精灵外包需求文档（Fiverr）

## 📋 项目概述

**项目名称**: PyCC2 - 32x32像素战术单位精灵包  
**项目类型**: 像素艺术资产制作  
**交付期限**: 7-10天  
**预算**: $300-500 USD

---

## 🎯 需求概述

为一款二战战术策略游戏（PyCC2）制作32x32像素的卡通风格单位精灵。游戏风格类似《Advance Wars》《Close Combat 2》，需要正俯视视角（90度鸟瞰）的战术单位。

---

## 📦 资产清单（Tier 1 - MVP）

### 步兵单位（4种）
1. **Rifleman**（步枪兵）
   - 基础步兵单位
   - 持步枪
   - 军绿色制服

2. **MG Team**（机枪组）
   - 轻机枪手
   - 持机枪（水平射击姿态）
   - 军绿色制服

3. **Mortar Team**（迫击炮组）
   - 迫击炮操作员
   - 旁边有迫击炮装备
   - 军绿色制服

4. **Officer**（军官）
   - 指挥官
   - 可能手持地图或指挥棒
   - 军绿色制服，可能有肩章

### 载具（3种）
5. **Sherman Tank**（谢尔曼坦克）
   - M4谢尔曼中型坦克
   - 暗绿色
   - 炮塔朝前

6. **Halftrack**（半履带车）
   - M3半履带运兵车
   - 暗绿色
   - 开放式顶部

7. **Jeep**（吉普车）
   - 威利斯吉普车
   - 暗绿色
   - 小型轻型载具

### 地形元素（8种）
8. **草地瓦片**（Grass tile）
9. **道路瓦片**（Road tile）
10. **建筑瓦片**（Building tile）
11. **树木**（Tree）
12. **掩体**（Bunker）
13. **弹坑**（Crater）
14. **桥梁**（Bridge）
15. **河流瓦片**（River tile）

### UI元素（5种）
16. **选中框**（Selection box）
17. **移动箭头**（Movement arrow）
18. **攻击准星**（Attack crosshair）
19. **血条**（Health bar）
20. **士气图标**（Morale icon）

**总计**: 20个资产

---

## 🎨 风格要求

### 参考风格
- **主要参考**: Advance Wars（GBA游戏）
- **备选参考**: Into the Breach、Wargroove
- **关键词**: 像素艺术、卡通风格、简化造型、清晰轮廓

### 视觉规范
1. **尺寸**: 32x32像素（严格）
2. **视角**: 正俯视（90度鸟瞰）
3. **轮廓**: 粗黑色描边（2-3像素宽）
4. **配色**: 
   - 盟军单位：军绿色（#6B8E23）
   - 敌军单位：红色/灰色（#DC143C / #808080）
   - 载具：暗绿色（#4F6F52）
5. **造型**: 极简几何形状，无渐变，纯平面色块
6. **背景**: 透明PNG

### 技术规范
- **格式**: PNG（透明背景）
- **色彩**: 限制在8-16色以内
- **抗锯齿**: 无（保持像素清晰）
- **动画帧数**: 无需动画（静态精灵）
- **方向数**: 初版只需1个方向（朝南）

---

## 📂 交付格式

### 文件结构
```
pycc2_sprites/
├── units/
│   ├── infantry/
│   │   ├── rifleman.png (32x32)
│   │   ├── mg_team.png (32x32)
│   │   ├── mortar_team.png (32x32)
│   │   └── officer.png (32x32)
│   └── vehicles/
│       ├── sherman_tank.png (32x32)
│       ├── halftrack.png (32x32)
│       └── jeep.png (32x32)
├── terrain/
│   ├── grass.png (32x32)
│   ├── road.png (32x32)
│   ├── building.png (32x32)
│   ├── tree.png (32x32)
│   ├── bunker.png (32x32)
│   ├── crater.png (32x32)
│   ├── bridge.png (32x32)
│   └── river.png (32x32)
└── ui/
    ├── selection_box.png (32x32)
    ├── movement_arrow.png (32x32)
    ├── attack_crosshair.png (32x32)
    ├── health_bar.png (32x32)
    └── morale_icon.png (32x32)
```

### 源文件
- 提供 .aseprite 或 .psd 源文件（如果有）
- 提供调色板文件（.pal或.txt）

---

## ✅ 验收标准

### 必须满足（Hard Requirements）
1. ✅ 所有精灵严格为32x32像素
2. ✅ PNG透明背景
3. ✅ 粗黑轮廓线（2-3像素）
4. ✅ 正俯视90度视角
5. ✅ 风格统一（所有资产风格一致）
6. ✅ 配色符合规范
7. ✅ 20个资产全部交付

### 期望满足（Soft Requirements）
- ⭐ 轮廓清晰，游戏内易识别
- ⭐ 简化造型，无过多细节
- ⭐ 色彩对比度高
- ⭐ 提供源文件和调色板

### 拒收条件
- ❌ 尺寸不是32x32
- ❌ 有平滑渐变或模糊效果
- ❌ 视角不是正俯视（如3/4视角）
- ❌ 无黑色轮廓线或轮廓过细
- ❌ 风格不统一（如混用写实和卡通）

---

## 💰 价格与付款

### 预算范围
- **基础包（20个资产）**: $300 USD
- **加急（5天交付）**: $400 USD
- **含源文件和调色板**: +$50 USD
- **含2次修改**:  包含在基础价格内

### 付款方式
- **预付款**: 30% ($100)
- **中期付款**: 30% ($100) - 提交10个资产后
- **尾款**: 40% ($120) - 全部资产验收通过后

### 修改政策
- **包含修改次数**: 2次（针对所有资产）
- **额外修改**: $30/次
- **修改范围**: 颜色、造型调整，不包含重新绘制

---

## 📅 时间表

| 里程碑 | 交付内容 | 时间 | 付款 |
|--------|---------|------|------|
| **M1: 样品** | 2个步兵精灵（Rifleman + MG Team） | Day 2 | $100 (30%) |
| **M2: 前期资产** | 所有步兵（4个）+ 所有载具（3个）+ 3个地形 | Day 5 | $100 (30%) |
| **M3: 完整交付** | 所有20个资产 + 源文件 | Day 7 | $120 (40%) |
| **M4: 修改完成** | 修改后最终版本 | Day 10 | - |

---

## 📧 Fiverr发布标题和描述

### 标题（英文）
```
Need 20 Pixel Art Sprites (32x32) for WW2 Tactical Strategy Game
```

### 描述（英文）
```
I'm looking for an experienced pixel artist to create 20 game assets 
(32x32 px) for a WW2 tactical strategy game in the style of Advance Wars.

Assets needed:
- 4 infantry units (rifleman, MG team, mortar, officer)
- 3 vehicles (Sherman tank, halftrack, jeep)
- 8 terrain tiles (grass, road, building, tree, etc.)
- 5 UI elements (selection box, arrows, icons)

Style requirements:
- 32x32 pixels (strict)
- Top-down 90° view (bird's eye)
- Bold black outline (2-3 px)
- Flat colors, no gradients
- Pixel art style (crisp pixels, no blur)
- Transparent PNG background

Reference: Advance Wars (GBA game)

Deliverables:
- 20 PNG files (32x32 each)
- Source files (.aseprite or .psd)
- Color palette file
- 2 revisions included

Budget: $300-400 USD
Timeline: 7-10 days

Please share:
1. Your portfolio (pixel art examples)
2. Similar projects you've done
3. Your timeline estimate

Looking forward to your proposals!
```

### 搜索关键词
- "pixel art game sprites"
- "32x32 pixel art"
- "top-down pixel sprites"
- "Advance Wars style"
- "RTS game assets"

---

## 🔍 如何筛选外包商

### 必须检查（Portfolio Review）
1. ✅ 有像素艺术作品集
2. ✅ 有32x32或类似尺寸经验
3. ✅ 有游戏资产制作经验
4. ✅ 评分≥4.8星
5. ✅ 完成订单≥10个

### 优先选择（Bonus Points）
- ⭐ 有战略游戏资产经验
- ⭐ 作品集中有Advance Wars风格
- ⭐ 有sprite sheet制作经验
- ⭐ 母语为英语（沟通顺畅）
- ⭐ 提供源文件

### 避免选择（Red Flags）
- ❌ 只有3D/写实风格作品
- ❌ 无游戏资产经验
- ❌ 评分<4.5星
- ❌ 新手（0-5个订单）
- ❌ 沟通响应慢（>24小时）

---

## 📎 附件（提供给外包商）

### 参考图片
1. **豆包AI生成的概念图**（4张步兵精灵）
   - 位置: `docs/references/douban_ai_samples/`
   - 用途: 展示期望的造型和姿态

2. **Advance Wars截图**（5张）
   - 位置: `docs/references/advance_wars/`
   - 用途: 风格参考

3. **PyCC2当前界面截图**（3张）
   - 位置: `docs/references/pycc2_current/`
   - 用途: 展示游戏上下文

### 调色板文件
```
# PyCC2 Cartoon Palette
# Allied Units
#6B8E23 (军绿色)
#556B2F (深绿)
#8FBC8F (浅绿)

# Axis Units
#DC143C (红色)
#8B0000 (深红)
#808080 (灰色)

# Vehicles
#4F6F52 (暗绿)
#2F4F4F (深暗绿)

# Outlines
#000000 (黑色)

# Backgrounds
Transparent
```

---

## 📝 沟通模板

### 初次联系
```
Hi [Artist Name],

I saw your portfolio and I'm impressed with your pixel art work, 
especially [specific project].

I'm working on a WW2 tactical strategy game (similar to Advance Wars) 
and need 20 pixel art sprites (32x32 px).

Please check the attached requirements document and reference images.

Can you:
1. Confirm you can deliver in 7-10 days?
2. Create 2 sample sprites (rifleman + tank) first for review?
3. Quote your price for the full 20 assets?

Looking forward to your reply!

Best regards,
[Your Name]
```

### 中期沟通
```
Hi [Artist Name],

Thanks for the M1 samples! They look great, just a few minor adjustments:

1. Rifleman: The outline could be 1px thicker
2. Tank: Make it slightly larger to fill the 32x32 canvas better

Once these are fixed, please proceed with M2 (next 10 assets).

Thanks!
```

### 最终验收
```
Hi [Artist Name],

All 20 assets look fantastic! They perfectly match our game style.

Just received the source files and color palette - everything is 
organized perfectly.

I've released the final payment. Thank you for the excellent work!

Would you be interested in Phase 2 (another 15 units) in the future?

Best regards,
[Your Name]
```

---

## ✅ 文档更新记录

- **创建时间**: 2026-11-01
- **版本**: v1.0
- **状态**: 待执行
- **下次更新**: 外包完成后补充实际经验

