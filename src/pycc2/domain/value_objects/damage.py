"""Damage Value Object

Represents damage with type classification and source tracking.
Immutable value object for combat resolution.
"""

from dataclasses import dataclass
from enum import Enum, auto


class DamageType(Enum):
    """Classification of damage types."""

    KINETIC = auto()  # Bullet/shrapnel damage
    EXPLOSIVE = auto()  # Grenade/mortar damage
    INCENDIARY = auto()  # Fire damage
    FRAGMENTATION = auto()  # Fragmentation damage
    CRUSHING = auto()  # Impact/crushing damage


@dataclass(frozen=True)
class Damage:
    """Immutable damage value object.

    Attributes:
        amount: Base damage value
        damage_type: Classification of damage type
        armor_penetration: Ability to bypass armor (0.0-1.0)
        source_unit_id: ID of unit that caused the damage (if applicable)
        source_weapon_name: Name of weapon that caused damage (if known)

    """

    amount: float
    damage_type: DamageType = DamageType.KINETIC
    armor_penetration: float = 0.0
    source_unit_id: str | None = None
    source_weapon_name: str | None = None

    def __post_init__(self):
        if self.amount < 0:
            raise ValueError("Damage amount cannot be negative")
        if not 0.0 <= self.armor_penetration <= 1.0:
            raise ValueError("Armor penetration must be between 0.0 and 1.0")

    @property
    def is_lethal(self) -> bool:
        """Check if damage could potentially kill a standard unit (>= 50)."""
        return self.amount >= 50.0

    @property
    def is_critical(self) -> bool:
        """Check if damage is critical level (>= 75% of standard HP)."""
        return self.amount >= 75.0

    def apply_armor_reduction(self, armor_value: float) -> "Damage":
        """Calculate damage after armor reduction.

        Args:
            armor_value: Target's armor value (0.0-1.0)

        Returns:
            New Damage object with reduced amount

        """
        effective_armor = armor_value * (1.0 - self.armor_penetration)
        reduction_factor = 1.0 - effective_armor
        reduced_amount = self.amount * reduction_factor

        return Damage(
            amount=reduced_amount,
            damage_type=self.damage_type,
            armor_penetration=self.armor_penetration,
            source_unit_id=self.source_unit_id,
            source_weapon_name=self.source_weapon_name,
        )

    def apply_cover_bonus(self, cover_bonus: float) -> "Damage":
        """Apply cover-based damage reduction.

        Args:
            cover_bonus: Cover bonus as damage reduction (0.0-1.0)

        Returns:
            New Damage object with reduced amount

        """
        if not 0.0 <= cover_bonus <= 1.0:
            raise ValueError("Cover bonus must be between 0.0 and 1.0")

        reduced_amount = self.amount * (1.0 - cover_bonus)

        return Damage(
            amount=reduced_amount,
            damage_type=self.damage_type,
            armor_penetration=self.armor_penetration,
            source_unit_id=self.source_unit_id,
            source_weapon_name=self.source_weapon_name,
        )

    def multiply(self, multiplier: float) -> "Damage":
        """Multiply damage by a factor (for crits, weak points, etc.).

        Args:
            multiplier: Multiplication factor

        Returns:
            New Damage object with modified amount

        """
        if multiplier < 0:
            raise ValueError("Multiplier cannot be negative")

        return Damage(
            amount=self.amount * multiplier,
            damage_type=self.damage_type,
            armor_penetration=self.armor_penetration,
            source_unit_id=self.source_unit_id,
            source_weapon_name=self.source_weapon_name,
        )

    def add(self, other: "Damage") -> "Damage":
        """Add two damage values together.

        Args:
            other: Another Damage object to add

        Returns:
            New Damage object with summed amounts

        """
        return Damage(
            amount=self.amount + other.amount,
            damage_type=self.damage_type,
            armor_penetration=max(self.armor_penetration, other.armor_penetration),
            source_unit_id=self.source_unit_id or other.source_unit_id,
            source_weapon_name=self.source_weapon_name or other.source_weapon_name,
        )

    @classmethod
    def create_kinetic(cls, amount: float, **kwargs) -> "Damage":
        """Factory method to create kinetic damage."""
        return cls(amount=amount, damage_type=DamageType.KINETIC, **kwargs)

    @classmethod
    def create_explosive(cls, amount: float, **kwargs) -> "Damage":
        """Factory method to create explosive damage."""
        return cls(amount=amount, damage_type=DamageType.EXPLOSIVE, **kwargs)

    @classmethod
    def zero(cls) -> "Damage":
        """Create zero-damage instance."""
        return cls(amount=0.0)

    def __repr__(self) -> str:
        return (
            f"Damage(amount={self.amount:.1f}, "
            f"type={self.damage_type.name}, "
            f"ap={self.armor_penetration:.2f})"
        )
