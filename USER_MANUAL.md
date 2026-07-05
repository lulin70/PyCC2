# User Manual — PyCC2 **v0.4.3**

> **This document has been updated to v0.4.3. For earlier version information, see Git history.**

*Manual version: 2.0 — For PyCC2 v0.4.3 | Last updated: 2026-07-05*

*The complete guide to commanding your Allied squads in Operation Market Garden*

---

## Table of Contents

1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Units Guide](#units-guide)
4. [Terrain Guide](#terrain-guide)
5. [Combat Mechanics](#combat-mechanics)
6. [AI Opponent](#ai-opponent)
7. [Victory & Defeat](#victory--defeat)
8. [Controls Reference](#controls-reference)
9. [Strategy Guide](#strategy-guide)
10. [Campaign Missions](#campaign-missions)
11. [Save System](#save-system)
12. [Troubleshooting](#troubleshooting)
13. [Glossary](#glossary)

---

## Introduction

Welcome to **PyCC2**, a tactical WWII combat simulator set during **Operation Market Garden** (September 17–25, 1944). You command Allied infantry companies in brutal close-quarters battles against Axis forces across the Dutch countryside.

This is **not** an arcade game. There are no power-ups, no respawns, no health packs. Your squads have limited ammunition, fragile morale, and mortal soldiers. Every decision matters.

**Your role**: Company commander. You don't pull triggers — your soldiers do. You give orders: *Move there. Shoot that. Take cover here.* Your job is to put the right squad in the right place at the right time.

---

## Getting Started

### Launching the Game

```bash
# Start the game
pycc2

# Or using Python module
python -m pycc2.main
```

### The Main Screen

When you launch, you'll see:

```
+----------------------------------------------------------+
| [FPS:60] Tick:0150  Time:00:50  Turn:1  [PAUSED]        |  <- Top bar (HUD)
+----------------------------------------------------------+
|                                                          |
|    +-----+                                                |
|    | o * |  <- Selected unit (yellow ring)               |
|    +-----+  Health: XXXX..  Morale: XXXXXX                |
|                                                          |
|          # # #                                           |  <- Enemy units (gray)
|                                                          |
|    ........                                              |  <- Woods (dark green)
|    ........                                              |
|                                                          |
|  =======                                                 |  <- Road (gray)
|                                                          |
|  [Minimap]                     [Command Bar]             |  <- Bottom HUD
|  XXXXXXX___    [Move][Attack][Hold][Dig][X]              |
+----------------------------------------------------------+
```

### Basic Flow

1. **Select** a unit by left-clicking it
2. **Order** it by right-clicking (ground = move, enemy = attack)
3. **Monitor** health bars, morale, and ammo
4. **Win** by eliminating the enemy commander or destroying all enemy forces

---

## Units Guide

### Allied Forces (Player)

Your demo starts with **7 Allied units** on the left side of the map.

#### Infantry Squad (Rifle Squad)

| Stat | Value |
|------|-------|
| HP | 100 |
| Primary Weapon | Rifle (10 rounds) |
| Damage per Shot | 8 – 18 |
| Vision Range | 5 tiles |
| Movement Speed | 3.0 tiles/sec |
| Base Morale | 85 |
| Role | General-purpose workhorse |

**Best for**: Holding positions, advancing under fire, flanking maneuvers. Your main fighting force. Balanced stats make them versatile in any situation.

#### Machine Gun Squad (MG Team)

| Stat | Value |
|------|-------|
| HP | 80 |
| Primary Weapon | MG42 (50 rounds) |
| Damage per Shot | 12 – 25 |
| Vision Range | 6 tiles |
| Movement Speed | 2.0 tiles/sec |
| Base Morale | 75 |
| Role | Area suppression, defensive anchor |

**Best for**: Defensive positions, holding chokepoints, providing covering fire. Vulnerable when moving due to slow speed. The large magazine (50 rounds) means sustained fire capability.

#### Sniper Team

| Stat | Value |
|------|-------|
| HP | 60 |
| Primary Weapon | Sniper Rifle (15 rounds) |
| Damage per Shot | 25 – 50 |
| Vision Range | **10 tiles** |
| Movement Speed | 2.5 tiles/sec |
| Base Morale | 80 |
| Stealth Bonus | **+40% concealment** |
| Role | Long-range precision strikes |

**Best for**: Picking off exposed targets from distance, spotting enemies with extended vision. Keep behind cover — fragile at only 60 HP! High damage per shot but limited ammo requires precision.

#### Medic Team

| Stat | Value |
|------|-------|
| HP | 70 |
| Primary Weapon | Pistol (12 rounds) |
| Damage per Shot | 4 – 8 |
| Vision Range | 5 tiles |
| Movement Speed | 3.0 tiles/sec |
| Heal Range | 3 tiles |
| Heal Rate | 0.5 HP/tick |
| Base Morale | 88 |
| Role | Support — heals nearby allies |

**Best for**: Keeping your frontline squads fighting longer. Position near (but not in) the thick of combat. White helmet sprite serves as visible identifier on the battlefield.

#### Commander (Cpt. Miller)

| Stat | Value |
|------|-------|
| HP | 100 |
| Primary Weapon | Pistol (14 rounds) |
| Damage per Shot | 6 – 12 |
| Vision Range | **7 tiles** |
| Movement Speed | 3.0 tiles/sec |
| Base Morale | **95** |
| Role | **Critical asset — loss = potential defeat** |

**Best for**: Rear-area coordination (high vision range of 7 tiles). **Protect at all costs** — losing your commander is often an instant defeat condition and causes massive morale penalty to all friendly units.

### Axis Forces (AI Enemy)

The AI controls **7 equivalent units** in the demo. Expect to face:

| Unit | Name (in-game) | Threat Level |
|------|----------------|-------------|
| x3 Infantry Squads | Grenadier-1, Grenadier-2, Grenadier-3 | Medium — main assault force |
| x1 MG Team | MG Team | Medium — defensive anchor |
| x1 Commander | **Oberst Krebs** | **Critical — your primary target** |
| x1 Tank | Panzer IV | **High — major threat** (200 HP, 35-70 damage) |
| x1 Sniper | Scharfschutze | High — will hunt your exposed units |

> [!IMPORTANT]
> The **Axis side is fully AI-controlled** with CommanderAI, SquadCoordinator, BehaviorTree decision making, and difficulty scaling. You're fighting a real opponent.

---

## Terrain Guide

The battlefield features **14 terrain types**, each with unique properties that affect movement, combat, and visibility.

### Movement Costs (lower = faster movement)

| Terrain | Move Cost | Cover Bonus | Concealment | Passable? | Blocks LOS? |
|---------|-----------|-------------|-------------|-----------|-------------|
| **Open** | 1.0x | 0% | 0% | Yes | No |
| **Road** | 0.8x | 0% | 0% | Yes | No |
| **Grass** | 1.2x | 5% | 15% | Yes | No |
| **Woods** | 2.0x | **20%** | **50%** | Yes | **Yes** |
| **Building (Enterable)** | 1.5x | **50%** | **70%** | Yes | No |
| **Building (Solid)** | Infinite | **80%** | **90%** | No | **Yes** |
| **Water** | Infinite | 0% | 5% | No | **Yes** |
| **Hedge** | 2.5x | 15% | 35% | Yes | No |
| **Wall** | Infinite | **70%** | **80%** | No | **Yes** |
| **Rough** | 1.8x | 8% | 25% | Yes | No |
| **Shallow Water** | 3.0x | 5% | 10% | Yes | No |
| **Bridge** | 0.9x | 0% | 0% | Yes | No |
| **Crater** | 2.5x | **25%** | 20% | Yes | No |
| **Swamp** | 4.0x | 0% | 30% | Yes | No |

### Line of Sight (LOS)

These terrains **completely block line of sight** — you cannot shoot through them:

- **Woods** — Dense forest blocks vision; use for ambush positions
- **Solid Buildings** — Complete blockage; provides heavy nearby cover
- **Walls** — Complete blockage; hard cover for adjacent tiles
- **Water** — Complete blockage; impassable anyway

**Tactical use**: Hide your sniper or MG team behind woods or solid buildings. Wait for enemies to enter open ground, then engage from safety.

### Height Values

Each terrain has an implicit height that affects visibility:

| Terrain | Height |
|---------|--------|
| Crater | -1 (depression) |
| Open / Road / Grass / Water / Swamp / Shallow / Bridge | 0 (ground level) |
| Hedge | 1 (low obstacle) |
| Woods / Building (Enterable) / Wall | 2 (elevated) |
| Building (Solid) | 3 (tallest) |

Higher terrain can see over lower terrain in some LOS calculations.

---

## Combat Mechanics

### The Shooting Process

When your squad attacks an enemy, the game runs through this resolution pipeline:

```
1. RANGE CHECK
   -> Is target within weapon range? (varies by unit type)
   -> Max effective range varies by weapon (sniper > rifle > pistol)

2. LINE OF SIGHT (LOS)
   -> Is path clear? (Bresenham raycast through tile grid)
   -> Blocked by: Woods, Solid Buildings, Walls, Water
   -> Partially affected by terrain height differences

3. BALLISTIC CALCULATION (BallisticEngine)
   -> Hit probability based on:
      * Distance to target (closer = more accurate)
      * Target's cover bonus (in building = much harder to hit)
      * Shooter's experience (difficulty setting modifier)
      * Random factor for unpredictability

4. DAMAGE ROLL
   -> If hit: damage = random(weapon_min, weapon_max)
      modified by distance and cover
   -> Typical results:
      * Pistol hit: 4-12 HP
      * Rifle hit: 8-18 HP
      * MG42 hit: 12-25 HP
      * Sniper hit: 25-50 HP
      * Tank cannon: 35-70 HP
      * Mortar: 20-45 HP
      * AT Gun: 30-60 HP

5. MORALE IMPACT
   -> Both sides' morale affected by:
      * Taking casualties (big morale drop)
      * Friendly dying nearby (panic chain risk)
      * Being under sustained fire (suppression decay)
```

### Cover Matters — A Lot

An infantryman **in the open** (cover bonus 0%) might be hit 50-60% of the time.
The same infantryman **inside an enterable building** (cover bonus 50%) might be hit only 10-20% of the time.
Behind a **solid building** (cover bonus 80%), hit chance drops to nearly zero from that direction.

**Always approach covered positions. Fight from cover whenever possible.**

### Morale System

Each unit has a morale value (0–100) that governs combat effectiveness:

| Morale Range | State | Combat Effect |
|--------------|-------|---------------|
| 86 – 100 | **Confident** | Full combat effectiveness, normal accuracy |
| 51 – 85 | **Normal** | Standard performance, slight accuracy variation |
| 31 – 50 | **Shaken** | Reduced accuracy, hesitation in orders |
| 11 – 30 | **Suppressed** | May refuse orders, pinned down, very low accuracy |
| 0 – 10 | **Broken** | Routing — unit flees or surrenders, effectively out of fight |

**Morale drops when**:
- Squadmates die (especially nearby units) — **large penalty**
- Taking heavy damage quickly — cumulative effect
- Commander killed — **massive army-wide penalty**
- Significantly outnumbered — gradual pressure

**Morale recovers slowly when**:
- Not taking damage for several ticks
- Near friendly units (proximity bonus)
- Commander alive and within vision range

### Ammunition Management

Every shot consumes 1 round of ammunition. When empty, the unit enters **RELOADING** state and cannot act until complete.

| Unit Type | Magazine Size | Reload Vulnerability |
|-----------|--------------|---------------------|
| Rifle Squad | 10 rounds | Must reload frequently (~45 ticks) |
| MG Team | **50 rounds** | Long sustained fire, rare reloads |
| Sniper | 15 rounds | Precise shots, conserves well |
| Commander | 14 rounds | Secondary combatant, adequate |
| Medic | 12 rounds | Self-defense only |
| Tank | 30 rounds | Make each shot count |
| AT Gun | 8 rounds | Very limited, choose targets carefully |
| Mortar | 6 rounds | Extremely limited, indirect fire |

**Tip**: Don't waste shots on low-percentage targets. Wait for good angles and close range.

### Unit States (State Machine)

Each unit cycles through these states:

```
IDLE <--> MOVING <--> ATTACKING <--> RELOADING
                    |
                    v
                  DEAD (terminal)
```

- **IDLE**: Standing by, awaiting orders
- **MOVING**: Following a path to destination
- **ATTACKING**: Firing at a target
- **RELOADING**: replenishing ammunition (vulnerable!)
- **DEAD**: Removed from play (terminal state, no recovery)

---

## AI Opponent

### What the Enemy Commander Is Thinking

The Axis AI uses a multi-layered decision system with **four distinct layers**:

#### Layer 1: Perception System

Each AI unit maintains its own perception of the battlefield:
- What can this specific unit see? (respects fog of war — AI doesn't cheat!)
- Where are detected enemies?
- What is the threat level of each detected target?
- Stealth bonuses apply (snipers are harder to detect)

#### Layer 2: Squad Coordinator

Manages how squads work together as a team:
- **Fire Concentration**: Multiple squads focus fire on one high-value target
- **Bounding Overwatch**: One squad moves while another covers from a fixed position
- **Crossfire Setup**: Position squads to attack targets from two+ angles simultaneously
- **Flanking Maneuver**: Send units around the sides while main force fixes enemy attention

In the demo, two squads are registered:
- `axis_alpha`: 3 infantry units (coordinated assault group)
- `axis_bravo`: MG team + Commander (support/command group)

#### Layer 3: Commander AI (Oberst Krebs)

Strategic-level assessment by the enemy commander:
- Evaluates overall **force ratio** (Am I stronger or weaker?)
- Assesses **threat level** across 5 tiers: NONE → LOW → MEDIUM → HIGH → CRITICAL
- Generates strategic orders based on the complete battle picture
- Adjusts stance based on battle progression

#### Layer 4: Per-Unit Behavior Trees

Each individual AI unit runs its own **Behavior Tree (BT)** for tactical decisions:

```
Root
+-- Sequence: Engage Target
|   +-- Selector: Have Target?
|   |   +-- Condition: Target Assigned?
|   |   +-- Action: Acquire Nearest Enemy
|   +-- Sequence: Attack
|       +-- Condition: In Range?
|       +-- Condition: Has Ammo?
|       +-- Condition: LOS Clear?
|       +-- Action: Fire Weapon
|       +-- Action: Reload if Empty
+-- Sequence: Move Tactics
|   +-- Selector: Decision
|       +-- Condition: Health Low? -> Retreat
|       +-- Condition: Enemy Close? -> Find Cover
|       +-- Default -> Advance / Patrol
+-- Fallback: Idle / Patrol
```

Different unit types use specialized BT factories (infantry BT, MG squad BT, commander BT, etc.).

### Difficulty Levels

| Level | Name | AI Perception | AI Hit Chance | AI Ammo | AI Morale |
|-------|------|--------------|---------------|---------|-----------|
| 1 | **Recruit** | Reduced range | -20% penalty | Limited supply | Breaks easily (low threshold) |
| 2 | **Regular** | Normal | Baseline | Normal supply | Standard behavior |
| 3 | **Veteran** | Enhanced range | +15% bonus | Generous supply | Steady under pressure |
| 4 | **Hero** | Perfect vision | +30% bonus | Effectively infinite | Unbreakable morale |

The default demo uses **MEDIUM (Regular)** difficulty. 18 parameters are tunable per difficulty level.

---

## Victory & Defeat

### Victory Conditions (any one achieves victory)

| Condition | Description |
|-----------|-------------|
| **Eliminate Enemy Commander** | Kill Oberst Krebs — fastest path to victory |
| **Destroy All Enemies** | Every Axis unit dead or routed (morale <= 10) |
| **Morale Collapse** | Average Axis morale drops to 10 or below (they surrender) |
| **Capture Objective** | Hold a specific position for required duration |
| **Time Victory** | Most units alive when timer expires (attrition win) |

### Defeat Conditions (any one triggers defeat)

| Condition | Description |
|-----------|-------------|
| **Commander Killed** | Cpt. Miller dies — usually instant defeat |
| **All Forces Lost** | Every Allied unit dead or routed |
| **Morale Collapse** | Average Allied morale drops to 10 or below |
| **Time Defeat** | Fewer surviving units than enemy when timer expires |

### Post-Battle Screen

When the battle ends (victory or defeat):
- Game pauses automatically
- Semi-transparent overlay appears
- Statistics panel shows:
  - Battle duration (game ticks / real time)
  - Kills and losses (both sides)
  - Accuracy percentage
  - Kill ratio
  - Damage dealt/received
- Press **ESC** or **R** to return / exit

---

## Controls Reference

### Mouse Controls

| Action | Input |
|--------|-------|
| Select unit | **Left Click** on unit sprite |
| Add to selection | **Shift + Left Click** |
| Move ordered units | **Right Click** on empty ground tile |
| Attack target | **Right Click** on enemy unit sprite |
| Camera pan (drag) | **Middle Click + Drag** |
| Zoom in | **Scroll Wheel Up** |
| Zoom out | **Scroll Wheel Down** |

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| **Z** | Move Fast — rapid movement to position |
| **X** | Sneak — stealthy movement with reduced detection |
| **S** | Fire — attack/shoot at target |
| **C** | Smoke — deploy smoke screen |
| **V** | Move — normal movement to position |
| **D** | Defend — dig in / take cover at current position |
| **H** | Hide — enter concealment mode |
| **ESC** | Deselect all units / Pause game / Open menu |
| **Space** | Pause / Resume game |
| **W** | Pan camera up |
| **A** | Pan camera left |
| **S** | Pan camera down (when no unit selected) |
| **D** | Pan camera right (when no unit selected) |
| **F11** | Toggle fullscreen mode |
| **F1** | Help / Tutorial overlay — toggle interactive hints and lessons |
| **F3** | Toggle debug information overlay (FPS, tick count, entity positions) |
| **F5** | Quick save to slot 0 (overwrites previous quick save) |
| **F9** | Quick load from slot 0 |
| **F10** | Settings menu — configure graphics, audio, gameplay, controls (4 tabs) |
| **+** or **=** | Zoom in |
| **-** or **_** | Zoom out |

---

## Strategy Guide

### Beginner Tips (Read These First)

1. **Keep your commander safe** — Cpt. Miller is your most valuable asset (95 base morale, 7-tile vision). Keep him 2-3 tiles behind the front line. His death = likely instant defeat.

2. **Use cover aggressively** — Never fight in the open if you can fight from woods (20% cover) or enterable buildings (50% cover). The ballistic engine applies significant hit chance reduction.

3. **Concentrate fire** — It's better to destroy one enemy completely than to lightly wound three. Dead enemies don't shoot back.

4. **Don't expose flanks** — The AI's SquadCoordinator will try to flank you. Keep a reserve squad watching your sides, especially your commander's flank.

5. **Watch your ammo** — Reloading at the wrong moment leaves your squad vulnerable. Track magazine counts: rifles have only 10 rounds.

6. **MG teams are defensive anchors** — Bravo-MG (80 HP, 50-round magazine, 12-25 damage) is devastating in fixed positions but painfully slow (2.0 tiles/sec). Set up early, don't reposition often.

7. **Snipers need patience** — Hawkeye (60 HP, 10-tile vision, 25-50 damage, +40% stealth) is a glass cannon. Maximum range and damage, minimum survivability. Always keep in woods or buildings.

### Intermediate Tactics

8. **Bounding overwatch** — Move one infantry squad forward while the MG team covers from a fixed position. Once the first squad reaches cover, they cover while the next squad moves. Slow but minimizes exposure.

9. **The "anvil and hammer"** — Fix the enemy in place with your MG team (anvil — sustained suppressive fire), then flank with infantry squads (hammer — decisive assault from the side).

10. **Morale management** — Don't let any squad get isolated. A lone squad taking casualties without nearby friendlies will break much faster. Keep units within 3-4 tiles of each other when possible.

11. **Use terrain corridors** — Roads offer fastest movement (0.8x cost) but zero protection. Woods provide excellent cover (20%) and concealment (50%) but halve your speed (2.0x cost). Find the tactical balance for each situation.

12. **Tank handling** — The enemy Panzer IV (200 HP, 35-70 damage per shot) is a major threat. It attracts ALL enemy fire due to its size. If you had a tank, support it with infantry. Against the enemy tank: coordinate sniper + MG + concentrated rifle fire.

13. **Medic positioning** — Doc (heals 0.5 HP/tick within 3 tiles) should stay 2 tiles behind the main line. This gives maximum coverage to frontline units while staying out of direct fire.

14. **Crater fields** — New in v0.4, bomb craters provide 25% cover bonus at the cost of slow movement (2.5x). Use them as improvised fighting positions when no better cover exists.

### Advanced Concepts

15. **Time advantage** — The AI processes decisions every game tick (~33ms at 30 UPS). Faster tactical decisions = more actions executed. Don't pause too long thinking — momentum matters.

16. **Suppression chains** — Even if you don't kill, suppressing an enemy (morale < 30) effectively removes them from the fight. They may refuse orders, stop shooting, or even rout. MG teams excel at area suppression due to high rate of fire and 50-round magazines.

17. **The commander snipe** — The fastest victory condition is killing Oberst Krebs. Risky because he's protected, but efficient: one well-placed sniper shot or concentrated volley can end the battle instantly. Worth attempting if you spot him exposed.

18. **Economy of force** — You don't need to win everywhere. Commit decisively in one sector, achieve local superiority, then roll the victory outward. A strong flank beats a weak front everywhere.

19. **AI behavior exploitation** — The AI's Behavior Tree prioritizes nearest threats and follows predictable patterns (patrol points, reaction to contact). Learn these patterns and set ambushes at predictable approach routes.

20. **Victory condition selection** — You don't always need to kill everyone. If the enemy morale is collapsing (several units below 30 morale), push hard to trigger mass surrender rather than hunting down every last soldier.

---

## Campaign Missions

PyCC2 includes a **campaign system** with **10 predefined missions** of escalating difficulty, spanning **63 historical maps** across Operation Market Garden:

### Mission 1: First Contact (Tutorial Difficulty)

- **Objective**: Eliminate the Axis recon patrol
- **Your Force**: 3 Infantry + 1 Commander
- **Enemy Force**: 3 Infantry + 1 Commander
- **Map**: Tutorial (20x20, basic terrain mix)
- **Tips**: Straightforward introduction to controls and mechanics. Focus on learning selection, movement, and attack orders. The smaller map means faster engagement. This mission includes **interactive tutorial prompts** that guide new players through the basics.

### Mission 2: The Bridge Too Far (Regular Difficulty)

- **Objective**: Secure the bridge crossing within time limit
- **Your Force**: 3 Infantry + 1 MG + 1 Sniper + 1 Commander
- **Enemy Force**: 3 Infantry + 1 MG + **1 Tank** + 1 Commander
- **Map**: Bridge Assault (24x24, includes bridge tile, craters, swamp sector)
- **Tips**: The Panzer IV changes everything. Use your sniper (Hawkeye) to soften it from max range, coordinate MG covering fire, and rush the objective before time runs out. The swamp sector slows movement — avoid it or use it as a barrier.

### Mission 3: Hold the Line (Veteran Difficulty)

- **Objective**: Defensive stand — hold position for time limit
- **Your Force**: 3 Infantry + 1 MG + 1 Medic + 1 Mortar + 1 Commander
- **Enemy Force**: 3 Infantry + 1 MG + 1 Tank + 1 Sniper + 1 Commander
- **Map**: Defense Line (larger map, varied terrain with multiple approach corridors)
- **Tips**: Defense is harder than offense. Use the medic (Doc) to keep squads fighting longer. The mortar team provides indirect fire against clustered enemies. Don't let them break through any single point — defense in depth.

### Mission 4: Counter-Attack (Veteran+ Difficulty)

- **Objective**: Breakthrough and eliminate enemy reinforcements
- **Your Force**: 4 Infantry + 1 MG + 1 Sniper + 1 Medic + 1 Mortar + 1 Commander
- **Enemy Force**: 4 Infantry + 2 MG + **1 Tank** + 1 Sniper + 1 AT Gun + 1 Commander
- **Map**: Open Field (large open terrain with limited cover)
- **Tips**: The enemy AT Gun is a major threat to your forces. Use smoke (if available) or terrain masking to approach. Coordinate combined arms: infantry draws fire while flanking units hit weak points. The medic becomes critical for sustained operations.

### Mission 5: Armored Column (Expert)

- **Objective**: Defensive stand against armored column for 20 minutes
- **Your Force**: 3× Rifle, 2× AT Guns, 1× Tank
- **Enemy Force**: 4× Tank, 3× Infantry
- **Map**: defense_line.json (48×32)
- **Tips**: AT weapons deal +200% damage to vehicles. Defensive formations provide +25% cover bonus. Tank AI prioritizes AT positions.

### Mission 6: Son (Hard) ⭐ NEW

- **Objective**: Capture the Son bridge
- **Your Force**: 5× Rifle, 2× MG, 1× Sniper
- **Enemy Force**: 6× Rifle, 3× MG, 2× AT Guns
- **Map**: son.json (44×36)
- **Tips**: Historical Day 1 battle (Sept 17). Bridge is key objective. Use combined arms approach.

### Mission 7: Veghel (Hard) ⭐ NEW

- **Objective**: Break through Veghel defensive line
- **Your Force**: 4× Rifle, 2× Tank, 1× AT Gun, 1× Medic
- **Enemy Force**: 8× Rifle, 4× MG, 2× AT Guns, 1× Tank
- **Map**: veghel.json (52×40)
- **Tips**: Historical Day 2 battle (Sept 18). Armor-infantry coordination critical.

### Mission 8: Grave (Expert) ⭐ NEW

- **Objective**: Cross the Grave river and survive
- **Your Force**: 3× Rifle, 1× MG, 1× Medic
- **Enemy Force**: 10× Rifle, 5× MG, 3× Tank
- **Map**: grave.json (48×48)
- **Tips**: Historical Day 4 battle (Sept 20). River crossing is dangerous. Use smoke for cover.

### Mission 9: Nijmegen (Expert) ⭐ NEW

- **Objective**: Seize the north bank of Waal river
- **Your Force**: 6× Rifle, 3× MG, 2× Tank, 1× Mortar
- **Enemy Force**: 12× Rifle, 6× MG, 4× Tank, 2× AT Guns
- **Map**: nijmegen.json (64×48)
- **Tips**: Historical Day 4 battle (Sept 20). Urban combat requires room-by-room clearing.

### Mission 10: Arnhem (Legend) ⭐ NEW

- **Objective**: Final assault on Arnhem bridge
- **Your Force**: 8× Rifle, 4× MG, 3× Tank, 2× Mortar
- **Enemy Force**: 8× Rifle, 4× MG, 3× Tank
- **Map**: arnhem.json (64×64)
- **Tips**: Historical final battle (Sept 24-26). Largest map with complex terrain. Full combined arms required.

> [!NOTE]
> Launch the game with `pycc2` or `python -m pycc2.main` to access the full campaign system. For mission-specific configurations, see the campaign system source code in `src/pycc2/domain/systems/campaign.py`.

---

## Tutorial System

PyCC2 includes an **integrated tutorial system** designed to help new players learn the game mechanics progressively:

### Tutorial Features

- **Interactive Prompts**: Context-sensitive hints appear during gameplay
- **Progressive Lessons**: Unlocks new concepts as you demonstrate mastery
- **Practice Mode**: Safe environment to experiment without consequences
- **Quick Reference**: Accessible anytime via **F1** key during gameplay

### Tutorial Lessons

| Lesson | Topic | Covered Mechanics |
|--------|-------|-------------------|
| 1 | Basic Selection | Left-click, multi-select with Shift |
| 2 | Movement | Right-click on ground, pathfinding |
| 3 | Combat Basics | Attack orders, range indicators |
| 4 | Cover System | Terrain bonuses, positioning |
| 5 | Morale Management | Morale bar, panic prevention |
| 6 | Advanced Tactics | Flanking, suppression fire |
| 7 | Unit Specialties | Each unit type's unique role |

### Accessing Tutorials

- Press **F1** at any time during gameplay to toggle tutorial overlay
- First launch automatically starts Tutorial (Mission 1)
- Can be replayed from the main menu or campaign screen
- Progress is saved independently of campaign saves

---

## Save System

PyCC2 supports **8 save slots** with **HMAC-SHA256 cryptographic integrity verification**:

### Quick Save/Load

| Key | Action |
|-----|--------|
| **F5** | Quick save to slot 0 (overwrites previous quick save) |
| **F9** | Quick load from slot 0 (most recent quick save) |

### Save File Location

```
PyCC2/saves/
+-- save_slot_0.json    <- Quick save slot (F5/F9)
+-- save_slot_1.json
+-- save_slot_2.json
+-- ...
+-- save_slot_7.json
```

### Save File Integrity (Tamper Protection)

Each save file contains an **HMAC-SHA256 cryptographic signature** computed over the entire save data. When loading:

1. Game reads the save JSON data
2. Recomputes HMAC-SHA256 using a secret key
3. Compares stored signature vs. recomputed signature
4. **If mismatch**: Save marked **CORRUPTED** — refused to load
5. **If format changed between versions**: Save marked **INCOMPATATIBLE**

This prevents:
- Editing HP values to invincibility
- Modifying ammo counts
- Changing unit positions
- Any form of save-file cheating

### Save Data Contents

Each save stores the complete game state:
- All unit positions, health, morale, ammo, state
- Camera position and zoom level
- Game tick counter and elapsed time
- Active victory/defeat condition state
- AI blackboard states and commander decisions
- Map state (if dynamic terrain is implemented)

---

## Troubleshooting

### Game window doesn't appear

- Verify pygame can access your display (see INSTALL.md platform-specific notes)
- Try setting environment variable: `SDL_VIDEODRIVER=x11` (Linux)
- On macOS: Allow Terminal/Terminal.app access in System Settings > Privacy & Security > Screen Recording

### Units don't respond to clicks

- Make sure you're clicking **on** the unit sprite (the colored figure), not near it
- Check that the game isn't paused (press **Space** to toggle pause)
- Verify a unit is actually selected (look for yellow highlight ring)

### Can't hear any sound

- Check system volume isn't muted
- PyCC2 generates audio **procedurally** — no external audio files are needed or loaded
- Some CI/headless environments don't support audio hardware — this is non-fatal, the game works silently
- Run: `python -c "import pygame; pygame.init(); pygame.mixer.init(); print(pygame.mixer.get_init())"` to test

### Game feels slow or laggy

- Reduce window size in Settings menu (F10)
- Lower display quality preset in configuration
- Ensure you're running **native Python** (not Rosetta translation on Apple Silicon Macs)
- Check FPS counter in HUD — if consistently below 30, consider reducing map size or unit count

### Saved game won't load

- Confirm `PyCC2/saves/` directory exists and contains `.json` files
- If status shows **CORRUPTED**: The file was tampered with — delete it and create a new save
- If status shows **INCOMPATIBLE**: The save format changed between versions — delete old saves, they can't be migrated
- Quick save slot (slot 0) is overwritten each time you press F5 — use other slots for named saves

### AI seems too easy / too hard

- Difficulty is configurable in the Settings menu (F10 → Gameplay tab)
- 5 presets available: RECRUIT / EASY / NORMAL / HARD / VETERAN
- Each preset adjusts experience level, supply level, and AI parameters independently per faction

---

## Glossary

| Term | Definition |
|------|------------|
| **Ballistic Engine** | Calculates shot trajectories, hit probability, and damage using distance falloff, cover modifiers, and random variance |
| **Behavior Tree (BT)** | Hierarchical AI decision-making structure used by each unit for tactical choices (move, shoot, reload, retreat) |
| **Blackboard** | Shared memory structure where AI units read/write tactical information (target assignments, threat levels, patrol state) |
| **Cover Bonus** | Percentage reduction in enemy hit chance when occupying certain terrain (buildings > woods > craters > open) |
| **Concealment Modifier** | Reduction in detection probability — higher value = harder for enemy to spot this unit |
| **Domain-Driven Design (DDD)** | Architectural pattern separating business logic (domain layer) from technical concerns (presentation/infrastructure) |
| **EventBus** | Publish/subscribe messaging system connecting game components decoupled from each other |
| **Fog of War** | Areas not visible to any of your units are hidden from both display and AI perception |
| **HMAC-SHA256** | Hash-based Message Authentication Code — cryptographic signature ensuring save files haven't been tampered with |
| **LOS (Line of Sight)** | Whether a straight-line path from shooter to target is unobstructed by blocking terrain (woods, solid buildings, walls, water) |
| **Morale** | Unit's willingness to fight (0–100 scale); low morale reduces accuracy, may cause routing |
| **Pixel Art** | Graphics style where images are drawn pixel-by-pixel, matching the original CC2 aesthetic |
| **Procedural Generation** | Creating content (sprites, sounds) via algorithms instead of external art/audio asset files |
| **State Machine** | Finite state controller managing unit lifecycle: IDLE → MOVING → ATTACKING → RELOADING → DEAD |
| **Suppression** | Combat state where heavy fire drives morale below 30, severely reducing effectiveness |
| **Tile** | One square unit of the game map grid; represents approximately 10 meters of real-world distance |
| **UPS (Updates Per Second)** | Game logic tick rate; PyCC2 runs logic at fixed 30 UPS with render interpolation at target FPS |
| **Unit Template** | Data definition containing all stats for a unit type (HP, weapon, speed, vision, etc.) |
| **Victory Conditions** | Set of rules determining when the battle ends and who wins (commander kill, elimination, morale collapse, objective, time) |

---

| Version | Date | Notes |
|---------|------|-------|
| v2.0 | 2026-06-14 | **v0.4.0**: Updated to current version — launch via `pycc2`, 7-command hotkey system (Z/X/S/C/V/D/H), save format save_slot_X.json, 63 maps, 277 unit templates, ~3513 tests, CC2 fidelity ~88% |
| v1.8 | 2026-05-19 | **v0.6-p4w2**: P5/P6/P7 Complete — Campaign Core (~60%), Combat Depth (~85%), Content Expansion (M6-M10), 10 missions, 10 maps, CC2 Fidelity ~71%, 1566 tests |
| v1.7 | 2026-05-19 | **v0.6-p4w2**: CC2 gap analysis (Campaign ~5%, Combat ~65%), Roadmap revised to P5 Campaign Core, Night combat system, Anti-tank armor mechanics, Weather rendering, Trilingual documentation (EN/ZH/JA), 1377 tests |
| v1.6 | 2026-05-19 | **v0.6-p4w2**: Campaign expanded to 5 missions (M1-M5), Tutorial system added, F1/F10 shortcuts, Performance optimizations documented, 1270 tests |
| v1.5 | 2026-05-18 | **v0.5-p4w1**: GameLoop decomposition, Settings menu (4 tabs), Security hardening, 1163 tests |
| v1.4 | 2025-05-18 | P3-Fix: 4 critical bugs resolved — BallisticEngine weapons补全, quick_load状态恢复, AI循环边界修复, main.py入口点重写 |
| v1.3 | 2026-05-17 | Complete Edition baseline — Full feature set documented |

---
*Manual version: 2.0 — For PyCC2 v0.4.3*
*Last updated: 2026-07-05*
