from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, TypeVar, overload

from .achievement_bridge_protocol import IAchievementBridge as IAchievementBridge
from .ai_service_protocol import IAIService as IAIService
from .bottom_panel_protocol import IBottomPanel as IBottomPanel
from .camera_protocol import ICamera as ICamera
from .campaign_ui_protocol import ICampaignUI as ICampaignUI
from .combat_camera_protocol import ICombatCamera as ICombatCamera
from .combat_director_protocol import ICombatDirector as ICombatDirector
from .day_night_protocol import IDayNightCycle as IDayNightCycle
from .deployment_manager_protocol import IDeploymentManager as IDeploymentManager
from .deployment_ui_protocol import IDeploymentUI as IDeploymentUI
from .display_config import DisplayConfig as DisplayConfig
from .effect_stack_protocol import IEffectStack as IEffectStack
from .environmental_audio_protocol import IEnvironmentalAudio as IEnvironmentalAudio
from .hud_manager_protocol import IHUDManager as IHUDManager
from .input_handler_protocol import IInputHandler as IInputHandler
from .ui_overlay_protocol import IHintManager as IHintManager
from .ui_overlay_protocol import ILightingRenderer as ILightingRenderer
from .ui_overlay_protocol import ISettingsMenu as ISettingsMenu
from .ui_overlay_protocol import ITutorialOverlay as ITutorialOverlay
from .ui_overlay_protocol import IWeatherRenderer as IWeatherRenderer
from .ui_overlay_protocol import IWeatherState as IWeatherState
from .input_router_protocol import IInputRouter as IInputRouter
from .interaction_controller_protocol import IInteractionController as IInteractionController
from .minimap_protocol import IMinimap as IMinimap
from .pause_menu_protocol import IPauseMenu as IPauseMenu
from .popup_manager_protocol import IPopupManager as IPopupManager
from .projectile_trail_protocol import IProjectileTrailSystem as IProjectileTrailSystem
from .render_pipeline_protocol import IRenderPipeline as IRenderPipeline
from .renderer_protocol import IRenderer as IRenderer
from .save_controller_protocol import ISaveController as ISaveController
from .shadow_system_protocol import IDynamicShadowSystem as IDynamicShadowSystem
from .sound_system_protocol import ISoundSystem as ISoundSystem
from .victory_manager_protocol import IVictoryManager as IVictoryManager
from .weather_system_protocol import IWeatherSystem as IWeatherSystem
from .window_manager_protocol import IWindowManager as IWindowManager

E = TypeVar("E")


class IEventPublisher(ABC):
    @overload
    @abstractmethod
    def publish(self, event: dict) -> None: ...

    @overload
    @abstractmethod
    def publish(self, event: object) -> None: ...

    @abstractmethod
    def publish(self, event: dict | object) -> None: ...

    @overload
    @abstractmethod
    def subscribe(self, event_type: type[E], handler: Callable[[E], None]) -> None: ...

    @overload
    @abstractmethod
    def subscribe(self, event_type: type, handler: Callable[[Any], None]) -> None: ...

    @abstractmethod
    def subscribe(self, event_type: type, handler: Callable) -> None: ...

    @abstractmethod
    def subscribe_to(self, event_name: str, handler: Callable[[dict], None]) -> None: ...

    @abstractmethod
    def publish_named(self, event_name: str, data: dict) -> None: ...


class IRandomNumberGenerator(ABC):
    @abstractmethod
    def randint(self, low: int, high: int) -> int: ...

    @abstractmethod
    def uniform(self, low: float = 0.0, high: float = 1.0) -> float: ...

    @abstractmethod
    def choice(self, seq: list) -> Any: ...

    @abstractmethod
    def gaussian(self, mu: float = 0.0, sigma: float = 1.0) -> float: ...
