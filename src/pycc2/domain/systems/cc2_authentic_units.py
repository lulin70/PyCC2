"""CC2 Authentic Unit Type System & Deployment Phase (facade).

This module re-exports the public API for backward compatibility.
The actual implementations live in:

  * unit_templates.py          — CC2UnitTemplate
  * unit_database.py           — build_cc2_unit_database, get_cc2_units, ...
  * unit_factories/            — faction-specific unit builders
  * deployment.py              — ZoneType, TileZone, DeploymentConfig, DeploymentPhase
"""
from __future__ import annotations

from pycc2.domain.systems.cc2_authentic_weapons import (
    Faction,
    InfantryRole,
    VehicleType,
    WeaponProfile,
    get_cc2_weapons,
)
from pycc2.domain.systems.deployment import (
    DeploymentConfig,
    DeploymentPhase,
    TileZone,
    ZoneType,
    create_default_deployment_config,
)
from pycc2.domain.systems.unit_database import (
    build_cc2_unit_database,
    get_cc2_units,
    get_units_by_role,
    get_units_for_faction,
)
from pycc2.domain.systems.unit_templates import CC2UnitTemplate

__all__ = [
    "CC2UnitTemplate",
    "DeploymentConfig",
    "DeploymentPhase",
    "Faction",
    "InfantryRole",
    "TileZone",
    "VehicleType",
    "WeaponProfile",
    "ZoneType",
    "build_cc2_unit_database",
    "create_default_deployment_config",
    "get_cc2_units",
    "get_cc2_weapons",
    "get_units_by_role",
    "get_units_for_faction",
]
