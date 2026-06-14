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

from pydantic import BaseModel, Field, ValidationError, model_validator

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic validation models for save data (prevent illegal value injection)
# ---------------------------------------------------------------------------

# Reasonable upper bounds to reject absurd values while allowing normal gameplay
_MAX_HP = 1000
_MAX_AMMO = 500
_MAX_MORALE = 100
_MAX_SUPPRESSION = 200
_MAX_VISION_RANGE = 30
_MAX_TICK = 10_000_000
_MAX_KILLS = 100_000
_MAX_TILE_COORD = 1000
_MAX_ZOOM = 20.0


class SaveHealthData(BaseModel):
    """Validation model for unit health data in save files."""

    hp: int = Field(ge=0, le=_MAX_HP)
    max_hp: int = Field(ge=1, le=_MAX_HP)
    state: str = Field(default="HEALTHY")

    @model_validator(mode="after")
    def hp_not_exceed_max(self) -> "SaveHealthData":
        if self.hp > self.max_hp:
            raise ValueError(f"hp {self.hp} exceeds max_hp {self.max_hp}")
        return self


class SaveMoraleData(BaseModel):
    """Validation model for unit morale data in save files."""

    value: int = Field(ge=0, le=_MAX_MORALE)
    panic_threshold: int = Field(default=30, ge=0, le=_MAX_MORALE)
    suppression: int = Field(default=0, ge=0, le=_MAX_SUPPRESSION)
    state: str = Field(default="RALLIED")


class SaveWeaponData(BaseModel):
    """Validation model for unit weapon data in save files."""

    primary_weapon_id: str = Field(default="")
    ammo_remaining: int = Field(ge=0, le=_MAX_AMMO)
    max_ammo: int = Field(default=10, ge=0, le=_MAX_AMMO)
    reload_ticks_left: int = Field(default=0, ge=0)
    state: str = Field(default="READY")

    @model_validator(mode="after")
    def ammo_not_exceed_max(self) -> "SaveWeaponData":
        if self.max_ammo > 0 and self.ammo_remaining > self.max_ammo:
            raise ValueError(f"ammo_remaining {self.ammo_remaining} exceeds max_ammo {self.max_ammo}")
        return self


class SavePositionData(BaseModel):
    """Validation model for unit position data in save files."""

    tile_coord: dict[str, int] = Field(default_factory=lambda: {"x": 0, "y": 0})
    pixel_offset: dict[str, int] = Field(default_factory=lambda: {"x": 0, "y": 0})
    facing_rad: float = Field(default=0.0, ge=-6.2832, le=6.2832)


class SaveVisionData(BaseModel):
    """Validation model for unit vision data in save files."""

    range_tiles: int = Field(default=6, ge=0, le=_MAX_VISION_RANGE)
    angle_rad: float = Field(default=3.1416, ge=0.0, le=6.2832)


class SaveUnitData(BaseModel):
    """Validation model for unit data in save files."""

    id: str = Field(default="")
    name: str = Field(default="")
    faction: str = Field(default="ALLIES")
    unit_type: str = Field(default="INFANTRY_SQUAD")
    health: SaveHealthData = Field(default_factory=lambda: SaveHealthData(hp=1, max_hp=1))
    morale: SaveMoraleData = Field(default_factory=SaveMoraleData)
    weapon: SaveWeaponData = Field(default_factory=SaveWeaponData)
    position: SavePositionData = Field(default_factory=SavePositionData)
    vision: SaveVisionData = Field(default_factory=SaveVisionData)
    squad_id: str | None = Field(default=None)
    is_alive: bool = Field(default=True)


class SaveCameraData(BaseModel):
    """Validation model for camera data in save files."""

    position: dict[str, float] = Field(default_factory=lambda: {"x": 0.0, "y": 0.0})
    zoom: float = Field(default=1.0, gt=0.0, le=_MAX_ZOOM)


class SaveBattleStatsData(BaseModel):
    """Validation model for battle stats in save files."""

    allies_kills: int = Field(default=0, ge=0, le=_MAX_KILLS)
    axis_kills: int = Field(default=0, ge=0, le=_MAX_KILLS)
    ticks_elapsed: int = Field(default=0, ge=0, le=_MAX_TICK)


class SaveGameStateData(BaseModel):
    """Validation model for the top-level game state in save files."""

    version: str = Field(default="0.1.1")
    tick: int = Field(default=0, ge=0, le=_MAX_TICK)
    paused: bool = Field(default=False)
    side_turn: str = Field(default="allies")
    camera: SaveCameraData = Field(default_factory=SaveCameraData)
    selected_unit_ids: list[str] = Field(default_factory=list)
    units: list[SaveUnitData] = Field(default_factory=list)
    battle_stats: SaveBattleStatsData = Field(default_factory=SaveBattleStatsData)

    model_config = {"extra": "allow"}


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
    SAVE_DIR_NAME = ""
    MAX_SLOTS = 8
    CURRENT_VERSION = "0.1.1"

    def __init__(self, base_dir: Path | str | None = None):
        if isinstance(base_dir, str):
            base_dir = Path(base_dir)
        self._base_dir = (
            Path(base_dir) if base_dir else Path(__file__).resolve().parent.parent.parent / "saves"
        )
        self._save_dir = self._base_dir / self.SAVE_DIR_NAME if self.SAVE_DIR_NAME else self._base_dir
        self._save_dir.mkdir(parents=True, exist_ok=True)
        self._hmac_key = self._get_hmac_key()

    _DEFAULT_KEY = b""  # Empty default — dev environment uses random key
    _using_default_key: bool = False

    @staticmethod
    def _get_hmac_key() -> bytes:
        env_key = os.environ.get("PYCC2_SAVE_HMAC_KEY")
        if env_key:
            try:
                key = env_key.encode("utf-8")
                if len(key) < 32:
                    logger.warning("HMAC key too short (%d bytes), minimum is 32. Generating random key.", len(key))
                    import secrets
                    key = secrets.token_bytes(32)
                return key
            except (AttributeError, UnicodeEncodeError) as e:
                logging.info(f"HMAC key from env failed: {e}")
        config_path = Path(__file__).resolve().parent.parent / "config" / "secrets.toml"
        if config_path.exists():
            try:
                for line in config_path.read_text().splitlines():
                    line = line.strip()
                    if line.startswith("hmac_key") and "=" in line:
                        key_val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        key = key_val.encode("utf-8")
                        if len(key) < 32:
                            logger.warning("HMAC key too short (%d bytes), minimum is 32. Generating random key.", len(key))
                            import secrets
                            key = secrets.token_bytes(32)
                        return key
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
        # Dev environment: use random session key for security.
        # Production must set PYCC2_SAVE_HMAC_KEY or config/secrets.toml.
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
        return hmac.HMAC(self._hmac_key, data_bytes, hashlib.sha256).hexdigest()

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

            # Atomic write: write to temp file first, then rename
            tmp_path = filepath.with_suffix(".tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(final_json)
            tmp_path.replace(filepath)

            # Restrict file permissions to owner-only (security hardening)
            # Silently skip in environments where chmod is not supported (e.g., some test containers)
            try:
                os.chmod(filepath, 0o600)
            except OSError:
                logger.debug("Could not set restrictive permissions on %s (unsupported in this environment)", filepath)
            return True
        except (OSError, TypeError, ValueError) as e:
            logger.warning("Save game failed for slot %d: %s", slot, e)
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

            # Pydantic validation: reject illegal values (negative HP, absurd ammo, etc.)
            state_data = data.get("state", {})
            try:
                validated = SaveGameStateData(**state_data)
                # Use validated data (coerced & bounds-checked) for further processing
                state_data = validated.model_dump()
            except ValidationError as exc:
                logger.warning("Save data validation failed for slot %d: %s", slot, exc)
                return None, None, SaveSlotStatus.CORRUPTED

            meta_dict = data.get("meta", {})
            save_version = meta_dict.get("version", "0.0")
            if save_version != self.CURRENT_VERSION:
                meta = SaveMetaData(
                    **{k: v for k, v in meta_dict.items() if k in SaveMetaData.__dataclass_fields__}
                )
                return state_data, meta, SaveSlotStatus.INCOMPATIBLE

            meta = SaveMetaData(
                **{k: v for k, v in meta_dict.items() if k in SaveMetaData.__dataclass_fields__}
            )
            return state_data, meta, SaveSlotStatus.OK

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
