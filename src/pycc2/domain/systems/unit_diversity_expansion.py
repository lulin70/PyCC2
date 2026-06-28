"""Unit Diversity Expansion — facade (P5-1 batch 1).

This module is a thin facade coordinating variant generation:
  - vehicle_variant_generator.py: VehicleVariantGenerator (Sherman/Panzer/TD families)
  - faction_variant_generator.py: FactionVariantGenerator (Commando/Fallschirmjäger/etc)

Experience-level variants and the coordinator remain here.

Public API (backward-compatible):
  - UnitDiversityGenerator class (generate_variants/generate_experience_variants/queries)
  - get_expanded_unit_database() -> dict[str, CC2UnitTemplate]
  - EXPERIENCE_MODIFIERS constant
"""

from __future__ import annotations

import logging
from dataclasses import replace
from typing import Any

from pycc2.domain.entities.unit import Faction
from pycc2.domain.systems.cc2_authentic_units import CC2UnitTemplate, get_cc2_units
from pycc2.domain.systems.cc2_authentic_weapons import InfantryRole
from pycc2.domain.systems.faction_variant_generator import FactionVariantGenerator
from pycc2.domain.systems.game_settings import ExperienceLevel
from pycc2.domain.systems.vehicle_variant_generator import VehicleVariantGenerator

logger = logging.getLogger(__name__)

# ========================================================================
# Experience-level stat modifiers
# ========================================================================

EXPERIENCE_MODIFIERS: dict[ExperienceLevel, dict[str, Any]] = {
    ExperienceLevel.CONSCRIPT: {
        "accuracy_modifier": 0.80,
        "speed_modifier": 0.90,
        "panic_modifier": 1.20,
        "morale_modifier": 0.80,
        "stealth_modifier": 0.90,
        "vision_modifier": -1,
        "extra_actions": 0,
        "exp_level_int": 0,
        "suffix": "(Conscript)",
        "cost_modifier": 0.70,
    },
    ExperienceLevel.REGULAR: {
        "accuracy_modifier": 1.0,
        "speed_modifier": 1.0,
        "panic_modifier": 1.0,
        "morale_modifier": 1.0,
        "stealth_modifier": 1.0,
        "vision_modifier": 0,
        "extra_actions": 0,
        "exp_level_int": 1,
        "suffix": "",
        "cost_modifier": 1.0,
    },
    ExperienceLevel.VETERAN: {
        "accuracy_modifier": 1.15,
        "speed_modifier": 1.10,
        "panic_modifier": 0.85,
        "morale_modifier": 1.10,
        "stealth_modifier": 1.05,
        "vision_modifier": 1,
        "extra_actions": 0,
        "exp_level_int": 2,
        "suffix": "(Veteran)",
        "cost_modifier": 1.30,
    },
    ExperienceLevel.ELITE: {
        "accuracy_modifier": 1.25,
        "speed_modifier": 1.15,
        "panic_modifier": 0.75,
        "morale_modifier": 1.20,
        "stealth_modifier": 1.10,
        "vision_modifier": 1,
        "extra_actions": 1,
        "exp_level_int": 3,
        "suffix": "(Elite)",
        "cost_modifier": 1.60,
    },
}


# ========================================================================
# UnitDiversityGenerator (facade)
# ========================================================================


class UnitDiversityGenerator:
    """Generate unit variants to expand the roster to 100+ templates.

    Usage::

        gen = UnitDiversityGenerator()
        all_units = gen.generate_variants(base_templates)
        logger.debug("Total: %d", gen.count_total_units())
    """

    def __init__(self) -> None:
        """Initialize the diversity generator with an empty generated registry."""
        self._generated: dict[str, CC2UnitTemplate] = {}
        self._vehicle_gen = VehicleVariantGenerator()
        self._faction_gen = FactionVariantGenerator()

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def generate_variants(self, base_templates: list[CC2UnitTemplate]) -> list[CC2UnitTemplate]:
        """Expand base templates with vehicle, experience, and faction variants.

        Returns the complete list of all generated unit templates.
        """
        self._generated.clear()

        # Step 1: Add all base templates
        for t in base_templates:
            self._generated[t.template_id] = t

        # Step 2: Generate vehicle variants (delegated)
        vehicle_variants = self._vehicle_gen.generate()
        for v in vehicle_variants:
            self._generated[v.template_id] = v

        # Step 3: Generate experience-level variants for infantry
        for t in list(base_templates):
            if isinstance(t.role, InfantryRole):
                exp_variants = self.generate_experience_variants(
                    t,
                    [ExperienceLevel.CONSCRIPT, ExperienceLevel.VETERAN, ExperienceLevel.ELITE],
                )
                for v in exp_variants:
                    self._generated[v.template_id] = v

        # Step 4: Generate faction-specific variants (delegated)
        faction_variants = self._faction_gen.generate()
        for v in faction_variants:
            self._generated[v.template_id] = v

        return list(self._generated.values())

    # ------------------------------------------------------------------
    # Experience-level variants
    # ------------------------------------------------------------------

    def generate_experience_variants(
        self,
        template: CC2UnitTemplate,
        levels: list[ExperienceLevel],
    ) -> list[CC2UnitTemplate]:
        """Generate experience-level variants of a base infantry template.

        Skips REGULAR (that's the base template itself).
        """
        variants: list[CC2UnitTemplate] = []

        for level in levels:
            if level == ExperienceLevel.REGULAR:
                continue  # Base template IS regular

            mod = EXPERIENCE_MODIFIERS[level]
            suffix = mod["suffix"]

            new_id = f"{template.template_id}_{level.name.lower()}"
            new_name = f"{template.display_name} {suffix}".strip()

            # Calculate modified stats
            new_morale = min(100.0, template.morale_initial * mod["morale_modifier"])
            new_stealth = min(1.0, template.stealth_rating * mod["stealth_modifier"])
            new_vision = max(1, template.vision_range + mod["vision_modifier"])
            new_cost = max(10, int(template.deployment_cost * mod["cost_modifier"]))
            new_speed = (
                int(template.vehicle_speed * mod["speed_modifier"])
                if template.vehicle_speed > 0
                else template.vehicle_speed
            )

            variant = replace(
                template,
                template_id=new_id,
                display_name=new_name,
                experience_level=mod["exp_level_int"],
                morale_initial=round(new_morale, 1),
                stealth_rating=round(new_stealth, 2),
                vision_range=new_vision,
                deployment_cost=new_cost,
                vehicle_speed=new_speed,
                historical_notes=(
                    f"{template.historical_notes} — {level.name} experience variant"
                    if template.historical_notes
                    else f"{level.name} experience variant"
                ),
            )
            variants.append(variant)

        return variants

    # ------------------------------------------------------------------
    # Count
    # ------------------------------------------------------------------

    def count_total_units(self) -> int:
        """Count all generated unit templates."""
        return len(self._generated)

    def get_all_units(self) -> dict[str, CC2UnitTemplate]:
        """Return the complete generated unit dictionary."""
        return dict(self._generated)

    def get_units_by_faction(self, faction: Faction) -> list[CC2UnitTemplate]:
        """Get all generated units for a specific faction."""
        return [u for u in self._generated.values() if u.faction == faction]


# ========================================================================
# Convenience function
# ========================================================================

_EXPANDED_UNITS: dict[str, CC2UnitTemplate] = {}


def get_expanded_unit_database() -> dict[str, CC2UnitTemplate]:
    """Lazy-initialize and return the expanded unit database (100+ templates)."""
    global _EXPANDED_UNITS
    if not _EXPANDED_UNITS:
        base_db = get_cc2_units()
        base_list = list(base_db.values())
        gen = UnitDiversityGenerator()
        expanded = gen.generate_variants(base_list)
        _EXPANDED_UNITS = {u.template_id: u for u in expanded}
    return _EXPANDED_UNITS
