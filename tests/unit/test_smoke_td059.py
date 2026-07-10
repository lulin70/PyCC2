"""Smoke tests for TD-059 remaining zero-coverage modules.

Covers 6 modules identified in TD-059 as lacking test files:
  - direction.py (value object: 8-direction compass enum)
  - damage.py (value object: immutable damage with type/AP/source)
  - combat_result.py (domain: combat outcome dataclass)
  - stereo_sound.py (infrastructure: positional pan/volume)
  - environmental_audio.py (infrastructure: procedural ambient sounds)
  - cc2_map_parser.py (infrastructure: CC2 native map format parser)

Each test verifies: import succeeds -> class can be instantiated ->
basic API works correctly.  Uses real components (no Mock) per
project testing philosophy.
"""

import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import numpy as np
import pytest

# =====================================================================
# Direction — 8-direction compass enum
# =====================================================================


class TestDirectionEnum:
    """Direction enum: 8-direction compass for grid movement."""

    def test_all_8_directions_exist(self):
        from pycc2.domain.value_objects.direction import Direction

        assert Direction.N.value == 0
        assert Direction.NE.value == 1
        assert Direction.E.value == 2
        assert Direction.SE.value == 3
        assert Direction.S.value == 4
        assert Direction.SW.value == 5
        assert Direction.W.value == 6
        assert Direction.NW.value == 7

    def test_aliases_match_canonical(self):
        from pycc2.domain.value_objects.direction import Direction

        assert Direction.NORTH is Direction.N
        assert Direction.EAST is Direction.E
        assert Direction.SOUTH is Direction.S
        assert Direction.WEST is Direction.W

    def test_offset_property(self):
        from pycc2.domain.value_objects.direction import Direction

        assert Direction.N.offset == (0, -1)
        assert Direction.E.offset == (1, 0)
        assert Direction.S.offset == (0, 1)
        assert Direction.W.offset == (-1, 0)
        assert Direction.NE.offset == (1, -1)

    def test_opposite_property(self):
        from pycc2.domain.value_objects.direction import Direction

        assert Direction.N.opposite is Direction.S
        assert Direction.E.opposite is Direction.W
        assert Direction.NE.opposite is Direction.SW
        assert Direction.SE.opposite is Direction.NW

    def test_is_cardinal_and_is_diagonal(self):
        from pycc2.domain.value_objects.direction import Direction

        assert Direction.N.is_cardinal is True
        assert Direction.E.is_cardinal is True
        assert Direction.N.is_diagonal is False
        assert Direction.NE.is_diagonal is True
        assert Direction.SW.is_cardinal is False

    def test_from_offset_roundtrip(self):
        from pycc2.domain.value_objects.direction import Direction

        for d in Direction.get_all():
            dx, dy = d.offset
            assert Direction.from_offset(dx, dy) is d

    def test_from_offset_zero_returns_none(self):
        from pycc2.domain.value_objects.direction import Direction

        assert Direction.from_offset(0, 0) is None

    def test_from_angle(self):
        from pycc2.domain.value_objects.direction import Direction

        assert Direction.from_angle(0.0) is Direction.E
        assert Direction.from_angle(90.0) is Direction.S
        assert Direction.from_angle(180.0) is Direction.W
        assert Direction.from_angle(270.0) is Direction.N

    def test_rotate_cw(self):
        from pycc2.domain.value_objects.direction import Direction

        assert Direction.N.rotate_cw(1) is Direction.NE
        assert Direction.N.rotate_cw(2) is Direction.E
        assert Direction.N.rotate_cw(8) is Direction.N

    def test_rotate_ccw(self):
        from pycc2.domain.value_objects.direction import Direction

        assert Direction.N.rotate_ccw(1) is Direction.NW
        assert Direction.E.rotate_ccw(2) is Direction.N  # E→NE→N

    def test_get_cardinals_and_diagonals(self):
        from pycc2.domain.value_objects.direction import Direction

        cardinals = Direction.get_cardinals()
        assert len(cardinals) == 4
        assert Direction.N in cardinals
        diagonals = Direction.get_diagonals()
        assert len(diagonals) == 4
        assert Direction.NE in diagonals

    def test_module_level_constants_exist(self):
        from pycc2.domain.value_objects.direction import (
            DIRECTION_ANGLES,
            DIRECTION_VECTORS,
            DIRECTION_VECTORS_REVERSE,
            Direction,
        )

        assert len(DIRECTION_ANGLES) == 8
        assert len(DIRECTION_VECTORS) == 8
        assert len(DIRECTION_VECTORS_REVERSE) == 8
        assert Direction.N in DIRECTION_ANGLES
        assert DIRECTION_VECTORS[Direction.E] == (1, 0)


# =====================================================================
# Damage — immutable damage value object
# =====================================================================


class TestDamageValueObject:
    """Damage: immutable value object with type, armor penetration, source."""

    def test_create_with_defaults(self):
        from pycc2.domain.value_objects.damage import Damage, DamageType

        d = Damage(amount=50.0)
        assert d.amount == 50.0
        assert d.damage_type is DamageType.KINETIC
        assert d.armor_penetration == 0.0
        assert d.source_unit_id is None
        assert d.source_weapon_name is None

    def test_negative_amount_raises(self):
        from pycc2.domain.value_objects.damage import Damage

        with pytest.raises(ValueError, match="cannot be negative"):
            Damage(amount=-1.0)

    def test_armor_penetration_out_of_range_raises(self):
        from pycc2.domain.value_objects.damage import Damage

        with pytest.raises(ValueError, match="Armor penetration"):
            Damage(amount=10.0, armor_penetration=1.5)
        with pytest.raises(ValueError, match="Armor penetration"):
            Damage(amount=10.0, armor_penetration=-0.1)

    def test_is_lethal_and_is_critical(self):
        from pycc2.domain.value_objects.damage import Damage

        assert Damage(amount=50.0).is_lethal is True
        assert Damage(amount=49.0).is_lethal is False
        assert Damage(amount=75.0).is_critical is True
        assert Damage(amount=74.0).is_critical is False

    def test_apply_armor_reduction(self):
        from pycc2.domain.value_objects.damage import Damage

        d = Damage(amount=100.0, armor_penetration=0.5)
        reduced = d.apply_armor_reduction(armor_value=0.8)
        # effective_armor = 0.8 * (1 - 0.5) = 0.4
        # reduction_factor = 1 - 0.4 = 0.6
        assert reduced.amount == pytest.approx(60.0)

    def test_apply_cover_bonus(self):
        from pycc2.domain.value_objects.damage import Damage

        d = Damage(amount=100.0)
        reduced = d.apply_cover_bonus(cover_bonus=0.3)
        assert reduced.amount == pytest.approx(70.0)

    def test_apply_cover_bonus_invalid_raises(self):
        from pycc2.domain.value_objects.damage import Damage

        d = Damage(amount=100.0)
        with pytest.raises(ValueError, match="Cover bonus"):
            d.apply_cover_bonus(1.5)

    def test_multiply(self):
        from pycc2.domain.value_objects.damage import Damage

        d = Damage(amount=50.0)
        doubled = d.multiply(2.0)
        assert doubled.amount == 100.0
        # Original unchanged (immutable)
        assert d.amount == 50.0

    def test_multiply_negative_raises(self):
        from pycc2.domain.value_objects.damage import Damage

        d = Damage(amount=50.0)
        with pytest.raises(ValueError, match="negative"):
            d.multiply(-1.0)

    def test_add(self):
        from pycc2.domain.value_objects.damage import Damage

        d1 = Damage(amount=30.0, armor_penetration=0.3, source_unit_id="u1")
        d2 = Damage(amount=20.0, armor_penetration=0.5)
        combined = d1.add(d2)
        assert combined.amount == 50.0
        assert combined.armor_penetration == 0.5  # max
        assert combined.source_unit_id == "u1"

    def test_factory_methods(self):
        from pycc2.domain.value_objects.damage import Damage, DamageType

        k = Damage.create_kinetic(40.0)
        assert k.damage_type is DamageType.KINETIC
        e = Damage.create_explosive(60.0)
        assert e.damage_type is DamageType.EXPLOSIVE
        z = Damage.zero()
        assert z.amount == 0.0

    def test_is_frozen(self):
        from pycc2.domain.value_objects.damage import Damage

        d = Damage(amount=50.0)
        with pytest.raises(AttributeError):
            d.amount = 100.0


# =====================================================================
# CombatResult — combat outcome dataclass
# =====================================================================


class TestCombatResult:
    """CombatResult and ShotResult: combat outcome tracking."""

    def test_combat_result_defaults(self):
        from pycc2.domain.combat.combat_result import CombatResult

        cr = CombatResult()
        assert cr.shots_fired == 0
        assert cr.shots_hit == 0
        assert cr.total_damage == 0.0
        assert cr.target_eliminated is False
        assert cr.shot_results == []

    def test_shot_result_defaults(self):
        from pycc2.domain.combat.combat_result import ShotResult

        sr = ShotResult()
        assert sr.hit is False
        assert sr.damage_dealt == 0.0
        assert sr.distance == 0.0

    def test_combat_result_with_shot_results(self):
        from pycc2.domain.combat.combat_result import CombatResult, ShotResult

        shots = [
            ShotResult(hit=True, damage_dealt=25.0, distance=10.0),
            ShotResult(hit=False, damage_dealt=0.0, distance=12.0),
        ]
        cr = CombatResult(
            shots_fired=2,
            shots_hit=1,
            total_damage=25.0,
            target_eliminated=False,
            shot_results=shots,
        )
        assert len(cr.shot_results) == 2
        assert cr.shot_results[0].hit is True
        assert cr.shot_results[1].damage_dealt == 0.0


# =====================================================================
# StereoSoundSystem — positional pan/volume
# =====================================================================


class TestStereoSoundSystem:
    """StereoSoundSystem: 3D positional stereo pan and volume."""

    def test_create_with_defaults(self):
        from pycc2.infrastructure.audio.stereo_sound import StereoSoundSystem

        s = StereoSoundSystem()
        assert s.MAX_DISTANCE == 50.0
        assert s.REFERENCE_DISTANCE == 10.0

    def test_calculate_stereo_pan_center(self):
        from pycc2.infrastructure.audio.stereo_sound import StereoSoundSystem

        s = StereoSoundSystem()
        pan = s.calculate_stereo_pan((0, 0), (0, 5))
        assert pan == 0.0  # Directly south, no horizontal pan

    def test_calculate_stereo_pan_right(self):
        from pycc2.infrastructure.audio.stereo_sound import StereoSoundSystem

        s = StereoSoundSystem()
        pan = s.calculate_stereo_pan((0, 0), (5, 0))
        assert pan > 0.0  # Source to the right

    def test_calculate_stereo_pan_left(self):
        from pycc2.infrastructure.audio.stereo_sound import StereoSoundSystem

        s = StereoSoundSystem()
        pan = s.calculate_stereo_pan((0, 0), (-5, 0))
        assert pan < 0.0  # Source to the left

    def test_calculate_stereo_pan_same_position(self):
        from pycc2.infrastructure.audio.stereo_sound import StereoSoundSystem

        s = StereoSoundSystem()
        pan = s.calculate_stereo_pan((3, 3), (3, 3))
        assert pan == 0.0

    def test_calculate_volume_zero_distance(self):
        from pycc2.infrastructure.audio.stereo_sound import StereoSoundSystem

        s = StereoSoundSystem()
        vol = s.calculate_volume((0, 0), (0, 0), base_volume=1.0)
        assert vol == 1.0  # No attenuation at source

    def test_calculate_volume_beyond_max(self):
        from pycc2.infrastructure.audio.stereo_sound import StereoSoundSystem

        s = StereoSoundSystem()
        vol = s.calculate_volume((0, 0), (100, 0), base_volume=1.0)
        assert vol == 0.0  # Beyond MAX_DISTANCE

    def test_calculate_volume_mid_distance(self):
        from pycc2.infrastructure.audio.stereo_sound import StereoSoundSystem

        s = StereoSoundSystem()
        vol = s.calculate_volume((0, 0), (25, 0), base_volume=1.0)
        # distance=25, MAX=50, attenuation = 1 - 25/50 = 0.5
        assert vol == pytest.approx(0.5)


# =====================================================================
# EnvironmentalAudio — procedural ambient sound generation
# =====================================================================


class TestEnvironmentalSoundType:
    """EnvironmentSoundType: 11 ambient sound categories."""

    def test_all_11_types_exist(self):
        from pycc2.infrastructure.audio.environmental_audio import (
            EnvironmentSoundType,
        )

        assert len(list(EnvironmentSoundType)) == 11
        assert EnvironmentSoundType.BIRDS
        assert EnvironmentSoundType.WIND
        assert EnvironmentSoundType.DISTANT_ARTILLERY
        assert EnvironmentSoundType.RAIN
        assert EnvironmentSoundType.THUNDER


class TestEnvironmentalSoundGenerator:
    """EnvironmentalSoundGenerator: procedural numpy waveform synthesis."""

    def test_generate_bird_chirp_returns_ndarray(self):
        from pycc2.infrastructure.audio.environmental_audio import (
            EnvironmentalSoundGenerator,
        )

        wave = EnvironmentalSoundGenerator.generate_bird_chirp(variant=0)
        assert isinstance(wave, np.ndarray)
        assert wave.ndim == 1
        assert len(wave) > 0

    def test_generate_wind_gust_returns_ndarray(self):
        from pycc2.infrastructure.audio.environmental_audio import (
            EnvironmentalSoundGenerator,
        )

        wave = EnvironmentalSoundGenerator.generate_wind_gust(intensity=0.5)
        assert isinstance(wave, np.ndarray)
        assert len(wave) > 0

    def test_generate_distant_artillery_returns_ndarray(self):
        from pycc2.infrastructure.audio.environmental_audio import (
            EnvironmentalSoundGenerator,
        )

        wave = EnvironmentalSoundGenerator.generate_distant_artillery(distance_factor=1.0)
        assert isinstance(wave, np.ndarray)
        assert len(wave) > 0

    def test_generate_rain_returns_ndarray(self):
        from pycc2.infrastructure.audio.environmental_audio import (
            EnvironmentalSoundGenerator,
        )

        wave = EnvironmentalSoundGenerator.generate_rain(intensity=0.7)
        assert isinstance(wave, np.ndarray)
        assert len(wave) > 0

    def test_generate_thunder_returns_ndarray(self):
        from pycc2.infrastructure.audio.environmental_audio import (
            EnvironmentalSoundGenerator,
        )

        wave = EnvironmentalSoundGenerator.generate_thunder()
        assert isinstance(wave, np.ndarray)
        assert len(wave) > 0

    def test_generate_fire_crackle_returns_ndarray(self):
        from pycc2.infrastructure.audio.environmental_audio import (
            EnvironmentalSoundGenerator,
        )

        wave = EnvironmentalSoundGenerator.generate_fire_crackle()
        assert isinstance(wave, np.ndarray)
        assert len(wave) > 0

    def test_to_int16_produces_valid_range(self):
        from pycc2.infrastructure.audio.environmental_audio import (
            EnvironmentalSoundGenerator,
        )

        wave = EnvironmentalSoundGenerator.generate_wind_gust(0.5)
        int16_wave = EnvironmentalSoundGenerator._to_int16(wave)
        assert int16_wave.dtype == np.int16
        assert int16_wave.min() >= -32768
        assert int16_wave.max() <= 32767


class TestEnvironmentalAudioSystem:
    """EnvironmentalAudioSystem: runtime ambient sound manager."""

    def test_create_instance(self):
        from pycc2.infrastructure.audio.environmental_audio import (
            EnvironmentalAudioSystem,
        )

        sys = EnvironmentalAudioSystem()
        assert sys is not None

    def test_set_time_of_day(self):
        from pycc2.infrastructure.audio.environmental_audio import (
            EnvironmentalAudioSystem,
        )

        sys = EnvironmentalAudioSystem()
        sys.set_time_of_day(12)
        assert sys is not None  # No crash

    def test_set_combat_intensity(self):
        from pycc2.infrastructure.audio.environmental_audio import (
            EnvironmentalAudioSystem,
        )

        sys = EnvironmentalAudioSystem()
        sys.set_combat_intensity(0.8)
        assert sys is not None

    def test_stop_all_no_crash(self):
        from pycc2.infrastructure.audio.environmental_audio import (
            EnvironmentalAudioSystem,
        )

        sys = EnvironmentalAudioSystem()
        sys.stop_all()
        assert sys is not None


# =====================================================================
# CC2MapParser — CC2 native map format parser
# =====================================================================


class TestCC2TerrainCode:
    """CC2TerrainCode: 32 CC2 native terrain codes (0x00-0x1F)."""

    def test_base_codes_exist(self):
        from pycc2.infrastructure.parsers.cc2_map_parser import CC2TerrainCode

        assert CC2TerrainCode.OPEN == 0x00
        assert CC2TerrainCode.ROAD == 0x01
        assert CC2TerrainCode.BUILDING_ENTERABLE == 0x07
        assert CC2TerrainCode.BRIDGE == 0x0B
        assert CC2TerrainCode.SWAMP == 0x0F

    def test_variation_codes_exist(self):
        from pycc2.infrastructure.parsers.cc2_map_parser import CC2TerrainCode

        assert CC2TerrainCode.VAR_10 == 0x10
        assert CC2TerrainCode.VAR_1F == 0x1F

    def test_total_count(self):
        from pycc2.infrastructure.parsers.cc2_map_parser import CC2TerrainCode

        assert len(CC2TerrainCode) == 32


class TestCC2ToPyCC2Map:
    """CC2_TO_PYCC2_MAP: terrain code conversion table."""

    def test_all_base_codes_mapped(self):
        from pycc2.domain.value_objects.terrain_type import TerrainType
        from pycc2.infrastructure.parsers.cc2_map_parser import (
            CC2_TO_PYCC2_MAP,
            CC2TerrainCode,
        )

        assert CC2_TO_PYCC2_MAP[CC2TerrainCode.OPEN] is TerrainType.OPEN
        assert CC2_TO_PYCC2_MAP[CC2TerrainCode.ROAD] is TerrainType.ROAD
        assert CC2_TO_PYCC2_MAP[CC2TerrainCode.BRIDGE] is TerrainType.BRIDGE
        assert CC2_TO_PYCC2_MAP[CC2TerrainCode.WALL] is TerrainType.WALL

    def test_variation_codes_mapped(self):
        from pycc2.infrastructure.parsers.cc2_map_parser import CC2_TO_PYCC2_MAP

        assert 0x10 in CC2_TO_PYCC2_MAP
        assert 0x1F in CC2_TO_PYCC2_MAP

    def test_total_mapping_count(self):
        from pycc2.infrastructure.parsers.cc2_map_parser import CC2_TO_PYCC2_MAP

        # 16 base + 16 variation = 32 entries
        assert len(CC2_TO_PYCC2_MAP) == 32


class TestCC2MapHeaderAndData:
    """CC2MapHeader and CC2MapData: parsed map structures."""

    def test_header_creation(self):
        from pycc2.infrastructure.parsers.cc2_map_parser import CC2MapHeader

        h = CC2MapHeader(
            format_version="cc2_map_v1",
            width=40,
            height=40,
            data_offset=4,
            byte_order="little",
            has_header=True,
        )
        assert h.width == 40
        assert h.format_version == "cc2_map_v1"

    def test_map_data_creation_and_to_json(self):
        from pycc2.infrastructure.parsers.cc2_map_parser import CC2MapData

        data = CC2MapData(
            name="test_map",
            width=2,
            height=2,
            terrain_grid=[[0, 1], [3, 6]],  # int TerrainType values
        )
        json_out = data.to_pycc2_json()
        assert json_out["name"] == "test_map"
        assert json_out["width"] == 2
        assert json_out["height"] == 2
        assert json_out["tiles"] == [[0, 1], [3, 6]]


class TestCC2MapParser:
    """CC2MapParser: main parser class."""

    def test_create_parser(self):
        from pycc2.infrastructure.parsers.cc2_map_parser import CC2MapParser

        parser = CC2MapParser()
        assert parser is not None

    def test_create_parser_with_byte_order(self):
        from pycc2.infrastructure.parsers.cc2_map_parser import CC2MapParser

        parser = CC2MapParser(default_byte_order="big")
        assert parser is not None

    def test_parse_nonexistent_file_raises(self):
        from pycc2.infrastructure.parsers.cc2_map_parser import CC2MapParser

        parser = CC2MapParser()
        with pytest.raises((FileNotFoundError, OSError, IOError)):
            parser.parse("/nonexistent/path/Map001.txt")
