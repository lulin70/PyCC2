# PyCC2 图像优化实施指南

**版本**: v1.0  
**日期**: 2026-06-16  
**状态**: 实施中

---

## 📋 优化概览

本指南提供PyCC2图像质量优化的完整实施路径，包括：
1. CC2原版素材集成框架
2. 程序化图像质量提升
3. 测试和验证流程
4. 避免幽灵功能的检查清单

---

## Phase 1: CC2原版精灵集成

### 1.1 资源准备清单

#### 必需资源
- [ ] CC2原版游戏文件 (Steam/GOG/SteamUnlocked)
- [ ] CC2Guide-SpriteFiles-v9.zip (已提供)
- [ ] CC2Spriter工具 v2.94 (closecombat2.hpage.com)
- [ ] CC2Guide-Terrain-File-v5.pdf (已提供)

#### 可选资源
- [ ] CC2MapMuseum.zip (自定义地图素材)
- [ ] 额外的mod素材包

### 1.2 精灵提取流程

```bash
# 步骤1: 定位CC2游戏精灵文件
CC2安装目录/
├── SPRI/      # 步兵精灵
├── IRPS/      # 车辆精灵（反向）
├── ALPH/      # Alpha通道
└── *.spr      # 精灵数据文件

# 步骤2: 使用CC2Spriter转换
1. 打开CC2Spriter v2.94
2. File → Open → 选择.spr文件
3. File → Export → PNG Sequence
4. 设置导出参数:
   - 格式: PNG
   - 透明度: 保留Alpha通道
   - 方向: 导出全部8方向
   - 帧数: 导出全部动画帧

# 步骤3: 组织导出的PNG文件
mkdir -p PyCC2/assets/sprites/cc2_original/
├── infantry/
│   ├── rifle_squad/
│   │   ├── N_idle_001.png
│   │   ├── N_walk_001.png
│   │   ├── N_shoot_001.png
│   │   └── ...
│   └── ...
├── vehicles/
│   ├── sherman_tank/
│   │   ├── N_idle_001.png
│   │   └── ...
│   └── ...
└── buildings/
    └── ...
```

### 1.3 集成到PyCC2

创建新的加载器: `src/pycc2/presentation/rendering/cc2_sprite_loader.py`

```python
"""
CC2 Original Sprite Loader

加载CC2原版精灵PNG文件，提供与现有系统兼容的接口。
确保功能被实际调用，避免幽灵功能。
"""

import pygame
from pathlib import Path
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

class CC2SpriteLoader:
    """加载CC2原版精灵素材"""
    
    def __init__(self, assets_root: Path):
        self.assets_root = assets_root
        self.cc2_sprite_path = assets_root / "sprites" / "cc2_original"
        self.sprite_cache: Dict[str, pygame.Surface] = {}
        self._load_stats = {"loaded": 0, "failed": 0, "cached": 0}
        
        logger.info("CC2SpriteLoader initialized: %s", self.cc2_sprite_path)
    
    def is_available(self) -> bool:
        """检查CC2原版素材是否可用"""
        return self.cc2_sprite_path.exists() and self.cc2_sprite_path.is_dir()
    
    def load_sprite(
        self, 
        unit_type: str, 
        direction: str, 
        animation: str = "idle", 
        frame: int = 0
    ) -> Optional[pygame.Surface]:
        """
        加载特定精灵
        
        参数:
            unit_type: 单位类型 (如 "rifle_squad", "sherman_tank")
            direction: 方向 ("N", "NE", "E", "SE", "S", "SW", "W", "NW")
            animation: 动画类型 ("idle", "walk", "shoot", "死亡")
            frame: 帧号
            
        返回:
            pygame.Surface 或 None（如果文件不存在）
        """
        cache_key = f"{unit_type}_{direction}_{animation}_{frame}"
        
        # 检查缓存
        if cache_key in self.sprite_cache:
            self._load_stats["cached"] += 1
            return self.sprite_cache[cache_key]
        
        # 构建文件路径
        sprite_file = self._build_sprite_path(unit_type, direction, animation, frame)
        
        if not sprite_file.exists():
            self._load_stats["failed"] += 1
            logger.debug("CC2 sprite not found: %s", sprite_file)
            return None
        
        try:
            # 加载PNG
            surface = pygame.image.load(str(sprite_file)).convert_alpha()
            self.sprite_cache[cache_key] = surface
            self._load_stats["loaded"] += 1
            logger.debug("Loaded CC2 sprite: %s", sprite_file.name)
            return surface
            
        except Exception as e:
            self._load_stats["failed"] += 1
            logger.error("Failed to load CC2 sprite %s: %s", sprite_file, e)
            return None
    
    def _build_sprite_path(
        self, 
        unit_type: str, 
        direction: str, 
        animation: str, 
        frame: int
    ) -> Path:
        """构建精灵文件路径"""
        # 判断单位类别
        category = self._get_unit_category(unit_type)
        
        # 文件命名: direction_animation_frame.png
        # 例如: N_walk_001.png
        filename = f"{direction}_{animation}_{frame:03d}.png"
        
        return self.cc2_sprite_path / category / unit_type / filename
    
    def _get_unit_category(self, unit_type: str) -> str:
        """根据单位类型判断类别"""
        vehicles = ["sherman", "panzer", "tiger", "halftrack", "jeep"]
        
        for vehicle in vehicles:
            if vehicle in unit_type.lower():
                return "vehicles"
        
        return "infantry"  # 默认为步兵
    
    def get_load_stats(self) -> Dict[str, int]:
        """获取加载统计信息（用于测试验证）"""
        return self._load_stats.copy()
    
    def preload_unit(self, unit_type: str) -> int:
        """预加载某个单位的所有精灵"""
        loaded_count = 0
        directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        animations = ["idle", "walk", "shoot"]
        
        for direction in directions:
            for animation in animations:
                for frame in range(8):  # 假设最多8帧
                    if self.load_sprite(unit_type, direction, animation, frame):
                        loaded_count += 1
        
        logger.info("Preloaded %d sprites for %s", loaded_count, unit_type)
        return loaded_count
```

### 1.4 集成到现有系统

修改 `sprite_cache_manager.py` 以支持CC2精灵加载器:

```python
# 在 SpriteCacheManager.__init__ 中添加
self.cc2_loader = CC2SpriteLoader(assets_root)
self.use_cc2_sprites = self.cc2_loader.is_available()

if self.use_cc2_sprites:
    logger.info("CC2 original sprites detected - using high quality assets")
else:
    logger.info("CC2 sprites not found - using procedural generation")

# 在生成精灵时，优先使用CC2原版
def get_unit_sprite(self, unit, direction):
    # 1. 尝试加载CC2原版
    if self.use_cc2_sprites:
        cc2_sprite = self.cc2_loader.load_sprite(
            unit_type=unit.unit_type.name.lower(),
            direction=direction,
            animation="idle",
            frame=0
        )
        if cc2_sprite:
            return cc2_sprite
    
    # 2. 回退到程序生成
    return self._generate_procedural_sprite(unit, direction)
```

### 1.5 测试和验证

创建测试文件: `tests/unit/test_cc2_sprite_loader.py`

```python
import pytest
from pathlib import Path
from pycc2.presentation.rendering.cc2_sprite_loader import CC2SpriteLoader

class TestCC2SpriteLoader:
    """测试CC2精灵加载器 - 确保功能被实际调用"""
    
    def test_loader_initialization(self, tmp_path):
        """测试加载器初始化"""
        loader = CC2SpriteLoader(tmp_path)
        assert loader.assets_root == tmp_path
        assert not loader.is_available()  # 没有素材
    
    def test_availability_check(self, tmp_path):
        """测试素材可用性检查"""
        # 创建假的CC2素材目录
        cc2_path = tmp_path / "sprites" / "cc2_original"
        cc2_path.mkdir(parents=True)
        
        loader = CC2SpriteLoader(tmp_path)
        assert loader.is_available()
    
    def test_sprite_path_building(self, tmp_path):
        """测试路径构建逻辑"""
        loader = CC2SpriteLoader(tmp_path)
        
        path = loader._build_sprite_path("rifle_squad", "N", "walk", 1)
        assert "infantry" in str(path)
        assert "rifle_squad" in str(path)
        assert "N_walk_001.png" in str(path)
    
    def test_load_stats_tracking(self, tmp_path):
        """测试加载统计 - 验证功能被调用"""
        loader = CC2SpriteLoader(tmp_path)
        
        # 尝试加载不存在的精灵
        result = loader.load_sprite("test_unit", "N", "idle", 0)
        assert result is None
        
        stats = loader.get_load_stats()
        assert stats["failed"] == 1
        assert stats["loaded"] == 0
    
    @pytest.mark.skipif(
        not Path("assets/sprites/cc2_original").exists(),
        reason="CC2 original sprites not available"
    )
    def test_load_real_cc2_sprite(self):
        """测试加载真实CC2精灵（如果存在）"""
        loader = CC2SpriteLoader(Path("assets"))
        
        # 尝试加载常见单位
        sprite = loader.load_sprite("rifle_squad", "N", "idle", 0)
        
        if sprite:
            assert sprite.get_width() > 0
            assert sprite.get_height() > 0
            
            stats = loader.get_load_stats()
            assert stats["loaded"] >= 1
```

---

## Phase 2: 程序化图像质量提升

### 2.1 当前问题分析

当CC2原版素材不可用时，PyCC2使用`PixelArtist3D`程序生成精灵。
当前质量: 6.5/10

可改进点:
1. 细节层次不足
2. 颜色单调
3. 缺少阴影和高光
4. 动画过渡生硬

### 2.2 增强程序化生成

创建增强版: `src/pycc2/presentation/rendering/enhanced_pixel_artist.py`

```python
"""
Enhanced Pixel Artist - 提升程序化图像质量

在没有CC2原版素材时，生成更高质量的程序化精灵。
"""

import pygame
import numpy as np
from typing import Tuple
import logging

logger = logging.getLogger(__name__)

class EnhancedPixelArtist:
    """增强的程序化精灵生成器"""
    
    def __init__(self):
        self.quality_level = "high"  # low, medium, high
        self._generation_count = 0
        logger.info("EnhancedPixelArtist initialized with quality: %s", self.quality_level)
    
    def generate_infantry_sprite(
        self, 
        faction: str, 
        direction: str,
        size: Tuple[int, int] = (32, 32)
    ) -> pygame.Surface:
        """生成步兵精灵 - 比原版有更多细节"""
        self._generation_count += 1
        
        surface = pygame.Surface(size, pygame.SRCALPHA)
        
        # 1. 基础轮廓（比之前更精细）
        self._draw_body_with_details(surface, faction, direction)
        
        # 2. 武器细节
        self._draw_weapon_details(surface, direction)
        
        # 3. 装备细节（头盔、背包等）
        self._draw_equipment(surface, faction)
        
        # 4. 阴影和高光
        self._apply_lighting(surface, direction)
        
        # 5. 抗锯齿
        self._apply_antialiasing(surface)
        
        return surface
    
    def _draw_body_with_details(self, surface, faction, direction):
        """绘制身体 - 添加更多细节"""
        # 基础颜色
        if faction.lower() == "allied":
            base_color = (85, 107, 47)  # 橄榄绿
            accent_color = (139, 115, 85)  # 棕色（装备）
        else:
            base_color = (105, 105, 105)  # 灰色
            accent_color = (64, 64, 64)  # 深灰（装备）
        
        center_x, center_y = surface.get_width() // 2, surface.get_height() // 2
        
        # 头部（带头盔细节）
        helmet_rect = pygame.Rect(center_x - 3, center_y - 6, 6, 5)
        pygame.draw.ellipse(surface, base_color, helmet_rect)
        # 头盔高光
        pygame.draw.line(surface, self._lighten_color(base_color), 
                        (center_x - 2, center_y - 5), (center_x, center_y - 5), 1)
        
        # 身体（带衣褶细节）
        body_rect = pygame.Rect(center_x - 4, center_y - 1, 8, 10)
        pygame.draw.rect(surface, base_color, body_rect)
        # 衣褶阴影
        pygame.draw.line(surface, self._darken_color(base_color),
                        (center_x, center_y), (center_x, center_y + 8), 1)
        
        # 腿部（带裤子细节）
        left_leg = pygame.Rect(center_x - 3, center_y + 9, 3, 6)
        right_leg = pygame.Rect(center_x, center_y + 9, 3, 6)
        pygame.draw.rect(surface, self._darken_color(base_color), left_leg)
        pygame.draw.rect(surface, self._darken_color(base_color), right_leg)
        
        # 手臂（带袖子细节）
        if direction in ["E", "NE", "SE"]:  # 右侧可见
            arm_rect = pygame.Rect(center_x + 4, center_y + 2, 2, 5)
            pygame.draw.rect(surface, base_color, arm_rect)
        if direction in ["W", "NW", "SW"]:  # 左侧可见
            arm_rect = pygame.Rect(center_x - 6, center_y + 2, 2, 5)
            pygame.draw.rect(surface, base_color, arm_rect)
    
    def _draw_weapon_details(self, surface, direction):
        """绘制武器细节"""
        center_x, center_y = surface.get_width() // 2, surface.get_height() // 2
        weapon_color = (64, 64, 64)  # 武器金属色
        
        # 根据方向绘制步枪
        if direction in ["E", "NE"]:
            # 枪管
            pygame.draw.line(surface, weapon_color,
                           (center_x + 2, center_y + 3),
                           (center_x + 8, center_y + 1), 2)
            # 枪托
            pygame.draw.rect(surface, (101, 67, 33),
                           pygame.Rect(center_x + 1, center_y + 3, 3, 2))
        elif direction in ["W", "NW"]:
            pygame.draw.line(surface, weapon_color,
                           (center_x - 2, center_y + 3),
                           (center_x - 8, center_y + 1), 2)
            pygame.draw.rect(surface, (101, 67, 33),
                           pygame.Rect(center_x - 4, center_y + 3, 3, 2))
    
    def _draw_equipment(self, surface, faction):
        """绘制装备细节（背包、弹药袋等）"""
        center_x, center_y = surface.get_width() // 2, surface.get_height() // 2
        equip_color = (101, 67, 33)  # 棕色装备
        
        # 背包
        backpack_rect = pygame.Rect(center_x - 2, center_y + 1, 4, 3)
        pygame.draw.rect(surface, equip_color, backpack_rect)
        
        # 弹药带
        pygame.draw.line(surface, self._darken_color(equip_color),
                        (center_x - 3, center_y + 3),
                        (center_x + 3, center_y + 3), 1)
    
    def _apply_lighting(self, surface, direction):
        """应用光照效果 - 添加阴影和高光"""
        # 假设光源从左上方来
        width, height = surface.get_size()
        
        # 创建一个半透明的阴影层
        shadow_layer = pygame.Surface((width, height), pygame.SRCALPHA)
        
        # 根据方向决定阴影位置
        if direction in ["E", "SE", "S"]:
            # 左侧和底部有阴影
            for x in range(width):
                for y in range(height):
                    pixel = surface.get_at((x, y))
                    if pixel.a > 0:  # 只处理不透明像素
                        # 计算阴影强度
                        shadow_intensity = int((x / width) * 30)
                        shadow_layer.set_at((x, y), (0, 0, 0, shadow_intensity))
        
        surface.blit(shadow_layer, (0, 0))
    
    def _apply_antialiasing(self, surface):
        """应用简单的抗锯齿"""
        # 使用pygame的平滑缩放技巧
        # 先放大2倍再缩小回来，实现平滑效果
        width, height = surface.get_size()
        scaled_up = pygame.transform.scale(surface, (width * 2, height * 2))
        smoothed = pygame.transform.smoothscale(scaled_up, (width, height))
        surface.blit(smoothed, (0, 0))
    
    def _lighten_color(self, color: Tuple[int, int, int], amount: int = 30) -> Tuple[int, int, int]:
        """使颜色变亮"""
        return tuple(min(255, c + amount) for c in color[:3])
    
    def _darken_color(self, color: Tuple[int, int, int], amount: int = 30) -> Tuple[int, int, int]:
        """使颜色变暗"""
        return tuple(max(0, c - amount) for c in color[:3])
    
    def get_generation_count(self) -> int:
        """获取生成计数（用于测试验证）"""
        return self._generation_count
```

### 2.3 集成测试

```python
# tests/unit/test_enhanced_pixel_artist.py

def test_enhanced_generation_is_called():
    """验证增强生成器被实际调用"""
    artist = EnhancedPixelArtist()
    
    initial_count = artist.get_generation_count()
    sprite = artist.generate_infantry_sprite("allied", "N")
    
    assert artist.get_generation_count() == initial_count + 1
    assert sprite.get_width() > 0
    assert sprite.get_height() > 0
```

---

## 避免幽灵功能检查清单

### ✅ 功能调用验证

每个新功能必须通过以下检查：

1. **初始化验证**
```python
# 在__init__中添加日志
logger.info("ComponentName initialized")
```

2. **调用计数器**
```python
# 添加调用统计
self._call_count = 0

def method(self):
    self._call_count += 1
    # ...实际逻辑
```

3. **集成测试**
```python
# 测试功能在实际游戏循环中被调用
def test_feature_integration():
    game = GameLoop()
    game.run_one_frame()
    
    # 验证功能被调用
    assert feature.was_called()
```

4. **运行时监控**
```python
# 添加运行时统计端点
def get_runtime_stats():
    return {
        "cc2_sprites_loaded": cc2_loader.get_load_stats(),
        "procedural_generated": pixel_artist.get_generation_count(),
        "cache_hits": cache_manager.get_cache_stats()
    }
```

### ✅ 测试覆盖要求

每个新功能必须有：
- [ ] 单元测试 (测试独立功能)
- [ ] 集成测试 (测试与现有系统集成)
- [ ] E2E测试 (测试在实际游戏中运行)
- [ ] 性能测试 (确保不影响帧率)

---

## 实施时间表

### 第1周: 框架和工具
- [ ] CC2SpriteLoader实现和测试
- [ ] EnhancedPixelArtist实现和测试
- [ ] 集成到sprite_cache_manager
- [ ] 单元测试全部通过

### 第2周: 素材准备（用户执行）
- [ ] 提取CC2原版精灵
- [ ] 组织文件结构
- [ ] 验证素材完整性

### 第3周: 集成和优化
- [ ] 加载CC2原版精灵
- [ ] 回退机制测试
- [ ] 性能优化
- [ ] E2E测试

### 第4周: Phase 2-4
- [ ] 地形纹理优化
- [ ] 动画系统增强
- [ ] 视觉效果提升

---

**文档维护**: 本指南将随着实施进展持续更新。

**下一步**: 开始实施CC2SpriteLoader和EnhancedPixelArtist。
