"""
Legacy Campaign System for PyCC2.

.. deprecated::
    This module is superseded by ``campaign_four_layer.py`` which provides
    CC2UnitTemplate-based unit definitions, four-layer campaign architecture,
    and richer tactical objectives.  This file is retained for backward
    compatibility only and will be removed in v0.9.

    Migration guide:
        - MissionDifficulty  → campaign_four_layer.CC2Difficulty
        - MissionObjective   → campaign_four_layer.CC2ObjectiveType
        - MissionDefinition  → campaign_four_layer.CC2Mission
        - ally_unit_templates / enemy_unit_templates (list[dict])
            → campaign_four_layer.CC2UnitTemplate instances
        - CampaignManager    → campaign_four_layer.FourLayerCampaignManager
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pycc2.domain.systems.campaign_state import BattleResult, CampaignState


class MissionDifficulty(Enum):
    RECRUIT = auto()
    REGULAR = auto()
    VETERAN = auto()
    HERO = auto()


class MissionObjective(Enum):
    ELIMINATE_ENEMY_FORCE = auto()
    CAPTURE_LOCATION = auto()
    SURVIVE_FOR_TIME = auto()
    ESCORT_UNIT = auto()
    DEFEND_POSITION = auto()


@dataclass
class MissionObjectiveDef:
    objective_type: MissionObjective
    description: str
    target_id: str | None = None
    position: tuple[int, int] | None = None
    radius: int = 0
    time_limit_ticks: int = 0


@dataclass
class MissionDefinition:
    id: str
    name: str
    description: str
    map_id: str
    difficulty: MissionDifficulty

    player_faction: str = "allies"
    time_limit_ticks: int = 0
    is_night_mission: bool = False
    weather: str = "clear"

    objectives: list[MissionObjectiveDef] = field(default_factory=list)
    ally_unit_templates: list[dict] = field(default_factory=list)
    enemy_unit_templates: list[dict] = field(default_factory=list)

    allow_defeat: bool = True
    brief_text: str = ""

    @property
    def total_objectives(self) -> int:
        return len(self.objectives)


class CampaignManager:
    def __init__(self, use_campaign_state: bool = False):
        self._missions: dict[str, MissionDefinition] = {}
        self._completed_missions: set[str] = set()
        self._current_mission: MissionDefinition | None = None
        self._campaign_state: CampaignState | None = None
        if use_campaign_state:
            from pycc2.domain.systems.campaign_state import CampaignState

            self._campaign_state = CampaignState.create_default()

    @property
    def campaign_state(self) -> CampaignState | None:
        return self._campaign_state

    def enable_campaign_mode(self) -> None:
        from pycc2.domain.systems.campaign_state import CampaignState

        if self._campaign_state is None:
            self._campaign_state = CampaignState.create_default()

    def register_mission(self, mission: MissionDefinition) -> None:
        self._missions[mission.id] = mission

    def get_mission(self, mission_id: str) -> MissionDefinition | None:
        return self._missions.get(mission_id)

    def start_mission(self, mission_id: str) -> MissionDefinition | None:
        mission = self.get_mission(mission_id)
        if mission:
            self._current_mission = mission
        return mission

    def complete_current_mission(
        self,
        victory: bool,
        battle_result: BattleResult | None = None,
    ) -> None:
        if self._current_mission:
            if victory:
                self._completed_missions.add(self._current_mission.id)
            if self._campaign_state and battle_result is not None:
                self._campaign_state.record_battle(battle_result)
                if victory:
                    self._campaign_state.replenish_all_units()
            self._current_mission = None

    @property
    def available_missions(self) -> list[MissionDefinition]:
        return [m for m in self._missions.values() if m.id not in self._completed_missions]

    @property
    def completed_count(self) -> int:
        return len(self._completed_missions)

    @property
    def total_missions(self) -> int:
        return len(self._missions)

    def get_missions_for_day(self, day: int) -> list[MissionDefinition]:
        """Get missions assigned to a specific operation day."""
        DAY_MISSION_MAP = {
            1: ["mission_01_tutorial", "mission_02_bridge", "mission_06_son"],
            2: ["mission_07_veghel", "mission_08_grave"],
            3: ["mission_04_night", "mission_09_nijmegen"],
            4: ["mission_03_hold", "mission_05_armor"],
            5: ["mission_10_arnhem"],
        }
        ids = DAY_MISSION_MAP.get(day, [])
        missions = []
        for mid in ids:
            m = self.get_mission(mid)
            if m and m.id not in self._completed_missions:
                missions.append(m)
        return missions


def create_default_campaign() -> CampaignManager:
    mgr = CampaignManager()

    mgr.register_mission(
        MissionDefinition(
            id="mission_01_tutorial",
            name="First Contact",
            description="Eliminate the Axis recon patrol. A straightforward introduction to combat.",
            map_id="tutorial",
            difficulty=MissionDifficulty.RECRUIT,
            objectives=[
                MissionObjectiveDef(
                    objective_type=MissionObjective.ELIMINATE_ENEMY_FORCE,
                    description="Destroy all enemy units",
                ),
            ],
            ally_unit_templates=[
                {"unit_type": "INFANTRY_SQUAD", "position": (2, 2)},
                {"unit_type": "INFANTRY_SQUAD", "position": (2, 5)},
                {"unit_type": "COMMANDER", "position": (4, 4)},
            ],
            enemy_unit_templates=[
                {"unit_type": "INFANTRY_SQUAD", "position": (17, 17)},
                {"unit_type": "INFANTRY_SQUAD", "position": (17, 14)},
                {"unit_type": "COMMANDER", "position": (16, 16)},
            ],
            brief_text="Welcome to Operation Market Garden, soldier. Your first task is to eliminate an Axis recon patrol operating near the drop zone. Use cover and coordinate your squads carefully.",
        )
    )

    mgr.register_mission(
        MissionDefinition(
            id="mission_02_bridge",
            name="The Bridge Too Far",
            description="Seize the strategic bridge before Axis reinforcements arrive.",
            map_id="bridge_assault",
            difficulty=MissionDifficulty.REGULAR,
            time_limit_ticks=5400,
            objectives=[
                MissionObjectiveDef(
                    objective_type=MissionObjective.CAPTURE_LOCATION,
                    description="Secure the bridge crossing",
                    position=(10, 10),
                    radius=2,
                ),
                MissionObjectiveDef(
                    objective_type=MissionObjective.ELIMINATE_ENEMY_FORCE,
                    description="Destroy or rout enemy forces",
                ),
            ],
            ally_unit_templates=[
                {"unit_type": "INFANTRY_SQUAD", "position": (2, 3)},
                {"unit_type": "INFANTRY_SQUAD", "position": (2, 7)},
                {"unit_type": "MACHINE_GUN_SQUAD", "position": (4, 5)},
                {"unit_type": "SNIPER_TEAM", "position": (3, 9)},
                {"unit_type": "COMMANDER", "position": (4, 5)},
            ],
            enemy_unit_templates=[
                {"unit_type": "INFANTRY_SQUAD", "position": (17, 3)},
                {"unit_type": "INFANTRY_SQUAD", "position": (17, 7)},
                {"unit_type": "MACHINE_GUN_SQUAD", "position": (16, 5)},
                {"unit_type": "TANK", "position": (18, 5)},
                {"unit_type": "COMMANDER", "position": (16, 6)},
            ],
            brief_text="Intelligence reports a heavy Axis presence guarding the bridge. A Panzer IV has been spotted. You have a sniper team for long-range support and 3 minutes to secure the objective before their reinforcements arrive.",
        )
    )

    mgr.register_mission(
        MissionDefinition(
            id="mission_03_hold",
            name="Hold the Line",
            description="Defend your position against waves of Axis attackers.",
            map_id="defense_line",
            difficulty=MissionDifficulty.VETERAN,
            objectives=[
                MissionObjectiveDef(
                    objective_type=MissionObjective.DEFEND_POSITION,
                    description="Hold the defensive line for 5 minutes",
                    position=(5, 10),
                    radius=3,
                    time_limit_ticks=9000,
                ),
            ],
            ally_unit_templates=[
                {"unit_type": "INFANTRY_SQUAD", "position": (4, 8)},
                {"unit_type": "INFANTRY_SQUAD", "position": (6, 8)},
                {"unit_type": "MACHINE_GUN_SQUAD", "position": (5, 10)},
                {"unit_type": "MEDIC_TEAM", "position": (5, 11)},
                {"unit_type": "MORTAR_TEAM", "position": (3, 12)},
                {"unit_type": "COMMANDER", "position": (5, 9)},
            ],
            enemy_unit_templates=[
                {"unit_type": "INFANTRY_SQUAD", "position": (17, 4)},
                {"unit_type": "INFANTRY_SQUAD", "position": (17, 8)},
                {"unit_type": "INFANTRY_SQUAD", "position": (17, 12)},
                {"unit_type": "MACHINE_GUN_SQUAD", "position": (16, 8)},
                {"unit_type": "TANK", "position": (18, 6)},
                {"unit_type": "SNIPER_TEAM", "position": (18, 10)},
                {"unit_type": "COMMANDER", "position": (17, 8)},
            ],
            brief_text="The Axis counterattack has begun. You must hold this sector at all costs. Your mortar team provides indirect fire support, and the medic team can patch up wounded squads. Do not let them break through!",
        )
    )

    mgr.register_mission(
        MissionDefinition(
            id="mission_04_night",
            name="Night Assault",
            description="Infiltrate under cover of darkness and destroy the enemy mortar position before dawn.",
            map_id="night_map",
            difficulty=MissionDifficulty.VETERAN,
            time_limit_ticks=7200,
            is_night_mission=True,
            weather="clear",
            objectives=[
                MissionObjectiveDef(
                    objective_type=MissionObjective.CAPTURE_LOCATION,
                    description="Destroy the enemy mortar battery",
                    position=(17, 5),
                    radius=2,
                ),
                MissionObjectiveDef(
                    objective_type=MissionObjective.CAPTURE_LOCATION,
                    description="Reach the extraction point",
                    position=(3, 19),
                    radius=2,
                ),
            ],
            ally_unit_templates=[
                {"unit_type": "INFANTRY_SQUAD", "position": (2, 18)},
                {"unit_type": "INFANTRY_SQUAD", "position": (2, 20)},
                {"unit_type": "SNIPER_TEAM", "position": (4, 19)},
                {"unit_type": "COMMANDER", "position": (3, 19)},
            ],
            enemy_unit_templates=[
                {"unit_type": "INFANTRY_SQUAD", "position": (17, 3)},
                {"unit_type": "INFANTRY_SQUAD", "position": (19, 5)},
                {"unit_type": "MACHINE_GUN_SQUAD", "position": (18, 4)},
                {"unit_type": "MACHINE_GUN_SQUAD", "position": (16, 6)},
                {"unit_type": "MORTAR_TEAM", "position": (17, 5)},
                {"unit_type": "COMMANDER", "position": (18, 5)},
            ],
            brief_text="0230 Hours. Intelligence confirms an enemy mortar battery is pounding our forward positions. Your elite squad must infiltrate through the forest, neutralize the mortar position, and extract before sunrise. Visibility is severely limited — use the darkness to your advantage. The enemy has MG nests covering likely approaches. Stealth and speed are essential.",
        )
    )

    mgr.register_mission(
        MissionDefinition(
            id="mission_05_armor",
            name="Armored Column",
            description="Ambush and destroy an enemy armored convoy before it reaches the frontline.",
            map_id="road_ambush",
            difficulty=MissionDifficulty.HERO,
            time_limit_ticks=5400,
            objectives=[
                MissionObjectiveDef(
                    objective_type=MissionObjective.ELIMINATE_ENEMY_FORCE,
                    description="Destroy all armored vehicles",
                ),
                MissionObjectiveDef(
                    objective_type=MissionObjective.SURVIVE_FOR_TIME,
                    description="Prevent enemy breakthrough",
                    time_limit_ticks=5400,
                ),
            ],
            ally_unit_templates=[
                {"unit_type": "INFANTRY_SQUAD", "position": (3, 8)},
                {"unit_type": "INFANTRY_SQUAD", "position": (3, 16)},
                {"unit_type": "MACHINE_GUN_SQUAD", "position": (5, 12)},
                {"unit_type": "SNIPER_TEAM", "position": (2, 12)},
                {"unit_type": "TANK", "position": (4, 12)},
                {"unit_type": "COMMANDER", "position": (4, 13)},
            ],
            enemy_unit_templates=[
                {"unit_type": "TANK", "position": (30, 10)},
                {"unit_type": "TANK", "position": (32, 14)},
                {"unit_type": "TANK", "position": (28, 12)},
                {"unit_type": "INFANTRY_SQUAD", "position": (29, 11)},
                {"unit_type": "INFANTRY_SQUAD", "position": (31, 13)},
                {"unit_type": "MACHINE_GUN_SQUAD", "position": (30, 12)},
                {"unit_type": "COMMANDER", "position": (31, 12)},
            ],
            brief_text="An enemy armored column has been spotted moving along the main supply route. Three Panzer IV tanks with infantry escort are heading toward our lines. You have one Sherman tank and limited anti-tank capabilities. Set the ambush along the tree line and hit them hard — you may only get one chance. Destroy the armor before they break through.",
        )
    )

    mgr.register_mission(
        MissionDefinition(
            id="mission_06_son",
            name="Son Bridge",
            description="Secure the first bridge on the Hell's Highway corridor.",
            map_id="son_bridge",
            difficulty=MissionDifficulty.REGULAR,
            time_limit_ticks=4800,
            objectives=[
                MissionObjectiveDef(
                    objective_type=MissionObjective.CAPTURE_LOCATION,
                    description="Secure the Son bridge crossing",
                    position=(12, 10),
                    radius=2,
                ),
                MissionObjectiveDef(
                    objective_type=MissionObjective.ELIMINATE_ENEMY_FORCE,
                    description="Destroy defending Axis force",
                ),
            ],
            ally_unit_templates=[
                {"unit_type": "INFANTRY_SQUAD", "position": (2, 3)},
                {"unit_type": "INFANTRY_SQUAD", "position": (2, 16)},
                {"unit_type": "SNIPER_TEAM", "position": (4, 10)},
                {"unit_type": "MACHINE_GUN_SQUAD", "position": (3, 8)},
                {"unit_type": "COMMANDER", "position": (3, 10)},
            ],
            enemy_unit_templates=[
                {"unit_type": "INFANTRY_SQUAD", "position": (20, 8)},
                {"unit_type": "INFANTRY_SQUAD", "position": (20, 13)},
                {"unit_type": "MACHINE_GUN_SQUAD", "position": (21, 10)},
                {"unit_type": "COMMANDER", "position": (20, 10)},
            ],
            brief_text="17 September, 1330 hours. The 101st Airborne has dropped near Son. Your first objective is to seize the bridge over the Wilhelmina Canal. German resistance is expected to be light but don't underestimate them — reconnaissance suggests an MG nest covering the approach.",
        )
    )

    mgr.register_mission(
        MissionDefinition(
            id="mission_07_veghel",
            name="Veghel Corridor",
            description="Clear Veghel and secure the supply route.",
            map_id="veghel",
            difficulty=MissionDifficulty.VETERAN,
            time_limit_ticks=6000,
            objectives=[
                MissionObjectiveDef(
                    objective_type=MissionObjective.CAPTURE_LOCATION,
                    description="Capture Veghel bridge",
                    position=(13, 11),
                    radius=2,
                ),
                MissionObjectiveDef(
                    objective_type=MissionObjective.DEFEND_POSITION,
                    description="Hold the corridor for reinforcements",
                    position=(13, 15),
                    radius=3,
                    time_limit_ticks=3000,
                ),
            ],
            ally_unit_templates=[
                {"unit_type": "INFANTRY_SQUAD", "position": (11, 19)},
                {"unit_type": "INFANTRY_SQUAD", "position": (13, 19)},
                {"unit_type": "INFANTRY_SQUAD", "position": (15, 19)},
                {"unit_type": "MACHINE_GUN_SQUAD", "position": (13, 18)},
                {"unit_type": "SNIPER_TEAM", "position": (10, 18)},
                {"unit_type": "COMMANDER", "position": (13, 20)},
            ],
            enemy_unit_templates=[
                {"unit_type": "INFANTRY_SQUAD", "position": (11, 4)},
                {"unit_type": "INFANTRY_SQUAD", "position": (13, 4)},
                {"unit_type": "INFANTRY_SQUAD", "position": (15, 4)},
                {"unit_type": "INFANTRY_SQUAD", "position": (13, 6)},
                {"unit_type": "MACHINE_GUN_SQUAD", "position": (12, 5)},
                {"unit_type": "MACHINE_GUN_SQUAD", "position": (14, 5)},
                {"unit_type": "TANK", "position": (13, 3)},
                {"unit_type": "COMMANDER", "position": (13, 5)},
            ],
            brief_text="18 September. Veghel is a critical junction on 'Hell's Highway' — without it, XXX Corps cannot advance north. The town is held by battle-hardened German paratroopers. Clear the buildings methodically.",
        )
    )

    mgr.register_mission(
        MissionDefinition(
            id="mission_08_grave",
            name="Grave Crossing",
            description="Force a crossing of the Maas-Frank Canal.",
            map_id="grave",
            difficulty=MissionDifficulty.VETERAN,
            time_limit_ticks=7200,
            is_night_mission=True,
            weather="clear",
            objectives=[
                MissionObjectiveDef(
                    objective_type=MissionObjective.CAPTURE_LOCATION,
                    description="Seize Grave bridge",
                    position=(12, 6),
                    radius=2,
                ),
                MissionObjectiveDef(
                    objective_type=MissionObjective.CAPTURE_LOCATION,
                    description="Establish bridgehead on north bank",
                    position=(12, 18),
                    radius=3,
                ),
            ],
            ally_unit_templates=[
                {"unit_type": "INFANTRY_SQUAD", "position": (8, 21)},
                {"unit_type": "INFANTRY_SQUAD", "position": (12, 21)},
                {"unit_type": "INFANTRY_SQUAD", "position": (16, 21)},
                {"unit_type": "MACHINE_GUN_SQUAD", "position": (10, 20)},
                {"unit_type": "MORTAR_TEAM", "position": (14, 22)},
                {"unit_type": "SNIPER_TEAM", "position": (12, 20)},
                {"unit_type": "COMMANDER", "position": (12, 22)},
            ],
            enemy_unit_templates=[
                {"unit_type": "INFANTRY_SQUAD", "position": (8, 3)},
                {"unit_type": "INFANTRY_SQUAD", "position": (12, 3)},
                {"unit_type": "INFANTRY_SQUAD", "position": (16, 3)},
                {"unit_type": "INFANTRY_SQUAD", "position": (12, 5)},
                {"unit_type": "MACHINE_GUN_SQUAD", "position": (10, 4)},
                {"unit_type": "MACHINE_GUN_SQUAD", "position": (14, 4)},
                {"unit_type": "TANK", "position": (12, 2)},
                {"unit_type": "COMMANDER", "position": (12, 4)},
            ],
            brief_text="17 September, dusk. The Grave bridge spans the Maas-Frank Canal — a major obstacle. Intelligence reports a strong German presence on the far bank. You'll need to cross under cover of darkness. The mortar team can provide suppressive fire while infantry forces the crossing.",
        )
    )

    mgr.register_mission(
        MissionDefinition(
            id="mission_09_nijmegen",
            name="Nijmegen Waal Crossing",
            description="Cross the Waal river under heavy fire and seize the Nijmegen bridge.",
            map_id="nijmegen",
            difficulty=MissionDifficulty.HERO,
            time_limit_ticks=5400,
            objectives=[
                MissionObjectiveDef(
                    objective_type=MissionObjective.CAPTURE_LOCATION,
                    description="Seize the Nijmegen Road Bridge",
                    position=(14, 12),
                    radius=2,
                ),
                MissionObjectiveDef(
                    objective_type=MissionObjective.SURVIVE_FOR_TIME,
                    description="Hold until relieved",
                    time_limit_ticks=5400,
                ),
            ],
            ally_unit_templates=[
                {"unit_type": "INFANTRY_SQUAD", "position": (4, 19)},
                {"unit_type": "INFANTRY_SQUAD", "position": (6, 19)},
                {"unit_type": "INFANTRY_SQUAD", "position": (5, 21)},
                {"unit_type": "MACHINE_GUN_SQUAD", "position": (4, 21)},
                {"unit_type": "MACHINE_GUN_SQUAD", "position": (7, 20)},
                {"unit_type": "SNIPER_TEAM", "position": (3, 20)},
                {"unit_type": "TANK", "position": (6, 22)},
                {"unit_type": "COMMANDER", "position": (5, 20)},
            ],
            enemy_unit_templates=[
                {"unit_type": "INFANTRY_SQUAD", "position": (21, 3)},
                {"unit_type": "INFANTRY_SQUAD", "position": (24, 3)},
                {"unit_type": "INFANTRY_SQUAD", "position": (22, 5)},
                {"unit_type": "INFANTRY_SQUAD", "position": (25, 5)},
                {"unit_type": "MACHINE_GUN_SQUAD", "position": (22, 4)},
                {"unit_type": "MACHINE_GUN_SQUAD", "position": (24, 4)},
                {"unit_type": "TANK", "position": (23, 2)},
                {"unit_type": "TANK", "position": (25, 3)},
                {"unit_type": "SNIPER_TEAM", "position": (26, 4)},
                {"unit_type": "COMMANDER", "position": (24, 3)},
            ],
            brief_text="20 September. The Waal River at Nijmegen is wide and deadly. British Grenadiers will make a daylight assault crossing in rubber boats while your units provide covering fire from the south bank. The bridge must be taken before German armor arrives in strength. This will be costly.",
        )
    )

    mgr.register_mission(
        MissionDefinition(
            id="mission_10_arnhem",
            name="Arnhem — A Bridge Too Far",
            description="The final desperate stand. Hold or evacuate at all costs.",
            map_id="arnhem",
            difficulty=MissionDifficulty.HERO,
            time_limit_ticks=9000,
            weather="overcast",
            objectives=[
                MissionObjectiveDef(
                    objective_type=MissionObjective.DEFEND_POSITION,
                    description="Defend the bridge perimeter",
                    position=(15, 10),
                    radius=4,
                    time_limit_ticks=9000,
                ),
                MissionObjectiveDef(
                    objective_type=MissionObjective.SURVIVE_FOR_TIME,
                    description="Survive until relief arrives",
                    time_limit_ticks=9000,
                ),
                MissionObjectiveDef(
                    objective_type=MissionObjective.ESCORT_UNIT,
                    description="Protect the division command post",
                ),
            ],
            ally_unit_templates=[
                {"unit_type": "INFANTRY_SQUAD", "position": (2, 23)},
                {"unit_type": "INFANTRY_SQUAD", "position": (4, 23)},
                {"unit_type": "INFANTRY_SQUAD", "position": (2, 25)},
                {"unit_type": "INFANTRY_SQUAD", "position": (4, 25)},
                {"unit_type": "MACHINE_GUN_SQUAD", "position": (3, 22)},
                {"unit_type": "MACHINE_GUN_SQUAD", "position": (5, 24)},
                {"unit_type": "SNIPER_TEAM", "position": (2, 22)},
                {"unit_type": "MORTAR_TEAM", "position": (6, 23)},
                {"unit_type": "MEDIC_TEAM", "position": (4, 24)},
                {"unit_type": "COMMANDER", "position": (3, 24)},
            ],
            enemy_unit_templates=[
                {"unit_type": "INFANTRY_SQUAD", "position": (25, 2)},
                {"unit_type": "INFANTRY_SQUAD", "position": (27, 2)},
                {"unit_type": "INFANTRY_SQUAD", "position": (26, 4)},
                {"unit_type": "INFANTRY_SQUAD", "position": (28, 4)},
                {"unit_type": "INFANTRY_SQUAD", "position": (27, 6)},
                {"unit_type": "MACHINE_GUN_SQUAD", "position": (25, 3)},
                {"unit_type": "MACHINE_GUN_SQUAD", "position": (28, 3)},
                {"unit_type": "MACHINE_GUN_SQUAD", "position": (26, 5)},
                {"unit_type": "TANK", "position": (26, 1)},
                {"unit_type": "TANK", "position": (28, 2)},
                {"unit_type": "TANK", "position": (27, 4)},
                {"unit_type": "SNIPER_TEAM", "position": (25, 5)},
                {"unit_type": "SNIPER_TEAM", "position": (28, 5)},
                {"unit_type": "COMMANDER", "position": (27, 3)},
            ],
            brief_text="21-25 September. 'A Bridge Too Far.' The British 1st Airborne Division is surrounded at Arnhem. Their perimeter is shrinking daily. German armor including Tiger tanks pounds their positions. You must hold the bridge area at all costs, hoping against hope that XXX Corps will break through. If relief doesn't come, you must organize a fighting evacuation across the Rhine under cover of darkness. Many will not make it. This is the bitter end of Market Garden — but your courage may yet save honor.",
        )
    )

    return mgr
