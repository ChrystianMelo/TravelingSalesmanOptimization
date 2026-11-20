from itertools import permutations

import pytest

from traveling_salesman_optimization.branch_and_bound import (
    _incident_vertices_by_cost,
    _two_edges_lower_bound,
    solve_branch_and_bound,
)
from traveling_salesman_optimization.tsplib import TSPInstance, calculate_route_cost


def make_euclidean_instance(
    coordinates: tuple[tuple[float, float], ...],
    vertex_ids: tuple[int, ...] | None = None,
) -> TSPInstance:
    # Usa o parser público indiretamente não seria conveniente em testes do solver;
    # esta construção replica apenas a matriz com a regra EUC_2D já testada.
    from math import hypot

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
        vertex_ids=vertex_ids or tuple(range(1, size + 1)),
        coordinates=coordinates,
        distances=tuple(tuple(row) for row in matrix),
    )


def brute_force_optimal_cost(instance: TSPInstance) -> int:
    return min(
        calculate_route_cost(instance.distances, (0, *tail))
        for tail in permutations(range(1, instance.dimension))
    )


def brute_force_completion_cost(instance: TSPInstance, partial_route: tuple[int, ...]) -> int:
    remaining = tuple(vertex for vertex in range(instance.dimension) if vertex not in partial_route)
    return min(
        calculate_route_cost(instance.distances, (*partial_route, *tail))
        for tail in permutations(remaining)
    )


def calculate_two_edges_bound(instance: TSPInstance, partial_route: tuple[int, ...]) -> int | None:
    remaining_mask = 0
    for vertex in range(instance.dimension):
        if vertex not in partial_route:
            remaining_mask |= 1 << vertex
    cost_so_far = sum(
        instance.distances[source][target]
        for source, target in zip(partial_route, partial_route[1:], strict=False)
    )
    return _two_edges_lower_bound(
        instance.distances,
        _incident_vertices_by_cost(instance.distances),
        partial_route[-1],
        remaining_mask,
        cost_so_far,
    )


def test_branch_and_bound_matches_brute_force_and_preserves_original_ids() -> None:
    instance = make_euclidean_instance(
        ((0, 0), (10, 10), (0, 10), (10, 0)),
        vertex_ids=(100, 8, 55, 21),
    )

    result = solve_branch_and_bound(instance)

    assert result.cost == brute_force_optimal_cost(instance) == 40
    assert result.initial_cost == 48
    assert result.route[0] == result.route[-1] == instance.vertex_ids[0]
    assert len(result.route) == instance.dimension + 1
    assert set(result.route[:-1]) == set(instance.vertex_ids)
    assert len(set(result.route[:-1])) == instance.dimension
    id_to_index = {vertex_id: index for index, vertex_id in enumerate(instance.vertex_ids)}
    returned_route_indices = tuple(id_to_index[vertex_id] for vertex_id in result.route[:-1])
    assert instance.route_cost(returned_route_indices) == result.cost
    assert result.expanded_nodes == 5
    assert result.pruned_nodes == 4
    assert result.generated_nodes == result.lower_bound_calls == 10


def test_two_edges_bound_never_exceeds_small_partial_route_completions() -> None:
    instance = make_euclidean_instance(((0, 0), (3, 1), (8, 0), (7, 6), (2, 7), (4, 5)))
    partial_routes = (
        (0,),
        (0, 1),
        (0, 1, 3),
        (0, 4, 5, 2),
        (0, 1, 3, 5, 4, 2),
    )

    for partial_route in partial_routes:
        bound = calculate_two_edges_bound(instance, partial_route)
        assert bound is not None
        assert bound <= brute_force_completion_cost(instance, partial_route)

    complete_route = partial_routes[-1]
    assert calculate_two_edges_bound(instance, complete_route) == calculate_route_cost(
        instance.distances, complete_route
    )


def test_branch_and_bound_accepts_a_replaceable_warm_start() -> None:
    instance = make_euclidean_instance(((0, 0), (10, 10), (0, 10), (10, 0)))
    calls = 0

    def alternative_strategy(_: TSPInstance) -> tuple[int, ...]:
        nonlocal calls
        calls += 1
        return (0, 2, 1, 3)

    result = solve_branch_and_bound(instance, alternative_strategy)

    assert calls == 1
    assert result.cost == 40


def test_instrumentation_uses_nested_monotonic_durations() -> None:
    instance = make_euclidean_instance(((0, 0), (10, 10), (0, 10), (10, 0)))

    result = solve_branch_and_bound(instance)

    assert result.status == "optimal"
    assert result.initial_cost == 48
    assert result.optimal_cost == result.cost == 40
    assert result.max_depth == instance.dimension - 1
    assert result.solver_total_seconds == pytest.approx(
        result.initialization_seconds + result.search_seconds
    )
    assert 0 <= result.lower_bound_seconds <= result.search_seconds
    assert result.lower_bound_calls > 0


def test_zero_time_limit_preserves_the_initial_incumbent() -> None:
    instance = make_euclidean_instance(((0, 0), (10, 10), (0, 10), (10, 0)))

    result = solve_branch_and_bound(instance, time_limit_seconds=0)

    assert result.status == "timeout"
    assert result.optimal_cost is None
    assert result.initial_cost == result.cost == 48
    assert result.route == (1, 2, 3, 4, 1)
    assert result.expanded_nodes == result.pruned_nodes == 0
    assert result.generated_nodes == 0
    assert result.lower_bound_calls == 0


def test_approximation_phase_metrics_are_exposed_by_the_solver() -> None:
    from traveling_salesman_optimization.approximation import christofides_route

    instance = make_euclidean_instance(((0, 0), (6, 0), (9, 4), (6, 9), (0, 8), (3, 4)))

    result = solve_branch_and_bound(
        instance,
        christofides_route,
        phase_memory_query=lambda: 123_456,
    )

    assert result.mst_calls == 1
    assert result.matching_calls == 1
    assert result.eulerian_circuit_calls == 1
    assert result.shortcut_calls == 1
    assert 0 <= result.mst_seconds <= result.initialization_seconds
    assert 0 <= result.matching_seconds <= result.initialization_seconds
    assert result.mst_process_peak_bytes == 123_456
    assert result.matching_process_peak_bytes == 123_456
