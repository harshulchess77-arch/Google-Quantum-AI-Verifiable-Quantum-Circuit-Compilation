# Benchmark I Analysis: Phasing by 1/√x (Fusion Energy)

**Document Target:** `notes/bench1_analysis.md`  
**Classification Guide:** Every assertion is marked as `[FROM SOURCE]`, `[INFERENCE]`, or `[UNKNOWN]`.

---

## 1. What This Circuit Computes & Why It Is a Bottleneck

### Scientific Role
In inertial confinement fusion simulation, calculating alpha-particle stopping power in warm dense plasmas requires modeling the step-by-step (Trotterized) time-evolution of $\eta = 218$ electrons on a 3D grid [FROM SOURCE]. 
The potential energy operator involves pairwise Coulomb repulsion:
$$V = \sum_{i \neq j=1}^\eta \frac{1}{|r_i - r_j|} = \sum_{i \neq j=1}^\eta \frac{1}{\sqrt{(x_i - x_j)^2 + (y_i - y_j)^2 + (z_i - z_j)^2}} \quad \text{[FROM SOURCE]}$$
For $\eta = 218$ electrons, there are $\binom{218}{2} = 23,653$ pairs of electrons per Trotter step [FROM SOURCE]. In each step, the circuit computes $w = |\Delta r|^2$, phases by $e^{2\pi i \beta / \sqrt{w}}$, and uncomputes scratch work back to clean $|0\rangle$ [FROM SOURCE]. This single subroutine dominates over 90% of the entire fault-tolerant simulation cost [FROM SOURCE].

### Problem Contract
- **Input:** A 22-qubit named register `"x"`, with integer $x \in [1, \max_x]$ where $\max_x = 3(2^{10} - 2)^2 = 3,133,452$ ($n_p = 10$, $\beta = 1$) [FROM SOURCE].
- **Output:** Phase kickback $\exp(2\pi i \beta / \sqrt{x})$ with relative phase error within $\text{tol}(x) = 2^{-24} \beta / \sqrt{x}$ turns [FROM SOURCE].
- **Registers:** Input register `"x"` must be restored identically; all scratch ancillas must be cleanly returned to $|0\rangle$ [FROM SOURCE].

---

## 2. Baseline Architecture & Cost Breakdown

The baseline circuit is structured in three consecutive arithmetic stages [FROM SOURCE]:
1. **Mantissa Normalization (`_normalize`):** Counts leading zero pairs $s$ into a 10-qubit unary flag register and bit-shifts $x$ in-place to $x_{\text{norm}} = x \cdot 2^{2s} \in [1, 4)$ [FROM SOURCE].
2. **Initial Seed Approximation (`_horner`):** Decodes the top 3 bits of $x_{\text{norm}}$ via a 2-Toffoli QROM to select one of 4 polynomial coefficient sets, then evaluates a cubic polynomial $y_0 \approx 1/\sqrt{x_{\text{norm}}}$ via in-place Horner's rule [FROM SOURCE].
3. **Newton-Raphson Iteration & Denormalization:** Computes $z = x_{\text{norm}} \cdot y_0^2$, forms $3 - z$, multiplies $p = y_0(3 - z) \approx 2/\sqrt{x_{\text{norm}}}$, denormalizes by shifting $y_1 = p \ll s$, phases each bit of $y_1$ with `Z_POW`, and uncomputes all stages in reverse [FROM SOURCE].

### Baseline Cost Share Table

| Subroutine / Component | Qubits Used | Estimated Toffolis (Fwd + Rev) | Gate Cost Share | Dominance Rank |
| :--- | :--- | :--- | :--- | :--- |
| **Horner Multipliers (`_horner`)** | Shared scratch + 4 coef regs (~70) | ~2,142 Toffolis | ~27.5% | 2 |
| **Mantissa Multiply $x_{\text{norm}} \cdot y_0^2$** | 30 bits | ~2,086 Toffolis | ~26.8% | 3 |
| **Final Newton-Raphson Multiply $y_0(3 - z)$** | 30 bits | ~1,734 Toffolis | ~22.3% | 4 |
| **Squaring $y_0^2$ (`_square`)** | 28 bits | ~884 Toffolis | ~11.3% | 5 |
| **CSWAP Shifting (Norm + Denorm)** | 22 qubits $x$ + 31 qubits $y_1$ | ~820 CSWAPs (~820 Toffolis) | ~10.5% | 6 |
| **Constant Additions & Interval Logic** | Ancillas | ~120 Toffolis | ~1.6% | 7 |
| **Overall Baseline Score ($S = Q \times C$)** | **$Q \approx 100$ qubits** | **$C \approx 7,800$ Toffoli-equiv.** | **$S \approx 2.08 \times 10^6$** | **Total** |

---

## 3. Candidate Reductions & Ranking

| Rank | Candidate Reduction Idea | Mechanism | Exact vs Approx | Verification Catch Mechanism | Priority Score $\frac{\text{Save} \times \text{Conf}}{\text{Effort}}$ |
| :---: | :--- | :--- | :--- | :--- | :---: |
| **1** | **Truncate Horner Precision ($\Delta x$ & coef bits)** | Reduce $\Delta x$ from 14 to 12 bits and coef bits from 17 to 15. The paper baseline achieves $2.84 \times 10^{-8}$ worst-case error while tolerance is $5.96 \times 10^{-8}$ ($2^{-24}$); there is a 52% headroom margin. | Approx | Caught if relative error exceeds $2^{-24}\beta/\sqrt{x}$ on any of the 3.13M points. | **High (8.5/10)** |
| **2** | **Full Measurement Uncomputation of Multipliers** | In forward evaluation, uncompute row-adders immediately by measuring partial products instead of running backward reversible addition in uncomputation. | Exact | Caught if uncomputed ancilla holds $|1\rangle$ (triggers random sign flip in `R`). | **High (8.0/10)** |
| **3** | **Optimal Polynomial Interpolation (Chebyshev/Remez)** | Re-fit polynomial coefficients using minimax Remez algorithm on $[1, 1.5]$ and $[1.5, 2]$ to minimize maximum relative error, enabling lower degree (quadratic) or fewer fractional bits. | Approx | Fails phase check $\text{tol}(x)$ in `verify_submission_invsqrt.py`. | **Med-High (7.5/10)** |
| **4** | **Combined Shift / Unary Register Compression** | Merge unary shift flags $f_k$ and eliminate CSWAP steps for small $k$ where frequency is low or bit-lengths allow grouped barrel shifting. | Exact | Value check on register $x$ or phase mismatch. | **Medium (6.0/10)** |
| **5** | **Direct Newton-Raphson Seed Lookup (Higher QROM)** | Use a 4-bit or 5-bit lookup table directly to give an initial seed with 8 bits of accuracy, eliminating one Horner multiplication step entirely. | Approx | Evaluated by total qubit-Toffoli product. | **Medium (5.5/10)** |

---

## 4. Verifier Capabilities and Detection Limits

- **What It Detects:**
  - Exhaustively checks every single integer $x \in [1, 3,133,452]$ with 64 random measurement shots ($200,540,928$ total shots) [FROM SOURCE].
  - Checks exact restoration of register `"x"` and clean $|0\rangle$ state on all scratch qubits [FROM SOURCE].
  - Checks phase error down to 64-bit fixed point against integer square root arithmetic [FROM SOURCE].
- **Detection Blindspots / Risks to AVOID:**
  - The verifier checks only the named register `"x"`. If an optimization forgets to name register `"x"` or introduces extra named registers, it crashes or gets rejected [FROM SOURCE].
  - Do NOT attempt to hard-code special cases: the test seed is salted with the SHA-256 digest of the circuit binary [FROM SOURCE].

---

## 5. First 5 Concrete Experiments for Devin

### Experiment 1.1: Baseline Replication & Bit-Precision Margin Characterization
- **Input:** `verifiers/invsqrt/nr_reference_circuit.py` and `verifiers/invsqrt/verify_submission_invsqrt.py`.
- **Change:** Run `fixed_point_model` across all $x \in [1, \max_x]$ sweeping `delta_bits` from 14 down to 11 and `coef_bits` from 17 down to 14. Find the minimal precision tuple where $\max \text{error}(x) < 2^{-24} / \sqrt{x}$.
- **Verification Command:** `python -c "from nr_reference_circuit import *; ..."`
- **Success Criterion:** Identify a parameter set saving $\ge 15\%$ Toffolis while retaining $< 90\%$ of allowed error threshold.

### Experiment 1.2: Remez Minimax Polynomial Optimization
- **Input:** Coefficients `POLY_A` and `POLY_B` in `nr_reference_circuit.py`.
- **Change:** Compute optimal degree-3 and degree-2 minimax polynomial coefficients minimizing relative error for $1/\sqrt{u}$ on $[1, 1.5]$ and $[1.5, 2]$ using Scipy/mpmath Remez exchange.
- **Verification Command:** Run `fixed_point_model` on all $x$ with new coefficients.
- **Success Criterion:** Max relative error reduced by $> 2\times$, allowing 2 fewer bits in multiplier scratch.

### Experiment 1.3: Multiplier MBUC Uncomputation Injection
- **Input:** `_horner` and `_add_row` functions in `nr_reference_circuit.py`.
- **Change:** Ensure all row additions in Horner and squaring stages release ancillas via `HMR` measurement-based uncomputation with phase kickback instead of reverse reversible uncomputation.
- **Verification Command:** Build candidate circuit and execute `verify_submission_invsqrt.py candidate.kmb --shots-per-x 1`.
- **Success Criterion:** Verification passes; Toffoli count drops by $\ge 20\%$.

### Experiment 1.4: Multiplier Row Truncation Tuning
- **Input:** `product_bits` (28) and `result_bits` (29) in `Precision`.
- **Change:** Truncate guard bits in partial-product accumulation of $z = x_{\text{norm}} \cdot y_0^2$ and $p = y_0(3 - z)$ from 29 bits to 27 bits.
- **Verification Command:** Run full sweep on `fixed_point_model`.
- **Success Criterion:** Zero overflow errors, relative error within $2^{-24}$, saving ~400 Toffolis.

### Experiment 1.5: CSWAP Barrel-Shifter Pruning
- **Input:** `_normalize` function in `nr_reference_circuit.py`.
- **Change:** Replace sequential 1-bit CSWAP rotations with logarithmic power-of-2 barrel shifting (shifts by 1, 2, 4, 8) conditioned on decoded binary shift amount.
- **Verification Command:** Verify equivalence on test vectors and run `verify_submission_invsqrt.py`.
- **Success Criterion:** CSWAP count reduced from 110 down to $< 60$.

---

## 6. Unknowns & What to Check
1. [RESOLVED] Exact baseline cost: $S \approx 2.08 \times 10^6$ ($Q \approx 100$, $C \approx 7,800$).
2. [UNKNOWN] Exact run-time for 200M shots on multi-core Devin instance (needs benchmark test on chunk size).
