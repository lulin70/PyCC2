"""
Deployment Factory — Force pool builders and AI deployment generator.

Pure functions with zero dependency on DeploymentUI instance state.
Extracted from deployment_ui.py God Class (v0.3.29 SRP refactoring).
"""

from __future__ import annotations

from pycc2.presentation.ui.deployment_models import DeploymentUnit
from pycc2.presentation.ui.deployment_models import IMPASSABLE_TERRAINS


def build_default_roster() -> list[DeploymentUnit]:
    """Build a default unit roster for demonstration purposes."""
    return [
        # Infantry
        DeploymentUnit("us_rifle_squad", "Rifle Squad", "infantry", 120),
        DeploymentUnit("us_rifle_squad", "Rifle Squad", "infantry", 120),
        DeploymentUnit("us_rifle_squad", "Rifle Squad", "infantry", 120),
        DeploymentUnit("us_assault_squad", "Assault Squad", "infantry", 145),
        DeploymentUnit("us_engineer_team", "Engineer Squad", "infantry", 140),
        # Support (MG/AT)
        DeploymentUnit("us_machine_gun_team", "MG Team (M1919A4)", "support", 160),
        DeploymentUnit("us_at_team", "AT Team (Bazooka)", "support", 150),
        DeploymentUnit("us_mortar_light", "Light Mortar (60mm)", "support", 140),
        DeploymentUnit("us_mortar_heavy", "Heavy Mortar (81mm)", "support", 175),
        DeploymentUnit("us_officer", "Officer / Commander", "support", 180),
        # Armor
        DeploymentUnit("us_sherman_m4", "M4 Sherman", "vehicle", 350),
        DeploymentUnit("us_stuart_m5", "M5 Stuart", "vehicle", 220),
        # Recon
        DeploymentUnit("us_scout_team", "Scout Team", "recon", 110),
        DeploymentUnit("us_sniper_team", "Sniper Team", "recon", 140),
    ]


def build_force_pool_from_settings(
    faction: str = "allied",
    requisition_points: int = 2000,
) -> list[DeploymentUnit]:
    """Build a force pool based on faction and requisition points.

    Returns a list of DeploymentUnit entries that the player can
    choose from during deployment.  The cost of each unit counts
    against the player's requisition point budget.
    """
    if faction in ("allied", "ally"):
        return [
            # Infantry
            DeploymentUnit("us_rifle_squad", "Rifle Squad", "infantry", 120),
            DeploymentUnit("us_rifle_squad", "Rifle Squad", "infantry", 120),
            DeploymentUnit("us_rifle_squad", "Rifle Squad", "infantry", 120),
            DeploymentUnit("us_assault_squad", "Assault Squad", "infantry", 145),
            DeploymentUnit("us_engineer_team", "Engineer Squad", "infantry", 140),
            # Support (MG/AT)
            DeploymentUnit("us_machine_gun_team", "MG Team (M1919A4)", "support", 160),
            DeploymentUnit("us_at_team", "AT Team (Bazooka)", "support", 150),
            DeploymentUnit("us_mortar_light", "Light Mortar (60mm)", "support", 140),
            DeploymentUnit("us_mortar_heavy", "Heavy Mortar (81mm)", "support", 175),
            DeploymentUnit("us_officer", "Officer / Commander", "support", 180),
            # Armor
            DeploymentUnit("us_sherman_m4", "M4 Sherman", "vehicle", 350),
            DeploymentUnit("us_stuart_m5", "M5 Stuart", "vehicle", 220),
            # Recon
            DeploymentUnit("us_scout_team", "Scout Team", "recon", 110),
            DeploymentUnit("us_sniper_team", "Sniper Team", "recon", 140),
        ]
    else:
        return [
            # Infantry
            DeploymentUnit("ger_rifle_squad", "Rifle Squad", "infantry", 120),
            DeploymentUnit("ger_rifle_squad", "Rifle Squad", "infantry", 120),
            DeploymentUnit("ger_rifle_squad", "Rifle Squad", "infantry", 120),
            DeploymentUnit("ger_assault_squad", "Sturm Squad", "infantry", 145),
            DeploymentUnit("ger_pioneer_team", "Pioneer Squad", "infantry", 140),
            # Support (MG/AT)
            DeploymentUnit("ger_mg42_team", "MG42 Team", "support", 170),
            DeploymentUnit("ger_at_team", "AT Team (Panzerschreck)", "support", 155),
            DeploymentUnit("ger_mortar_light", "Light Mortar (50mm)", "support", 130),
            DeploymentUnit("ger_mortar_heavy", "Heavy Mortar (81mm)", "support", 175),
            DeploymentUnit("ger_officer", "Officer / Commander", "support", 180),
            # Armor
            DeploymentUnit("ger_panther", "Panther", "vehicle", 400),
            DeploymentUnit("ger_stug", "StuG III", "vehicle", 280),
            # Recon
            DeploymentUnit("ger_scout_team", "Scout Team", "recon", 110),
            DeploymentUnit("ger_sniper_team", "Sniper Team", "recon", 140),
        ]


def generate_ai_deployment(
    map_data: dict,
    faction: str = "axis",
    requisition_points: int = 1500,
) -> list[dict]:
    """Generate AI deployment placements for the enemy side.

    Returns a list of placement dicts:
      {"unit_template_id": str, "display_name": str,
       "unit_type": str, "position": (x, y)}
    """
    map_width = map_data.get("width", 50)
    map_height = map_data.get("height", 42)
    tile_grid = map_data.get("tiles")

    # Determine enemy zone
    spawn_points = map_data.get("spawn_points", [])
    enemy_positions: list[tuple[int, int]] = []

    side_key = "axis" if faction == "axis" else "allies"

    for sp in spawn_points:
        if sp.get("side") == side_key:
            sp_x, sp_y = sp["position"]
            # Generate positions around the spawn point
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    nx, ny = sp_x + dx, sp_y + dy
                    if 0 <= nx < map_width and 0 <= ny < map_height:
                        # Check terrain is passable
                        if tile_grid is not None:
                            terrain = int(tile_grid[ny][nx])
                            if terrain in IMPASSABLE_TERRAINS:
                                continue
                        enemy_positions.append((nx, ny))

    # If no spawn points, use right third of map
    if not enemy_positions:
        third = map_width // 3
        for y in range(map_height):
            for x in range(map_width - third, map_width):
                if tile_grid is not None:
                    terrain = int(tile_grid[y][x])
                    if terrain not in IMPASSABLE_TERRAINS:
                        enemy_positions.append((x, y))
                else:
                    enemy_positions.append((x, y))

    # Build AI force pool
    if faction in ("axis",):
        ai_units = [
            ("ger_rifle_squad", "Rifle Squad", "infantry", 120),
            ("ger_rifle_squad", "Rifle Squad", "infantry", 120),
            ("ger_rifle_squad", "Rifle Squad", "infantry", 120),
            ("ger_mg42_team", "MG42 Team", "support", 170),
            ("ger_at_team", "AT Team (Panzerschreck)", "support", 155),
            ("ger_mortar_heavy", "Heavy Mortar (81mm)", "support", 175),
            ("ger_officer", "Officer / Commander", "support", 180),
            ("ger_panther", "Panther", "vehicle", 400),
        ]
    else:
        ai_units = [
            ("us_rifle_squad", "Rifle Squad", "infantry", 120),
            ("us_rifle_squad", "Rifle Squad", "infantry", 120),
            ("us_rifle_squad", "Rifle Squad", "infantry", 120),
            ("us_machine_gun_team", "MG Team (M1919A4)", "support", 160),
            ("us_at_team", "AT Team (Bazooka)", "support", 150),
            ("us_mortar_heavy", "Heavy Mortar (81mm)", "support", 175),
            ("us_officer", "Officer / Commander", "support", 180),
            ("us_sherman_m4", "M4 Sherman", "vehicle", 350),
        ]

    # Place AI units within budget
    placements: list[dict] = []
    spent = 0
    used_positions: set[tuple[int, int]] = set()

    for template_id, name, utype, cost in ai_units:
        if spent + cost > requisition_points:
            continue
        # Find a free position
        for pos in enemy_positions:
            if pos not in used_positions:
                used_positions.add(pos)
                placements.append({
                    "unit_template_id": template_id,
                    "display_name": name,
                    "unit_type": utype,
                    "position": pos,
                })
                spent += cost
                break

    return placements
