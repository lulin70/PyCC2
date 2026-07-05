# PyCC2 User Guide

**v0.4.3 | Beta Candidate — Fully Playable | July 5, 2026**

> 🎮 **Game Status**: Beta Candidate — AI対戦可用、コア玩法完整！
> This guide covers the current v0.4.3 features based on runtime verification.

---

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [Game Interface](#2-game-interface)
3. [Deployment Phase](#3-deployment-phase)
4. [Combat Commands](#4-combat-commands)
5. [Combat Mechanics](#5-combat-mechanics)
6. [Campaign System](#6-campaign-system)
7. [Tactical Tips](#7-tactical-tips)
8. [Known Issues](#8-known-issues)

---

## 1. Getting Started

### Installation

```bash
git clone https://github.com/lulin70/PyCC2.git
cd PyCC2
python -m venv .venv
source .venv/bin/activate   # macOS/Linux
pip install -e .
```

### Launching the Game

```bash
pycc2
```

### New Game Setup

When starting a new campaign, you'll set **experience level** and **supply level** for **both factions**. This is CC2's classic asymmetric design:

#### 5 Difficulty Presets

| Preset | Allied XP | Allied Supply | Axis XP | Axis Supply | For |
|--------|-----------|---------------|---------|-------------|-----|
| **Recruit** | Veteran | Abundant | Recruit | Depleted | First-time players |
| **Easy** | Regular | Adequate | Recruit | Depleted | Some tactical game experience |
| **Normal** | Regular | Adequate | Regular | Adequate | Fair fight seekers |
| **Hard** | Regular | Depleted | Veteran | Adequate | Experienced CC2 players |
| **Veteran** | Recruit | Critical | Elite | Abundant | Hardcore challenge seekers |

#### Experience Level Effects

| Level | Hit Modifier | Morale Resistance | Panic Threshold | Reaction Speed | Initial XP | Suppression Recovery |
|-------|--------------|-------------------|-----------------|---------------|------------|----------------------|
| Recruit | ×0.75 | ×0.70 | ×1.30 | ×0.80 | 0 | ×0.70 |
| Regular | ×1.00 | ×1.00 | ×1.00 | ×1.00 | 100 | ×1.00 |
| Veteran | ×1.15 | ×1.20 | ×0.80 | ×1.10 | 300 | ×1.20 |
| Elite | ×1.25 | ×1.40 | ×0.60 | ×1.20 | 600 | ×1.40 |
| Crack | ×1.35 | ×1.60 | ×0.45 | ×1.30 | 1000 | ×1.60 |

#### Supply Level Effects

| Level | Ammo Resupply | Reinforce Rate | Morale Recovery | Purchase Points | Initial Ammo |
|-------|---------------|----------------|-----------------|-----------------|--------------|
| Abundant | ×1.00 | ×1.00 | ×0.80 | ×1.20 | ×1.00 |
| Adequate | ×0.75 | ×0.80 | ×0.60 | ×1.00 | ×0.90 |
| Depleted | ×0.50 | ×0.50 | ×0.40 | ×0.80 | ×0.75 |
| Critical | ×0.25 | ×0.20 | ×0.15 | ×0.50 | ×0.50 |

---

## 2. Game Interface

### Main Menu ✅ Working

Options available:
- **New Campaign** — Start Operation Market Garden full campaign
- **Quick Battle** — Select map and forces for single battle
- **Tutorial** — Interactive new player guidance
- **Settings** — Graphics, Audio, Game, Controls tabs
- **Exit**

### Combat Screen Layout

```
┌──────────────────────────────────────────────────────────┐
│ [FPS:60] Time:05:30  Battle:3  [Pause]                  │ ← Top status bar
├──────────────────────────────────────────────────────────┤
│                                                          │
│    🟢🟢🟢     ← Your units (Allied - green)              │
│                                                          │
│          🏠🏠                                          │
│          🏠🏠     ← Buildings (enterable for cover)      │
│                                                          │
│                🔴🔴  ← Enemy units (Axis - red)          │
│                                                          │
│  [Minimap]                           [Command Bar]       │
│  ██████░░    [Move][Fast][Sneak][Fire][Smoke]            │
│              [Defend][Hide][Cancel]                      │
└──────────────────────────────────────────────────────────┘
```

### HUD Elements

| Element | Location | Description |
|---------|----------|-------------|
| **Health Bar** | Bottom panel | Unit HP (green→yellow→red) |
| **Morale Bar** | Bottom panel | Unit morale state |
| **Ammo Indicator** | Bottom panel | Remaining ammunition % |
| **Minimap** | Bottom-right | Tactical overview with terrain detail (roads, buildings, water, woods) — real Minimap component since v0.3.31 |
| **Command Bar** | Bottom-center | Quick command buttons with hover/click feedback + tooltips (v0.3.33) |
| **FPS Counter** | Top-left | Performance monitoring |
| **Battle Timer** | Top-center | 20-minute countdown |
| **Unit Info Panel** | Selected unit | Name, health, morale, ammo, status |
| **Weather Overlay** | Full screen | Atmospheric haze (light_fog default since v0.3.34), 4 modes: clear/light_fog/dust/smoke |
| **Theme** | Settings | Default/Dark/Light themes available at runtime (v0.3.36) |

---

## 3. Deployment Phase

Before each battle, you deploy your forces in designated zones.

### How to Deploy

1. Select unit from force pool (left panel or list)
2. Click within your deployment zone (blue area)
3. Adjust facing direction (affects initial LOS)
4. Confirm deployment to start battle

### Deployment Zones

| Zone | Description |
|------|-------------|
| **Friendly Zone** (Blue) | Your starting area, free deployment |
| **No-Man's Land** (Yellow) | Middle ground, either side can deploy (risky) |
| **Enemy Zone** (Red) | Enemy starting area, cannot deploy here |

### Deployment LOS Preview

✅ **Working in v0.4.0**: Before placing a unit, hold Ctrl to preview its line-of-sight. This helps you position units with good fields of fire.

### Force Limits

| Unit Type | Max Count | Notes |
|-----------|-----------|-------|
| Infantry units | 9 | Rifle squads, sniper teams, medics, etc. |
| Support units | 6 | MG teams, AT guns, mortars, tanks, etc. |

Forces are limited by **purchase points** — each unit costs points, build your optimal task force within the budget.

---

## 4. Combat Commands

### The 7 CC2 Commands ✅ All Working

| Command | Hotkey | Effect | When to Use |
|---------|--------|--------|-------------|
| **Move Fast** | Z | Run quickly, but fatigue ↑↑, accuracy ↓↓ | Urgent repositioning, crossing open ground |
| **Sneak** | X | Move slowly, high stealth, hard to detect | Reconnaissance, flanking approaches |
| **Fire** | S | Attack target, sustained until canceled | Engaging enemies in good position |
| **Smoke** | C | Throw smoke grenade (radius ~3 tiles, ~30 sec) | Covering movement, blocking enemy LOS |
| **Move** | V | Normal speed movement, maintains awareness | Standard tactical movement |
| **Defend** | D | Defensive stance, accuracy ↑, cannot move | Holding position, ambush preparation |
| **Hide** | H | Concealed state, very low detection probability | Ambushes, avoiding detection |

### Command Execution Methods

| Method | Input | Notes |
|--------|-------|-------|
| **Radial Menu** | Right-click drag on terrain | Shows pie menu with all commands |
| **Hotkey + Click** | Press hotkey, then click destination | Faster for experienced players |
| **Hotkey + Enemy** | Press hotkey, then click enemy | Issues attack/move command directly |

### Command Queue ✅ Working

**How to queue commands**: Hold **Shift** + Right-click multiple locations

Example: Shift+Right-click point A → Shift+Right-click point B → Shift+Right-click enemy C

The unit will execute commands in sequence: Move to A → Move to B → Attack C

⚠️ **Note**: Visual waypoint display is pending (M3 polish item). The queue works correctly, but you won't see numbered waypoints on screen yet.

---

## 5. Combat Mechanics

### Suppression System (6 Levels) ✅ Complete

Suppression is THE core combat mechanic. Sustained fire gradually reduces enemy effectiveness:

| Level | Effect | Visual Indicator |
|-------|--------|------------------|
| **None** | Normal operations | No indicator |
| **Light** | Accuracy -15%, slight speed reduction | Slight screen shake |
| **Medium** | Accuracy -35%, cannot run, only crawl | Medium shake |
| **Heavy** | Accuracy -60%, cannot move, only return fire | Heavy shake |
| **Pinned** | Cannot return fire, soldiers huddled | Red overlay |
| **Fully Suppressed** | Complete combat ineffective, morale collapses rapidly | Dark red overlay |

**Suppression sources**: MG sustained fire, artillery, concentrated rifle fire

**Recovery**: Gradual after stopping fire; higher experience = faster recovery

### Morale & Psychology Model ✅ Complete

Based on Dr. Steven Silver's military psychology model. Each unit has independent morale (0-100):

| Range | State | Combat Effects |
|-------|-------|----------------|
| 86-100 | **Elated** | Full bonuses, soldiers actively seek engagement |
| 51-85 | **Normal** | Standard operating parameters |
| 31-50 | **Shaken** | Accuracy reduced, may hesitate on orders |
| 11-30 | **Panicked** | Severe penalties, may refuse orders, rout |
| 0-10 | **Broken** | Completely out of control, unit routs or surrenders |

**Morale decrease factors**:
- 🔴 **Friendly KIA nearby** — Biggest impact (especially if close)
- 🔴 **Leader/NCO killed — Whole sector major penalty**
- 🟡 **Continuous suppression** — Gradual decline
- 🟡 **Flank exposed** — Penalty when attacked from side/rear
- 🟡 **Isolated** — No friendly units nearby

**Morale recovery factors**:
- ✅ Not taking fire — Slow recovery
- ✅ Friendly units nearby — Proximity bonus
- ✅ Leader alive and in sight — Significant bonus
- ✅ NCO Rally — Sergeants can rally panicked troops

### Fatigue System ✅ Complete

Extended combat accumulates fatigue:
- **Accuracy decreases** — Tired troops shoot less accurately
- **Movement slower** — Fatigued units are sluggish
- **Morale recovery slower** — Exhausted soldiers harder to motivate
- **Sources**: Fast movement, continuous combat, no rest periods

### Weapon Jamming ✅ Complete

Historical weapon reliability simulation:

| Weapon Type | Jam Probability | Clear Time | Notes |
|-------------|----------------|------------|-------|
| Rifle | 0.1% | 3 ticks | Very reliable |
| SMG (Sten) | **1.5%** | 5 ticks | Historically problematic! |
| Machine Gun | 0.3% | 8 ticks | Moderate |
| Pistol | 0.5% | 3 ticks | Low |
| AT Weapon | 0.8% | 6 ticks | Moderate |
| **Captured Weapon** | **+1% extra** | **+50% time** | Unknown maintenance, foreign parts |

During jam: unit cannot shoot or fast-move.

> ⚠️ **Historical Note**: The Sten gun's 1.5% jam rate caused serious problems for British paratroopers at Arnhem.

### Ammo Pickup & Scavenging ✅ Complete

When low on ammo, search the battlefield:

| Source | Range | What You Get | Caveats |
|--------|-------|-------------|---------|
| Friendly corpse | 5 tiles | 50% ammo transfer | Same weapon type preferred |
| Enemy corpse | 3 tiles | Full weapon + ammo | Captured weapon: -20% accuracy, +50% reload time |

**Pickup requirements**:
- Unit must be prone or crouching
- Not under medium+ suppression
- Takes 2 ticks (vulnerable during pickup)
- Corpses disappear after 300 ticks

### Surrender System ✅ Complete

Units surrender under specific conditions (common at Arnhem):

**Requirements (all must be true)**:
- Ammo < 5% (almost empty)
- Morale < 15 (near broken)
- No friendlies within 8 tiles (isolated)
- Enemies within 5 tiles (threat imminent)

**Probability modifiers**:
- Surrounded (2+ enemy directions): +10%
- Leader dead: +15%
- Veteran/Elite experience: -10%
- Each nearby friendly: -5%

After surrender: unit becomes non-combatant, weapons/ammo drop for scavenging.

---

## 6. Campaign System

### Four-Layer Campaign Structure ✅ Complete

```
Grand Campaign (Operation Market Garden, Sep 17-26, 1944)
  └─ Sector Campaign    Arnhem / Nijmegen / Eindhoven
       └─ Operation      2-5 battles in series
            └─ Battle      Single engagement
```

### How Battles Connect

Each battle result affects subsequent battles:
- **Victory** → More purchase points, advance front line
- **Defeat** → Fewer purchase points, may be forced to retreat
- **Draw** → Both sides attrition, situation unchanged

### Supply Lines ✅ Complete

Supply is THE critical Market Garden mechanic:

| Supply Type | Source | Effect |
|-------------|--------|--------|
| **Land Supply** | XXX Corps advance / German roads-rails | 100% ammo, reinforcements, morale recovery |
| **Air Drop** | Allied drop zones (must control LZ) | 50-100% (depends on LZ control) |
| **Supply Cut** | LZ captured / surrounded | 0% — Out of ammo, morale collapse |

**Key Rules**:
- Germans always have land supply (road/rail connection)
- Allied airborne depend on air drops — if Germans take the LZ, air drops stop
- When XXX Corps arrives, that zone switches to land supply
- Each day, choose which sector gets priority resupply

### Unit Veterans & Experience ✅ Complete

Units gain experience in combat and improve over time:

| Rank | XP Required | Effects |
|------|-------------|---------|
| Recruit | 0 | Base stats |
| Regular | 100 | Standard performance |
| Veteran | 300 | Hit +15%, Morale resist +20% |
| Elite | 600 | Hit +25%, Morale resist +40% |
| Crack | 1000 | Hit +35%, Morale resist +60% |

**Critical**: Veterans persist across campaign battles. Dead = everything lost. Protect your veterans!

### Building Garrison ✅ Complete

Units can enter buildings for defensive advantages:
- **Defense bonus**: Harder to hit when inside
- **Window firing arcs**: Can only shoot through windows (limited arc)
- **Cover from some directions**: Walls block incoming fire

**Engineers can demolish bridges** ✅: Creates impassable water gaps, cutting off enemy routes.

---

## 7. Tactical Tips

### Golden Rules

#### 🚫 NEVER Stay in Open Ground

Open ground is a graveyard for infantry. Use **bound-and-overwatch**:
- Move from one cover to next in 3-5 second bursts
- Never expose more than 1-2 seconds in open terrain

#### 🔥 Smoke is Your Life Line

Smoke grenades can:
- Cover infantry moving across dangerous open areas
- Shield tanks passing through AT fire zones
- Cover retreat operations
- Block enemy sniper sightlines

Smoke lasts ~30 seconds, radius ~3 tiles, drifts with wind. **Always smoke before moving in open.**

#### 🎖️ Protect Your Leaders & NCOs

Leader/NCO death causes:
- Permanent 30-50% combat effectiveness loss for their squad
- Major morale penalty for nearby units
- Loss of NCO rally ability (panicked troops can't be rallied)

Keep leaders in rear, focus on commanding not shooting.

#### 🔄 Flank Whenever Possible

Frontal assault on prepared positions is suicide. Use flanking:
- MG team pins frontally (the anvil)
- Infantry maneuvers around flank (the hammer)
- Two-pronged attack → enemy breaks

#### 💎 Conserve Ammunition

Ammo isn't infinite. Supply lines may be cut:
- Don't waste ammo on low-probability targets
- MG suppression more efficient than precision rifle fire
- Scavenge battlefield for ammo
- Captured weapons have lower accuracy but better than nothing

### Advanced Tactics

#### Hammer & Anvil

```
        [Enemy Position]
             ↑
     [MG Team] ← Anvil (frontal suppression)
    /
[Infantry] ← Hammer (flank maneuver)
```

1. MG team sets up, begins suppression fire
2. Enemy pinned down, can't move or return effective fire
3. Infantry flanks to side/rear
4. Infantry initiates assault from flank
5. Enemy caught in crossfire, morale collapses

#### Anti-Tank Ambush

AT units use Hide (H) command:
- AT unit conceals itself, won't reveal early
- Auto-fires when enemy tank enters effective range
- First shot has highest accuracy (enemy unaware)
- After firing, consider relocating (AI prioritizes exposed AT positions)

#### Infantry-Tank Cooperation

Never send tanks alone:
- Infantry ahead, reconning and protecting flanks
- Tanks advance along roads (reduce side exposure)
- Infantry intercepts AT teams
- Tanks provide fire support for infantry

#### Reconnaissance-Fire Team

1. Sniper team deployed forward in concealed position, silent observation
2. Observer marks high-value targets (MG gunner, AT soldier, leader)
3. Sniper eliminates marked targets one by one
4. Enemy firepower weakened, main force advances to clear

### Defensive Principles

- **Crossfire**: Two firing positions with overlapping sectors of fire
- **Defense in Depth**: Multiple successive fallback lines
- **Ambush Positions**: AT units hidden along likely enemy routes
- **Reserve Force**: Never commit all units to front line, keep 1-2 in reserve

---

## 8. New Features in v0.3.31+

### Visual Enhancements (v0.3.31-v0.3.34)

| Feature | Version | Description |
|---------|---------|-------------|
| **Desaturation Effect** | v0.3.31 | CC2-style grayscale war atmosphere — pixel-level color grading for authentic dark wartime feel |
| **Infantry 8-Direction Visuals** | v0.3.31 | Enhanced visual variety (~80%+) for infantry sprites across all 8 facing directions |
| **Minimap Terrain Detail** | v0.3.31 | Roads, buildings, water, and woods now rendered with distinct visual styles on the minimap |
| **Real Minimap Component** | v0.3.31 | Replaced text placeholder with actual interactive minimap in HUD |
| **Death Fade-Out** | v0.3.32 | Fallen units fade out over 500ms with CC2 dark-gray ghost rendering |
| **Screen Flash** | v0.3.32 | Warm white flash on explosions, soft red flash on kill shots |
| **Movement Smoothing** | v0.3.32 | Units move smoothly at 12 units/second instead of teleporting between tiles |
| **UI Panel Transitions** | v0.3.32 | FadeTransition animations (0.18-0.2s) on BottomPanel, Minimap, and HUD |
| **Combat Particles** | v0.3.32 | Enriched particle effects: dirt_splash, blood_pool, hit_marker (5 types per hit) |
| **Weather Overlay** | v0.3.33-v0.3.34 | 4 weather modes (clear/light_fog/dust/smoke) with animated particle drift; defaults to light_fog |
| **Shell Casing Ejection** | v0.3.33 | Brass casings with trajectory, gravity, bounce, and fade-out physics |
| **Button Feedback** | v0.3.33 | Hover/click feedback and tooltip system for all command buttons |
| **Post-Processing** | v0.3.34 | Desaturation and vignette effects now active (were never instantiated before) |

### System Enhancements (v0.3.35-v0.4.0)

| Feature | Version | Description |
|---------|---------|-------------|
| **Theme Switching** | v0.3.36 | Default/Dark/Light themes available at runtime via settings |
| **Environmental Audio** | v0.3.37 | 11 procedurally-generated ambient sounds synced to game state |
| **Dirty Rectangle Optimization** | v0.3.37 | Partial screen updates for improved rendering performance |
| **Resource Cache Manager** | v0.3.37 | HTTP download manager with SHA256 verification, LRU cache, offline mode |
| **Save System Hardening** | v0.3.35 | File permissions locked to 0o600, HMAC key minimum length validation |

---

## 9. Known Issues

Based on v0.4.0 runtime verification (June 13, 2026).

### P1 — Polish (Degrades Experience)

| # | Issue | Impact | Workaround |
|---|-------|--------|------------|
| 1 | Command queue has no visual waypoint display | Don't know queued commands at a glance | Remember what you queued; check unit pathing |
| 2 | Vehicle damage lacks visual feedback | Can't see if vehicle is damaged/smoking | Check unit info panel for HP status |
| 3 | Smoke particle effects basic | Doesn't look as good as CC2 original | Mechanics work (blocks LOS), just visuals need polish |

### P2 — Minor (Nice to Have)

| # | Issue | Impact | Workaround |
|---|-------|--------|------------|
| 4 | Save/Load UI not fully integrated | Must use keyboard shortcuts | Backend works, UI buttons coming in M3 |
| 5 | Some weapon volumes inconsistent | Occasional loud/quiet sounds | Adjust in Settings > Audio |
| 6 | Rare crash on rapid clicking during AI turn | Game may close unexpectedly | Avoid spam-clicking during AI turns |

### What's NOT Broken (for reference)

These were all fixed in M1/M2:
- ~~HUD crashing on unit select~~ ✅ Fixed
- ~~AI doing nothing~~ ✅ Fixed  
- ~~Only 3/7 commands working~~ ✅ Fixed (all 7 working)
- ~~Units showing as colored shapes~~ ✅ Fixed (sprites rendering)
- ~~No victory conditions~~ ✅ Fixed (CC2 triple system)

---

## Appendix: Keyboard Shortcuts Reference

| Action | Shortcut | Context |
|--------|----------|---------|
| **Select Unit** | Left Click | Always |
| **Issue Command** | Right Click (drag) or Hotkey | In combat |
| **Multi-Select** | Shift + Left Click | In combat |
| **Queue Commands** | Shift + Right Click | In combat |
| **Move Fast** | Z | Unit selected |
| **Sneak** | X | Unit selected |
| **Fire** | S | Unit selected + enemy targeted |
| **Smoke** | C | Unit selected |
| **Move** | V | Unit selected |
| **Defend** | D | Unit selected |
| **Hide** | H | Unit selected |
| **Cancel Command** | Escape | Unit selected |
| **Pan Camera** | WASD / Arrows / Edge scroll | Always |
| **Zoom** | Mouse Wheel | Always |
| **Pause Menu** | ESC | Always |
| **Time Control** | Space | In combat (pause/slow/normal/fast) |
| **LOS Check** | Hold Ctrl | Unit selected |
| **Screenshot** | F12 | Always (if enabled) |
| **Full Screen** | F11 | Always |

---

*User Guide Version*: 3.39
*Last Updated*: 2026-06-13
*Game Version*: PyCC2 v0.4.3
*CC2 Fidelity*: ~88%
*Status*: Beta Candidate — Fully Playable

**Next Update**: After M3 completion (command queue UI, vehicle damage visuals, save/load UI)
