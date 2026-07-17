"""Archived prototype modules — kept for historical reference only.

These modules were identified as ghost prototypes (0 src references) during
TD-077 evaluation (v0.7.1, 2026-07-17). They are NOT imported by any active
code path and should NOT be used in production. They are preserved here for:

1. Design reference for future rewrites (e.g., casualty_system's scoring formulas)
2. Architecture patterns that may inform refactoring (e.g., cc2_hud's
   renderer/input_handler separation)
3. Test assets that document expected behavior (in tests/_archive/)

Modules in this archive:
- ai_config.py (193L): Data-driven AI config, needs full AI refactor to integrate
- casualty_system.py (459L): Casualty tracking, has implementation defects (setattr/perf_counter)
- ammo_type_system.py (341L): Ammo type system, has implementation defects (perf_counter/dict)
- combat_log.py (284L): Combat log UI, render/data coupling issues
- cc2_hud.py (432L): HUD implementation, superseded by CC2BottomPanel
- enhanced_ui_renderer.py (346L): UI rendering utilities, kept as tool backup
- enhanced_post_processing.py (267L): Post-processing, has performance defects (per-pixel loop)
- hud_constants.py (57L): cc2_hud dependency (closed death code group)
- hud_input.py (110L): cc2_hud dependency (closed death code group)
- hud_renderer.py (886L): cc2_hud dependency (closed death code group)

Decision: ARCHIVE (v0.7.1, 2026-07-17)
See: docs/ROADMAP_v0.7.1.md for full evaluation matrix.
"""
