# Benchmark II Analysis: Reed-Solomon Syndrome Decoder for DQI (Combinatorial Optimization)

**Document Target:** `notes/bench2_analysis.md`  
**Classification Guide:** Every assertion is marked as `[FROM SOURCE]`, `[INFERENCE]`, or `[UNKNOWN]`.

---

## 1. What This Circuit Computes & Why It Is a Bottleneck

### Scientific Role
In combinatorial optimization, the Optimal Polynomial Intersection (OPI) problem seeks a low-degree polynomial over a finite field that intersects as many target sets as possible [FROM SOURCE]. Decoded Quantum Interferometry (DQI) uses the quantum Fourier transform to turn OPI into decoding a Reed–Solomon code $RS(m=4095, k=4025, d=71)$ over Galois field $GF(2^{12})$ [FROM SOURCE].
In optimized DQI, measurement-based uncomputation erases the error register early, leaving a classical measurement record $M \in GF(2^{12})^m$ and quantum error syndromes $S_0, \dots, S_{n-1}$ [FROM SOURCE]. The quantum decoder must evaluate the classical syndrome, recover the error polynomial, apply a phase correction $(-1)^{\sum_j \text{popcount}(e_j \wedge M_j)}$, and restore all quantum syndromes cleanly to $|0\rangle$ [FROM SOURCE].
The syndrome decoder accounts for **over 90% of the entire DQI algorithm cost** [FROM SOURCE].

### Problem Contract & Scoring
- **Registers:** $n=70$ syndrome registers $S_0, \dots, S_{69}$ of width $b=12$ ($840$ qubits) and $m=4095$ classical registers $E_0, \dots, E_{4094}$ of width 12 ($49,140$ classical bits) [FROM SOURCE].
- **Cost Formula:**
  $$\text{Cost} = R(\varepsilon^+) \cdot Q^2 \cdot T \quad \text{[FROM SOURCE]}$$
  - $Q$: Total qubit count (syndrome + workspace).
  - $T$: Single-run Toffoli count (forward evaluation + complete cleanup).
  - $R(\varepsilon^+)$: Repetition factor $= \frac{\ln 2}{\ln 2 - \ln(1/2 + 2\sqrt{\varepsilon^+})}$.
  - **Notice the critical asymmetry:** **Qubits are squared ($Q^2$)!** A 1% cut in qubits provides the same benefit as a 2% cut in Toffoli gates [FROM SOURCE].

---

## 2. Baseline Architecture & Cost Breakdown

The reference circuit follows the Extended Euclidean Algorithm (EEA) of Proos and Zalka [FROM SOURCE]:
1. **Solve Key Equation (EEA):** Computes error-locator $\sigma(z)$ and error-evaluator $\omega(z)$ by running synchronized EEA steps on $z^{2\ell}$ and $S(z)$ ($\ell = 35$) [FROM SOURCE]. Uses arrays of $n+3$ field registers ($73 \times 12 = 876$ qubits) for polynomial coefficients [FROM SOURCE].
2. **Chien Search & Forney's Formula:** Evaluates $\sigma(\alpha^{-j})$ over all $m=4095$ points using linear feedback shifts. When $\sigma = 0$, computes error $e_j = \omega(\alpha^{-j}) / \sigma'(\alpha^{-j})$ via field inversion and kicks back the phase [FROM SOURCE].
3. **Reverse Uncomputation:** Runs the synchronized EEA in reverse to restore syndromes and clear scratch registers [FROM SOURCE].

### Baseline Cost Share Table

| Subroutine | Qubits Allocated | Toffolis | Cost Share (Toffolis) | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **EEA Polynomial Division / Multiplications** | ~900 qubits (coefs + degrees) | ~2,500,000 Toffolis | ~43.7% | 63-Toffoli Karatsuba $F_{2^{12}}$ multipliers |
| **Reverse EEA Uncomputation** | Reuses forward workspace | ~2,500,000 Toffolis | ~43.7% | Symmetrical reverse execution |
| **Forney Formula & Inversion Scaffold** | 48 scaffold qubits | ~500,000 Toffolis | ~8.7% | Itoh–Tsujii addition chain (315 Tofs/inv) |
| **Chien Search & Control Flow Flags** | ~50 qubits | ~225,000 Toffolis | ~3.9% | Linear feedback + comparators |
| **Total Baseline Reference** | **$Q = 1,893$ qubits** | **$T = 5,725,461$ Toffolis** | **100%** | **$S \approx 2.44 \times 10^{13}$ ($R \approx 1.19$)** |

---

## 3. Candidate Reductions & Ranking

| Rank | Candidate Reduction Idea | Mechanism | Exact vs Approx | Verification Catch Mechanism | Priority Score $\frac{\text{Save} \times \text{Conf}}{\text{Effort}}$ |
| :---: | :--- | :--- | :--- | :--- | :---: |
| **1** | **Scaffold & Working Register Compaction ($Q^2$ impact!)** | Reuse polynomial scratch registers between $\sigma$ and $\omega$. The baseline allocates separate arrays of $n+3$ registers. Reducing $Q$ from 1,893 to ~1,400 cuts total cost by $(1400/1893)^2 \approx 45\%$ directly! | Exact | Caught if register overlap corrupts data; verifier checks clean return to $|0\rangle$. | **Highest (9.5/10)** |
| **2** | **Sub-Quadratic $F_{2^{12}}$ Multiplier (51-Toffoli)** | Replace 63-Toffoli generic Karatsuba multiplier with hand-tuned 51-Toffoli sub-quadratic field multiplier as proven in Khattar et al. (saving 12 Toffolis $\times$ tens of thousands of multiplications). | Exact | Caught by Galois field algebraic validation during EEA. | **High (9.0/10)** |
| **3** | **Bounded EEA Iteration Count (Approximate Decoding)** | Truncate the maximum number of EEA iterations from $2\ell = 70$ down to empirical distribution limit (e.g. 64). The score allows $\varepsilon^+ \le 1/16$ with slight penalty in $R(\varepsilon^+)$. If 68 iterations cuts 10% Toffolis and raises $R$ by only 1%, net gain is huge. | Approx | Monitored by Clopper-Pearson failure counter across 102,400 shots. | **High (8.5/10)** |
| **4** | **Itoh–Tsujii Addition Chain Optimization** | Optimize the addition chain for $2^{12} - 2 = 4094$. Use an optimal addition sequence to compute field inversion with fewer multiplications. | Exact | Value check on recovered error $e_j$. | **Medium (7.0/10)** |
| **5** | **Berlekamp–Massey Alternative Decoder** | Replace Extended Euclidean Algorithm with an in-place quantum Berlekamp–Massey architecture, which historically requires fewer ancillary registers. | Exact | Full verifier run (102,400 shots). | **Med-Low (5.0/10)** |

---

## 4. Verifier Capabilities and Detection Limits

- **What It Detects:**
  - Evaluates 102,400 shots drawn from the exact DQI weight distribution [FROM SOURCE].
  - Checks exact syndrome restoration on all 70 registers $S_0, \dots, S_{69}$ and clean $|0\rangle$ on all ancillas [FROM SOURCE].
  - Tracks empirical failure rate $k/N$. If $k$ failures occur, Clopper-Pearson bounds $\varepsilon^+$ at $1 - 2^{-128}$ confidence. If $\varepsilon^+ \ge 1/16$, score is infinite/rejected [FROM SOURCE].
- **Risks to AVOID:**
  - No `Z_POW` gates are allowed in DQI (only classical logic and phase kickback) [FROM SOURCE].
  - Any circuit that drops too many EEA iterations and exceeds $\varepsilon^+ \ge 1/16$ receives no finite score [FROM SOURCE].

---

## 5. First 5 Concrete Experiments for Devin

### Experiment 2.1: Register Lifetime Analysis & Scratch Compaction
- **Input:** `verifiers/dqi/dqi_reference_circuit.py`.
- **Change:** Profile active register lifetimes in `ProosAndZalkaDecoder`. Overlap the memory footprint of temporary polynomial registers in step 1 and step 2.
- **Verification Command:** `python dqi_reference_circuit.py candidate_compact.kmb --m 63 --n 10` (test on small field first).
- **Success Criterion:** Reduce total qubit count $Q$ by $\ge 150$ qubits (yielding $\ge 15\%$ reduction in $Q^2$).

### Experiment 2.2: 51-Toffoli $F_{2^{12}}$ Multiplier Drop-In
- **Input:** Finite field multiplier in `dqi_reference_circuit.py`.
- **Change:** Implement the 51-Toffoli 2-stage Karatsuba/Montgomery multiplier over $GF(2^{12})$ with irreducible polynomial $x^{12} + x^7 + x^6 + x^5 + x^3 + x + 1$.
- **Verification Command:** Run field arithmetic unit tests and verify small instance.
- **Success Criterion:** Toffoli count drops by ~19% per field multiplication; passes verification.

### Experiment 2.3: Iteration Truncation Trade-Off Characterization
- **Input:** Parameter `n_iters` in `build_syndrome_decoding_mbuc`.
- **Change:** Test `n_iters = 68, 66, 64, 62` against the 102,400 shot verifier with small batch sizes. Measure empirical failure rate $\hat{\varepsilon}$ and compute net score $R(\varepsilon^+) \cdot Q^2 \cdot T$.
- **Verification Command:** `python verify_submission_dqi.py candidate.kmb --batch-size 256`.
- **Success Criterion:** Find optimal iteration cutoff where Toffoli savings exceed the small increase in repetition factor $R(\varepsilon^+)$.

### Experiment 2.4: Itoh–Tsujii Inversion Chain Refinement
- **Input:** Field inversion routine in `dqi_reference_circuit.py`.
- **Change:** Re-synthesize addition chain for exponent $4094 = (111111111110)_2$ to minimize temporary registers and field multiplications.
- **Verification Command:** Run Galois field inversion unit test.
- **Success Criterion:** Reduce scaffold qubits by 8 and multiplication count by 1.

### Experiment 2.5: Chien Search Degree Truncation
- **Input:** Chien search loop in stage 2 of `dqi_reference_circuit.py`.
- **Change:** Early-exit or prune testing on higher powers when degree of $\sigma$ is small.
- **Verification Command:** Verify on small instance and check full Clopper-Pearson bound.
- **Success Criterion:** Save $\ge 50,000$ Toffolis in stage 2 without increasing error rate.

---

## 6. Unknowns & What to Check
1. [UNKNOWN] What is the exact irreducible polynomial used by `km.GF2Field(12)` in `kickmix.so`? (Must be verified in Linux container so our hand-tuned multiplier matches exact field definition).
2. [UNKNOWN] Execution speed of 102,400 shots on multi-core Devin instance (~150 seconds reported in paper).
