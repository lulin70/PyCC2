"""Communication System — CC2-Authentic Radio Communication Simulation

Simulates radio communication delays and failures between command
elements and frontline units. In CC2, communication is critical for
coordinating attacks, calling artillery, and maintaining unit cohesion.

Components:
  1. CommunicationSystem  — Manages radio networks and message delivery
  2. CommunicationRelay   — Handles message relay through officers

Radio types:
  - HQ: unlimited range, 0 delay
  - Officer: 15 tile range, 1 tick delay
  - Infantry squad: 8 tile range, 2 tick delay (must relay through officer)

Communication effects:
  - Orders to units beyond radio range: +5 tick delay (runner must be sent)
  - Radio interference: RAIN/FOG adds +2 tick delay
  - Artillery call-in requires officer with radio in range of HQ
  - If officer killed, squad loses radio contact (becomes autonomous)

CommunicationRelay:
  - If squad has no radio contact, nearest officer can relay
  - Relay adds +3 tick delay per hop
  - Max 2 hops (beyond that, order lost)

Integration:
  - Modify CommanderAI to check communication before issuing orders
  - Modify TacticExecutor to add delay based on communication status
  - Units without comms operate on last received orders + autonomous behavior
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

from pycc2.domain.ai.tactic_intent import TacticIntent
from pycc2.domain.entities.unit import UnitType

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit
    from pycc2.domain.systems.environment import EnvironmentState

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HQ_RADIO_RANGE: int = 999  # Unlimited range
HQ_RADIO_DELAY: int = 0  # No delay

OFFICER_RADIO_RANGE: int = 15  # 15 tile range
OFFICER_RADIO_DELAY: int = 1  # 1 tick delay

SQUAD_RADIO_RANGE: int = 8  # 8 tile range
SQUAD_RADIO_DELAY: int = 2  # 2 tick delay

RUNNER_DELAY: int = 5  # +5 ticks when out of radio range
RELAY_DELAY_PER_HOP: int = 3  # +3 ticks per relay hop
MAX_RELAY_HOPS: int = 2  # Max 2 hops before order is lost

WEATHER_DELAY: int = 2  # +2 ticks in RAIN/FOG

# Unit types with radio capabilities
_OFFICER_TYPES: set[UnitType] = {UnitType.COMMANDER}
_SQUAD_TYPES: set[UnitType] = {
    UnitType.INFANTRY_SQUAD,
    UnitType.MACHINE_GUN_SQUAD,
    UnitType.SNIPER_TEAM,
    UnitType.MEDIC_TEAM,
    UnitType.AT_GUN_TEAM,
    UnitType.MORTAR_TEAM,
}


# ---------------------------------------------------------------------------
# Radio type
# ---------------------------------------------------------------------------


class RadioType(Enum):
    HQ = auto()  # Commander/HQ — unlimited range
    OFFICER = auto()  # Officer with radio — 15 tile range
    SQUAD = auto()  # Infantry squad radio — 8 tile range
    NONE = auto()  # No radio — must use runner


# ---------------------------------------------------------------------------
# Communication status
# ---------------------------------------------------------------------------


class CommStatus(Enum):
    DIRECT = auto()  # Direct radio contact with HQ
    RELAYED = auto()  # Contact via relay through officer
    RUNNER = auto()  # No radio — runner being sent
    LOST = auto()  # Communication lost (order not delivered)
    AUTONOMOUS = auto()  # Operating without comms (last orders + BT)


# ---------------------------------------------------------------------------
# Pending message
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class CommMessage:
    """A message (order) being transmitted through the comm system."""

    message_id: str
    sender_id: str  # Unit sending the order (usually HQ/officer)
    recipient_id: str  # Unit receiving the order
    intent: TacticIntent
    total_delay: int  # Total ticks before delivery
    ticks_remaining: int  # Ticks until delivery
    status: CommStatus = CommStatus.DIRECT
    relay_hops: int = 0  # Number of relay hops

    @property
    def is_delivered(self) -> bool:
        return self.ticks_remaining <= 0

    @property
    def is_lost(self) -> bool:
        return self.status == CommStatus.LOST


# ---------------------------------------------------------------------------
# Unit comm state
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class UnitCommState:
    """Communication state for a single unit."""

    unit_id: str
    radio_type: RadioType
    has_contact: bool = True  # Whether unit has radio contact
    last_contact_tick: int = 0  # Last tick with confirmed contact
    last_orders: TacticIntent | None = None  # Last received orders
    autonomous: bool = False  # Whether operating autonomously

    @property
    def can_transmit(self) -> bool:
        return self.radio_type != RadioType.NONE and self.has_contact


# ---------------------------------------------------------------------------
# CommunicationRelay
# ---------------------------------------------------------------------------


class CommunicationRelay:
    """Handles message relay through officer units.

    When a squad has no direct radio contact with HQ, the nearest
    officer can relay the message. Each relay hop adds delay.
    """

    def __init__(self) -> None:
        self._logger = logging.getLogger("pycc2.ai.comm_relay")

    def find_relay_path(
        self,
        sender: Unit,
        recipient: Unit,
        officers: list[Unit],
        all_units: list[Unit],
    ) -> list[Unit]:
        """Find a relay path from sender to recipient through officers.

        Returns a list of relay nodes (officers) in order.
        Max 2 hops (3 nodes: sender -> officer1 -> officer2 -> recipient).
        """
        if not officers:
            return []

        recipient_pos = recipient.position.tile_coord
        sender_pos = sender.position.tile_coord

        # Try direct relay: sender -> officer -> recipient
        for officer in officers:
            if not officer.is_alive:
                continue
            off_pos = officer.position.tile_coord

            # Officer must be in range of both sender and recipient
            sender_dist = sender_pos.chebyshev_distance(off_pos)
            recipient_dist = recipient_pos.chebyshev_distance(off_pos)

            if sender_dist <= OFFICER_RADIO_RANGE and recipient_dist <= OFFICER_RADIO_RANGE:
                return [officer]

        # Try 2-hop relay: sender -> officer1 -> officer2 -> recipient
        if len(officers) >= 2:
            for o1 in officers:
                if not o1.is_alive:
                    continue
                o1_pos = o1.position.tile_coord
                sender_dist = sender_pos.chebyshev_distance(o1_pos)
                if sender_dist > OFFICER_RADIO_RANGE:
                    continue

                for o2 in officers:
                    if o2 is o1 or not o2.is_alive:
                        continue
                    o2_pos = o2.position.tile_coord

                    # o1 must reach o2, o2 must reach recipient
                    o1_o2_dist = o1_pos.chebyshev_distance(o2_pos)
                    o2_recip_dist = o2_pos.chebyshev_distance(recipient_pos)

                    if o1_o2_dist <= OFFICER_RADIO_RANGE and o2_recip_dist <= OFFICER_RADIO_RANGE:
                        return [o1, o2]

        return []

    def calculate_relay_delay(self, hops: int) -> int:
        """Calculate additional delay from relay hops."""
        return hops * RELAY_DELAY_PER_HOP


# ---------------------------------------------------------------------------
# CommunicationSystem
# ---------------------------------------------------------------------------


class CommunicationSystem:
    """Manages radio communication between all units.

    Responsibilities:
      - Track radio contact status for each unit
      - Calculate message delivery delays
      - Process message queue (advance delivery each tick)
      - Handle communication loss when officers are killed
      - Apply weather interference effects
    """

    def __init__(self) -> None:
        self._unit_states: dict[str, UnitCommState] = {}
        self._message_queue: list[CommMessage] = []
        self._relay = CommunicationRelay()
        self._hq_id: str | None = None
        self._message_counter: int = 0
        self._logger = logging.getLogger("pycc2.ai.comm_system")

    @property
    def message_queue(self) -> list[CommMessage]:
        return list(self._message_queue)

    @property
    def unit_states(self) -> dict[str, UnitCommState]:
        return dict(self._unit_states)

    def register_unit(self, unit: Unit) -> None:
        """Register a unit with the communication system."""
        radio_type = self._determine_radio_type(unit)
        state = UnitCommState(
            unit_id=unit.id,
            radio_type=radio_type,
        )
        self._unit_states[unit.id] = state

        # Track HQ
        if radio_type == RadioType.HQ:
            self._hq_id = unit.id

    def unregister_unit(self, unit_id: str) -> None:
        """Remove a unit from the communication system."""
        self._unit_states.pop(unit_id, None)
        if self._hq_id == unit_id:
            self._hq_id = None

    def send_order(
        self,
        sender: Unit,
        recipient: Unit,
        intent: TacticIntent,
        all_units: list[Unit],
        environment: EnvironmentState | None = None,
    ) -> CommMessage:
        """Send an order from one unit to another through the comm system.

        Calculates delay based on radio type, distance, relay hops,
        and weather conditions.
        """
        sender_state = self._unit_states.get(sender.id)
        recipient_state = self._unit_states.get(recipient.id)

        if sender_state is None:
            self.register_unit(sender)
            sender_state = self._unit_states[sender.id]
        if recipient_state is None:
            self.register_unit(recipient)
            recipient_state = self._unit_states[recipient.id]

        # Calculate base delay and status
        delay, status, hops = self._calculate_comm(
            sender, recipient, sender_state, recipient_state, all_units
        )

        # Apply weather interference
        if environment is not None:
            from pycc2.domain.systems.environment import WeatherCondition

            if environment.weather in (WeatherCondition.RAIN, WeatherCondition.FOG):
                delay += WEATHER_DELAY

        # Create message
        self._message_counter += 1
        message = CommMessage(
            message_id=f"msg_{self._message_counter}",
            sender_id=sender.id,
            recipient_id=recipient.id,
            intent=intent,
            total_delay=delay,
            ticks_remaining=delay,
            status=status,
            relay_hops=hops,
        )
        self._message_queue.append(message)

        self._logger.debug(
            f"Order sent: {sender.id} -> {recipient.id}, "
            f"status={status.name}, delay={delay} ticks, hops={hops}"
        )

        return message

    def tick(self) -> list[CommMessage]:
        """Advance all pending messages by one tick.

        Returns list of messages that were delivered this tick.
        """
        delivered: list[CommMessage] = []

        for msg in self._message_queue:
            msg.ticks_remaining -= 1

            if msg.is_delivered:
                delivered.append(msg)

                # Update recipient's last orders
                recipient_state = self._unit_states.get(msg.recipient_id)
                if recipient_state is not None:
                    recipient_state.last_orders = msg.intent
                    recipient_state.has_contact = True
                    recipient_state.autonomous = False

                self._logger.debug(
                    f"Order delivered: {msg.sender_id} -> {msg.recipient_id}, "
                    f"intent={msg.intent.tactic_type.name}"
                )

        # Remove delivered messages
        self._message_queue = [m for m in self._message_queue if not m.is_delivered]

        return delivered

    def check_comm_loss(self, all_units: list[Unit]) -> list[str]:
        """Check for communication loss due to officer casualties.

        Returns list of unit IDs that lost communication this tick.
        """
        lost: list[str] = []

        # Find living officers
        living_officers = [u for u in all_units if u.is_alive and u.unit_type in _OFFICER_TYPES]

        # Check each unit's comm status
        for unit_id, state in self._unit_states.items():
            unit = self._find_unit(unit_id, all_units)
            if unit is None or not unit.is_alive:
                continue

            if state.radio_type == RadioType.HQ:
                continue  # HQ always has contact

            if state.radio_type == RadioType.NONE:
                continue  # Already no radio

            # Check if unit has contact with any officer or HQ
            has_contact = False

            # Direct contact with HQ
            if self._hq_id is not None:
                hq = self._find_unit(self._hq_id, all_units)
                if hq is not None and hq.is_alive:
                    hq_range = self._get_radio_range(state.radio_type)
                    dist = unit.position.tile_coord.chebyshev_distance(hq.position.tile_coord)
                    if dist <= hq_range:
                        has_contact = True

            # Contact through officer relay
            if not has_contact and living_officers:
                for officer in living_officers:
                    off_range = self._get_radio_range(state.radio_type)
                    dist = unit.position.tile_coord.chebyshev_distance(officer.position.tile_coord)
                    if dist <= off_range:
                        has_contact = True
                        break

            if not has_contact and state.has_contact:
                state.has_contact = False
                state.autonomous = True
                lost.append(unit_id)
                self._logger.info(f"Unit {unit_id} lost communication — now autonomous")

        return lost

    def get_comm_delay(
        self,
        sender: Unit,
        recipient: Unit,
        all_units: list[Unit],
        environment: EnvironmentState | None = None,
    ) -> int:
        """Calculate the communication delay for sending an order.

        Does not create a message — just returns the delay.
        """
        sender_state = self._unit_states.get(sender.id)
        recipient_state = self._unit_states.get(recipient.id)

        if sender_state is None:
            sender_state = UnitCommState(
                unit_id=sender.id,
                radio_type=self._determine_radio_type(sender),
            )
        if recipient_state is None:
            recipient_state = UnitCommState(
                unit_id=recipient.id,
                radio_type=self._determine_radio_type(recipient),
            )

        delay, _status, _hops = self._calculate_comm(
            sender, recipient, sender_state, recipient_state, all_units
        )

        if environment is not None:
            from pycc2.domain.systems.environment import WeatherCondition

            if environment.weather in (WeatherCondition.RAIN, WeatherCondition.FOG):
                delay += WEATHER_DELAY

        return delay

    def get_unit_status(self, unit_id: str) -> UnitCommState | None:
        """Get the communication status for a unit."""
        return self._unit_states.get(unit_id)

    def is_artillery_available(self, caller: Unit, all_units: list[Unit]) -> bool:
        """Check if artillery can be called by this unit.

        Artillery call-in requires an officer with radio in range of HQ.
        """
        # Must be an officer or have officer nearby
        if caller.unit_type in _OFFICER_TYPES:
            # Officer can call directly if in range of HQ
            if self._hq_id is not None:
                hq = self._find_unit(self._hq_id, all_units)
                if hq is not None and hq.is_alive:
                    dist = caller.position.tile_coord.chebyshev_distance(hq.position.tile_coord)
                    return bool(dist <= OFFICER_RADIO_RANGE)
            return False

        # Non-officer needs an officer in range to relay
        for unit in all_units:
            if unit.is_alive and unit.unit_type in _OFFICER_TYPES:
                dist = caller.position.tile_coord.chebyshev_distance(unit.position.tile_coord)
                if dist <= SQUAD_RADIO_RANGE and self._hq_id is not None:
                    hq = self._find_unit(self._hq_id, all_units)
                    if hq is not None and hq.is_alive:
                        officer_dist = unit.position.tile_coord.chebyshev_distance(
                            hq.position.tile_coord
                        )
                        return bool(officer_dist <= OFFICER_RADIO_RANGE)
        return False

    # -- internal helpers --

    def _calculate_comm(
        self,
        sender: Unit,
        recipient: Unit,
        sender_state: UnitCommState,
        recipient_state: UnitCommState,
        all_units: list[Unit],
    ) -> tuple[int, CommStatus, int]:
        """Calculate communication delay, status, and relay hops.

        Returns (delay, status, hops).
        """
        # HQ to anyone: direct, no delay
        if sender_state.radio_type == RadioType.HQ:
            return (HQ_RADIO_DELAY, CommStatus.DIRECT, 0)

        # Calculate distance
        dist = sender.position.tile_coord.chebyshev_distance(recipient.position.tile_coord)

        # Direct radio contact
        sender_range = self._get_radio_range(sender_state.radio_type)
        if dist <= sender_range:
            delay = self._get_radio_delay(sender_state.radio_type)
            return (delay, CommStatus.DIRECT, 0)

        # Try relay through officers
        officers = [
            u
            for u in all_units
            if u.is_alive and u.unit_type in _OFFICER_TYPES and u.id != sender.id
        ]

        relay_path = self._relay.find_relay_path(sender, recipient, officers, all_units)

        if relay_path:
            hops = len(relay_path)
            if hops <= MAX_RELAY_HOPS:
                base_delay = self._get_radio_delay(sender_state.radio_type)
                relay_delay = self._relay.calculate_relay_delay(hops)
                return (base_delay + relay_delay, CommStatus.RELAYED, hops)

        # No radio contact — must send runner
        if recipient_state.radio_type != RadioType.NONE:
            return (RUNNER_DELAY, CommStatus.RUNNER, 0)

        # Completely out of contact
        return (RUNNER_DELAY + 5, CommStatus.LOST, 0)

    @staticmethod
    def _determine_radio_type(unit: Unit) -> RadioType:
        """Determine the radio type for a unit based on its type."""
        if unit.unit_type == UnitType.COMMANDER:
            return RadioType.HQ
        if unit.unit_type in _OFFICER_TYPES:
            return RadioType.OFFICER
        if unit.unit_type in _SQUAD_TYPES:
            return RadioType.SQUAD
        if unit.unit_type == UnitType.TANK:
            return RadioType.OFFICER  # Tanks have good radios
        return RadioType.NONE

    @staticmethod
    def _get_radio_range(radio_type: RadioType) -> int:
        """Get the radio range for a given radio type."""
        ranges = {
            RadioType.HQ: HQ_RADIO_RANGE,
            RadioType.OFFICER: OFFICER_RADIO_RANGE,
            RadioType.SQUAD: SQUAD_RADIO_RANGE,
            RadioType.NONE: 0,
        }
        return ranges.get(radio_type, 0)

    @staticmethod
    def _get_radio_delay(radio_type: RadioType) -> int:
        """Get the base radio delay for a given radio type."""
        delays = {
            RadioType.HQ: HQ_RADIO_DELAY,
            RadioType.OFFICER: OFFICER_RADIO_DELAY,
            RadioType.SQUAD: SQUAD_RADIO_DELAY,
            RadioType.NONE: RUNNER_DELAY,
        }
        return delays.get(radio_type, RUNNER_DELAY)

    @staticmethod
    def _find_unit(unit_id: str, all_units: list[Unit]) -> Unit | None:
        for u in all_units:
            if u.id == unit_id:
                return u
        return None
