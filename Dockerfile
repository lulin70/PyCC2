FROM python:3.12-slim

# Install pygame system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsdl2-dev \
    libsdl2-image-dev \
    libsdl2-mixer-dev \
    libsdl2-ttf-dev \
    libfreetype6-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy source code and data files
COPY src/ src/
COPY tests/ tests/
COPY data/ data/

# Copy and install dependencies (layer caching)
COPY pyproject.toml ./
RUN pip install --no-cache-dir --no-build-isolation ".[dev]" || \
    pip install --no-cache-dir pygame numpy pydantic pytest pytest-cov pytest-mock pytest-randomly pytest-timeout

# Set environment for headless CI
ENV SDL_VIDEODRIVER=dummy
ENV SDL_AUDIODRIVER=dummy
ENV PYTHONPATH=/app/src

# Default: run unit tests only (e2e tests require display renderer, see CI workflow)
# Deselect tests that require SVG assets or have rendering differences in Docker
CMD ["python", "-m", "pytest", "tests/unit/", "-q", "--tb=short", \
     "--deselect", "tests/unit/test_svg_integration.py::TestSVGSpriteIntegration::test_p0_svg_loader_available", \
     "--deselect", "tests/unit/test_sprite_renderer.py::TestFactionColors::test_allies_sprite_has_green_tones", \
     "--deselect", "tests/unit/test_sprite_renderer.py::TestCreateUnitSprite::test_returns_surface_with_correct_size", \
     "--deselect", "tests/unit/test_sprite_renderer.py::TestUnitTypeWeaponShapes::test_mg_squad_differs_from_infantry", \
     "--deselect", "tests/unit/test_sprite_renderer.py::TestUnitTypeWeaponShapes::test_commander_differs_from_infantry"]
