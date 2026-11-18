"""Branch-and-Bound exato com busca best-first para o TSP simétrico."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from heapq import heappop, heappush
from itertools import count
from time import perf_counter
from typing import Literal

from traveling_salesman_optimization.initial_solutions import (
    InitialRouteStrategy,
    trivial_initial_route,
)
from traveling_salesman_optimization.tsplib import TSPInstance

SolverStatus = Literal["running", "optimal", "timeout"]


@dataclass(frozen=True, slots=True)
class BranchAndBoundResult:
    """Melhor solução viável e instrumentação da árvore de busca.

    ``cost`` é sempre o custo da melhor rota viável conhecida. Quando
    ``status`` é ``"optimal"``, esse custo tem otimalidade comprovada; quando é
    ``"timeout"``, ele é apenas a incumbente preservada.

    Os tempos usam ``time.perf_counter``, um relógio monotônico. O tempo total
    do solver é a soma de inicialização e busca. O tempo de limite inferior
    está contido no tempo de busca, e o tempo de AGM está contido tanto no
    tempo de limite inferior quanto no de busca: esses valores não devem ser
    somados. Checkpoints também estão contidos no tempo da busca.

    ``max_depth`` conta arestas escolhidas depois da origem: a raiz tem
    profundidade zero e uma rota completa de ``n`` vértices tem profundidade
    ``n - 1``.
    """

    route: tuple[int, ...]
    cost: int
    initial_cost: int
    status: SolverStatus
    expanded_nodes: int
    pruned_nodes: int
    max_depth: int
    initialization_seconds: float
    search_seconds: float
    solver_total_seconds: float
    lower_bound_calls: int
    lower_bound_seconds: float
    mst_calls: int
    mst_computations: int
    mst_cache_hits: int
    mst_seconds: float
    checkpoint_calls: int
    checkpoint_seconds: float

    @property
    def optimal_cost(self) -> int | None:
        """Retorna o custo ótimo somente quando a prova foi concluída."""

        return self.cost if self.status == "optimal" else None


ProgressCallback = Callable[[BranchAndBoundResult], None]


class _DeadlineExceeded(Exception):
    """Sinal interno para encerrar a busca em um ponto cooperativo."""


def solve_branch_and_bound(
    instance: TSPInstance,
    initial_route_strategy: InitialRouteStrategy = trivial_initial_route,
    *,
    time_limit_seconds: float | None = None,
    progress_callback: ProgressCallback | None = None,
    checkpoint_interval_seconds: float = 30.0,
) -> BranchAndBoundResult:
    """Resolve ``instance`` por Branch-and-Bound best-first.

    A lógica de exploração é a mesma da versão não instrumentada: o primeiro
    vértice fica fixo, estados são priorizados pelo limite inferior e a AGM de
    cada subconjunto é memorizada. O prazo é verificado em pontos seguros do
    laço principal, da geração de filhos e do Prim. Ao expirar, a função
    devolve a melhor solução viável já encontrada e ``status="timeout"``.

    Args:
        instance: Instância com matriz de custos já calculada.
        initial_route_strategy: Estratégia que produz a incumbente inicial.
        time_limit_seconds: Prazo monotônico para inicialização mais busca.
            ``None`` desabilita o prazo; zero provoca timeout cooperativo assim
            que a rota inicial estiver disponível.
        progress_callback: Função opcional que persiste um retrato da busca.
        checkpoint_interval_seconds: Intervalo monotônico entre retratos.

    Returns:
        Melhor ciclo conhecido, seu status e todas as métricas coletadas.

    Raises:
        ValueError: Se a entrada, o prazo ou a rota inicial forem inválidos.
    """

    dimension = instance.dimension
    if dimension == 0:
        raise ValueError("a instância deve possuir ao menos um vértice")
    if time_limit_seconds is not None and time_limit_seconds < 0:
        raise ValueError("o limite de tempo não pode ser negativo")
    if checkpoint_interval_seconds <= 0:
        raise ValueError("o intervalo de checkpoint deve ser positivo")

    solver_started = perf_counter()
    deadline = None if time_limit_seconds is None else solver_started + time_limit_seconds

    initial_route = tuple(initial_route_strategy(instance))
    if len(initial_route) != dimension or set(initial_route) != set(range(dimension)):
        raise ValueError("a estratégia inicial deve retornar cada índice uma única vez")
    if initial_route[0] != 0:
        origin_position = initial_route.index(0)
        initial_route = initial_route[origin_position:] + initial_route[:origin_position]

    distances = instance.distances
    best_route = initial_route
    best_cost = instance.route_cost(initial_route)
    initial_cost = best_cost
    initialization_finished = perf_counter()
    initialization_seconds = initialization_finished - solver_started
    search_started = initialization_finished

    expanded_nodes = 0
    pruned_nodes = 0
    max_depth = 0
    lower_bound_calls = 0
    lower_bound_seconds = 0.0
    mst_calls = 0
    mst_computations = 0
    mst_cache_hits = 0
    mst_seconds = 0.0
    checkpoint_calls = 0
    checkpoint_seconds = 0.0
    mst_cache: dict[int, int] = {}
    next_checkpoint = search_started

    def check_deadline(now: float | None = None) -> None:
        if deadline is not None and (perf_counter() if now is None else now) >= deadline:
            raise _DeadlineExceeded

    def make_result(status: SolverStatus, now: float | None = None) -> BranchAndBoundResult:
        measured_at = perf_counter() if now is None else now
        route_ids = tuple(instance.vertex_ids[index] for index in best_route)
        return BranchAndBoundResult(
            route=route_ids + (route_ids[0],),
            cost=best_cost,
            initial_cost=initial_cost,
            status=status,
            expanded_nodes=expanded_nodes,
            pruned_nodes=pruned_nodes,
            max_depth=max_depth,
            initialization_seconds=initialization_seconds,
            search_seconds=measured_at - search_started,
            solver_total_seconds=measured_at - solver_started,
            lower_bound_calls=lower_bound_calls,
            lower_bound_seconds=lower_bound_seconds,
            mst_calls=mst_calls,
            mst_computations=mst_computations,
            mst_cache_hits=mst_cache_hits,
            mst_seconds=mst_seconds,
            checkpoint_calls=checkpoint_calls,
            checkpoint_seconds=checkpoint_seconds,
        )

    def maybe_checkpoint(*, force: bool = False) -> None:
        nonlocal checkpoint_calls, checkpoint_seconds, next_checkpoint
        if progress_callback is None:
            return
        now = perf_counter()
        if not force and now < next_checkpoint:
            return
        callback_started = now
        progress_callback(make_result("running", now))
        checkpoint_seconds += perf_counter() - callback_started
        checkpoint_calls += 1
        next_checkpoint = perf_counter() + checkpoint_interval_seconds

    def minimum_spanning_tree_cost(vertices_mask: int) -> int:
        """Calcula por Prim a AGM do subconjunto, com cache por bitmask."""

        nonlocal mst_calls, mst_computations, mst_cache_hits, mst_seconds
        mst_calls += 1
        call_started = perf_counter()
        try:
            cached = mst_cache.get(vertices_mask)
            if cached is not None:
                mst_cache_hits += 1
                return cached

            mst_computations += 1
            if vertices_mask == 0 or vertices_mask & (vertices_mask - 1) == 0:
                mst_cache[vertices_mask] = 0
                return 0

            first_bit = vertices_mask & -vertices_mask
            first = first_bit.bit_length() - 1
            remaining_mask = vertices_mask ^ first_bit
            connection_cost = {
                vertex: distances[first][vertex]
                for vertex in range(dimension)
                if remaining_mask & (1 << vertex)
            }
            total = 0

            while remaining_mask:
                check_deadline()
                next_vertex = min(
                    (vertex for vertex in connection_cost if remaining_mask & (1 << vertex)),
                    key=connection_cost.__getitem__,
                )
                total += connection_cost[next_vertex]
                next_bit = 1 << next_vertex
                remaining_mask ^= next_bit
                for vertex in connection_cost:
                    if remaining_mask & (1 << vertex):
                        connection_cost[vertex] = min(
                            connection_cost[vertex], distances[next_vertex][vertex]
                        )
            mst_cache[vertices_mask] = total
            return total
        finally:
            mst_seconds += perf_counter() - call_started

    def lower_bound(current: int, remaining_mask: int, cost_so_far: int) -> int:
        """Limita inferiormente uma extensão e mede a chamada completa."""

        nonlocal lower_bound_calls, lower_bound_seconds
        lower_bound_calls += 1
        call_started = perf_counter()
        try:
            check_deadline(call_started)
            if remaining_mask == 0:
                return cost_so_far + distances[current][0]
            remaining = (vertex for vertex in range(dimension) if remaining_mask & (1 << vertex))
            from_current = min(distances[current][vertex] for vertex in remaining)
            remaining = (vertex for vertex in range(dimension) if remaining_mask & (1 << vertex))
            to_origin = min(distances[vertex][0] for vertex in remaining)
            return (
                cost_so_far + minimum_spanning_tree_cost(remaining_mask) + from_current + to_origin
            )
        finally:
            lower_bound_seconds += perf_counter() - call_started

    status: SolverStatus = "optimal"
    try:
        maybe_checkpoint(force=True)
        check_deadline()
        all_except_origin = ((1 << dimension) - 1) ^ 1
        root_bound = lower_bound(0, all_except_origin, 0)
        insertion_order = count()
        frontier: list[tuple[int, int, int, int, int, tuple[int, ...]]] = []
        heappush(
            frontier,
            (root_bound, next(insertion_order), 0, all_except_origin, 0, (0,)),
        )

        while frontier:
            check_deadline()
            maybe_checkpoint()
            bound, _, current, remaining_mask, cost_so_far, partial_route = heappop(frontier)

            if bound >= best_cost:
                pruned_nodes += 1
                continue

            if remaining_mask == 0:
                best_cost = bound
                best_route = partial_route
                continue

            expanded_nodes += 1
            for next_vertex in range(1, dimension):
                check_deadline()
                next_bit = 1 << next_vertex
                if not remaining_mask & next_bit:
                    continue

                child_remaining = remaining_mask ^ next_bit
                child_cost = cost_so_far + distances[current][next_vertex]
                child_bound = lower_bound(next_vertex, child_remaining, child_cost)
                child_route = partial_route + (next_vertex,)
                max_depth = max(max_depth, len(child_route) - 1)
                heappush(
                    frontier,
                    (
                        child_bound,
                        next(insertion_order),
                        next_vertex,
                        child_remaining,
                        child_cost,
                        child_route,
                    ),
                )
    except _DeadlineExceeded:
        status = "timeout"

    return make_result(status)
