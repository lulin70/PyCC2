# Phase 3: 单位头像系统技术规格

**负责人**: 架构师 + 代码审查员  
**审阅人**: 测试专家  
**创建时间**: 2026-06-16 20:07  
**状态**: ✅ 设计完成

---

## 1. API规格

### 1.1 核心类签名

```python
class UnitPortraitRenderer:
    """军事风格单位头像渲染器"""
    
    def __init__(self, max_cache_size: int = 100):
        """初始化渲染器
        
        Args:
            max_cache_size: 缓存容量，默认100个头像
        """
        
    def render_portrait(
        self,
        unit_type: UnitType,
        faction: Faction,
        health_percent: float = 1.0
    ) -> pygame.Surface:
        """生成96x96头像
        
        Args:
            unit_type: 单位类型枚举
            faction: 派系枚举（ALLIES/AXIS）
            health_percent: 健康值0.0-1.0
            
        Returns:
            96x96 pygame Surface
            
        Raises:
            ValueError: unit_type不在枚举中
            ValueError: health_percent不在0.0-1.0范围
        """
        
    def render_portrait_scaled(
        self,
        unit_type: UnitType,
        faction: Faction,
        size: int,
        health_percent: float = 1.0
    ) -> pygame.Surface:
        """生成指定尺寸头像
        
        Args:
            size: 目标尺寸（32/64/96）
            
        Returns:
            size×size pygame Surface
            
        Raises:
            ValueError: size不在[16, 256]范围
        """
        
    def clear_cache(self) -> None:
        """清空缓存"""
        
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计
        
        Returns:
            {"size": int, "hits": int, "misses": int, "hit_rate": float}
        """
```

---

## 2. 输入验证

### 2.1 参数验证规则

| 参数 | 类型 | 有效范围 | 错误处理 |
|------|------|---------|---------|
| unit_type | UnitType | 枚举值 | ValueError: "Invalid unit_type: {value}" |
| faction | Faction | ALLIES/AXIS | ValueError: "Invalid faction: {value}" |
| health_percent | float | [0.0, 1.0] | ValueError: "health_percent must be 0.0-1.0, got {value}" |
| size | int | [16, 256] | ValueError: "size must be 16-256, got {value}" |

### 2.2 验证代码示例

```python
def _validate_inputs(self, unit_type, faction, health_percent):
    if not isinstance(unit_type, UnitType):
        raise ValueError(f"Invalid unit_type: {unit_type}")
    if not isinstance(faction, Faction):
        raise ValueError(f"Invalid faction: {faction}")
    if not 0.0 <= health_percent <= 1.0:
        raise ValueError(f"health_percent must be 0.0-1.0, got {health_percent}")
```

---

## 3. 边界情况处理

### 3.1 健康值边界

| health_percent | 处理方式 |
|----------------|---------|
| 1.0 | 完整头像，金色徽章 |
| 0.75-0.99 | 轻微划痕 |
| 0.50-0.74 | 明显磨损 |
| 0.20-0.49 | 严重破损+灰化25% |
| 0.01-0.19 | 严重破损+灰化50% |
| 0.0 | 完全灰化+红叉 |

### 3.2 缓存边界

```python
# 缓存满时LRU淘汰
if len(self._cache) >= self._max_cache_size:
    oldest_key = next(iter(self._cache))  # 字典保序特性
    del self._cache[oldest_key]
```

### 3.3 尺寸边界

```python
# size限制
if not 16 <= size <= 256:
    raise ValueError(f"size must be 16-256, got {size}")

# 缩放策略
if size < 96:
    surface = pygame.transform.smoothscale(portrait_96, (size, size))
elif size > 96:
    surface = pygame.transform.scale(portrait_96, (size, size))
```

---

## 4. 错误处理策略

### 4.1 异常层次

```python
class PortraitRendererError(Exception):
    """基础异常"""
    pass

class InvalidInputError(PortraitRendererError):
    """输入验证失败"""
    pass

class RenderingError(PortraitRendererError):
    """渲染过程失败"""
    pass
```

### 4.2 容错机制

```python
def render_portrait(self, unit_type, faction, health_percent=1.0):
    try:
        self._validate_inputs(unit_type, faction, health_percent)
        return self._render_portrait_internal(...)
    except InvalidInputError as e:
        logger.error(f"Invalid input: {e}")
        raise  # 向上抛出
    except Exception as e:
        logger.error(f"Rendering failed: {e}")
        # 降级：返回简单占位图标
        return self._render_fallback_portrait(unit_type, faction)

def _render_fallback_portrait(self, unit_type, faction):
    """降级方案：简单彩色方块"""
    surface = pygame.Surface((96, 96))
    color = (0, 150, 0) if faction == Faction.ALLIES else (150, 0, 0)
    surface.fill(color)
    return surface
```

---

## 5. 性能优化

### 5.1 缓存键设计

```python
def _get_cache_key(self, unit_type, faction, health_percent):
    # 健康值量化到5档减少缓存项
    health_level = int(health_percent * 4) * 25  # 0,25,50,75,100
    return f"{unit_type.value}_{faction.value}_{health_level}"
```

**缓存容量计算**:
- 10单位类型 × 2派系 × 5健康档 = 100项
- 每项96x96x4字节 ≈ 37KB
- 总计: 100 × 37KB ≈ **3.7MB**

### 5.2 性能测试要求

```python
def test_performance_first_render():
    renderer = UnitPortraitRenderer()
    start = time.perf_counter()
    portrait = renderer.render_portrait(UnitType.INFANTRY, Faction.ALLIES, 1.0)
    elapsed = time.perf_counter() - start
    assert elapsed < 0.005, f"First render too slow: {elapsed*1000:.2f}ms"

def test_performance_cached_render():
    renderer = UnitPortraitRenderer()
    renderer.render_portrait(UnitType.INFANTRY, Faction.ALLIES, 1.0)  # 预热
    
    start = time.perf_counter()
    portrait = renderer.render_portrait(UnitType.INFANTRY, Faction.ALLIES, 1.0)
    elapsed = time.perf_counter() - start
    assert elapsed < 0.001, f"Cached render too slow: {elapsed*1000:.2f}ms"
```

---

## 6. 测试接口

### 6.1 公共方法测试矩阵

| 方法 | 正常用例 | 边界用例 | 异常用例 |
|------|---------|---------|---------|
| render_portrait() | 10类型×2派系 | health=0.0/1.0 | 非法unit_type |
| render_portrait_scaled() | size=32/64/96 | size=16/256 | size=300 |
| clear_cache() | 清空后重新渲染 | 空缓存清空 | N/A |
| get_cache_stats() | 命中率计算 | 空缓存统计 | N/A |

### 6.2 私有方法测试（通过公共接口）

| 私有方法 | 测试策略 |
|---------|---------|
| _render_background_layer() | 验证背景色正确 |
| _render_helmet() | 验证不同单位头盔样式 |
| _render_wear_texture() | 验证磨损随健康值变化 |

---

## 7. 集成接口

### 7.1 CC2HUD集成点

```python
# cc2_hud.py __init__()
from .unit_portrait_renderer import UnitPortraitRenderer

class CC2HUD:
    def __init__(self, ...):
        self.portrait_renderer = UnitPortraitRenderer(max_cache_size=100)
        self.portrait_renderer.prewarm_cache()  # 预热常用头像

# cc2_hud.py _render_left_panel()
portrait = self.portrait_renderer.render_portrait_scaled(
    unit.unit_type, unit.faction, 
    size=64,
    health_percent=unit.health / unit.max_health
)
screen.blit(portrait, (x, y))

# cc2_hud.py _render_center_panel()
portrait = self.portrait_renderer.render_portrait(
    selected_unit.unit_type,
    selected_unit.faction,
    health_percent=selected_unit.health / selected_unit.max_health
)
screen.blit(portrait, (center_x, 20))
```

---

## 8. 兼容性保证

### 8.1 向后兼容

```python
# 默认参数保证简单调用
portrait = renderer.render_portrait(UnitType.INFANTRY, Faction.ALLIES)
# 等价于
portrait = renderer.render_portrait(UnitType.INFANTRY, Faction.ALLIES, 1.0)
```

### 8.2 未来扩展

```python
def render_portrait(
    self,
    unit_type: UnitType,
    faction: Faction,
    health_percent: float = 1.0,
    **kwargs  # 预留扩展参数
) -> pygame.Surface:
    # kwargs可接受：
    # - animation_frame: int = 0 (未来动画)
    # - render_mode: str = "default" (未来多模式)
    pass
```

---

## 9. 文档要求

### 9.1 类文档

```python
class UnitPortraitRenderer:
    """军事风格单位头像渲染器
    
    生成96x96像素军事风格头像，支持：
    - 10种单位类型
    - 2种派系（ALLIES/AXIS）
    - 5档健康值显示
    - LRU缓存（默认100项）
    
    Examples:
        >>> renderer = UnitPortraitRenderer()
        >>> portrait = renderer.render_portrait(
        ...     UnitType.INFANTRY, Faction.ALLIES, 0.75
        ... )
        >>> portrait.get_size()
        (96, 96)
        
    Performance:
        - First render: <5ms
        - Cached render: <1ms
        - Memory: ~3.7MB for 100 cached portraits
    """
```

### 9.2 方法文档

```python
def render_portrait(self, unit_type, faction, health_percent=1.0):
    """生成单位头像
    
    渲染6层头像：背景→肩章→脸部→头盔→徽章→磨损
    
    Args:
        unit_type: 单位类型，必须是UnitType枚举成员
        faction: 派系，ALLIES或AXIS
        health_percent: 健康值百分比，范围[0.0, 1.0]
            - 1.0: 完整头像
            - 0.5: 明显磨损
            - 0.0: 完全灰化
            
    Returns:
        96x96 pygame.Surface，RGBA格式
        
    Raises:
        ValueError: 参数不在有效范围
        RenderingError: 渲染过程失败
        
    Examples:
        >>> portrait = renderer.render_portrait(
        ...     UnitType.TANK, Faction.AXIS, 0.8
        ... )
    """
```

---

## 10. 验收标准

### 10.1 功能验收

- [ ] 支持10种单位类型
- [ ] 支持2种派系
- [ ] 支持5档健康值显示
- [ ] 三种尺寸(32/64/96)
- [ ] 缓存命中率>90%
- [ ] 降级方案工作

### 10.2 性能验收

- [ ] 首次渲染<5ms
- [ ] 缓存命中<1ms
- [ ] 内存占用<5MB
- [ ] 无内存泄漏

### 10.3 质量验收

- [ ] 单元测试覆盖率≥95%
- [ ] 所有边界情况有测试
- [ ] 异常处理完整
- [ ] 文档完整(类+方法)

---

**文档版本**: v1.0  
**审阅状态**: ✅ 架构师批准  
**下一步**: Phase 5 UI集成设计
