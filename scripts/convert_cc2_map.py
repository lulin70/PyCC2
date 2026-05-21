#!/usr/bin/env python3
"""CC2 Map Converter — Convert CC2 native map files to PyCC2 JSON format.

Reads a Close Combat 2 binary map file (Map### format), parses the terrain
data, and outputs a PyCC2-compatible JSON map file.

Usage:
    # Basic conversion
    python convert_cc2_map.py /path/to/Map001

    # Specify explicit dimensions
    python convert_cc2_map.py /path/to/Map001 --width 40 --height 40

    # Mac byte order
    python convert_cc2_map.py /path/to/Map001 --byte-order big

    # Interactive mode (add Victory Locations and spawn points)
    python convert_cc2_map.py /path/to/Map001 --interactive

    # Specify output path
    python convert_cc2_map.py /path/to/Map001 -o /path/to/output.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running as a script without the package installed.
try:
    from pycc2.domain.value_objects.terrain_type import TerrainType
    from pycc2.infrastructure.parsers.cc2_map_parser import parse_cc2_map
except ImportError:
    _src = Path(__file__).resolve().parent.parent / "src"
    if str(_src) not in sys.path:
        sys.path.insert(0, str(_src))
    from pycc2.domain.value_objects.terrain_type import TerrainType
    from pycc2.infrastructure.parsers.cc2_map_parser import parse_cc2_map


def _terrain_summary(grid: list[list[int]]) -> dict[str, int]:
    """Count occurrences of each terrain type in the grid."""
    counts: dict[str, int] = {}
    for row in grid:
        for val in row:
            try:
                name = TerrainType(val).display_name
            except ValueError:
                name = f"Unknown({val})"
            counts[name] = counts.get(name, 0) + 1
    return counts


def _interactive_add_objectives(map_data: dict) -> dict:
    """Interactively add Victory Locations to the map."""
    print("\n=== Add Victory Locations ===")
    print("Enter objective positions as 'x,y' (or 'done' to finish)")
    print(f"Map dimensions: {map_data['width']}x{map_data['height']}")

    objectives = map_data.get("objectives", [])
    idx = len(objectives) + 1

    while True:
        raw = input(f"  Objective #{idx} position (x,y) or 'done': ").strip()
        if raw.lower() in ("done", "d", ""):
            break

        try:
            parts = raw.split(",")
            if len(parts) != 2:
                print("    Invalid format. Use 'x,y'")
                continue
            x, y = int(parts[0].strip()), int(parts[1].strip())
            if not (0 <= x < map_data["width"] and 0 <= y < map_data["height"]):
                print(f"    Position out of bounds (0-{map_data['width']-1}, 0-{map_data['height']-1})")
                continue
        except (ValueError, IndexError):
            print("    Invalid input. Use integer coordinates 'x,y'")
            continue

        name = input(f"  Objective #{idx} name [Victory Location {idx}]: ").strip()
        if not name:
            name = f"Victory Location {idx}"

        obj_type = input(f"  Objective #{idx} type (capture/defend/reach) [capture]: ").strip()
        if obj_type not in ("capture", "defend", "reach"):
            obj_type = "capture"

        required = input("  Required? (y/n) [y]: ").strip().lower()
        is_required = required != "n"

        objectives.append({
            "id": f"vl_{idx}",
            "name": name,
            "position": [x, y],
            "radius": 2,
            "required": is_required,
        })
        idx += 1

    map_data["objectives"] = objectives
    return map_data


def _interactive_add_spawns(map_data: dict) -> dict:
    """Interactively add spawn points to the map."""
    print("\n=== Add Spawn Points ===")
    print("Enter spawn positions as 'x,y' (or 'done' to finish)")
    print(f"Map dimensions: {map_data['width']}x{map_data['height']}")

    spawn_points = map_data.get("spawn_points", [])

    for side in ("allies", "axis"):
        raw = input(f"  {side.capitalize()} spawn position (x,y) or 'skip': ").strip()
        if raw.lower() in ("skip", "s", ""):
            continue

        try:
            parts = raw.split(",")
            if len(parts) != 2:
                print("    Invalid format. Use 'x,y'")
                continue
            x, y = int(parts[0].strip()), int(parts[1].strip())
            if not (0 <= x < map_data["width"] and 0 <= y < map_data["height"]):
                print("    Position out of bounds")
                continue
        except (ValueError, IndexError):
            print("    Invalid input. Skipping.")
            continue

        max_units = input(f"  Max units for {side} [6]: ").strip()
        try:
            units_max = int(max_units) if max_units else 6
        except ValueError:
            units_max = 6

        spawn_points.append({
            "id": f"spawn_{side}",
            "side": side,
            "position": [x, y],
            "units_max": units_max,
        })

    map_data["spawn_points"] = spawn_points
    return map_data


def main() -> None:
    """Main entry point for the CC2 map converter."""
    parser = argparse.ArgumentParser(
        description="Convert CC2 native map files to PyCC2 JSON format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "input",
        type=str,
        help="Path to the CC2 map file (e.g. Map001)",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output JSON file path (default: <input_stem>.json in current directory)",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=None,
        help="Explicit map width (overrides auto-detection)",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=None,
        help="Explicit map height (overrides auto-detection)",
    )
    parser.add_argument(
        "--byte-order",
        choices=["little", "big"],
        default="little",
        help="Byte order for header parsing: 'little' (PC) or 'big' (Mac). Default: little",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Interactively add Victory Locations and spawn points",
    )
    parser.add_argument(
        "--name",
        type=str,
        default=None,
        help="Display name for the map (default: derived from filename)",
    )
    parser.add_argument(
        "--id",
        type=str,
        default=None,
        dest="map_id",
        help="Map ID (default: derived from filename)",
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    # Parse the CC2 map
    print(f"Parsing CC2 map: {input_path}")
    try:
        if args.width is not None and args.height is not None:
            map_data = parse_cc2_map(
                input_path,
                width=args.width,
                height=args.height,
                byte_order=args.byte_order,
            )
        else:
            map_data = parse_cc2_map(
                input_path,
                byte_order=args.byte_order,
            )
    except (ValueError, FileNotFoundError) as e:
        print(f"Error parsing map: {e}", file=sys.stderr)
        sys.exit(1)

    # Convert to JSON dict
    json_dict = map_data.to_pycc2_json()

    # Override name/id if provided
    if args.name:
        json_dict["name"] = args.name
    if args.map_id:
        json_dict["id"] = args.map_id

    # Report parsing results
    print(f"  Dimensions: {map_data.width}x{map_data.height}")
    print(f"  Byte order: {map_data.byte_order}")
    print(f"  Total tiles: {map_data.width * map_data.height}")

    if map_data.unmapped_codes:
        print("  Warning: Unmapped terrain codes found:")
        for code, count in sorted(map_data.unmapped_codes.items()):
            print(f"    Code 0x{code:02X}: {count} tiles (mapped to OPEN)")

    # Terrain summary
    summary = _terrain_summary(map_data.terrain_grid)
    print("\n  Terrain distribution:")
    for name, count in sorted(summary.items(), key=lambda x: -x[1]):
        pct = count / (map_data.width * map_data.height) * 100
        print(f"    {name:25s}: {count:5d} ({pct:5.1f}%)")

    # Interactive mode
    if args.interactive:
        json_dict = _interactive_add_objectives(json_dict)
        json_dict = _interactive_add_spawns(json_dict)

    # Determine output path
    output_path = Path(args.output) if args.output else Path(f"{input_path.stem}.json")

    # Write JSON
    output_path.write_text(json.dumps(json_dict, indent=2), encoding="utf-8")
    print(f"\nOutput written to: {output_path}")
    print(f"  Map ID: {json_dict['id']}")
    print(f"  Map name: {json_dict['name']}")
    print(f"  Objectives: {len(json_dict.get('objectives', []))}")
    print(f"  Spawn points: {len(json_dict.get('spawn_points', []))}")


if __name__ == "__main__":
    main()
