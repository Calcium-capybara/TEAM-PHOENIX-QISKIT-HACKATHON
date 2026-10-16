# Qiskit Fall Fest 2026 — Phase 1: PS-O1
## Weighted Max-Cut: QAOA Circuit Construction, Hardware Routing, and Bottleneck Analysis

**Track:** Quantum Optimization (QAOA / QUBO)  
**Problem Statement:** PS-O1 (Max-Cut on Weighted Graphs)  

---

## 1. Executive Summary

This repository contains the complete, reproducible implementation for **PS-O1: Max-Cut on Weighted Graphs** using the Quantum Approximate Optimization Algorithm (QAOA) on 6-node weighted interaction topologies.

The project investigates **algorithm-architecture co-design**:
1. Formulating the weighted Max-Cut objective into a diagonal cost Hamiltonian $\hat{C} = \sum_{(u,v)} w_{uv} \frac{I - Z_u Z_v}{2}$.
2. Validating against an exact classical reference solver using exhaustive brute-force state enumeration across all $2^6 = 64$ bitstrings ($C_{\text{opt}} = 16.0$).
3. Constructing parameterised logical QAOA circuits for depths $p=1$ and $p=2$, and optimizing variational angles $(\boldsymbol{\gamma}, \boldsymbol{\beta})$ via classical COBYLA optimization across multiple restarts.
4. Compiling the synthesized quantum circuits onto physical target architectures:
   - **Processor A:** 5-qubit T-shaped branching tree reference (`[(0,1), (0,2), (0,3), (3,4)]`).
   - **Processor B:** 9-qubit sparse heavy-hex inspired lattice (12 bidirectional edges).
5. Quantifying compilation overhead: circuit depth expansion, CX count scaling, and SWAP routing bottleneck analysis.
6. Formulating the architectural ideology for **Processor D** (9-qubit ring-with-chord topology) to resolve planar layout congestion.

---

## 2. Benchmark Instance & Classical Baseline

### Primary Benchmark: Programmatic Erdős–Rényi Instance (`data/raw/erdos_renyi_6.json`)
Per the PS-O1 specification:
```python
import networkx as nx
import random
random.seed(42)
G = nx.erdos_renyi_graph(n=6, p=0.5, seed=42)
# Integer edge weights 1-5 assigned deterministically via random.Random(42)
```
- **Graph Topology:** 6 vertices ($V = \{0, 1, 2, 3, 4, 5\}$), 9 edges ($|E| = 9$, density $= 60.0\%$).
- **Edge Weights:** `(0,2): 1`, `(0,3): 1`, `(0,4): 3`, `(1,4): 2`, `(1,5): 2`, `(2,3): 2`, `(2,4): 1`, `(3,4): 5`, `(3,5): 1`.
- **Total Edge Weight:** 18.0.
- **Exact Classical Optimum:** Cut weight **16.0** ($88.89\%$ of total weight).
  - Complementary optimal partitions: $\{0, 1, 3\} \mid \{2, 4, 5\}$ and $\{2, 4, 5\} \mid \{0, 1, 3\}$.
  - Optimal bitstrings (Qiskit little-endian): `'001011'` and `'110100'`.

---

## 3. Hardware Architectures & Empirical Findings

### Processor Configurations
- **Processor A:** 5 physical qubits, T-shaped branching tree `[(0,1),(0,2),(0,3),(3,4)]` with central hub at qubit 0.
- **Processor B:** 9 physical qubits, sparse heavy-hex inspired lattice (12 bidirectional edges).
- **Native Gate Basis & Noise Model:** `{rz, sx, x, cx}` with synthetic depolarizing rates $p_{1q}=0.1\%, p_{cx}=0.5\%, p_{\text{readout}}=1.0\%$.

### Hardware Compilation Summary
*(Extracted from `results/tables/official_er6_benchmark_comparison.csv`)*

| Architecture | QAOA Depth ($p$) | Compilation Status | Logical Depth | Logical CX | Compiled Depth | Compiled CX | Routing SWAPs | Best Cut | Exact Optimum | Approx Ratio ($\alpha$) |
|---|---|---|---|---|---|---|---|---|---|---|
| **Processor A** | 1 | `CAPACITY_EXCEEDED` | 10 | 18 | `N/A` | `N/A` | `N/A` | `N/A` | 16.0 | `N/A` |
| **Processor B** | 1 | `SUCCESS` | 10 | 18 | 38 | 21 | 1.0 (3 CX) | 16.0 | 16.0 | 0.691 (69.1%) |
| **Processor B** | 2 | `SUCCESS` | 17 | 36 | 69 | 42 | 2.0 (6 CX) | 16.0 | 16.0 | 0.770 (77.0%) |

### Key Experimental Insights
1. **Capacity Threshold (Processor A):** Compiling a 6-logical-qubit benchmark onto a 5-physical-qubit processor raises `CapacityError`, recorded honestly as `CAPACITY_EXCEEDED` without fabricating data.
2. **Heavy-Hex Routing Overhead (Processor B):** Due to the sparse planar connectivity, non-adjacent logical interactions require routing:
   - At $p=1$: 1 SWAP ($+3$ CX gates), expanding physical depth from 10 to 38 ($+280\%$).
   - At $p=2$: 2 SWAPs ($+6$ CX gates), expanding physical depth from 17 to 69 ($+306\%$).
3. **Approximation vs Noise Trade-off:** Increasing ansatz depth ($p=1 \to p=2$) raises the ideal approximation ratio ($\alpha = 0.691 \to 0.770$) and triples optimal ground state probability ($6.01\% \to 18.40\%$), but doubles physical CX count ($21 \to 42$), reducing projected circuit fidelity from $90.0\%$ to $81.0\%$.

---

## 4. Architectural Co-Design & Processor D Ideology

To overcome the routing bottleneck identified on Processor B,:
- **Physical Challenges Encountered (Section 6):** Diagrammatic and mathematical analysis of the capacity barrier on Processor A and planar routing congestion on Processor B.
- **Ideology of Building Processor D (Section 7):** A co-designed 9-qubit ring-with-chord topology featuring an outer 6-qubit ring and an inner 3-qubit triangular core. This reduces graph diameter from 3 to 2, cuts maximum shortest-path distances, and reduces the **Connectivity Mismatch Score ($M$)** by **$69.2\%$** ($0.1379$ vs $0.4483$).

---

## 5. Quickstart & Verification

```powershell
# 1. Install dependencies
pip install -r requirements.txt

# 2. Execute the reproducible notebook
jupyter notebook main.ipynb
```

All benchmark figures in `results/figures/` and tables in `results/tables/` are dynamically reproduced by executing `main.ipynb`.

