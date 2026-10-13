# Qiskit Fall Fest 2026 — Phase 1: PS-O1
## Weighted Max-Cut: QAOA Circuit Construction and SWAP Bottleneck Analysis

**Team:** Phoenix (6 Members)  
**Track 2:** Quantum Optimization (QAOA / QUBO)  
**Problem Statement:** PS-O1 (Max-Cut on Weighted Graphs)  
**Institution:** SRM University-AP

---

## 1. Project Overview & Objectives

This repository contains our team's code and analysis for **Phase 1 (PS-O1)** of the Qiskit Fall Fest 2026 hackathon. 

Our work focuses on implementing the Quantum Approximate Optimization Algorithm (QAOA) to solve the weighted Max-Cut problem, with a specific emphasis on how hardware topology impacts circuit compilation. 

### Key Milestones:
* **Hamiltonian Mapping:** Formulated the weighted Max-Cut problem into an Ising spin glass cost Hamiltonian: \(\hat{C} = \sum_{(u,v)} w_{uv} \frac{I - Z_u Z_v}{2}\).
* **Classical Baseline:** Developed an exhaustive brute-force solver to determine the exact classical optimum for performance benchmarking.
* **Ansatz Implementation:** Built and executed parameterized QAOA circuits for depths p=1 and p=2.
* **Variational Optimization:** Utilized the classical gradient-free COBYLA optimizer to find optimal parameters \((\boldsymbol{\gamma}, \boldsymbol{\beta})\).
* **Hardware-Aware Compilation:** Transpiled logical QAOA circuits onto two physical target architectures to benchmark hardware constraints:
  * **Processor A (Linear Chain):** A 5-qubit architecture baseline `[(0,1), (1,2), (2,3), (3,4)]`.
  * **Processor B (Heavy-Hex):** A 9-qubit sparse configuration featuring 12 physical edges.
* **Overhead Analysis:** Profiled performance metrics across both processors, tracking CNOT (CX) counts, circuit depth, and SWAP-routing penalties.

---

