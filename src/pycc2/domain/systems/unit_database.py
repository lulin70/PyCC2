"""CC2 authentic unit database aggregator."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pycc2.domain.systems.cc2_authentic_weapons import (
    Faction,
    InfantryRole,
    VehicleType,
)
from pycc2.domain.systems.unit_factories.american_units import _build_american_units
from pycc2.domain.systems.unit_factories.british_units import _build_british_units
from pycc2.domain.systems.unit_factories.german_units import _build_german_units
from pycc2.domain.systems.unit_factories.german_units_expanded import _build_german_expanded_units
from pycc2.domain.systems.unit_factories.polish_units import _build_polish_units

if TYPE_CHECKING:
    from pycc2.domain.systems.unit_templates import CC2UnitTemplate

logger = logging.getLogger(__name__)


def build_cc2_unit_database() -> dict[str, CC2UnitTemplate]:
    """Build the complete CC2 unit database from faction-specific modules."""
    units: dict[str, CC2UnitTemplate] = {}
    units.update(_build_american_units())
    units.update(_build_british_units())
    units.update(_build_german_units())
    units.update(_build_german_expanded_units())
    units.update(_build_polish_units())
    return units


CC2_UNITS: dict[str, CC2UnitTemplate] = {}


def get_cc2_units() -> dict[str, CC2UnitTemplate]:
    """Lazy-initialize and return the unit database."""
    global CC2_UNITS
    if not CC2_UNITS:
        CC2_UNITS = build_cc2_unit_database()
    return CC2_UNITS


def get_units_for_faction(faction: Faction) -> list[CC2UnitTemplate]:
    """Return all unit templates available to a faction."""
    db = get_cc2_units()
    return [u for u in db.values() if u.faction == faction]


def get_units_by_role(role: InfantryRole | VehicleType) -> list[CC2UnitTemplate]:
    """Return all units matching a specific role."""
    db = get_cc2_units()
    return [u for u in db.values() if u.role == role]
