"""
PyCC2 Application Entry Point

Main entry point for the PyCC2 tactical combat simulator.
Shows the New Game menu first, then enters the deployment phase
where the player selects and places troops, then launches the battle.
"""

import sys


def main() -> int:
    """Main entry point for PyCC2 application.

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    import logging
    from pathlib import Path

    logger = logging.getLogger("pycc2")
    logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s: %(message)s")

    try:
        logger.info("Starting PyCC2...")

        import pygame

        from pycc2.domain.entities.game_map import GameMap
        from pycc2.domain.value_objects.vec2 import Vec2
        from pycc2.presentation.input.handler import PygameInputHandler
        from pycc2.presentation.input.interaction_controller import InteractionController
        from pycc2.presentation.rendering.camera import Camera
        from pycc2.presentation.rendering.enhanced_renderer import EnhancedRenderer
        from pycc2.presentation.rendering.window_config import DisplayInfo, WindowManager
        from pycc2.presentation.ui.new_game_menu import NewGameMenu
        from pycc2.services.ai_service import AIService
        from pycc2.services.event_bus import EventBus
        from pycc2.services.game_loop import GameLoop, GameState

        # Initialize pygame
        pygame.init()

        # Create window
        wm = WindowManager(
            DisplayInfo(base_width=1280, base_height=720)
        )
        screen = wm.initialize()

        # ---- Show New Game menu ----
        menu = NewGameMenu()
        menu_action: str | None = None

        clock = pygame.time.Clock()
        while menu_action is None:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return 0
                if event.type == pygame.MOUSEMOTION:
                    menu.update_mouse(event.pos)
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    menu_action = menu.handle_click(event.pos)
                if event.type == pygame.KEYDOWN:
                    menu_action = menu.handle_key(event.key)

            menu.render(screen)
            pygame.display.flip()
            clock.tick(60)

        if menu_action == 'quit':
            logger.info("Player quit from menu")
            return 0

        # ---- Handle Load Game action ----
        if menu_action and menu_action.startswith('load_game:'):
            slot_str = menu_action.split(':')[1]
            try:
                load_slot = int(slot_str)
            except ValueError:
                logger.error(f"Invalid load slot: {slot_str}")
                return 1

            from pycc2.infrastructure.save_system import SecureSaveManager
            save_mgr = SecureSaveManager()
            state_dict, meta, status = save_mgr.load_game(load_slot)
            if state_dict is None or status.name not in ("OK", "INCOMPATIBLE"):
                logger.error(f"Failed to load save slot {load_slot}: {status}")
                return 1

            # We need a map to load into — try to get it from save data or use default
            map_stem = 'arnhem'
            map_path = Path(f"data/maps/{map_stem}.json")
            if not map_path.exists():
                map_dir = Path("data/maps")
                maps = [m for m in map_dir.glob("*.json") if m.stem != "_schema"]
                if maps:
                    map_path = maps[0]
                else:
                    logger.error("No map files found in data/maps/")
                    return 1

            game_map = GameMap.from_json(map_path)
            center_x = game_map.width * 16.0
            center_y = game_map.height * 16.0
            camera = Camera(
                position=Vec2(center_x, center_y),
                viewport_width=1280,
                viewport_height=720,
            )

            # Create minimal units (will be replaced by loaded state)
            units: list = []

            state = GameState(
                game_map=game_map,
                units=units,
                camera=camera,
            )

            renderer = EnhancedRenderer()
            renderer.initialize(screen)

            event_bus = EventBus()
            input_handler = PygameInputHandler(camera=camera, window_manager=wm)

            # Create interaction controller for unit selection
            interaction_controller = InteractionController(
                camera=camera,
                game_map=game_map,
                event_bus=event_bus,
            )

            game_loop = GameLoop(
                renderer=renderer,
                window_manager=wm,
                event_bus=event_bus,
                state=state,
                input_handler=input_handler,
                interaction_controller=interaction_controller,
            )

            # Restore saved state
            from pycc2.services.save_controller import SaveController
            save_ctrl = SaveController()
            save_ctrl.initialize()
            restored = save_ctrl.restore_state(state_dict, game_loop)
            if not restored:
                logger.error("Failed to restore game state from save")
                return 1

            logger.info(f"Game loaded from slot {load_slot}, entering main loop...")
            exit_code = game_loop.run()
            return exit_code

        # ---- Resolve map path ----
        if menu_action == 'start_skirmish':
            map_stem = menu.get_selected_map()
        else:
            map_stem = menu.get_selected_map()

        map_path = Path(f"data/maps/{map_stem}.json")
        if not map_path.exists():
            map_dir = Path("data/maps")
            maps = list(map_dir.glob("*.json"))
            maps = [m for m in maps if m.stem != "_schema"]
            if maps:
                map_path = maps[0]
            else:
                logger.error("No map files found in data/maps/")
                return 1

        logger.info(f"Loading map: {map_path.stem}")
        game_map = GameMap.from_json(map_path)

        # ---- Get game settings from menu ----
        game_settings = menu.get_settings()
        player_side = game_settings.player_side
        faction = "allied" if player_side == "allied" else "axis"

        # Create camera centered on map
        center_x = game_map.width * 16.0
        center_y = game_map.height * 16.0
        camera = Camera(
            position=Vec2(center_x, center_y),
            viewport_width=1280,
            viewport_height=720,
        )

        # Start with empty units — they will be created during deployment
        units: list = []

        # Create game state
        state = GameState(
            game_map=game_map,
            units=units,
            camera=camera,
        )

        # Create renderer
        renderer = EnhancedRenderer()
        renderer.initialize(screen)

        # Create event bus and input handler
        event_bus = EventBus()
        input_handler = PygameInputHandler(camera=camera, window_manager=wm)

        # Create AI service
        ai_service = AIService(event_bus=event_bus)

        # Create interaction controller for unit selection
        interaction_controller = InteractionController(
            camera=camera,
            game_map=game_map,
            event_bus=event_bus,
        )

        # Create game loop
        game_loop = GameLoop(
            renderer=renderer,
            window_manager=wm,
            event_bus=event_bus,
            state=state,
            input_handler=input_handler,
            ai_service=ai_service,
            interaction_controller=interaction_controller,
        )

        # ---- Enter deployment phase ----
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

        logger.info("Entering deployment phase — faction=%s", faction)
        game_loop.start_deployment(
            map_data=map_data,
            faction=faction,
            game_settings=game_settings,
        )

        logger.info("Game initialized, entering main loop...")
        exit_code = game_loop.run()
        return exit_code

    except KeyboardInterrupt:
        logger.info("Game interrupted by user")
        return 130
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        return 1
    finally:
        try:
            import pygame
            pygame.quit()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
