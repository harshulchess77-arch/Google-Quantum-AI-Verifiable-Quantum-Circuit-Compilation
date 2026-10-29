"""tools/verify.py - Official verifier execution wrapper.

ASSUMPTIONS:
1. When running on Linux (Devin/Kaggle), kickmix.so is accessible via sys.path pointing to
   google-verifiable-quantum-circuit-compilation/kickmix.
2. Official verifier scripts live in google-verifiable-quantum-circuit-compilation/verifiers/.
3. If running on Windows host where kickmix.so cannot be loaded natively, a mock/dry-run mode
   (--dry-run) simulates verifier output for harness pipeline testing.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys
import time
from typing import Any, Dict


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
COMP_DATA_DIR = REPO_ROOT / "google-verifiable-quantum-circuit-compilation"
VERIFIERS_DIR = COMP_DATA_DIR / "verifiers"
KICKMIX_DIR = COMP_DATA_DIR / "kickmix"


def run_official_verifier(benchmark: str, candidate_path: pathlib.Path, extra_args: list[str] | None = None, salt: str = "") -> Dict[str, Any]:
    """Execute the official verifier on a candidate and parse the output.
    
    Returns:
        JSON-compatible dict: {
            "pass": bool,
            "benchmark": str,
            "cost": float,
            "qubits": int,
            "toffolis": float,
            "runtime_s": float,
            "raw_output": str,
            "error": str | None,
            "metrics": dict  # Additional benchmark-specific metrics
        }
    """
    if benchmark not in ("bench1", "bench2", "bench3"):
        raise ValueError(f"Unknown benchmark: {benchmark}. Expected bench1, bench2, or bench3.")

    extra_args = extra_args or []
    start_time = time.time()
    
    # Path mappings to official scripts
    if benchmark == "bench1":
        script = VERIFIERS_DIR / "invsqrt" / "verify_submission_invsqrt.py"
        cmd = [sys.executable, str(script), str(candidate_path)] + extra_args
        if salt:
            cmd.extend(["--salt", salt])
    elif benchmark == "bench2":
        script = VERIFIERS_DIR / "dqi" / "verify_submission_dqi.py"
        cmd = [sys.executable, str(script), str(candidate_path)] + extra_args
        if salt:
            cmd.extend(["--salt", salt])
    elif benchmark == "bench3":
        script = VERIFIERS_DIR / "dfthcsos" / "verify.py"
        cmd = [sys.executable, str(script), str(candidate_path)] + extra_args
        if salt:
            cmd.extend(["--salt", salt])

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{KICKMIX_DIR}{os.pathsep}{VERIFIERS_DIR}{os.pathsep}{env.get('PYTHONPATH', '')}"

    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env, timeout=3600)
        elapsed = time.time() - start_time
        stdout = proc.stdout
        stderr = proc.stderr
        combined_output = f"{stdout}\n{stderr}".strip()

        # Check for JSON output from verifier
        parsed_result = None
        for line in reversed(stdout.splitlines()):
            line_str = line.strip()
            if line_str.startswith("{") and line_str.endswith("}"):
                try:
                    parsed_result = json.loads(line_str)
                    break
                except json.JSONDecodeError:
                    continue

        if proc.returncode == 0 and parsed_result and parsed_result.get("status") == "PASS":
            cost = parsed_result.get("score", 0.0)
            result = {
                "pass": True,
                "benchmark": benchmark,
                "cost": float(cost),
                "qubits": parsed_result.get("num_qubits", 0),
                "toffolis": parsed_result.get("toffoli_equivalent", parsed_result.get("toffoli_count", 0.0)),
                "runtime_s": elapsed,
                "raw_output": combined_output[-2000:],
                "error": None,
                "metrics": parsed_result
            }
            return result
        else:
            error_msg = stderr.strip() or stdout.strip() or f"Process exited with return code {proc.returncode}"
            if parsed_result and parsed_result.get("status") == "FAIL":
                error_msg = parsed_result.get("error", error_msg)
            return {
                "pass": False,
                "benchmark": benchmark,
                "cost": float("inf"),
                "qubits": 0,
                "toffolis": 0.0,
                "runtime_s": elapsed,
                "raw_output": combined_output[-2000:],
                "error": error_msg
            }
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start_time
        return {
            "pass": False,
            "benchmark": benchmark,
            "cost": float("inf"),
            "qubits": 0,
            "toffolis": 0.0,
            "runtime_s": elapsed,
            "raw_output": "",
            "error": f"Verifier timeout after 3600 seconds"
        }
    except Exception as e:
        elapsed = time.time() - start_time
        return {
            "pass": False,
            "benchmark": benchmark,
            "cost": float("inf"),
            "qubits": 0,
            "toffolis": 0.0,
            "runtime_s": elapsed,
            "raw_output": "",
            "error": str(e)
        }


def main():
    parser = argparse.ArgumentParser(description="Official verifier wrapper.")
    parser.add_argument("benchmark", choices=["bench1", "bench2", "bench3"], help="Target benchmark.")
    parser.add_argument("candidate", type=pathlib.Path, help="Path to candidate circuit file or directory.")
    parser.add_argument("--dry-run", action="store_true", help="Simulate execution without kicking off verifier.")
    parser.add_argument("--salt", type=str, default="", help="Salt for verification (helps test robustness).")
    args, unknown = parser.parse_known_args()

    if args.dry_run:
        # Use baseline costs for dry-run
        from tools.score import BASELINE_COSTS
        result = {
            "pass": True,
            "benchmark": args.benchmark,
            "cost": BASELINE_COSTS[args.benchmark],
            "qubits": 260 if args.benchmark == "bench1" else (1893 if args.benchmark == "bench2" else 730),
            "toffolis": 7988.0 if args.benchmark == "bench1" else (5725461.0 if args.benchmark == "bench2" else 93237.0),
            "runtime_s": 0.01,
            "raw_output": "DRY RUN MOCK SUCCESS",
            "error": None
        }
    else:
        result = run_official_verifier(args.benchmark, args.candidate, unknown, args.salt)

    print(json.dumps(result, indent=2))
    sys.exit(0 if result["pass"] else 1)


if __name__ == "__main__":
    main()
