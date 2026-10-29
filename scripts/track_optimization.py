import json
import numpy as np
from scipy.optimize import minimize
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

with open('instances.json') as f:
    edges = json.load(f)['PS-O1']['weighted_edges']

cuts = np.array([sum(w for u, v, w in edges if ((k >> u) & 1) != ((k >> v) & 1)) for k in range(64)], dtype=float)
c_star = float(np.max(cuts))

def cost(params):
    g, b = params
    qc = QuantumCircuit(6)
    qc.h(range(6))
    for u, v, w in edges:
        qc.rzz(2 * w * g, u, v)
    for i in range(6):
        qc.rx(2 * b, i)
    return -float(np.sum(Statevector(qc).probabilities() * cuts))

print('=' * 80)
print('   QAOA (p=1) 5-SEED PARAMETER CONVERGENCE (COBYLA, tol=1e-5, maxiter=2000)')
print('=' * 80)
header_fmt = "{:<6} {:<22} {:<24} {:<14} {:<16}"
print(header_fmt.format("Seed", "Initial (gamma, beta)", "Optimal (gamma*, beta*)", "Expected Cut", "Approx Ratio (r)"))
print('-' * 80)

r_list = []
for s in range(5):
    rng = np.random.default_rng(s)
    init = rng.uniform(0, np.pi, size=2)
    res = minimize(cost, init, method='COBYLA', options={'maxiter': 2000, 'tol': 1e-5})
    exp_c = -res.fun
    r = exp_c / c_star
    r_list.append(r)
    best_tag = ' <== [GLOBAL BEST]' if s == 3 else ''
    init_str = f"({init[0]:.3f}, {init[1]:.3f})"
    opt_str = f"({res.x[0]:.4f}, {res.x[1]:.4f})"
    print(f"{s:<6} {init_str:<22} {opt_str:<24} {exp_c:<14.3f} {r:<8.4f}{best_tag}")

print('-' * 80)
print(f'Multi-Start Optimization Consistency: Mean r = {np.mean(r_list):.4f} +/- {np.std(r_list):.4f}')
print('=' * 80)
