"""Commander AI that builds a battlefield picture and issues tactical orders."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING

from pycc2.domain.value_objects.tile_coord import TileCoord

if TYPE_CHECKING:
    from pycc2.domain.ai.tactic_intent import TacticIntent, TacticType
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Unit


class CommanderRole(Enum):
    """Scope of command authority for a commander unit."""

    OVERALL = auto()
    SQUAD_LEADER = auto()


class ThreatLevel(Enum):
    """Graduated threat assessment tiers."""

    NONE = auto()
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    CRITICAL = auto()


@dataclass(slots=True)
class BattlefieldPicture:
    """Aggregated snapshot of allied and enemy dispositions for decision making."""

    ally_count: int = 0
    ally_average_health: float = 1.0
    ally_positions: list[TileCoord] = field(default_factory=list)
    ally_squads: dict[str, list[str]] = field(default_factory=dict)
    suppressed_allies: list[str] = field(default_factory=list)
    enemy_count: int = 0
    enemy_positions: list[TileCoord] = field(default_factory=list)
    enemy_threats: list[tuple[str, float]] = field(default_factory=list)
    strongest_enemy_pos: TileCoord | None = None
    weakest_enemy_pos: TileCoord | None = None
    estimated_enemy_strength: float = 0.0
    key_terrain: list[TileCoord] = field(default_factory=list)
    cover_positions: list[TileCoord] = field(default_factory=list)
    threat_level: ThreatLevel = ThreatLevel.NONE
    force_ratio: float = 1.0
    front_line_center: TileCoord | None = None
    recommended_action: str = "hold"


@dataclass(slots=True)
class CommanderOrder:
    """Issued order targeting units with a tactic, priority, and expiry."""

    order_id: str
    commander_id: str
    target_unit_ids: list[str]
    order_type: TacticType
    priority: int = 5
    target_position: TileCoord | None = None
    target_unit_id: str | None = None
    reasoning: str = ""
    expires_in_ticks: int = -1
    _created_tick: int = field(default=0, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_created_tick", 0)

    @property
    def created_tick(self) -> int:
        """Return the tick at which this order was created."""
        return self._created_tick

    def set_created_tick(self, tick: int) -> None:
        """Set the creation tick used for expiry tracking."""
        object.__setattr__(self, "_created_tick", tick)

    def is_expired(self, current_tick: int) -> bool:
        """Return whether the order has expired relative to the current tick."""
        if self.expires_in_ticks == -1:
            return False
        return current_tick - self._created_tick >= self.expires_in_ticks


_UNIT_TYPE_FIRE_POWER: dict[int, float] = {}
_TYPE_CHECKING_DONE = False


def _get_fire_power(unit_type_int: int) -> float:
    global _UNIT_TYPE_FIRE_POWER, _TYPE_CHECKING_DONE
    if not _TYPE_CHECKING_DONE:
        from pycc2.domain.entities.unit import UnitType

        _UNIT_TYPE_FIRE_POWER = {
            UnitType.INFANTRY_SQUAD.value: 1.0,
            UnitType.MACHINE_GUN_SQUAD.value: 2.5,
            UnitType.COMMANDER.value: 1.5,
            UnitType.AT_GUN_TEAM.value: 3.0,
            UnitType.MORTAR_TEAM.value: 2.0,
        }
        _TYPE_CHECKING_DONE = True
    return _UNIT_TYPE_FIRE_POWER.get(unit_type_int, 1.0)


class CommanderAI:
    """Builds a battlefield picture from reports and issues tactical orders to subordinates."""

    def __init__(
        self,
        commander_unit: Unit,
        role: CommanderRole = CommanderRole.OVERALL,
    ) -> None:
        """Initialize the commander with its unit, command role, and empty battlefield picture."""
        self._commander = commander_unit
        self._role = role
        self._picture = BattlefieldPicture()
        self._pending_orders: list[CommanderOrder] = []
        self._order_history: list[CommanderOrder] = []
        self._last_assessment_tick: int = 0
        self._assessment_interval: int = 30
        self._current_directive: str = "hold"
        self._order_tick_counter: int = 0

    @property
    def commander(self) -> Unit:
        """Return the commander unit driving this AI."""
        return self._commander

    @property
    def picture(self) -> BattlefieldPicture:
        """Return the latest aggregated battlefield picture."""
        return self._picture

    @property
    def role(self) -> CommanderRole:
        """Return the command role scope of this commander."""
        return self._role

    def assess_battlefield(
        self,
        all_units: list[Unit],
        game_map: GameMap,
        current_tick: int,
    ) -> BattlefieldPicture:
        """Aggregate allied and enemy dispositions into a fresh battlefield picture."""

        pic = BattlefieldPicture()
        my_faction = self._commander.faction
        cmd_pos = self._commander.position.tile_coord

        allies = [u for u in all_units if u.faction == my_faction and u.is_alive]
        enemies = [u for u in all_units if u.faction != my_faction and u.is_alive]

        pic.ally_count = len(allies)
        pic.enemy_count = len(enemies)
        pic.ally_positions = [u.position.tile_coord for u in allies]
        pic.enemy_positions = [u.position.tile_coord for u in enemies]

        if allies:
            pic.ally_average_health = sum(u.health.hp_ratio for u in allies) / len(allies)

        squad_map: dict[str, list[str]] = {}
        for u in allies:
            sid = u.squad_id or "unassigned"
            squad_map.setdefault(sid, []).append(u.id)
        pic.ally_squads = squad_map

        pic.suppressed_allies = [u.id for u in allies if not u.morale.is_combat_effective]

        threat_list: list[tuple[str, float]] = []
        strongest_score = -1.0
        weakest_score = float("inf")
        strongest_pos = None
        weakest_pos = None
        total_enemy_str = 0.0

        for e in enemies:
            dist = max(e.position.tile_coord.chebyshev_distance(cmd_pos), 1)
            score = self.calculate_threat_score(e, dist)
            threat_list.append((e.id, score))
            total_enemy_str += score
            if score > strongest_score:
                strongest_score = score
                strongest_pos = e.position.tile_coord
            if score < weakest_score:
                weakest_score = score
                weakest_pos = e.position.tile_coord

        pic.enemy_threats = sorted(threat_list, key=lambda t: t[1], reverse=True)
        pic.strongest_enemy_pos = strongest_pos
        pic.weakest_enemy_pos = weakest_pos
        pic.estimated_enemy_strength = total_enemy_str

        ally_str = sum(_get_fire_power(u.unit_type.value) * u.health.hp_ratio for u in allies)
        enemy_str = total_enemy_str if total_enemy_str > 0 else 1e-6
        pic.force_ratio = ally_str / enemy_str

        pic.threat_level = self._determine_threat_level(
            pic.force_ratio, pic.ally_average_health, len(enemies)
        )

        if pic.ally_positions and pic.enemy_positions:
            ax = sum(p.x for p in pic.ally_positions) / len(pic.ally_positions)
            ay = sum(p.y for p in pic.ally_positions) / len(pic.ally_positions)
            ex = sum(p.x for p in pic.enemy_positions) / len(pic.enemy_positions)
            ey = sum(p.y for p in pic.enemy_positions) / len(pic.enemy_positions)
            fcx = int((ax + ex) / 2)
            fcy = int((ay + ey) / 2)
            pic.front_line_center = TileCoord(fcx, fcy)

        pic.key_terrain = self._find_key_terrain(game_map)
        pic.cover_positions = self._find_cover_positions(game_map, cmd_pos, radius=8)

        pic.recommended_action = self._recommend_action(pic)

        self._picture = pic
        self._last_assessment_tick = current_tick
        return pic

    def _determine_threat_level(
        self,
        force_ratio: float,
        avg_health: float,
        enemy_count: int,
    ) -> ThreatLevel:
        if force_ratio < 0.5 or avg_health < 0.3:
            return ThreatLevel.CRITICAL
        if force_ratio < 0.8 or enemy_count > 2:
            return ThreatLevel.HIGH
        if 0.8 <= force_ratio <= 1.2 or 1 <= enemy_count <= 2:
            return ThreatLevel.MEDIUM
        if force_ratio > 1.2 and enemy_count == 0:
            return ThreatLevel.LOW
        return ThreatLevel.NONE

    def _find_key_terrain(self, game_map: GameMap) -> list[TileCoord]:
        from pycc2.domain.value_objects.terrain_type import TerrainType

        key: list[TileCoord] = []
        w, h = game_map.width, game_map.height
        for y in range(h):
            for x in range(w):
                tc = TileCoord(x, y)
                tt = game_map.get_terrain(tc)
                if (
                    tt in (TerrainType.BUILDING_SOLID, TerrainType.BRIDGE)
                    or tt == TerrainType.WOODS
                    and len(key) < 10
                ):
                    key.append(tc)
        return key[:15]

    def _find_cover_positions(
        self,
        game_map: GameMap,
        center: TileCoord,
        radius: int = 8,
    ) -> list[TileCoord]:
        from pycc2.domain.value_objects.terrain_type import TerrainType

        covers: list[TileCoord] = []
        cover_types = {
            TerrainType.WOODS,
            TerrainType.BUILDING_ENTERABLE,
            TerrainType.BUILDING_SOLID,
            TerrainType.HEDGE,
            TerrainType.ROUGH,
        }
        for y in range(center.y - radius, center.y + radius + 1):
            for x in range(center.x - radius, center.x + radius + 1):
                tc = TileCoord(x, y)
                if not game_map.is_within_bounds(tc):
                    continue
                if game_map.get_terrain(tc) in cover_types:
                    covers.append(tc)
        return covers[:20]

    def _recommend_action(self, pic: BattlefieldPicture) -> str:
        tl = pic.threat_level
        if tl == ThreatLevel.CRITICAL:
            return "retreat"
        if tl == ThreatLevel.HIGH:
            return "defend" if pic.force_ratio > 0.7 else "retreat"
        if tl == ThreatLevel.MEDIUM:
            return "attack" if pic.force_ratio > 1.0 else "defend"
        return "hold"

    def generate_orders(
        self,
        managed_unit_ids: list[str],
        all_units: list[Unit],
        squad_coordinator: SquadCoordinator | None = None,
        difficulty_config: DifficultyConfig | None = None,
    ) -> list[CommanderOrder]:
        """Generate tactical orders for managed units based on the current battlefield picture."""
        aggressiveness = 0.5
        if difficulty_config is not None:
            aggressiveness = getattr(difficulty_config, "aggressiveness", 0.5)

        pic = self._picture
        orders: list[CommanderOrder] = []
        self._order_tick_counter += 1

        managed = [u for u in all_units if u.id in managed_unit_ids and u.is_alive]
        mg_units = [u for u in managed if u.unit_type.value == 2]
        infantry = [u for u in managed if u.unit_type.value == 1 and u.id != self._commander.id]
        low_hp = [u for u in managed if u.health.hp_ratio < 0.35]
        cmd_units = (
            [u for u in managed if u.id == self._commander.id]
            if self._commander.id in managed_unit_ids
            else []
        )

        tl = pic.threat_level
        fr = pic.force_ratio

        if tl == ThreatLevel.CRITICAL:
            self._orders_for_critical(managed, mg_units, infantry, low_hp, pic, orders)
        elif tl == ThreatLevel.HIGH:
            self._orders_for_high(managed, mg_units, infantry, pic, orders, squad_coordinator, fr)
        elif tl == ThreatLevel.MEDIUM:
            self._orders_for_medium(managed, mg_units, infantry, pic, orders, aggressiveness)
        else:
            self._orders_for_low_or_none(managed, cmd_units, pic, orders)

        self._apply_low_hp_cover_order(low_hp, orders, tl)

        for o in orders:
            o.set_created_tick(self._order_tick_counter)

        self._pending_orders.extend(orders)
        self._order_history.extend(orders)
        return orders

    def _orders_for_critical(
        self,
        managed: list[Unit],
        mg_units: list[Unit],
        infantry: list[Unit],
        low_hp: list[Unit],
        pic: BattlefieldPicture,
        orders: list[CommanderOrder],
    ) -> None:
        """Issue orders for the CRITICAL threat level: regroup wounded and hold the line."""
        from pycc2.domain.ai.tactic_intent import TacticType

        rally = self._get_rally_point(pic)
        if low_hp:
            orders.append(
                self._make_order(
                    [u.id for u in low_hp],
                    TacticType.REGROUP,
                    priority=9,
                    target_position=rally,
                    reasoning="Critical threat – regroup wounded units",
                )
            )
        remaining = [u for u in managed if u not in low_hp]
        if remaining:
            orders.append(
                self._make_order(
                    [u.id for u in remaining],
                    TacticType.DEFEND,
                    priority=8,
                    reasoning="Critical threat – hold defensive line",
                )
            )

    def _orders_for_high(
        self,
        managed: list[Unit],
        mg_units: list[Unit],
        infantry: list[Unit],
        pic: BattlefieldPicture,
        orders: list[CommanderOrder],
        squad_coordinator: SquadCoordinator | None,
        fr: float,
    ) -> None:
        """Issue orders for the HIGH threat level based on the force ratio."""
        from pycc2.domain.ai.tactic_intent import TacticType

        if fr > 0.7:
            if mg_units:
                target_eid = pic.enemy_threats[0][0] if pic.enemy_threats else None
                orders.append(
                    self._make_order(
                        [u.id for u in mg_units],
                        TacticType.SUPPRESS_FIRE,
                        priority=7,
                        target_unit_id=target_eid,
                        reasoning="Suppress highest-threat enemy",
                    )
                )
            if infantry:
                orders.append(
                    self._make_order(
                        [u.id for u in infantry],
                        TacticType.HOLD_POSITION,
                        priority=6,
                        reasoning="Provide covering fire while MG suppresses",
                    )
                )
            if squad_coordinator is not None and pic.weakest_enemy_pos:
                mobile = [u for u in managed if u not in mg_units][:2]
                if mobile:
                    orders.append(
                        self._make_order(
                            [u.id for u in mobile],
                            TacticType.FLANKING
                            if hasattr(TacticType, "FLANKING")
                            else TacticType.ATTACK,
                            priority=5,
                            target_position=pic.weakest_enemy_pos,
                            reasoning="Flank weakest enemy position",
                        )
                    )
        else:
            rally = self._get_rally_point(pic)
            orders.append(
                self._make_order(
                    [u.id for u in managed],
                    TacticType.RETREAT,
                    priority=8,
                    target_position=rally,
                    reasoning="Outnumbered – ordered retreat",
                )
            )

    def _orders_for_medium(
        self,
        managed: list[Unit],
        mg_units: list[Unit],
        infantry: list[Unit],
        pic: BattlefieldPicture,
        orders: list[CommanderOrder],
        aggressiveness: float,
    ) -> None:
        """Issue orders for the MEDIUM threat level based on aggressiveness."""
        from pycc2.domain.ai.tactic_intent import TacticType

        if aggressiveness > 0.5 and pic.weakest_enemy_pos:
            if infantry:
                orders.append(
                    self._make_order(
                        [u.id for u in infantry[:3]],
                        TacticType.ATTACK,
                        priority=6,
                        target_position=pic.weakest_enemy_pos,
                        reasoning="Concentrate fire on weakest enemy",
                    )
                )
            if mg_units and pic.enemy_threats:
                orders.append(
                    self._make_order(
                        [u.id for u in mg_units],
                        TacticType.SUPPRESS_FIRE,
                        priority=5,
                        target_unit_id=pic.enemy_threats[1][0]
                        if len(pic.enemy_threats) > 1
                        else pic.enemy_threats[0][0],
                        reasoning="Suppress secondary threats",
                    )
                )
        else:
            if pic.cover_positions:
                orders.append(
                    self._make_order(
                        [u.id for u in managed[:4]],
                        TacticType.DEFEND,
                        priority=6,
                        target_position=pic.cover_positions[0],
                        reasoning="Take up defensive positions on favorable terrain",
                    )
                )
            rest = [u for u in managed if u not in (infantry[:4] if infantry else [])]
            if rest:
                orders.append(
                    self._make_order(
                        [u.id for u in rest],
                        TacticType.PATROL,
                        priority=3,
                        reasoning="Maintain patrol while others defend",
                    )
                )

    def _orders_for_low_or_none(
        self,
        managed: list[Unit],
        cmd_units: list[Unit],
        pic: BattlefieldPicture,
        orders: list[CommanderOrder],
    ) -> None:
        """Issue orders for LOW/NONE threat levels: advance patrol and secure key terrain."""
        from pycc2.domain.ai.tactic_intent import TacticType

        if managed:
            orders.append(
                self._make_order(
                    [u.id for u in managed[: len(managed) // 2 + 1]],
                    TacticType.PATROL,
                    priority=3,
                    reasoning="Advance patrol – low threat environment",
                )
            )
        if pic.key_terrain and cmd_units:
            orders.append(
                self._make_order(
                    [u.id for u in cmd_units],
                    TacticType.HOLD_POSITION,
                    priority=4,
                    target_position=pic.key_terrain[0],
                    reasoning="Secure key terrain feature",
                )
            )

    def _apply_low_hp_cover_order(
        self,
        low_hp: list[Unit],
        orders: list[CommanderOrder],
        tl: ThreatLevel,
    ) -> None:
        """Append a TAKE_COVER order for low-HP units outside CRITICAL threat."""
        from pycc2.domain.ai.tactic_intent import TacticType

        if low_hp and tl not in (ThreatLevel.CRITICAL,):
            already_regroup = {
                uid
                for o in orders
                for uid in o.target_unit_ids
                if o.order_type == TacticType.REGROUP
            }
            needs_cover = [u for u in low_hp if u.id not in already_regroup]
            if needs_cover:
                orders.append(
                    self._make_order(
                        [u.id for u in needs_cover],
                        TacticType.TAKE_COVER,
                        priority=7,
                        reasoning="Low-health units should take cover",
                    )
                )

    def _get_rally_point(self, pic: BattlefieldPicture) -> TileCoord | None:
        if pic.cover_positions:
            return pic.cover_positions[0]
        if pic.ally_positions:
            return pic.ally_positions[0]
        return self._commander.position.tile_coord

    def _make_order(
        self,
        target_unit_ids: list[str],
        order_type: TacticType,
        priority: int = 5,
        target_position: TileCoord | None = None,
        target_unit_id: str | None = None,
        reasoning: str = "",
        expires_in_ticks: int = -1,
    ) -> CommanderOrder:
        return CommanderOrder(
            order_id=str(uuid.uuid4())[:8],
            commander_id=self._commander.id,
            target_unit_ids=target_unit_ids,
            order_type=order_type,
            priority=priority,
            target_position=target_position,
            target_unit_id=target_unit_id,
            reasoning=reasoning,
            expires_in_ticks=expires_in_ticks,
        )

    def get_pending_orders_for_unit(self, unit_id: str) -> list[CommanderOrder]:
        """Return pending orders whose target unit list includes the given unit id."""
        return [o for o in self._pending_orders if unit_id in o.target_unit_ids]

    def expire_old_orders(self, current_tick: int) -> None:
        """Remove orders from the pending list that have expired at current_tick."""
        surviving = [o for o in self._pending_orders if not o.is_expired(current_tick)]
        self._pending_orders = surviving

    def convert_to_unit_intents(self, orders: list[CommanderOrder]) -> list[TacticIntent]:
        """Convert commander orders into per-unit tactic intents."""
        from pycc2.domain.ai.tactic_intent import TacticIntent

        intents: list[TacticIntent] = []
        for o in orders:
            for uid in o.target_unit_ids:
                intent = TacticIntent(
                    unit_id=uid,
                    tactic_type=o.order_type,
                    priority=o.priority,
                    target_position=o.target_position,
                    target_unit_id=o.target_unit_id,
                )
                intents.append(intent)
        return intents

    @staticmethod
    def calculate_threat_score(unit: Unit, distance_to_commander: float) -> float:
        """Compute a threat score for an enemy based on fire power, distance, and health."""
        dist_factor = 1.0 / max(distance_to_commander, 1)
        fire_power = _get_fire_power(unit.unit_type.value)
        health_factor = unit.health.hp_ratio
        return fire_power * dist_factor * (0.5 + 0.5 * health_factor)


class TacticalAdvisor:
    """Stateless helper proposing attack vectors and positions from the battlefield map."""

    @staticmethod
    def suggest_attack_vector(
        commander_pos: TileCoord,
        enemy_positions: list[TileCoord],
        game_map: GameMap,
        ally_positions: list[TileCoord],
    ) -> list[TileCoord]:
        """Suggest a step path toward the most attackable enemy position."""
        if not enemy_positions:
            return []

        best_target = min(
            enemy_positions,
            key=lambda ep: sum(1 for ap in ally_positions if game_map.has_line_of_sight(ap, ep)),
        )
        path = [commander_pos]
        current = commander_pos
        dx = 1 if best_target.x > current.x else (-1 if best_target.x < current.x else 0)
        dy = 1 if best_target.y > current.y else (-1 if best_target.y < current.y else 0)
        for _ in range(min(current.chebyshev_distance(best_target), 12)):
            next_tc = TileCoord(current.x + dx, current.y + dy)
            if game_map.is_within_bounds(next_tc):
                path.append(next_tc)
            current = next_tc
            if current == best_target:
                break
        return path

    @staticmethod
    def suggest_defensive_positions(
        fallback_point: TileCoord,
        unit_count: int,
        game_map: GameMap,
    ) -> list[TileCoord]:
        """Suggest cover terrain positions near the fallback point for the given unit count."""
        from pycc2.domain.value_objects.terrain_type import TerrainType

        cover_types = {
            TerrainType.WOODS,
            TerrainType.BUILDING_ENTERABLE,
            TerrainType.BUILDING_SOLID,
            TerrainType.HEDGE,
            TerrainType.ROUGH,
        }
        candidates: list[TileCoord] = []
        r = max(unit_count + 2, 5)
        for y in range(fallback_point.y - r, fallback_point.y + r + 1):
            for x in range(fallback_point.x - r, fallback_point.x + r + 1):
                tc = TileCoord(x, y)
                if not game_map.is_within_bounds(tc):
                    continue
                if game_map.get_terrain(tc) in cover_types:
                    candidates.append(tc)
        candidates.sort(key=lambda c: c.chebyshev_distance(fallback_point))
        return candidates[:unit_count]

    @staticmethod
    def suggest_retreat_route(
        unit_pos: TileCoord,
        safe_zone: TileCoord,
        game_map: GameMap,
        enemy_positions: list[TileCoord],
    ) -> list[TileCoord]:
        """Suggest a retreat route from unit_pos to safe_zone avoiding enemy line of sight."""
        route = [unit_pos]
        current = unit_pos
        for _ in range(current.manhattan_distance(safe_zone)):
            neighbors = sorted(
                current.neighbors_8,
                key=lambda n: (
                    n.manhattan_distance(safe_zone),
                    sum(1 for e in enemy_positions if game_map.has_line_of_sight(n, e)),
                ),
            )
            best = next((n for n in neighbors if game_map.is_passable(n)), None)
            if best is None or best == safe_zone:
                break
            route.append(best)
            current = best
            if current == safe_zone:
                break
        if safe_zone not in route:
            route.append(safe_zone)
        return route

    @staticmethod
    def optimize_fire_allocation(
        allies: list[Unit],
        enemies: list[Unit],
    ) -> dict[str, str]:
        """Return a mapping of ally unit id to best assigned enemy target id."""
        allocation: dict[str, str] = {}
        if not allies or not enemies:
            return allocation

        enemy_values: dict[str, float] = {}
        for e in enemies:
            ev = _get_fire_power(e.unit_type.value) * e.health.hp_ratio
            enemy_values[e.id] = ev

        assigned_targets: set[str] = set()
        for a in sorted(allies, key=lambda u: _get_fire_power(u.unit_type.value), reverse=True):
            best_target_id = None
            best_efficiency = -1.0
            apos = a.position.tile_coord
            for e in enemies:
                if e.id in assigned_targets:
                    continue
                dist = max(apos.chebyshev_distance(e.position.tile_coord), 1)
                efficiency = enemy_values.get(e.id, 1.0) / dist
                if efficiency > best_efficiency:
                    best_efficiency = efficiency
                    best_target_id = e.id
            if best_target_id:
                allocation[a.id] = best_target_id
                assigned_targets.add(best_target_id)
        return allocation


if TYPE_CHECKING:
    from pycc2.domain.ai.difficulty_system import DifficultyConfig
    from pycc2.domain.ai.squad_coordinator import SquadCoordinator
