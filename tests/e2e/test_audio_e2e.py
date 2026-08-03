"""E2E: Audio System — TC-060~068 coverage (P0 盲区修复).

Verifies audio subsystem integration with GameLoop: weapon sounds,
environmental audio, BGM, volume control, resource-missing graceful
degradation, stereo positioning, voice command system.

覆盖场景 (tests/e2e/E2E_REAL_USER_SCENARIOS.md 第六章):
  - TC-060: 音频系统初始化与 GameLoop 集成 (P0)
  - TC-061: 武器音效在战斗事件下播放 (P0)
  - TC-062: 环境音效系统运行不崩溃 (P0)
  - TC-063: BGM 系统初始化 (P1)
  - TC-064: 音量设置与读取 (P1)
  - TC-065: 音频资源缺失时优雅降级 (P2)
  - TC-066: 3D 立体声定位不崩溃 (P2)
  - TC-067: 语音命令系统初始化不崩溃 (P2)

设计说明:
  - headless 环境音频驱动是 dummy，音效不会真正播放，验证重点是
    "不崩溃 + API 可调用 + 状态正确"。
  - 使用真实组件 (Real SoundSystem / Real GameLoop) 而非 Mock。
  - 文档中的类名 (WeaponSoundSystem/EnvironmentalAudio/BGMSystem/
    StereoSoundManager) 与代码实际类名 (WeaponSoundGenerator/
    EnvironmentalAudioSystem/BGMGenerator/StereoSoundSystem) 存在
    差异，测试基于实际 API 编写。
"""

from __future__ import annotations

import os
import sys

# Ensure tests/e2e/ is in sys.path so `from conftest import GameLoopFactory`
# works when running this file individually. With `tests/__init__.py` and
# `tests/e2e/__init__.py` present, pytest uses package-style imports and does
# not add tests/e2e/ to sys.path for single-file runs.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_JOYSTICK_DRIVER", "dummy")

import pytest
from conftest import GameLoopFactory

from pycc2.domain.value_objects.audio_enums import SoundType
from pycc2.domain.value_objects.vec2 import Vec2
from pycc2.infrastructure.audio.bgm_system import (
    AmbientSoundGenerator,
    BGMGenerator,
    MusicMood,
)
from pycc2.infrastructure.audio.environmental_audio import (
    EnvironmentalAudioSystem,
    EnvironmentSoundType,
)
from pycc2.infrastructure.audio.stereo_sound import StereoSoundSystem
from pycc2.infrastructure.audio.voice_command_system import (
    VoiceCommandSystem,
    VoiceCommandType,
)
from pycc2.infrastructure.audio.weapon_sounds import (
    WEAPON_SOUND_PROFILES,
    WeaponSoundGenerator,
)
from pycc2.presentation.audio.combat_sound_events import CombatSoundEvent
from pycc2.presentation.audio.enhanced_sound_bridge import EnhancedSoundSystem
from pycc2.presentation.audio.sound_system import SoundSystem


class TestAudioSystemE2E:
    """音频系统 E2E 测试 — TC-060~068 覆盖。"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试方法前初始化 pygame headless 环境。"""
        import pygame

        pygame.init()
        self.screen = pygame.display.set_mode((1280, 720))
        self.pygame = pygame
        yield
        pygame.quit()

    # ------------------------------------------------------------------
    # TC-060: 音频系统初始化与 GameLoop 集成
    # ------------------------------------------------------------------

    def test_audio_system_initializes_with_game_loop(self):
        """GameLoop 装配后音频系统可用 (TC-060)。

        GameLoop.__post_init__ 通过 GameLoopAssembler._init_sound() 自动
        装配 SoundSystem 与 EnvironmentalAudioSystem。验证两个系统均
        可用且 initialized 状态正确。
        """
        factory = GameLoopFactory(self.screen)
        try:
            game_loop = factory.game_loop

            # SoundSystem 应被 GameLoopAssembler 自动装配
            assert game_loop.sound_system is not None, (
                "GameLoop.sound_system 应被 GameLoopAssembler._init_sound() 装配"
            )
            assert isinstance(game_loop.sound_system, SoundSystem)
            assert game_loop.sound_system.initialized is True, "SoundSystem.initialize() 应已被调用"

            # EnvironmentalAudioSystem 应被装配 (允许 None — 优雅降级)
            env_audio = getattr(game_loop, "_environmental_audio", None)
            if env_audio is not None:
                assert isinstance(env_audio, EnvironmentalAudioSystem)

            # 验证音量配置可用
            config = game_loop.sound_system.config
            assert 0.0 <= config.master_volume <= 1.0
            assert 0.0 <= config.sfx_volume <= 1.0

            # 多次运行 tick 不崩溃 (音频事件队列处理)
            errors = factory.run_ticks(count=10, dt=1.0 / 30.0)
            assert errors == [], f"运行 tick 期间发生异常: {errors}"
        finally:
            factory.shutdown()

    # ------------------------------------------------------------------
    # TC-061: 武器音效在战斗事件下播放
    # ------------------------------------------------------------------

    def test_weapon_sound_plays_on_combat_event(self):
        """战斗事件触发武器音效不崩溃 (TC-061)。

        验证 WeaponSoundGenerator 与 SoundSystem.play(SoundType.*) 在
        headless 环境下 API 可调用、不崩溃、返回类型正确。
        """
        # 1) WeaponSoundGenerator: 遍历多个武器 ID, 验证不崩溃
        weapon_ids = ["MG42", "Lee-Enfield", "Sherman 75mm", "M1 Bazooka"]
        for wid in weapon_ids:
            assert wid in WEAPON_SOUND_PROFILES, f"武器 {wid} 应在 WEAPON_SOUND_PROFILES 中"
            # headless 下 mixer 可能未真正初始化, 但 API 不应崩溃
            WeaponSoundGenerator.play_weapon_sound(wid, volume=0.3)

        # 2) 未知武器 ID 应走 _DEFAULT_PROFILE 不崩溃
        WeaponSoundGenerator.play_weapon_sound("nonexistent_weapon_xyz", volume=0.2)

        # 3) SoundSystem.play(SoundType.*): 多种战斗音效
        ss = SoundSystem()
        ss.initialize()
        try:
            combat_sounds = [
                SoundType.RIFLE_SHOT,
                SoundType.MG_BURST,
                SoundType.EXPLOSION,
                SoundType.TANK_CANNON,
                SoundType.AT_GUN,
                SoundType.MORTAR,
                SoundType.SMG,
                SoundType.SNIPER,
                SoundType.HIT_CONFIRM,
                SoundType.UNIT_DEATH,
            ]
            for st in combat_sounds:
                result = ss.play(st)
                assert isinstance(result, bool), (
                    f"play({st}) 应返回 bool, 实际返回 {type(result).__name__}"
                )
        finally:
            ss.shutdown()

    # ------------------------------------------------------------------
    # TC-062: 环境音效系统运行不崩溃
    # ------------------------------------------------------------------

    def test_environmental_audio_runs_without_crash(self):
        """环境音效系统多 tick 运行不崩溃 (TC-062)。

        EnvironmentalAudioSystem 接受上下文输入 (time_of_day / weather /
        combat_intensity / location) 并在 update(dt) 中动态调整环境音,
        验证多帧运行无异常。

        注: EnvironmentalSoundGenerator 生成 mono (1D) 数组, 需 mono mixer。
        若 mixer 已被 SoundSystem 初始化为 stereo, 需先 quit 再让
        EnvironmentalAudioSystem.initialize() 重新以 channels=1 初始化。
        """
        # 重置 mixer, 让 EnvironmentalAudioSystem 以 mono 模式初始化
        # (其生成器输出 1D int16 数组, 与 stereo mixer 不兼容)
        if self.pygame.mixer.get_init():
            self.pygame.mixer.quit()

        env_audio = EnvironmentalAudioSystem()
        env_audio.initialize(self.pygame.mixer)

        # 上下文设置不应崩溃
        env_audio.set_time_of_day(14)  # 下午 2 点
        env_audio.set_location_type("forest")
        env_audio.set_weather_rain(False)
        env_audio.set_combat_intensity(0.1)
        env_audio.set_master_volume(0.4)

        # 多帧 update 不崩溃
        for _ in range(20):
            env_audio.update(dt=1.0 / 30.0)

        # 切换到雨天 + 高战斗强度 (触发音效切换)
        env_audio.set_weather_rain(True)
        env_audio.set_combat_intensity(0.8)
        for _ in range(10):
            env_audio.update(dt=1.0 / 30.0)

        # 切换到夜晚 + 城市
        env_audio.set_weather_rain(False)
        env_audio.set_time_of_day(22)
        env_audio.set_location_type("city")
        env_audio.set_combat_intensity(0.0)
        for _ in range(10):
            env_audio.update(dt=1.0 / 30.0)

        # is_playing / stop_all 不崩溃
        playing_state = env_audio.is_playing(EnvironmentSoundType.WIND)
        assert isinstance(playing_state, bool)
        env_audio.stop_all()

    # ------------------------------------------------------------------
    # TC-063: BGM 系统初始化
    # ------------------------------------------------------------------

    def test_bgm_system_initializes(self):
        """BGM 系统生成不同 mood 的音乐波形 (TC-063)。

        BGMGenerator 与 AmbientSoundGenerator 是无状态的程序化合成器,
        验证 generate_mood_music 返回 int16 ndarray, 不同 mood 均可合成。
        """
        import numpy as np

        # 1) BGMGenerator: 多种 mood
        moods = [
            MusicMood.MENU,
            MusicMood.BATTLE_LIGHT,
            MusicMood.BATTLE_INTENSE,
            MusicMood.VICTORY,
            MusicMood.DEFEAT,
            MusicMood.AMBIENT,
        ]
        for mood in moods:
            wave = BGMGenerator.generate_mood_music(mood, duration=1.0)
            assert isinstance(wave, np.ndarray), (
                f"generate_mood_music({mood}) 应返回 ndarray, 实际 {type(wave).__name__}"
            )
            assert wave.dtype == np.int16, f"波形 dtype 应为 int16, 实际 {wave.dtype}"
            assert len(wave) > 0, f"mood={mood} 波形不应为空"

        # 2) AmbientSoundGenerator: wind / rain / distant_gunfire
        wind = AmbientSoundGenerator.generate_wind(intensity=0.5, duration=1.0)
        assert isinstance(wind, np.ndarray) and wind.dtype == np.int16

        rain = AmbientSoundGenerator.generate_rain(intensity=0.7, duration=1.0)
        assert isinstance(rain, np.ndarray) and rain.dtype == np.int16

        gunfire = AmbientSoundGenerator.generate_distant_gunfire(duration=1.0)
        assert isinstance(gunfire, np.ndarray) and gunfire.dtype == np.int16

    # ------------------------------------------------------------------
    # TC-064: 音量设置与读取
    # ------------------------------------------------------------------

    def test_volume_control_set_get(self):
        """音量设置与读取一致性 (TC-064)。

        SoundSystem 提供 master_volume / sfx_volume / category_volumes
        三层独立控制, 验证 set/get 对称且值被 clamp 到 [0, 1]。
        """
        ss = SoundSystem()
        ss.initialize()
        try:
            # 1) master volume
            ss.set_master_volume(0.3)
            assert ss.config.master_volume == pytest.approx(0.3)
            ss.set_master_volume(1.5)  # 超界应 clamp 到 1.0
            assert ss.config.master_volume == pytest.approx(1.0)
            ss.set_master_volume(-0.5)  # 超界应 clamp 到 0.0
            assert ss.config.master_volume == pytest.approx(0.0)

            # 2) sfx volume
            ss.set_sfx_volume(0.6)
            assert ss.config.sfx_volume == pytest.approx(0.6)
            ss.set_sfx_volume(2.0)
            assert ss.config.sfx_volume == pytest.approx(1.0)

            # 3) category volumes (ui / combat / environment / music)
            for category in ["ui", "combat", "environment", "music"]:
                ss.set_category_volume(category, 0.7)
                got = ss.get_category_volume(category)
                assert got == pytest.approx(0.7), f"category={category} set 0.7 but get {got}"

            # 4) 未知 category 应返回默认 1.0 (不崩溃)
            unknown_vol = ss.get_category_volume("nonexistent_category")
            assert unknown_vol == pytest.approx(1.0)

            # 5) toggle 开关 — play 在 disabled 后应返回 False
            initial_enabled = ss.config.enabled
            ss.toggle()
            assert ss.config.enabled is (not initial_enabled)
            # 恢复并播放验证
            if not ss.config.enabled:
                ss.toggle()
            assert ss.config.enabled is True
        finally:
            ss.shutdown()

    # ------------------------------------------------------------------
    # TC-065: 音频资源缺失时优雅降级
    # ------------------------------------------------------------------

    def test_audio_resource_missing_graceful_degradation(self):
        """音频资源缺失时优雅降级不崩溃 (TC-065)。

        EnhancedSoundSystem 在 WAV 文件缺失时回退到程序化合成;
        WeaponSoundGenerator 对未知 weapon_id 走 _DEFAULT_PROFILE;
        SoundSystem 未初始化时 play() 返回 False。所有路径均不抛异常。
        """
        # 1) EnhancedSoundSystem: 多数事件映射的 file_path 为空字符串,
        #    验证 play_combat_event 走程序化 fallback 不崩溃。
        ess = EnhancedSoundSystem()
        ess._base_path = ess._base_path / "nonexistent_dir"  # 强制文件缺失
        init_ok = ess.initialize()
        # headless 下 init 可能成功也可能失败, 都不应崩溃
        assert isinstance(init_ok, bool)

        for event in [
            CombatSoundEvent.RIFLE_FIRE,
            CombatSoundEvent.EXPLOSION,
            CombatSoundEvent.GRENADE_EXPLOSION_SHORT,  # 无文件, 走 fallback
            CombatSoundEvent.AIRSTRIKE_BOMB,
        ]:
            result = ess.play_combat_event(event, volume=0.3)
            assert isinstance(result, bool), (
                f"play_combat_event({event}) 应返回 bool, 实际 {type(result).__name__}"
            )
        ess.shutdown()

        # 2) WeaponSoundGenerator: 未知 weapon 不崩溃 (走 _DEFAULT_PROFILE)
        WeaponSoundGenerator.play_weapon_sound("totally_unknown_weapon", volume=0.2)
        profile = WeaponSoundGenerator.get_weapon_profile("totally_unknown_weapon")
        assert profile is not None
        assert profile.weapon_id == "unknown"

        # 3) SoundSystem 未初始化 play() 返回 False 不崩溃
        ss = SoundSystem()  # 未调用 initialize
        assert ss.initialized is False
        result = ss.play(SoundType.RIFLE_SHOT)
        assert result is False, "未初始化的 SoundSystem.play() 应返回 False"

        # 4) SoundSystem disabled 后 play() 返回 False
        ss2 = SoundSystem()
        ss2.initialize()
        ss2._config.enabled = False
        assert ss2.play(SoundType.RIFLE_SHOT) is False
        ss2.shutdown()

    # ------------------------------------------------------------------
    # TC-066: 3D 立体声定位不崩溃
    # ------------------------------------------------------------------

    def test_stereo_positioning_no_crash(self):
        """3D 立体声定位计算不崩溃 (TC-066)。

        StereoSoundSystem 与 SoundSystem.calculate_stereo_pan 均基于
        源点/听者点位置计算左右声道, 验证多场景计算结果在合理区间。
        """
        # 1) StereoSoundSystem (infrastructure/audio/stereo_sound.py)
        stereo = StereoSoundSystem()

        # 源在听者正前方 — pan 接近 0
        pan_center = stereo.calculate_stereo_pan(listener_pos=(10.0, 10.0), source_pos=(10.0, 5.0))
        assert -1.0 <= pan_center <= 1.0

        # 源在听者右侧 — pan > 0
        pan_right = stereo.calculate_stereo_pan(listener_pos=(10.0, 10.0), source_pos=(15.0, 10.0))
        assert -1.0 <= pan_right <= 1.0
        assert pan_right > 0, f"右侧源 pan 应 > 0, 实际 {pan_right}"

        # 源在听者左侧 — pan < 0
        pan_left = stereo.calculate_stereo_pan(listener_pos=(10.0, 10.0), source_pos=(5.0, 10.0))
        assert -1.0 <= pan_left <= 1.0
        assert pan_left < 0, f"左侧源 pan 应 < 0, 实际 {pan_left}"

        # 同位置 — pan 为 0
        pan_same = stereo.calculate_stereo_pan(listener_pos=(10.0, 10.0), source_pos=(10.0, 10.0))
        assert pan_same == pytest.approx(0.0)

        # 2) StereoSoundSystem.calculate_volume 距离衰减
        vol_close = stereo.calculate_volume(
            listener_pos=(10.0, 10.0), source_pos=(10.0, 11.0), base_volume=1.0
        )
        vol_far = stereo.calculate_volume(
            listener_pos=(10.0, 10.0),
            source_pos=(10.0, 10.0 + stereo.MAX_DISTANCE + 1),
            base_volume=1.0,
        )
        assert 0.0 <= vol_close <= 1.0
        assert vol_far == pytest.approx(0.0), "超出 MAX_DISTANCE 应返回 0"
        assert vol_close > vol_far

        # 3) SoundSystem.calculate_stereo_pan (Vec2 版本)
        ss = SoundSystem()
        ss.initialize()
        try:
            left_vol, right_vol = ss.calculate_stereo_pan(
                source_pos=Vec2(15.0, 10.0),
                listener_pos=Vec2(10.0, 10.0),
                listener_facing=0.0,
            )
            assert 0.0 <= left_vol <= 1.0
            assert 0.0 <= right_vol <= 1.0
        finally:
            ss.shutdown()

    # ------------------------------------------------------------------
    # TC-067: 语音命令系统初始化不崩溃
    # ------------------------------------------------------------------

    def test_voice_command_system_no_crash(self):
        """语音命令系统冷却与文本查询不崩溃 (TC-067)。

        VoiceCommandSystem 提供 cooldown / play_command / get_command_text
        三个 API, 验证 cooldown 生效、文本映射完整、play_command 不崩溃。
        """
        voice = VoiceCommandSystem()

        # 1) 所有 VoiceCommandType 应有对应文本
        for cmd_type in VoiceCommandType:
            text = voice.get_command_text(cmd_type)
            assert isinstance(text, str)
            assert len(text) > 0, f"cmd={cmd_type} 文本不应为空"

        # 2) 冷却机制: 首次 can_play 应为 True
        t0 = 0.0
        assert voice.can_play(VoiceCommandType.MOVING, t0) is True

        # 3) play_command 不崩溃 (sound_system=None, 应返回 True 用于测试)
        result = voice.play_command(VoiceCommandType.MOVING, t0, sound_system=None)
        assert isinstance(result, bool)

        # 4) 冷却期内 can_play 应为 False
        t1 = 1.0  # < _cooldown_time (3.0s)
        assert voice.can_play(VoiceCommandType.MOVING, t1) is False

        # 5) 冷却结束后 can_play 应为 True
        t2 = 5.0  # > _cooldown_time
        assert voice.can_play(VoiceCommandType.MOVING, t2) is True

        # 6) 不同 cmd_type 互不影响冷却
        assert voice.can_play(VoiceCommandType.CONTACT, t1) is True
        result = voice.play_command(VoiceCommandType.CONTACT, t1, sound_system=None)
        assert isinstance(result, bool)

        # 7) 预存 API 不匹配 bug (记录, 不在本测试任务修复范围):
        #    VoiceCommandSystem.play_command(sound_system=ss) 调用
        #    sound_system.play(str), 但 SoundSystem.play() 期望 SoundType
        #    枚举 (访问 .name 属性), 触发 AttributeError。
        #    待修复 voice_command_system.py:56 后可补充真实 SoundSystem 集成用例。
