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
RUN pip install --no-cache-dir setuptools wheel && \
    pip install --no-cache-dir --no-build-isolation ".[dev]" || \
    pip install --no-cache-dir pygame numpy pydantic defusedxml pytest pytest-cov pytest-mock pytest-randomly pytest-timeout freezegun scipy hypothesis
# Fallback retains as install safety net; pyproject.toml [dev] is complete.

# Set environment for headless CI
ENV SDL_VIDEODRIVER=dummy
ENV SDL_AUDIODRIVER=dummy
ENV PYTHONPATH=/app/src

# Default: run unit tests only (e2e tests require display renderer, see CI workflow)
CMD ["python", "-m", "pytest", "tests/unit/", "-q", "--tb=short"]
