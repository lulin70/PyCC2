"""
CC2 Native Map Format Parser.

Reads Close Combat 2 binary map files (Map### format) and converts
CC2 terrain codes to PyCC2 TerrainType enum values.

CC2 Map Binary Format (based on Mafi's CC2 Guides):
    - Maps are stored under X:\\Data\\Data\\Maps\\Map###\\
    - The terrain file (Map### or .txt) contains a flat byte grid
    - Each byte encodes a terrain element (0x00-0x1F)
    - Map dimensions are derived from file size (standard CC2 maps are 40x40)

Supported CC2 terrain codes:
    0x00  Open ground / Short grass
    0x01  Road
    0x02  Dirt
    0x03  Tall grass
    0x04  Hedge / Bush
    0x05  Light woods
    0x06  Dense woods
    0x07  Building (enterable)
    0x08  Building wall (solid)
    0x09  Water (shallow)
    0x0A  Water (deep)
    0x0B  Bridge
    0x0C  Wall
    0x0D  Rubble
    0x0E  Rough / Rocky
    0x0F  Swamp
    0x10-0x1F  Variations and special tiles (mapped to closest base type)
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import Any

from pycc2.domain.value_objects.terrain_type import TerrainType


class CC2TerrainCode(IntEnum):
    """CC2 native terrain type codes as documented in Mafi's CC2 Guides."""

    OPEN = 0x00
    ROAD = 0x01
    DIRT = 0x02
    TALL_GRASS = 0x03
    HEDGE = 0x04
    LIGHT_WOODS = 0x05
    DENSE_WOODS = 0x06
    BUILDING_ENTERABLE = 0x07
    BUILDING_SOLID = 0x08
    SHALLOW_WATER = 0x09
    DEEP_WATER = 0x0A
    BRIDGE = 0x0B
    WALL = 0x0C
    RUBBLE = 0x0D
    ROUGH = 0x0E
    SWAMP = 0x0F
    # Variation codes 0x10-0x1F
    VAR_10 = 0x10
    VAR_11 = 0x11
    VAR_12 = 0x12
    VAR_13 = 0x13
    VAR_14 = 0x14
    VAR_15 = 0x15
    VAR_16 = 0x16
    VAR_17 = 0x17
    VAR_18 = 0x18
    VAR_19 = 0x19
    VAR_1A = 0x1A
    VAR_1B = 0x1B
    VAR_1C = 0x1C
    VAR_1D = 0x1D
    VAR_1E = 0x1E
    VAR_1F = 0x1F


# Mapping from CC2 terrain codes to PyCC2 TerrainType values.
# Variation codes (0x10-0x1F) are mapped to their closest base type.
CC2_TO_PYCC2_MAP: dict[int, TerrainType] = {
    CC2TerrainCode.OPEN: TerrainType.OPEN,
    CC2TerrainCode.ROAD: TerrainType.ROAD,
    CC2TerrainCode.DIRT: TerrainType.ROUGH,
    CC2TerrainCode.TALL_GRASS: TerrainType.GRASS,
    CC2TerrainCode.HEDGE: TerrainType.HEDGE,
    CC2TerrainCode.LIGHT_WOODS: TerrainType.WOODS,
    CC2TerrainCode.DENSE_WOODS: TerrainType.WOODS,
    CC2TerrainCode.BUILDING_ENTERABLE: TerrainType.BUILDING_ENTERABLE,
    CC2TerrainCode.BUILDING_SOLID: TerrainType.BUILDING_SOLID,
    CC2TerrainCode.SHALLOW_WATER: TerrainType.SHALLOW,
    CC2TerrainCode.DEEP_WATER: TerrainType.WATER,
    CC2TerrainCode.BRIDGE: TerrainType.BRIDGE,
    CC2TerrainCode.WALL: TerrainType.WALL,
    CC2TerrainCode.RUBBLE: TerrainType.CRATER,
    CC2TerrainCode.ROUGH: TerrainType.ROUGH,
    CC2TerrainCode.SWAMP: TerrainType.SWAMP,
    # Variation codes — mapped to closest base type.
    # CC2 uses these for visual variants (e.g. different road surfaces,
    # damaged buildings, seasonal grass). They share gameplay properties
    # with their base type.
    0x10: TerrainType.GRASS,  # Grass variation 1
    0x11: TerrainType.GRASS,  # Grass variation 2
    0x12: TerrainType.ROAD,  # Road variation 1 (dirt road)
    0x13: TerrainType.ROAD,  # Road variation 2 (paved)
    0x14: TerrainType.WOODS,  # Woods variation 1 (sparse)
    0x15: TerrainType.WOODS,  # Woods variation 2 (autumn)
    0x16: TerrainType.BUILDING_ENTERABLE,  # Building variation 1
    0x17: TerrainType.BUILDING_SOLID,  # Building variation 1
    0x18: TerrainType.HEDGE,  # Hedge variation (fence line)
    0x19: TerrainType.ROUGH,  # Rough variation 1 (rocky)
    0x1A: TerrainType.ROUGH,  # Rough variation 2 (rubble field)
    0x1B: TerrainType.SHALLOW,  # Shallow water variation (ford)
    0x1C: TerrainType.CRATER,  # Rubble variation (shell hole)
    0x1D: TerrainType.SWAMP,  # Swamp variation (marsh)
    0x1E: TerrainType.OPEN,  # Open variation (hardstanding)
    0x1F: TerrainType.OPEN,  # Open variation (yard)
}

# Standard CC2 map dimensions used for dimension inference.
# CC2 shipped with specific map sizes; the most common is 40x40.
_CC2_STANDARD_SIZES: list[tuple[int, int]] = [
    (40, 40),
    (36, 36),
    (32, 32),
    (48, 48),
    (44, 44),
    (30, 30),
    (28, 28),
    (24, 24),
]

# Known CC2 map file header signatures.
# CC2 terrain files may start with a small header or be raw byte grids.
_CC2_HEADER_SIGNATURES: dict[bytes, str] = {
    b"CC2M": "cc2_map_v1",
    b"MAPF": "cc2_map_v2",
}


@dataclass(slots=True)
class CC2MapHeader:
    """Parsed header information from a CC2 map file."""

    format_version: str
    width: int
    height: int
    data_offset: int
    byte_order: str  # "little" or "big"
    has_header: bool


@dataclass
class CC2MapData:
    """Fully parsed CC2 map data ready for conversion to PyCC2 format."""

    name: str
    width: int
    height: int
    terrain_grid: list[list[int]]  # PyCC2 TerrainType integer values
    source_path: str = ""
    byte_order: str = "little"
    unmapped_codes: dict[int, int] = field(default_factory=dict)

    def to_pycc2_json(self) -> dict[str, Any]:
        """Convert to PyCC2-compatible JSON map dictionary.

        Returns:
            Dictionary matching the PyCC2 map JSON schema (see data/maps/_schema.json).
        """
        return {
            "id": Path(self.source_path).stem
            if self.source_path
            else self.name.lower().replace(" ", "_"),
            "name": self.name,
            "width": self.width,
            "height": self.height,
            "tiles": self.terrain_grid,
            "objectives": [],
            "spawn_points": [],
        }


class CC2MapParser:
    """Parser for Close Combat 2 native binary map files.

    Handles the CC2 Map### binary format, including:
    - Raw byte grids (no header)
    - Files with CC2M/MAPF headers
    - Both little-endian (PC) and big-endian (Mac) byte orders
    - Automatic dimension inference from file size

    Usage:
        parser = CC2MapParser()
        map_data = parser.parse("Map001")
        json_dict = map_data.to_pycc2_json()
    """

    def __init__(self, default_byte_order: str = "little") -> None:
        """Initialize the parser.

        Args:
            default_byte_order: Default byte order for headerless files.
                "little" for PC, "big" for Mac. Defaults to "little".
        """
        if default_byte_order not in ("little", "big"):
            raise ValueError(f"byte_order must be 'little' or 'big', got {default_byte_order!r}")
        self._default_byte_order = default_byte_order

    def parse(self, filepath: str | Path) -> CC2MapData:
        """Parse a CC2 binary map file.

        Args:
            filepath: Path to the CC2 map file.

        Returns:
            CC2MapData with terrain grid converted to PyCC2 TerrainType values.

        Raises:
            FileNotFoundError: If the map file does not exist.
            ValueError: If the file cannot be parsed as a valid CC2 map.
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"CC2 map file not found: {filepath}")

        raw_bytes = filepath.read_bytes()
        if not raw_bytes:
            raise ValueError(f"CC2 map file is empty: {filepath}")

        header = self._parse_header(raw_bytes)
        terrain_bytes = raw_bytes[header.data_offset :]

        if not terrain_bytes:
            raise ValueError(f"No terrain data after header in: {filepath}")

        width, height = self._resolve_dimensions(header, terrain_bytes)
        expected_size = width * height

        if len(terrain_bytes) < expected_size:
            raise ValueError(
                f"Terrain data too small: expected {expected_size} bytes "
                f"({width}x{height}), got {len(terrain_bytes)} in {filepath}"
            )

        terrain_grid, unmapped = self._convert_terrain(terrain_bytes[:expected_size], width, height)

        return CC2MapData(
            name=filepath.stem,
            width=width,
            height=height,
            terrain_grid=terrain_grid,
            source_path=str(filepath),
            byte_order=header.byte_order,
            unmapped_codes=unmapped,
        )

    def parse_with_dimensions(
        self,
        filepath: str | Path,
        width: int,
        height: int,
    ) -> CC2MapData:
        """Parse a CC2 map file with explicitly provided dimensions.

        Use this when automatic dimension inference fails or when the
        map uses non-standard dimensions.

        Args:
            filepath: Path to the CC2 map file.
            width: Map width in tiles.
            height: Map height in tiles.

        Returns:
            CC2MapData with terrain grid converted to PyCC2 TerrainType values.
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"CC2 map file not found: {filepath}")

        raw_bytes = filepath.read_bytes()
        header = self._parse_header(raw_bytes)
        terrain_bytes = raw_bytes[header.data_offset :]

        expected_size = width * height
        if len(terrain_bytes) < expected_size:
            raise ValueError(
                f"Terrain data too small for {width}x{height}: "
                f"need {expected_size} bytes, got {len(terrain_bytes)}"
            )

        terrain_grid, unmapped = self._convert_terrain(terrain_bytes[:expected_size], width, height)

        return CC2MapData(
            name=filepath.stem,
            width=width,
            height=height,
            terrain_grid=terrain_grid,
            source_path=str(filepath),
            byte_order=header.byte_order,
            unmapped_codes=unmapped,
        )

    def _parse_header(self, raw_bytes: bytes) -> CC2MapHeader:
        """Detect and parse the CC2 map file header.

        CC2 map files may have:
        - No header (raw byte grid)
        - A 4-byte signature header (CC2M or MAPF)
        - A header with embedded dimensions

        Args:
            raw_bytes: Full file contents.

        Returns:
            CC2MapHeader with parsed or inferred header information.
        """
        if len(raw_bytes) < 4:
            # Very small file — treat as headerless
            return CC2MapHeader(
                format_version="raw",
                width=0,
                height=0,
                data_offset=0,
                byte_order=self._default_byte_order,
                has_header=False,
            )

        signature = raw_bytes[:4]

        if signature == b"CC2M":
            return self._parse_cc2m_header(raw_bytes)
        if signature == b"MAPF":
            return self._parse_mapf_header(raw_bytes)

        # No recognized header — assume raw byte grid
        return CC2MapHeader(
            format_version="raw",
            width=0,
            height=0,
            data_offset=0,
            byte_order=self._default_byte_order,
            has_header=False,
        )

    def _parse_cc2m_header(self, raw_bytes: bytes) -> CC2MapHeader:
        """Parse a CC2M-format header.

        CC2M header layout (12 bytes):
            Offset 0-3:   Signature "CC2M"
            Offset 4-5:   Width (uint16)
            Offset 6-7:   Height (uint16)
            Offset 8-11:  Reserved / data offset

        The byte order is detected by checking if width/height values
        are reasonable in little-endian vs big-endian.
        """
        if len(raw_bytes) < 12:
            raise ValueError("CC2M header too short: expected at least 12 bytes")

        # Try little-endian first (PC format)
        width_le = struct.unpack_from("<H", raw_bytes, 4)[0]
        height_le = struct.unpack_from("<H", raw_bytes, 6)[0]

        # Try big-endian (Mac format)
        width_be = struct.unpack_from(">H", raw_bytes, 4)[0]
        height_be = struct.unpack_from(">H", raw_bytes, 6)[0]

        # Determine byte order: prefer the one that gives valid dimensions
        if 4 <= width_le <= 128 and 4 <= height_le <= 128:
            byte_order = "little"
            width, height = width_le, height_le
        elif 4 <= width_be <= 128 and 4 <= height_be <= 128:
            byte_order = "big"
            width, height = width_be, height_be
        else:
            # Neither is valid — default to little-endian and hope for the best
            byte_order = "little"
            width, height = width_le, height_le

        return CC2MapHeader(
            format_version="cc2_map_v1",
            width=width,
            height=height,
            data_offset=12,
            byte_order=byte_order,
            has_header=True,
        )

    def _parse_mapf_header(self, raw_bytes: bytes) -> CC2MapHeader:
        """Parse a MAPF-format header.

        MAPF header layout (16 bytes):
            Offset 0-3:   Signature "MAPF"
            Offset 4-5:   Version (uint16)
            Offset 6-7:   Width (uint16)
            Offset 8-9:   Height (uint16)
            Offset 10-11: Data offset (uint16)
            Offset 12-15: Reserved
        """
        if len(raw_bytes) < 16:
            raise ValueError("MAPF header too short: expected at least 16 bytes")

        # Try little-endian first
        width_le = struct.unpack_from("<H", raw_bytes, 6)[0]
        height_le = struct.unpack_from("<H", raw_bytes, 8)[0]
        offset_le = struct.unpack_from("<H", raw_bytes, 10)[0]

        width_be = struct.unpack_from(">H", raw_bytes, 6)[0]
        height_be = struct.unpack_from(">H", raw_bytes, 8)[0]
        offset_be = struct.unpack_from(">H", raw_bytes, 10)[0]

        if 4 <= width_le <= 128 and 4 <= height_le <= 128:
            byte_order = "little"
            width, height, data_offset = width_le, height_le, offset_le
        elif 4 <= width_be <= 128 and 4 <= height_be <= 128:
            byte_order = "big"
            width, height, data_offset = width_be, height_be, offset_be
        else:
            byte_order = "little"
            width, height, data_offset = width_le, height_le, offset_le

        # Ensure data_offset is at least past the header
        if data_offset < 16:
            data_offset = 16

        return CC2MapHeader(
            format_version="cc2_map_v2",
            width=width,
            height=height,
            data_offset=data_offset,
            byte_order=byte_order,
            has_header=True,
        )

    def _resolve_dimensions(self, header: CC2MapHeader, terrain_bytes: bytes) -> tuple[int, int]:
        """Determine map width and height.

        If the header provides valid dimensions, use those.
        Otherwise, try to infer dimensions from the data size.

        Args:
            header: Parsed header information.
            terrain_bytes: Raw terrain byte data.

        Returns:
            Tuple of (width, height).
        """
        if header.has_header and 4 <= header.width <= 128 and 4 <= header.height <= 128:
            return header.width, header.height

        # Infer dimensions from file size
        data_size = len(terrain_bytes)
        return self._infer_dimensions(data_size)

    def _infer_dimensions(self, data_size: int) -> tuple[int, int]:
        """Infer map dimensions from terrain data size.

        Tries standard CC2 sizes first, then falls back to square root.

        Args:
            data_size: Number of terrain bytes.

        Returns:
            Tuple of (width, height).
        """
        # Check against known CC2 standard sizes
        for w, h in _CC2_STANDARD_SIZES:
            if w * h == data_size:
                return w, h

        # Try square root for square maps
        import math

        side = int(math.isqrt(data_size))
        if side * side == data_size and 4 <= side <= 128:
            return side, side

        # Try common rectangular ratios
        for w in range(8, 65):
            if data_size % w == 0:
                h = data_size // w
                if 8 <= h <= 64:
                    return w, h

        # Last resort: assume square with truncation
        side = int(math.sqrt(data_size))
        side = max(8, min(64, side))
        return side, side

    def _convert_terrain(
        self,
        terrain_bytes: bytes,
        width: int,
        height: int,
    ) -> tuple[list[list[int]], dict[int, int]]:
        """Convert CC2 terrain byte codes to PyCC2 TerrainType integer grid.

        Args:
            terrain_bytes: Raw terrain byte data (one byte per tile).
            width: Map width.
            height: Map height.

        Returns:
            Tuple of (2D list of PyCC2 TerrainType integer values, unmapped codes dict).
        """
        grid: list[list[int]] = []
        unmapped: dict[int, int] = {}
        for row_idx in range(height):
            row_start = row_idx * width
            row: list[int] = []
            for col_idx in range(width):
                cc2_code = terrain_bytes[row_start + col_idx]
                pycc2_terrain = CC2_TO_PYCC2_MAP.get(cc2_code)
                if pycc2_terrain is not None:
                    row.append(pycc2_terrain.value)
                else:
                    # Unknown terrain code — default to OPEN
                    row.append(TerrainType.OPEN.value)
                    unmapped[cc2_code] = unmapped.get(cc2_code, 0) + 1
            grid.append(row)
        return grid, unmapped


def parse_cc2_map(
    filepath: str | Path,
    width: int | None = None,
    height: int | None = None,
    byte_order: str = "little",
) -> CC2MapData:
    """Convenience function to parse a CC2 map file.

    Args:
        filepath: Path to the CC2 map file.
        width: Optional explicit map width. If provided with height,
            overrides automatic dimension detection.
        height: Optional explicit map height.
        byte_order: Default byte order ("little" or "big").

    Returns:
        CC2MapData with terrain grid converted to PyCC2 TerrainType values.
    """
    parser = CC2MapParser(default_byte_order=byte_order)
    if width is not None and height is not None:
        return parser.parse_with_dimensions(filepath, width, height)
    return parser.parse(filepath)
