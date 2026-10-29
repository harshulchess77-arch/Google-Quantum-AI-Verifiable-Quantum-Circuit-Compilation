"""tools/loop.py - Autonomous optimization search loop.

Workflow:
    Propose Candidate -> Write Candidate -> Verify via tools/verify.py ->
    Accept iff (pass == True AND cost < best_cost) ->
    Atomic Update to bench*/best/ -> Append to bench*/LOG.md
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import pathlib
import shutil
import sys
import time
from typing import Callable, Dict, Any

from tools.score import BASELINE_COSTS, compute_competition_score
from tools.verify import run_official_verifier


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


def get_best_cost(bench_dir: pathlib.Path, benchmark: str) -> float:
    """Read the current best cost from best/ or fallback to baseline."""
    best_file = bench_dir / "best" / "score.json"
    if best_file.exists():
        try:
            data = json.loads(best_file.read_text())
            return float(data.get("cost", BASELINE_COSTS[benchmark]))
        except Exception:
            pass
    return BASELINE_COSTS[benchmark]


def atomic_update_best(bench_dir: pathlib.Path, candidate_path: pathlib.Path, result: Dict[str, Any]) -> None:
    """Atomically update the best/ directory with the newly accepted candidate."""
    best_dir = bench_dir / "best"
    temp_best = bench_dir / "temp_best"
    if temp_best.exists():
        shutil.rmtree(temp_best)
    temp_best.mkdir(parents=True, exist_ok=True)

    # Copy candidate files
    if candidate_path.is_dir():
        shutil.copytree(candidate_path, temp_best / candidate_path.name)
    else:
        shutil.copy2(candidate_path, temp_best / candidate_path.name)

    # Write score metadata
    (temp_best / "score.json").write_text(json.dumps(result, indent=2))

    # Atomic swap
    if best_dir.exists():
        backup_dir = bench_dir / "best_old"
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
        best_dir.rename(backup_dir)
        temp_best.rename(best_dir)
        shutil.rmtree(backup_dir)
    else:
        temp_best.rename(best_dir)


def append_to_log(bench_dir: pathlib.Path, run_id: str, description: str, passed: bool, cost: float, notes: str) -> None:
    """Append the iteration outcome to LOG.md."""
    log_path = bench_dir / "LOG.md"
    if not log_path.exists():
        log_path.write_text("# Experiment Log\n\n| Run ID | Idea / Description | Validated | Cost | Notes |\n|---|---|---|---|---|\n")

    status_str = "PASS" if passed else "FAIL"
    cost_str = f"{cost:,.2f}" if cost < float("inf") else "INF"
    line = f"| `{run_id}` | {description} | {status_str} | {cost_str} | {notes} |\n"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line)


def baseline_proposer(benchmark: str) -> Callable[[int], tuple[pathlib.Path, str]]:
    """Propose the baseline circuit for initial verification."""
    def proposer(it: int) -> tuple[pathlib.Path, str]:
        if benchmark == "bench1":
            baseline_path = REPO_ROOT / "bench1" / "baseline" / "invsqrt.kmb"
        elif benchmark == "bench2":
            baseline_path = REPO_ROOT / "bench2" / "baseline" / "dqi.kmb"
        elif benchmark == "bench3":
            baseline_path = REPO_ROOT / "bench3" / "baseline" / "dfthcsos"
        else:
            raise ValueError(f"Unknown benchmark: {benchmark}")
        return baseline_path, f"Baseline verification from sample_submission"
    return proposer


def run_search_loop(
    benchmark: str,
    proposer_fn: Callable[[int], tuple[pathlib.Path, str]],
    max_iterations: int = 10,
    wall_clock_budget_s: float = 3600.0,
    dry_run: bool = False,
    salts: list[str] | None = None
) -> None:
    """Execute the optimization loop."""
    bench_dir = REPO_ROOT / benchmark
    best_cost = get_best_cost(bench_dir, benchmark)
    start_time = time.time()

    print(f"[{benchmark.upper()}] Starting search loop. Initial Best Cost: {best_cost:,.2f}")

    for it in range(1, max_iterations + 1):
        if time.time() - start_time > wall_clock_budget_s:
            print(f"[{benchmark.upper()}] Wall-clock budget exceeded ({wall_clock_budget_s}s). Halting.")
            break

        run_id = f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{it}"
        candidate_path, idea_desc = proposer_fn(it)

        print(f"[{benchmark.upper()} Iteration {it}/{max_iterations}] Testing candidate: {idea_desc}")

        # For dqi, test multiple salts to ensure robustness
        if benchmark == "bench2" and salts:
            results = []
            for salt in salts:
                if dry_run:
                    # For baseline, use exact cost; for optimization tests, simulate improvement
                    if "baseline" in idea_desc.lower():
                        test_cost = best_cost
                    else:
                        test_cost = best_cost * 0.95
                    result = {
                        "pass": True,
                        "benchmark": benchmark,
                        "cost": test_cost,
                        "qubits": 1800,
                        "toffolis": 5000000.0,
                        "runtime_s": 0.05,
                        "raw_output": f"Dry run mock (salt={salt})",
                        "error": None
                    }
                else:
                    result = run_official_verifier(benchmark, candidate_path, salt=salt)
                results.append(result)
                if not result["pass"]:
                    break
            
            # Use the worst cost across all salts for conservative scoring
            result = results[0]
            if all(r["pass"] for r in results):
                result["cost"] = max(r["cost"] for r in results)
                result["notes"] = f"Verified across {len(salts)} salts, max cost: {result['cost']:,.2f}"
            else:
                result["pass"] = False
                result["error"] = f"Failed on one or more salts: {[r['error'] for r in results if not r['pass']]}"
        else:
            if dry_run:
                # For baseline verification, use exact baseline cost
                if "baseline" in idea_desc.lower():
                    test_cost = best_cost
                else:
                    test_cost = best_cost * 0.95
                result = {
                    "pass": True,
                    "benchmark": benchmark,
                    "cost": test_cost,
                    "qubits": 260 if benchmark == "bench1" else (1893 if benchmark == "bench2" else 730),
                    "toffolis": 7988.0 if benchmark == "bench1" else (5725461.0 if benchmark == "bench2" else 93237.0),
                    "runtime_s": 0.05,
                    "raw_output": "Dry run mock",
                    "error": None
                }
            else:
                result = run_official_verifier(benchmark, candidate_path)

        passed = result["pass"]
        cost = result["cost"]

        if passed and cost < best_cost:
            improvement = (best_cost - cost) / best_cost * 100
            notes = f"Accepted! Improved cost by {improvement:.2f}% (Previous: {best_cost:,.2f} -> New: {cost:,.2f})"
            if "notes" in result:
                notes += f" | {result['notes']}"
            print(f"  --> {notes}")
            atomic_update_best(bench_dir, candidate_path, result)
            best_cost = cost
        else:
            reason = result.get("error") or (f"Cost {cost:,.2f} >= Best {best_cost:,.2f}")
            notes = f"Rejected. Reason: {reason}"
            print(f"  --> {notes}")

        append_to_log(bench_dir, run_id, idea_desc, passed, cost, notes)

    print(f"[{benchmark.upper()}] Search finished. Final Best Cost: {best_cost:,.2f}")


def main():
    parser = argparse.ArgumentParser(description="Autonomous search loop.")
    parser.add_argument("benchmark", choices=["bench1", "bench2", "bench3"], help="Target benchmark.")
    parser.add_argument("--max-iters", type=int, default=5, help="Maximum iterations.")
    parser.add_argument("--budget-s", type=float, default=1800.0, help="Wall-clock time limit in seconds.")
    parser.add_argument("--dry-run", action="store_true", help="Execute loop logic in dry-run mode.")
    parser.add_argument("--baseline", action="store_true", help="Verify baseline circuit instead of using dummy proposer.")
    parser.add_argument("--salts", type=str, default="", help="Comma-separated list of salts for multi-salt verification (dqi only).")
    args = parser.parse_args()

    proposer = baseline_proposer(args.benchmark) if args.baseline else None
    if proposer is None:
        # Default dummy proposer for testing
        def dummy_proposer(it: int) -> tuple[pathlib.Path, str]:
            dummy_path = REPO_ROOT / args.benchmark / "candidates" / f"candidate_{it}.kmb"
            dummy_path.parent.mkdir(parents=True, exist_ok=True)
            dummy_path.touch(exist_ok=True)
            return dummy_path, f"Hypothesis {it}: test optimization"
        proposer = dummy_proposer

    salts_list = args.salts.split(",") if args.salts else None
    run_search_loop(args.benchmark, proposer, max_iterations=args.max_iters, wall_clock_budget_s=args.budget_s, dry_run=args.dry_run, salts=salts_list)


if __name__ == "__main__":
    main()
