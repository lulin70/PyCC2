FROM python:3.11-slim

# Install pygame system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsdl2-dev \
    libsdl2-image-dev \
    libsdl2-mixer-dev \
    libsdl2-ttf-dev \
    libfreetype6-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy source code first
COPY src/ src/
COPY tests/ tests/

# Copy and install dependencies (layer caching)
COPY pyproject.toml ./
RUN pip install --no-cache-dir --no-build-isolation ".[dev]" || \
    pip install --no-cache-dir pygame numpy pydantic pytest

# Set environment for headless CI
ENV SDL_VIDEODRIVER=dummy
ENV SDL_AUDIODRIVER=dummy

# Default: run tests
CMD ["python", "-m", "pytest", "tests/", "-q", "--tb=short"]
