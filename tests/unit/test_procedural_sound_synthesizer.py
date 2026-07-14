"""Tests for ProceduralSoundSynthesizer — CC2 combat sound waveform generation.

Tests verify that each generator returns a valid numpy int16 array with
expected length and value range. No audio hardware required — the
synthesizer is pure DSP (numpy → ndarray).
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import numpy as np
import pytest

from pycc2.presentation.audio.combat_sound_events import CombatSoundEvent
from pycc2.presentation.audio.procedural_sound_synthesizer import (
    ProceduralSoundSynthesizer,
)

SAMPLE_RATE = 44100


def _expected_samples(duration_ms: int) -> int:
    return int(SAMPLE_RATE * duration_ms / 1000)


def _assert_valid_waveform(result, expected_len: int) -> None:
    """Assert result is a valid int16 numpy array with expected length."""
    assert result is not None, "Generator returned None"
    assert isinstance(result, np.ndarray), f"Expected ndarray, got {type(result)}"
    assert result.dtype == np.int16, f"Expected int16, got {result.dtype}"
    assert len(result) == expected_len, f"Expected {expected_len} samples, got {len(result)}"
    assert result.min() >= -32768, f"Value below int16 min: {result.min()}"
    assert result.max() <= 32767, f"Value above int16 max: {result.max()}"
    assert np.any(result != 0), "Waveform is all zeros (silent)"


@pytest.fixture
def synth():
    return ProceduralSoundSynthesizer()


# ===========================================================================
# Volume property
# ===========================================================================


@pytest.mark.unit
class TestVolume:
    def test_default_volume(self, synth):
        assert synth.sfx_volume == 1.0

    def test_custom_volume(self):
        s = ProceduralSoundSynthesizer(sfx_volume=0.5)
        assert s.sfx_volume == 0.5

    def test_volume_clamped_high(self):
        s = ProceduralSoundSynthesizer(sfx_volume=2.0)
        assert s.sfx_volume == 1.0

    def test_volume_clamped_low(self):
        s = ProceduralSoundSynthesizer(sfx_volume=-0.5)
        assert s.sfx_volume == 0.0

    def test_volume_setter(self, synth):
        synth.sfx_volume = 0.3
        assert synth.sfx_volume == 0.3

    def test_volume_setter_clamps(self, synth):
        synth.sfx_volume = 5.0
        assert synth.sfx_volume == 1.0
        synth.sfx_volume = -1.0
        assert synth.sfx_volume == 0.0


# ===========================================================================
# generate_cc2_combat dispatch
# ===========================================================================


@pytest.mark.unit
class TestGenerateCC2Combat:
    @pytest.mark.parametrize(
        "event,duration_ms",
        [
            (CombatSoundEvent.TANK_CANNON_FIRE, 800),
            (CombatSoundEvent.AT_ROCKET_FIRE, 1200),
            (CombatSoundEvent.MORTAR_LAUNCH, 1500),
            (CombatSoundEvent.GRENADE_EXPLOSION_SHORT, 200),
            (CombatSoundEvent.AIRSTRIKE_BOMB, 1500),
            (CombatSoundEvent.VEHICLE_ENGINE_START, 2000),
            (CombatSoundEvent.VEHICLE_ENGINE_IDLE, 1500),
            (CombatSoundEvent.VEHICLE_MOVE, 1200),
            (CombatSoundEvent.ARMOR_PENETRATE, 350),
            (CombatSoundEvent.RICOCHET_BOUNCE, 450),
            (CombatSoundEvent.NEAR_MISS_WHIZZ, 180),
            (CombatSoundEvent.SMOKE_DEPLOY_HISS, 2000),
            (CombatSoundEvent.SUPPRESSION_FIRE, 1500),
        ],
    )
    def test_generates_valid_waveform(self, synth, event, duration_ms):
        result = synth.generate_cc2_combat(event)
        _assert_valid_waveform(result, _expected_samples(duration_ms))

    def test_unknown_event_returns_none(self, synth):
        result = synth.generate_cc2_combat(CombatSoundEvent.WEAPON_SWITCH)
        assert result is None


# ===========================================================================
# generate_suppression_fire (public entry)
# ===========================================================================


@pytest.mark.unit
class TestGenerateSuppressionFire:
    def test_default_duration(self, synth):
        result = synth.generate_suppression_fire()
        _assert_valid_waveform(result, _expected_samples(1500))

    def test_custom_duration(self, synth):
        result = synth.generate_suppression_fire(duration_ms=500)
        _assert_valid_waveform(result, _expected_samples(500))

    def test_short_duration(self, synth):
        result = synth.generate_suppression_fire(duration_ms=120)
        _assert_valid_waveform(result, _expected_samples(120))


# ===========================================================================
# Individual generator tests
# ===========================================================================


@pytest.mark.unit
class TestTankCannonFire:
    def test_returns_valid_waveform(self, synth):
        result = synth._gen_tank_cannon_fire()
        _assert_valid_waveform(result, _expected_samples(800))


@pytest.mark.unit
class TestATRocketFire:
    def test_returns_valid_waveform(self, synth):
        result = synth._gen_at_rocket_fire()
        _assert_valid_waveform(result, _expected_samples(1200))


@pytest.mark.unit
class TestMortarLaunch:
    def test_returns_valid_waveform(self, synth):
        result = synth._gen_mortar_launch()
        _assert_valid_waveform(result, _expected_samples(1500))


@pytest.mark.unit
class TestGrenadeExplosionShort:
    def test_returns_valid_waveform(self, synth):
        result = synth._gen_grenade_explosion_short()
        _assert_valid_waveform(result, _expected_samples(200))


@pytest.mark.unit
class TestAirstrikeBomb:
    def test_returns_valid_waveform(self, synth):
        result = synth._gen_airstrike_bomb()
        _assert_valid_waveform(result, _expected_samples(1500))


@pytest.mark.unit
class TestVehicleEngine:
    def test_start(self, synth):
        result = synth._gen_vehicle_engine("start")
        _assert_valid_waveform(result, _expected_samples(2000))

    def test_idle(self, synth):
        result = synth._gen_vehicle_engine("idle")
        _assert_valid_waveform(result, _expected_samples(1500))

    def test_move(self, synth):
        result = synth._gen_vehicle_engine("move")
        _assert_valid_waveform(result, _expected_samples(1200))

    def test_unknown_state_returns_none(self, synth):
        assert synth._gen_vehicle_engine("unknown") is None


@pytest.mark.unit
class TestArmorPenetrate:
    def test_returns_valid_waveform(self, synth):
        result = synth._gen_armor_penetrate()
        _assert_valid_waveform(result, _expected_samples(350))


@pytest.mark.unit
class TestRicochetBounce:
    def test_returns_valid_waveform(self, synth):
        result = synth._gen_ricochet_bounce()
        _assert_valid_waveform(result, _expected_samples(450))


@pytest.mark.unit
class TestNearMissWhizz:
    def test_returns_valid_waveform(self, synth):
        result = synth._gen_near_miss_whizz()
        _assert_valid_waveform(result, _expected_samples(180))


@pytest.mark.unit
class TestSmokeDeployHiss:
    def test_returns_valid_waveform(self, synth):
        result = synth._gen_smoke_deploy_hiss()
        _assert_valid_waveform(result, _expected_samples(2000))


@pytest.mark.unit
class TestSuppressionFire:
    def test_default_duration(self, synth):
        result = synth._gen_suppression_fire()
        _assert_valid_waveform(result, _expected_samples(1500))

    def test_custom_duration(self, synth):
        result = synth._gen_suppression_fire(duration_ms=600)
        _assert_valid_waveform(result, _expected_samples(600))


# ===========================================================================
# generate_via_sound_system (non-CC2 events)
# ===========================================================================


@pytest.mark.unit
class TestGenerateViaSoundSystem:
    @pytest.mark.parametrize(
        "event",
        [
            CombatSoundEvent.RIFLE_FIRE,
            CombatSoundEvent.MG_FIRE,
            CombatSoundEvent.PISTOL_FIRE,
            CombatSoundEvent.EXPLOSION,
            CombatSoundEvent.HIT_CONFIRM,
            CombatSoundEvent.HIT_CRITICAL,
            CombatSoundEvent.UNIT_DEATH,
            CombatSoundEvent.WEAPON_RELOAD,
        ],
    )
    def test_generates_waveform(self, synth, event):
        result = synth.generate_via_sound_system(event)
        assert result is not None, f"generate_via_sound_system({event}) returned None"
        assert isinstance(result, np.ndarray)

    def test_unknown_event_returns_none(self, synth):
        result = synth.generate_via_sound_system(CombatSoundEvent.WEAPON_SWITCH)
        assert result is None

    def test_cc2_event_not_handled(self, synth):
        """CC2-specific events should return None from generate_via_sound_system."""
        result = synth.generate_via_sound_system(CombatSoundEvent.TANK_CANNON_FIRE)
        assert result is None
