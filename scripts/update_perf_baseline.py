#!/usr/bin/env python3
"""Update FPS performance baseline (V-04 Wave B-rev P0-NEW-4).

Reads latest FPS benchmark results from pytest-benchmark JSON output and
updates tests/benchmark/perf_baseline.json. Optionally commits the change.

Usage:
    # Run FPS benchmark + update baseline + commit
    python scripts/update_perf_baseline.py --commit

    # Only update baseline (no commit)
    python scripts/update_perf_baseline.py

    # Use specific benchmark JSON file
    python scripts/update_perf_baseline.py --input .benchmarks/latest.json

Created: 2026-07-20 (Wave B-rev P0-NEW-4)
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BASELINE_FILE = REPO_ROOT / "tests" / "benchmark" / "perf_baseline.json"
BENCHMARK_TEST = "tests/benchmark/test_fps_baseline.py"
DEFAULT_BENCHMARK_DIR = REPO_ROOT / ".benchmarks"
# Must match tests/benchmark/test_fps_baseline.py::FRAMES_PER_ROUND
FRAMES_PER_ROUND = 600


def run_fps_benchmark() -> Path:
    """Run pytest-benchmark and return path to JSON output."""
    print(f"[update_perf_baseline] Running {BENCHMARK_TEST} ...")
    cmd = [
        sys.executable, "-m", "pytest", BENCHMARK_TEST,
        "--benchmark-only",
        "--benchmark-save=latest",
        "--benchmark-storage=" + str(DEFAULT_BENCHMARK_DIR),
        "-q",
    ]
    result = subprocess.run(cmd, cwd=REPO_ROOT, check=False)
    if result.returncode != 0:
        print(f"[update_perf_baseline] WARN: pytest exited {result.returncode}, "
              f"capturing partial results")

    # pytest-benchmark saves to .benchmarks/Linux-CPython-3.X-x86_64/latest.json
    # Find the most recent JSON file
    candidates = sorted(DEFAULT_BENCHMARK_DIR.rglob("*.json"), key=lambda p: p.stat().st_mtime)
    if not candidates:
        raise FileNotFoundError(
            f"No benchmark JSON found in {DEFAULT_BENCHMARK_DIR}. "
            "Run pytest-benchmark first."
        )
    latest = candidates[-1]
    print(f"[update_perf_baseline] Using benchmark JSON: {latest}")
    return latest


def extract_fps_values(benchmark_json: Path) -> dict[str, float]:
    """Extract FPS values from pytest-benchmark JSON output.

    pytest-benchmark stores TIME (seconds) per round, not FPS. We convert:
        FPS = FRAMES_PER_ROUND / time

    Maps test names to baseline keys:
        test_fps_normal_load -> normal_load (median FPS = frames / median_time)
        test_fps_heavy_load -> heavy_load_worst (worst FPS = frames / max_time)

    Note: max_time corresponds to min FPS (worst case), since FPS = frames / time.
    """
    data = json.loads(benchmark_json.read_text())
    benchmarks = data.get("benchmarks", [])
    if not benchmarks:
        raise ValueError("No benchmarks found in JSON output")

    baseline: dict[str, float] = {}
    for bench in benchmarks:
        name = bench.get("name", "")
        stats = bench.get("stats", {})
        # pytest-benchmark provides min/median/max/mean (all in seconds)
        median_time = stats.get("median", 0.0)
        max_time = stats.get("max", 0.0)

        # Convert time → FPS and map test names to baseline keys
        # (must match test_fps_baseline.py)
        if "test_fps_normal_load" in name:
            # median FPS = frames / median_time
            if median_time > 0:
                baseline["normal_load"] = FRAMES_PER_ROUND / float(median_time)
        elif "test_fps_heavy_load" in name:
            # worst FPS = frames / max_time (max time = min FPS = worst case)
            if max_time > 0:
                baseline["heavy_load_worst"] = FRAMES_PER_ROUND / float(max_time)
        # Add more mappings as needed

    if not baseline:
        raise ValueError(
            f"No recognized FPS tests in benchmark JSON. "
            f"Found: {[b.get('name') for b in benchmarks]}"
        )
    return baseline


def update_baseline_file(new_values: dict[str, float]) -> bool:
    """Merge new values into baseline file. Returns True if changed."""
    if BASELINE_FILE.exists():
        existing = json.loads(BASELINE_FILE.read_text())
    else:
        existing = {}
        BASELINE_FILE.parent.mkdir(parents=True, exist_ok=True)

    changed = False
    for key, value in new_values.items():
        if existing.get(key) != value:
            existing[key] = value
            changed = True
            print(f"[update_perf_baseline] Updated {key}: {value:.2f}")

    if changed:
        BASELINE_FILE.write_text(json.dumps(existing, indent=2, sort_keys=True))
        print(f"[update_perf_baseline] Baseline saved to {BASELINE_FILE}")
    else:
        print("[update_perf_baseline] No changes (values identical to existing baseline)")
    return changed


def git_commit_baseline() -> bool:
    """Commit baseline file change. Returns True if committed."""
    cmd = ["git", "add", str(BASELINE_FILE)]
    result = subprocess.run(cmd, cwd=REPO_ROOT, check=False)
    if result.returncode != 0:
        print("[update_perf_baseline] git add failed", file=sys.stderr)
        return False

    # Check if there's anything to commit
    status = subprocess.run(
        ["git", "status", "--porcelain", str(BASELINE_FILE)],
        cwd=REPO_ROOT, capture_output=True, text=True, check=False
    )
    if not status.stdout.strip():
        print("[update_perf_baseline] Nothing to commit (baseline unchanged)")
        return False

    commit_msg = (
        "chore(benchmark): update FPS perf_baseline.json (V-04 Wave B-rev)\n\n"
        "Auto-generated by scripts/update_perf_baseline.py\n"
        "Source: tests/benchmark/test_fps_baseline.py"
    )
    result = subprocess.run(
        ["git", "commit", "-m", commit_msg],
        cwd=REPO_ROOT, check=False
    )
    if result.returncode == 0:
        print("[update_perf_baseline] Committed baseline update")
        return True
    else:
        print("[update_perf_baseline] git commit failed", file=sys.stderr)
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Update FPS performance baseline")
    parser.add_argument(
        "--input", type=Path, default=None,
        help="Path to pytest-benchmark JSON output (default: run benchmark)"
    )
    parser.add_argument(
        "--commit", action="store_true",
        help="Git commit the baseline update"
    )
    args = parser.parse_args()

    try:
        benchmark_json = args.input or run_fps_benchmark()

        new_values = extract_fps_values(benchmark_json)
        changed = update_baseline_file(new_values)

        if args.commit and changed:
            git_commit_baseline()

        return 0
    except (FileNotFoundError, ValueError, subprocess.CalledProcessError) as e:
        print(f"[update_perf_baseline] ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
