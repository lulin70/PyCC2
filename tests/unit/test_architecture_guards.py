"""TD-041: Architecture guard tests — enforce 4-layer DDD dependency direction.

Validates that source code adheres to the architectural rules documented in
CONTRIBUTING.md:
  domain → services → presentation → infrastructure (no upward dependencies)

Checks module-level imports only (not TYPE_CHECKING blocks or function-local
lazy imports). The composition root (game_loop_assembler.py) is exempt because
it legitimately imports from all layers for dependency injection; its imports
are function-local for lazy instantiation so they are not flagged.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

SRC_ROOT = Path(__file__).resolve().parents[2] / "src" / "pycc2"


def _extract_import_names(node: ast.Import | ast.ImportFrom) -> list[str]:
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if isinstance(node, ast.ImportFrom) and node.module:
        return [node.module]
    return []


def _is_type_checking_guard(test: ast.expr) -> bool:
    return (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING") or (
        isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"
    )


def _get_module_level_imports(file_path: Path) -> list[str]:
    """Return module-level import targets, excluding TYPE_CHECKING blocks.

    Only top-level Import/ImportFrom nodes are inspected. Imports inside
    functions or classes are not checked (lazy imports for breaking cycles).
    """
    source = file_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(file_path))
    imports: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.If) and _is_type_checking_guard(node.test):
            continue
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            imports.extend(_extract_import_names(node))
    return imports


def _layer_violations(layer: str, forbidden_layers: tuple[str, ...]) -> list[tuple[Path, str]]:
    """Find module-level imports from forbidden layers in the given layer."""
    layer_dir = SRC_ROOT / layer
    if not layer_dir.exists():
        return []
    violations: list[tuple[Path, str]] = []
    for py_file in layer_dir.rglob("*.py"):
        if py_file.name == "__init__.py":
            continue
        for imp in _get_module_level_imports(py_file):
            if imp.startswith("pycc2."):
                parts = imp.split(".")
                if len(parts) >= 2 and parts[1] in forbidden_layers:
                    violations.append((py_file.relative_to(SRC_ROOT), imp))
    return violations


class TestDomainLayerIsolation:
    """Domain layer must not import from services/presentation/infrastructure."""

    def test_domain_no_upper_layer_imports(self):
        violations = _layer_violations("domain", ("services", "presentation", "infrastructure"))
        assert violations == [], (
            "Domain layer must not import upper layers. Found violations:\n"
            + "\n".join(f"  {f}: {imp}" for f, imp in violations)
        )


class TestServicesLayerIsolation:
    """Services layer must not import from presentation at module level.

    game_loop_assembler.py is the composition root; its cross-layer imports
    are function-local (lazy instantiation) so they are not flagged.
    """

    def test_services_no_presentation_module_level_imports(self):
        violations = _layer_violations("services", ("presentation",))
        assert violations == [], (
            "Services layer must not import presentation at module level. "
            "Found violations:\n" + "\n".join(f"  {f}: {imp}" for f, imp in violations)
        )


class TestPresentationLayerIsolation:
    """Presentation layer must not import from infrastructure."""

    def test_presentation_no_infrastructure_imports(self):
        violations = _layer_violations("presentation", ("infrastructure",))
        assert violations == [], (
            "Presentation layer must not import infrastructure. "
            "Found violations:\n" + "\n".join(f"  {f}: {imp}" for f, imp in violations)
        )


class TestInfrastructureLayerIsolation:
    """Infrastructure layer must not import from presentation/services."""

    def test_infrastructure_no_upper_imports(self):
        violations = _layer_violations("infrastructure", ("presentation", "services"))
        assert violations == [], (
            "Infrastructure layer must not import upper layers. "
            "Found violations:\n" + "\n".join(f"  {f}: {imp}" for f, imp in violations)
        )


class TestLayerDirectoriesExist:
    """All 4 DDD layers must exist as directories."""

    @pytest.mark.parametrize("layer", ["domain", "services", "presentation", "infrastructure"])
    def test_layer_directory_exists(self, layer: str):
        layer_dir = SRC_ROOT / layer
        assert layer_dir.is_dir(), f"Layer directory missing: {layer_dir}"
