# V-07 Visual Regression Baseline Scenarios

> 5 core scenarios for PyCC2 v0.9.0 visual regression testing (Wave B-rev design).

## Scenarios

| # | Scenario | Description | Threshold | Rationale |
|---|----------|-------------|-----------|----------|
| 1 | `main_menu` | Title screen with version + start prompt | 1.0% (strict) | Pure UI text, must match pixel-perfect |
| 2 | `grass_terrain` | 16x16 grass map + 1 allied infantry | 5.0% (loose) | Procedural texture has random noise |
| 3 | `urban_terrain` | 16x16 urban map with roads + buildings + 2 units | 3.0% (default) | Mix of terrain + sprites |
| 4 | `post_battle_report` | Campaign UI post-battle report (victory) | 1.0% (strict) | UI text + banner, must match |
| 5 | `minimap` | Minimap rendering of mixed terrain (grass/road/woods/water) | 3.0% (default) | Compact terrain rendering |

## Threshold Rationale (V-07 Wave B-rev design)

- **Strict (1.0%)**: UI text / banner / report — any pixel diff indicates real change
- **Default (3.0%)**: Standard scenarios with mixed rendering — absorbs anti-aliasing
- **Loose (5.0%)**: Procedural terrain with random noise — needs tolerance for stochastic textures

## Platform-Specific Baselines

Baselines are stored under `baselines/<platform>/` because SDL_VIDEODRIVER=dummy
still has minor platform-specific rendering differences (font rendering, alpha blending).

| Platform | Dir | CI Used |
|----------|-----|---------|
| Linux | `baselines/linux/` | GitHub Actions Ubuntu |
| macOS | `baselines/macos/` | Local dev |
| Windows | `baselines/windows/` | Future |

## Regenerating Baselines

When intentional visual changes occur (V-01 config refactor / V-10 Morandi skin),
regenerate baselines:

```bash
# Regenerate all baselines for the current platform
python tests/visual_regression/generate_baselines.py --force

# Regenerate a specific scenario
python tests/visual_regression/generate_baselines.py --scenario main_menu --force

# Regenerate for a specific platform (e.g. CI)
python tests/visual_regression/generate_baselines.py --platform linux --force
```

## CI Integration (V-07 Wave D5 — future)

Wave D5 will add a weekly scheduled CI job that:
1. Runs `generate_baselines.py --platform linux` to refresh CI baselines
2. Runs `pytest tests/visual_regression/` to verify no regression
3. Commits new baselines if intentional changes are detected

See [VISUAL_POLISH_PLAN.md](../../docs/VISUAL_POLISH_PLAN.md) V-07 章节 for details.
