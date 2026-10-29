# Repository Ground Truth: Exact Specifications

**Document Target:** `notes/repo_ground_truth.md`  
**Classification Guide:** Every technical requirement is marked as `[FROM SOURCE]`, `[INFERENCE]`, or `[UNKNOWN]`.  
**Purpose:** Extract the exact ground-truth verifier and scoring specifications to guide the optimization harness.

---

## 1. Official Competition Metric [FROM SOURCE]

### Overall Scoring Formula
The competition score is the geometric mean of each task's improvement relative to a baseline [FROM SOURCE]:

```
Overall_Score = (Product over benchmarks of (Baseline_Cost_i / Candidate_Cost_i))^(1/3)
```

The hosts' reference submissions score 1.0, and halving every benchmark's cost scores 2.0 [FROM SOURCE].

### Benchmark-Specific Cost Functions [FROM SOURCE]

| Benchmark | Cost Formula | Variables |
|-----------|--------------|-----------|
| **invsqrt** (Benchmark I) | `S = Q × C` | Q = qubit count, C = Toffoli-equivalents per shot |
| **dqi** (Benchmark II) | `S = R(ε+) × Q² × T` | R(ε+) = repetition factor, Q = qubits, T = Toffoli count |
| **dfthcsos** (Benchmark III) | `S = λ_eff × T_tot × Q_tot` | λ_eff = spectrum-amplified normalization, T_tot = total Toffolis, Q_tot = total qubits |

---

## 2. Benchmark I: invsqrt (Fusion Energy) [FROM SOURCE]

### Problem Contract
- **Input:** A 22-qubit named register `"x"`, with integer `x ∈ [1, max_x]` where `max_x = 3(2^10 - 2)^2 = 3,133,452` (n_p = 10, β = 1) [FROM SOURCE].
- **Output:** Phase kickback `exp(2πi β / √x)` with relative phase error within `tol(x) = 2^(-24) β / √x` turns [FROM SOURCE].
- **Registers:** Input register `"x"` must be restored identically; all scratch ancillas must be cleanly returned to `|0⟩` [FROM SOURCE].

### Verification Strategy [FROM SOURCE]
- Every input `x ∈ [1, max_x]` is simulated `shots_per_x = 64` times (200,540,928 total shots) [FROM SOURCE].
- The simulator PRNG is seeded from the SHA-256 digest of the circuit's canonical `.kmb` binary serialization combined with a competition salt [FROM SOURCE].
- On each shot, the tracked phase θ(x) (in turns, modulo 1) is checked in 64-bit fixed point (uint64 units of 2^(-64) turns) against exact integer square-root arithmetic `⌊2^65 β / √x⌋ = isqrt(⌊2^130 β² / x⌋)` [FROM SOURCE].
- Every shot must pass (k = 0 failures) within tolerance `tol(x) = 2^(-24) β / √x` turns [FROM SOURCE].

### Cost Formula [FROM SOURCE]
```
S = Q × C
Q = circuit's total qubit count
C = Toffolis + T/4 (mean Toffoli-equivalent cost per shot)
  - Clifford Z_POW angles are free
  - T-angles cost 1 T
  - Each of the n_rot finer Z_POW rotations is priced analytically via mixed fallback synthesis at 0.56 log₂(1/ε) + 5.3 T-gates
```

### Baseline Performance [FROM SOURCE]
- Q = 260 qubits
- Toffoli gates = 7,735
- T gates = 1
- Non-Clifford Z_POW rotations = 37
- Toffoli-equivalent cost C = 7,988
- Space-time score S = Q × C = 2.08 × 10^6
- Worst-case relative error = 2.84 × 10^(-8) = 2^(-25.07) (at x = 2,588,411)

### Verifier Script [FROM SOURCE]
- Location: `verifiers/invsqrt/verify_submission_invsqrt.py`
- Reference circuit generator: `verifiers/invsqrt/nr_reference_circuit.py`
- Function signature: `verify_submission_invsqrt.verify(circuit, problem_spec, salt)`

---

## 3. Benchmark II: dqi (Combinatorial Optimization) [FROM SOURCE]

### Problem Contract
- **Parameters:** RS(4095, 4025) over GF(2^12) with parameters (m, n, b, r) = (4095, 70, 12, 2016) [FROM SOURCE].
- **Input:** Syndrome register `s = BT e` (70 × 12 = 840 qubits) and classical measurement record `c` (4095 × 12 = 49,140 bits) [FROM SOURCE].
- **Output:** Apply phase correction `(-1)^(c·bin(e))` to syndrome state |s⟩ [FROM SOURCE].
- **Error tolerance:** Decoding failures are allowed but increase cost via repetition factor R(ε+) [FROM SOURCE].

### Verification Strategy [FROM SOURCE]
- Verifier samples error vector e ~ |a_e|² with wt(e) ≤ ℓ = 35 [FROM SOURCE].
- Weight distribution follows eigenvector v of tridiagonal matrix A [FROM SOURCE].
- Conditioned on wt(e) = w, draws w distinct error positions uniformly and each nonzero symbol uniformly from F_q \ {0} [FROM SOURCE].
- Computes syndrome s = BT e and samples record c uniformly at random [FROM SOURCE].
- Tests k failed shots out of N = 102,400, computes upper confidence bound ε+ on ε at confidence level 1 - 2^(-128) [FROM SOURCE].

### Cost Formula [FROM SOURCE]
```
S = R(ε+) × Q² × T
R(ε) = ln(2) / -ln(1/2 + 2√ε)  (repetition factor)
Q = total qubit count (syndrome plus workspace)
T = single-run Toffoli count (including workspace cleanup)
```
- Factor Q²T measures single-run cost, so 1% reduction in qubits improves score as much as 2% reduction in Toffoli gates [FROM SOURCE].
- If ε+ ≥ 1/16, submission receives no finite score [FROM SOURCE].
- With zero failures in N = 102,400 shots, ε+ ≈ 8.7 × 10^(-4), so R(ε+) ≈ 1.19 [FROM SOURCE].

### Baseline Performance [FROM SOURCE]
- Q = 1,893 qubits
- Toffoli gates = 5,725,461 (after Step 3 cleanup)
- Estimated score: R(ε+) ≈ 1.19, Q² = 3,583,449, T = 5,725,461 → S ≈ 2.44 × 10^13

### Verifier Script [FROM SOURCE]
- Location: `verifiers/dqi/verify_submission_dqi.py`
- Reference circuit generator: `verifiers/dqi/dqi_reference_circuit.py`
- Function signature: `verify_submission_dqi.verify(circuit, problem_spec, salt)`

---

## 4. Benchmark III: dfthcsos (Quantum Chemistry) [FROM SOURCE]

### Problem Contract
- **System:** FeMoCo76o113e (N = 76 orbitals, η = 113 electrons) [FROM SOURCE].
- **Input:** Factorization parameters (R, B, C ranks, vectors u^(ρ)_b, weights w^(ρc)_b, W^(ρc)), Givens tree, and ANGLE_k circuits [FROM SOURCE].
- **Output:** Block encoding of DFTHC Hamiltonian with Frobenius error ≤ 20 mHa [FROM SOURCE].
- **Constraints:**
  - Any ANGLE_k circuit using > 128 qubits is rejected [FROM SOURCE].
  - Encoded Hamiltonian deviation > 20 mHa from reference is rejected [FROM SOURCE].
  - LCU normalization exceeds allowed limits is rejected [FROM SOURCE].

### Verification Strategy [FROM SOURCE]
- Simulates every valid vector address with 64 measurement samples per address [FROM SOURCE].
- Checks consistent angle words, unchanged addresses, clean workspace, and corrected phases during forward and reverse traversal [FROM SOURCE].
- Recovers words to determine vectors used in subsequent calculations [FROM SOURCE].
- Constructs X^(ρc) and h¹' from decoded vectors [FROM SOURCE].
- Matches decoded one-body vectors to eigenvectors of h¹' and reconstructs ~h¹' [FROM SOURCE].
- Acceptance requires:
  - ε₁ = ||~h¹' - h¹'||_F ≤ 0.020 Ha [FROM SOURCE]
  - ε₂ = ||Σ_(ρ,c) X^(ρc) ⊗ X^(ρc) - h² - T(S₀)||_F ≤ 0.020 Ha [FROM SOURCE]
- Recomputes Λ and E_SOS with fixed E_upper = -22140.27335 Ha [FROM SOURCE].
- All metrics must be finite, with 0 < E_gap < 2Λ, E_gap > 3.914898 Ha, and Λ > 49.0 Ha [FROM SOURCE].

### Cost Formula [FROM SOURCE]
```
S = λ_eff × T_tot × Q_tot
λ_eff = √(E_gap × (2Λ - E_gap))  (spectrum-amplified block-encoding one-norm)
T_tot = simulated Toffoli count of Angle_k circuits (forward + reverse) + heuristic costs of Outer, Inner, and N-1 Givens rotations
Q_tot = persistent qubits (state-preparation registers + J_b rot angle-word registers) + largest temporary workspace among Outer, Inner, and Angle_k circuits
```

### Baseline Performance [FROM SOURCE]
- λ_eff = 49.301369
- T_total = 93,237
- Q_total = 730
- Score = λ_eff × T_total × Q_total = 3,355,599,588.3155365

### Verifier Script [FROM SOURCE]
- Location: `verifiers/dfthcsos/verify.py`
- Reference submission directory: `verifiers/dfthcsos/example_submission/`
- Scoring README: `verifiers/dfthcsos/SCORING_README.md`
- Function signature: `dfthcsos.verify(angle_circuits, npz, tree_edges, salt, shots_per_address)`

---

## 5. Submission File Format [FROM SOURCE]

### Required Files
A submission must be a zip archive containing:
- `invsqrt.kmb` or `invsqrt.kmx` (Benchmark I)
- `dqi.kmb` or `dqi.kmx` (Benchmark II)
- A folder named `dfthcsos` containing:
  - Circuits `angle_k_0`, `angle_k_1`, … `angle_k_<n-1>` (numbered from 0 with no gaps), each as `.kmb` or `.kmx`
  - `submission.npz` holding the factorization (U, W, H2_I, H1_I, Hsym_lower) and the Givens tree (tree_edges)

### Kickmix Format [FROM SOURCE]
- `.kmx`: text format (human-readable)
- `.kmb`: binary format (compact, used for submission)
- Both formats are supported by kickmix and verifiers

### Allowed Instructions [FROM SOURCE]
```
ALLOWED_INSTRUCTIONS = {
    'X', 'CX', 'CCX', 'Z', 'CZ', 'CCZ', 'Z_POW', 'NEG', 'SWAP', 'CSWAP', 'R', 'HMR',
    'BIT_INVERT', 'BIT_STORE0', 'BIT_STORE1', 'PUSH_CONDITION', 'POP_CONDITION',
    'INFO_TAG', 'DEBUG_PRINT'
}
```

### Circuit Constraints [FROM SOURCE]
- Maximum qubit or bit ID: 2^30 // 1536 (to cap memory growth at ~1 GB)
- Maximum registers: benchmark-specific (e.g., invsqrt allows 1, dqi allows n + m = 70 + 4095 = 4165)
- Every register must be named (dfthcsos verifier crashes on unnamed registers)

---

## 6. Environment Setup [FROM SOURCE]

### Python Path Requirements
To import kickmix and verifiers:
```python
import sys
sys.path += [
    'google-verifiable-quantum-circuit-compilation/kickmix',
    'google-verifiable-quantum-circuit-compilation/verifiers'
]
import kickmix
```

### Dependencies
- numpy
- scipy (for tensor operations in dfthcsos)
- kickmix (C++20 SIMD simulator via kickmix.so on Linux)

### Platform Constraints
- kickmix.so is compiled for Linux glibc [FROM SOURCE].
- On Windows, kickmix.so cannot be loaded natively; requires Linux environment or mock mode for testing.

---

## 7. Scoring Time Estimate [FROM SOURCE]
Scoring takes roughly 45 minutes per submission on the Kaggle infrastructure.

---

## 8. Sample Submission Baseline Costs [FROM SOURCE]

From the sample_submission directory:
- `invsqrt.kmb`: 579,721 bytes
- `dqi.kmb`: 886,118,180 bytes
- `dfthcsos/`: contains 10 angle circuits and submission.npz

The reference submissions score 1.0 on the leaderboard.

---

## 9. Safety Rules (Non-Negotiable) [FROM SOURCE]

1. The official verifiers are sacred ground truth. Never weaken, modify, mock, bypass, or special-case them.
2. Treat `third_party/` and `bench*/baseline/` as strictly READ-ONLY.
3. Write every generated circuit to `bench*/candidates/` using `<timestamp>_<short_sha256>.<ext>`.
4. Update `bench*/best/` atomically (write to temporary file, then os.replace) and ONLY when `pass == True` AND `candidate_cost < current_best_cost`.
5. Never reimplement verification logic inside the harness—always invoke the official standalone verifier binary/script.
