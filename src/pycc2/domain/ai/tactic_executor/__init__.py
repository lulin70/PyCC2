"""TacticExecutor package — translates tactic intents into unit actions.

D11 SRP 拆分: 原 tactic_executor.py (1346L) 拆为 facade + 7 mixin。
Public API 不变: ``from pycc2.domain.ai.tactic_executor import TacticExecutor``
"""

from pycc2.domain.ai.tactic_executor.facade import TacticExecutor

__all__ = ["TacticExecutor"]
