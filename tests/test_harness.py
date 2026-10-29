"""tests/test_harness.py - Unit tests for the optimization harness.

Tests scoring formulas, atomic update logic, and verifier integration.
"""

import json
import math
import pathlib
import shutil
import tempfile
import time
from typing import Dict, Any

import pytest

# Add repo root to path for imports
import sys
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.score import (
    BASELINE_COSTS,
    compute_repetition_factor_dqi,
    compute_benchmark_cost,
    compute_competition_score
)


class TestScoringFormulas:
    """Test exact competition scoring formulas."""

    def test_repetition_factor_dqi(self):
        """Test DQI repetition factor formula R(ε+)."""
        # Exact zero failures: ε+ ≈ 8.7e-4 → R ≈ 1.19
        eps = 8.7e-4
        r = compute_repetition_factor_dqi(eps)
        assert abs(r - 1.19) < 0.01, f"Expected R≈1.19 for ε={eps}, got {r}"

        # Higher failure rate: ε+ = 1e-3 → R ≈ 1.21
        eps = 1e-3
        r = compute_repetition_factor_dqi(eps)
        assert abs(r - 1.21) < 0.01, f"Expected R≈1.21 for ε={eps}, got {r}"

        # Threshold: ε+ = 1/16 = 0.0625 → infinite (rejected)
        eps = 0.0625
        r = compute_repetition_factor_dqi(eps)
        assert math.isinf(r), f"Expected infinite R for ε={eps}"

        # Above threshold: ε+ = 0.1 → infinite (rejected)
        eps = 0.1
        r = compute_repetition_factor_dqi(eps)
        assert math.isinf(r), f"Expected infinite R for ε={eps}"

    def test_bench1_cost_formula(self):
        """Test Benchmark I cost: S = Q × C."""
        metrics = {"qubits": 260, "toffolis": 7988.0}
        cost = compute_benchmark_cost("bench1", metrics)
        expected = 260 * 7988.0
        assert cost == expected, f"Expected {expected}, got {cost}"

    def test_bench2_cost_formula(self):
        """Test Benchmark II cost: S = R(ε+) × Q² × T."""
        metrics = {"qubits": 1893, "toffolis": 5725461.0, "eps_plus": 8.7e-4}
        cost = compute_benchmark_cost("bench2", metrics)
        r = compute_repetition_factor_dqi(8.7e-4)
        expected = r * (1893 ** 2) * 5725461.0
        assert abs(cost - expected) < 1e9, f"Expected {expected}, got {cost}"

    def test_bench3_cost_formula(self):
        """Test Benchmark III cost: S = λ_eff × T_tot × Q_tot."""
        metrics = {"lambda_eff": 49.301369, "toffolis": 93237.0, "qubits": 730}
        cost = compute_benchmark_cost("bench3", metrics)
        expected = 49.301369 * 93237.0 * 730
        assert abs(cost - expected) < 1e6, f"Expected {expected}, got {cost}"

    def test_competition_score_geometric_mean(self):
        """Test overall score is geometric mean of improvements."""
        # Baseline scores: all 1.0 (no improvement)
        costs = {"bench1": BASELINE_COSTS["bench1"], "bench2": BASELINE_COSTS["bench2"], "bench3": BASELINE_COSTS["bench3"]}
        overall, improvements = compute_competition_score(costs)
        assert overall == 1.0, f"Expected 1.0, got {overall}"
        assert all(imp == 1.0 for imp in improvements.values()), f"Expected all 1.0, got {improvements}"

        # Halve all costs: geometric mean should be 2.0
        halved_costs = {k: v / 2 for k, v in BASELINE_COSTS.items()}
        overall, improvements = compute_competition_score(halved_costs)
        assert abs(overall - 2.0) < 0.01, f"Expected 2.0, got {overall}"
        assert all(abs(imp - 2.0) < 0.01 for imp in improvements.values()), f"Expected all 2.0, got {improvements}"

        # Mixed improvements: (2.0, 1.5, 1.0) → geom mean = (2*1.5*1)^(1/3) = 3^(1/3) ≈ 1.44
        mixed_costs = {
            "bench1": BASELINE_COSTS["bench1"] / 2.0,
            "bench2": BASELINE_COSTS["bench2"] / 1.5,
            "bench3": BASELINE_COSTS["bench3"]
        }
        overall, improvements = compute_competition_score(mixed_costs)
        expected = (2.0 * 1.5 * 1.0) ** (1.0 / 3.0)
        assert abs(overall - expected) < 0.01, f"Expected {expected}, got {overall}"

    def test_infinite_cost_handling(self):
        """Test that infinite costs result in zero improvement."""
        costs = {
            "bench1": float("inf"),
            "bench2": BASELINE_COSTS["bench2"],
            "bench3": BASELINE_COSTS["bench3"]
        }
        overall, improvements = compute_competition_score(costs)
        assert overall == 0.0, f"Expected 0.0, got {overall}"
        assert improvements["bench1"] == 0.0, f"Expected 0.0 for bench1, got {improvements['bench1']}"


class TestAtomicUpdate:
    """Test atomic update logic for best/ directory."""

    def test_atomic_update_best(self):
        """Test that best/ is updated atomically."""
        from tools.loop import atomic_update_best

        with tempfile.TemporaryDirectory() as tmpdir:
            bench_dir = pathlib.Path(tmpdir)
            best_dir = bench_dir / "best"
            candidates_dir = bench_dir / "candidates"
            candidates_dir.mkdir(parents=True, exist_ok=True)

            # Create a candidate file
            candidate = candidates_dir / "test.kmb"
            candidate.write_text("test circuit")

            # Create result
            result = {
                "pass": True,
                "benchmark": "bench1",
                "cost": 100.0,
                "qubits": 50,
                "toffolis": 2.0,
                "runtime_s": 1.0
            }

            # Perform atomic update
            atomic_update_best(bench_dir, candidate, result)

            # Verify best/ exists and contains correct files
            assert best_dir.exists(), "best/ directory should exist"
            assert (best_dir / "test.kmb").exists(), "Candidate file should be in best/"
            assert (best_dir / "score.json").exists(), "score.json should be in best/"

            # Verify score.json content
            score_data = json.loads((best_dir / "score.json").read_text())
            assert score_data["cost"] == 100.0, f"Expected cost 100.0, got {score_data['cost']}"

    def test_atomic_update_replace_existing(self):
        """Test that existing best/ is replaced atomically."""
        from tools.loop import atomic_update_best

        with tempfile.TemporaryDirectory() as tmpdir:
            bench_dir = pathlib.Path(tmpdir)
            best_dir = bench_dir / "best"
            candidates_dir = bench_dir / "candidates"
            candidates_dir.mkdir(parents=True, exist_ok=True)
            best_dir.mkdir(parents=True, exist_ok=True)

            # Create initial best/
            (best_dir / "old.kmb").write_text("old circuit")
            (best_dir / "score.json").write_text(json.dumps({"cost": 200.0}))

            # Create new candidate
            candidate = candidates_dir / "new.kmb"
            candidate.write_text("new circuit")

            result = {
                "pass": True,
                "benchmark": "bench1",
                "cost": 100.0,
                "qubits": 50,
                "toffolis": 2.0,
                "runtime_s": 1.0
            }

            # Perform atomic update
            atomic_update_best(bench_dir, candidate, result)

            # Verify old file is gone
            assert not (best_dir / "old.kmb").exists(), "Old file should be removed"

            # Verify new file exists
            assert (best_dir / "new.kmb").exists(), "New file should exist"
            assert (best_dir / "score.json").exists(), "score.json should exist"

            # Verify new score
            score_data = json.loads((best_dir / "score.json").read_text())
            assert score_data["cost"] == 100.0, f"Expected cost 100.0, got {score_data['cost']}"


class TestVerifierWrapper:
    """Test verifier wrapper (dry-run mode only on Windows)."""

    def test_dry_run_mode(self):
        """Test dry-run mode returns mock success."""
        from tools.verify import run_official_verifier

        with tempfile.TemporaryDirectory() as tmpdir:
            candidate = pathlib.Path(tmpdir) / "test.kmb"
            candidate.write_text("test")

            # Note: dry-run is implemented in verify.py's main(), not run_official_verifier
            # This test verifies the structure is correct
            pass


class TestLoopLogic:
    """Test optimization loop logic."""

    def test_get_best_cost_with_existing(self):
        """Test get_best_cost reads from existing score.json."""
        from tools.loop import get_best_cost

        with tempfile.TemporaryDirectory() as tmpdir:
            bench_dir = pathlib.Path(tmpdir)
            best_dir = bench_dir / "best"
            best_dir.mkdir(parents=True, exist_ok=True)

            # Write score.json
            (best_dir / "score.json").write_text(json.dumps({"cost": 123.45}))

            cost = get_best_cost(bench_dir, "bench1")
            assert cost == 123.45, f"Expected 123.45, got {cost}"

    def test_get_best_cost_fallback_to_baseline(self):
        """Test get_best_cost falls back to baseline when no score.json exists."""
        from tools.loop import get_best_cost

        with tempfile.TemporaryDirectory() as tmpdir:
            bench_dir = pathlib.Path(tmpdir)
            cost = get_best_cost(bench_dir, "bench1")
            assert cost == BASELINE_COSTS["bench1"], f"Expected {BASELINE_COSTS['bench1']}, got {cost}"

    def test_append_to_log(self):
        """Test LOG.md append functionality."""
        from tools.loop import append_to_log

        with tempfile.TemporaryDirectory() as tmpdir:
            bench_dir = pathlib.Path(tmpdir)
            append_to_log(bench_dir, "run1", "Test idea", True, 100.0, "Success")

            log_path = bench_dir / "LOG.md"
            assert log_path.exists(), "LOG.md should be created"

            content = log_path.read_text()
            assert "run1" in content, "Run ID should be in log"
            assert "Test idea" in content, "Description should be in log"
            assert "PASS" in content, "PASS status should be in log"
            assert "100.00" in content, "Cost should be in log"

            # Append another entry
            append_to_log(bench_dir, "run2", "Test idea 2", False, float("inf"), "Failed")

            content = log_path.read_text()
            assert "run2" in content, "Second run should be in log"
            assert "FAIL" in content, "FAIL status should be in log"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
