"""Graph, coupling map, and performance visualization module (Member 5).

Generates high-resolution PNG figures matching organizer requirements:
1. Processor coupling topologies (Processor A 5q tree vs Processor B 9q heavy-hex)
2. Compilation overhead comparison (Depth and CX counts across p=1, p=2)
3. QAOA energy convergence optimization curves (p=1 vs p=2)
4. SWAP routing overhead breakdown
5. Sampled cut weight probability distribution histograms
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

from src.processors import get_undirected_edges, load_processor


def plot_architecture_topologies(
    output_path: str | Path = "results/figures/architecture_topologies_comparison.png",
) -> None:
    """Plot Processor A and Processor B coupling maps side-by-side."""
    cfg_a = load_processor("processor_A")
    cfg_b = load_processor("processor_B")

    edges_a = get_undirected_edges(cfg_a)
    edges_b = get_undirected_edges(cfg_b)

    ga = nx.Graph()
    ga.add_nodes_from(range(cfg_a["num_qubits"]))
    ga.add_edges_from(edges_a)

    gb = nx.Graph()
    gb.add_nodes_from(range(cfg_b["num_qubits"]))
    gb.add_edges_from(edges_b)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Processor A layout: T-branching tree with hub at 0
    pos_a = {
        0: (0.0, 0.0),    # Central hub
        1: (-1.0, 0.0),   # Left branch
        2: (0.0, 1.0),    # Top branch
        3: (1.0, 0.0),    # Right branch
        4: (2.0, 0.0),    # Leaf attached to 3
    }
    nx.draw_networkx_nodes(ga, pos_a, ax=ax1, node_color="#4C72B0", node_size=800)
    nx.draw_networkx_labels(ga, pos_a, ax=ax1, font_color="white", font_weight="bold", font_size=12)
    nx.draw_networkx_edges(ga, pos_a, ax=ax1, width=2.5, edge_color="#2C3E50")
    ax1.set_title("Processor A (5 Qubits)\nT-Shaped Branching Tree Reference\nCapacity Limit: ≤ 5 Qubits", fontsize=12, fontweight="bold", pad=12)
    ax1.axis("off")

    # Processor B layout: 9-qubit heavy-hex
    pos_b = {
        0: (0.0, 2.0),
        1: (1.0, 2.0),
        2: (2.0, 1.5),
        3: (2.5, 0.5),
        4: (2.0, -0.5),
        5: (1.0, -0.5),
        6: (0.0, 0.0),
        7: (-1.0, 0.0),
        8: (-0.5, 1.2),
    }
    nx.draw_networkx_nodes(gb, pos_b, ax=ax2, node_color="#2CA02C", node_size=800)
    nx.draw_networkx_labels(gb, pos_b, ax=ax2, font_color="white", font_weight="bold", font_size=12)
    nx.draw_networkx_edges(gb, pos_b, ax=ax2, width=2.5, edge_color="#1B4F72")
    ax2.set_title("Processor B (9 Qubits)\nHeavy-Hex Sparse Coupling (12 Edges)\nAccommodates 6-Qubit Benchmarks", fontsize=12, fontweight="bold", pad=12)
    ax2.axis("off")

    plt.tight_layout()
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_circuit_depth_and_cx(
    output_path: str | Path = "results/figures/circuit_depth_cx_comparison.png",
) -> None:
    """Plot logical vs compiled circuit depth and CX count for Processor B."""
    labels = ["Depth (p=1)", "Depth (p=2)", "CX Count (p=1)", "CX Count (p=2)"]
    logical = [10, 17, 18, 36]
    compiled_b = [38, 69, 21, 42]

    x = np.arange(len(labels))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 6))
    bars1 = ax.bar(x - width / 2, logical, width, label="Logical (Ideal Baseline)", color="#4C72B0")
    bars2 = ax.bar(x + width / 2, compiled_b, width, label="Processor B (Compiled)", color="#D95F02")

    ax.set_ylabel("Count / Depth", fontsize=12, fontweight="bold")
    ax.set_title("Circuit Depth & CX Gate Scaling on Processor B\n(Official 6-Node ER6 Benchmark)", fontsize=13, fontweight="bold", pad=12)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=11, fontweight="medium")
    ax.legend(fontsize=11)
    ax.grid(axis="y", linestyle="--", alpha=0.6)

    # Value labels
    for bar in bars1:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, yval + 1, f"{int(yval)}", ha="center", va="bottom", fontsize=10)
    for bar in bars2:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, yval + 1, f"{int(yval)}", ha="center", va="bottom", fontsize=10, fontweight="bold")

    plt.tight_layout()
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_energy_convergence(
    traces_p1: Sequence[float] | None = None,
    traces_p2: Sequence[float] | None = None,
    exact_optimum: float = 16.0,
    output_path: str | Path = "results/figures/energy_convergence_curves.png",
) -> None:
    """Plot QAOA expected cut optimization curves for p=1 and p=2."""
    fig, ax = plt.subplots(figsize=(10, 6))

    if traces_p1 is not None and len(traces_p1) > 0:
        ax.plot(range(len(traces_p1)), traces_p1, label=f"QAOA p=1 (Final: {traces_p1[-1]:.2f})", color="#4C72B0", lw=2.2)
    if traces_p2 is not None and len(traces_p2) > 0:
        ax.plot(range(len(traces_p2)), traces_p2, label=f"QAOA p=2 (Final: {traces_p2[-1]:.2f})", color="#2CA02C", lw=2.2)

    ax.axhline(exact_optimum, color="#D95F02", linestyle="--", lw=2.0, label=f"Exact Classical Optimum ({exact_optimum:.1f})")

    ax.set_xlabel("Optimizer Function Evaluations", fontsize=12, fontweight="bold")
    ax.set_ylabel("Expected Cut Value ⟨C⟩", fontsize=12, fontweight="bold")
    ax.set_title("QAOA Energy Convergence Curves (COBYLA Optimization)\nOfficial 6-Node ER6 Graph", fontsize=13, fontweight="bold", pad=12)
    ax.legend(fontsize=11, loc="lower right")
    ax.grid(True, linestyle="--", alpha=0.6)

    plt.tight_layout()
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_swap_overhead(
    output_path: str | Path = "results/figures/swap_routing_overhead.png",
) -> None:
    """Plot SWAP routing overhead breakdown for Processor B."""
    categories = ["p = 1 Depth", "p = 2 Depth"]
    baseline_cx = [18, 36]
    overhead_cx = [3, 6]
    estimated_swaps = [1.0, 2.0]

    x = np.arange(len(categories))
    width = 0.45

    fig, ax = plt.subplots(figsize=(8, 6))
    p1 = ax.bar(x, baseline_cx, width, label="Baseline Unrouted CX (2 × RZZ)", color="#4C72B0")
    p2 = ax.bar(x, overhead_cx, width, bottom=baseline_cx, label="Routing Overhead CX (3 × SWAP)", color="#E74C3C")

    ax.set_ylabel("Two-Qubit (CX) Gates", fontsize=12, fontweight="bold")
    ax.set_title("SWAP Routing Bottleneck & CX Gate Breakdown\nProcessor B (9-Qubit Heavy-Hex)", fontsize=13, fontweight="bold", pad=12)
    ax.set_xticks(x)
    ax.set_xticklabels(categories, fontsize=12, fontweight="medium")
    ax.legend(fontsize=11)
    ax.grid(axis="y", linestyle="--", alpha=0.6)

    for i in range(len(categories)):
        total = baseline_cx[i] + overhead_cx[i]
        swaps = estimated_swaps[i]
        ax.text(x[i], total + 1, f"Total CX: {total}\n({swaps:.0f} SWAP)", ha="center", va="bottom", fontsize=10, fontweight="bold")

    plt.tight_layout()
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_cut_distribution(
    dist_p1: Mapping[float, int] | None = None,
    dist_p2: Mapping[float, int] | None = None,
    exact_optimum: float = 16.0,
    output_path: str | Path = "results/figures/cut_distribution_histogram.png",
) -> None:
    """Plot sampled cut weight probability distributions for p=1 and p=2."""
    fig, ax = plt.subplots(figsize=(10, 6))

    all_cuts = sorted(set(
        (list(dist_p1.keys()) if dist_p1 else []) + (list(dist_p2.keys()) if dist_p2 else [])
    ))

    if not all_cuts:
        all_cuts = [6.0, 8.0, 10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0]

    x = np.arange(len(all_cuts))
    width = 0.38

    if dist_p1:
        total1 = sum(dist_p1.values())
        probs1 = [dist_p1.get(c, 0) / total1 for c in all_cuts]
        ax.bar(x - width / 2, probs1, width, label="QAOA p=1 (4096 Shots)", color="#4C72B0", alpha=0.85)

    if dist_p2:
        total2 = sum(dist_p2.values())
        probs2 = [dist_p2.get(c, 0) / total2 for c in all_cuts]
        ax.bar(x + width / 2, probs2, width, label="QAOA p=2 (4096 Shots)", color="#2CA02C", alpha=0.85)

    ax.set_xlabel("Cut Value", fontsize=12, fontweight="bold")
    ax.set_ylabel("Sampling Probability", fontsize=12, fontweight="bold")
    ax.set_title("Sampled Cut Weight Probability Distribution\nComparing QAOA Depth p=1 vs p=2", fontsize=13, fontweight="bold", pad=12)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{c:.0f}" for c in all_cuts], fontsize=11)

    # Highlight exact optimum
    if exact_optimum in all_cuts:
        idx_opt = all_cuts.index(exact_optimum)
        ax.axvline(idx_opt, color="#D95F02", linestyle="--", lw=2, label=f"Exact Optimum ({exact_optimum:.0f})")

    ax.legend(fontsize=11)
    ax.grid(axis="y", linestyle="--", alpha=0.6)

    plt.tight_layout()
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def generate_all_figures(output_dir: str | Path = "results/figures") -> None:
    """Generate and save all publication-grade comparison figures."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    plot_architecture_topologies(out / "architecture_topologies_comparison.png")
    plot_circuit_depth_and_cx(out / "circuit_depth_cx_comparison.png")
    plot_swap_overhead(out / "swap_routing_overhead.png")
