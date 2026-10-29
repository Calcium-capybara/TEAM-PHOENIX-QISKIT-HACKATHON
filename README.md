# Qiskit Fall Fest 2026 — Phase 2: Optimization Track
## PS-O1: Quantum Optimization of Network Partitioning Using QAOA

**Team:** Phoenix  
**Problem Statement:** PS-O1 (Max-Cut on Weighted Graphs)  
**Track:** Quantum Optimization (QAOA / QUBO)  

---

## 1. Overview & Key Results

This project presents our Phase 2 work on **PS-O1: Quantum Optimization of Network Partitioning Using QAOA**. 

Our team investigated how physical quantum chip layouts, limited qubit counts, and routing constraints affect the execution of QAOA. We tested the locked 6-vertex weighted graph benchmark (total weight 27.0) across three distinct hardware setups:
- **Processor A:** 5-qubit tree layout (capacity-limited baseline).
- **Processor B:** 9-qubit sparse heavy-hex layout (reference architecture).
- **Processor D:** 9-qubit custom co-designed layout (developed to remove the SWAP bottlenecks seen on B).

### Key Results Summary Table
*(Official Results from `results/tables/results.csv` and `results/tables/bell.csv`)*

| Processor | Condition | Executable | Logical CX | Physical CX | Depth | 2Q Depth | SWAPs | CX Overhead | Best Cut | $r_{\text{best}}$ | Approx Ratio ($r$) | $P(\text{opt})$ | Exact Optimum $C^*$ | Random Baseline $r$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Processor A** | Ideal | `False` | — | — | — | — | — | — | — | — | — | — | 22.0 | 0.6136 |
| **Processor A** | Noisy | `False` | — | — | — | — | — | — | — | — | — | — | 22.0 | 0.6136 |
| **Processor B** | Ideal | `True` | 18 | 21 | 37 | 17 | 1 | 3 | 22.0 | 1.0000 | 0.8073 | 13.96% | 22.0 | 0.6136 |
| **Processor B** | Noisy | `True` | 18 | 21 | 37 | 17 | 1 | 3 | 22.0 | 1.0000 | 0.7874 | 12.60% | 22.0 | 0.6136 |
| **Processor D** | Ideal | `True` | 18 | 18 | 29 | 14 | 0 | 0 | 22.0 | 1.0000 | 0.8052 | 13.84% | 22.0 | 0.6136 |
| **Processor D** | Noisy | `True` | 18 | 18 | 29 | 14 | 0 | 0 | 22.0 | 1.0000 | 0.7862 | 12.50% | 22.0 | 0.6136 |

#### Bell-State Verification on Processor D (`results/tables/bell.csv`)
* **Adjacent Pair (0, 2)** (Distance = 1 hop, 1 CX):
  * Ideal Fidelity: $F = 1.0000 \pm 0.0000$
  * Noisy Fidelity: $F = 0.9633 \pm 0.0021$
* **Farthest Pair (5, 6)** (Distance = 3 hops, 7 CX):
  * Ideal Fidelity: $F = 1.0000 \pm 0.0000$
  * Noisy Fidelity: $F = 0.9485 \pm 0.0025$

---

## 2. Repository Layout

```
project/
├── README.md                      # Team, PS-O1 setup, execution instructions, key results table
├── main.ipynb                     # Complete reproducible notebook executing all objectives
├── requirements.txt               # Pinned dependencies (Qiskit 1.4+, Qiskit-Aer 0.17+, NumPy, Scipy, NetworkX)
├── qff_phase2.py                  # Official organizer starter module (kept strictly unchanged)
├── instances.json                 # Official locked problem instances (kept strictly unchanged)
├── data/
│   └── instance.json              # Locked PS-O1 problem instance extract
├── processors/
│   ├── processor_A.json           # 5-qubit reference tree
│   ├── processor_B.json           # 9-qubit heavy-hex reference
│   └── processor_D.json           # Validated 9-qubit custom co-designed topology
├── results/
│   ├── tables/
│   │   ├── results.csv            # Official kit format benchmark results table
│   │   └── bell.csv               # Objective 1 Bell-state verification table
│   └── figures/                   # PNG figures used in report and notebook
│       ├── problem_graph_partition.png
│       ├── architecture_topologies.png
│       ├── circuit_metrics_comparison.png
│       ├── convergence_curves.png
│       ├── cut_distribution.png
│       └── bell_fidelity.png
├── report.md                      # Comprehensive Phase 2 technical report (Objectives 1–5)
└── Phase One/                     # Preserved archive of all Phase 1 files and historical work
```

---

## 3. Setup & Execution Instructions

### Environment Setup & Execution Options

#### Option A: Using the Official QFF Laptop Setup (`C:\QFF`)
If you ran the official `QFF_2026_INSTALL_AND_TEST_WINDOWS.ps1` installer:
```powershell
# Launch JupyterLab with the official hackathon environment
C:\QFF\.qff2026-venv\Scripts\jupyter-lab.exe
# When opening main.ipynb, ensure the kernel is set to: Python (QFF 2026)
```

#### Option B: Clean Independent Virtual Environment (Python 3.10–3.12)
```powershell
# 1. Create and activate a clean virtual environment
python -m venv opt-env
.\opt-env\Scripts\activate      # Windows (or: source opt-env/bin/activate on Unix)

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch and execute the complete reproducible experiment
jupyter notebook main.ipynb
```

The notebook executes all five objectives end-to-end in under 30 seconds on standard CPU hardware without manual code edits.

---

## 4. Problem Formulation & Methodology (PS-O1)

### Locked Problem Graph
The official PS-O1 instance consists of a 6-vertex graph with 9 weighted edges:
- Vertices: $V = \{0, 1, 2, 3, 4, 5\}$
- Edges: $(0,2): 1, (0,3): 4, (0,4): 4, (1,4): 3, (1,5): 3, (2,3): 5, (2,4): 1, (3,4): 4, (3,5): 2$
- Total Edge Weight: $27.0$

### Exact Classical Solver & Baselines
- **Exact Global Optimum:** $C^* = 22.0$ (cuts 7 of 9 edges, achieving $81.48\%$ of total weight).
- **Optimal Ground States:** Exactly 2 complementary bitstrings:
  - $x = (0, 0, 1, 0, 1, 1) \implies \text{Partition } \{0, 1, 3\} \mid \{2, 4, 5\}$ (Qiskit key `'110100'`)
  - $x = (1, 1, 0, 1, 0, 0) \implies \text{Partition } \{2, 4, 5\} \mid \{0, 1, 3\}$ (Qiskit key `'001011'`)
- **Random Guessing Baseline:** Exhaustive expectation across all 64 basis states yields mean cut $13.50$, random approximation ratio $r_{\text{random}} = 0.6136$, and random optimal probability $P_{\text{opt},\text{random}} = 0.03125$ ($3.125\%$).

### QAOA Implementation & Optimization
- Parameterised $p = 1$ QAOA ansatz with classical COBYLA optimizer across **5 seeded starts** (seeds 0, 1, 2, 3, 4).
- Angles initialized uniformly in $[0, \pi]$.
- Optimal parameters found: $\gamma^* = 0.0840$, $\beta^* = 1.2381$.
- Achieved **$r = 0.8052$** (ideal) and **$r = 0.7862$** (noisy), with $P(\text{opt}) = 13.84\%$ (ideal) and $12.50\%$ (noisy), outperforming random guessing by $4\times$.

---

## 5. Processor Architectures & Routing Bottleneck Analysis

### Processor A (Capacity Barrier)
Processor A has 5 physical qubits, but our network graph problem has 6 vertices (needs 6 qubits). Following the Challenge Kit's explicit capacity rule, we do not truncate the graph or force-fit it. Instead, Processor A is properly reported as `executable: False`.

### Processor B (Heavy-Hex Routing Overhead)
Processor B uses a heavy-hex lattice with sparse connectivity. Because several interacting nodes lack direct physical connections, Qiskit's router must insert **1 SWAP gate** (adding 3 physical CX gates). This increases compiled circuit depth from 10 to **37** and raises physical CX count to **21**.

### Processor D (Our Custom Co-Design)
We engineered Processor D to eliminate the bottleneck seen on Processor B. By directly connecting the 9 problem edges across qubits 0–5 while keeping all node degrees $\le 4$ and connecting auxiliary qubits 6–8:
- **0 SWAP gates** are needed.
- **0 CX overhead** (exact 18 physical CX gates).
- Compiled depth drops from 37 on Processor B down to **29** on Processor D (a **21.6% depth reduction**).
- Passes all rules in `validate_processor_d()`.

---

## 6. Development Notes & Acknowledgements

This implementation was developed by Team Phoenix for Qiskit Fall Fest 2026. General coding assistants and syntax linters were used during development strictly for code formatting, LaTeX equation drafting, and checking data table layouts against the hackathon kit templates. All algorithm design, Hamiltonian formulations, circuit mappings, hardware architecture trade-offs, and result analyses were formulated, tested, and validated directly by our team.

