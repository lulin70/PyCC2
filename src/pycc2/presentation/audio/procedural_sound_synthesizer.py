"""Procedural Sound Synthesizer - CC2-specific combat sound waveform generation.

Extracted from enhanced_sound_bridge.py (TD-072) to separate two unrelated
responsibilities:
- Audio bridging (file loading → caching → playback dispatch) → EnhancedSoundSystem
- Procedural waveform synthesis (numpy DSP → ndarray) → this module

This module is stateless beyond ``sfx_volume`` and returns raw numpy arrays.
The caller (EnhancedSoundSystem) is responsible for wrapping the ndarray into
``mixer.Sound`` and caching it.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np

from pycc2.presentation.audio.combat_sound_events import CombatSoundEvent

logger = logging.getLogger(__name__)


class ProceduralSoundSynthesizer:
    """CC2-specific procedural combat sound synthesizer.

    Generates raw numpy waveforms for combat events. Stateless beyond
    ``sfx_volume``. Does NOT interact with pygame mixer or file cache.
    """

    def __init__(self, sfx_volume: float = 1.0) -> None:
        """Initialize synthesizer with sfx volume.

        Args:
            sfx_volume: Initial sfx volume (0.0-1.0)

        """
        self._sfx_volume: float = max(0.0, min(1.0, sfx_volume))

    @property
    def sfx_volume(self) -> float:
        """Get the sfx volume."""
        return self._sfx_volume

    @sfx_volume.setter
    def sfx_volume(self, value: float) -> None:
        """Set the sfx volume (clamped to 0.0-1.0)."""
        self._sfx_volume = max(0.0, min(1.0, value))

    def generate_cc2_combat(self, event: CombatSoundEvent) -> np.ndarray | None:
        """Dispatch to CC2-specific waveform generators.

        Args:
            event: Combat sound event to synthesize

        Returns:
            numpy ndarray (int16) or None if no generator for this event

        """
        generators = {
            CombatSoundEvent.TANK_CANNON_FIRE: self._gen_tank_cannon_fire,
            CombatSoundEvent.AT_ROCKET_FIRE: self._gen_at_rocket_fire,
            CombatSoundEvent.MORTAR_LAUNCH: self._gen_mortar_launch,
            CombatSoundEvent.GRENADE_EXPLOSION_SHORT: self._gen_grenade_explosion_short,
            CombatSoundEvent.AIRSTRIKE_BOMB: self._gen_airstrike_bomb,
            CombatSoundEvent.VEHICLE_ENGINE_START: lambda: self._gen_vehicle_engine("start"),
            CombatSoundEvent.VEHICLE_ENGINE_IDLE: lambda: self._gen_vehicle_engine("idle"),
            CombatSoundEvent.VEHICLE_MOVE: lambda: self._gen_vehicle_engine("move"),
            CombatSoundEvent.ARMOR_PENETRATE: self._gen_armor_penetrate,
            CombatSoundEvent.RICOCHET_BOUNCE: self._gen_ricochet_bounce,
            CombatSoundEvent.NEAR_MISS_WHIZZ: self._gen_near_miss_whizz,
            CombatSoundEvent.SMOKE_DEPLOY_HISS: self._gen_smoke_deploy_hiss,
            CombatSoundEvent.SUPPRESSION_FIRE: lambda: self._gen_suppression_fire(),
        }

        generator = generators.get(event)
        if generator:
            return generator()
        return None

    def generate_via_sound_system(self, event: CombatSoundEvent) -> np.ndarray | None:
        """Dispatch to sound_system.ProceduralSoundGenerator for non-CC2 events.

        Args:
            event: Combat sound event to synthesize

        Returns:
            numpy ndarray or None if no generator for this event

        """
        from pycc2.presentation.audio.sound_system import (
            ProceduralSoundGenerator,
        )

        generators = {
            CombatSoundEvent.RIFLE_FIRE: lambda: ProceduralSoundGenerator.generate_rifle_shot(),
            CombatSoundEvent.MG_FIRE: lambda: ProceduralSoundGenerator.generate_mg_burst(),
            CombatSoundEvent.PISTOL_FIRE: lambda: ProceduralSoundGenerator.generate_rifle_shot(
                duration_ms=80
            ),
            CombatSoundEvent.EXPLOSION: lambda: ProceduralSoundGenerator.generate_explosion(),
            CombatSoundEvent.HIT_CONFIRM: lambda: (
                ProceduralSoundGenerator.generate_hit_confirm()
            ),
            CombatSoundEvent.HIT_CRITICAL: lambda: (
                ProceduralSoundGenerator.generate_hit_confirm(duration_ms=120)
            ),
            CombatSoundEvent.UNIT_DEATH: lambda: ProceduralSoundGenerator.generate_death_cry(),
            CombatSoundEvent.WEAPON_RELOAD: lambda: ProceduralSoundGenerator.generate_click(
                duration_ms=50, frequency=400
            ),
        }

        generator = generators.get(event)
        if generator:
            return generator()
        return None

    def generate_suppression_fire(self, duration_ms: int = 1500) -> np.ndarray | None:
        """Public entry for suppression fire with custom duration.

        Args:
            duration_ms: Duration of suppression fire in milliseconds

        Returns:
            numpy ndarray (int16) or None

        """
        return self._gen_suppression_fire(duration_ms)

    def _gen_tank_cannon_fire(self) -> np.ndarray | None:
        """Generate tank main gun fire - deep boom with reverb tail."""
        import numpy as np

        duration_ms = 800
        samples = int(44100 * duration_ms / 1000)
        t = np.linspace(0, duration_ms / 1000, samples)

        attack = int(samples * 0.02)
        decay = int(samples * 0.15)
        envelope = np.ones(samples)
        envelope[:attack] = np.linspace(0, 1, attack)
        envelope[attack : attack + decay] = np.exp(-3 * np.arange(decay) / decay)
        envelope[attack + decay :] *= np.exp(
            -1.5 * np.arange(samples - attack - decay) / (samples - attack - decay)
        )

        base_freq = 60
        fundamental = np.sin(2 * np.pi * base_freq * t) * 0.6
        harmonic2 = np.sin(2 * np.pi * base_freq * 2.3 * t) * 0.25
        harmonic3 = np.sin(2 * np.pi * base_freq * 4.7 * t) * 0.15

        noise = np.random.uniform(-1, 1, samples) * 0.3
        noise_envelope = np.exp(-8 * t / (duration_ms / 1000))
        noise *= noise_envelope

        signal = (fundamental + harmonic2 + harmonic3 + noise) * envelope
        signal = np.clip(signal, -1, 1)

        return (signal * 32767).astype(np.int16)

    def _gen_at_rocket_fire(self) -> np.ndarray | None:
        """Generate anti-tank rocket launch - whoosh + explosion."""
        import numpy as np

        duration_ms = 1200
        samples = int(44100 * duration_ms / 1000)
        np.linspace(0, duration_ms / 1000, samples)

        launch_duration = int(samples * 0.4)
        explosion_start = int(samples * 0.35)

        envelope = np.zeros(samples)
        envelope[:launch_duration] = np.exp(-2 * np.arange(launch_duration) / launch_duration) * 0.7
        if explosion_start < samples:
            exp_length = samples - explosion_start
            envelope[explosion_start:] = np.exp(-3 * np.arange(exp_length) / exp_length) * 1.0

        freq_sweep = np.linspace(200, 80, launch_duration)
        whoosh = np.sin(2 * np.pi * np.cumsum(freq_sweep) / 44100)[:launch_duration] * 0.5
        whoosh += np.random.uniform(-0.3, 0.3, launch_duration)

        explosion = np.zeros(samples)
        if explosion_start < samples:
            exp_samples = samples - explosion_start
            exp_t = np.linspace(0, exp_samples / 44100, exp_samples)
            explosion[explosion_start:] = np.random.uniform(-1, 1, exp_samples) * 0.8 * np.exp(
                -4 * exp_t / (exp_samples / 44100)
            ) + np.sin(2 * np.pi * 45 * exp_t) * 0.4 * np.exp(-5 * exp_t / (exp_samples / 44100))

        signal = np.zeros(samples)
        signal[:launch_duration] = whoosh
        signal += explosion
        signal *= envelope
        signal = np.clip(signal, -1, 1)

        return (signal * 32767).astype(np.int16)

    def _gen_mortar_launch(self) -> np.ndarray | None:
        """Generate mortar launch with distinctive whistle."""
        import numpy as np

        duration_ms = 1500
        samples = int(44100 * duration_ms / 1000)
        np.linspace(0, duration_ms / 1000, samples)

        thump_samples = int(0.05 * 44100)
        whistle_start = int(0.08 * 44100)

        thump = np.zeros(samples)
        thump[:thump_samples] = (
            np.sin(2 * np.pi * 80 * np.linspace(0, 0.05, thump_samples)) * 0.7
            + np.random.uniform(-0.4, 0.4, thump_samples)
        ) * np.exp(-8 * np.arange(thump_samples) / thump_samples)

        whistle = np.zeros(samples)
        if whistle_start < samples:
            whistle_samples = samples - whistle_start
            whistle_t = np.linspace(0, whistle_samples / 44100, whistle_samples)
            freq = np.linspace(400, 150, whistle_samples)
            phase = np.cumsum(2 * np.pi * freq / 44100)
            whistle[whistle_start:] = (np.sin(phase) * 0.4 + np.sin(phase * 1.5) * 0.2) * np.exp(
                -1.2 * whistle_t / (duration_ms / 1000)
            )

        impact = np.zeros(samples)
        impact_start = int(0.85 * samples)
        if impact_start < samples:
            impact_samples = samples - impact_start
            impact_t = np.linspace(0, impact_samples / 44100, impact_samples)
            impact[impact_start:] = (
                np.random.uniform(-1, 1, impact_samples)
                * 0.6
                * np.exp(-6 * impact_t / (impact_samples / 44100))
            )

        signal = thump + whistle + impact
        signal = np.clip(signal, -1, 1)

        return (signal * 32767).astype(np.int16)

    def _gen_grenade_explosion_short(self) -> np.ndarray | None:
        """Generate short grenade explosion - higher frequency, shorter duration."""
        import numpy as np

        duration_ms = 200
        samples = int(44100 * duration_ms / 1000)
        t = np.linspace(0, duration_ms / 1000, samples)

        attack = int(samples * 0.01)
        envelope = np.ones(samples)
        envelope[:attack] = np.linspace(0, 1, attack)
        envelope[attack:] *= np.exp(-12 * np.arange(samples - attack) / (samples - attack))

        base_freq = 150
        signal = (
            np.sin(2 * np.pi * base_freq * t) * 0.5
            + np.sin(2 * np.pi * base_freq * 2.1 * t) * 0.3
            + np.sin(2 * np.pi * base_freq * 3.5 * t) * 0.2
            + np.random.uniform(-1, 1, samples) * 0.6
        ) * envelope

        signal = np.clip(signal, -1, 1)
        return (signal * 32767).astype(np.int16)

    def _gen_airstrike_bomb(self) -> np.ndarray | None:
        """Generate airstrike bomb - multiple explosions in sequence."""
        import numpy as np

        total_duration_ms = 1500
        total_samples = int(44100 * total_duration_ms / 1000)
        signal = np.zeros(total_samples)

        explosion_intervals = [0, 150, 300]
        explosion_duration_ms = 400

        for offset_ms in explosion_intervals:
            start_sample = int(offset_ms / 1000 * 44100)
            exp_samples = int(44100 * explosion_duration_ms / 1000)
            end_sample = min(start_sample + exp_samples, total_samples)

            if start_sample >= total_samples:
                break

            actual_samples = end_sample - start_sample
            t = np.linspace(0, actual_samples / 44100, actual_samples)

            attack = min(int(actual_samples * 0.02), actual_samples)
            envelope = np.ones(actual_samples)
            envelope[:attack] = np.linspace(0, 1, attack)
            envelope[attack:] *= np.exp(
                -5 * np.arange(actual_samples - attack) / (actual_samples - attack)
            )

            explosion = (
                np.random.uniform(-1, 1, actual_samples) * 0.9 * envelope
                + np.sin(2 * np.pi * 55 * t) * 0.4 * envelope
            )

            volume_factor = 1.0 - (offset_ms / 600) * 0.3
            signal[start_sample:end_sample] += explosion * volume_factor

        signal = np.clip(signal, -1, 1)
        return (signal * 32767).astype(np.int16)

    def _gen_vehicle_engine(self, state: str) -> np.ndarray | None:
        """Generate vehicle engine sounds based on state."""
        import numpy as np

        if state == "start":
            duration_ms = 2000
            samples = int(44100 * duration_ms / 1000)
            t = np.linspace(0, duration_ms / 1000, samples)

            crank_duration = int(0.4 * 44100)
            envelope = np.zeros(samples)
            envelope[:crank_duration] = 0.3
            envelope[crank_duration:] = np.linspace(0.3, 0.8, samples - crank_duration)

            crank = np.zeros(samples)
            crank[:crank_duration] = (
                np.sin(2 * np.pi * 8 * np.linspace(0, 0.4, crank_duration)) * 0.5
                + np.random.uniform(-0.3, 0.3, crank_duration)
            ) * np.repeat(np.linspace(1, 0.6, crank_duration), 1)

            engine_rpm = np.linspace(400, 700, samples)
            engine = np.sin(2 * np.pi * np.cumsum(engine_rpm) / 44100) * 0.6
            engine += np.sin(2 * np.pi * np.cumsum(engine_rpm * 2) / 44100) * 0.3
            pulse = 0.1 * np.sin(2 * np.pi * 15 * t)

            signal = (crank + engine + pulse) * envelope
            signal = np.clip(signal, -1, 1)
            return (signal * 32767).astype(np.int16)

        elif state == "idle":
            duration_ms = 1500
            samples = int(44100 * duration_ms / 1000)
            t = np.linspace(0, duration_ms / 1000, samples)

            base_rpm = 500
            engine = (
                np.sin(2 * np.pi * base_rpm * t) * 0.4
                + np.sin(2 * np.pi * base_rpm * 2 * t) * 0.2
                + np.sin(2 * np.pi * base_rpm * 0.5 * t) * 0.3
            )
            pulse = 0.15 * np.sin(2 * np.pi * 12 * t)
            rumble = np.random.uniform(-0.1, 0.1, samples) * 0.5

            signal = engine + pulse + rumble
            fade = np.linspace(0.8, 0.8, samples)
            signal *= fade
            signal = np.clip(signal, -1, 1)
            return (signal * 32767).astype(np.int16)

        elif state == "move":
            duration_ms = 1200
            samples = int(44100 * duration_ms / 1000)
            t = np.linspace(0, duration_ms / 1000, samples)

            base_rpm_array = np.linspace(550, 650, samples)
            engine = np.sin(2 * np.pi * np.cumsum(base_rpm_array) / 44100) * 0.5
            engine += np.sin(2 * np.pi * np.cumsum(base_rpm_array * 2.5) / 44100) * 0.25

            track_clatter = np.zeros(samples)
            clatter_interval = int(44100 / 30)
            for i in range(0, samples - 50, clatter_interval):
                end = min(i + 50, samples)
                track_clatter[i:end] = np.random.uniform(-0.2, 0.2, end - i) * np.exp(
                    -0.5 * np.arange(end - i) / 50
                )

            signal = engine + track_clatter
            signal = np.clip(signal, -1, 1)
            return (signal * 32767).astype(np.int16)

        return None

    def _gen_armor_penetrate(self) -> np.ndarray | None:
        """Generate armor penetration hit - high-pitched metal piercing."""
        import numpy as np

        duration_ms = 350
        samples = int(44100 * duration_ms / 1000)
        t = np.linspace(0, duration_ms / 1000, samples)

        attack = int(samples * 0.005)
        envelope = np.ones(samples)
        envelope[:attack] = np.linspace(0, 1, attack)
        envelope[attack:] *= np.exp(-8 * np.arange(samples - attack) / (samples - attack))

        metal_strike = (
            np.sin(2 * np.pi * 2500 * t) * 0.5
            + np.sin(2 * np.pi * 3200 * t) * 0.3
            + np.sin(2 * np.pi * 4100 * t) * 0.2
        )
        screech = np.sin(2 * np.pi * 6000 * t) * 0.3 * np.exp(-15 * t / (duration_ms / 1000))

        ring_decay = np.zeros(samples)
        ring_start = int(samples * 0.03)
        if ring_start < samples:
            ring_samples = samples - ring_start
            ring_t = np.linspace(0, ring_samples / 44100, ring_samples)
            ring_freq = 1800
            ring_decay[ring_start:] = (
                np.sin(2 * np.pi * ring_freq * ring_t)
                * 0.25
                * np.exp(-3 * ring_t / (ring_samples / 44100))
            )

        signal = (metal_strike + screech + ring_decay) * envelope
        signal = np.clip(signal, -1, 1)
        return (signal * 32767).astype(np.int16)

    def _gen_ricochet_bounce(self) -> np.ndarray | None:
        """Generate ricochet bounce - mid-frequency bounce with echo decay."""
        import numpy as np

        duration_ms = 450
        samples = int(44100 * duration_ms / 1000)
        t = np.linspace(0, duration_ms / 1000, samples)

        initial_hit = int(samples * 0.08)
        bounce1_start = int(samples * 0.18)
        bounce2_start = int(samples * 0.38)

        signal = np.zeros(samples)

        hit_t = np.linspace(0, initial_hit / 44100, initial_hit)
        signal[:initial_hit] = (
            np.sin(2 * np.pi * 1200 * hit_t) * 0.6 + np.random.uniform(-0.3, 0.3, initial_hit)
        ) * np.exp(-10 * np.arange(initial_hit) / initial_hit)

        for bounce_start in [bounce1_start, bounce2_start]:
            if bounce_start < samples:
                bounce_len = min(int(samples * 0.1), samples - bounce_start)
                bounce_t = np.linspace(0, bounce_len / 44100, bounce_len)
                freq = 900 if bounce_start == bounce1_start else 650
                amplitude = 0.35 if bounce_start == bounce1_start else 0.2
                signal[bounce_start : bounce_start + bounce_len] += (
                    np.sin(2 * np.pi * freq * bounce_t) * amplitude
                    + np.random.uniform(-0.15, 0.15, bounce_len) * amplitude
                ) * np.exp(-8 * np.arange(bounce_len) / bounce_len)

        echo_decay = np.exp(-2 * t / (duration_ms / 1000))
        signal *= echo_decay
        signal = np.clip(signal, -1, 1)
        return (signal * 32767).astype(np.int16)

    def _gen_near_miss_whizz(self) -> np.ndarray | None:
        """Generate near miss bullet whizz - fast frequency sweep from high to low."""
        import numpy as np

        duration_ms = 180
        samples = int(44100 * duration_ms / 1000)

        freq_start = 6000
        freq_end = 800
        freq_sweep = np.linspace(freq_start, freq_end, samples)

        phase = np.cumsum(2 * np.pi * freq_sweep / 44100)
        tone = np.sin(phase) * 0.7

        noise_floor = np.random.uniform(-0.15, 0.15, samples)

        envelope = np.ones(samples)
        rise = int(samples * 0.15)
        fall_start = int(samples * 0.6)
        envelope[:rise] = np.linspace(0, 1, rise)
        envelope[fall_start:] *= np.linspace(1, 0.1, samples - fall_start)

        signal = (tone + noise_floor) * envelope
        signal = np.clip(signal, -1, 1)
        return (signal * 32767).astype(np.int16)

    def _gen_smoke_deploy_hiss(self) -> np.ndarray | None:
        """Generate smoke grenade deploy - filtered white noise with slow decay."""
        import numpy as np

        duration_ms = 2000
        samples = int(44100 * duration_ms / 1000)
        t = np.linspace(0, duration_ms / 1000, samples)

        raw_noise = np.random.uniform(-1, 1, samples)

        hiss_start = int(0.02 * 44100)
        burst = np.zeros(samples)
        burst[:hiss_start] = (
            raw_noise[:hiss_start] * 0.8 * np.exp(-20 * np.arange(hiss_start) / hiss_start)
        )

        sustained = raw_noise * 0.4 * np.exp(-0.8 * t / (duration_ms / 1000))

        signal = burst + sustained
        low_pass = 0.95
        for i in range(1, samples):
            signal[i] = low_pass * signal[i - 1] + (1 - low_pass) * signal[i]

        signal = np.clip(signal, -1, 1)
        return (signal * 32767).astype(np.int16)

    def _gen_suppression_fire(self, duration_ms: int = 1500) -> np.ndarray | None:
        """Generate suppression fire - sustained machine gun bursts."""
        import numpy as np

        samples = int(44100 * duration_ms / 1000)
        np.linspace(0, duration_ms / 1000, samples)
        signal = np.zeros(samples)

        burst_count = int(duration_ms / 120)
        for i in range(burst_count):
            burst_start = int(i * 120 / 1000 * 44100)
            burst_len = min(int(60 / 1000 * 44100), samples - burst_start)

            if burst_start >= samples or burst_len <= 0:
                break

            burst_t = np.linspace(0, burst_len / 44100, burst_len)
            burst_env = np.exp(-15 * np.arange(burst_len) / burst_len)

            shot = (
                np.sin(2 * np.pi * 180 * burst_t) * 0.5 * burst_env
                + np.random.uniform(-0.4, 0.4, burst_len) * burst_env
            )

            signal[burst_start : burst_start + burst_len] += shot

        overall_envelope = np.ones(samples)
        fade_out = int(samples * 0.85)
        overall_envelope[fade_out:] = np.linspace(1, 0.3, samples - fade_out)

        signal *= overall_envelope * 0.7
        signal = np.clip(signal, -1, 1)
        return (signal * 32767).astype(np.int16)
