# Verifiable Quantum Circuit Compilation

Autonomous optimization harness for Google Quantum AI's Kaggle competition: **"Verifiable Quantum Circuit Compilation"** ($150,000 prize pool).

## Overview

This repository provides a production-grade toolchain for optimizing quantum circuits targeting three real-world bottlenecks in fusion energy, combinatorial optimization, and quantum chemistry. The harness implements closed verification loops using AI agents, classical optimization, and algorithmic insights to find smaller, faster circuit compilations while strictly passing the official kickmix verifiers.

## Competition Summary

**Goal:** Minimize the geometric mean of improvement across three benchmarks:

```
Overall_Score = ( (REF_INVSQRT / cost_invsqrt) × (REF_DQI / cost_dqi) × (REF_DFTHCSOS / cost_dfthcsos) )^(1/3)
```

**Reference Baselines:**
- `REF_INVSQRT` = 2,076,774.23 (Fusion Energy - 1/√x phasing)
- `REF_DQI` = 24,439,463,583,672.93 (Combinatorial Optimization - Reed-Solomon decoder)
- `REF_DFTHCSOS` = 3,355,599,588.32 (Quantum Chemistry - FeMoCo block encoding)

**Target Score:** > 26.14113 (requires geometric mean improvement > 17,863.8×)

## Live Scoreboard

| Benchmark | Current Cost | Reference Cost | Improvement | Status |
|-----------|--------------|----------------|-------------|--------|
| **invsqrt** (Fusion) | 2,076,774.23 | 2,076,774.23 | 1.0× | Baseline |
| **dqi** (Optimization) | 24,439,463,583,672.93 | 24,439,463,583,672.93 | 1.0× | Baseline |
| **dfthcsos** (Chemistry) | 3,355,599,588.32 | 3,355,599,588.32 | 1.0× | Baseline |
| **Overall Score** | **1.0** | **1.0** | **1.0×** | Baseline |

*Last updated: 2026-10-28*

## Benchmarks

### Benchmark I: invsqrt (Fusion Energy)
- **Problem:** Compute phase kickback `exp(2πi β / √x)` for all `x ∈ [1, 3,133,452]`
- **Cost Formula:** `S = Q × C` (qubits × Toffoli-equivalents)
- **Tolerance:** Relative phase error ≤ 2⁻²⁴
- **Verfier:** `verifiers/invsqrt/verify_submission_invsqrt.py`

### Benchmark II: dqi (Combinatorial Optimization)
- **Problem:** Reversible Reed-Solomon syndrome decoder for Decoded Quantum Interferometry
- **Cost Formula:** `S = R(ε+) × Q² × T` (repetition factor × qubits² × Toffolis)
- **Tolerance:** Upper confidence bound `ε+ < 1/16` on failure rate
- **Verifier:** `verifiers/dqi/verify_submission_dqi.py`

### Benchmark III: dfthcsos (Quantum Chemistry)
- **Problem:** DF-THC block encoding of FeMoCo76o113e nitrogenase catalyst
- **Cost Formula:** `S = λ_eff × T_tot × Q_tot` (spectrum-amplified normalization × Toffolis × qubits)
- **Constraints:** `error_1 ≤ 20 mHa`, `error_2 ≤ 20 mHa`, `Λ > 49`, `E_gap > 3.914898 Ha`, Q ≤ 128 per circuit
- **Verifier:** `verifiers/dfthcsos/verify.py`

## Repository Structure

```
.
├── third_party/               # READ-ONLY: Official kickmix, Qualtran, verifiers
├── notes/                      # Technical documentation and analysis
│   ├── repo_ground_truth.md   # Exact verifier specifications
│   └── paper_summary.md       # Companion paper summary
├── tools/                     # Optimization toolchain
│   ├── score.py              # Competition metric calculator
│   ├── verify.py             # Multi-salt verifier wrapper
│   ├── loop.py               # Autonomous optimization loop
│   ├── build_submission.py   # Submission.zip builder
│   └── passes/               # Modular optimization passes
├── tests/                     # Pytest unit tests
├── bench1/                    # Benchmark I: invsqrt
│   ├── baseline/             # Reference circuit
│   ├── candidates/           # Generated candidates
│   ├── best/                 # Verified best circuit
│   ├── analysis.md           # Optimization strategy
│   └── LOG.md                # Experiment log
├── bench2/                    # Benchmark II: dqi
│   ├── baseline/
│   ├── candidates/
│   ├── best/
│   ├── analysis.md
│   └── LOG.md
└── bench3/                    # Benchmark III: dfthcsos
    ├── baseline/
    ├── candidates/
    ├── best/
    ├── analysis.md
    └── LOG.md
```

## Installation

### Prerequisites
- Python 3.10+
- Linux environment with glibc (required for kickmix.so)
- Dependencies: numpy, scipy

### Setup
```bash
# Clone repository
git clone <repository-url>
cd quantum-circuit-competition

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

## Usage

### Verify Baseline Circuits
```bash
make verify
# Or directly:
python -m tools.verify bench1 bench1/baseline/invsqrt.kmb
python -m tools.verify bench2 bench2/baseline/dqi.kmb
python -m tools.verify bench3 bench3/baseline/dfthcsos
```

### Calculate Competition Score
```bash
make score
# Or directly:
python -m tools.score
```

### Run Optimization Loop
```bash
# Dry-run (testing harness logic)
python -m tools.loop bench1 --baseline --dry-run

# Full optimization with multi-salt verification (dqi)
python -m tools.loop bench2 --salts "salt1,salt2,salt3,salt4,salt5"
```

### Build Submission
```bash
make submission
# Or directly:
python -m tools.build_submission --verify
```

### Run Tests
```bash
make test
# Or directly:
python -m pytest tests/ -v
```

## Safety Rules

1. **READ-ONLY Zones:** Never modify `third_party/` or `bench*/baseline/`
2. **Atomic Updates:** Candidates only accepted to `bench*/best/` when `pass == True` AND `cost < best_cost`
3. **Official Verifiers:** Never bypass or reimplement verification logic
4. **Linux Requirement:** kickmix.so requires Linux glibc; use `--dry-run` on Windows for testing

## Optimization Strategy

### Universal Passes (All Benchmarks)
- Wire liveness analysis and ancilla recycling
- Gate cancellation and commutation
- CSWAP decomposition optimization
- Measurement-based uncomputation (HMR)

### Benchmark-Specific Optimizations
- **invsqrt:** Precision tuning, polynomial approximation, multiplier pruning
- **dqi:** Qubit compaction (high leverage due to Q² in cost), GF(2) product sharing
- **dfthcsos:** Angle word packing, bit-width optimization, factorization rank tuning

## Verification

The official verifiers in `third_party/verifiers/` are the ground truth. They:
- Fuzz-test circuits on classical bitstring inputs
- Seed tests with SHA-256 digest of candidate circuit (Fiat-Shamir heuristic)
- Check exact restoration of registers and clean ancilla states
- Verify phase accuracy within specified tolerances

## Competition Timeline

- **Start:** October 22, 2026
- **Mid-Competition Milestone:** November 20, 2026 ($10,000 prize)
- **Longest Leader Prize:** January 4, 2027 ($10,000 prize)
- **Entry Deadline:** January 13, 2027
- **Final Submission Deadline:** January 20, 2027

## License

Apache 2.0 - See [LICENSE](LICENSE) for details.

## Acknowledgments

- Google Quantum AI for the competition and verifiers
- Qualtran library for kickmix circuit simulation
- Competition participants and contributors

## Citation

```bibtex
@misc{quantum_circuit_competition_2026,
  title={Verifiable Quantum Circuit Compilation},
  author={Competition Contributors},
  year={2026},
  howpublished={Kaggle Competition},
  url={https://www.kaggle.com/competitions/google-verifiable-quantum-circuit-compilation}
}
```
