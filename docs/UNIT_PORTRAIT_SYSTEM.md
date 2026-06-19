# Unit Portrait System Documentation

## Overview

The Unit Portrait System generates 96x96 military-style unit portraits procedurally in the authentic Close Combat 2 style. These portraits appear in unit selection panels, command interfaces, and After-Action Report (AAR) screens.

## Architecture

### Core Component: `UnitPortraitRenderer`

Located in `src/pycc2/presentation/ui/unit_portrait_renderer.py`

```python
from pycc2.presentation.ui import UnitPortraitRenderer, generate_unit_portrait

# Method 1: With Unit object
renderer = UnitPortraitRenderer()
portrait = renderer.generate_portrait(unit)

# Method 2: Convenience function
portrait = generate_unit_portrait(unit)

# Method 3: Without Unit object
portrait = renderer.generate_for_unit_type("ALLIES", "INFANTRY_SQUAD", seed=42)
```

## Visual Design Features

### CC2 Authentic Style

The portrait system replicates Close Combat 2's original 96x96 portrait paintings with:

1. **Simplified Geometric Rendering**
   - No detailed facial features (maintaining CC2 abstraction level)
   - Face silhouettes using ellipse shapes
   - Shadow/highlight gradients for depth

2. **Faction-Specific Elements**
   
   **Allied Forces (US):**
   - M1 Helmet: Rounded dome with rim
   - Olive drab uniform (#505626)
   - Gold insignia (#DAA520)
   - Dark green backgrounds (#1C2318)

   **Axis Forces (German):**
   - Stahlhelm: Angular helmet with neck guard flare
   - Field grey uniform (#595F54)
   - Silver insignia (#C0C0C0)
   - Dark grey backgrounds (#202224)

   **British Forces:**
   - Brodie Helmet: Distinctive "tin hat" shape
   - Khaki uniform (#766C48)
   - Red insignia (#A52A2A)
   - Military green backgrounds

3. **Unit Type Variations**

   Each unit type has distinctive insignia:
   
   - **Commander**: Officer rank bars (Lieutenant/Captain)
   - **Infantry Squad**: Sergeant chevrons
   - **Sniper Team**: Crossed rifles
   - **Medic Team**: Red cross symbol
   - **Machine Gun Squad**: MG symbol
   - **AT Gun Team**: Crossed cannons
   - **Tank Crew**: Padded tanker helmet with goggles
   - **Mortar Team**: Standard chevrons

### Rendering Layers

Portraits are rendered in these sequential layers:

1. **Background** (Bottom Layer)
   - Radial gradient (darker at edges)
   - Faction-specific military colors
   - Subtle vignette effect

2. **Shoulders/Uniform**
   - Trapezoid shapes for shoulder perspective
   - Uniform color with shadow/highlight
   - Collar details

3. **Face Silhouette**
   - Simplified oval shapes
   - No detailed features (eyes/nose/mouth)
   - Skin tone with shadow gradients
   - Jaw shadow for depth

4. **Helmet/Headgear**
   - Faction-specific military headgear
   - Realistic geometric construction
   - Chin straps and details
   - Distinctive shapes for identification

5. **Insignia**
   - Unit type identification symbols
   - Positioned on right shoulder
   - Faction-appropriate colors

6. **Texture Noise** (Top Layer)
   - Subtle random pixel variation
   - Simulates hand-painted appearance
   - Weathered/authentic feel

## Technical Implementation

### Color Palette System

```python
class PortraitPalette(Enum):
    """Military color palettes matching CC2 screenshots."""
    
    # Allies
    ALLIES_HELMET = (89, 107, 53)      # Olive green
    ALLIES_UNIFORM = (80, 86, 38)      # Olive drab
    ALLIES_INSIGNIA = (218, 165, 32)   # Gold
    
    # Axis
    AXIS_HELMET = (60, 62, 56)         # Field grey
    AXIS_UNIFORM = (89, 95, 84)        # Field grey
    AXIS_INSIGNIA = (192, 192, 192)    # Silver
    
    # ... (see source code for complete palette)
```

### FactionColors Dataclass

```python
@dataclass
class FactionColors:
    helmet: tuple[int, int, int]
    uniform: tuple[int, int, int]
    insignia: tuple[int, int, int]
    skin_base: tuple[int, int, int]
    skin_shadow: tuple[int, int, int]
    background: tuple[int, int, int]
    
    @classmethod
    def for_faction(cls, faction_name: str) -> FactionColors:
        """Factory method to get colors for faction."""
```

### Portrait Caching

The renderer automatically caches generated portraits:

```python
renderer = UnitPortraitRenderer()

# First call: generates and caches
portrait1 = renderer.generate_portrait(unit)

# Second call: returns cached surface (fast)
portrait2 = renderer.generate_portrait(unit)

# Same surface object
assert portrait1 is portrait2

# Clear cache when unit state changes significantly
renderer.clear_cache()
```

Cache keys: `{faction}_{unit_type}_{unit_id}`

### Performance Characteristics

- **First Generation**: ~5-8ms per portrait (96x96 pixels)
- **Cached Retrieval**: <0.1ms (simple dictionary lookup)
- **Memory**: ~37KB per cached portrait (uncompressed RGBA)
- **Recommended**: Cache portraits for frequently displayed units

## Usage Examples

### Example 1: Unit Selection Panel

```python
from pycc2.presentation.ui import UnitPortraitRenderer

class UnitSelectionPanel:
    def __init__(self):
        self.portrait_renderer = UnitPortraitRenderer()
    
    def render_unit_entry(self, surface, unit, x, y):
        """Render unit list entry with portrait."""
        # Get portrait (cached if already generated)
        portrait = self.portrait_renderer.generate_portrait(unit)
        
        # Draw portrait with border
        surface.blit(portrait, (x, y))
        pygame.draw.rect(surface, (100, 100, 95), 
                        (x-2, y-2, 100, 100), 2)
        
        # Draw unit name next to portrait
        name_surf = self.font.render(unit.name, True, (200, 200, 190))
        surface.blit(name_surf, (x + 106, y + 20))
```

### Example 2: After-Action Report

```python
def render_aar_casualties(surface, casualties_list):
    """Render AAR casualties section with portraits."""
    renderer = UnitPortraitRenderer()
    
    y_offset = 100
    for unit in casualties_list:
        # Generate portrait
        portrait = renderer.generate_portrait(unit)
        
        # Draw with greyscale filter (for casualties)
        grey_portrait = portrait.copy()
        grey_portrait.set_alpha(128)
        surface.blit(grey_portrait, (50, y_offset))
        
        # Draw casualty info
        text = f"{unit.name} - KIA"
        text_surf = font.render(text, True, (180, 60, 60))
        surface.blit(text_surf, (160, y_offset + 30))
        
        y_offset += 110
```

### Example 3: Command Interface

```python
def render_selected_unit_detail(surface, unit):
    """Render detailed unit panel with large portrait."""
    renderer = UnitPortraitRenderer()
    
    # Generate portrait
    portrait = renderer.generate_portrait(unit)
    
    # Draw in panel at (20, 20)
    surface.blit(portrait, (20, 20))
    
    # Draw frame around portrait (CC2 style)
    frame_color = (100, 100, 95)
    pygame.draw.rect(surface, frame_color, (18, 18, 100, 100), 3)
    
    # Draw inner shadow
    pygame.draw.rect(surface, (30, 30, 28), (20, 20, 96, 96), 1)
    
    # Unit info next to portrait
    info_x = 130
    render_unit_stats(surface, unit, info_x, 20)
```

### Example 4: Portrait Gallery (Testing)

```python
def generate_portrait_gallery():
    """Generate grid of all faction/unit combinations."""
    renderer = UnitPortraitRenderer()
    
    factions = ["ALLIES", "BRITISH", "AXIS"]
    unit_types = ["INFANTRY_SQUAD", "COMMANDER", "TANK", 
                  "SNIPER_TEAM", "MEDIC_TEAM"]
    
    # Generate grid surface
    grid = renderer.generate_portrait_grid(factions, unit_types)
    
    # Save to file
    pygame.image.save(grid, "portrait_gallery.png")
```

## Integration with Existing Systems

### With CC2HUD

```python
# In cc2_hud.py
from pycc2.presentation.ui import UnitPortraitRenderer

class CC2HUD:
    def __init__(self, ...):
        # ... existing code ...
        self._portrait_renderer = UnitPortraitRenderer()
    
    def _render_center_panel(self, surface, x, y, w, h):
        """Render center panel with selected unit portrait."""
        if self._selected_unit_id:
            unit = self._get_selected_unit()
            
            # Render portrait in center panel
            portrait = self._portrait_renderer.generate_portrait(unit)
            portrait_x = x + 10
            portrait_y = y + 10
            surface.blit(portrait, (portrait_x, portrait_y))
            
            # ... rest of unit info rendering ...
```

### With UnitPanel

```python
# In unit_panel.py
from pycc2.presentation.ui import generate_unit_portrait

class UnitPanel:
    def render(self, surface: Surface) -> None:
        """Render unit panel with portrait."""
        if not self._visible or not self._selected_unit:
            return
        
        # Generate portrait
        portrait = generate_unit_portrait(self._selected_unit)
        
        # Render at top of panel
        portrait_x = self._position[0] + 10
        portrait_y = self._position[1] + 10
        surface.blit(portrait, (portrait_x, portrait_y))
        
        # ... rest of panel rendering ...
```

## Testing

Run the comprehensive test suite:

```bash
# Run portrait system tests with visual display
python scripts/test_unit_portraits.py
```

This generates a grid of all faction/unit type combinations and displays them in a window.

**Test Coverage:**
- Portrait generation for all unit types
- Faction-specific rendering (Allies, Axis, British)
- Portrait caching functionality
- Generation without Unit objects
- Visual verification grid

## Design Rationale

### Why Procedural Generation?

1. **No Asset Dependencies**: Game runs without external portrait images
2. **Consistency**: All portraits follow same style guidelines
3. **Flexibility**: Easy to add new factions/unit types
4. **File Size**: No need to ship hundreds of portrait images
5. **Authentic CC2 Style**: Geometric shapes match original game's aesthetic

### Why 96x96 Resolution?

- Original CC2 used 96x96 for portraits
- Large enough for recognizable details
- Small enough for efficient rendering/caching
- Standard size for UI consistency

### Why No Detailed Faces?

- Maintains CC2's level of abstraction
- Avoids uncanny valley issues
- Focuses attention on military equipment (helmets, uniforms)
- Easier to generate procedurally with consistent quality
- Aligns with game's tactical (not personal) focus

## Future Enhancements

Potential improvements for future versions:

1. **Rank Variations**
   - More rank insignia (Private, Sergeant, Lieutenant, Captain, etc.)
   - Dynamically based on unit veterancy

2. **Damage States**
   - Wounded appearance (bandages, blood)
   - Fatigued appearance (darker colors, posture)
   - Integrated with unit health component

3. **Equipment Variations**
   - Different weapon types visible
   - Special equipment (radios, binoculars)
   - Seasonal uniforms (winter gear)

4. **Animation**
   - Subtle head tilt animation
   - Breathing movement
   - Expression changes based on morale

5. **Higher Resolution**
   - Optional 192x192 "HD" portraits
   - More detailed rendering at larger sizes

## Reference Images

Original CC2 portrait characteristics (from game screenshots):

- Size: 96x96 pixels
- Style: Hand-painted military portraits
- Colors: Dark, muted military palettes
- Detail level: Simplified faces, prominent headgear
- Background: Solid dark colors or subtle textures
- Perspective: Slight 3/4 view, shoulders visible

## Credits

Portrait system design and implementation based on:
- Close Combat 2 (1997) by Atomic Games
- CC2 screenshot analysis and color extraction
- Military uniform reference materials
- Pygame graphics primitives

---

**Document Version**: 1.0  
**Last Updated**: 2024  
**Author**: PyCC2 Development Team
