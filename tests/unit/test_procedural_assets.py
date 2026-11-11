"""G5 验收：程序化美术兜底可用，且 HUD 只有单一入口。

背景（W3）：
- 运行时优先读取外部 PixVoxel PNG 与 SVG。用户决定保留该优先级。
- 因此 G5 的验收口径是「断开所有外部素材后，程序化生成仍然完整可用」。
- 本文件强制关闭 PixVoxel / SVG / CC2 外部精灵，并打桩 AssetLoader。
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()

from pycc2.domain.value_objects.building_data import CC2BuildingType
from pycc2.presentation.rendering.cc2_building_renderer import render_cc2_building
from pycc2.presentation.rendering.sprite_cache_manager import SpriteCacheManager

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src" / "pycc2"

ALL_UNIT_TYPES = [
    "INFANTRY_SQUAD",
    "MACHINE_GUN_SQUAD",
    "COMMANDER",
    "MORTAR_TEAM",
    "TANK",
    "SNIPER_TEAM",
    "MEDIC_TEAM",
    "AT_GUN_TEAM",
]

FACTIONS = ["allies", "axis", "polish"]

# 允许调用 pygame.image.load 的模块（外部素材边界）。
IMAGE_LOAD_WHITELIST = {
    "asset_loader.py",
    "cc2_sprite_loader.py",
    "pixvoxel_loader.py",
    "direction_sprite.py",
}


@pytest.fixture()
def procedural_manager(pygame_display, monkeypatch):
    """返回只走程序化路径的 SpriteCacheManager。"""
    manager = SpriteCacheManager()
    manager._use_pixvoxel_sprites = False
    manager._use_svg_sprites = False
    manager._use_cc2_sprites = False
    monkeypatch.setattr(manager._asset_loader, "load_unit_sprite", lambda **kwargs: None)
    return manager


def _has_visible_pixels(surface: pygame.Surface) -> bool:
    rect = surface.get_bounding_rect()
    return rect.width > 0 and rect.height > 0


class TestProceduralUnitSprites:
    """断开外部素材后，每类单位仍有可见的程序化精灵。"""

    @pytest.mark.parametrize("faction", FACTIONS)
    @pytest.mark.parametrize("unit_type", ALL_UNIT_TYPES)
    def test_every_unit_type_is_non_empty(self, procedural_manager, faction, unit_type):
        for direction in range(8):
            sprite = procedural_manager.create_unit_sprite(faction, unit_type, direction)
            assert sprite is not None, f"{faction}/{unit_type}/d{direction} 无精灵"
            assert _has_visible_pixels(sprite), f"{faction}/{unit_type}/d{direction} 精灵为空"

    @pytest.mark.parametrize(
        ("left", "right"),
        [
            ("MACHINE_GUN_SQUAD", "INFANTRY_SQUAD"),
            ("COMMANDER", "INFANTRY_SQUAD"),
            ("MEDIC_TEAM", "INFANTRY_SQUAD"),
            ("TANK", "AT_GUN_TEAM"),
            ("MORTAR_TEAM", "INFANTRY_SQUAD"),
        ],
    )
    def test_roles_are_visually_distinct(self, procedural_manager, left, right):
        a = procedural_manager.create_unit_sprite("allies", left, 0)
        b = procedural_manager.create_unit_sprite("allies", right, 0)
        assert pygame.image.tostring(a, "RGBA") != pygame.image.tostring(b, "RGBA"), (
            f"{left} 与 {right} 外观相同"
        )

    def test_tank_differs_between_factions(self, procedural_manager):
        allies = procedural_manager.create_unit_sprite("allies", "TANK", 0)
        axis = procedural_manager.create_unit_sprite("axis", "TANK", 0)
        assert pygame.image.tostring(allies, "RGBA") != pygame.image.tostring(axis, "RGBA")


class TestProceduralBuildings:
    """每类建筑都有程序化外观。"""

    @pytest.mark.parametrize("building_type", list(CC2BuildingType))
    def test_every_building_type_is_non_empty(self, pygame_display, building_type):
        surface = render_cc2_building(building_type, tile_size=48)
        assert surface is not None
        assert _has_visible_pixels(surface), f"{building_type} 渲染结果为空"


class TestExternalAssetBoundary:
    """记录外部素材依赖边界，避免新增隐式图片加载。"""

    def test_image_load_is_limited_to_loader_modules(self):
        offenders: list[str] = []
        for path in SRC_ROOT.rglob("*.py"):
            if "pygame.image.load" not in path.read_text(encoding="utf-8"):
                continue
            if path.name not in IMAGE_LOAD_WHITELIST:
                offenders.append(str(path.relative_to(PROJECT_ROOT)))
        assert not offenders, f"发现未登记的图片加载模块: {offenders}"

    def test_hud_has_single_entry(self):
        import pycc2.presentation.rendering as rendering_pkg

        assert not hasattr(rendering_pkg, "HUDManager"), "渲染包不应再导出 HUDManager"
        assert importlib.util.find_spec("pycc2.presentation.rendering.hud") is None, (
            "rendering/hud.py 应已删除"
        )

        from pycc2.services.hud_manager import HUDManager

        assert HUDManager is not None
