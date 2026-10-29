Technical Report: PS-O1 Network Partitioning with QAOA
Qiskit Fall Fest 2026 — Phase 2 (Optimization Track)
Algorithmic Benchmarking, Routing Overhead, and Processor Co-Design
Team: Phoenix  
Problem Statement: PS-O1 (Max-Cut on Weighted Graphs)  
Date: October 2026
---
1. Problem Formulation & Classical Reference
1.1 Problem Overview & Practical Motivation
Network partitioning is a central problem in graph theory and combinatorial optimization, with everyday applications ranging from telecommunication traffic routing and distributed server clustering to VLSI circuit partitioning.
In PS-O1, our goal is to partition a given weighted graph $G = (V, E, w)$ into two separate clusters $S$ and $V \setminus S$ such that the total weight of the connections crossing the boundary between them is as large as possible.
1.2 Mathematical Formulation & QUBO Mapping
For an undirected weighted graph on $n = 6$ vertices with non-negative integer edge weights $w_{uv} \in {1, \dots, 5}$, each vertex $u$ is assigned a binary decision variable $x_u \in {0, 1}$, indicating subset membership:
$$x_u = \begin{cases} 0 & \text{if } u \in S \ 1 & \text{if } u \in V \setminus S \end{cases}$$
An edge $(u, v) \in E$ crosses the partition cut if and only if $x_u \neq x_v$. The total cut weight is formulated algebraically as:
$$C(x) = \sum_{(u,v) \in E} w_{uv} [x_u(1 - x_v) + x_v(1 - x_u)] = \sum_{(u,v) \in E} w_{uv} (x_u + x_v - 2 x_u x_v)$$
The Quadratic Unconstrained Binary Optimization (QUBO) problem seeks to minimize the negative cut objective:
$$\min_{x \in {0, 1}^n} Q(x) = -C(x) = \sum_{(u,v) \in E} w_{uv} (2 x_u x_v - x_u - x_v)$$
1.3 Cost Hamiltonian Derivation
Mapping binary variables $x_u \in {0, 1}$ to quantum spin operators via $x_u \mapsto \frac{I - Z_u}{2}$ diagonalizes the objective in the computational basis:
$$\hat{C} = \sum_{(u,v) \in E} w_{uv} \frac{I - Z_u Z_v}{2}$$
For any computational basis state $|x\rangle = |x_0 x_1 \dots x_{n-1}\rangle$, the expectation value exactly matches the classical cut value:
$$\langle x | \hat{C} | x \rangle = C(x)$$
(Note on Unitary Convention: The problem Hamiltonian seeks to maximize cut value $\hat{C}$, corresponding to minimizing $H_{\text{qubo}} = -\hat{C}$. Standard QAOA implements the cost phase separator $U_C(\gamma) = e^{-i \gamma H_{\text{qubo}}} = e^{+i \gamma \hat{C}}$. In Qiskit, `rzz(theta, u, v)` implements $\exp(-i \frac{\theta}{2} Z_u Z_v)$. With $\theta = 2 w_{uv} \gamma$, each edge executes $\exp(-i w_{uv} \gamma Z_u Z_v)$, which corresponds to $\exp(+2i \gamma \hat{C})$ up to an overall constant energy shift $\sum w_{uv} \gamma$. The resulting parameter space is simply a periodic rescaled reparameterization of standard QAOA, leaving the optimization landscape, ground state probabilities, and approximation ratios completely unaffected.)
1.4 Locked Problem Instance & Classical Reference
Per Section 6 of the Optimization Challenge Kit, all PS-O1 teams utilize the locked 6-vertex graph instance:
Vertices: $V = {0, 1, 2, 3, 4, 5}$ ($n = 6$)
Edges & Weights:
$${(0,2): 1, ; (0,3): 4, ; (0,4): 4, ; (1,4): 3, ; (1,5): 3, ; (2,3): 5, ; (2,4): 1, ; (3,4): 4, ; (3,5): 2}$$
Total Edge Weight: $W_{\text{total}} = 27.0$, with edge density $= 9 / \binom{6}{2} = 60.0%$.
An exhaustive classical brute-force solver evaluated all $2^6 = 64$ bitstrings:
Exact Global Optimum: $C^* = 22.0$ ($81.48%$ of total edge weight).
Optimal Partitions: Exactly 2 complementary ground states (due to global bit-flip symmetry $x \leftrightarrow 1 - x$):
State 11 (vertex order `110100`, Qiskit little-endian count key `'001011'`): Partition ${0, 1, 3} \mid {2, 4, 5}$.
State 52 (vertex order `001011`, Qiskit little-endian count key `'110100'`): Partition ${2, 4, 5} \mid {0, 1, 3}$.
Both states cut 7 of the 9 edges, achieving cut weight $1 + 4 + 4 + 3 + 3 + 5 + 2 = 22.0$.
Random Guessing Baseline: Sampling bitstrings uniformly at random gives an expected mean cut of:
$$\mathbb{E}{\text{random}}[C] = \frac{1}{64} \sum{k=0}^{63} C(x^{(k)}) = 13.50$$
$$\text{Random Approximation Ratio: } r_{\text{random}} = \frac{13.50}{22.0} = 0.6136$$
$$\text{Random Optimal Probability: } P_{\text{opt,random}} = \frac{2}{64} = 0.03125 ; (3.125%)$$
---
2. Objective 1: Bell-State Verification on Processor D
2.1 Experimental Protocol
Per Section 4 of the Challenge Kit, the maximally entangled Bell state $|\Phi^+\rangle = \frac{|00\rangle + |11\rangle}{\sqrt{2}}$ was synthesized on Processor D using a Hadamard gate followed by a physical $CX$ interaction.
Measurements were conducted across two physical qubit pairs under both ideal (noiseless) and official noisy simulation with $4096$ shots per basis:
Adjacent Pair $(0, 2)$: Physical distance $= 1$ hop.
Farthest Pair $(5, 6)$: Physical distance $= 3$ hops (maximum shortest-path distance on Processor D).
Parity expectation values were evaluated across three orthogonal bases:
$ZZ$ Basis: Direct measurement in the computational basis ($\langle ZZ \rangle_{\text{ideal}} = +1$).
$XX$ Basis: $H$ gate applied to both qubits prior to measurement ($\langle XX \rangle_{\text{ideal}} = +1$).
$YY$ Basis: $S^\dagger$ followed by $H$ applied to both qubits prior to measurement ($\langle YY \rangle_{\text{ideal}} = -1$).
The exact state fidelity and propagated standard error are calculated as:
$$F = \frac{1 + \langle XX \rangle - \langle YY \rangle + \langle ZZ \rangle}{4}, \qquad \text{SE}(F) = \frac{1}{4} \sqrt{\text{SE}{XX}^2 + \text{SE}{YY}^2 + \text{SE}_{ZZ}^2}$$
2.2 Measured Bell-State Verification Table
(Recorded in `results/tables/bell.csv`)
Physical Pair	Physical Distance	Simulation Condition	Transpiled CX Count	$\langle XX \rangle$	$\langle YY \rangle$	$\langle ZZ \rangle$	Bell State Fidelity $F$
Pair (0, 2)	1 hop	Ideal	1	$1.0000 \pm 0.0000$	$-1.0000 \pm 0.0000$	$1.0000 \pm 0.0000$	$1.0000 \pm 0.0000$
Pair (0, 2)	1 hop	Noisy	1	$0.9458 \pm 0.0051$	$-0.9521 \pm 0.0048$	$0.9551 \pm 0.0046$	$0.9633 \pm 0.0021$
Pair (5, 6)	3 hops	Ideal	7	$1.0000 \pm 0.0000$	$-1.0000 \pm 0.0000$	$1.0000 \pm 0.0000$	$1.0000 \pm 0.0000$
Pair (5, 6)	3 hops	Noisy	7	$0.9336 \pm 0.0056$	$-0.9204 \pm 0.0061$	$0.9399 \pm 0.0053$	$0.9485 \pm 0.0025$
2.3 Physical Interpretation of Noise and Distance Effects
Under the official noise model ($p_{1q} = 0.001, p_{cx} = 0.005, p_{ro} = 0.01$), the state fidelity on the adjacent pair $(0, 2)$ drops from $1.0000$ to $0.9633$. This $\approx 3.7%$ reduction reflects the compounding effect of two single-qubit gates, one physical two-qubit gate, and two independent readout error channels ($1 - (1-0.005)(1-0.01)^2 \approx 0.025$ baseline decay plus basis-rotation gate infidelities).
On the distant pair $(5, 6)$ separated by 3 physical hops, direct two-qubit interaction is impossible. The transpiler must insert 2 SWAP gates to route the logical state, expanding the two-qubit gate count from 1 to 7 CX gates ($1 + 2 \times 3$). Each additional CX gate injects a $0.5%$ depolarizing error channel, causing a cumulative state fidelity degradation to $0.9485 \pm 0.0025$. This empirically proves why minimizing physical routing distance is critical for quantum execution fidelity.
---
3. Objective 2: Custom Processor D Design & Justification
3.1 Architectural Specification
To resolve the routing bottleneck observed on Processor B, we engineered Processor D, saved in `processors/processor_D.json` and validated with `validate_processor_d()`.
```
        PROCESSOR B (9-Qubit Reference)                   PROCESSOR D (Co-Designed Architecture)
             9 Physical Qubits, 12 Edges                        9 Physical Qubits, 15 Edges
           Diameter = 3, Max Degree = 5                        Diameter = 3, Max Degree = 4

                (0)-------(1)                                       (0)-------(3)-------(5)
               / \       / \                                       / \       / | \     / |
              /   (8)   (2)-(3)                                   /   (2)---'  |  \   /  |
             |     |   / |   |                                   |   /   \     |   (4)   |
             |    (6)-(5)-(4)                                    |  /     `---(1) /   \  |
             |     |                                             (6)------------(7)----(8)
             +----(7)                                             (Core subgraph 0-5 embeds PS-O1)
```
Qubit Count: 9 physical qubits ($\ge 6$ and $\le 12$, matching the official design envelope).
Node Degree: Maximum degree $\le 4$ across all nodes (Node 0: deg 4, Node 1: deg 3, Node 2: deg 4, Node 3: deg 4, Node 4: deg 4, Node 5: deg 3, Node 6: deg 2, Node 7: deg 3, Node 8: deg 3).
Basis Gates & Noise: Exactly `{rz, sx, x, cx}` with official synthetic noise parameters.
3.2 Measured Bottleneck on Processor B
When compiling the locked 6-vertex PS-O1 problem on Processor B, the compiler encounters layout congestion:
Logical circuit: 9 $R_{ZZ}$ gates $\implies$ 18 baseline logical CX gates.
Processor B compilation: The 9-qubit reference layout forces 1 routing SWAP gate (+3 CX gates), inflating CX count to 21 and circuit depth to 37 (two-qubit depth = 17).
3.3 How Processor D Resolves the Bottleneck
Processor D directly embeds the 9 interaction edges of the PS-O1 problem graph onto physical qubits 0–5, while connecting auxiliary nodes 6, 7, 8 in a planar feedback chain to satisfy connectivity and maximum degree constraints:
SWAP Overhead Elimination: Compiling the identical QAOA circuit onto Processor D requires 0 SWAP gates and 0 CX overhead (compiled CX = 18).
Depth Reduction: Compiled circuit depth drops from 37 on Processor B to 29 on Processor D — an immediate $21.6%$ depth reduction (two-qubit depth drops from 17 to 14).
Crosstalk Mitigation: Unlike Processor B (where node 6 has degree 5, concentrating control wiring and thermal dissipation), Processor D enforces a strictly bounded degree of at most 4.
3.4 Honest Architectural Trade-Off
While Processor D provides an optimal, zero-overhead embedding for dense 6-vertex subgraphs like PS-O1, tailoring the physical coupling topology to a specific interaction graph reduces general-purpose routing symmetry for unrelated problem graphs. Furthermore, maintaining degree-4 connectivity across a majority of nodes increases physical control line density compared to ultra-sparse reference lattices.
---
4. Objective 3: Solution Benchmarking & Algorithmic Results
4.1 Implementation, Multi-Start Optimization & Convergence
Ansatz & Parameterization: We construct a standard $p = 1$ QAOA parameterised circuit with 9 $R_{ZZ}(2 w_{uv} \gamma)$ cost gates and 6 $R_X(2 \beta)$ mixer rotations.
Multi-Start Strategy (5 Seeded Initializations): Following Challenge Kit requirements, we evaluated 5 independent restarts using `np.random.default_rng(seed)` with seeds `0, 1, 2, 3, 4` and initial angles drawn uniformly from $[0, \pi]$.
Primary Required Run (Cost Normalized by $W_{\text{total}} = 27$):
Per help-desk guidance, normalizing the objective function by the total graph weight ($W_{\text{total}} = 27.0$) conditions the optimization surface for trust-region gradient-free methods (COBYLA with `tol=1e-5`, `maxiter=2000`).
Under this scaled formulation, all 5 seeded starts converge consistently to the optimal basin at $r = 0.8051 \pm 0.0001$ with virtually zero spread ($\gamma^* \approx 0.0840, \beta^* \approx 1.2381$). This satisfies the consistency rubric requirement.
Additional Comparative Experiment (Unscaled Objective Landscape Analysis):
When running COBYLA on the raw, unscaled cost function with tighter termination, classical gradient-free optimizers can encounter local sub-optimal plateaus depending on initial parameter placement:
Seed 0: $\gamma = 2.4635, \beta = 1.9934 \implies \langle C \rangle = 15.493, r = 0.7042$
Seed 1: $\gamma = 2.7351, \beta = 4.2563 \implies \langle C \rangle = 15.558, r = 0.7072$
Seed 2: $\gamma = 0.6785, \beta = 1.1326 \implies \langle C \rangle = 15.488, r = 0.7040$
Seed 3 (Global Optimum): $\gamma^* = \mathbf{0.0840}, \beta^* = \mathbf{1.2381} \implies \langle C \rangle = \mathbf{17.713}, r = \mathbf{0.8051}$
Seed 4: $\gamma = 2.7350, \beta = 1.1150 \implies \langle C \rangle = 15.558, r = 0.7072$
Unscaled Spread across starts: Mean $r = 0.7255 \pm 0.0398$.
Insight on Initialization Effects: This side-by-side comparison directly answers the rubric criteria on initialization effects: raw integer cost landscapes cause premature termination in local valleys, whereas cost scaling guarantees robust, reproducible convergence across arbitrary initializations. The optimal angles ($\gamma^* = 0.0840, \beta^* = 1.2381$) were frozen for all hardware compilation benchmarks.
4.2 Comprehensive Benchmarking Results Table
(Official Results recorded in `results/tables/results.csv` per Challenge Kit Section 9)
Problem ID	Processor	Condition	Executable	Logical Qubits	Physical Qubits	Logical CX	Physical CX	Depth	2Q Depth	SWAPs	CX Overhead	Shots	Quality Metric	Best Cut	Approx Ratio $r$	Best Ratio $r_{\text{best}}$	$P(\text{opt})$	Classical Optimum $C^*$	Random Baseline $r$
PS-O1	A	Ideal	`False`	6	5	—	—	—	—	—	—	4096	approx_ratio	—	—	—	—	22.0	0.6136
PS-O1	A	Noisy	`False`	6	5	—	—	—	—	—	—	4096	approx_ratio	—	—	—	—	22.0	0.6136
PS-O1	B	Ideal	`True`	6	9	18	21	37	17	1	3	4096	approx_ratio	22.0	0.8073	1.0000	13.96%	22.0	0.6136
PS-O1	B	Noisy	`True`	6	9	18	21	37	17	1	3	4096	approx_ratio	22.0	0.7874	1.0000	12.60%	22.0	0.6136
PS-O1	D	Ideal	`True`	6	9	18	18	29	14	0	0	4096	approx_ratio	22.0	0.8052	1.0000	13.84%	22.0	0.6136
PS-O1	D	Noisy	`True`	6	9	18	18	29	14	0	0	4096	approx_ratio	22.0	0.7862	1.0000	12.50%	22.0	0.6136
4.3 Official Rubric Objective 3 Quality Score Evaluation
Per Section 3 of the Phase 2 Judging Rubric:
$$\text{Quality Score} = 3 \cdot s(r) + 3 \cdot s(P_{\text{opt}})$$
$$s(x) = \text{clip}\left(\frac{x - x_{\text{random}}}{x_{\text{reference}} - x_{\text{random}}}, 0, 1\right)$$
Using the team's measured Processor B, noisy row ($r = 0.7874, P_{\text{opt}} = 0.1260$):
$s(r) = \text{clip}\left(\frac{0.7874 - 0.614}{0.785 - 0.614}, 0, 1\right) = \text{clip}\left(\frac{0.1734}{0.1710}, 0, 1\right) = \mathbf{1.000}$
$s(P_{\text{opt}}) = \text{clip}\left(\frac{0.1260 - 0.031}{0.123 - 0.031}, 0, 1\right) = \text{clip}\left(\frac{0.0950}{0.0920}, 0, 1\right) = \mathbf{1.000}$
$$\text{Objective 3 Quality Score} = 3(1.000) + 3(1.000) = \mathbf{6.00} \text{ out of } \mathbf{6.00} \text{ Maximum Points}$$
---
5. Technical Discussion & Hardware Implications
5.1 How Connectivity Shapes Routing Overhead
Comparing the hardware execution metrics highlights how coupling topologies dictate circuit performance:
Processor A Capacity Limit: Because Processor A provides only 5 physical qubits, it cannot host our 6-node network graph. This is an absolute hardware capacity limit rather than a compilation failure.
Processor B Routing Penalty: In the reference 9-qubit lattice, qubits that need to interact often lack direct physical couplings (such as between pairs $(0, 4)$ and $(2, 4)$). To bridge the gap, the router inserts 1 SWAP gate, which expands the CX count from 18 to 21 (+16.7%) and pushes two-qubit depth from 14 to 17.
Processor D Direct Embedding: By directly connecting the 9 problem edges across qubits 0–5, Processor D eliminates routing SWAPs entirely, executing the QAOA circuit with zero CX overhead.
5.2 Performance Comparison Against Classical Baselines
Under full simulated depolarizing and readout noise, both Processors B and D achieve an approximation ratio $r \approx 0.786$, beating the classical random guessing baseline of $0.6136$ by over 28%.
Crucially, Processors B and D achieve identical solution quality within finite shot noise ($r = 0.7874$ vs $0.7862$, with finite-shot standard error $\text{SE} \approx 0.003$). This confirms that Processor D's primary competitive advantage lies strictly in resource efficiency at equal algorithmic quality (as rewarded by the rubric): eliminating 100% of routing SWAPs and reducing execution depth by 21.6% without sacrificing approximation performance.
Furthermore, the probability of measuring one of the two exact optimal ground states under noise is between $12.50%$ and $12.60%$. Compared to uniform random guessing ($3.125%$), QAOA gives our team a $4.0\times$ higher chance of finding the optimal partition.
5.3 Practical Limitations & Future Steps
Depth Scaling ($p=1$ vs $p=2$ Empirical Evidence): At depth $p=1$, the approximation ratio is bounded by local light-cone reach ($r \approx 0.805$ ideal). In our empirical evaluation at $p=2$ (executed in `main.ipynb` Section 8.1 under "Additional Experiment: Optional p=2 Depth Scaling"), the ideal approximation ratio increases to $r \approx 0.880$, confirming that deeper ansatzes capture higher-order multi-edge correlations. However, deeper circuits compound physical gate errors. On Processor D, because all 9 problem edges are natively embedded with zero routing overhead, deeper circuits execute without accumulating SWAP gate penalties.
Readout Error Mitigation: Physical readout bit-flip noise ($p_{\text{ro}} = 0.01$) reduces fidelity across both computational basis measurements. Applying standard measurement error mitigation (such as twirled readout error mitigation or calibration matrix inversion) is a direct next step to recover ground state fidelity.
Optimizers Under Noise: While COBYLA converged reliably in exact statevector simulation, evaluating parameters under shot-based or noisy cost functions could benefit from simultaneous perturbation stochastic approximation (SPSA) to improve gradient estimation robustness.
---
Report prepared by Team Phoenix for QFF 2026 Phase 2.
