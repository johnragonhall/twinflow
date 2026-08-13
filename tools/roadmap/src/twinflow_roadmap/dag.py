"""Cycle detection and layering, in one place.

Two callers need the same walk: the work-package graph in roadmap.py and the
rendered phase diagram in graph.py. Two copies of a graph algorithm is two
places for an off-by-one, and the second copy is the one nobody tests.

`cycles` reports every node on a cycle rather than the one node the walk
happened to notice, because a message naming one member of a three-node cycle
sends a contributor to the wrong edge.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping


def cycles(edges: Mapping[str, Iterable[str]]) -> list[tuple[str, ...]]:
    """Every cycle reachable in the graph, each as the nodes that close it.

    Edges pointing at a node the mapping does not declare are ignored: a
    dangling reference is somebody else's finding, and reporting it twice helps
    nobody.
    """
    color: dict[str, int] = dict.fromkeys(edges, 0)
    stack: list[str] = []
    found: list[tuple[str, ...]] = []
    seen: set[frozenset[str]] = set()

    def walk(node: str) -> None:
        color[node] = 1
        stack.append(node)
        for neighbor in edges.get(node, ()):
            if neighbor not in color:
                continue
            if color[neighbor] == 0:
                walk(neighbor)
            elif color[neighbor] == 1:
                cycle = tuple(stack[stack.index(neighbor) :])
                key = frozenset(cycle)
                if key not in seen:
                    seen.add(key)
                    found.append(cycle)
        stack.pop()
        color[node] = 2

    for node in edges:
        if color[node] == 0:
            walk(node)
    return found


def is_acyclic(edges: Mapping[str, Iterable[str]]) -> bool:
    """A Kahn sort, which is an independent answer to the same question.

    Deliberately a different algorithm from `cycles`. The property suite asserts
    the two agree, and two implementations of one idea that agree on generated
    input is worth more than one implementation nobody can check.
    """
    remaining = {
        node: {edge for edge in targets if edge in edges} for node, targets in edges.items()
    }
    while remaining:
        ready = [node for node, targets in remaining.items() if not targets]
        if not ready:
            return False
        for node in ready:
            del remaining[node]
        for targets in remaining.values():
            targets.difference_update(ready)
    return True


def waves(edges: Mapping[str, Iterable[str]]) -> list[list[str]]:
    """Layers that may run together, each sorted so the output is stable.

    Stops when nothing is ready, so a graph with a cycle returns the layers it
    could order rather than nothing at all. The caller reports the cycle.
    """
    remaining = {
        node: {edge for edge in targets if edge in edges} for node, targets in edges.items()
    }
    layers: list[list[str]] = []
    while remaining:
        ready = sorted(node for node, targets in remaining.items() if not targets)
        if not ready:
            break
        layers.append(ready)
        for node in ready:
            del remaining[node]
        for targets in remaining.values():
            targets.difference_update(ready)
    return layers
