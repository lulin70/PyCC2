"""E2E tests for TC-054 (HMAC tamper protection) and TC-059 (path traversal safety).

Covers:
  - TC-054: SecureSaveManager HMAC-SHA256 signature presence and tamper rejection.
    Saves are signed with HMAC-SHA256 over the {meta, state} payload; any
    modification of state/meta invalidates the signature and the load is
    rejected as CORRUPTED.
  - TC-059: Filename sanitization rejects path traversal (../) and absolute
    paths, confining saves to the save directory. Slot-based access also
    rejects out-of-range slot indices.

Uses the real GameLoop (assembled via conftest.GameLoopFactory) and real
SecureSaveManager with tmp_path isolation and a stable PYCC2_SAVE_HMAC_KEY
env var (so save/load work across instances - simulating a real
restart-cycle E2E). No Mock for domain objects.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest
from conftest import GameLoopFactory

from pycc2.infrastructure.save_system import (
    SaveMetaData,
    SaveSlotStatus,
    SecureSaveManager,
)

# Stable HMAC key so save/load work across separate SecureSaveManager
# instances (simulates: save -> exit game -> restart -> load). 32+ bytes.
_STABLE_HMAC_KEY = "pycc2-e2e-security-test-hmac-key-0123456789abcdef"


def _make_real_state_dict() -> dict:
    """Build a minimal but valid SaveGameStateData-compatible state dict.

    Constructed from real values (no Mock) - satisfies SaveGameStateData
    pydantic validation on load.
    """
    return {
        "version": SecureSaveManager.CURRENT_VERSION,
        "tick": 1234,
        "paused": False,
        "side_turn": "allies",
        "camera": {"position": {"x": 100.0, "y": 200.0}, "zoom": 1.5},
        "selected_unit_ids": ["u1"],
        "units": [
            {
                "id": "u1",
                "name": "Alpha Squad",
                "faction": "ALLIES",
                "unit_type": "INFANTRY_SQUAD",
                "health": {"hp": 75, "max_hp": 100, "state": "HEALTHY"},
                "morale": {
                    "value": 70,
                    "panic_threshold": 30,
                    "suppression": 0,
                    "state": "RALLIED",
                },
                "weapon": {
                    "primary_weapon_id": "rifle",
                    "ammo_remaining": 7,
                    "max_ammo": 10,
                    "reload_ticks_left": 0,
                    "state": "READY",
                },
                "position": {
                    "tile_coord": {"x": 5, "y": 6},
                    "pixel_offset": {"x": 0, "y": 0},
                    "facing_rad": 0.0,
                },
                "vision": {"range_tiles": 6, "angle_rad": 3.1416},
                "squad_id": None,
                "is_alive": True,
            }
        ],
        "battle_stats": {"allies_kills": 3, "axis_kills": 1, "ticks_elapsed": 1234},
    }


# ---------------------------------------------------------------------------
# TC-054 + TC-059: Save security E2E
# ---------------------------------------------------------------------------


class TestSaveSecurityE2E:
    """TC-054 + TC-059: Save file HMAC tamper protection and path traversal safety."""

    @pytest.fixture(autouse=True)
    def pygame_env(self):
        """Initialize pygame headless with a 1280x720 screen."""
        pygame.init()
        self.screen = pygame.display.set_mode((1280, 720))
        yield
        pygame.quit()

    @pytest.fixture
    def game_loop(self):
        """Assemble a real GameLoop via GameLoopFactory (E2E assembly check)."""
        factory = GameLoopFactory(self.screen)
        yield factory.game_loop
        factory.shutdown()

    @pytest.fixture
    def secure_manager(self, tmp_path: Path, monkeypatch) -> SecureSaveManager:
        """SecureSaveManager with a stable HMAC key + tmp_path isolation.

        The stable key lets a second SecureSaveManager instance (constructed
        after tampering) verify the signature - simulating a real restart.
        """
        monkeypatch.setenv("PYCC2_SAVE_HMAC_KEY", _STABLE_HMAC_KEY)
        return SecureSaveManager(base_dir=tmp_path)

    def test_save_file_hmac_signature_present(
        self, secure_manager: SecureSaveManager, tmp_path: Path
    ) -> None:
        """TC-054: Saved file contains a non-empty HMAC-SHA256 signature field."""
        state = _make_real_state_dict()
        meta = SaveMetaData(tick=1234, mission_id="sec_test", allies_alive=1, axis_alive=0)
        assert secure_manager.save_game(0, state, meta) is True, "save_game should succeed"

        slot_file = tmp_path / "save_slot_0.json"
        assert slot_file.exists(), "Save file should be created on disk"
        with open(slot_file, encoding="utf-8") as f:
            data = json.load(f)

        assert "hmac" in data, "Save file must contain HMAC signature field"
        assert isinstance(data["hmac"], str)
        assert len(data["hmac"]) > 0, "HMAC signature must not be empty"
        # HMAC-SHA256 produces a 64-char hex digest
        assert len(data["hmac"]) == 64, (
            f"HMAC-SHA256 hex digest should be 64 chars, got {len(data['hmac'])}"
        )

    def test_tampered_save_file_rejected(
        self, secure_manager: SecureSaveManager, tmp_path: Path
    ) -> None:
        """TC-054: Tampering with save content -> load rejected as CORRUPTED.

        Simulates a cheat attempt: player edits the save file to set unit HP
        to 999. The HMAC signature no longer matches -> CORRUPTED.
        """
        state = _make_real_state_dict()
        secure_manager.save_game(0, state, SaveMetaData(tick=1234))

        slot_file = secure_manager._slot_path(0)
        with open(slot_file, encoding="utf-8") as f:
            data = json.load(f)

        # Tamper: modify unit HP (a realistic cheat attempt)
        data["state"]["units"][0]["health"]["hp"] = 999
        with open(slot_file, "w", encoding="utf-8") as f:
            json.dump(data, f)

        # Use a FRESH manager instance (simulates restart) with the same key
        fresh_manager = SecureSaveManager(base_dir=tmp_path)
        loaded_state, loaded_meta, status = fresh_manager.load_game(0)
        assert status == SaveSlotStatus.CORRUPTED, (
            "Tampered save must be rejected (HMAC verification failed)"
        )
        assert loaded_state is None, "Corrupted save should return None state"
        assert loaded_meta is None, "Corrupted save should return None meta"

    def test_save_file_path_no_traversal(self, tmp_path: Path) -> None:
        """TC-059: Filename with ../ path traversal is sanitized to a safe name.

        _sanitize_filename strips path separators and extracts the basename,
        preventing writes outside the save directory.
        """
        malicious_names = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32\\config",
            "save/../../escape",
            "../../../../tmp/evil",
            "/etc/shadow",
        ]
        for name in malicious_names:
            safe = SecureSaveManager._sanitize_filename(name)
            # No path separators survive sanitization
            assert "/" not in safe, f"Sanitized '{safe}' still has '/' (from '{name}')"
            assert "\\" not in safe, f"Sanitized '{safe}' still has '\\' (from '{name}')"
            # Must be a bare filename (no directory component)
            assert safe == os.path.basename(safe), (
                f"Sanitized '{safe}' must be a bare filename (from '{name}')"
            )
            # Resolved path must stay within the save directory
            resolved = (tmp_path / safe).resolve()
            save_dir_resolved = tmp_path.resolve()
            assert str(resolved).startswith(str(save_dir_resolved)), (
                f"Sanitized name '{safe}' escapes save dir (from '{name}')"
            )

    def test_save_filename_validation(self, tmp_path: Path) -> None:
        """TC-059: Illegal filenames (special chars / absolute paths) are cleaned.

        Also verifies slot-based access rejects out-of-range slots (defense
        in depth).
        """
        # Absolute paths -> path separators replaced, basename extracted (no traversal)
        for abs_name in ("/etc/passwd", "C:\\Windows\\evil"):
            safe = SecureSaveManager._sanitize_filename(abs_name)
            assert "/" not in safe, f"Absolute path '{abs_name}' still has '/' in '{safe}'"
            assert "\\" not in safe, f"Absolute path '{abs_name}' still has '\\' in '{safe}'"
            assert safe == os.path.basename(safe), (
                f"Sanitized '{safe}' must be a bare filename (from '{abs_name}')"
            )

        # Special characters -> replaced with underscore
        safe = SecureSaveManager._sanitize_filename("save<>:|?*.json")
        for ch in '<>:"|?*':
            assert ch not in safe, f"Special char '{ch}' survived in '{safe}'"

        # Empty / dot-only -> fallback to 'save'
        assert SecureSaveManager._sanitize_filename("") == "save"
        assert SecureSaveManager._sanitize_filename(".") == "save"
        assert SecureSaveManager._sanitize_filename("..") == "save"

        # Slot-based save rejects out-of-range slots (defense in depth)
        mgr = SecureSaveManager(base_dir=tmp_path)
        with pytest.raises(ValueError):
            mgr._slot_path(-1)
        with pytest.raises(ValueError):
            mgr._slot_path(mgr.MAX_SLOTS)

    def test_save_load_roundtrip_integrity(
        self, secure_manager: SecureSaveManager, game_loop, tmp_path: Path
    ) -> None:
        """TC-054: Normal save->load roundtrip preserves data integrity (OK status).

        Uses the real GameLoop (assembled via GameLoopFactory) to verify E2E
        assembly, then saves/loads a real state dict and checks every field.
        """
        # Verify the real GameLoop assembled successfully (E2E check)
        assert game_loop is not None, "GameLoop should be assembled by GameLoopFactory"

        original_state = _make_real_state_dict()
        original_meta = SaveMetaData(
            tick=1234,
            mission_id="integrity_test",
            allies_alive=1,
            axis_alive=0,
            game_result="ongoing",
            playtime_seconds=120.5,
        )
        assert secure_manager.save_game(0, original_state, original_meta) is True

        # Load with a FRESH manager instance (simulates restart) using same key
        fresh_manager = SecureSaveManager(base_dir=tmp_path)
        loaded_state, loaded_meta, status = fresh_manager.load_game(0)
        assert status == SaveSlotStatus.OK, f"Untampered save must load as OK, got {status}"
        assert loaded_state is not None, "Loaded state must not be None"
        assert loaded_meta is not None, "Loaded meta must not be None"

        # State integrity
        assert loaded_state["tick"] == 1234, "tick should be preserved"
        assert loaded_state["side_turn"] == "allies", "side_turn should be preserved"
        assert loaded_state["camera"]["zoom"] == 1.5, "camera zoom should be preserved"
        assert len(loaded_state["units"]) == 1, "unit count should be preserved"
        assert loaded_state["units"][0]["id"] == "u1", "unit id should be preserved"
        assert loaded_state["units"][0]["health"]["hp"] == 75, "unit HP should be preserved"
        assert loaded_state["units"][0]["weapon"]["ammo_remaining"] == 7, "ammo should be preserved"

        # Meta integrity
        assert loaded_meta.mission_id == "integrity_test", "mission_id should be preserved"
        assert loaded_meta.allies_alive == 1, "allies_alive should be preserved"
        assert loaded_meta.playtime_seconds == 120.5, "playtime_seconds should be preserved"
        assert loaded_meta.version == SecureSaveManager.CURRENT_VERSION, (
            "meta version should be set to CURRENT_VERSION on save"
        )
