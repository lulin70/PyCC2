# PyCC2 视觉优化计划方案

**文档版本**: 1.0  
**创建日期**: 2026-05-21  
**目标**: 接近甚至超越Close Combat 2的视觉质量  
**状态**: 待审核

---

## 📋 执行摘要

本计划旨在将PyCC2的视觉质量从当前的简单方格/图标风格，提升到接近甚至超越原版CC2的等距3D战术游戏水平。计划分为4个Phase，预计总工期4-6周。

### 当前状态评估
- ❌ **地形**: 简单方格，无纹理细节
- ❌ **单位**: 简单圆形图标，无方向感
- ❌ **视角**: 俯视2D，非等距视角
- ❌ **UI**: 基础功能，缺乏战术信息
- ✅ **游戏逻辑**: 核心战斗系统完整

### 目标状态
- ✅ **地形**: 等距视角，14种地形类型，丰富纹理
- ✅ **单位**: 8方向精灵，清晰识别，动画流畅
- ✅ **视角**: 等距45度视角，专业战术游戏感
- ✅ **UI**: 完整战术界面（单位面板+小地图+命令栏）
- ✅ **效果**: 爆炸、烟雾、天气等视觉效果

---

## 🎯 Phase 1: 获取CC2原版精灵资源

**目标**: 获取并解析CC2原版资源，建立资源库  
**工期**: 1周  
**优先级**: P0（最高）

### 1.1 资源下载
**负责人**: DevOps Engineer

- [ ] 下载CC2Guide-SpriteFiles-v9.zip (566KB)
  - URL: `https://closecombat2.hpage.com/get_file.php?id=23591021&vnr=473429`
  - 内容: .spr文件格式详解
  
- [ ] 下载CC2MapMuseum.zip
  - URL: `https://closecombat2.hpage.com/get_file.php?id=30120667&vnr=908650`
  - 内容: 所有CC2自定义地图，可能包含精灵资源
  
- [ ] 下载CC2Guide-Terrain-File-v5.pdf
  - URL: `https://closecombat2.hpage.com/get_file.php?id=23591023&vnr=812344`
  - 内容: Terrain.azp格式文档

**备选方案**:
- 从GOG/Steam提取原版游戏资源
- 使用SteamUnlocked等渠道

### 1.2 资源解析工具开发
**负责人**: Solo Coder

创建工具解析CC2专有格式：

#### 1.2.1 SPR文件解析器
```python
# scripts/parse_cc2_spr.py
class CC2SpriteParser:
    """解析CC2的.spr精灵文件"""
    
    def parse_spr_file(self, filepath: Path) -> SpriteData:
        """
        解析.spr文件
        返回: 像素数据、调色板、尺寸信息
        """
        pass
    
    def export_to_png(self, sprite_data: SpriteData, output_path: Path):
        """导出为PNG格式"""
        pass
```

#### 1.2.2 AZP地形文件解析器
```python
# scripts/parse_cc2_terrain.py
class CC2TerrainParser:
    """解析CC2的Terrain.azp文件"""
    
    def parse_azp_file(self, filepath: Path) -> TerrainData:
        """解析.azp地形文件"""
        pass
    
    def extract_tiles(self, terrain_data: TerrainData, output_dir: Path):
        """提取所有地形tile为PNG"""
        pass
```

### 1.3 资源提取和整理
**负责人**: UI Designer

- [ ] 提取所有单位精灵（盟军+德军）
- [ ] 提取所有地形tile（14种类型）
- [ ] 提取建筑物精灵
- [ ] 提取特效精灵（爆炸、烟雾）
- [ ] 整理到标准目录结构

**目录结构**:
```
PyCC2/assets/
├── sprites/
│   ├── units/
│   │   ├── allies/
│   │   │   ├── infantry_d0.png ... infantry_d7.png
│   │   │   ├── mg_team_d0.png ... mg_team_d7.png
│   │   │   └── ...
│   │   └── axis/
│   ├── vehicles/
│   ├── buildings/
│   └── effects/
└── terrain/
    ├── terrain_00.png (草地)
    ├── terrain_01.png (道路)
    └── ... (共14个)
```

### 1.4 验收标准
- ✅ 成功下载所有3个资源文件
- ✅ SPR解析器能正确解析至少10个精灵文件
- ✅ AZP解析器能提取所有14种地形tile
- ✅ 所有资源整理到标准目录结构
- ✅ 生成资源清单文档

---

## 🗺️ Phase 2: 地形系统改进

**目标**: 实现等距视角地形渲染系统  
**工期**: 1-2周  
**优先级**: P0（最高）

### 2.1 等距地形渲染器
**负责人**: Architect + Solo Coder

#### 2.1.1 更新地形渲染系统
```python
# src/pycc2/presentation/rendering/isometric_terrain_renderer.py
class IsometricTerrainRenderer:
    """等距视角地形渲染器"""
    
    def __init__(self):
        self.tile_width = 64   # 等距tile宽度
        self.tile_height = 32  # 等距tile高度
        self.terrain_tiles = {}  # 缓存地形tile
    
    def world_to_iso(self, x: int, y: int) -> tuple[int, int]:
        """世界坐标转等距坐标"""
        iso_x = (x - y) * (self.tile_width // 2)
        iso_y = (x + y) * (self.tile_height // 2)
        return iso_x, iso_y
    
    def render_terrain(self, game_map: GameMap, camera: Camera):
        """渲染等距地形"""
        # 按照从后到前的顺序渲染（画家算法）
        for y in range(game_map.height):
            for x in range(game_map.width):
                tile_id = game_map.tile_grid[y, x]
                iso_x, iso_y = self.world_to_iso(x, y)
                screen_pos = camera.world_to_screen((iso_x, iso_y))
                self.draw_tile(tile_id, screen_pos)
```

#### 2.1.2 地形过渡系统
```python
class TerrainTransitionSystem:
    """地形过渡和混合"""
    
    def generate_transition_tiles(self):
        """生成地形过渡tile（如草地→道路）"""
        pass
    
    def apply_autotiling(self, game_map: GameMap):
        """自动tile匹配（Wang tiles或类似算法）"""
        pass
```

### 2.2 地形细节增强
**负责人**: UI Designer

- [ ] 为每种地形类型创建多个变体（避免重复感）
- [ ] 添加地形装饰物（石头、草丛、树木）
- [ ] 实现地形阴影系统
- [ ] 添加地形高度视觉暗示

### 2.3 程序化地形生成（备选）
**负责人**: Solo Coder

如果CC2原版资源不可用，使用程序化生成：

```python
# scripts/generate_isometric_terrain.py
class IsometricTerrainGenerator:
    """生成等距视角地形tile"""
    
    def generate_grass_tile(self) -> Image:
        """生成草地tile（带纹理细节）"""
        pass
    
    def generate_road_tile(self) -> Image:
        """生成道路tile（带车辙）"""
        pass
    
    # ... 其他地形类型
```

### 2.4 验收标准
- ✅ 地形使用等距视角渲染
- ✅ 支持14种地形类型
- ✅ 地形过渡自然平滑
- ✅ 每种地形有丰富的纹理细节
- ✅ 性能: 60 FPS @ 1920x1080

---

## 👥 Phase 3: 单位精灵系统

**目标**: 实现8方向单位精灵和动画系统  
**工期**: 2周  
**优先级**: P0（最高）

### 3.1 单位精灵渲染器
**负责人**: Architect + Solo Coder

#### 3.1.1 更新精灵渲染系统
```python
# src/pycc2/presentation/rendering/unit_sprite_renderer.py
class UnitSpriteRenderer:
    """单位精灵渲染器（8方向）"""
    
    def get_unit_sprite(self, unit: Unit) -> Surface:
        """
        根据单位类型、派系、方向获取精灵
        
        方向映射:
        0 = 北 (N)
        1 = 东北 (NE)
        2 = 东 (E)
        3 = 东南 (SE)
        4 = 南 (S)
        5 = 西南 (SW)
        6 = 西 (W)
        7 = 西北 (NW)
        """
        direction = self.calculate_direction(unit.facing)
        sprite_key = f"{unit.faction}_{unit.type}_d{direction}"
        return self.sprite_cache.get(sprite_key)
    
    def calculate_direction(self, facing_angle: float) -> int:
        """将角度转换为8方向索引"""
        # 0° = 北, 45° = 东北, 90° = 东, ...
        direction = int((facing_angle + 22.5) / 45) % 8
        return direction
```

### 3.2 单位动画系统
**负责人**: Solo Coder

#### 3.2.1 动画状态机
```python
class UnitAnimationStateMachine:
    """单位动画状态机"""
    
    states = ['idle', 'moving', 'firing', 'dying']
    
    def update(self, unit: Unit, delta_time: float):
        """更新动画状态"""
        if unit.is_moving:
            self.play_animation('moving', loop=True)
        elif unit.is_firing:
            self.play_animation('firing', loop=False)
        elif not unit.is_alive:
            self.play_animation('dying', loop=False)
        else:
            self.play_animation('idle', loop=True)
    
    def get_current_frame(self) -> Surface:
        """获取当前动画帧"""
        pass
```

### 3.3 单位类型覆盖
**负责人**: UI Designer + Solo Coder

为以下单位类型创建精灵：

#### 步兵单位（每个8方向）
- [ ] 步兵班 (Infantry Squad)
- [ ] 机枪组 (MG Team)
- [ ] 指挥官 (Commander)
- [ ] 狙击手 (Sniper)
- [ ] 工兵 (Engineer)
- [ ] 医疗兵 (Medic)

#### 载具单位（每个8方向）
- [ ] 轻型坦克
- [ ] 中型坦克 (Sherman/PzIV)
- [ ] 重型坦克 (Tiger)
- [ ] 半履带车
- [ ] 吉普车
- [ ] 卡车

### 3.4 单位阴影和高光
**负责人**: UI Designer

- [ ] 为所有单位添加椭圆阴影
- [ ] 添加选中高光效果
- [ ] 添加鼠标悬停效果
- [ ] 添加单位状态指示器（压制、疲劳等）

### 3.5 验收标准
- ✅ 所有单位使用8方向精灵
- ✅ 单位朝向正确反映移动方向
- ✅ 移动动画流畅（4-6帧）
- ✅ 射击动画清晰可见
- ✅ 死亡动画自然
- ✅ 盟军和德军视觉区分明显

---

## ✨ Phase 4: 视觉效果和UI

**目标**: 添加战斗效果和完整UI系统  
**工期**: 1-2周  
**优先级**: P1（高）

### 4.1 粒子效果系统
**负责人**: Solo Coder

#### 4.1.1 粒子系统架构
```python
# src/pycc2/presentation/effects/particle_system.py
class ParticleSystem:
    """粒子效果系统"""
    
    def create_explosion(self, position: Vec2, size: str = 'medium'):
        """创建爆炸效果"""
        particles = []
        # 火光粒子（橙红色）
        # 烟雾粒子（灰黑色）
        # 碎片粒子
        return ExplosionEffect(particles)
    
    def create_smoke(self, position: Vec2, duration: float = 5.0):
        """创建烟雾效果"""
        pass
    
    def create_muzzle_flash(self, position: Vec2, direction: Vec2):
        """创建枪口火光"""
        pass
    
    def create_bullet_trail(self, start: Vec2, end: Vec2):
        """创建弹道轨迹"""
        pass
```

### 4.2 战斗效果
**负责人**: UI Designer + Solo Coder

- [ ] **爆炸效果**: 手榴弹、炮弹、坦克炮（6-8帧动画）
- [ ] **枪口火光**: 步枪、机枪射击（2-3帧）
- [ ] **烟雾效果**: 烟雾弹、燃烧、尘土（循环动画）
- [ ] **弹道轨迹**: 曳光弹、炮弹飞行
- [ ] **命中效果**: 火花、血迹、弹孔

### 4.3 环境效果
**负责人**: Solo Coder

- [ ] **天气系统**: 雨、雾、雪（粒子效果）
- [ ] **时间系统**: 黎明、白天、黄昏、夜晚（色调调整）
- [ ] **动态阴影**: 单位和建筑物的阴影
- [ ] **环境音效**: 风声、雨声、远处炮火

### 4.4 UI系统重构
**负责人**: UI Designer + Product Manager

#### 4.4.1 单位信息面板
```
┌─────────────────────┐
│  [单位头像]         │
│  步兵班 (盟军)      │
│  ━━━━━━━━━━ 士气    │
│  ████████░░ 90%     │
│                     │
│  人员: 8/10         │
│  弹药: 240发        │
│  状态: 正常         │
│                     │
│  [疲劳] [压制]      │
└─────────────────────┘
```

#### 4.4.2 小地图
```
┌─────────────────┐
│  [战场全景]     │
│  ▲ ▲ ▲          │
│    ■ ■          │
│  ▼ ▼            │
│  [视野框]       │
└─────────────────┘
```

#### 4.4.3 命令栏
```
┌──────────────────────────────────────────────────┐
│ [移动] [攻击] [防御] [撤退] [烟雾] [隐蔽] [...]  │
└──────────────────────────────────────────────────┘
```

### 4.5 后处理效果（可选）
**负责人**: Solo Coder

- [ ] 暗角效果（Vignette）
- [ ] 色彩分级（Color Grading）
- [ ] 景深效果（Depth of Field）
- [ ] 屏幕震动（Screen Shake）

### 4.6 验收标准
- ✅ 爆炸效果逼真，有火光和烟雾
- ✅ 射击时有明显的枪口火光
- ✅ 烟雾效果自然扩散
- ✅ 单位信息面板显示完整信息
- ✅ 小地图实时更新单位位置
- ✅ 命令栏所有按钮可用
- ✅ 天气效果可见且不影响性能

---

## 📊 资源需求

### 人力资源
| 角色 | 工作量 | 主要职责 |
|------|--------|----------|
| Product Manager | 10% | 需求定义、优先级管理 |
| Architect | 20% | 技术架构设计、代码审查 |
| UI Designer | 40% | 精灵设计、UI设计、视觉效果 |
| Solo Coder | 80% | 核心开发、工具开发 |
| Test Expert | 30% | 测试策略、质量保证 |
| DevOps | 10% | 资源下载、部署管理 |
| Security | 5% | 资源合规性审查 |

### 技术资源
- **开发环境**: Python 3.9+, Pygame 2.5+
- **图像处理**: Pillow, NumPy
- **版本控制**: Git
- **CI/CD**: GitHub Actions（可选）

### 外部资源
- CC2原版游戏资源（合法获取）
- CC2社区文档和工具
- 开源像素艺术资源（备选）

---

## ⏱️ 时间计划

### 总体时间线（4-6周）
```
Week 1: Phase 1 - 资源获取和解析
Week 2-3: Phase 2 - 地形系统改进
Week 4-5: Phase 3 - 单位精灵系统
Week 6: Phase 4 - 视觉效果和UI
```

### 里程碑
| 里程碑 | 日期 | 交付物 |
|--------|------|--------|
| M1: 资源就绪 | Week 1 | CC2资源提取完成 |
| M2: 地形完成 | Week 3 | 等距地形渲染 |
| M3: 单位完成 | Week 5 | 8方向单位精灵 |
| M4: 效果完成 | Week 6 | 完整视觉效果 |
| M5: 发布 | Week 6 | V1.0视觉优化版 |

---

## 🎯 成功标准

### 定量指标
- ✅ **帧率**: 稳定60 FPS @ 1920x1080
- ✅ **内存占用**: <500MB
- ✅ **加载时间**: <5秒
- ✅ **精灵数量**: >100个单位精灵
- ✅ **地形类型**: 14种
- ✅ **特效类型**: >10种

### 定性指标
- ✅ **视觉风格**: 接近或超越CC2原版
- ✅ **用户反馈**: 正面评价>80%
- ✅ **可玩性**: 不影响游戏性能
- ✅ **专业度**: 达到商业游戏水平

---

## ⚠️ 风险评估

### 高风险
| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| CC2资源无法获取 | 高 | 中 | 使用程序化生成备选方案 |
| 性能不达标 | 高 | 低 | 优化渲染管线，使用LOD |
| 等距渲染复杂度高 | 中 | 中 | 参考现有等距游戏引擎 |

### 中风险
| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| 时间超期 | 中 | 中 | 分阶段交付，优先核心功能 |
| 精灵质量不足 | 中 | 低 | 聘请专业像素艺术家 |
| 兼容性问题 | 低 | 低 | 多平台测试 |

### 低风险
| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| 资源版权问题 | 低 | 低 | 使用合法渠道，保留证明 |
| 团队协作问题 | 低 | 低 | 定期沟通，明确分工 |

---

## 📈 后续优化方向

### V1.1 增强版（Phase 5）
- 高级粒子系统（GPU加速）
- 动态光照和阴影
- 更多单位类型和动画
- 多人游戏视觉同步

### V2.0 现代化版（Phase 6）
- 3D渲染引擎（可选）
- 高分辨率纹理（4K）
- 现代化UI/UX
- VR支持（实验性）

---

## 📝 审核和批准

### DevSquad团队审核
- [ ] Product Manager: 需求和优先级审核
- [ ] Architect: 技术架构审核
- [ ] UI Designer: 视觉设计审核
- [ ] Solo Coder: 实施可行性审核
- [ ] Test Expert: 测试策略审核
- [ ] DevOps: 部署和资源审核
- [ ] Security: 合规性审核

### 最终批准
- [ ] 项目负责人签字
- [ ] 预算批准
- [ ] 开始执行

---

## 📅 版本历史

| 版本 | 日期 | 变更 | 作者 |
|------|------|------|------|
| 1.0 | 2026-05-21 | 初始版本，完整优化计划 | Kiro AI |

---

**下一步**: 提交DevSquad团队审核，达成共识后开始Phase 1执行。
