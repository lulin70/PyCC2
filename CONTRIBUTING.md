# Contributing to PyCC2

Thank you for your interest in contributing to **PyCC2** (Python Company Command 2)!

## Development Setup

```bash
# Clone and install
git clone https://github.com/lulin70/PyCC2.git
cd PyCC2
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate     # Windows
pip install -e ".[dev]"

# Verify installation
python -m pytest tests/ -m "not slow" --tb=no -q
```

## Project Structure

```
PyCC2/
├── src/pycc2/
│   ├── domain/          # Business logic (entities, systems, value objects)
│   │   ├── entities/    # Unit, GameMap, Squad, etc.
│   │   ├── systems/     # Combat, morale, campaign, AI, etc.
│   │   ├── components/  # Health, Morale, Position, etc.
│   │   └── interfaces/  # Protocol definitions (32 protocols)
│   ├── services/        # Application services layer
│   ├── presentation/    # UI/rendering (pygame-based)
│   │   └── rendering/   # 76 rendering modules
│   └── infrastructure/  # External integrations
├── tests/
│   ├── unit/            # ~80 unit test files
│   ├── integration/     # ~20 integration tests
│   ├── e2e/             # ~22 end-to-end tests
│   └── benchmark/       # Performance baselines
├── scripts/             # Utility and helper scripts
└── docs/                # Design documentation
```

## Code Style & Quality

This project enforces strict code quality via CI:

| Tool | Purpose | Config |
|------|---------|--------|
| **ruff** | Linting + formatting | `.github/workflows/ci.yml` |
| **mypy** | Type checking (non-blocking) | `pyproject.toml` |
| **bandit** | Security scanning (low+ severity blocks) | `ci.yml` |
| **pytest** | Testing with coverage | `pyproject.toml` |

### Pre-commit Hooks

```bash
pre-commit run --all-files
```

### Running Tests Locally

```bash
# Full regression (excludes slow benchmarks)
SDL_VIDEODRIVER=dummy python -m pytest tests/ -m "not slow" -q

# With coverage
SDL_VIDEODRIVER=dummy python -m pytest tests/ -m "not slow" --cov=src/pycc2

# E2E user journey tests only
SDL_VIDEODRIVER=dummy python -m pytest tests/e2e/test_user_journey*.py -v

# Performance benchmarks (marked @slow)
SDL_VIDEODRIVER=dummy python -m pytest tests/benchmark/ -v
```

> **Note**: Tests requiring a display (E2E, visual smoke) auto-skip in headless environments.

## Git Workflow

All code changes must follow the PR workflow:

1. Create a feature branch from `main`
2. Make commits with descriptive messages
3. Push branch and create a Pull Request
4. Ensure CI passes (Lint + Test 3.11 + Test 3.12)
5. Request review and merge (squash)

```bash
git checkout -b fix/your-fix-name
# ... make changes ...
git add <files>
git commit -m "fix: description of change"
git push -u origin fix/your-fix-name
gh pr create --base main --title "fix: ..." --body "..."
```

## Commit Message Convention

Follow Conventional Commits:

- `fix:` — Bug fix
- `feat:` — New feature
- `refactor:` — Code restructuring (no behavior change)
- `docs:` — Documentation only
- `test:` — Test additions/changes
- `chore:` — Build/config/tooling
- `perf:` — Performance improvement

Include version info and test count when relevant.

## Testing Requirements

- **Unit tests**: Required for all new domain/systems code
- **Integration tests**: For cross-module interactions
- **No Mock overuse**: Prefer real components when API needs底层objects
- **Test dimensions**: Cover happy path (>50%), error cases (>15%), boundaries (>10%)
- **Never modify assertions to pass** — fix the source code instead

## Architecture Rules

1. **4-layer DDD**: domain → services → presentation → infrastructure (no upward dependencies)
2. **Protocol interfaces**: All cross-boundary contracts defined in `domain/interfaces/`
3. **No hardcoded secrets**: Use environment variables or config files
4. **Event-driven**: Use EventBus for decoupled communication
5. **Object pooling**: Rendering pipeline uses SurfacePool, ParticlePool, TerrainTileCache

### Architecture Guard Tests (TD-041)

Layer dependencies are enforced automatically by `tests/unit/test_architecture_guards.py`:
- Domain must not import from services/presentation/infrastructure
- Services must not import from presentation at module level (TYPE_CHECKING and function-local lazy imports are exempt)
- Presentation must not import from infrastructure
- Infrastructure must not import from presentation/services

The composition root (`game_loop_assembler.py`) is exempt — its cross-layer imports are function-local for dependency injection. Run `pytest tests/unit/test_architecture_guards.py -v` before submitting changes that touch imports.

## Change Impact Analysis (TD-041)

Before modifying a module's public interface (function/method signature, class fields, Protocol definitions), check all references:

1. **Find all callers** — `grep -rn "module_name" src/pycc2/ tests/` or use IDE "Find Usages"
2. **Check Protocol contracts** — changes to `src/pycc2/domain/interfaces/*.py` affect all implementations; search for classes implementing the Protocol
3. **Run architecture guards** — `pytest tests/unit/test_architecture_guards.py -v` ensures no new layer violations
4. **Run affected tests** — `pytest tests/unit/test_<module>.py tests/integration/ -v` for the module and its integration tests
5. **Update docs if API changes** — README, USER_MANUAL, CONTRIBUTING, TECH_DEBT must stay consistent with code

For cross-layer changes (e.g., modifying a domain entity used by services and presentation), run the full regression: `SDL_VIDEODRIVER=dummy python -m pytest tests/ -m "not slow" -q`.

## Reporting Issues

- Bug reports: Include steps to reproduce, expected vs actual behavior
- Feature requests: Describe use case and acceptance criteria
- Security issues: Do NOT open public issues — contact maintainers directly

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
