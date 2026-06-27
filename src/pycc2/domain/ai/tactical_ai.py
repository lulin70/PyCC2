"""P9 AI Tactical System — CC2-Authentic Combat Behaviors

Backward-compatible re-export shell.

The implementation has been split into focused sub-modules:
  - tactical_ai_types:    FlankSide, TacticalContext, PrioritizedIntent, TacticalAIBase
  - tactical_flanking:    FlankingAI
  - tactical_suppression: SuppressionAI
  - tactical_coordination: InfantryTankCoordAI, VictoryPointAI
  - tactical_orchestrator: TacticalOrchestrator

All public symbols are re-exported here so that existing imports like::

    from pycc2.domain.ai.tactical_ai import FlankingAI, TacticalOrchestrator

continue to work without modification.
"""

# -- Types & base --
from pycc2.domain.ai.tactical_ai_types import (  # noqa: F401
    FlankSide,
    PrioritizedIntent,
    TacticalAIBase,
    TacticalContext,
    _flank_position,
    _infer_facing,
    _threat_score,
)

# -- AI modules --
from pycc2.domain.ai.tactical_coordination import (  # noqa: F401
    InfantryTankCoordAI,
    VictoryPointAI,
)
from pycc2.domain.ai.tactical_flanking import FlankingAI  # noqa: F401
from pycc2.domain.ai.tactical_orchestrator import TacticalOrchestrator  # noqa: F401
from pycc2.domain.ai.tactical_suppression import SuppressionAI  # noqa: F401

__all__ = [
    "FlankSide",
    "PrioritizedIntent",
    "TacticalAIBase",
    "TacticalContext",
    "_flank_position",
    "_infer_facing",
    "_threat_score",
    "FlankingAI",
    "SuppressionAI",
    "InfantryTankCoordAI",
    "VictoryPointAI",
    "TacticalOrchestrator",
]
