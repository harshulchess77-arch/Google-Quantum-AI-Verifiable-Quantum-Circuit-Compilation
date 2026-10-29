"""tools/score.py - Official competition evaluation metric computation.

Computes the geometric mean of improvement over baseline:
    Overall_Score = ( (REF_INVSQRT / cost_invsqrt) * (REF_DQI / cost_dqi) * (REF_DFTHCSOS / cost_dfthcsos) ) ** (1/3)

Reference Constants (from official leaderboard baseline):
    REF_INVSQRT  = 2076774.233715282
    REF_DQI      = 24439463583672.93
    REF_DFTHCSOS = 3355599588.3155375
"""

from __future__ import annotations

import argparse
import json
import math
from typing import Dict, Any


# Reference baseline costs from the official leaderboard.
# These are the exact baseline scores that the competition metric uses.
REF_INVSQRT = 2076774.233715282
REF_DQI = 24439463583672.93
REF_DFTHCSOS = 3355599588.3155375

BASELINE_COSTS = {
    "bench1": REF_INVSQRT,
    "bench2": REF_DQI,
    "bench3": REF_DFTHCSOS,
}


def compute_repetition_factor_dqi(eps_plus: float) -> float:
    """Computes R(eps+) for DQI (from verify_submission_dqi.py docstring).

    Formula: R(eps) = ln(2) / -ln(1/2 + 2*sqrt(eps))
    Rejected (infinite) if eps_plus >= 1/16 = 0.0625.
    """
    if eps_plus >= 0.0625:  # 1/16 threshold — strict; anything at or above is rejected
        return float("inf")
    inner = 0.5 + 2.0 * math.sqrt(eps_plus)
    if inner >= 1.0:
        return float("inf")
    return math.log(2.0) / (-math.log(inner))


def compute_benchmark_cost(benchmark: str, metrics: Dict[str, Any]) -> float:
    """Compute benchmark cost from component metrics."""
    if benchmark == "bench1":
        # score = Q * C
        q = metrics.get("qubits", 0)
        c = metrics.get("toffolis", 0.0)
        return float(q * c)
    elif benchmark == "bench2":
        # score = R(eps+) * Q^2 * T
        q = metrics.get("qubits", 0)
        t = metrics.get("toffolis", 0.0)
        eps_plus = metrics.get("eps_plus", 8.7e-4)
        r = compute_repetition_factor_dqi(eps_plus)
        return float(r * (q ** 2) * t)
    elif benchmark == "bench3":
        # score = lambda_eff * T_tot * Q_tot
        lambda_eff = metrics.get("lambda_eff", 20.5)
        t_tot = metrics.get("toffolis", 0.0)
        q_tot = metrics.get("qubits", 0)
        return float(lambda_eff * t_tot * q_tot)
    else:
        raise ValueError(f"Unknown benchmark: {benchmark}")


def compute_competition_score(candidate_costs: Dict[str, float]) -> tuple[float, Dict[str, float]]:
    """Compute overall Kaggle geometric mean improvement score.
    
    Returns:
        (overall_score, dict_of_improvements)
    """
    improvements = {}
    for bench, baseline_cost in BASELINE_COSTS.items():
        candidate_cost = candidate_costs.get(bench, baseline_cost)
        if candidate_cost <= 0.0 or math.isinf(candidate_cost):
            improvements[bench] = 0.0
        else:
            improvements[bench] = baseline_cost / candidate_cost

    ratios = list(improvements.values())
    if any(r <= 0.0 for r in ratios):
        overall = 0.0
    else:
        overall = math.prod(ratios) ** (1.0 / len(ratios))

    return overall, improvements


def main():
    parser = argparse.ArgumentParser(description="Competition score calculation.")
    parser.add_argument("--costs", type=str, help="JSON string with benchmark costs {'bench1': ..., ...}")
    args = parser.parse_args()

    if args.costs:
        costs = json.loads(args.costs)
    else:
        costs = BASELINE_COSTS

    overall, improvements = compute_competition_score(costs)
    result = {
        "overall_score": overall,
        "improvements": improvements,
        "candidate_costs": costs
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
