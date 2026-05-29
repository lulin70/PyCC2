#!/usr/bin/env python3
"""Quick debug script for E2E deployment issue."""
import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame
pygame.init()
screen = pygame.display.set_mode((800, 600))

import sys
sys.path.insert(0, 'tests/e2e')
from test_e2e_full_coverage import _GameLoopFactory

f = _GameLoopFactory(screen)
dui = f.start_deployment()

print('=== Deployment Debug ===')
print(f'Phase: {dui._state.phase}')
print(f'Friendly zone size: {len(dui.state.friendly_zone)}')
print(f'Available units: {len(dui.state.available_units)}')
print(f'RP remaining: {dui.requisition_remaining}')
print()

for i, unit in enumerate(dui.state.available_units[:5]):
    print(f'Unit[{i}]: {unit.display_name} ({unit.unit_type}) cost={unit.deployment_cost} placed={unit.is_placed}')

print()
print('Checking first 30 friendly zone tiles:')
for idx, (tx, ty) in enumerate(dui.state.friendly_zone[:30]):
    terrain = dui._get_terrain_at(tx, ty)
    can_place = dui.can_place_at(dui.state.available_units[0], tx, ty, terrain)
    print(f'  [{idx}] ({tx},{ty}): terrain={terrain}, can_place={can_place}')

print()
print('Trying to select first unit via click:')
r = dui.handle_click_full(50, 46, 0, 0, 16)
print(f'  Result: {r}')
print(f'  Selected index: {dui._selected_unit_index}')

if dui._selected_unit_index is not None:
    print()
    print('Trying to place selected unit:')
    for idx, (tx, ty) in enumerate(dui.state.friendly_zone[:20]):
        if dui.can_place_at(dui.state.available_units[dui._selected_unit_index], tx, ty, dui._get_terrain_at(tx, ty)):
            sx = dui._roster_width + tx * 16
            sy = ty * 16
            r2 = dui.handle_click_full(sx, sy, 0, 0, 16)
            print(f'  [{idx}] ({tx},{ty})→screen({sx},{sy}): {r2}')
            if r2 and 'place_unit' in str(r2):
                print('  ✅ PLACED SUCCESSFULLY!')
                break
    else:
        print('  ❌ Could not place in first 20 zone tiles')

f.shutdown()
pygame.quit()
