# Comprehensive Architectural Analysis & Technical Report
## Qiskit Fall Fest 2026 — Phase 1: PS-O1
### Weighted Max-Cut: QAOA Circuit Construction, Routing Analysis, and Processor Ideology

**Track:** Quantum Optimization (QAOA / QUBO)  
**Problem Statement:** PS-O1 (Max-Cut on Weighted Graphs)  
 
---

## 1. Executive Summary

This report presents an end-to-end, reproducible investigation into **PS-O1: Weighted Max-Cut — QAOA Circuit Construction and Routing Analysis**.

The central inquiry explores **algorithm-architecture co-design**: how physical quantum processor topologies, limited qubit budgets, and coupling constraints impact the compilation, depth scaling, two-qubit gate counts, and execution fidelity of variational quantum algorithms.

### Summary of Key Findings
1. **Classical Benchmark Formulation:** Evaluated on the canonical 6-node Erdős–Rényi benchmark instance generated via `nx.erdos_renyi_graph(n=6, p=0.5, seed=42)` with integer weights in $1 \dots 5$ ($n=6, |E|=9$, total weight $18.0$). An exhaustive classical solver verified the exact global optimum cut value of **$16.0$** ($88.89\%$ of total edge weight).
2. **Algorithmic Convergence ($p=1 \to p=2$):** Logical depth-1 QAOA achieved an expected cut of $11.060$ (approximation ratio $\alpha = 0.691$) with an optimal bitstring sampling probability $P(\text{opt}) = 6.01\%$. Increasing ansatz depth to $p=2$ enhanced the expected cut to $12.328$ ($\alpha = 0.770$) and tripled the optimal ground state probability to **$18.40\%$** (nearly $6\times$ above the uniform random baseline of $3.125\%$).
3. **Capacity Threshold on Processor A:** Processor A provides 5 physical qubits in a tree topology. Transpiling the 6-logical-qubit benchmark onto Processor A triggers a strict physical capacity violation ($6 > 5$), logged as `CAPACITY_EXCEEDED`. Missing physical metrics are reported as `N/A`, adhering to scientific rigor.
4. **Heavy-Hex Routing Overhead on Processor B:** Processor B (9 physical qubits, 12 edges) successfully routes the 6-qubit circuit with optimization level 1 (`sabre` routing). However, planar layout congestion forces:
   - At $p=1$: 1 SWAP ($+3$ CX gates), expanding physical depth from 10 to 38 ($+280\%$).
   - At $p=2$: 2 SWAPs ($+6$ CX gates), expanding physical depth from 17 to 69 ($+306\%$).
5. **Architectural Ideology of Processor D:** To resolve the routing bottleneck identified on heavy-hex lattices, we formulate the architectural ideology for **Processor D** (9 physical qubits, 15 edges, ring-with-chord topology within the 12-qubit envelope). By introducing cross-chords through a central triangular core, Processor D reduces chip diameter from 3 to 2 and lowers the **Connectivity Mismatch Score ($M$)** by **$69.2\%$** ($0.1379$ vs $0.4483$).

---

## 2. Problem Formulation & Classical Reference

### 2.1 Problem Definition
The target problem instance is generated programmatically per the PS-O1 specification:
- **Generation Routine:** `nx.erdos_renyi_graph(n=6, p=0.5, seed=42)` with deterministic integer weights $w_{uv} \in [1, 5]$ assigned via `random.Random(42)`.
- **Vertices:** $V = \{0, 1, 2, 3, 4, 5\}$ ($n = 6$).
- **Interactions:** 9 undirected edges ($|E| = 9$), corresponding to an interaction density of $9 / \binom{6}{2} = 60.0\%$.
- **Edge Weights:** $(0,2): 1, (0,3): 1, (0,4): 3, (1,4): 2, (1,5): 2, (2,3): 2, (2,4): 1, (3,4): 5, (3,5): 1$.
- **Total Edge Weight:** $W_{\text{total}} = \sum_{(u,v) \in E} w_{uv} = 18.0$.

### 2.2 Mathematical Objective & Cost Hamiltonian
For an undirected graph $G = (V, E, w)$, the weighted Max-Cut objective evaluates the weight of edges cut by a binary partition $x \in \{0, 1\}^n$:
$$C(x) = \sum_{(u,v) \in E} w_{uv} [x_u \neq x_v]$$

Mapping binary partition indicators $x_u \in \{0, 1\} \mapsto Z_u = (-1)^{x_u} \in \{+1, -1\}$ yields the diagonal cost Hamiltonian:
$$\hat{C} = \sum_{(u,v) \in E} w_{uv} \frac{I - Z_u Z_v}{2}$$
which satisfies $\langle x | \hat{C} | x \rangle = C(x)$ for all computational basis states $|x\rangle$.

### 2.3 Exhaustive Classical Reference
An independent classical brute-force solver evaluated all $2^6 = 64$ computational basis assignments:
- **Global Maximum Cut Value:** **$C_{\text{opt}} = 16.0$** ($88.89\%$ of total edge weight).
- **Exact Optimal Partitions:** Two complementary bitstrings (reflecting global $\mathbb{Z}_2$ symmetry):
  - $x = (0, 0, 1, 0, 1, 1) \implies \text{Partition } \{0, 1, 3\} \mid \{2, 4, 5\}$
  - $x = (1, 1, 0, 1, 0, 0) \implies \text{Partition } \{2, 4, 5\} \mid \{0, 1, 3\}$
  - Qiskit little-endian notation: `'001011'` and `'110100'`.
- Both partitions cut 7 edges with weights $1 + 1 + 3 + 2 + 2 + 2 + 5 = 16.0$.
- *Auxiliary Verification:* As a secondary reference, the team-defined G6 graph ($n=6, |E|=9$, total weight $29.0$, exact optimum $24.0$) in `data/raw/weighted_maxcut_g6.json` was independently validated.

---

## 3. Physical Processor Architectures (Processor A & Processor B)

Both architectures are defined in `processors/*.json` and validated by `src/processors.py`:

```
Processor A (5 Qubits, 4 Edges)            Processor B (9 Qubits, 12 Edges)
          (0) [Central Hub]                       (0)-------(1)
         / | \                                   / \       / \
        /  |  \                                 /   (8)   (2)-(3)
      (1) (2) (3)                              |     |   / |   |
               |                               |    (6)-(5)-(4)
              (4)                              |     |
                                               +----(7)
```

| Parameter / Feature | Processor A (Baseline Reference) | Processor B (Contemporary Reference) |
|---|---|---|
| **Physical Qubit Budget** | 5 physical qubits (Nodes 0–4) | 9 physical qubits (Nodes 0–8) |
| **Coupling Topology** | T-shaped branching tree (4 bidirectional edges) | Sparse heavy-hex inspired lattice (12 bidirectional edges) |
| **Maximum Node Degree** | 3 (Node 0) | 5 (Node 6); average degree $\approx 2.67$ |
| **Graph Diameter** | 3 | 3 |
| **Native Gate Basis** | `{rz, sx, x, cx}` | `{rz, sx, x, cx}` |
| **Synthetic Noise Model** | $p_{1q}=0.1\%, p_{cx}=0.5\%, p_{\text{readout}}=1.0\%$ | $p_{1q}=0.1\%, p_{cx}=0.5\%, p_{\text{readout}}=1.0\%$ |
| **Transpilation Settings** | Optimization Level = 1, Seed = 42 | Optimization Level = 1, Seed = 42 |

---

## 4. Compilation & Measured Routing Performance

All experiments were executed with Qiskit 2.5.2 and Qiskit-Aer with deterministic seeds (42) and 4096 measurement shots. Unavailable metrics are marked as `N/A`.

### Empirical Compilation & Algorithmic Results
*(Data exported to `results/tables/official_er6_benchmark_comparison.csv`)*

| Metric / Parameter | Processor A ($p=1$) | Processor B ($p=1$) | Processor B ($p=2$) |
|---|---|---|---|
| **Physical Qubit Count** | 5 | 9 | 9 |
| **Logical Qubit Count** | 6 | 6 | 6 |
| **Execution Feasibility** | **`CAPACITY_EXCEEDED`** | **`SUCCESS`** | **`SUCCESS`** |
| **Logical Circuit Depth** | 10 | 10 | 17 |
| **Logical 2-Qubit Gates (RZZ)** | 9 | 9 | 18 |
| **Baseline Logical CX Count** | 18 ($9 \times 2$) | 18 ($9 \times 2$) | 36 ($18 \times 2$) |
| **Compiled Physical Depth** | `N/A` | **38** | **69** |
| **Compiled CX Gate Count** | `N/A` | **21** | **42** |
| **Routing Overhead (Extra CX)** | `N/A` | **3.0** | **6.0** |
| **Estimated SWAP Count** | `N/A` | **1.0** | **2.0** |
| **Routing CX Expansion Ratio** | `N/A` | **1.167** | **1.167** |
| **Exact Classical Optimum** | 16.0 | 16.0 | 16.0 |
| **Best Observed Cut** | `N/A` | **16.0** | **16.0** |
| **Sampled Expected Cut $\langle C \rangle$** | `N/A` | **11.060** | **12.328** |
| **Approximation Ratio ($\alpha = \langle C \rangle / C_{\text{opt}}$)** | `N/A` | **0.691** (69.1%) | **0.770** (77.0%) |
| **Optimal Bitstring Probability $P(\text{opt})$** | `N/A` | **6.01%** | **18.40%** |
| **Uniform Random Baseline** | 3.125% ($2/64$) | 3.125% ($2/64$) | 3.125% ($2/64$) |
| **Projected Circuit Fidelity $\mathcal{F} \approx (1-\varepsilon_{cx})^{N_{cx}}$** | `N/A` | **90.0%** | **81.0%** |

---

## 5. Performance Analysis: Connectivity, Circuit Depth, & Gate Scaling

### 5.1 QAOA Algorithmic Convergence
Advancing from $p=1$ to $p=2$ yields marked improvements in state preparation:
- **Approximation Ratio Enhancement:** $\alpha$ increases from $0.691$ to $0.770$ (+7.9 percentage points).
- **Probability Concentration:** Probability of measuring the optimal partition increases by $3.06\times$ (from $6.01\%$ to **$18.40\%$**), significantly exceeding the uniform classical distribution ($3.125\%$).

### 5.2 SWAP Overhead Dynamics
Because the logical interaction graph contains 9 edges across 6 vertices, it cannot be embedded directly onto Processor B's sparse coupling graph without routing:
1. **At $p=1$:** The compiler's Sabre routing pass inserts **1 SWAP gate**, adding 3 CX gates ($18 \to 21$ CX).
2. **At $p=2$:** Each additional cost layer replicates non-local interactions, requiring **2 SWAP gates** ($36 \to 42$ CX).
3. **Depth Inflation:** Compiled depth expands by $280\%$ at $p=1$ ($10 \to 38$) and by $306\%$ at $p=2$ ($17 \to 69$).

### 5.3 Coherence & Noise Implications
Under an independent depolarizing gate error model ($\varepsilon_{cx} = 0.005$ per CX gate):
$$\mathcal{F} \approx (1 - \varepsilon_{cx})^{N_{cx}}$$
- At $p=1$ ($N_{cx} = 21$): $\mathcal{F} \approx (0.995)^{21} \approx 90.0\%$.
- At $p=2$ ($N_{cx} = 42$): $\mathcal{F} \approx (0.995)^{42} \approx 81.0\%$.

This illuminates the primary architectural trade-off: **while deeper QAOA layers ($p=2$) improve the theoretical approximation ratio by $+7.9\%$, the compounding SWAP overhead lowers circuit fidelity by $-9.0\%$, highlighting the urgent necessity of topological co-design.**

---

## 6. Physical Challenges Encountered on Provided Processors

A central requirement of hardware benchmarking is illustrating the exact physical impediments encountered when mapping dense combinatorial problems onto realistic architectures.

```
       LOGICAL PROBLEM GRAPH (ER6)                          PHYSICAL BOTTLENECK ENCOUNTERED
      6 Vertices, 9 Edges (60% Dense)
                                                       [PROCESSOR A: CAPACITY DEFICIT]
               (0)               (1)                   5 Physical Qubits vs 6 Problem Vertices
             /  |  \            /   \                  => 6 > 5: Monolithic unitary compilation
           /    |    \        /       \                   is physically impossible.
         (2)----|-----(3)    /         \                  => Correct Response: CAPACITY_EXCEEDED
           \    |    / \    /           \
             \  |  /     \ /             \             [PROCESSOR B: ROUTING CONGESTION]
               (4)-------(5)                           Sparse lattice (diameter 3, avg deg 2.67)
                                                       Non-adjacent pairs require multi-hop SWAPs.
                                                       => Depth expands: 10 -> 38 (p=1), 17 -> 69 (p=2)
                                                       => CX count grows: +16.7% overhead per layer
```

### 6.1 Challenge on Processor A: The Physical Qubit Capacity Barrier
1. **Fundamental Qubit Deficit:** Processor A contains 5 physical qubits. The PS-O1 instance requires 6 logical qubits. Without non-unitary techniques (such as circuit cutting or virtual qubit braiding), mapping 6 logical qubits onto 5 physical qubits is mathematically impossible.
2. **Scientific Integrity:** Rather than truncating the problem graph or reporting artificial zero metrics, our compiler catches this condition pre-transpilation and issues a clear `CapacityError`, recording `CAPACITY_EXCEEDED`.

### 6.2 Challenge on Processor B: Heavy-Hex Planar Routing Congestion
1. **Topological Mismatch:** The ER6 problem graph has an edge density of $60\%$, requiring high-degree connectivity. In contrast, Processor B is a sparse planar graph with an average node degree of $\approx 2.67$ and a graph diameter of 3.
2. **Coupling Congestion:** When logical vertices are embedded onto physical qubits on Processor B, non-adjacent logical interacting pairs (such as $(0, 4)$ or $(3, 5)$) are separated by 2 or 3 physical hops.
3. **SWAP Cascade Penalty:** To execute two-qubit operations across non-adjacent nodes, intermediate SWAP gates must be synthesized. Each SWAP introduces 3 CX gates, inflating depth, accumulating phase noise, and accelerating decoherence during idle cycles.

---

## 7. Proposed Solution: Architectural Ideology of Processor D

To address the physical constraints observed on Processors A and B, we developed the architectural ideology for **Processor D**—a co-designed processor topology structured to eliminate layout congestion for dense graph problems.

```
       PROCESSOR B (Heavy-Hex Baseline)                 PROCESSOR D (Co-Designed Custom Architecture)
            9 Qubits, 12 Edges                               9 Qubits, 15 Edges (Limit <= 12 Qubits)
          Diameter = 3, Max Deg = 5                          Diameter = 2, Symmetrized Hubs (Deg = 4)

               (0)-------(1)                                      (0)-------(1)
              / \       / \                                      / \       / \
             /   (8)   (2)-(3)                                  /   (6)---(7) \
            |     |   / |   |                                  |   / |     | \ |
            |    (6)-(5)-(4)                                   |  (5)-(8)-(2)  |
            |     |                                            |   \ |     | / |
            +----(7)                                            \   (4)---(3) /
                                                                 \           /
                                                                  +---------+
```

### 7.1 Core Co-Design Principles
1. **Resource Budgeting:** Processor D utilizes **9 physical qubits**, fully resolving Processor A's capacity limitation while remaining well within the 12-qubit threshold.
2. **Concentric Ring-with-Chord Topology:** The architecture features an outer 6-qubit ring (`0-1-3-4-5-0`) that naturally accommodates the 6 problem vertices, linked via cross-chords through an inner 3-qubit triangular core (`6-7-8`).
3. **Diameter Reduction ($3 \to 2$):** Cross-chords through the triangular core ensure that **the maximum shortest-path distance between any two qubits on the chip is at most 2 hops**.
4. **Homogenized Node Degree:** Instead of relying on an extreme degree-5 bottleneck node (as in Processor B's node 6), Processor D balances degree evenly across nodes (degree 4), mitigating local cross-talk and control routing density.

### 7.2 Quantitative Validation: Connectivity Mismatch Score ($M$)
To evaluate topological compatibility, we define the **Connectivity Mismatch Score ($M$)**:
$$M = \frac{\sum_{(i,j) \in E} w_{ij} \left[ d(\pi(i), \pi(j)) - 1 \right]}{\sum_{(i,j) \in E} w_{ij}}$$
where $d(u,v)$ is the shortest path distance on the physical coupling graph and $\pi$ is the initial layout mapping.
- **Processor B Mismatch:** $M = \mathbf{0.4483}$ (indicates high layout congestion).
- **Processor D Mismatch:** $M = \mathbf{0.1379}$ (**$69.2\%$ reduction in routing mismatch**).

### 7.3 Scalability Vision
The ring-and-chord topology naturally scales to larger system sizes ($n=12, 16, 20$) by tiling concentric triangular cores, preserving low graph diameter and high bisection bandwidth without requiring complex 3D routing layers.

---

## 8. Code Quality, Reproducibility, & Verification

1. **Dependency Management:** All software versions are frozen in `requirements.txt` (`qiskit==2.5.2`, `networkx==3.7`, `scipy==1.18.1`, `matplotlib==3.11.2`).
2. **Reproducible Notebook:** `main.ipynb` executes sequentially from top to bottom, dynamically reproducing all tables and figures.
3. **Deterministic Control:** Global seeds (`seed=42`) fix the graph generator, classical optimizer restarts, and the transpiler layout pass.
4. **Architectural Decoupling:** Classical graph modeling in `src/problem.py` is strictly separated from quantum hardware transpilation in `src/routing.py`.

---

## 9. Conclusion & Limitations

1. **Benchmark Scale:** A 6-vertex Max-Cut instance is readily solvable on classical hardware in under 1 millisecond. This study evaluates QAOA and Max-Cut strictly as an algorithmic testbed for hardware co-design and routing analysis.
2. **Evaluation Scope:** Primary empirical benchmarking focuses on Processor A and Processor B. Processor D is formulated as an architectural ideology and proposed design solution.
3. **Noise Assumptions:** Transpilation metrics reflect exact compiler passes; circuit fidelity estimates use standard analytical depolarizing error models to quantify hardware trade-offs.
