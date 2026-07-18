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
    """Build the complete CC2 unit database from faction-specific modules.

    v0.7.6 INTEGRATE (TD-077 Wave 4): also merges templates produced by
    :class:`VehicleVariantGenerator` and :class:`FactionVariantGenerator`.
    Template IDs that collide with an existing factory entry are skipped
    with a warning log (defensive — current generators already avoid the
    known factory IDs, but this guards against future drift).

    The variant generators are imported lazily inside this function to
    avoid a circular import: both generators import ``CC2UnitTemplate``
    from :mod:`cc2_authentic_units`, which in turn re-exports from this
    module. Function-level imports match the lazy-import pattern used by
    ``GameLoopAssembler`` (the composition root).
    """
    from pycc2.domain.systems.faction_variant_generator import FactionVariantGenerator
    from pycc2.domain.systems.vehicle_variant_generator import VehicleVariantGenerator

    units: dict[str, CC2UnitTemplate] = {}
    units.update(_build_american_units())
    units.update(_build_british_units())
    units.update(_build_german_units())
    units.update(_build_german_expanded_units())
    units.update(_build_polish_units())

    # v0.7.6 Wave 4: merge variant generators (Sherman/Panzer/Halftrack/TD
    # families + Commando/PIAT/Ranger/Fallschirmjäger etc).
    for template in VehicleVariantGenerator().generate():
        if template.template_id in units:
            logger.warning(
                "Template ID conflict: %s, skipping (vehicle_variant_generator)",
                template.template_id,
            )
            continue
        units[template.template_id] = template
    for template in FactionVariantGenerator().generate():
        if template.template_id in units:
            logger.warning(
                "Template ID conflict: %s, skipping (faction_variant_generator)",
                template.template_id,
            )
            continue
        units[template.template_id] = template
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
