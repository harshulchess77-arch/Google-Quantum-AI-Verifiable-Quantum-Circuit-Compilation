# Benchmark III Analysis: QROM and Majorana Rotations for DFTHC Chemistry (FeMoCo)

**Document Target:** `notes/bench3_analysis.md`  
**Classification Guide:** Every assertion is marked as `[FROM SOURCE]`, `[INFERENCE]`, or `[UNKNOWN]`.

---

## 1. What This Circuit Computes & Why It Is a Bottleneck

### Scientific Role
Simulating biological nitrogen fixation in the active site of nitrogenase—the iron-molybdenum-sulfur cofactor **FeMoCo** ($N = 76$ spatial orbitals, $\eta = 113$ electrons)—is an iconic challenge for quantum chemistry [FROM SOURCE]. Industrial Haber–Bosch fertilizer production consumes ~2% of global energy [FROM SOURCE]. Classical computers fail due to strong electron correlation [FROM SOURCE].
Quantum phase estimation simulates the FeMoCo Hamiltonian $H = T + V$ encoded via **Double-Factorized Tensor Hypercontraction (DFTHC)** [FROM SOURCE]. The Hamiltonian integral tensor is factorized into low-rank representations $(U, W)$, converted into Givens rotation angles $\vec{\theta}$ on an orbital tree, loaded into quantum memory via **QROM boolean oracles** (`ANGLE_k`), and applied as controlled Majorana Givens rotations [FROM SOURCE].
The QROM table lookups and Givens rotations constitute the primary resource bottleneck of the entire block encoding [FROM SOURCE].

### Problem Contract & Scoring
- **Submission:** A folder `dfthcsos` containing $K$ angle circuits `angle_k_0.km[xb]`, ..., `angle_k_<K-1>.km[xb]` (where $K = \lceil 75 / J \rceil$, loading $J$ angles per batch), and `submission.npz` containing arrays `U`, `W`, `H2_I`, `H1_I`, `Hsym_lower`, and `tree_edges` [FROM SOURCE].
- **Cost Formula:**
  $$\text{Cost} = \lambda_{\text{eff}} \times T_{\text{tot}} \times Q_{\text{tot}} \quad \text{[FROM SOURCE]}$$
  - $\lambda_{\text{eff}} = \sqrt{E_{\text{gap}} (2\Lambda - E_{\text{gap}})}$: Spectral normalization calculated from the submitted factorization and decoded angles [FROM SOURCE].
  - $T_{\text{tot}} = \text{ANGLES Toffolis} + \text{Outer Prep} + \text{Inner Prep} + 2(N-1)(2 b_{\text{rot}} - 1)$ Givens Toffolis [FROM SOURCE].
  - $Q_{\text{tot}} = \text{Persistent Prep Qubits} + J \cdot b_{\text{rot}} + \max(\text{Outer Temp}, \text{Inner Temp}, \text{Angle Temp})$ [FROM SOURCE].
- **Strict Hard Rejection Gates:**
  - Any `angle_k` circuit wider than **128 qubits** is rejected [FROM SOURCE].
  - Encoded Hamiltonian Frobenius residual must satisfy $\text{error}_1 \le 20\text{ mHa}$ and $\text{error}_2 \le 20\text{ mHa}$ [FROM SOURCE].
  - Normalization floors: $\Lambda > 49.0$ Ha and $E_{\text{gap}} > 3.914898$ Ha [FROM SOURCE].

---

## 2. Baseline Architecture & Cost Breakdown

The provided baseline uses:
- Rank parameters: $R = 65$, $B = 60$, $C = 60$ ($R \cdot B = 3900$, plus 76 one-body addresses = 3976 total rows) [FROM SOURCE].
- Precision: $b_{\text{rot}} = 12$ bits per rotation angle [FROM SOURCE].
- Batch size: $J = 8$ angle words per batch ($K = \lceil 75 / 8 \rceil = 10$ circuits: `angle_k_0` through `angle_k_9`) [FROM SOURCE].
- QROM compilation: Linear unary iteration with measurement-based uncomputation [FROM SOURCE].

### Baseline Cost Breakdown Table

| Component | Nature | Toffoli Cost | Qubit Footprint | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **`ANGLE_k` Circuits (10 circuits)** | Explicit kickmix simulation | ~78,000 Toffolis | ~110 qubits (cap: 128) | Loads 75 angles across 3976 addresses |
| **Outer State Preparation** | Heuristic formula (`SpinFreeData_V1`) | ~12,000 Toffolis | ~45 qubits | Driven by rank $R$ and $B$ |
| **Inner State Preparation** | Heuristic formula (`SpinFreeData_V1`) | ~8,500 Toffolis | ~35 qubits | Driven by rank $C$ |
| **Givens Rotations** | Analytical formula | $2 \times 75 \times (2 \times 12 - 1) = 3,450$ Toffolis | Reuses orbital register | Controlled adders |
| **Factorization Factor $\lambda_{\text{eff}}$** | Algebraic | $\approx 20.5$ Ha | N/A | Derived from $\Lambda$ and $E_{\text{gap}}$ |
| **Total Baseline Score** | **Combined Product** | **$T_{\text{tot}} \approx 102,000$** | **$Q_{\text{tot}} \approx 200$** | **$S \approx 4.18 \times 10^8$** |

---

## 3. Candidate Reductions & Ranking

| Rank | Candidate Reduction Idea | Mechanism | Exact vs Approx | Verification Catch Mechanism | Priority Score $\frac{\text{Save} \times \text{Conf}}{\text{Effort}}$ |
| :---: | :--- | :--- | :--- | :--- | :---: |
| **1** | **Batch Size Tuning ($J$) & Unary QROM Scheduling** | The baseline chooses $J = 8$. Changing $J$ directly trades Toffolis against persistent qubits ($J \cdot b_{\text{rot}}$). If $J=6$ or $J=7$, we may reduce $Q_{\text{tot}}$ while staying comfortably under the 128-qubit cap. | Exact | Verifier checks exact register layout and qubit bounds. | **Highest (9.2/10)** |
| **2** | **Factorization Rank Compression ($R, B, C$)** | Re-run alternating least-squares (ALS) or gradient tensor decomposition to shrink $R$ from 65 to ~55 and $B, C$ from 60 to ~50 while keeping Frobenius residuals $< 20\text{ mHa}$. Reduces rows from 3,976 to ~2,800, directly cutting QROM Toffolis and state prep by $> 25\%$. | Approx | Caught by Frobenius norm checks `error_1` and `error_2` $\le 20\text{ mHa}$. | **High (9.0/10)** |
| **3** | **Optimal Givens Tree Search (Short-Depth / Spanning)** | Use spectral clustering on two-body orbital integrals to construct a Givens spanning tree $T$ that clusters active orbitals together, reducing large angle variances and improving compression. | Exact | Verified by `TreeMajoranaCoefficients` classical reconstruction. | **Med-High (7.8/10)** |
| **4** | **Angle Precision Reduction ($b_{\text{rot}} = 11$ or $10$)** | Test whether $b_{\text{rot}} = 11$ bits retains the required 20 mHa chemical precision. If it passes, every Givens rotation Toffoli drops by 4, persistent registers drop by $J$ qubits, and QROM table size drops by ~8%. | Approx | Residual error checked against reference FCIDUMP. | **Med-High (7.5/10)** |
| **5** | **Advanced QROM Decomposition (Babbush-Gidney)** | Implement segmented/windowed QROM lookup tables with clean temporary ancillas to cut Toffoli counts on unary iteration. | Exact | Verifier fuzz testing on address retrieval. | **Medium (6.5/10)** |

---

## 4. Verifier Capabilities and Detection Limits

- **What It Detects:**
  - Evaluates all valid vector addresses $a < 76 + R \cdot B$ with 64 measurement samples per address [FROM SOURCE].
  - Checks exact retrieval of 75 angle words, unchanged addresses, clean workspace, and phase restoration [FROM SOURCE].
  - Strict acceptance gates:
    - $\text{error}_1 \le 0.020$ Ha (20 mHa).
    - $\text{error}_2 \le 0.020$ Ha (20 mHa).
    - Hard cap: every single `angle_k` circuit must use $\le 128$ qubits.
    - Floors: $\Lambda > 49.0$ Ha and $E_{\text{gap}} > 3.914898$ Ha.
- **Risks to AVOID:**
  - Attempting to shrink $\Lambda$ below 49.0 or game $E_{\text{gap}}$ triggers an instant rejection assertion [FROM SOURCE].
  - Overstepping the 128-qubit ceiling on ANY single `angle_k` circuit causes immediate disqualification [FROM SOURCE].

---

## 5. First 5 Concrete Experiments for Devin

### Experiment 3.1: Parametric Batch Size Sweep ($J \in [4, 12]$)
- **Input:** `verifiers/dfthcsos/example_submission/angle_k_reference_circuit.py`.
- **Change:** Modify batch size $J$ from 8 to values in $\{5, 6, 7, 9, 10, 11\}$. Recompile angle circuits for the baseline `submission.npz`.
- **Verification Command:** `python dfthcsos/verify.py sample_submission/dfthcsos/`.
- **Success Criterion:** Find optimal $J$ minimizing $T_{\text{tot}} \times Q_{\text{tot}}$ while verifying that all circuits stay $\le 128$ qubits.

### Experiment 3.2: Precision Pruning ($b_{\text{rot}} = 11$)
- **Input:** `submission.npz` and `angle_k_reference_circuit.py`.
- **Change:** Round `angle_words` from 12-bit to 11-bit integers. Evaluate chemical reconstruction error via `scoreinfra/dfthc_math.py`.
- **Verification Command:** Check if $\text{error}_1, \text{error}_2 \le 20\text{ mHa}$ and run verifier.
- **Success Criterion:** If 20 mHa gate passes, reduces Givens Toffolis and register footprint immediately by $\sim 8\%$.

### Experiment 3.3: Alternating Least Squares (ALS) Low-Rank Factorization
- **Input:** `FeMoCo76o113e.fcidump` and baseline `submission.npz`.
- **Change:** Train a smaller rank tensor factorization with $R = 58, B = 54, C = 54$ using regularized ALS starting from the baseline tensors.
- **Verification Command:** Check Frobenius error and LCU floors.
- **Success Criterion:** Residuals $< 20\text{ mHa}$, reducing total address rows by $> 20\%$.

### Experiment 3.4: Minimum-Spanning-Tree Givens Reordering
- **Input:** `tree_edges` in `submission.npz`.
- **Change:** Compute edge weights from orbital exchange integrals and construct a Minimum Spanning Tree (MST) rather than a linear or random tree.
- **Verification Command:** Verify with `verify.py`.
- **Success Criterion:** Reduced angle word entropy and verified compatibility.

### Experiment 3.5: QROM Unary Iteration Optimization
- **Input:** `angle_k_reference_circuit.py`.
- **Change:** Optimize the unary iteration cursor movement and control decoding to eliminate redundant `X` gates and intermediate flags.
- **Verification Command:** Run `verify.py`.
- **Success Criterion:** $\ge 5\%$ reduction in simulated angle Toffolis with identical word outputs.

---

## 6. Unknowns & What to Check
1. [UNKNOWN] What training script generated the baseline factorization tensors $(U, W)$? (Reference mentions a separate starter kit dataset: "Verifiable Circuit Compilation Starter Kit").
2. [UNKNOWN] How close is the baseline's current Frobenius residual to the 20 mHa boundary? (Need to run `scoreinfra/dfthc_math.py` on baseline to find exact slack).
