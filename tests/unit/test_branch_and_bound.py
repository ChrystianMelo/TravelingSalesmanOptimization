from itertools import permutations

import pytest

from traveling_salesman_optimization.branch_and_bound import solve_branch_and_bound
from traveling_salesman_optimization.tsplib import TSPInstance, calculate_route_cost


def make_instance(
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


def brute_force_cost(instance: TSPInstance) -> int:
    return min(
        calculate_route_cost(instance.distances, (0, *tail))
        for tail in permutations(range(1, instance.dimension))
    )


@pytest.mark.parametrize(
    "coordinates",
    [
        ((0, 0),),
        ((0, 0), (3, 4)),
        ((0, 0), (10, 10), (0, 10), (10, 0)),
        ((0, 0), (3, 1), (8, 0), (7, 6), (2, 7)),
        ((1, 1), (5, 2), (9, 6), (5, 9), (0, 6), (4, 5)),
    ],
)
def test_branch_and_bound_matches_brute_force(
    coordinates: tuple[tuple[float, float], ...],
) -> None:
    instance = make_instance(coordinates)

    result = solve_branch_and_bound(instance)

    assert result.cost == brute_force_cost(instance)
    assert result.route[0] == result.route[-1] == instance.vertex_ids[0]
    assert len(result.route) == instance.dimension + 1
    assert set(result.route[:-1]) == set(instance.vertex_ids)
    assert len(set(result.route[:-1])) == instance.dimension
    id_to_index = {vertex_id: index for index, vertex_id in enumerate(instance.vertex_ids)}
    returned_route_indices = tuple(id_to_index[vertex_id] for vertex_id in result.route[:-1])
    assert instance.route_cost(returned_route_indices) == result.cost
    assert result.expanded_nodes >= 0
    assert result.pruned_nodes >= 1


def test_solver_improves_a_crossing_trivial_route_and_preserves_original_ids() -> None:
    instance = make_instance(
        ((0, 0), (10, 10), (0, 10), (10, 0)),
        vertex_ids=(100, 8, 55, 21),
    )
    trivial_cost = instance.route_cost((0, 1, 2, 3))

    result = solve_branch_and_bound(instance)

    assert trivial_cost == 48
    assert result.cost == 40
    assert result.cost < trivial_cost
    assert result.route[0] == result.route[-1] == 100
    assert set(result.route[:-1]) == {100, 8, 55, 21}
    # A ordem best-first desta instância difere da DFS: cinco estados parciais
    # geram filhos antes de a primeira folha ótima tornar os demais podáveis.
    assert result.expanded_nodes == 5
    assert result.pruned_nodes == 4


def test_initial_route_strategy_is_replaceable() -> None:
    instance = make_instance(((0, 0), (10, 10), (0, 10), (10, 0)))
    calls = 0

    def alternative_strategy(_: TSPInstance) -> tuple[int, ...]:
        nonlocal calls
        calls += 1
        return (0, 2, 1, 3)

    result = solve_branch_and_bound(instance, alternative_strategy)

    assert calls == 1
    assert result.cost == 40


def test_instrumentation_uses_nested_monotonic_durations() -> None:
    instance = make_instance(((0, 0), (10, 10), (0, 10), (10, 0)))

    result = solve_branch_and_bound(instance)

    assert result.status == "optimal"
    assert result.initial_cost == 48
    assert result.optimal_cost == result.cost == 40
    assert result.max_depth == instance.dimension - 1
    assert result.solver_total_seconds == pytest.approx(
        result.initialization_seconds + result.search_seconds
    )
    assert 0 <= result.mst_seconds <= result.lower_bound_seconds <= result.search_seconds
    assert result.lower_bound_calls > 0
    assert result.mst_calls == result.mst_computations + result.mst_cache_hits


def test_zero_deadline_preserves_trivial_incumbent() -> None:
    instance = make_instance(((0, 0), (10, 10), (0, 10), (10, 0)))

    result = solve_branch_and_bound(instance, time_limit_seconds=0)

    assert result.status == "timeout"
    assert result.optimal_cost is None
    assert result.initial_cost == result.cost == 48
    assert result.route == (1, 2, 3, 4, 1)
    assert result.expanded_nodes == result.pruned_nodes == 0
    assert result.lower_bound_calls == result.mst_calls == 0
