# Qiskit Fall Fest 2026 — Phase 2: Optimization Track
## PS-O1: Quantum Optimization of Network Partitioning Using QAOA

**Team:** Phoenix  
**Problem Statement:** PS-O1 (Max-Cut on Weighted Graphs)  
**Track:** Quantum Optimization (QAOA / QUBO)  

---

## 1. Executive Summary

This repository contains the complete, reproducible Phase 2 submission for **PS-O1: Quantum Optimization of Network Partitioning Using QAOA**.

The project investigates algorithm-architecture co-design by solving the official locked 6-vertex weighted network partitioning instance (total edge weight 27.0) across three processor architectures:
- **Processor A:** 5-qubit branching tree (capacity-limited baseline).
- **Processor B:** 9-qubit sparse heavy-hex lattice (contemporary reference).
- **Processor D:** 9-qubit custom co-designed topology (engineered to eliminate routing SWAP bottlenecks).

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

### Environment Setup (Python 3.10–3.13)
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
Processor A provides 5 physical qubits. Compiling a 6-logical-qubit graph triggers the official capacity rule (`needs 6 qubits > 5`) and is marked `executable: False`. We report this boundary condition honestly without truncating the problem instance.

### Processor B (Heavy-Hex Routing Bottleneck)
Due to sparse planar connectivity and high graph diameter (3 hops), compiling the 60% dense graph requires inserting **1 SWAP gate** (3 extra CX gates), expanding physical depth from logical 10 to **37** (+270%) and CX count to **21**.

### Processor D (Custom Co-Design)
Processor D is a 9-qubit architecture directly embedding the PS-O1 interaction topology into physical qubits 0–5 while maintaining degrees $\le 4$ and augmenting with auxiliary nodes 6–8:
- **0 SWAP gates** inserted.
- **0 CX overhead** (18 CX gates total).
- Physical depth reduced from 37 (Processor B) to **29** (Processor D) — an **$21.6\%$ depth reduction**.
- Fully validated against `validate_processor_d()`.

---

## 6. AI Assistance Statement

In accordance with hackathon guidelines, AI tools (Claude 3.7 Sonnet / Google Gemini) were utilized for:
- Accelerating script boilerplate, LaTeX equation rendering, and matplotlib styling.
- Validating schema compliance with official Challenge Kit templates.
All algorithmic derivations, QUBO formulation, QAOA parameters, Processor D topology design, and final scientific interpretations were developed, verified, and confirmed by Team Phoenix.
