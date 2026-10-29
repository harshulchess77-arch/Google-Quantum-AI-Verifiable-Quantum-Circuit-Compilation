# Strategy and Search Design: Winning the $150k Prize Pool

**Document Target:** `notes/strategy_and_search_design.md`  
**Author:** Lead Research Engineer  
**Classification Guide:** Every recommendation is marked as `[FROM SOURCE]`, `[INFERENCE]`, or `[UNKNOWN]`.

---

## 1. Timeline and Week-by-Week Roadmap (Oct 2026 – Jan 2027)

| Period | Strategic Focus & Milestones | Deliverables |
| :--- | :--- | :--- |
| **Week 1 (Oct 28 – Nov 3)** | **Harness Activation & Quick Wins:** Verify baseline scores on Devin (Linux). Execute Experiment 1.1 (Horner precision tuning) and Experiment 3.1 ($J$ batch size tuning on DFTHC). Establish working baseline submissions for all 3 tasks. | First valid baseline submission scored on Kaggle ($1.0$ baseline). |
| **Week 2 (Nov 4 – Nov 10)** | **Targeted Architectural Optimizations:** Implement Remez minimax polynomials for `invsqrt`; drop in 51-Toffoli Galois multiplier and compact working registers in `dqi`. | Score $\ge 1.35$ on Public Leaderboard. |
| **Week 3 (Nov 11 – Nov 17)** | **Deep Compression & Scaling:** Execute low-rank ALS tensor factorization on FeMoCo ($R, B, C$ reduction) to cut DFTHC QROM addresses. Benchmark II iteration truncation trade-off. | Score $\ge 1.70$. Prepare clean public notebook draft. |
| **Milestone Gate (Nov 20, 2026)** | **Mid-Competition Milestone Prize ($10,000):** Finalize and publish high-scoring public notebook before 11:59 PM UTC, Nov 20. Must be maintained publicly until competition close. | Submit for Milestone Prize. |
| **Weeks 5–8 (Nov 21 – Dec 18)** | **Longest Leader Drive:** Run continuous search loops with Devin on single-task specializations. Regularly deploy incremental improvements to hold top rank on leaderboard. | Target Longest Leader Prize ($10,000). |
| **Weeks 9–10 (Dec 19 – Jan 4)** | **Longest Leader Closeout (Jan 4, 2027):** Ensure qualifying notebooks and datasets are public by Jan 4, 2027 deadline. | Lock in Longest Leader Prize qualification. |
| **Weeks 11–12 (Jan 5 – Jan 20)** | **Endgame Optimization:** Multi-task integration, final verification runs across private splits, code cleanup, reproducibility documentation (Apache 2.0). | Final 2 submissions selected by Jan 20, 2027. |

---

## 2. Agentic Loop Design & Context Control

### The Challenge of Context in Giant Circuits
Circuit files contain between $10^5$ and $8.6 \times 10^7$ gates [FROM SOURCE]. Feeding raw `.kmx` or `.kmb` circuit files to an LLM blows up token budgets and causes catastrophic hallucinations [INFERENCE].

### Architectural Loop Rules
1. **Never pass raw circuits to the LLM:** The LLM operates strictly on **parameterized Python generator scripts** (e.g., `nr_reference_circuit.py`, `dqi_reference_circuit.py`, `angle_k_reference_circuit.py`) and small, isolated arithmetic building blocks (e.g. `_add_row`, `_square`, `GF2FieldMultiplier`) [INFERENCE].
2. **Context Window Packaging:** In each iteration, Devin receives:
   - The current component generator code ($< 300$ lines).
   - Component test harness script ($< 50$ lines).
   - Summary of last 3 failed experiments and exact verifier error snippets ($< 500$ tokens).
   - Current best score breakdown: $(Q, T, \text{Cost})$.
3. **Hybrid Proposer Workflow:**
   - **Hand-Coded Rewrites:** Used for parameter sweeps (`delta_bits`, `coef_bits`, `n_iters`, batch size $J$). Zero token cost, fast, deterministic.
   - **LLM Proposers:** Used for arithmetic rewrites (replacing Karatsuba, injecting MBUC measurements, restructuring polynomial Horners).
4. **Failure Memory:** `LOG.md` maintains an active hash of explored parameter sets to prevent repeating dead ends.

---

## 3. Compute and Token Budget

### Pricing Model (Nov 2026 Discount vs Standard)
- Through Nov 30, 2026: Discounted rate of **$2.00 / 1M input tokens** and **$10.00 / 1M output tokens**.
- Standard rate: **$4.00 / 1M input tokens** and **$20.00 / 1M output tokens**.

### Recommended Model Thinking Levels per Stage
- **Stage 1: Parameter Sweeps & Grid Tuning:** `LOW` thinking (deterministic Python loops, no LLM required).
- **Stage 2: Circuit Rewrites & Code Generation:** `MEDIUM` thinking (~$0.02 – $0.05 per proposal).
- **Stage 3: Architectural Redesign & Failure Diagnosis:** `HIGH` thinking (deep reasoning on algebraic Galois field and tensor factorizations, ~$0.15 per cycle).
- **Estimated Total Cost:** 500 iterations $\approx$ **$35 – $75 total LLM spend**, well within budget.

---

## 4. Single-Task Performance Prize Recommendation ($10,000 Prize)

### Recommendation: Benchmark II (`dqi`)
- **Confidence:** **VERY HIGH (90%)** [INFERENCE].
- **Why DQI is the Best Target:**
  1. **Quadratic Qubit Dominance ($Q^2$):** In Benchmark I and III, costs scale linearly with $Q \times T$. In DQI, the cost is $R(\varepsilon^+) \cdot Q^2 \cdot T$. Any optimization that compacts scratch registers or reuses arrays gives a squared bonus [FROM SOURCE].
  2. **Clear Classical Error-Correction Levers:** Reed–Solomon decoding is a mature classical field. Specialized sub-quadratic multipliers and bounded-iteration approximations can cut Toffolis significantly while keeping $\varepsilon^+$ well below the $1/16$ penalty cliff [FROM SOURCE].
  3. **High Baseline Inefficiency:** The reference implementation uses a generic 63-Toffoli multiplier and generous scratch registers ($1,893$ qubits). Khattar et al. already proved 51-Toffoli multipliers work, proving substantial immediate room for optimization [FROM SOURCE].

---

## 5. Risk Matrix & Mitigations

| Risk | Impact | Mitigation Strategy |
| :--- | :---: | :--- |
| **Verifier Timeout on Devin** | High | Run rapid development on truncated shot counts (e.g. `--shots-per-x 1` or `--num-shots 1024`) during candidate search; only run full 102,400 shots on candidates that beat `best/`. |
| **Fiat-Shamir Salt Drift** | High | All local seeds must combine SHA-256 with competition salts; never hard-code outputs for specific test vectors. |
| **Approximation Blowup ($\varepsilon^+ \ge 1/16$)** | Severe | Enforce automated safety assertions in `tools/verify.py` that immediately reject candidates exceeding $\varepsilon^+ \ge 0.04$. |
| **128-Qubit Cap in DFTHC** | Fatal | Hard assertion check in `tools/verify.py` that rejects any `angle_k` circuit with $> 128$ qubits before submitting. |
| **Licensing Incompatibility** | Disqualification | All developed code must be compatible with Apache 2.0 open source license as required by competition rules. |

---

## 6. Public Notebook Strategy

- **When to Share:** Publish a working baseline + moderate improvement (~1.15 score) around **November 16–18** (just prior to the Nov 20 Milestone deadline).
- **What to Publish:** A well-documented, clean notebook showing the basic compilation and verification loop using the baseline and a minor parameter optimization.
- **What to Hold Back:** Do NOT publish our core mathematical breakthroughs (such as the 51-Toffoli Galois multiplier, compact register allocations, or trained low-rank FeMoCo factorizations) until after the Milestone and Longest Leader windows!

---

## 7. The 10 Most Important Decisions to Make This Week

1. **Host Environment for Devin:** Confirm Devin has access to a Linux environment with glibc support where `kickmix.so` loads cleanly.
2. **First Benchmark Focus:** Commit to Benchmark I (`invsqrt`) and Benchmark II (`dqi`) as our initial parallel tracks.
3. **Verification Shot Divisor Policy:** Set local search verification to `--shot-divisor 10` for fast filtering, with mandatory full-shot confirmation before updating `best/`.
4. **Baseline Score Anchoring:** Run the reference baseline through `tools/verify.py` on Devin and record the exact baseline scores in `bench*/LOG.md`.
5. **Initial Kaggle Submission:** Submit the untouched `sample_submission/` zip archive to Kaggle immediately to verify that our submission pipeline and Kaggle scoring match.
6. **Git Version Control:** Initialize a clean git repository for our project files so atomic tracking and rollbacks are guaranteed.
7. **Precision Tuning Strategy:** Authorize the automated parameter sweep on `nr_reference_circuit.py` precision bits.
8. **Galois Multiplier Implementation:** Decide whether to implement the 51-Toffoli multiplier via table-driven Karatsuba or polynomial basis squaring.
9. **FeMoCo Training Setup:** Review whether to run ALS tensor factorization locally or download the official Starter Kit dataset.
10. **Public Notebook Publishing Date:** Set the target publication date for our public notebook (recommended: Nov 18, 2026).
