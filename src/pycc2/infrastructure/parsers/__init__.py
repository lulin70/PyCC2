"""CC2 Native Map Format Parsers.

Provides parsers for Close Combat 2 native binary map files,
converting CC2 terrain codes to PyCC2 TerrainType values.
"""

from __future__ import annotations

from pycc2.infrastructure.parsers.cc2_map_parser import (
    CC2MapParser,
    CC2TerrainCode,
    parse_cc2_map,
)

__all__ = [
    "CC2MapParser",
    "CC2TerrainCode",
    "parse_cc2_map",
]
