"""Weighted Max-Cut problem definition (Member 3).

This module is pure classical code: it has no Qiskit dependency and knows nothing
about processor topology. It provides

* :class:`WeightedGraph` -- a validated, immutable, undirected weighted graph,
* the weighted cut objective ``C(x) = sum_{(u,v) in E} w_uv * [x_u != x_v]``,
* bitstring <-> assignment conversion with an explicit, documented bit order,
* an exact brute-force reference for small graphs.

Conventions
-----------
* Vertices are the integers ``0 .. n-1``. This index is the canonical vertex order
  used everywhere (objective, QAOA qubit index, classical bit index).
* An *assignment* is a tuple ``x`` of length ``n`` with ``x[i] in {0, 1}`` giving
  the side of the partition that vertex ``i`` belongs to.
* Edges are stored canonically as ``(u, v, w)`` with ``u < v``, sorted by
  ``(u, v)``. Self-loops and duplicate edges (including reversed duplicates such
  as ``(0, 1)`` and ``(1, 0)``) are rejected so no edge is ever double-counted.
* Weights must be finite and non-negative (the standard weighted Max-Cut setting).

Bitstring order
---------------
Two string orders exist and conversion functions always require the caller to
name one explicitly:

* ``"qiskit"`` (little-endian): the *rightmost* character is vertex 0. This is
  how Qiskit displays measurement counts when qubit ``i`` is measured into
  classical bit ``i``. Example, n=4: ``"0011"`` means x0=1, x1=1, x2=0, x3=0.
* ``"vertex"`` (big-endian, human reading order): the *leftmost* character is
  vertex 0. Example, n=4: ``"0011"`` means x0=0, x1=0, x2=1, x3=1.

PROVENANCE: the PS-O1 Challenge Kit requires a fixed six-vertex weighted
benchmark graph but does not prescribe one. The team's final, team-selected
benchmark is G6 (``load_graph()``, ``data/weighted_maxcut_g6.json``). The graphs
returned by the ``synthetic_*`` functions below are SYNTHETIC development/test
instances only and must not be reported as the benchmark.
"""

from __future__ import annotations

import json
import math
import time
from collections.abc import Mapping, Sequence as SequenceABC
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Literal, Sequence

import numpy as np
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit.circuit import ParameterVector
from qiskit.primitives import StatevectorSampler
from qiskit.quantum_info import SparsePauliOp, Statevector
from scipy.optimize import minimize

BitOrder = Literal["qiskit", "vertex"]

#: Default safety cap for exhaustive search (2**20 ~ 1e6 assignments).
DEFAULT_MAX_EXACT_NODES = 20

#: Absolute tolerance used when comparing floating-point cut values.
CUT_ATOL = 1e-9

#: G6: the team's final, team-selected benchmark (6 vertices, 9 edges, integer weights 1..5).
#: Not organizer-provided (the kit leaves the choice of graph to teams); see the file's "status" field.
DEFAULT_GRAPH_PATH = Path(__file__).resolve().parents[1] / "data" / "raw" / "erdos_renyi_6.json"


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WeightedGraph:
    """Validated undirected weighted graph on vertices ``0 .. num_nodes-1``.

    Build instances with :meth:`from_edges`, :meth:`from_networkx`,
    :meth:`from_dict` or :meth:`from_json` rather than the raw constructor, so
    edges are canonicalised and validated.

    Attributes:
        num_nodes: Number of vertices ``n``.
        edges: Canonical edges ``((u, v, w), ...)`` with ``u < v``, sorted.
        name: Free-text identifier, recorded in results.
        source: Provenance label, e.g. ``"synthetic"`` or ``"official"``.
        labels: Original vertex labels (``labels[i]`` is the label of vertex ``i``).
    """

    num_nodes: int
    edges: tuple[tuple[int, int, float], ...]
    name: str = "unnamed"
    source: str = "unspecified"
    labels: tuple[Any, ...] = field(default=())

    def __post_init__(self) -> None:
        if isinstance(self.num_nodes, bool) or not isinstance(self.num_nodes, (int, np.integer)):
            raise TypeError(f"num_nodes must be an int, got {type(self.num_nodes).__name__}")
        if self.num_nodes < 1:
            raise ValueError(f"num_nodes must be >= 1, got {self.num_nodes}")
        object.__setattr__(self, "num_nodes", int(self.num_nodes))
        object.__setattr__(self, "edges", _canonical_edges(self.edges, self.num_nodes))
        if not self.labels:
            object.__setattr__(self, "labels", tuple(range(self.num_nodes)))
        elif len(self.labels) != self.num_nodes:
            raise ValueError(
                f"labels has length {len(self.labels)}, expected num_nodes={self.num_nodes}"
            )
        else:
            object.__setattr__(self, "labels", tuple(self.labels))

    # -- constructors -------------------------------------------------------

    @classmethod
    def from_edges(
        cls,
        num_nodes: int,
        edges: Iterable[Sequence[Any]],
        *,
        name: str = "unnamed",
        source: str = "unspecified",
    ) -> "WeightedGraph":
        """Create a graph from ``(u, v)`` or ``(u, v, w)`` tuples (missing weight = 1.0)."""
        return cls(num_nodes=num_nodes, edges=tuple(edges), name=name, source=source)

    @classmethod
    def from_networkx(
        cls, graph: Any, *, weight: str = "weight", name: str | None = None, source: str = "unspecified"
    ) -> "WeightedGraph":
        """Create a graph from an undirected ``networkx.Graph``.

        Node labels are sorted (falling back to ``str`` ordering for mixed types)
        and mapped to ``0 .. n-1``; the original labels are kept in ``labels``.
        Edges without a ``weight`` attribute get weight 1.0.
        """
        if graph.is_directed():
            raise ValueError("Max-Cut requires an undirected graph")
        if graph.is_multigraph():
            raise ValueError("multigraphs are not supported; merge parallel edges first")
        nodes = list(graph.nodes)
        try:
            nodes = sorted(nodes)
        except TypeError:
            nodes = sorted(nodes, key=str)
        index = {node: i for i, node in enumerate(nodes)}
        edges = [(index[u], index[v], data.get(weight, 1.0)) for u, v, data in graph.edges(data=True)]
        return cls(
            num_nodes=len(nodes),
            edges=tuple(edges),
            name=name if name is not None else str(graph.graph.get("name", "networkx")),
            source=source,
            labels=tuple(nodes),
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WeightedGraph":
        """Inverse of :meth:`to_dict`.

        Expected keys: ``num_nodes`` and ``edges`` (list of ``[u, v]`` or
        ``[u, v, w]``); optional ``name``, ``source``, ``labels``.
        """
        if "num_nodes" not in data or "edges" not in data:
            raise ValueError("graph dict must contain 'num_nodes' and 'edges'")
        return cls(
            num_nodes=data["num_nodes"],
            edges=tuple(tuple(e) for e in data["edges"]),
            name=data.get("name", "unnamed"),
            source=data.get("source", "unspecified"),
            labels=tuple(data.get("labels", ())),
        )

    @classmethod
    def from_json(cls, path: str | Path) -> "WeightedGraph":
        """Load a graph saved in the :meth:`to_dict` format."""
        with open(path, encoding="utf-8") as fh:
            return cls.from_dict(json.load(fh))

    # -- serialisation ------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """JSON-serialisable representation."""
        return {
            "name": self.name,
            "source": self.source,
            "num_nodes": self.num_nodes,
            "edges": [[u, v, w] for u, v, w in self.edges],
            "labels": [_jsonable(label) for label in self.labels],
        }

    def to_json(self, path: str | Path) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=2)

    def to_networkx(self) -> Any:
        import networkx as nx

        g = nx.Graph(name=self.name)
        g.add_nodes_from(range(self.num_nodes))
        g.add_weighted_edges_from(self.edges)
        return g

    # -- convenience --------------------------------------------------------

    @property
    def num_edges(self) -> int:
        return len(self.edges)

    @property
    def total_weight(self) -> float:
        """Sum of all edge weights (an upper bound on any cut)."""
        return float(sum(w for _, _, w in self.edges))

    def weight(self, u: int, v: int) -> float:
        """Weight of edge ``{u, v}``; raises ``KeyError`` if absent."""
        a, b = (u, v) if u < v else (v, u)
        for x, y, w in self.edges:
            if (x, y) == (a, b):
                return w
        raise KeyError(f"no edge between {u} and {v}")


def _jsonable(value: Any) -> Any:
    return value if isinstance(value, (int, float, str, bool)) or value is None else str(value)


def _canonical_edges(edges: Iterable[Sequence[Any]], num_nodes: int) -> tuple[tuple[int, int, float], ...]:
    seen: dict[tuple[int, int], Sequence[Any]] = {}
    out: list[tuple[int, int, float]] = []
    for raw in edges:
        if isinstance(raw, (str, bytes)) or not hasattr(raw, "__len__") or len(raw) not in (2, 3):
            raise ValueError(f"edge must be (u, v) or (u, v, w), got {raw!r}")
        u, v = _vertex(raw[0], num_nodes), _vertex(raw[1], num_nodes)
        w = _weight(raw[2] if len(raw) == 3 else 1.0, (u, v))
        if u == v:
            raise ValueError(f"self-loop on vertex {u} is not allowed in Max-Cut")
        key = (min(u, v), max(u, v))
        if key in seen:
            raise ValueError(
                f"duplicate undirected edge {key}: {seen[key]!r} and {raw!r} "
                "(merge parallel edges before constructing the graph)"
            )
        seen[key] = raw
        out.append((key[0], key[1], w))
    out.sort(key=lambda e: (e[0], e[1]))
    return tuple(out)


def _vertex(value: Any, num_nodes: int) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise TypeError(f"vertex must be an int, got {value!r}")
    if not 0 <= value < num_nodes:
        raise ValueError(f"vertex {value} out of range for num_nodes={num_nodes}")
    return int(value)


def _weight(value: Any, edge: tuple[int, int]) -> float:
    if isinstance(value, bool):
        raise TypeError(f"weight of edge {edge} must be a number, got bool")
    try:
        w = float(value)
    except (TypeError, ValueError):
        raise TypeError(f"weight of edge {edge} must be a number, got {value!r}") from None
    if not math.isfinite(w):
        raise ValueError(f"weight of edge {edge} must be finite, got {w}")
    if w < 0:
        raise ValueError(f"weight of edge {edge} must be non-negative, got {w}")
    return w


# ---------------------------------------------------------------------------
# Strict loader for the team graph schema (data/weighted_maxcut_g6.json)
# ---------------------------------------------------------------------------

_G6_REQUIRED = ("num_vertices", "vertices", "edges")
_G6_EDGE_KEYS = frozenset({"u", "v", "weight"})


def _is_int(x: Any) -> bool:
    """True for genuine integers; ``bool`` is excluded even though it subclasses ``int``."""
    return isinstance(x, int) and not isinstance(x, bool)


def parse_graph_dict(data: Any) -> WeightedGraph:
    """Strictly validate a graph in the team JSON schema and return a :class:`WeightedGraph`.

    Schema (as in ``data/weighted_maxcut_g6.json``)::

        {"num_vertices": int >= 1,
         "vertices": [0, 1, ..., num_vertices-1],          # exactly, in order
         "edges": [{"u": int, "v": int, "weight": int}, ...],  # non-empty
         "weight_range": [lo, hi],                          # optional, ints, 1 <= lo <= hi
         "benchmark_id": str, ...}                          # optional; other keys ignored

    Edge rules: endpoints are ints (not bool) in ``0..num_vertices-1``; no
    self-loops; no duplicate or reversed-duplicate edges; each record has exactly
    the keys ``u``, ``v``, ``weight``. Weights are ints (not bool, not float)
    ``>= 1``, and within ``weight_range`` when it is given.

    Raises ``TypeError`` for wrong types and ``ValueError`` for missing fields or
    invalid values; messages name the offending field or edge index. Nothing is
    repaired or defaulted.
    """
    if not isinstance(data, Mapping):
        raise TypeError(f"graph data must be a JSON object, got {type(data).__name__}")
    missing = [k for k in _G6_REQUIRED if k not in data]
    if missing:
        raise ValueError(f"graph data is missing required field(s): {missing}")

    n = data["num_vertices"]
    if not _is_int(n):
        raise TypeError(f"'num_vertices' must be an int, got {type(n).__name__} {n!r}")
    if n < 1:
        raise ValueError(f"'num_vertices' must be >= 1, got {n}")

    vertices = data["vertices"]
    if not isinstance(vertices, list):
        raise TypeError(f"'vertices' must be a list, got {type(vertices).__name__}")
    for i, x in enumerate(vertices):
        if not _is_int(x):
            raise TypeError(f"'vertices'[{i}] must be an int, got {type(x).__name__} {x!r}")
    if len(vertices) != n:
        raise ValueError(f"'vertices' has {len(vertices)} entries but 'num_vertices' is {n}")
    if vertices != list(range(n)):
        raise ValueError(f"'vertices' must be exactly [0, ..., {n - 1}] in order, got {vertices}")

    lo, hi = 1, None
    if "weight_range" in data:
        wr = data["weight_range"]
        if not (isinstance(wr, list) and len(wr) == 2 and all(_is_int(x) for x in wr)):
            raise TypeError(f"'weight_range' must be a list of two ints, got {wr!r}")
        if not 1 <= wr[0] <= wr[1]:
            raise ValueError(f"'weight_range' must satisfy 1 <= lo <= hi, got {wr}")
        lo, hi = wr

    edges = data["edges"]
    if not isinstance(edges, list):
        raise TypeError(f"'edges' must be a list, got {type(edges).__name__}")
    if not edges:
        raise ValueError("'edges' must not be empty")
    seen: dict[tuple[int, int], int] = {}
    parsed = []
    for i, e in enumerate(edges):
        where = f"edges[{i}]"
        if not isinstance(e, Mapping):
            raise TypeError(f"{where} must be an object with keys u, v, weight; got {e!r}")
        if set(e) != _G6_EDGE_KEYS:
            raise ValueError(
                f"{where} must have exactly the keys ['u', 'v', 'weight']; "
                f"missing {sorted(_G6_EDGE_KEYS - set(e))}, unexpected {sorted(set(e) - _G6_EDGE_KEYS)}"
            )
        u, v, w = e["u"], e["v"], e["weight"]
        for key, x in (("u", u), ("v", v)):
            if not _is_int(x):
                raise TypeError(f"{where}.{key} must be an int vertex, got {type(x).__name__} {x!r}")
            if not 0 <= x < n:
                raise ValueError(f"{where}.{key}={x} is out of range 0..{n - 1}")
        if u == v:
            raise ValueError(f"{where} is a self-loop on vertex {u}")
        key = (min(u, v), max(u, v))
        if key in seen:
            raise ValueError(f"{where} {key} duplicates edges[{seen[key]}] (undirected)")
        seen[key] = i
        if not _is_int(w):
            raise TypeError(f"{where}.weight must be an int, got {type(w).__name__} {w!r}")
        if w < lo or (hi is not None and w > hi):
            rng = f"[{lo}, {hi}]" if hi is not None else f">= {lo}"
            raise ValueError(f"{where}.weight={w} is outside the allowed range {rng}")
        parsed.append((u, v, float(w)))

    name = data.get("benchmark_id", "unnamed")
    if not isinstance(name, str):
        raise TypeError(f"'benchmark_id' must be a string, got {type(name).__name__}")
    status = data.get("status", "unspecified")
    return WeightedGraph(num_nodes=n, edges=tuple(parsed), name=name,
                         source=status if isinstance(status, str) else "unspecified")


def load_graph(path: str | Path = DEFAULT_GRAPH_PATH) -> WeightedGraph:
    """Load and strictly validate a graph file in the team schema (default: G6).

    See :func:`parse_graph_dict` for the rules. Invalid JSON raises ``ValueError``
    naming the file; a missing file raises ``FileNotFoundError``.
    """
    path = Path(path)
    with open(path, encoding="utf-8") as fh:
        try:
            data = json.load(fh)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}: invalid JSON: {exc}") from exc
    return parse_graph_dict(data)


# ---------------------------------------------------------------------------
# Assignments and bitstrings
# ---------------------------------------------------------------------------


def validate_assignment(graph: WeightedGraph, assignment: Sequence[Any]) -> tuple[int, ...]:
    """Return ``assignment`` as a tuple of 0/1 ints, or raise a descriptive error.

    Accepted containers: ``list``, ``tuple`` (any ordered ``Sequence``) or a 1-D
    numpy integer array, indexed by vertex. Rejected with ``TypeError``: strings
    and bytes (use :func:`bitstring_to_assignment` so the bit order is explicit),
    unordered or non-sequence inputs (``set``, ``dict``, generators, scalars),
    and entries that are not integers -- including ``bool``/``numpy.bool_``
    (``True`` is an ``int`` subclass but is not accepted as a bit) and floats
    such as ``1.0``. Rejected with ``ValueError``: wrong length (including an
    empty assignment), multi-dimensional arrays, and integers other than 0/1.
    """
    values = _assignment_values(assignment)
    if len(values) != graph.num_nodes:
        raise ValueError(f"assignment has length {len(values)}, expected {graph.num_nodes}")
    return _check_bits(values)


def _assignment_values(assignment: Any) -> tuple[Any, ...]:
    """Container checks shared by every assignment-consuming function."""
    if isinstance(assignment, (str, bytes, bytearray)):
        raise TypeError(
            "assignment must be a sequence of 0/1 ints; convert strings with "
            "bitstring_to_assignment(..., order=...) so the bit order is explicit"
        )
    if isinstance(assignment, np.ndarray):
        if assignment.ndim != 1:
            raise ValueError(f"assignment array must be 1-D, got shape {assignment.shape}")
        return tuple(assignment.tolist())  # numpy scalars -> Python int/float/bool
    if isinstance(assignment, SequenceABC):
        return tuple(assignment)
    raise TypeError(
        f"assignment must be an ordered sequence (list, tuple or 1-D numpy array), "
        f"got {type(assignment).__name__}"
    )


def _check_bits(values: tuple[Any, ...]) -> tuple[int, ...]:
    """Entry checks shared by every assignment-consuming function."""
    out = []
    for i, b in enumerate(values):
        if isinstance(b, (bool, np.bool_)) or not isinstance(b, (int, np.integer)):
            raise TypeError(f"assignment[{i}] must be the int 0 or 1, got {type(b).__name__} {b!r}")
        if b not in (0, 1):
            raise ValueError(f"assignment[{i}] must be 0 or 1, got {b!r}")
        out.append(int(b))
    return tuple(out)


def _bits_any_length(assignment: Any) -> tuple[int, ...]:
    """Validated non-empty 0/1 tuple, for helpers that have no graph to check length against."""
    values = _assignment_values(assignment)
    if not values:
        raise ValueError("assignment must not be empty")
    return _check_bits(values)


def _check_num_nodes(num_nodes: Any) -> int:
    if isinstance(num_nodes, bool) or not isinstance(num_nodes, (int, np.integer)):
        raise TypeError(f"num_nodes must be an int, got {type(num_nodes).__name__} {num_nodes!r}")
    if num_nodes < 1:
        raise ValueError(f"num_nodes must be >= 1, got {num_nodes}")
    return int(num_nodes)


def bitstring_to_assignment(bitstring: str, num_nodes: int, *, order: BitOrder) -> tuple[int, ...]:
    """Convert a bitstring into an assignment indexed by vertex.

    Args:
        bitstring: String of ``'0'``/``'1'`` of length ``num_nodes``.
        num_nodes: Expected number of vertices.
        order: ``"qiskit"`` (rightmost char = vertex 0) or ``"vertex"``
            (leftmost char = vertex 0). Required, to prevent silent reversals.
    """
    num_nodes = _check_num_nodes(num_nodes)
    if not isinstance(bitstring, str):
        raise TypeError(f"bitstring must be a str, got {type(bitstring).__name__}")
    if " " in bitstring:
        raise ValueError(
            f"bitstring {bitstring!r} contains spaces (multiple classical registers?); "
            "measure all vertices into a single register"
        )
    if len(bitstring) != num_nodes:
        raise ValueError(f"bitstring {bitstring!r} has length {len(bitstring)}, expected {num_nodes}")
    if set(bitstring) - {"0", "1"}:
        raise ValueError(f"bitstring {bitstring!r} may only contain '0' and '1'")
    chars = bitstring[::-1] if order == "qiskit" else bitstring if order == "vertex" else None
    if chars is None:
        raise ValueError(f"order must be 'qiskit' or 'vertex', got {order!r}")
    return tuple(int(c) for c in chars)


def assignment_to_bitstring(assignment: Sequence[int], *, order: BitOrder) -> str:
    """Inverse of :func:`bitstring_to_assignment`. Entries are validated like :func:`cut_value`."""
    s = "".join(str(b) for b in _bits_any_length(assignment))
    if order == "qiskit":
        return s[::-1]
    if order == "vertex":
        return s
    raise ValueError(f"order must be 'qiskit' or 'vertex', got {order!r}")


def assignment_to_index(assignment: Sequence[int]) -> int:
    """Computational-basis index ``k = sum_i x_i 2**i`` (vertex i = bit i, Qiskit convention)."""
    return sum(b << i for i, b in enumerate(_bits_any_length(assignment)))


def index_to_assignment(index: int, num_nodes: int) -> tuple[int, ...]:
    """Inverse of :func:`assignment_to_index`."""
    num_nodes = _check_num_nodes(num_nodes)
    if isinstance(index, bool) or not isinstance(index, (int, np.integer)):
        raise TypeError(f"index must be an int, got {type(index).__name__} {index!r}")
    index = int(index)
    if not 0 <= index < 2**num_nodes:
        raise ValueError(f"index {index} out of range for {num_nodes} vertices")
    return tuple((index >> i) & 1 for i in range(num_nodes))


def partition(assignment: Sequence[int]) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Split vertices into ``(side_0, side_1)`` according to the assignment (entries validated)."""
    bits = _bits_any_length(assignment)
    side0 = tuple(i for i, b in enumerate(bits) if b == 0)
    side1 = tuple(i for i, b in enumerate(bits) if b == 1)
    return side0, side1


def partition_to_assignment(
    num_nodes: int, side0: Iterable[int], side1: Iterable[int]
) -> tuple[int, ...]:
    """Inverse of :func:`partition`: vertices in ``side0`` get 0, in ``side1`` get 1.

    The two sides must be disjoint and together contain every vertex exactly once.
    """
    s0, s1 = list(side0), list(side1)
    for v in s0 + s1:
        _vertex(v, num_nodes)
    if len(set(s0)) != len(s0) or len(set(s1)) != len(s1):
        raise ValueError("a vertex is listed twice within one side of the partition")
    overlap = set(s0) & set(s1)
    if overlap:
        raise ValueError(f"vertices {sorted(overlap)} appear on both sides of the partition")
    missing = set(range(num_nodes)) - set(s0) - set(s1)
    if missing:
        raise ValueError(f"vertices {sorted(missing)} are not assigned to either side")
    x = [0] * num_nodes
    for v in s1:
        x[v] = 1
    return tuple(x)


# ---------------------------------------------------------------------------
# Objective
# ---------------------------------------------------------------------------


def cut_value(graph: WeightedGraph, assignment: Sequence[int]) -> float:
    """Weighted cut ``C(x) = sum_{(u,v)} w_uv [x_u != x_v]`` (each undirected edge once)."""
    x = validate_assignment(graph, assignment)
    return float(sum(w for u, v, w in graph.edges if x[u] != x[v]))


def cut_edges(graph: WeightedGraph, assignment: Sequence[int]) -> tuple[tuple[int, int, float], ...]:
    """Edges crossing the cut."""
    x = validate_assignment(graph, assignment)
    return tuple(e for e in graph.edges if x[e[0]] != x[e[1]])


def cut_value_from_bitstring(graph: WeightedGraph, bitstring: str, *, order: BitOrder) -> float:
    return cut_value(graph, bitstring_to_assignment(bitstring, graph.num_nodes, order=order))


def cut_value_from_partition(graph: WeightedGraph, side0: Iterable[int], side1: Iterable[int]) -> float:
    """Weighted cut of the partition ``side0 | side1`` (must cover all vertices)."""
    return cut_value(graph, partition_to_assignment(graph.num_nodes, side0, side1))


def all_cut_values(graph: WeightedGraph, *, max_nodes: int = DEFAULT_MAX_EXACT_NODES) -> np.ndarray:
    """Cut value of every basis state, as an array indexed by ``k = sum_i x_i 2**i``.

    This is exactly the diagonal of the QAOA cost Hamiltonian in Qiskit's
    little-endian computational basis.
    """
    _guard_size(graph.num_nodes, max_nodes)
    n = graph.num_nodes
    k = np.arange(2**n, dtype=np.int64)
    values = np.zeros(2**n, dtype=float)
    for u, v, w in graph.edges:
        values += w * (((k >> u) ^ (k >> v)) & 1)
    return values


def _guard_size(num_nodes: int, max_nodes: int) -> None:
    if num_nodes > max_nodes:
        raise ValueError(
            f"exhaustive search over 2**{num_nodes} assignments refused "
            f"(max_nodes={max_nodes}); raise max_nodes explicitly if intended"
        )


# ---------------------------------------------------------------------------
# Exact classical reference
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExactSolution:
    """Brute-force Max-Cut optimum.

    ``optimal_assignments`` lists *every* optimal assignment, including both
    members of each complementary pair (x and 1-x give the same cut).
    """

    optimal_value: float
    optimal_assignments: tuple[tuple[int, ...], ...]
    num_evaluated: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "optimal_value": self.optimal_value,
            "optimal_assignments": [list(a) for a in self.optimal_assignments],
            "optimal_bitstrings_qiskit": [assignment_to_bitstring(a, order="qiskit") for a in self.optimal_assignments],
            "optimal_partitions": [[list(s) for s in partition(a)] for a in self.optimal_assignments],
            "num_evaluated": self.num_evaluated,
        }


def solve_exact(
    graph: WeightedGraph, *, max_nodes: int = DEFAULT_MAX_EXACT_NODES, atol: float = CUT_ATOL
) -> ExactSolution:
    """Exhaustively evaluate all ``2**n`` assignments and return all optima.

    Refuses graphs with more than ``max_nodes`` vertices to avoid accidental
    exponential blow-up.
    """
    values = all_cut_values(graph, max_nodes=max_nodes)
    best = float(values.max())
    idx = np.flatnonzero(np.isclose(values, best, rtol=0.0, atol=atol))
    return ExactSolution(
        optimal_value=best,
        optimal_assignments=tuple(index_to_assignment(int(k), graph.num_nodes) for k in idx),
        num_evaluated=int(values.size),
    )


def approximation_ratio(value: float, optimal_value: float, *, atol: float = CUT_ATOL) -> float | None:
    """``value / optimal_value``; ``None`` when the optimum is 0 (ratio undefined)."""
    if abs(optimal_value) <= atol:
        return None
    return float(value) / float(optimal_value)


# ---------------------------------------------------------------------------
# SYNTHETIC development graphs (NOT the official benchmark)
# ---------------------------------------------------------------------------


def synthetic_weighted_graph() -> WeightedGraph:
    """SYNTHETIC 4-vertex weighted development graph (not an official benchmark).

    Edges: (0,1,1), (1,2,2), (2,3,3), (0,3,4), (0,2,5). Hand-verified optimum:
    cut 11 for x = (0,0,1,1) and its complement (1,1,0,0), i.e. {0,1} | {2,3}.
    """
    return WeightedGraph.from_edges(
        4,
        [(0, 1, 1.0), (1, 2, 2.0), (2, 3, 3.0), (3, 0, 4.0), (0, 2, 5.0)],
        name="synthetic_weighted_4",
        source="synthetic",
    )


def synthetic_unweighted_graph() -> WeightedGraph:
    """SYNTHETIC 4-vertex unweighted graph (square plus diagonal 0-2), optimum 4.

    This is the team's earlier development example; it is NOT an official benchmark.
    """
    return WeightedGraph.from_edges(
        4,
        [(0, 1), (1, 2), (2, 3), (3, 0), (0, 2)],
        name="synthetic_square_diagonal_4",
        source="synthetic",
    )


# ---------------------------------------------------------------------------
# Official Generator per PS-O1 Setup
# ---------------------------------------------------------------------------


def generate_erdos_renyi_benchmark(seed: int = 42) -> WeightedGraph:
    """Generate the official 6-node random graph: nx.erdos_renyi_graph(n=6, p=0.5, seed=42)
    with reproducible integer edge weights in 1..5.
    """
    import random
    import networkx as nx

    g_raw = nx.erdos_renyi_graph(n=6, p=0.5, seed=seed)
    rng = random.Random(seed)
    edges = []
    for u, v in sorted(g_raw.edges()):
        w = rng.randint(1, 5)
        edges.append((min(u, v), max(u, v), float(w)))

    return WeightedGraph.from_edges(
        num_nodes=6,
        edges=edges,
        name=f"erdos_renyi_6_p0.5_seed{seed}",
        source="official_networkx_generator",
    )


# ---------------------------------------------------------------------------
# Hamiltonian Construction
# ---------------------------------------------------------------------------

QREG_NAME = "q"
CREG_NAME = "meas"
BIT_ORDER = "qiskit"


def cost_hamiltonian(graph: WeightedGraph) -> SparsePauliOp:
    """Construct cost Hamiltonian C_hat = sum_{(u,v)} w_uv (I - Z_u Z_v)/2 as SparsePauliOp.
    
    Qubit i corresponds to vertex i. Diagonal equals all_cut_values(graph).
    """
    n = graph.num_nodes
    terms: list[tuple[str, list[int], float]] = [("", [], 0.5 * graph.total_weight)]
    terms += [("ZZ", [u, v], -0.5 * w) for u, v, w in graph.edges]
    return SparsePauliOp.from_sparse_list(terms, num_qubits=n).simplify()


# ---------------------------------------------------------------------------
# QAOA Circuit Construction
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class QAOACircuit:
    """Parameterised, topology-independent logical QAOA circuit."""

    circuit: QuantumCircuit
    gammas: ParameterVector
    betas: ParameterVector
    p: int
    graph: WeightedGraph
    measured: bool
    vertex_to_qubit: tuple[int, ...]
    qubit_to_clbit: tuple[int, ...]
    bit_order: str = BIT_ORDER

    @property
    def num_qubits(self) -> int:
        return self.circuit.num_qubits

    def parameter_dict(self, gammas: Sequence[float], betas: Sequence[float]) -> dict:
        """Map angle values onto circuit parameters."""
        gammas, betas = _check_angles(gammas, betas, self.p)
        mapping = {self.gammas[l]: gammas[l] for l in range(self.p)}
        mapping.update({self.betas[l]: betas[l] for l in range(self.p)})
        return mapping

    def bind(self, gammas: Sequence[float], betas: Sequence[float]) -> QuantumCircuit:
        """Return a copy of the circuit with parameters bound."""
        return self.circuit.assign_parameters(self.parameter_dict(gammas, betas), strict=False)

    def metadata(self) -> dict[str, Any]:
        """Interface metadata for transpilation and metrics."""
        ops = self.circuit.count_ops()
        return {
            "p": self.p,
            "num_qubits": self.num_qubits,
            "num_clbits": self.circuit.num_clbits,
            "measured": self.measured,
            "vertex_to_qubit": list(self.vertex_to_qubit),
            "qubit_to_clbit": list(self.qubit_to_clbit),
            "bit_order": self.bit_order,
            "parameter_names": [prm.name for prm in [*self.gammas, *self.betas]],
            "logical_depth": self.circuit.depth(),
            "logical_two_qubit_gates": int(ops.get("rzz", 0)),
            "logical_op_counts": {k: int(v) for k, v in ops.items()},
            "graph": self.graph.to_dict(),
        }


def build_qaoa_circuit(
    graph: WeightedGraph, p: int = 1, *, measure: bool = True, barriers: bool = False
) -> QAOACircuit:
    """Build the logical depth-p QAOA circuit for a weighted graph."""
    if isinstance(p, bool) or not isinstance(p, (int, np.integer)) or p < 1:
        raise ValueError(f"p must be an int >= 1, got {p!r}")
    p = int(p)
    n = graph.num_nodes
    gammas = ParameterVector("gamma", p)
    betas = ParameterVector("beta", p)

    qreg = QuantumRegister(n, QREG_NAME)
    if measure:
        creg = ClassicalRegister(n, CREG_NAME)
        qc = QuantumCircuit(qreg, creg, name=f"qaoa_p{p}")
    else:
        qc = QuantumCircuit(qreg, name=f"qaoa_p{p}")

    qc.h(qreg)
    for layer in range(p):
        if barriers:
            qc.barrier()
        append_cost_layer(qc, graph, gammas[layer])
        if barriers:
            qc.barrier()
        append_mixer_layer(qc, betas[layer])
    if measure:
        if barriers:
            qc.barrier()
        for i in range(n):
            qc.measure(qreg[i], creg[i])

    qc.metadata = {
        "problem": "weighted_maxcut",
        "graph_name": graph.name,
        "graph_source": graph.source,
        "p": p,
        "bit_order": BIT_ORDER,
    }
    return QAOACircuit(
        circuit=qc,
        gammas=gammas,
        betas=betas,
        p=p,
        graph=graph,
        measured=measure,
        vertex_to_qubit=tuple(range(n)),
        qubit_to_clbit=tuple(range(n)) if measure else (),
    )


def append_cost_layer(qc: QuantumCircuit, graph: WeightedGraph, gamma: Any) -> None:
    """Append U_C(gamma) = exp(-i gamma C_hat): rzz(-w*gamma) per edge."""
    for u, v, w in graph.edges:
        if w != 0.0:
            qc.rzz(-w * gamma, u, v)


def append_mixer_layer(qc: QuantumCircuit, beta: Any) -> None:
    """Append U_B(beta) = exp(-i beta sum_j X_j): rx(2*beta) on every qubit."""
    for q in range(qc.num_qubits):
        qc.rx(2 * beta, q)


def _check_angles(gammas: Sequence[float], betas: Sequence[float], p: int) -> tuple[list[float], list[float]]:
    g = [float(x) for x in np.atleast_1d(gammas)]
    b = [float(x) for x in np.atleast_1d(betas)]
    if len(g) != p or len(b) != p:
        raise ValueError(f"expected {p} gammas and {p} betas, got {len(g)} and {len(b)}")
    if not all(math.isfinite(x) for x in g + b):
        raise ValueError("angles must be finite")
    return g, b


# ---------------------------------------------------------------------------
# Statevector & Sampling Evaluation
# ---------------------------------------------------------------------------


def statevector_probabilities(qaoa: QAOACircuit, gammas: Sequence[float], betas: Sequence[float]) -> np.ndarray:
    """Exact basis-state probabilities, indexed by k = sum_i x_i 2**i."""
    circ = qaoa.bind(gammas, betas)
    if qaoa.measured:
        circ = circ.remove_final_measurements(inplace=False)
    return Statevector(circ).probabilities()


def statevector_expectation(
    qaoa: QAOACircuit, gammas: Sequence[float], betas: Sequence[float], *, cut_values: np.ndarray | None = None
) -> float:
    """Exact expectation value <gamma, beta| C_hat |gamma, beta>."""
    if cut_values is None:
        cut_values = all_cut_values(qaoa.graph)
    return float(statevector_probabilities(qaoa, gammas, betas) @ cut_values)


def sample_counts(
    qaoa: QAOACircuit, gammas: Sequence[float], betas: Sequence[float], *, shots: int = 1024, seed: int | None = None
) -> dict[str, int]:
    """Sample the measured circuit with Qiskit StatevectorSampler."""
    if not qaoa.measured:
        raise ValueError("circuit was built with measure=False")
    if shots < 1:
        raise ValueError("shots must be >= 1")
    sampler = StatevectorSampler(seed=seed)
    job = sampler.run([qaoa.bind(gammas, betas)], shots=int(shots))
    return dict(getattr(job.result()[0].data, CREG_NAME).get_counts())


@dataclass(frozen=True)
class DecodedSample:
    bitstring: str
    assignment: tuple[int, ...]
    partition: tuple[tuple[int, ...], tuple[int, ...]]
    cut_value: float
    count: int


def decode_counts(graph: WeightedGraph, counts: Mapping[str, int]) -> list[DecodedSample]:
    """Decode Qiskit-ordered counts into assignments and cut values."""
    out = []
    for key, c in counts.items():
        x = bitstring_to_assignment(key, graph.num_nodes, order=BIT_ORDER)
        out.append(DecodedSample(key, x, partition(x), cut_value(graph, x), int(c)))
    out.sort(key=lambda s: (-s.cut_value, -s.count, s.bitstring))
    return out


def cut_distribution(samples: Sequence[DecodedSample]) -> dict[float, int]:
    """Histogram {cut value: count} in ascending order."""
    dist: dict[float, int] = {}
    for s in samples:
        dist[s.cut_value] = dist.get(s.cut_value, 0) + s.count
    return dict(sorted(dist.items()))


def best_cut_with_statevector_probability(
    probabilities: np.ndarray, cut_values: np.ndarray, threshold: float
) -> float | None:
    """Largest cut among basis states with probability > threshold."""
    probabilities = np.asarray(probabilities, dtype=float)
    cut_values = np.asarray(cut_values, dtype=float)
    if probabilities.shape != cut_values.shape:
        raise ValueError("probabilities and cut_values must have the same shape")
    threshold = _require_real("threshold", threshold)
    if not 0.0 <= threshold < 1.0:
        raise ValueError(f"threshold must be in [0, 1), got {threshold}")
    if not np.all(np.isfinite(probabilities)) or np.any(probabilities < 0):
        raise ValueError("probabilities must be finite and non-negative")
    mask = probabilities > threshold
    return float(cut_values[mask].max()) if mask.any() else None


# ---------------------------------------------------------------------------
# Classical Optimization of QAOA Parameters
# ---------------------------------------------------------------------------


@dataclass
class QAOAConfig:
    """QAOA experiment and optimizer settings."""

    p: int = 1
    optimizer: str = "COBYLA"
    maxiter: int = 200
    tol: float | None = 1e-6
    n_restarts: int = 3
    initial_point: Sequence[float] | None = None
    objective: str = "statevector"
    shots: int = 4096
    seed: int | None = 1234
    gamma_range: tuple[float, float] = (0.0, math.pi)
    beta_range: tuple[float, float] = (0.0, math.pi / 2)
    statevector_probability_threshold: float = 1e-12

    def validate(self) -> None:
        for name in ("p", "maxiter", "n_restarts", "shots"):
            _require_int(name, getattr(self, name), minimum=1)
        if not isinstance(self.optimizer, str) or not self.optimizer:
            raise TypeError(f"optimizer must be a non-empty str, got {self.optimizer!r}")
        if self.objective not in ("statevector", "shots"):
            raise ValueError(f"objective must be 'statevector' or 'shots', got {self.objective!r}")
        if self.tol is not None:
            _require_real("tol", self.tol)
            if self.tol <= 0:
                raise ValueError(f"tol must be > 0 or None, got {self.tol}")
        if self.seed is not None:
            _require_int("seed", self.seed, minimum=0)
        for name in ("gamma_range", "beta_range"):
            rng = getattr(self, name)
            if not (isinstance(rng, (tuple, list)) and len(rng) == 2):
                raise TypeError(f"{name} must be a (low, high) pair, got {rng!r}")
            lo, hi = (_require_real(f"{name}[{i}]", x) for i, x in enumerate(rng))
            if not lo < hi:
                raise ValueError(f"{name} must satisfy low < high, got {rng!r}")
        if self.initial_point is not None:
            if isinstance(self.initial_point, (str, bytes)) or not hasattr(self.initial_point, "__len__"):
                raise TypeError(f"initial_point must be a sequence of 2p numbers, got {self.initial_point!r}")
            if len(self.initial_point) != 2 * self.p:
                raise ValueError(f"initial_point must have length 2p = {2 * self.p}")
            for i, x in enumerate(self.initial_point):
                _require_real(f"initial_point[{i}]", x)
        _require_real("statevector_probability_threshold", self.statevector_probability_threshold)
        if not 0.0 <= self.statevector_probability_threshold < 1.0:
            raise ValueError("statevector_probability_threshold must be in [0, 1)")


def _require_int(name: str, value: Any, *, minimum: int) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise TypeError(f"{name} must be an int, got {type(value).__name__} {value!r}")
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}, got {value}")


def _require_real(name: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float, np.integer, np.floating)):
        raise TypeError(f"{name} must be a real number, got {type(value).__name__} {value!r}")
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite, got {value}")
    return float(value)


@dataclass
class OptimizationTrace:
    initial_point: list[float]
    final_point: list[float]
    final_expectation: float
    nfev: int
    success: bool
    message: str
    history: list[float] = field(default_factory=list)


def optimize_parameters(
    qaoa: QAOACircuit, config: QAOAConfig
) -> tuple[list[float], list[float], list[OptimizationTrace]]:
    """Maximise expected cut over variational angles (gammas, betas)."""
    config.validate()
    p = qaoa.p
    rng = np.random.default_rng(config.seed)
    cut_values = all_cut_values(qaoa.graph)

    def expectation(x: np.ndarray) -> float:
        g, b = x[:p], x[p:]
        if config.objective == "statevector":
            return statevector_expectation(qaoa, g, b, cut_values=cut_values)
        counts = sample_counts(qaoa, g, b, shots=config.shots, seed=config.seed)
        # Fixed little-endian index resolution:
        return sum(
            c * cut_values[assignment_to_index(bitstring_to_assignment(k, qaoa.graph.num_nodes, order="qiskit"))]
            for k, c in counts.items()
        ) / config.shots

    traces: list[OptimizationTrace] = []
    for r in range(config.n_restarts):
        if r == 0 and config.initial_point is not None:
            x0 = np.asarray(config.initial_point, dtype=float)
        else:
            x0 = np.concatenate([rng.uniform(*config.gamma_range, p), rng.uniform(*config.beta_range, p)])
        history: list[float] = []

        def objective(x: np.ndarray) -> float:
            val = expectation(x)
            history.append(val)
            return -val

        res = minimize(objective, x0, method=config.optimizer, tol=config.tol, options={"maxiter": config.maxiter})
        traces.append(
            OptimizationTrace(
                initial_point=[float(v) for v in x0],
                final_point=[float(v) for v in res.x],
                final_expectation=float(-res.fun),
                nfev=int(res.nfev),
                success=bool(res.success),
                message=str(res.message),
                history=history,
            )
        )
    best = max(traces, key=lambda t: t.final_expectation)
    return best.final_point[:p], best.final_point[p:], traces


# ---------------------------------------------------------------------------
# End-to-end Solver Pipeline
# ---------------------------------------------------------------------------


@dataclass
class QAOAResult:
    """Structured QAOA results container."""

    graph: dict[str, Any]
    p: int
    gammas: list[float]
    betas: list[float]
    exact: dict[str, Any] | None
    optimal_value: float | None
    expected_cut: float
    expected_approximation_ratio: float | None
    optimal_solution_probability: float | None
    best_cut_with_statevector_probability: float | None
    statevector_probability_threshold: float
    shots: int
    seed: int | None
    counts: dict[str, int]
    cut_distribution: dict[float, int]
    sampled_mean_cut: float
    sampled_approximation_ratio: float | None
    best_observed_cut: float
    best_observed_bitstring: str
    best_observed_assignment: list[int]
    best_observed_partition: list[list[int]]
    best_observed_ratio: float | None
    best_observed_is_exact_optimum: bool | None
    sampled_optimal_frequency: float | None
    most_frequent_bitstring: str
    bit_order: str
    evaluation_mode: str
    optimizer_success: bool
    optimizer: dict[str, Any]
    circuit: dict[str, Any]
    runtime_seconds: float

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["cut_distribution"] = {str(k): v for k, v in self.cut_distribution.items()}
        return d


def run_qaoa(
    graph: WeightedGraph,
    config: QAOAConfig | None = None,
    *,
    exact: ExactSolution | None = None,
    max_exact_nodes: int = DEFAULT_MAX_EXACT_NODES,
) -> QAOAResult:
    """Execute complete QAOA optimization, sampling, and classical verification."""
    config = config or QAOAConfig()
    config.validate()
    t0 = time.perf_counter()

    if exact is None and graph.num_nodes <= max_exact_nodes:
        exact = solve_exact(graph, max_nodes=max_exact_nodes)
    opt = exact.optimal_value if exact is not None else None

    qaoa = build_qaoa_circuit(graph, config.p, measure=True)
    gammas, betas, traces = optimize_parameters(qaoa, config)

    probs = statevector_probabilities(qaoa, gammas, betas)
    cut_values = all_cut_values(graph)
    expected = float(probs @ cut_values)
    p_opt = None
    if exact is not None:
        p_opt = float(probs[np.isclose(cut_values, opt, rtol=0.0, atol=CUT_ATOL)].sum())
    sv_best = best_cut_with_statevector_probability(probs, cut_values, config.statevector_probability_threshold)

    counts = sample_counts(qaoa, gammas, betas, shots=config.shots, seed=config.seed)
    samples = decode_counts(graph, counts)
    best = samples[0]
    sampled_mean = sum(s.cut_value * s.count for s in samples) / config.shots
    most_frequent = max(samples, key=lambda s: (s.count, s.cut_value)).bitstring

    def ratio(v: float) -> float | None:
        return approximation_ratio(v, opt) if opt is not None else None

    best_trace = max(traces, key=lambda t: t.final_expectation)
    return QAOAResult(
        graph=graph.to_dict(),
        p=config.p,
        gammas=gammas,
        betas=betas,
        exact=exact.to_dict() if exact is not None else None,
        optimal_value=opt,
        expected_cut=expected,
        expected_approximation_ratio=ratio(expected),
        optimal_solution_probability=p_opt,
        best_cut_with_statevector_probability=sv_best,
        statevector_probability_threshold=config.statevector_probability_threshold,
        shots=config.shots,
        seed=config.seed,
        counts=dict(sorted(counts.items())),
        cut_distribution=cut_distribution(samples),
        sampled_mean_cut=sampled_mean,
        sampled_approximation_ratio=ratio(sampled_mean),
        best_observed_cut=best.cut_value,
        best_observed_bitstring=best.bitstring,
        best_observed_assignment=list(best.assignment),
        best_observed_partition=[list(s) for s in best.partition],
        best_observed_ratio=ratio(best.cut_value),
        best_observed_is_exact_optimum=(None if opt is None else abs(best.cut_value - opt) <= CUT_ATOL),
        sampled_optimal_frequency=(
            None if opt is None else sum(s.count for s in samples if abs(s.cut_value - opt) <= CUT_ATOL) / config.shots
        ),
        most_frequent_bitstring=most_frequent,
        bit_order=BIT_ORDER,
        evaluation_mode=f"optimise:{config.objective}; report:statevector expectation + {config.shots} noiseless shots",
        optimizer_success=best_trace.success,
        optimizer={
            "name": config.optimizer,
            "maxiter": config.maxiter,
            "tol": config.tol,
            "n_restarts": config.n_restarts,
            "objective": config.objective,
            "seed": config.seed,
            "best_restart": traces.index(best_trace),
            "restarts": [asdict(t) for t in traces],
        },
        circuit=qaoa.metadata(),
        runtime_seconds=time.perf_counter() - t0,
    )


def logical_circuit_for_routing(
    graph: WeightedGraph, p: int, gammas: Sequence[float] | None = None, betas: Sequence[float] | None = None
) -> QuantumCircuit:
    """Build and bind logical circuit for processor compilation."""
    qaoa = build_qaoa_circuit(graph, p, measure=True)
    if gammas is None and betas is None:
        return qaoa.circuit
    if gammas is None or betas is None:
        raise ValueError("provide both gammas and betas, or neither")
    return qaoa.bind(gammas, betas)

