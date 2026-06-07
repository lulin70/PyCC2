from __future__ import annotations

import logging
import hashlib
import hmac
import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class SaveSlotStatus(Enum):
    EMPTY = "empty"
    OK = "ok"
    CORRUPTED = "corrupted"
    INCOMPATIBLE = "incompatible"


@dataclass(slots=True)
class SaveMetaData:
    version: str = "0.1.1"
    saved_at: str = ""
    tick: int = 0
    mission_id: str = ""
    allies_alive: int = 0
    axis_alive: int = 0
    game_result: str = ""
    playtime_seconds: float = 0.0
    notes: str = ""


@dataclass
class SaveFile:
    meta: SaveMetaData
    game_state_dict: dict[str, Any]
    hmac_signature: str = ""


class SecureSaveManager:
    SAVE_DIR_NAME = "saves"
    MAX_SLOTS = 8
    CURRENT_VERSION = "0.1.1"

    def __init__(self, base_dir: Path | str | None = None):
        if isinstance(base_dir, str):
            base_dir = Path(base_dir)
        self._base_dir = (
            Path(base_dir) if base_dir else Path(__file__).resolve().parent.parent.parent / "saves"
        )
        self._save_dir = self._base_dir / self.SAVE_DIR_NAME
        self._save_dir.mkdir(parents=True, exist_ok=True)
        self._hmac_key = self._get_hmac_key()

    _DEFAULT_KEY = b""  # Empty default — dev environment uses random key
    _using_default_key: bool = False

    @staticmethod
    def _get_hmac_key() -> bytes:
        env_key = os.environ.get("PYCC2_SAVE_HMAC_KEY")
        if env_key:
            try:
                return env_key.encode("utf-8")
            except (AttributeError, UnicodeEncodeError) as e:
                logging.info(f"HMAC key from env failed: {e}")
        config_path = Path(__file__).resolve().parent.parent / "config" / "secrets.toml"
        if config_path.exists():
            try:
                for line in config_path.read_text().splitlines():
                    line = line.strip()
                    if line.startswith("hmac_key") and "=" in line:
                        key_val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        return key_val.encode("utf-8")
            except Exception as e:
                logging.info(f"HMAC key from config failed: {e}")
        import warnings

        is_production = os.environ.get("PYCC2_ENV", "").lower() == "production"
        if is_production:
            raise RuntimeError(
                "Production environment requires a secure HMAC key. "
                "Set PYCC2_SAVE_HMAC_KEY environment variable or "
                "provide config/secrets.toml with hmac_key."
            )
        warnings.warn(
            "No HMAC key configured. Using random key for this session. "
            "Set PYCC2_SAVE_HMAC_KEY env var for persistent keys.",
            UserWarning,
            stacklevel=2,
        )
        SecureSaveManager._using_default_key = True
        # Generate a random key for this session (saves won't be portable across sessions)
        import secrets
        return secrets.token_bytes(32)

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """Remove path traversal characters from filename."""
        safe = re.sub(r'[\\/:*?"<>|]', '_', filename)
        safe = os.path.basename(safe)
        if not safe or safe.startswith('.'):
            safe = 'save'
        return safe

    @classmethod
    def is_secure(cls) -> bool:
        return not cls._using_default_key

    def _slot_path(self, slot: int) -> Path:
        if not 0 <= slot < self.MAX_SLOTS:
            raise ValueError(f"Slot must be 0-{self.MAX_SLOTS - 1}, got {slot}")
        return self._save_dir / f"save_slot_{slot}.json"

    def _compute_hmac(self, data_bytes: bytes) -> str:
        return hmac.new(self._hmac_key, data_bytes, hashlib.sha256).hexdigest()

    def _serialize_state(self, state_dict: dict) -> str:
        return json.dumps(state_dict, default=str, ensure_ascii=False, indent=2)

    def _deserialize_state(self, json_str: str) -> dict:
        return json.loads(json_str)

    def save_game(self, slot: int, state_dict: dict, meta: SaveMetaData | None = None) -> bool:
        try:
            filepath = self._slot_path(slot)

            if meta is None:
                meta = SaveMetaData()
            meta.saved_at = datetime.now(UTC).isoformat()
            meta.version = self.CURRENT_VERSION

            save_data = {
                "meta": asdict(meta),
                "state": state_dict,
            }

            json_str = self._serialize_state(save_data)
            signature = self._compute_hmac(json_str.encode("utf-8"))

            complete_save = {
                "meta": asdict(meta),
                "state": state_dict,
                "hmac": signature,
            }

            final_json = self._serialize_state(complete_save)

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(final_json)

            return True
        except (OSError, TypeError, ValueError) as e:
            return False

    def load_game(self, slot: int) -> tuple[dict | None, SaveMetaData | None, SaveSlotStatus]:
        filepath = self._slot_path(slot)

        if not filepath.exists():
            return None, None, SaveSlotStatus.EMPTY

        try:
            with open(filepath, encoding="utf-8") as f:
                content = f.read()

            data = self._deserialize_state(content)

            stored_hmac = data.get("hmac", "")
            if not stored_hmac:
                return None, None, SaveSlotStatus.CORRUPTED

            payload_for_check = {
                "meta": data.get("meta", {}),
                "state": data.get("state", {}),
            }
            payload_json = self._serialize_state(payload_for_check)
            computed_hmac = self._compute_hmac(payload_json.encode("utf-8"))

            if not hmac.compare_digest(stored_hmac, computed_hmac):
                return None, None, SaveSlotStatus.CORRUPTED

            meta_dict = data.get("meta", {})
            save_version = meta_dict.get("version", "0.0")
            if save_version != self.CURRENT_VERSION:
                meta = SaveMetaData(
                    **{k: v for k, v in meta_dict.items() if k in SaveMetaData.__dataclass_fields__}
                )
                return data.get("state"), meta, SaveSlotStatus.INCOMPATIBLE

            meta = SaveMetaData(
                **{k: v for k, v in meta_dict.items() if k in SaveMetaData.__dataclass_fields__}
            )
            return data.get("state"), meta, SaveSlotStatus.OK

        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            return None, None, SaveSlotStatus.CORRUPTED

    def delete_save(self, slot: int) -> bool:
        filepath = self._slot_path(slot)
        if filepath.exists():
            filepath.unlink()
            return True
        return False

    def get_slot_info(self, slot: int) -> tuple[SaveMetaData | None, SaveSlotStatus]:
        _, meta, status = self.load_game(slot)
        return meta, status

    def list_all_slots(self) -> list[tuple[int, SaveMetaData | None, SaveSlotStatus]]:
        results = []
        for i in range(self.MAX_SLOTS):
            meta, status = self.get_slot_info(i)
            results.append((i, meta, status))
        return results

    def find_empty_slot(self) -> int | None:
        for i in range(self.MAX_SLOTS):
            _, status = self.get_slot_info(i)
            if status == SaveSlotStatus.EMPTY:
                return i
        return None

    def export_state_from_game_loop(self, game_loop) -> dict:
        state = game_loop.state
        units_data = []
        for u in state.units:
            unit_dict = {
                "id": u.id,
                "name": u.name,
                "faction": u.faction.name,
                "unit_type": u.unit_type.name,
                "health": {
                    "hp": u.health.hp,
                    "max_hp": u.health.max_hp,
                    "state": u.health.state.name,
                },
                "morale": {
                    "value": u.morale.value,
                    "panic_threshold": u.morale.panic_threshold,
                    "suppression": u.morale.suppression,
                    "state": u.morale.state.name,
                },
                "weapon": {
                    "primary_weapon_id": u.weapon.primary_weapon_id,
                    "ammo_remaining": u.weapon.ammo_remaining,
                    "max_ammo": u.weapon.max_ammo,
                    "reload_ticks_left": u.weapon.reload_ticks_left,
                    "state": u.weapon.state.name,
                },
                "position": {
                    "tile_coord": {"x": u.position.tile_coord.x, "y": u.position.tile_coord.y},
                    "pixel_offset": {
                        "x": u.position.pixel_position.x - u.position.tile_coord.x * 48,
                        "y": u.position.pixel_position.y - u.position.tile_coord.y * 48,
                    },
                    "facing_rad": u.position.facing_rad,
                },
                "vision": {
                    "range_tiles": u.vision.range_tiles,
                    "angle_rad": u.vision.angle_rad,
                },
                "squad_id": u.squad_id,
                "is_alive": u.is_alive,
            }
            units_data.append(unit_dict)

        return {
            "version": self.CURRENT_VERSION,
            "tick": state.tick,
            "paused": state.paused,
            "side_turn": state.side_turn,
            "camera": {
                "position": {"x": state.camera.position.x, "y": state.camera.position.y},
                "zoom": state.camera.zoom,
            },
            "selected_unit_ids": list(state.selected_unit_ids),
            "units": units_data,
            "battle_stats": self._extract_battle_stats(game_loop),
        }

    def _extract_battle_stats(self, game_loop) -> dict:
        battle_stats = None
        if hasattr(game_loop, "victory_manager") and game_loop.victory_manager is not None:
            battle_stats = game_loop.victory_manager.battle_stats
        if battle_stats is not None:
            return {
                "allies_kills": battle_stats.allies_kills,
                "axis_kills": battle_stats.axis_kills,
                "ticks_elapsed": battle_stats.ticks_elapsed,
            }
        return {}
