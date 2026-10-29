# Companion Paper Summary: Leveraging Verifiable Structure in Quantum Circuits to Find More Efficient Compilations with Agentic AI

**Source:** Khattar et al., arXiv:2610.23832 (Google Quantum AI)  
**Document Target:** `notes/paper_summary.md`  
**Classification Guide:** Every statement below is marked as `[FROM SOURCE]`, `[INFERENCE]`, or `[UNKNOWN]`.

---

## 1. Core Idea of "Verifiable Structure" and Kickmix Circuits

### Plain Terms
In general quantum computing, verifying that an arbitrary $n$-qubit circuit matches a target unitary requires simulating full $2^n$-dimensional state vectors, which becomes impossible on classical hardware past roughly 40 qubits [FROM SOURCE]. However, the costliest fault-tolerant subroutines (arithmetic adders, multipliers, QROM table lookups, error-correcting syndrome decoders) do not use continuous, arbitrary quantum interference internally [FROM SOURCE]. Instead, they compute classical functions on quantum superpositions [FROM SOURCE]. 

If a circuit maps each computational basis input $|x\rangle$ to a single basis output $|y\rangle$ with an overall phase $e^{i\theta(x)}$, a classical simulator only needs to track **one classical bit per qubit wire** and **one running scalar phase** [FROM SOURCE]. This turns intractable $2^n$ quantum matrix simulation into linear-time classical bit-tracking that executes tens of millions of gates in seconds [FROM SOURCE].

### Formal Definition & Allowed Gate Set
A **kickmix circuit** is restricted strictly to instructions that map computational basis states to computational basis states up to a global scalar phase [FROM SOURCE]. The simulator processes batches of 64 to 512 trajectory shots in parallel using CPU SIMD bit-packing [FROM SOURCE].

Every instruction in kickmix belongs to one of four classes:
1. **Reversible Classical Gates:**
   - Instructions: `X`, `CX`, `CCX` (Toffoli), `SWAP`, `CSWAP` [FROM SOURCE].
   - Action: Permute computational basis states directly by updating stored qubit bits [FROM SOURCE].
2. **Diagonal Phase Gates:**
   - Instructions: `Z`, `CZ`, `CCZ`, `Z_POW` (arbitrary angle rotation), `NEG` [FROM SOURCE].
   - Action: Leave basis bit values unchanged and increment the tracked scalar phase whenever all control qubits are $|1\rangle$ [FROM SOURCE].
3. **Measurement and Reset Gates:**
   - Instructions: `HMR` (Hadamard-Measure-Reset in $X$-basis), `R` (computational basis reset) [FROM SOURCE].
   - Action: Used for measurement-based uncomputation. `HMR` projects a temporary qubit into the $X$-basis $(|0\rangle \pm |1\rangle)/\sqrt{2}$, records classical measurement outcome $b \in \{0, 1\}$, flips the tracked output phase if $q_t \cdot b = 1$, and resets $q_t$ to $|0\rangle$ [FROM SOURCE].
   - Safety enforcement: If an uncomputed qubit holds $|1\rangle$ upon executing `R`, or if an `HMR` phase fixup is missing, the simulator applies a random sign flip, causing fuzz verification to fail with probability $1/2$ [FROM SOURCE].
4. **Control and Marker Pseudo-Instructions:**
   - Instructions: `BIT_INVERT`, `BIT_STORE0`, `BIT_STORE1`, `PUSH_CONDITION`, `POP_CONDITION`, `INFO_TAG`, `DEBUG_PRINT` [FROM SOURCE].

### What Breaks the Guarantee?
Any gate that creates arbitrary non-Clifford superpositions across basis states—such as an unmeasured Hadamard on a computational basis register, arbitrary single-qubit rotations ($R_x, R_y$), or entangling gates like $\sqrt{\text{SWAP}}$—breaks the single-basis-state mapping and causes kickmix simulation to be invalid [FROM SOURCE]. Unmeasured scratch garbage left in state $|1\rangle$ also triggers random phase corruptions during deallocation [FROM SOURCE].

---

## 2. Formal Meaning of "Approximately Correct with Small Bounded Error"

### Trace Distance Bound Under Superposition
Let the ideal circuit apply unitary $U$ to state $|\psi\rangle = \sum_x \alpha_x |x\rangle$. Let $W$ be the isometry implemented by the kickmix circuit with $m$ deferred measurement record qubits, acting as:
$$W|\psi\rangle = 2^{-m/2} \sum_r V_r |\psi\rangle \otimes |r\rangle \quad \text{[FROM SOURCE]}$$
where $r \in \{0, 1\}^m$ indexes measurement outcomes and $V_r$ is the conditional linear operator [FROM SOURCE].

Let $B_r = \{x : V_r |x\rangle \neq U|x\rangle\}$ be the failing basis inputs for record $r$, and let $\varepsilon_r = \sum_{x \in B_r} |\alpha_x|^2$ be the failure probability weighted by algorithm input distribution $|\alpha_x|^2$ [FROM SOURCE]. The average per-input failure rate is:
$$\varepsilon = \mathbb{E}_r [\varepsilon_r] \quad \text{[FROM SOURCE]}$$

Because the measurement record states are orthonormal, the error branches sum in quadrature:
$$\|W|\psi\rangle - U|\psi\rangle \otimes |+\rangle^{\otimes m}\|^2 \le 4\varepsilon \quad \text{[FROM SOURCE]}$$
The fidelity between the physical output state and ideal state $U|\psi\rangle$ is at least $(1 - 2\varepsilon)^2$, and the physical trace distance is rigorously bounded by:
$$\mathcal{D}_{\text{trace}} \le 2\sqrt{\varepsilon} \quad \text{[FROM SOURCE]}$$
Any phase discrepancy within tolerance $\tau$ turns adds at most $2\pi\tau$ to the trace distance, which is negligible under competition thresholds [FROM SOURCE].

### Confidence Level and Sample Size (Clopper-Pearson Bound)
To guarantee that true failure rate $\varepsilon \le \varepsilon^+$ without maintaining secret test sets, the verifier tests $N$ independent shots seeded via **Fiat-Shamir** (SHA-256 digest of candidate circuit binary + competition secret salt) [FROM SOURCE].

If $k$ failures are observed in $N$ shots, the one-sided Clopper-Pearson upper confidence bound $\varepsilon^+$ at confidence $1 - \delta = 1 - 2^{-128}$ satisfies:
$$\sum_{j=0}^k \binom{N}{j} (\varepsilon^+)^j (1 - \varepsilon^+)^{N-j} = \delta = 2^{-128} \quad \text{[FROM SOURCE]}$$

When a circuit passes all $N$ shots with zero failures ($k = 0$):
$$(1 - \varepsilon^+)^N = 2^{-128} \implies \varepsilon^+ \approx \frac{\ln(1/\delta)}{N} \approx \frac{128 \ln 2}{N} \approx \frac{88.72}{N} \quad \text{[FROM SOURCE]}$$

- For $N = 10,240$ shots with zero failures: $\varepsilon^+ < 1.0\%$ ($0.87\%$) at confidence $1 - 2^{-128}$ [FROM SOURCE].
- For $N = 102,400$ shots with zero failures (DQI benchmark): $\varepsilon^+ < 0.1\%$ ($0.087\%$) at confidence $1 - 2^{-128}$ [FROM SOURCE].
- For $N = 200,540,928$ shots (exhaustive $64 \times 3,133,452$ on invsqrt): every input is verified deterministically ($k=0$ required) [FROM SOURCE].

---

## 3. The AI-Agent Loop in the Paper

### Setup and Workflow
- **Actions:** The agent is provided a high-level circuit builder script (Python using Qualtran's `kickmix` API) or low-level instruction streams [FROM SOURCE]. The agent proposes alternative mathematical decompositions, truncates carry bits, adjusts register bit-widths, reorders loops, or introduces measurement uncomputations [FROM SOURCE].
- **Reward Signal:** Fast, non-interactive execution of the official verifier. The verifier returns binary correctness plus the exact objective cost $S$ [FROM SOURCE]. Fuzz-testing executes in seconds (e.g., evaluating 102,400 shots of an 86M-gate circuit takes ~150s) [FROM SOURCE].
- **Precedent (ecdsa.fail):** In the 2026 ecdsa.fail competition, over 100 participants with classical backgrounds used AI coding agents in closed verification loops to slash Toffoli gate counts in half on elliptic-curve point addition [FROM SOURCE].

### What Worked vs. What Didn't (Paraphrased)
- **What Worked:**
  - Decomposing large arithmetic routines into modular building blocks with localized verification [FROM SOURCE].
  - Replacing standard reversible arithmetic uncomputations with measurement-based uncomputations (saving roughly 50% Toffolis on scratch cleanups) [FROM SOURCE].
  - Pruning low-order bit precisions and carry chains where algorithmic error tolerance allows it [FROM SOURCE].
  - Hardware-style pipelining and register reuse (sharing a single scratch register across sequential Horner steps) [FROM SOURCE].
- **What Didn't:**
  - Black-box full-unitary quantum optimizers: They fail to scale beyond ~40 qubits and cannot alter algorithmic structures or trade precision for cost [FROM SOURCE].
  - Seed grinding: Attempting to game randomized inputs by inserting no-ops is prevented by salting the SHA-256 seed [FROM SOURCE].
  - Unbounded approximation: Sacrificing too much precision in decoders or factorizations blows up repetition factors or causes immediate rejection [FROM SOURCE].

---

## 4. Concrete Circuit-Reduction Techniques

The following table compiles all concrete circuit optimization techniques and arithmetic tricks detailed across the paper and appendices:

| Technique | Where It Applies | Expected Saving / Mechanism | Source Section |
| :--- | :--- | :--- | :--- |
| **Measurement-Based Uncomputation (MBUC)** | Clean-up of scratch ancillas storing reversible logic products ($a \wedge b$) | Replaces backward Toffoli uncomputation with an $X$-basis measurement (`HMR`) and phase correction, saving ~50% Toffolis on uncomputation. | §I, §II.A, §III.B |
| **Controlled-SWAP Truncated Loop** | Normalization register bit-shifting in $1/\sqrt{x}$ | For step $k$, bottom $2k$ bits are already zero; reduces active wire count to $n_p + 1 - k$, requiring only $n_p(n_p+1)$ CSWAPs instead of full register shifts. | §III.A, App. B.2 |
| **Shift/Unary Normalization Encoding** | Dynamic range scaling for fixed-point arithmetic ($1/\sqrt{x}$) | Shifting pairs of leading zeros normalizes mantissa into $[1, 4)$, shrinking required fractional precision from 35 bits to 14–20 bits. | §III.A, App. B.1 |
| **Horner's Rule In-Place Polynomial Evaluation** | Polynomial evaluation $y_0 = a_0 - a_1 \Delta x + a_2 \Delta x^2 - a_3 \Delta x^3$ | Rewrites as nested form $a_0 - \Delta x(a_1 - \Delta x(a_2 - a_3 \Delta x))$. Evaluates directly in coefficient registers ($c_2, c_1, c_0$) in-place, eliminating 6 fresh output registers. | App. B.3 |
| **Shared Multiplier Scratch Register** | Successive multiplications in Horner and Newton-Raphson | A single shared 30-qubit scratch register holds row partial products across all multipliers; intermediate products are uncomputed via measurement immediately. | App. B.3 |
| **Single-Bit Offset Logic ($\Delta x_{11} = b_{13} \wedge b_{11}$)** | Range-centering for cubic polynomial approximation in $1/\sqrt{x}$ | Only the 0.5s-place bit requires logic; all other lower bits of $\Delta x$ are read directly from $x_{\text{norm}}$ without allocating extra registers or CNOTs. | App. B.3 |
| **Squaring Diagonal Cross-Term Splitting** | Multiplier squaring $T(y_0^2)$ | Diagonal bits $y_k^2 = y_k$ copied with CNOTs; doubled cross-terms $2 y_k y_l$ added row-by-row, cutting Toffolis nearly in half relative to general multiplication. | App. B.3 |
| **Two's Complement Inversion via $X$ + Constant Add** | Newton-Raphson correction step $3 - z$ | Bitwise $X$ gates followed by classical addition of $(3 \ll 28) + 1$, costing only 28 Toffolis for full 30-bit in-place negation. | App. B.3 |
| **Karatsuba / Hand-Tuned $F_{2^{12}}$ Multipliers** | Finite field multiplication in Reed-Solomon DQI decoder | Replacing generic field multipliers with specialized Karatsuba or sub-quadratic circuits cuts Toffolis from 63 to 51 per multiplication. | §III.B.2 |
| **Itoh–Tsujii Inversion Chains** | Galois field inversion $a^{-1} = a^{2^{12}-2}$ in $F_{2^{12}}$ | Computes field inversions via addition chains using Frobenius squarings (free CNOTs) and minimal field multiplications (315 Toffolis, 48 scaffold qubits). | §III.B.2 |
| **Approximate Syndrome Decoding Trade-Off** | DQI Reed-Solomon decoder | Allows bounded error rate $\varepsilon^+ \le 1/16$; trading exact decoding for cheaper circuit depth adds a minor repetition factor $R(\varepsilon^+)$ to the score. | §III.B.3 |
| **Batched QROM Angle Streaming ($J$ angles/batch)** | Hamiltonian Majorana rotation loading in DFTHC | Tuning batch size $J \in [1, N-1]$ balances persistent angle-word registers ($J b_{\text{rot}}$ qubits) against sequential QROM access overhead. | §III.C.4 |
| **Majorana Givens Rotation Tree Optimization** | Mapping Givens rotation angles to electronic orbitals | Reordering tree edges $T$ directly alters angle values and Givens circuit depth, minimizing state preparation overhead and rotation costs. | §III.C.5 |
| **Tensor Hypercontraction (DFTHC) Rank Pruning** | Electronic integral tensor factorization ($U, W, H$) | Optimizing low-rank factors $(R, B, C)$ under 20 mHa Frobenius error minimizes outer/inner state preparation costs and QROM sizes. | §III.C.3 |

---

## 5. Cost Formulas and Dominance

The competition evaluation takes the **geometric mean** of the relative improvement over the host baseline across all three benchmarks [FROM SOURCE]:
$$\text{Score} = \left( \prod_{i=1}^3 \frac{\text{Baseline Cost}_i}{\text{Candidate Cost}_i} \right)^{1/3} \quad \text{[FROM SOURCE]}$$

### Benchmark I: `invsqrt`
$$\text{Cost} = Q \times C \quad \text{[FROM SOURCE]}$$
- $Q$: Total qubit count (including register $x$ and all ancillas) [FROM SOURCE].
- $C = \text{Toffolis} + \frac{T}{4}$: Mean Toffoli-equivalent cost per shot [FROM SOURCE].
- Rotation cost: Fine $Z_{\text{pow}}$ rotations are synthesized at $0.56 \log_2(1/\epsilon) + 5.3$ $T$-gates each [FROM SOURCE].
- **Dominance:** Qubits and Toffolis enter symmetrically as a product ($Q \times C$). Reducing either by 10% produces identical 10% score improvements [INFERENCE].

### Benchmark II: `dqi`
$$\text{Cost} = R(\varepsilon^+) \cdot Q^2 \cdot T \quad \text{[FROM SOURCE]}$$
- $Q$: Total qubit count (syndromes + workspace) [FROM SOURCE].
- $T$: Single-run Toffoli count (including cleanup) [FROM SOURCE].
- $R(\varepsilon^+)$: Repetition factor $= \frac{\ln 2}{\ln 2 - \ln(1 + 4\sqrt{\varepsilon^+})}$ [FROM SOURCE].
- **Dominance:** **Qubits dominate heavily over Toffolis.** The exponent $Q^2$ means a 1% reduction in qubits yields a ~2% improvement in total cost, twice as impactful as a 1% Toffoli reduction [FROM SOURCE].

### Benchmark III: `dfthcsos`
$$\text{Cost} = \lambda_{\text{eff}} \times T_{\text{tot}} \times Q_{\text{tot}} \quad \text{[FROM SOURCE]}$$
- $\lambda_{\text{eff}} = \sqrt{E_{\text{gap}} (2\Lambda - E_{\text{gap}})}$: Derived from tensor factorization eigenvalues and LCU normalizations [FROM SOURCE].
- $T_{\text{tot}}$: Total simulated Toffoli count of `angle_k` circuits (forward + reverse) plus analytical costs of `Outer`, `Inner`, and $N-1$ Givens rotations [FROM SOURCE].
- $Q_{\text{tot}}$: Persistent angle registers + max sequential scratch workspace across `Outer`, `Inner`, and `angle_k` [FROM SOURCE]. Hard constraint: any `angle_k` wider than 128 qubits is rejected [FROM SOURCE].
- **Dominance:** Balanced space-time product ($T_{\text{tot}} \times Q_{\text{tot}}$) scaled by the algebraic factor $\lambda_{\text{eff}}$ [FROM SOURCE].

---

## 6. List of UNKNOWNs to Resolve from Local Repo & Environment

The following items are not documented in the PDF text and require inspection of local code files in `google-verifiable-quantum-circuit-compilation/`:

1. **Exact Local CLI Commands for Verifiers [UNKNOWN]:**
   - Need to inspect `verifiers/invsqrt/`, `verifiers/dqi/`, and `verifiers/dfthcsos/` to identify the Python runner scripts and CLI flags used to verify `.kmb`/`.kmx` files locally.
2. **Kickmix Binary Compilation & Platform Compatibility [UNKNOWN]:**
   - `kickmix/kickmix.so` was compiled for the Kaggle Linux container (glibc). Need to verify if `kickmix` can run on Windows natively, or if local verification must run in WSL2/Docker or if Qualtran source is available.
3. **Exact Baseline Numbers [UNKNOWN]:**
   - Need to parse `sample_submission/` or run the baseline circuits to record exact baseline numerical values for $(Q, C, S)$ across `invsqrt`, `dqi`, and `dfthcsos`.
4. **DFTHC Analytical Cost Functions [UNKNOWN]:**
   - Need to inspect `verifiers/dfthcsos/scoreinfra/reference.py` to get the exact analytical formulas for $C_{\text{out}}$, $C_{\text{in}}$, and Givens Toffoli costs.
5. **Exact Format of `submission.npz` Arrays [UNKNOWN]:**
   - Need to examine array shapes and precision types in `sample_submission/dfthcsos/submission.npz`.
