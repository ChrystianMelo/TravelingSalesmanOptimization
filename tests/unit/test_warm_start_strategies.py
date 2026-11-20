from collections import Counter
from itertools import permutations
from math import hypot

import pytest

from traveling_salesman_optimization import approximation as approximation_module
from traveling_salesman_optimization.approximation import (
    _eulerian_circuit,
    _eulerian_to_hamiltonian,
    _minimum_spanning_tree_edges,
    _minimum_weight_perfect_matching,
    christofides_route,
    twice_around_tree_route,
)
from traveling_salesman_optimization.initial_solutions import INITIAL_ROUTE_STRATEGIES
from traveling_salesman_optimization.tsplib import TSPInstance


def make_euclidean_instance(coordinates: tuple[tuple[float, float], ...]) -> TSPInstance:
    size = len(coordinates)
    matrix = [[0] * size for _ in range(size)]
    for source in range(size):
        for target in range(source + 1, size):
            distance = int(
                hypot(
                    coordinates[source][0] - coordinates[target][0],
                    coordinates[source][1] - coordinates[target][1],
                )
                + 0.5
            )
            matrix[source][target] = matrix[target][source] = distance
    return TSPInstance(
        name="test",
        vertex_ids=tuple(range(1, size + 1)),
        coordinates=coordinates,
        distances=tuple(tuple(row) for row in matrix),
    )


def brute_force_optimal_cost(instance: TSPInstance) -> int:
    return min(
        instance.route_cost((0, *tail)) for tail in permutations(range(1, instance.dimension))
    )


def assert_valid_route(instance: TSPInstance, route: tuple[int, ...]) -> None:
    assert len(route) == instance.dimension
    assert set(route) == set(range(instance.dimension))
    assert route[0] == 0


@pytest.mark.parametrize(
    ("strategy_name", "expected_cost"),
    [
        pytest.param("trivial", 54, id="trivial"),
        pytest.param("nearest_neighbor", 43, id="nearest-neighbor"),
        pytest.param("convex_hull", 40, id="convex-hull"),
        pytest.param("twice_around_tree", 48, id="twice-around-tree"),
        pytest.param("christofides", 44, id="christofides"),
    ],
)
def test_each_warm_start_strategy_builds_the_expected_route(
    strategy_name: str, expected_cost: int
) -> None:
    instance = make_euclidean_instance(((0, 0), (10, 10), (0, 10), (10, 0), (5, 2), (2, 6)))

    route = tuple(INITIAL_ROUTE_STRATEGIES[strategy_name](instance))
    assert_valid_route(instance, route)
    assert instance.route_cost(route) == expected_cost


def test_graph_primitives_find_the_expected_mst_and_perfect_matching() -> None:
    distances = (
        (0, 1, 8, 9),
        (1, 0, 2, 8),
        (8, 2, 0, 1),
        (9, 8, 1, 0),
    )

    assert _minimum_spanning_tree_edges(distances) == ((0, 1), (1, 2), (2, 3))
    matching = _minimum_weight_perfect_matching((0, 1, 2, 3), distances)
    matched_vertices = tuple(vertex for edge in matching for vertex in edge)
    assert matching == ((0, 1), (2, 3))
    assert len(matched_vertices) == len(set(matched_vertices))
    assert set(matched_vertices) == {0, 1, 2, 3}


def test_eulerian_pipeline_preserves_parallel_edges_and_shortcuts_repetitions() -> None:
    edges = ((0, 1), (0, 1), (1, 2), (1, 2), (0, 2), (0, 2))

    circuit = _eulerian_circuit(3, edges)
    traversed_edges = Counter(
        tuple(sorted((source, target)))
        for source, target in zip(circuit, circuit[1:], strict=False)
    )

    assert circuit[0] == circuit[-1] == 0
    assert len(circuit) == len(edges) + 1
    assert traversed_edges == Counter(tuple(sorted(edge)) for edge in edges)
    assert _eulerian_to_hamiltonian((0, 1, 2, 1, 3, 2, 0), 4) == (0, 1, 2, 3)
    with pytest.raises(RuntimeError, match="não visitou todos"):
        _eulerian_to_hamiltonian((0, 1, 0), 3)


def test_approximations_handle_zero_one_and_two_vertices() -> None:
    cases = (
        ((), ()),
        (((2.0, 3.0),), (0,)),
        (((0.0, 0.0), (3.0, 4.0)), (0, 1)),
    )

    for coordinates, expected_route in cases:
        instance = make_euclidean_instance(coordinates)
        assert twice_around_tree_route(instance) == expected_route
        assert christofides_route(instance) == expected_route


def test_approximations_respect_their_metric_bounds_on_a_small_instance() -> None:
    instance = make_euclidean_instance(((0, 0), (6, 0), (9, 4), (6, 9), (0, 8), (3, 4)))
    optimum = brute_force_optimal_cost(instance)
    twice_route = twice_around_tree_route(instance)
    christofides = christofides_route(instance)

    assert_valid_route(instance, twice_route)
    assert_valid_route(instance, christofides)
    assert twice_route == twice_around_tree_route(instance)
    assert christofides == christofides_route(instance)
    assert instance.route_cost(twice_route) <= 2 * optimum
    assert 2 * instance.route_cost(christofides) <= 3 * optimum


def test_christofides_rejects_an_incomplete_matching(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    instance = make_euclidean_instance(((0, 0), (10, 0), (10, 10), (0, 10)))
    monkeypatch.setattr(
        approximation_module,
        "_minimum_weight_perfect_matching",
        lambda odd_vertices, distances: (),
    )

    with pytest.raises(RuntimeError, match="cada vértice ímpar exatamente uma vez"):
        christofides_route(instance)
