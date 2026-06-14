"""
步兵渲染系统 (Infantry Rendering System)

从 pixel_artist_3d.py 中提取的步兵/角色渲染逻辑。
负责统一管理所有步兵相关的像素艺术生成，包括：
- 基础步兵精灵生成
- 受伤状态叠加层
- 方向性参数计算
- 武器绘制
- 趴伏/死亡状态
- 动画帧表生成
- 动画状态管理

职责分离：
- PixelArtist3D: 主协调器（保留载具/环境渲染）
- InfantryRenderer: 步兵专用渲染逻辑

Created: v0.3.10 (extracted from pixel_artist_3d.py ~600 lines)
"""

from __future__ import annotations

import logging
import math
from enum import Enum, auto
from typing import TYPE_CHECKING

import pygame

from pycc2.domain.entities.unit import Faction
from pycc2.domain.value_objects.direction import Direction
from pycc2.presentation.rendering.pixel_artist_enums import InfantryType

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    pass


class InfantryAnimationState(Enum):
    """步兵动画状态枚举"""

    IDLE = auto()
    WALKING = auto()
    RUNNING = auto()
    SHOOTING = auto()
    RELOADING = auto()
    DYING = auto()
    DEAD = auto()
    PRONE = auto()


class InfantryRenderer:
    """
    步兵像素艺术渲染器。

    封装所有步兵相关的精灵生成逻辑，提供清晰的接口给 PixelArtist3D 调用。

    使用示例:
        renderer = InfantryRenderer()
        sprite = renderer.create_infantry_sprite(
            infantry_type=InfantryType.RIFLEMAN,
            faction=Faction.ALLIES,
            direction=Direction.SOUTH
        )
    """

    # CC2 步兵基础调色板 (从原版截图分析)
    ALLIES_BASE_COLOR = (98, 115, 82)  # 盟军：橄榄绿
    AXIS_BASE_COLOR = (119, 111, 95)  # 轴心国：灰绿色

    # 身体部位颜色偏移
    SKIN_TONE = (210, 175, 145)  # 肤色
    HELMET_COLOR_ALLIES = (72, 86, 63)  # 盔甲绿（盟军）
    HELMET_COLOR_AXIS = (105, 100, 85)  # 灰色（轴心国）
    BOOT_COLOR = (62, 50, 42)  # 棕色靴子
    GEAR_COLOR = (80, 75, 65)  # 装备灰褐色

    # 武器颜色
    WEAPON_METAL = (120, 120, 118)  # 金属灰色
    WOOD_STOCK = (139, 109, 76)  # 木托

    def __init__(self, base_size: int = 24):
        """
        初始化步兵渲染器。

        Args:
            base_size: 基础精灵尺寸（默认24x24像素，CC2标准）
        """
        self.base_size = base_size
        self._body_surf: pygame.Surface | None = None

    def create_infantry_sprite(
        self,
        infantry_type: InfantryType = InfantryType.RIFLEMAN,
        faction: Faction = Faction.ALLIES,
        direction: Direction = Direction.SOUTH,
        animation_state: InfantryAnimationState = InfantryAnimationState.IDLE,
        is_wounded: bool = False,
        frame_offset: int = 0,
    ) -> pygame.Surface:
        """
        创建步兵精灵（主入口方法）。

        根据步兵类型、阵营、方向和动画状态生成 CC2 风格的像素艺术精灵。

        Args:
            infantry_type: 步兵类型（步枪手/MG/反坦克等）
            faction: 阵营（盟军/轴心国）
            direction: 面向方向（8方向）
            animation_state: 动画状态（待机/移动/射击/死亡等）
            is_wounded: 是否受伤（会显示绷带/血迹效果）
            frame_offset: 动画帧偏移（用于动画循环）

        Returns:
            24×24 像素的 Pygame Surface
        """
        size = self.base_size
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        surface.fill((0, 0, 0, 0))  # 透明背景

        # 选择基础颜色
        if faction == Faction.ALLIES:
            base_color = self.ALLIES_BASE_COLOR
            helmet_color = self.HELMET_COLOR_ALLIES
        else:
            base_color = self.AXIS_BASE_COLOR
            helmet_color = self.HELMET_COLOR_AXIS

        # 获取方向参数
        dir_params = self._get_direction_params(direction)

        # 绘制身体各部位（按层次顺序）
        # 1. 腿部（最底层）
        if animation_state in [InfantryAnimationState.WALKING, InfantryAnimationState.RUNNING]:
            self._draw_legs(surface, dir_params, base_color, frame_offset)
        elif animation_state == InfantryAnimationState.PRONE:
            self._draw_infantry_prone_topdown(surface, dir_params, base_color, faction)
        elif animation_state in [InfantryAnimationState.DYING, InfantryAnimationState.DEAD]:
            self._draw_infantry_death_topdown(
                surface,
                dir_params,
                base_color,
                faction,
                animation_state == InfantryAnimationState.DEAD,
            )
        else:
            # 待机/站立姿势
            self._draw_body(surface, dir_params, base_color, helmet_color)

        # 2. 武器（在身体上层）
        if animation_state not in [InfantryAnimationState.DYING, InfantryAnimationState.DEAD]:
            weapon_type = self._get_weapon_for_type(infantry_type)
            self._draw_infantry_weapon(
                surface, dir_params, weapon_type, animation_state == InfantryAnimationState.SHOOTING
            )

        # 3. 头部/头盔（最上层）
        if animation_state not in [
            InfantryAnimationState.PRONE,
            InfantryAnimationState.DYING,
            InfantryAnimationState.DEAD,
        ]:
            self._draw_head(surface, dir_params, helmet_color, self.SKIN_TONE)

        # 应用受伤效果叠加层
        if is_wounded:
            surface = self.apply_wounded_overlay(surface)

        return surface

    def apply_wounded_overlay(self, surface: pygame.Surface) -> pygame.Surface:
        """
        为角色添加受伤效果叠加层。

        效果包括：
        - 绷带纹理（白色/米色像素点）
        - 血迹效果（暗红色半透明区域）
        - 轻微的颜色变暗（模拟失血）

        Args:
            surface: 输入精灵表面

        Returns:
            应用了受伤效果的表面（新实例）
        """
        result = surface.copy()
        w, h = result.get_size()

        # 添加随机血迹像素
        import random

        random.seed(42)  # 固定种子保证一致性

        for _ in range(5):  # 5个血迹点
            x = random.randint(2, w - 3)
            y = random.randint(4, h - 2)

            # 暗红色半透明圆点
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    if 0 <= x + dx < w and 0 <= y + dy < h:
                        alpha = 100 if (dx == 0 and dy == 0) else 50
                        result.set_at((x + dx, y + dy), (139, 0, 0, alpha))

        # 添加绷带效果（浅色条纹）
        bandage_y = h // 2
        for x in range(3, w - 3, 3):
            if x % 6 == 0:
                result.set_at((x, bandage_y), (240, 230, 210, 180))
                result.set_at((x, bandage_y + 1), (240, 230, 210, 150))

        return result

    def _get_direction_params(self, direction: Direction) -> dict:
        """
        获取方向的渲染参数。

        返回包含以下信息的字典：
        - body_offset: 身体中心偏移
        - facing_x/y: 面向向量
        - flip_horizontal: 是否水平翻转
        - visibility: 可见性因子（背面时降低）

        Args:
            direction: 方向枚举

        Returns:
            参数字典
        """
        params = {
            Direction.NORTH: {
                "body_offset": (12, 8),
                "facing": (0, -1),
                "flip": False,
                "visibility": 0.7,  # 背面略暗
            },
            Direction.SOUTH: {
                "body_offset": (12, 14),
                "facing": (0, 1),
                "flip": False,
                "visibility": 1.0,  # 正面全亮
            },
            Direction.EAST: {
                "body_offset": (14, 12),
                "facing": (1, 0),
                "flip": False,
                "visibility": 0.9,
            },
            Direction.WEST: {
                "body_offset": (10, 12),
                "facing": (-1, 0),
                "flip": True,
                "visibility": 0.9,
            },
            Direction.NORTHEAST: {
                "body_offset": (13, 9),
                "facing": (0.7, -0.7),
                "flip": False,
                "visibility": 0.8,
            },
            Direction.SOUTHEAST: {
                "body_offset": (13, 13),
                "facing": (0.7, 0.7),
                "flip": False,
                "visibility": 0.95,
            },
            Direction.SOUTHWEST: {
                "body_offset": (11, 13),
                "facing": (-0.7, 0.7),
                "flip": True,
                "visibility": 0.95,
            },
            Direction.NORTHWEST: {
                "body_offset": (11, 9),
                "facing": (-0.7, -0.7),
                "flip": True,
                "visibility": 0.8,
            },
        }

        return params.get(direction, params[Direction.SOUTH])

    def _draw_body(
        self, surface: pygame.Surface, params: dict, base_color: tuple, helmet_color: tuple
    ) -> None:
        """绘制站立姿态的身体。"""
        cx, cy = params["body_offset"]
        vis = params["visibility"]

        # 调整颜色亮度基于可见性
        body_color = tuple(int(c * vis) for c in base_color)

        # 躯干（椭圆形简化为矩形）
        body_rect = pygame.Rect(cx - 4, cy - 2, 8, 10)
        pygame.draw.rect(surface, body_color, body_rect)

        # 腿部（两条腿）
        leg_color = tuple(max(0, int(c * 0.9 * vis)) for c in base_color)
        pygame.draw.rect(surface, leg_color, (cx - 3, cy + 7, 2, 6))  # 左腿
        pygame.draw.rect(surface, leg_color, (cx + 1, cy + 7, 2, 6))  # 右腿

    def _draw_head(
        self, surface: pygame.Surface, params: dict, helmet_color: tuple, skin_color: tuple
    ) -> None:
        """绘制头部和头盔。"""
        cx, cy = params["body_offset"]
        vis = params["visibility"]

        # 头盔（圆形）
        helmet_radius = 4
        helmet_color_adj = tuple(int(c * vis) for c in helmet_color)
        pygame.draw.circle(surface, helmet_color_adj, (cx, cy - 5), helmet_radius)

        # 脸部可见部分（仅正面和侧面）
        if vis > 0.8:
            face_color = tuple(int(c * vis) for c in skin_color)
            pygame.draw.circle(surface, face_color, (cx, cy - 3), 2)

    def _draw_legs(
        self, surface: pygame.Surface, params: dict, base_color: tuple, frame_offset: int
    ) -> None:
        """绘制行走/跑步状态的腿部动画。"""
        cx, cy = params["body_offset"]

        # 简单的腿部摆动动画
        swing = math.sin(frame_offset * 0.5) * 3  # 摆动幅度

        leg_color = tuple(int(c * 0.9) for c in base_color)

        # 左腿
        left_leg_x = cx - 3 + int(swing)
        pygame.draw.rect(surface, leg_color, (left_leg_x, cy + 7, 2, 6))

        # 右腿（相位差180度）
        right_leg_x = cx + 1 - int(swing)
        pygame.draw.rect(surface, leg_color, (right_leg_x, cy + 7, 2, 6))

    def _draw_infantry_weapon(
        self, surface: pygame.Surface, params: dict, weapon_type: str, is_firing: bool = False
    ) -> None:
        """
        绘制步兵武器。

        支持多种武器类型：
        - rifle: 步枪（M1 Garand / Kar98k）
        - mg: 机枪（Bren / MG42）
        - at: 反坦克火箭（Bazooka / Panzerschreck）
        - smg: 冲锋枪（Thompson / MP40）
        - sniper: 狙击枪（Springfield / KAR98k狙击版）

        Args:
            surface: 目标表面
            params: 方向参数
            weapon_type: 武器类型字符串
            is_firing: 是否正在射击（显示枪口焰）
        """
        cx, cy = params["body_offset"]
        fx, fy = params["facing"]

        # 武器基础位置（右手位置）
        weapon_x = cx + int(fx * 6)
        weapon_y = cy + int(fy * 2)

        # 根据武器类型调整大小和形状
        if weapon_type == "rifle":
            # 步枪：长条形
            length = 14
            end_x = weapon_x + int(fx * length)
            end_y = weapon_y + int(fy * length)
            pygame.draw.line(surface, self.WEAPON_METAL, (weapon_x, weapon_y), (end_x, end_y), 2)
            # 枪托
            stock_x = weapon_x - int(fx * 3)
            stock_y = weapon_y - int(fy * 1)
            pygame.draw.line(surface, self.WOOD_STOCK, (weapon_x, weapon_y), (stock_x, stock_y), 2)

        elif weapon_type == "mg":
            # 机枪：更粗更长
            length = 16
            end_x = weapon_x + int(fx * length)
            end_y = weapon_y + int(fy * length)
            pygame.draw.line(surface, self.WEAPON_METAL, (weapon_x, weapon_y), (end_x, end_y), 3)
            # 两脚架
            bipod_y = weapon_y + 4
            pygame.draw.line(
                surface, self.WEAPON_METAL, (weapon_x - 2, bipod_y), (weapon_x - 4, bipod_y + 4), 1
            )
            pygame.draw.line(
                surface, self.WEAPON_METAL, (weapon_x + 2, bipod_y), (weapon_x + 4, bipod_y + 4), 1
            )

        elif weapon_type == "at":
            # 反坦克火箭：短粗 + 圆筒发射器
            tube_length = 8
            end_x = weapon_x + int(fx * tube_length)
            end_y = weapon_y + int(fy * tube_length)
            pygame.draw.line(surface, self.WEAPON_METAL, (weapon_x, weapon_y), (end_x, end_y), 4)
            # 护木
            pygame.draw.rect(surface, self.WOOD_STOCK, (weapon_x - 2, weapon_y - 1, 4, 3))

        elif weapon_type == "smg":
            # 冲锋枪：中等长度
            length = 10
            end_x = weapon_x + int(fx * length)
            end_y = weapon_y + int(fy * length)
            pygame.draw.line(surface, self.WEAPON_METAL, (weapon_x, weapon_y), (end_x, end_y), 2)
            # 弹匣
            mag_x = weapon_x + int(fx * 4)
            mag_y = weapon_y + 2
            pygame.draw.rect(surface, self.WEAPON_METAL, (mag_x, mag_y, 2, 4))

        elif weapon_type == "sniper":
            # 狙击枪：长 + 瞄准镜
            length = 16
            end_x = weapon_x + int(fx * length)
            end_y = weapon_y + int(fy * length)
            pygame.draw.line(surface, self.WEAPON_METAL, (weapon_x, weapon_y), (end_x, end_y), 2)
            # 瞄准镜（中段凸起）
            scope_x = weapon_x + int(fx * 8)
            scope_y = weapon_y + int(fy * 8) - 1
            pygame.draw.circle(surface, (80, 80, 80), (scope_x, scope_y), 2)

        # 枪口焰效果
        if is_firing:
            muzzle_x = end_x + int(fx * 3)
            muzzle_y = end_y + int(fy * 3)
            # 黄橙色闪光
            pygame.draw.circle(surface, (255, 200, 50), (muzzle_x, muzzle_y), 3)
            pygame.draw.circle(surface, (255, 100, 0), (muzzle_x, muzzle_y), 2)

    def _draw_infantry_prone_topdown(
        self, surface: pygame.Surface, params: dict, base_color: tuple, faction: Faction
    ) -> None:
        """
        绘制趴伏状态的步兵俯视图。

        趴伏时身体呈水平椭圆状，更贴近地面，
        适合利用掩体的战术动作。

        Args:
            surface: 目标表面
            params: 方向参数
            base_color: 基础颜色
            faction: 阵营
        """
        cx, cy = params["body_offset"]
        vis = params["visibility"]
        body_color = tuple(int(c * vis) for c in base_color)

        # 身体（水平椭圆，用多边形近似）
        points = [
            (cx - 8, cy),  # 头部左侧
            (cx + 6, cy - 2),  # 脚部右侧
            (cx + 6, cy + 2),  # 脚部右下
            (cx - 8, cy + 4),  # 头部右下
        ]
        pygame.draw.polygon(surface, body_color, points)

        # 头部（小圆）
        head_x = cx - 6
        head_color = (
            self.HELMET_COLOR_ALLIES if faction == Faction.ALLIES else self.HELMET_COLOR_AXIS
        )
        head_color = tuple(int(c * vis) for c in head_color)
        pygame.draw.circle(surface, head_color, (head_x, cy + 2), 3)

    def _draw_infantry_death_topdown(
        self,
        surface: pygame.Surface,
        params: dict,
        base_color: tuple,
        faction: Faction,
        is_dead: bool = False,
    ) -> None:
        """
        绘制死亡状态的步兵俯视图。

        分两个阶段：
        - DYING: 正在倒下（倾斜姿态）
        - DEAD: 完全倒地（水平姿态，颜色变暗）

        Args:
            surface: 目标表面
            params: 方向参数
            base_color: 基础颜色
            faction: 阵营
            is_dead: 是否完全死亡
        """
        cx, cy = params["body_offset"]

        # 死亡时颜色变暗
        darkness = 0.5 if is_dead else 0.7
        body_color = tuple(int(c * darkness) for c in base_color)

        if is_dead:
            # 完全倒地：水平姿态
            points = [
                (cx - 6, cy + 2),
                (cx + 8, cy),
                (cx + 8, cy + 3),
                (cx - 6, cy + 5),
            ]
            pygame.draw.polygon(surface, body_color, points)

            # 武器掉落在一旁
            weapon_color = (100, 100, 98)
            pygame.draw.line(surface, weapon_color, (cx + 4, cy + 1), (cx + 9, cy + 4), 1)
        else:
            # 正在倒下：倾斜姿态
            tilt_angle = 30  # 倾斜角度

            # 简化表示：用旋转的矩形
            if self._body_surf is None:
                self._body_surf = pygame.Surface((10, 6), pygame.SRCALPHA)
            self._body_surf.fill((0, 0, 0, 0))
            self._body_surf.fill(body_color)
            rotated = pygame.transform.rotate(self._body_surf, tilt_angle)

            rot_rect = rotated.get_rect(center=(cx, cy))
            surface.blit(rotated, rot_rect.topleft)

    def _get_weapon_for_type(self, infantry_type: InfantryType) -> str:
        """根据步兵类型获取对应武器类型。"""
        weapon_map = {
            InfantryType.RIFLEMAN: "rifle",
            InfantryType.MG: "mg",
            InfantryType.AT: "at",
            InfantryType.OFFICER: "smg",  # 冲锋枪
            InfantryType.SNIPER: "sniper",
            InfantryType.MEDIC: "smg",  # 卡宾枪/冲锋枪
            InfantryType.ENGINEER: "smg",  # 工程师冲锋枪
        }
        return weapon_map.get(infantry_type, "rifle")

    def create_infantry_animation_sheet(
        self,
        infantry_type: InfantryType = InfantryType.RIFLEMAN,
        faction: Faction = Faction.ALLIES,
        include_all_states: bool = True,
    ) -> dict[InfantryAnimationState, list[pygame.Surface]]:
        """
        创建完整的步兵动画帧表。

        生成所有方向和动画状态的精灵组合，
        用于高效的动画切换。

        Args:
            infantry_type: 步兵类型
            faction: 阵营
            include_all_states: 是否包含所有状态（否则只生成IDLE/WALKING）

        Returns:
            字典：{动画状态: [8个方向的精灵列表]}
        """
        states = (
            list(InfantryAnimationState)
            if include_all_states
            else [InfantryAnimationState.IDLE, InfantryAnimationState.WALKING]
        )

        animation_sheet = {}

        for state in states:
            direction_sprites = []
            for direction in Direction:
                # 计算帧偏移（用于行走/跑步动画）
                frame_offset = (
                    0
                    if state == InfantryAnimationState.IDLE
                    else list(Direction).index(direction) * 2
                )

                sprite = self.create_infantry_sprite(
                    infantry_type=infantry_type,
                    faction=faction,
                    direction=direction,
                    animation_state=state,
                    frame_offset=frame_offset,
                )
                direction_sprites.append(sprite)

            animation_sheet[state] = direction_sprites

        return animation_sheet


class InfantryAnimator:
    """
    步兵动画状态管理器。

    控制单位的动画状态切换，支持：
    - 平滑的状态过渡
    - 动画帧率控制
    - 方向变化时的插值
    """

    def __init__(self, fps: int = 8):
        """
        初始化动画管理器。

        Args:
            fps: 动画帧率（默认8 FPS，CC2风格低帧率动画）
        """
        self.fps = fps
        self.current_state = InfantryAnimationState.IDLE
        self.current_direction = Direction.SOUTH
        self.frame_counter = 0
        self.state_timer = 0  # 状态持续时间计数器

    def update(self, dt_ms: int = 16) -> None:
        """
        更新动画状态。

        Args:
            dt_ms: 帧间隔时间（毫秒）
        """
        self.frame_counter += 1
        self.state_timer += dt_ms

        # 自动状态转换规则
        if self.current_state == InfantryAnimationState.SHOOTING:
            if self.state_timer > 300:  # 射击持续300ms
                self.transition_to(InfantryAnimationState.IDLE)

        elif self.current_state == InfantryAnimationState.DYING:
            if self.state_timer > 1000:  # 死亡动画1秒后变为DEAD
                self.transition_to(InfantryAnimationState.DEAD)

    def transition_to(self, new_state: InfantryAnimationState) -> None:
        """
        过渡到新的动画状态。

        Args:
            new_state: 目标状态
        """
        if new_state != self.current_state:
            self.current_state = new_state
            self.state_timer = 0
            self.frame_counter = 0

    def set_direction(self, direction: Direction) -> None:
        """设置面向方向。"""
        self.current_direction = direction

    def get_current_frame_index(self) -> int:
        """
        获取当前动画帧索引。

        Returns:
            帧索引（基于帧计数器和FPS计算）
        """
        return (self.frame_counter // (60 // self.fps)) % 8
