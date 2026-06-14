"""
PyCC2 Application Entry Point

Main entry point for the PyCC2 tactical combat simulator.
Shows the New Game menu first, then enters the deployment phase
where the player selects and places troops, then launches the battle.
"""

import logging
import sys

logger = logging.getLogger("pycc2")


def _show_main_menu(screen, clock):
    """Display the main menu and return (action, menu) tuple.

    Returns:
        Tuple of (menu_action, menu_object). menu_action is one of:
        'start_campaign', 'start_skirmish', 'load_game:N', or 'quit'.
    """
    import pygame

    from pycc2.presentation.ui.new_game_menu import NewGameMenu

    menu = NewGameMenu()
    menu_action = None

    while menu_action is None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return 'quit', menu
            if event.type == pygame.MOUSEMOTION:
                menu.update_mouse(event.pos)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                menu_action = menu.handle_click(event.pos)
            if event.type == pygame.KEYDOWN:
                menu_action = menu.handle_key(event.key)

        menu.render(screen)
        pygame.display.flip()
        clock.tick(60)

    return menu_action, menu


def _resolve_map_path(map_stem):
    """Resolve map file path, falling back to first available map.

    Args:
        map_stem: Map filename stem (without extension)

    Returns:
        Path to map file, or None if no maps found.
    """
    from pathlib import Path

    map_path = Path(f"data/maps/{map_stem}.json")
    if map_path.exists():
        return map_path

    map_dir = Path("data/maps")
    maps = [m for m in map_dir.glob("*.json") if m.stem != "_schema"]
    if maps:
        return maps[0]

    logger.error("No map files found in data/maps/")
    return None


def _create_game_objects(game_map, camera, screen, wm, event_bus, ai_service=None):
    """Create shared game objects used by both load and new game paths.

    Eliminates ~80 lines of duplicated object creation code between the two
    game initialization branches.

    Args:
        game_map: The game map
        camera: The camera
        screen: Pygame screen surface
        wm: WindowManager instance
        event_bus: EventBus instance
        ai_service: Optional AIService (only for new games)

    Returns:
        Dict containing all created game objects including 'game_loop'.
    """
    from pycc2.domain.interfaces.display_config import DisplayConfig as DC
    from pycc2.presentation.input.handler import PygameInputHandler
    from pycc2.presentation.input.interaction_controller import InteractionController
    from pycc2.presentation.rendering.enhanced_renderer import EnhancedRenderer
    from pycc2.presentation.ui.hint_manager import HintManager
    from pycc2.presentation.ui.keybind_manager import KeybindManager
    from pycc2.presentation.ui.settings_menu import SettingsMenu
    from pycc2.presentation.ui.tutorial_system import TutorialOverlay
    from pycc2.services.game_loop import GameLoop, GameState

    units: list = []
    state = GameState(
        game_map=game_map,
        units=units,
        camera=camera,
    )

    renderer = EnhancedRenderer()
    renderer.initialize(screen)

    input_handler = PygameInputHandler(camera=camera, window_manager=wm)

    interaction_controller = InteractionController(
        camera=camera,
        game_map=game_map,
        event_bus=event_bus,
    )

    display_config = DC()
    hint_manager = HintManager()
    keybind_manager = KeybindManager()
    settings_menu = SettingsMenu(display_config, keybind_manager=keybind_manager)
    tutorial_overlay = TutorialOverlay(display_config)

    interaction_controller.set_hint_manager(hint_manager)
    interaction_controller.set_keybind_manager(keybind_manager)

    game_loop_kwargs = dict(
        renderer=renderer,
        window_manager=wm,
        event_bus=event_bus,
        state=state,
        input_handler=input_handler,
        interaction_controller=interaction_controller,
        hint_manager=hint_manager,
        settings_menu=settings_menu,
        tutorial_overlay=tutorial_overlay,
    )
    if ai_service is not None:
        game_loop_kwargs['ai_service'] = ai_service

    game_loop = GameLoop(**game_loop_kwargs)

    return {
        'state': state,
        'renderer': renderer,
        'event_bus': event_bus,
        'input_handler': input_handler,
        'interaction_controller': interaction_controller,
        'display_config': display_config,
        'hint_manager': hint_manager,
        'keybind_manager': keybind_manager,
        'settings_menu': settings_menu,
        'tutorial_overlay': tutorial_overlay,
        'game_loop': game_loop,
    }


def _load_saved_game(slot, screen, wm):
    """Load a saved game from the specified slot.

    Args:
        slot: Save slot number
        screen: Pygame screen surface
        wm: WindowManager instance

    Returns:
        GameLoop instance on success, None on failure.
    """
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.value_objects.vec2 import Vec2
    from pycc2.infrastructure.save_system import SecureSaveManager
    from pycc2.presentation.rendering.camera import Camera
    from pycc2.services.event_bus import EventBus
    from pycc2.services.save_controller import SaveController

    save_mgr = SecureSaveManager()
    state_dict, meta, status = save_mgr.load_game(slot)
    if state_dict is None or status.name not in ("OK", "INCOMPATIBLE"):
        logger.error(f"Failed to load save slot {slot}: {status}")
        return None

    # Resolve map path — try to get it from save data or use default
    map_stem = 'arnhem'
    map_path = _resolve_map_path(map_stem)
    if map_path is None:
        return None

    game_map = GameMap.from_json(map_path)
    center_x = game_map.width * 16.0
    center_y = game_map.height * 16.0
    camera = Camera(
        position=Vec2(center_x, center_y),
        viewport_width=1280,
        viewport_height=720,
    )

    event_bus = EventBus()
    objects = _create_game_objects(game_map, camera, screen, wm, event_bus)
    game_loop = objects['game_loop']

    # Restore saved state
    save_ctrl = SaveController()
    save_ctrl.initialize()
    restored = save_ctrl.restore_state(state_dict, game_loop)
    if not restored:
        logger.error("Failed to restore game state from save")
        return None

    logger.info(f"Game loaded from slot {slot}, entering main loop...")
    return game_loop


def _start_new_game(menu, menu_action, screen, wm):
    """Initialize a new game from menu selection.

    Args:
        menu: NewGameMenu instance
        menu_action: Menu action string ('start_campaign' or 'start_skirmish')
        screen: Pygame screen surface
        wm: WindowManager instance

    Returns:
        GameLoop instance on success, None on failure.
    """
    import json
    from pathlib import Path

    from pycc2.domain.entities.game_map import GameMap, SpawnPoint
    from pycc2.domain.value_objects.tile_coord import TileCoord
    from pycc2.domain.value_objects.vec2 import Vec2
    from pycc2.presentation.rendering.camera import Camera
    from pycc2.services.ai_service import AIService
    from pycc2.services.event_bus import EventBus

    # Resolve map path
    map_stem = menu.get_selected_map()
    map_path = _resolve_map_path(map_stem)
    if map_path is None:
        return None

    logger.info(f"Loading map: {map_path.stem}")

    try:
        game_map = GameMap.from_json(map_path)
    except Exception as e:
        logger.error(f"Failed to load map {map_path}: {e}")
        return None

    # Validate spawn points - add defaults if missing
    if not game_map.spawn_points:
        logger.warning("Map has no spawn_points, adding defaults")
        game_map.spawn_points = [
            SpawnPoint(
                id="friendly_default",
                side="friendly",
                position=TileCoord(5, game_map.height // 2),
                units_max=9,
            ),
            SpawnPoint(
                id="enemy_default",
                side="enemy",
                position=TileCoord(game_map.width - 5, game_map.height // 2),
                units_max=9,
            ),
        ]
        logger.info(f"Added {len(game_map.spawn_points)} default spawn points")

    # Get game settings from menu
    try:
        game_settings = menu.get_settings()
        player_side = game_settings.player_side
        faction = "allied" if player_side == "allied" else "axis"
        logger.info(f"Settings loaded: {player_side} side")
    except Exception as e:
        logger.error("Failed to get game settings: %s", e, exc_info=True)
        return None

    # Create camera centered on map
    center_x = game_map.width * 16.0
    center_y = game_map.height * 16.0
    camera = Camera(
        position=Vec2(center_x, center_y),
        viewport_width=1280,
        viewport_height=720,
    )

    # Create event bus and AI service
    event_bus = EventBus()
    ai_service = AIService(event_bus=event_bus)

    # Create shared game objects
    objects = _create_game_objects(game_map, camera, screen, wm, event_bus, ai_service=ai_service)
    game_loop = objects['game_loop']

    # Build map_data dict for deployment UI from GameMap
    map_data = {
        "width": game_map.width,
        "height": game_map.height,
        "tiles": game_map.tile_grid.tolist(),
        "spawn_points": [
            {
                "id": sp.id,
                "side": sp.side,
                "position": [sp.position.x, sp.position.y],
                "units_max": sp.units_max,
            }
            for sp in game_map.spawn_points
        ],
    }

    # Load scenario data for faction asymmetry and VL info (G5/G6)
    scenario_stem = menu.get_selected_map() if hasattr(menu, 'get_selected_map') else map_stem
    scenario_path = Path(f"data/scenarios/{scenario_stem}.json")
    if not scenario_path.exists():
        # Try matching by map_id in scenario files
        for sp in Path("data/scenarios").glob("*.json"):
            if sp.stem == "_schema":
                continue
            try:
                with open(sp) as f:
                    scenario = json.load(f)
                if scenario.get("map_id") == scenario_stem:
                    scenario_path = sp
                    break
            except Exception as e:
                logging.info(f"Scenario file parse failed: {e}")
                continue

    if scenario_path.exists():
        try:
            with open(scenario_path) as f:
                scenario_data = json.load(f)
            # Include scenario-level data in map_data for deployment
            map_data["victory_locations"] = scenario_data.get("victory_locations", [])
            map_data["forces"] = scenario_data.get("forces", {})
            map_data["special_rules"] = scenario_data.get("special_rules", [])
            map_data["scenario_id"] = scenario_data.get("scenario_id", "")
            logger.info("Loaded scenario data from %s", scenario_path.stem)
        except Exception as e:
            logger.warning("Failed to load scenario data from %s: %s", scenario_path, e)

    # Enter deployment phase
    logger.info("Entering deployment phase — faction=%s", faction)
    try:
        game_loop.start_deployment(
            map_data=map_data,
            faction=faction,
            game_settings=game_settings,
        )
    except Exception as e:
        logger.error("Failed to start deployment: %s", e, exc_info=True)
        return None

    logger.info("Game initialized, entering main loop...")
    return game_loop


def _run_game_loop(game_loop):
    """Run the game main loop.

    Args:
        game_loop: GameLoop instance

    Returns:
        Exit code from game loop.
    """
    try:
        return game_loop.run()
    except Exception as e:
        logger.error("Game loop crashed: %s", e, exc_info=True)
        return 1


def main() -> int:
    """Main entry point for PyCC2 application.

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s: %(message)s")

    try:
        logger.info("Starting PyCC2...")

        import pygame

        from pycc2.presentation.rendering.window_config import DisplayInfo, WindowManager

        # Initialize pygame
        pygame.init()

        # Create window
        wm = WindowManager(
            DisplayInfo(base_width=1280, base_height=720)
        )
        screen = wm.initialize()

        # Show main menu
        clock = pygame.time.Clock()
        menu_action, menu = _show_main_menu(screen, clock)

        if menu_action == 'quit':
            logger.info("Player quit from menu")
            return 0

        # Validate menu action
        if menu_action not in ('start_campaign', 'start_skirmish') and not (menu_action and menu_action.startswith('load_game:')):
            logger.warning(f"Unknown menu action: {menu_action}, treating as start_campaign")
            menu_action = 'start_campaign'  # Default to campaign mode

        logger.info(f"Menu action: {menu_action}")

        # Handle load game
        if menu_action and menu_action.startswith('load_game:'):
            slot_str = menu_action.split(':')[1]
            try:
                load_slot = int(slot_str)
            except ValueError:
                logger.error(f"Invalid load slot: {slot_str}")
                return 1

            game_loop = _load_saved_game(load_slot, screen, wm)
            if game_loop is None:
                return 1
            return _run_game_loop(game_loop)

        # Handle new game
        game_loop = _start_new_game(menu, menu_action, screen, wm)
        if game_loop is None:
            return 1
        return _run_game_loop(game_loop)

    except KeyboardInterrupt:
        logger.info("Game interrupted by user")
        return 130
    except Exception as e:
        logger.critical("Fatal error: %s", e, exc_info=True)
        return 1
    finally:
        try:
            import pygame
            pygame.quit()
        except Exception as e:
            logging.debug(f"pygame.quit() failed: {e}")


if __name__ == "__main__":
    sys.exit(main())
