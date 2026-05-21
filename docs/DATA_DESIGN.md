# PyCC2 数据设计文档 **v1.6** (P4)

> **文档版本**: v1.6 | **日期**: 2026-05-19 | **基于产品版本**: v0.6-p4w2

## 1. Pydantic Model 定义 (9个模型)

### 1.1 EngineConfig (TOML 配置)

引擎配置模型，从 `engine.toml` 文件加载。

```python
from pydantic import BaseModel, Field
from typing import Optional

class DisplayConfig(BaseModel):
    logical_w: int = Field(default=1280, ge=640, le=4096)
    logical_h: int = Field(default=720, ge=480, le=2160)
    fullscreen: bool = False
    target_fps: int = Field(default=60, ge=30, le=144)

class GameplayConfig(BaseModel):
    logic_ups: int = Field(default=30, ge=10, le=60)
    game_speed: float = Field(default=1.0, ge=0.25, le=4.0)

class AudioConfig(BaseModel):
    enabled: bool = True
    master_vol: float = Field(default=0.8, ge=0.0, le=1.0)
    music_vol: float = Field(default=0.6, ge=0.0, le=1.0)

class DebugConfig(BaseModel):
    show_fps: bool = False
    debug_overlay: bool = False
    god_mode: bool = False
    dev_mode: bool = False

class PathConfig(BaseModel):
    data_dir: str = "data"
    save_dir: str = "saves"
    log_dir: str = "logs"

class EngineConfig(BaseModel):
    display: DisplayConfig = Field(default_factory=DisplayConfig)
    gameplay: GameplayConfig = Field(default_factory=GameplayConfig)
    audio: AudioConfig = Field(default_factory=AudioConfig)
    debug: DebugConfig = Field(default_factory=DebugConfig)
    paths: PathConfig = Field(default_factory=PathConfig)
```

**字段说明：**

| 分组 | 字段 | 类型 | 默认值 | 约束 | 说明 |
|------|------|------|--------|------|------|
| display | logical_w | int | 1280 | [640, 4096] | 逻辑窗口宽度 |
| display | logical_h | int | 720 | [480, 2160] | 逻辑窗口高度 |
| display | fullscreen | bool | False | - | 全屏模式 |
| display | target_fps | int | 60 | [30, 144] | 目标帧率 |
| gameplay | logic_ups | int | 30 | [10, 60] | 逻辑更新频率(UPS) |
| gameplay | game_speed | float | 1.0 | [0.25, 4.0] | 游戏速度倍率 |
| audio | enabled | bool | True | - | 音频开关 |
| audio | master_vol | float | 0.8 | [0.0, 1.0] | 主音量 |
| audio | music_vol | float | 0.6 | [0.0, 1.0] | 音乐音量 |
| debug | show_fps | bool | False | - | 显示FPS |
| debug | debug_overlay | bool | False | - | 调试覆盖层 |
| debug | god_mode | bool | False | - | 上帝模式 |
| debug | dev_mode | bool | False | - | 开发者模式 |
| paths | data_dir | str | "data" | - | 数据目录 |
| paths | save_dir | str | "saves" | - | 存档目录 |
| paths | log_dir | str | "logs" | - | 日志目录 |

---

### 1.2 TerrainType (IntEnum) + TerrainProps

地形类型枚举和地形属性模型。

```python
from enum import IntEnum
from pydantic import BaseModel, Field

class TerrainType(IntEnum):
    OPEN = 0                # 开阔地
    ROAD = 1                # 道路
    GRASS = 2               # 草地
    WOODS = 3               # 林地
    BUILDING_ENTERABLE = 4  # 可进入建筑
    BUILDING_SOLID = 5      # 实心建筑
    WATER = 6               # 水域
    HEDGE = 7               # 树篱
    WALL = 8                # 墙壁
    ROUGH = 9               # 粗糙地形
    SHALLOW = 10            # 浅水
    BRIDGE = 11             # 桥梁

class TerrainProps(BaseModel):
    movement_cost: float = Field(default=1.0, ge=0.5, le=10.0)
    cover_bonus: float = Field(default=0.0, ge=0.0, le=1.0)
    concealment: float = Field(default=0.0, ge=0.0, le=1.0)
    blocks_los: bool = False
    height: int = Field(default=0, ge=-2, le=10)
    is_passable: bool = True
```

**12种地形属性表：**

| 地形 | 枚举值 | 移动代价 | 掩体加成 | 隐蔽性 | 阻挡视线 | 高度 | 可通行 |
|------|--------|----------|----------|--------|----------|------|--------|
| OPEN (开阔地) | 0 | 1.0 | 0.0 | 0.0 | False | 0 | True |
| ROAD (道路) | 1 | 0.8 | 0.0 | 0.0 | False | 0 | True |
| GRASS (草地) | 2 | 1.2 | 0.05 | 0.15 | False | 0 | True |
| WOODS (林地) | 3 | 2.0 | 0.20 | 0.50 | True | 2 | True |
| BUILDING_ENTERABLE (可进入建筑) | 4 | 1.5 | 0.50 | 0.70 | True | 3 | True |
| BUILDING_SOLID (实心建筑) | 5 | ∞ | 0.80 | 0.90 | True | 4 | False |
| WATER (水域) | 6 | ∞ | 0.00 | 0.05 | False | -1 | False |
| HEDGE (树篱) | 7 | 2.5 | 0.15 | 0.35 | True | 1 | True |
| WALL (墙壁) | 8 | ∞ | 0.70 | 0.80 | True | 2 | False |
| ROUGH (粗糙地形) | 9 | 1.8 | 0.10 | 0.25 | False | 0 | True |
| SHALLOW (浅水) | 10 | 3.0 | 0.05 | 0.10 | False | -1 | True |
| BRIDGE (桥梁) | 11 | 0.9 | 0.00 | 0.00 | False | 0 | True |

---

### 1.3 WeaponConfig

武器配置模型。

```python
from typing import List, Literal, Optional
from pydantic import BaseModel, Field

class WeaponConfig(BaseModel):
    id: str
    name: str
    type: Literal["rifle", "smg", "sniper", "mg", "pistol", "tank_cannon", "sniper_rifle", "mortar"]
    caliber: str
    range_max: int = Field(..., gt=0)
    range_effective: int = Field(..., gt=0, le="range_max")
    accuracy_base: float = Field(default=0.7, ge=0.1, le=1.0)
    spread_base: float = Field(default=5.0, ge=0.0, le=45.0)
    damage_base: int = Field(..., gt=0)
    penetration: int = Field(default=0, ge=0)
    rof: int = Field(..., gt=0, description="Rounds per minute")
    magazine_size: int = Field(..., gt=0)
    reload_time_ticks: int = Field(..., ge=0)
    suppression_value: float = Field(default=0.1, ge=0.0, le=1.0)
    can_indirect: bool = False
    special_tags: List[str] = Field(default_factory=list)
```

**武器类型说明（8种，P3-Fix补全后）：**

| 类型 | 说明 | 典型射程 | 典型ROF | 特点 |
|------|------|----------|---------|------|
| rifle | 步枪 | 400-500m | 30-40 rpm | 精度高，标准步兵武器 |
| smg | 冲锋枪 | 100-200m | 400-600 rpm | 近战高火力，散布大 |
| sniper | 狙击步枪 | 800-1200m | 10-20 rpm | 超远射程，高精度 |
| mg | 通用机枪 | 800-1200m | 600-1200 rpm | 高持续火力，压制强 |
| pistol | 手枪 | 50-100m | 30-40 rpm | 副武器，近距离 |
| tank_cannon | 坦克主炮 | 500-1500m | 6-12 rpm | 超高伤害/穿透，载具专用 |
| sniper_rifle | 反器材狙击枪 | 1000-1500m | 10-15 rpm | 极远射程，反器材/轻装甲 |
| mortar | 迫击炮 | 800-1500m | 8-15 rpm | 间接射击，高压制，曲射弹道 |

---

### 1.4 UnitTemplate

单位模板模型。

```python
from typing import List, Literal, Optional
from pydantic import BaseModel, Field

class UnitTemplate(BaseModel):
    id: str
    name: str
    faction: Literal["allies", "axis"]
    unit_type: Literal[
        "infantry_rifle",
        "infantry_mg",
        "infantry_at",
        "infantry_commander",
        "vehicle_light",
        "vehicle_medium",
        "support_mortar"
    ]
    staff_count_default: int = Field(default=10, ge=1, le=100)
    move_speed: float = Field(default=3.0, ge=0.5, le=20.0)
    base_hp: int = Field(..., gt=0)
    base_morale: int = Field(default=100, ge=0, le=100)
    vision_range: int = Field(default=10, ge=3, le=30)
    weapons: List[str] = Field(..., min_length=1)
    special_abilities: List[str] = Field(default_factory=list)
```

**单位类型说明：**

| 单位类型 | 默认人数 | 移速 | HP | 士气 | 视野 | 典型武器 |
|----------|----------|------|-----|------|------|----------|
| infantry_rifle (步枪兵) | 10 | 3.0 | 100 | 100 | 10 | rifle |
| infantry_mg (机枪组) | 4 | 2.0 | 80 | 90 | 12 | mg |
| infantry_at (反坦克组) | 3 | 2.5 | 70 | 85 | 11 | at_rifle |
| infantry_commander (指挥官) | 1 | 3.0 | 120 | 110 | 14 | pistol/rifle |
| vehicle_light (轻型载具) | 1 | 6.0 | 200 | N/A | 15 | vehicle_gun |
| vehicle_medium (中型载具) | 1 | 4.5 | 350 | N/A | 16 | vehicle_gun |
| support_mortar (迫击炮组) | 4 | 1.5 | 60 | 85 | 13 | mortar |

---

### 1.5 SpawnPoint

出生点模型。

```python
from pydantic import BaseModel, Field
from typing import Literal

class SpawnPoint(BaseModel):
    id: str
    position_x: int = Field(..., ge=0)
    position_y: int = Field(..., ge=0)
    faction: Literal["allies", "axis"]
    spawn_units: List[str] = Field(default_factory=list)
```

---

### 1.6 Objective

目标点模型。

```python
from enum import Enum
from pydantic import BaseModel, Field

class ObjectiveType(str, Enum):
    CAPTURE = "capture"       # 占领
    DEFEND = "defend"         # 防守
    REACH = "reach"           # 到达
    DESTROY = "destroy"       # 摧毁

class Objective(BaseModel):
    id: str
    type: ObjectiveType
    position_x: int = Field(..., ge=0)
    position_y: int = Field(..., ge=0)
    radius: int = Field(default=2, ge=1, le=10)
    time_limit_ticks: Optional[int] = None
    description: str = ""
```

---

### 1.7 TileMapConfig

地图配置模型（含字段验证器）。

```python
from pydantic import BaseModel, Field, field_validator, ValidationInfo
from typing import List
import numpy as np

class TileMapConfig(BaseModel):
    width: int = Field(..., ge=16, le=256)
    height: int = Field(..., ge=16, le=256)
    terrain_grid: List[List[int]]
    spawn_points: List[SpawnPoint]
    objectives: List[Objective]

    @field_validator("terrain_grid")
    @classmethod
    def validate_terrain_grid(cls, v: List[List[int]], info: ValidationInfo) -> List[List[int]]:
        if not v:
            raise ValueError("terrain_grid cannot be empty")

        height = len(v)
        for row_idx, row in enumerate(v):
            if len(row) != len(v[0]):
                raise ValueError(f"Row {row_idx} length mismatch")

            for col_idx, terrain_val in enumerate(row):
                if terrain_val < 0 or terrain_val > 11:
                    raise ValueError(
                        f"Invalid terrain value {terrain_val} at ({row_idx}, {col_idx}). "
                        f"Must be in range [0, 11]"
                    )

        return v

    @field_validator("width", "height")
    @classmethod
    def validate_dimensions(cls, v: int) -> int:
        if not 16 <= v <= 256:
            raise ValueError(f"Dimension must be between 16 and 256, got {v}")
        return v
```

**验证规则：**

| 规则 | 条件 | 错误信息 |
|------|------|----------|
| 宽度范围 | 16 ≤ width ≤ 256 | Dimension must be between 16 and 256 |
| 高度范围 | 16 ≤ height ≤ 256 | Dimension must be between 16 and 256 |
| 地形网格非空 | terrain_grid ≠ [] | terrain_grid cannot be empty |
| 行长度一致 | 所有行等长 | Row X length mismatch |
| 地形值合法 | 0 ≤ value ≤ 11 | Invalid terrain value at (X, Y) |

---

### 1.8 SaveGameData (含 UnitSaveData / SquadSaveData / CampaignState)

存档数据模型。

```python
from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class UnitSaveData(BaseModel):
    unit_id: str
    template_id: str
    position_x: int
    position_y: int
    current_hp: int
    current_morale: int
    ammo_remaining: Dict[str, int]
    status_effects: List[str] = Field(default_factory=list)
    is_alive: bool = True

class SquadSaveData(BaseModel):
    squad_id: str
    units: List[UnitSaveData]
    selected_weapon_index: int = 0
    current_order: str = "idle"
    formation: str = "line"

class CampaignState(BaseModel):
    mission_index: int
    missions_completed: List[str]
    total_score: int = 0
    casualties_allies: int = 0
    casualties_axis: int = 0
    difficulty: str = "normal"

class SaveGameData(BaseModel):
    version: str = "1.0.0"
    timestamp: datetime = Field(default_factory=datetime.now)
    campaign_state: CampaignState
    squads: Dict[str, SquadSaveData]
    game_tick: int = 0
    camera_position: tuple = (0, 0)
    camera_zoom: float = 1.0
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

**存档数据结构：**

```
SaveGameData
├── version: str                    # 存档格式版本
├── timestamp: datetime             # 保存时间戳
├── campaign_state: CampaignState   # 战役状态
│   ├── mission_index: int          # 当前任务索引
│   ├── missions_completed: list    # 已完成任务列表
│   ├── total_score: int            # 总分
│   ├── casualties_allies: int      # 盟军伤亡
│   ├── casualties_axis: int        # 德军伤亡
│   └── difficulty: str             # 难度设置
├── squads: dict                    # 小队字典
│   └── SquadSaveData
│       ├── squad_id: str           # 小队ID
│       ├── units: list             # 单位列表
│       │   └── UnitSaveData
│       │       ├── unit_id: str
│       │       ├── template_id: str
│       │       ├── position: (x, y)
│       │       ├── current_hp: int
│       │       ├── current_morale: int
│       │       ├── ammo_remaining: dict
│       │       ├── status_effects: list
│       │       └── is_alive: bool
│       ├── selected_weapon_index: int
│       ├── current_order: str
│       └── formation: str
├── game_tick: int                  # 当前游戏tick
├── camera_position: tuple          # 相机位置
├── camera_zoom: float              # 相机缩放
└── metadata: dict                  # 扩展元数据
```

---

### 1.9 CampaignState

战役状态模型（已在 SaveGameData 中定义，此处为独立引用）。

```python
# 见上方 SaveGameData 中的 CampaignState 定义
# 支持多任务战役进度追踪
```

---

## 2. 示例数据文件内容

### 2.1 tutorial.json (教学地图)

16x16 地图，适合新手入门任务。

```json
{
  "id": "tutorial",
  "name": "Tutorial Mission",
  "description": "Basic training mission to learn controls",
  "tile_map": {
    "width": 16,
    "height": 16,
    "terrain_grid": [
      [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
      [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
      [0, 0, 3, 3, 0, 0, 0, 0, 0, 0, 0, 0, 5, 5, 0, 0],
      [0, 0, 3, 3, 0, 1, 1, 1, 1, 1, 0, 0, 5, 5, 0, 0],
      [0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
      [0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
      [0, 0, 0, 0, 0, 1, 0, 6, 6, 1, 0, 0, 0, 0, 0, 0],
      [0, 0, 0, 0, 0, 1, 0, 6, 6, 1, 0, 0, 0, 0, 0, 0],
      [0, 0, 0, 0, 0, 1, 11, 11, 11, 1, 0, 0, 0, 0, 0, 0],
      [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0],
      [0, 0, 3, 3, 0, 0, 0, 0, 0, 0, 0, 0, 4, 4, 0, 0],
      [0, 0, 3, 3, 0, 0, 0, 0, 0, 0, 0, 0, 4, 4, 0, 0],
      [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
      [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
      [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
      [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    ],
    "spawn_points": [
      {
        "id": "spawn_allies_1",
        "position_x": 2,
        "position_y": 2,
        "faction": "allies",
        "spawn_units": ["rifle_squad_us"]
      },
      {
        "id": "spawn_allies_2",
        "position_x": 2,
        "position_y": 10,
        "faction": "allies",
        "spawn_units": ["mg_squad_us"]
      },
      {
        "id": "spawn_axis_1",
        "position_x": 13,
        "position_y": 2,
        "faction": "axis",
        "spawn_units": ["rifle_squad_ge"]
      },
      {
        "id": "spawn_axis_2",
        "position_x": 13,
        "position_y": 10,
        "faction": "axis",
        "spawn_units": ["rifle_squad_ge"]
      }
    ],
    "objectives": [
      {
        "id": "obj_building_capture",
        "type": "capture",
        "position_x": 8,
        "position_y": 8,
        "radius": 2,
        "time_limit_ticks": 6000,
        "description": "Capture the central building"
      }
    ]
  }
}
```

**地图元素分布：**

| 地形类型 | 数量 | 占比 | 位置 |
|----------|------|------|------|
| OPEN (开阔地) | ~180 | 70% | 大部分区域 |
| ROAD (道路) | 18 | 7% | 中央横向道路 |
| WOODS (林地) | 12 | 5% | 左上/左下角各一块 |
| BUILDING_ENTERABLE (可进入建筑) | 4 | 1.5% | 右下角 |
| BUILDING_SOLID (实心建筑) | 4 | 1.5% | 右上角 |
| WATER (水域) | 4 | 1.5% | 中央桥梁两侧 |
| BRIDGE (桥梁) | 3 | 1.2% | 横跨水域 |

---

### 2.2 rifle_squad_us.json (美军步枪班)

M1 Garand 步枪班，标准10人编制。

```json
{
  "id": "rifle_squad_us",
  "name": "US Rifle Squad",
  "faction": "allies",
  "unit_type": "infantry_rifle",
  "staff_count_default": 10,
  "move_speed": 3.0,
  "base_hp": 100,
  "base_morale": 100,
  "vision_range": 10,
  "weapons": ["m1_garand"],
  "special_abilities": ["grenade_throw", "rush"],
  "description": "Standard US Army rifle squad with M1 Garand rifles"
}
```

**单位属性：**

| 属性 | 值 | 说明 |
|------|-----|------|
| 编制人数 | 10人 | 标准二战美军步枪班 |
| 移动速度 | 3.0 tiles/tick | 标准步兵移速 |
| 生命值 | 100 HP | 基础生命值 |
| 初始士气 | 100 | 满士气开始 |
| 视野范围 | 10 tiles | 标准视野 |
| 主武器 | M1 Garand | 半自动步枪 |
| 特殊能力 | 手榴弹投掷、冲锋 | 战术技能 |

---

### 2.3 m1_garand.json (M1 Garand 步枪)

美国陆军制式半自动步枪。

```json
{
  "id": "m1_garand",
  "name": "M1 Garand",
  "type": "rifle",
  "caliber": ".30-06 Springfield",
  "range_max": 550,
  "range_effective": 400,
  "accuracy_base": 0.75,
  "spread_base": 3.5,
  "damage_base": 35,
  "penetration": 12,
  "rof": 40,
  "magazine_size": 8,
  "reload_time_ticks": 30,
  "suppression_value": 0.15,
  "can_indirect": false,
  "special_tags": ["semi_auto", "reliable", "standard_issue"]
}
```

**武器性能参数：**

| 参数 | 值 | 说明 |
|------|-----|------|
| 口径 | .30-06 Springfield | 7.62×63mm |
| 最大射程 | 550 m | 理论最大距离 |
| 有效射程 | 400 m | 最佳作战距离 |
| 基础精度 | 75% | 标准命中率 |
| 散布角度 | 3.5° | 弹道散布 |
| 基础伤害 | 35 HP | 单发伤害 |
| 穿透力 | 12 | 装甲穿透值 |
| 射速 | 40 RPM | 每分钟发射数 |
| 弹匣容量 | 8 发 | en-bloc clip |
| 装填时间 | 30 ticks | 约1.5秒 |
| 压制值 | 0.15 | 士气压制效果 |

---

### 2.4 mg42.json (MG42 通用机枪)

德军标志性通用机枪。

```json
{
  "id": "mg42",
  "name": "MG42",
  "type": "machine_gun",
  "caliber": "7.92×57mm Mauser",
  "range_max": 1200,
  "range_effective": 800,
  "accuracy_base": 0.65,
  "spread_base": 8.0,
  "damage_base": 28,
  "penetration": 10,
  "rof": 1200,
  "magazine_size": 50,
  "reload_time_ticks": 60,
  "suppression_value": 0.45,
  "can_indirect": false,
  "special_tags": ["high_rof", "suppressing_fire", "barrel_overheat"]
}
```

**武器性能对比：M1 Garand vs MG42：**

| 参数 | M1 Garand | MG42 | 差异说明 |
|------|-----------|------|----------|
| 类型 | 步枪 | 机枪 | 定位不同 |
| 有效射程 | 400m | 800m | MG42 远程优势 |
| 精度 | 75% | 65% | 步枪精度更高 |
| 散布 | 3.5° | 8.0° | 连发散布更大 |
| 伤害 | 35 | 28 | 步枪单发更高 |
| 射速 | 40 RPM | 1200 RPM | MG42 压倒性优势 |
| 弹容量 | 8 发 | 50 发 | MG42 持续火力强 |
| 压制值 | 0.15 | 0.45 | MG42 压制能力突出 |

---

### 2.5 engine.toml (默认引擎配置)

TOML 格式的引擎配置文件。

```toml
[display]
logical_w = 1280
logical_h = 720
fullscreen = false
target_fps = 60

[gameplay]
logic_ups = 30
game_speed = 1.0

[audio]
enabled = true
master_vol = 0.8
music_vol = 0.6

[debug]
show_fps = false
debug_overlay = false
god_mode = false
dev_mode = false

[paths]
data_dir = "data"
save_dir = "saves"
log_dir = "logs"
```

**配置文件加载流程：**

```
engine.toml → TOML解析 → EngineConfig Pydantic校验 → 运行时使用
     ↓
  缺失字段 → 使用默认值
     ↓
  无效值 → 抛出 ValidationError
```

---

## 3. 数据完整性约束规则表

### 3.1 模型级约束

| 模型 | 约束类型 | 规则描述 | 优先级 | 处理方式 |
|------|----------|----------|--------|----------|
| EngineConfig | Range | display尺寸在合理范围内 | P0 | ValidationError |
| EngineConfig | Type | FPS/UPS为正整数 | P0 | ValidationError |
| TerrainType | Enum | 必须是12种预定义值之一 | P0 | ValueError |
| TerrainProps | Range | movement_cost ∈ [0.5, 10.0] | P0 | ValidationError |
| TerrainProps | Range | cover_bonus/concealment ∈ [0, 1] | P0 | ValidationError |
| WeaponConfig | Range | range_max > range_effective > 0 | P0 | ValidationError |
| WeaponConfig | Range | accuracy_base ∈ [0.1, 1.0] | P0 | ValidationError |
| WeaponConfig | Range | rof > 0, magazine_size > 0 | P0 | ValidationError |
| UnitTemplate | Range | staff_count ∈ [1, 100] | P0 | ValidationError |
| UnitTemplate | NonEmpty | weapons列表至少1个元素 | P0 | ValidationError |
| TileMapConfig | Range | w/h ∈ [16, 256] | P0 | ValidationError + field_validator |
| TileMapConfig | Shape | terrain_grid矩形且匹配w/h | P0 | ValidationError |
| TileMapConfig | Value | terrain值 ∈ [0, 11] | P0 | ValidationError |
| SaveGameData | Type | 时间戳自动生成 | P1 | 自动填充 |
| SaveGameData | Reference | squad/unit ID唯一性 | P1 | 应用层检查 |

### 3.2 引用完整性约束

| 源模型 | 目标模型 | 约束规则 | 校验时机 |
|--------|----------|----------|----------|
| UnitTemplate.weapons | WeaponConfig.id | 武器ID必须存在 | 加载时 |
| TileMapConfig.spawn_points.faction | UnitTemplate.faction | 阵营匹配 | 任务初始化 |
| SaveGameData.squads.units.template_id | UnitTemplate.id | 模板存在 | 读档时 |
| SpawnPoint.spawn_units | UnitTemplate.id | 模板存在 | 任务初始化 |
| CampaignState.missions_completed | Mission.id | 任务ID有效 | 战役推进 |

### 3.3 业务规则约束

| 规则ID | 规则描述 | 影响范围 | 校验方式 |
|--------|----------|----------|----------|
| BR-01 | 同一位置最多1个单位 | 地图网格 | 碰撞检测 |
| BR-02 | 单位HP ≤ base_hp | 战斗系统 | 上界约束 |
| BR-03 | 士气 ∈ [0, 100] | 士气系统 | clamp处理 |
| BR-04 | 弹药 ≥ 0 且 ≤ magazine_size | 弹药系统 | 边界检查 |
| BR-05 | 相机缩放 ∈ [0.5x, 3.0x] | 渲染系统 | clamp处理 |
| BR-06 | 游戏tick单调递增 | 时间系统 | 只增不减 |
| BR-07 | 存档版本兼容性 | 存档系统 | 版本迁移 |
| BR-08 | 阵营单位数量平衡 | 任务设计 | 设计时检查 |

### 3.4 数据流验证节点

```
JSON/TOML文件
    ↓
[1] 文件格式验证 (语法正确性)
    ↓
[2] Schema验证 (Pydantic Model)
    ↓
[3] 业务规则验证 (应用层)
    ↓
[4] 引用完整性验证 (跨模型)
    ↓
✅ 验证通过 → 内存对象可用
❌ 验证失败 → 详细错误信息 + 回滚
```

### 3.5 异常分类与处理策略

| 异常类 | 触发条件 | 严重程度 | 用户提示 | 恢复方案 |
|--------|----------|----------|----------|----------|
| ValidationError | 字段值非法 | **致命** | "配置文件有误" | 终止启动 |
| ValueError | 枚举值无效 | **致命** | "数据格式错误" | 使用默认值 |
| FileNotFoundError | 文件缺失 | **严重** | "找不到资源" | 降级运行 |
| SaveCorruptedError | 存档损坏 | **中等** | "存档已损坏" | 删除/备份恢复 |
| SaveVersionError | 版本不兼容 | **低** | "需要转换" | 自动迁移 |
| KeyError | 引用缺失 | **严重** | "数据不完整" | 跳过该条目 |
| JSONDecodeError | JSON解析失败 | **致命** | "文件损坏" | 终止操作 |

---

## 附录 A: 数据文件目录结构

```
PyCC2/
├── data/
│   ├── maps/
│   │   ├── tutorial.json
│   │   ├── mission_1.json
│   │   └── ...
│   ├── units/
│   │   ├── rifle_squad_us.json
│   │   ├── mg_squad_us.json
│   │   ├── rifle_squad_ge.json
│   │   └── ...
│   ├── weapons/
│   │   ├── m1_garand.json
│   │   ├── mg42.json
│   │   ├── mp40.json
│   │   └── ...
│   └── config/
│       └── engine.toml
├── saves/
│   ├── save_001.sav
│   ├── save_002.sav
│   └── autosave.sav
└── logs/
    ├── game_2024-01-01.log
    └── error.log
```

## 附录 B: 版本历史

| 版本 | 日期 | 作者 | 变更内容 |
|------|------|------|----------|
| v1.0 | 2024-01 | PyCC2 Team | 初始版本，定义9个核心数据模型 |
| v1.1 | 2026-05-18 | Data Designer | Consensus Review修订: EngineConfig默认值对齐, 版本表同步 |
| v1.2 | 2025-05-18 | Data Designer | P3-Fix: WeaponConfig类型补全为8种(新增sniper/mg/pistol/tank_cannon/sniper_rifle), 移除过时at_gun/vehicle_gun, 武器表同步更新 |

## 附录 C: 相关文档

- [交互设计规范](./VISUAL_SPEC.md) - UI/UX布局与视觉规范
- [安全评审报告](./SECURITY.md) - 安全威胁分析与缓解措施
- [测试计划](./TEST_PLAN.md) - 测试策略与覆盖率目标
