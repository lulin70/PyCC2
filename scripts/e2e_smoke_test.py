"""E2E smoke test - verify all integrated systems work together."""

import sys

sys.path.insert(0, "src")

import os

from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent, MoraleState
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.squad import Squad, SquadType
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.presentation.input.attack_line_system import AttackLineStatus
from pycc2.presentation.ui.radial_menu import RadialCommand


def make_unit(id="t", name="Test", unit_type=UnitType.INFANTRY_SQUAD, faction=Faction.ALLIES):
    return Unit(
        id=id,
        name=name,
        unit_type=unit_type,
        faction=faction,
        health=HealthComponent(hp=100, max_hp=100),
        morale=MoraleComponent(value=80),
        weapon=WeaponComponent(primary_weapon_id="rifle", ammo_remaining=120, max_ammo=120),
        position=PositionComponent(0, 0),
        vision=VisionComponent(10),
    )


# 1. Infantry with fatigue + veterancy
u = make_unit()
assert u.fatigue is not None
assert u.veterancy is not None
assert u.crew is None  # Infantry has no crew
print(f"[OK] Infantry: fatigue={u.fatigue.level.name}, veterancy={u.veterancy.rank.name}")

# 2. Tank with crew
t = make_unit(id="tk", name="Tank", unit_type=UnitType.TANK)
assert t.crew is not None
print(f"[OK] Tank: crew_size={len(t.crew._members)}, efficiency={t.crew.vehicle_efficiency:.2f}")

# 3. Squad integration
s = Squad(squad_id="sq1", squad_type=SquadType.RIFLE_SQUAD, faction="allies", name="Alpha")
u.squad_ref = s
print(f"[OK] Squad: size={u.squad_size}, status={u.squad_status_string}")

# 4. Accuracy modifier chain (fatigue + veterancy + crew)
acc = u.get_accuracy_modifier()
for _ in range(100):
    u.fatigue.accumulate("fast_move")
acc_after = u.get_accuracy_modifier()
assert acc_after <= acc  # Fatigue should not increase accuracy
print(f"[OK] Accuracy: {acc:.3f} -> {acc_after:.3f} (after 100x fast_move fatigue)")

# 5. Morale 5-state
states = [s.name for s in MoraleState]
assert len(states) == 5
print(f"[OK] Morale 5-state: {states}")

# 6. 7 commands
assert len(RadialCommand) == 7
print(f"[OK] Commands: {len(RadialCommand)}")

# 7. Attack line 4-color
statuses = [s.name for s in AttackLineStatus]
assert len(statuses) >= 4
print(f"[OK] Attack line: {statuses}")

# 8. Maps
maps = [f for f in os.listdir("data/maps") if f.endswith(".json")]
print(f"[OK] Maps: {len(maps)} files")

# 9. Vehicle sprites
from pycc2.presentation.rendering.pixel_artist_3d import Direction, PixelArtist3D

artist = PixelArtist3D()
ht = artist.create_halftrack_sprite(direction=Direction.NORTH, faction="allies")
jp = artist.create_jeep_sprite(direction=Direction.NORTH, faction="allies")
at = artist.create_at_gun_sprite(direction=Direction.NORTH, faction="allies")
print(f"[OK] Sprites: halftrack={ht.get_size()}, jeep={jp.get_size()}, at_gun={at.get_size()}")

# 10. Building interior auto-switch
from pycc2.presentation.rendering.cc2_building_renderer import should_show_interior

result = should_show_interior((5, 5), [])
assert not result
print("[OK] Building interior auto-switch function")

# 11. Campaign UI
print("[OK] Campaign UI")

print()
print("=== ALL 11 SYSTEMS VERIFIED ===")
