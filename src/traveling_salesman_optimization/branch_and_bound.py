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
from traveling_salesman_optimization.phase_profiling import (
    MemoryQuery,
    collect_approximation_profile,
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
    está contido no tempo de busca e não deve ser somado a ele. Checkpoints
    também estão contidos no tempo da busca.

    ``max_depth`` conta arestas escolhidas depois da origem: a raiz tem
    profundidade zero e uma rota completa de ``n`` vértices tem profundidade
    ``n - 1``.
    """

    route: tuple[int, ...]
    cost: int
    initial_cost: int
    status: SolverStatus
    generated_nodes: int
    expanded_nodes: int
    pruned_nodes: int
    max_depth: int
    initialization_seconds: float
    search_seconds: float
    solver_total_seconds: float
    lower_bound_calls: int
    lower_bound_seconds: float
    checkpoint_calls: int
    checkpoint_seconds: float
    mst_calls: int
    mst_seconds: float
    mst_process_peak_bytes: int
    matching_calls: int
    matching_seconds: float
    matching_process_peak_bytes: int
    eulerian_circuit_calls: int
    eulerian_circuit_seconds: float
    eulerian_circuit_process_peak_bytes: int
    shortcut_calls: int
    shortcut_seconds: float
    shortcut_process_peak_bytes: int

    @property
    def optimal_cost(self) -> int | None:
        """Retorna o custo ótimo somente quando a prova foi concluída."""

        return self.cost if self.status == "optimal" else None


ProgressCallback = Callable[[BranchAndBoundResult], None]


class _DeadlineExceeded(Exception):
    """Sinal interno para encerrar a busca em um ponto cooperativo."""


@dataclass(frozen=True, slots=True)
class _RouteNode:
    """Representa um prefixo por compartilhamento estrutural com seu pai."""

    vertex: int
    parent: _RouteNode | None
    depth: int


def _materialize_route(node: _RouteNode) -> tuple[int, ...]:
    """Reconstrói uma rota somente quando ela se torna a incumbente."""

    route = [0] * (node.depth + 1)
    current: _RouteNode | None = node
    while current is not None:
        route[current.depth] = current.vertex
        current = current.parent
    return tuple(route)


def _incident_vertices_by_cost(
    distances: tuple[tuple[int, ...], ...],
) -> tuple[tuple[int, ...], ...]:
    """Ordena os outros vértices por custo incidente e, depois, por índice."""

    dimension = len(distances)
    return tuple(
        tuple(
            sorted(
                (target for target in range(dimension) if target != source),
                key=lambda target: (distances[source][target], target),
            )
        )
        for source in range(dimension)
    )


def _cheapest_allowed_edges_sum(
    vertex: int,
    allowed_mask: int,
    required: int,
    distances: tuple[tuple[int, ...], ...],
    incident_vertices: tuple[tuple[int, ...], ...],
) -> int | None:
    """Soma ``required`` arestas distintas permitidas, ou sinaliza inviabilidade."""

    total = 0
    selected = 0
    for target in incident_vertices[vertex]:
        if allowed_mask & (1 << target):
            total += distances[vertex][target]
            selected += 1
            if selected == required:
                return total
    return None


def _two_edges_lower_bound(
    distances: tuple[tuple[int, ...], ...],
    incident_vertices: tuple[tuple[int, ...], ...],
    current: int,
    remaining_mask: int,
    cost_so_far: int,
) -> int | None:
    """Adapta o LB das duas arestas aos estados de caminho da busca.

    As arestas já percorridas são obrigatórias. Vértices internos do caminho
    já têm grau dois; origem e ponta atual têm uma aresta fixa e só podem usar
    como segunda aresta um vértice ainda não visitado. Um vértice restante pode
    ligar-se a outro restante ou a uma das duas pontas. Arestas para vértices
    internos e o fechamento antecipado entre as pontas não são permitidos.

    O retorno ``None`` indica que algum vértice não possui arestas permitidas
    suficientes para completar grau dois. Estados completos recebem o custo
    exato, com a volta à origem.
    """

    dimension = len(distances)
    if remaining_mask == 0:
        return cost_so_far + distances[current][0]

    # O projeto aceita as instâncias degeneradas de um ou dois vértices. Para
    # dois vértices, a única rota usa a mesma aresta na ida e na volta, embora
    # não existam duas arestas incidentes distintas no grafo simples.
    if dimension <= 2:
        if remaining_mask & (remaining_mask - 1):
            return None
        remaining_vertex = remaining_mask.bit_length() - 1
        return cost_so_far + distances[current][remaining_vertex] + distances[remaining_vertex][0]

    visited_count = dimension - remaining_mask.bit_count()
    if visited_count == 1:
        # Raiz: nenhum grau foi fixado e todas as arestas entre vértices
        # distintos estão permitidas.
        all_vertices_mask = (1 << dimension) - 1
        contribution_sum = 0
        for vertex in range(dimension):
            contribution = _cheapest_allowed_edges_sum(
                vertex,
                all_vertices_mask ^ (1 << vertex),
                2,
                distances,
                incident_vertices,
            )
            if contribution is None:
                return None
            contribution_sum += contribution
        return (contribution_sum + 1) // 2

    # Cada aresta fixa aparece na contribuição das duas pontas, portanto
    # 2 * cost_so_far já incorpora toda a rota parcial na soma dos vértices.
    contribution_sum = 2 * cost_so_far
    origin_contribution = _cheapest_allowed_edges_sum(
        0, remaining_mask, 1, distances, incident_vertices
    )
    current_contribution = _cheapest_allowed_edges_sum(
        current, remaining_mask, 1, distances, incident_vertices
    )
    if origin_contribution is None or current_contribution is None:
        return None
    contribution_sum += origin_contribution + current_contribution

    pending = remaining_mask
    while pending:
        vertex_bit = pending & -pending
        vertex = vertex_bit.bit_length() - 1
        allowed_mask = (remaining_mask ^ vertex_bit) | 1 | (1 << current)
        contribution = _cheapest_allowed_edges_sum(
            vertex, allowed_mask, 2, distances, incident_vertices
        )
        if contribution is None:
            return None
        contribution_sum += contribution
        pending ^= vertex_bit

    return (contribution_sum + 1) // 2


def solve_branch_and_bound(
    instance: TSPInstance,
    initial_route_strategy: InitialRouteStrategy = trivial_initial_route,
    *,
    time_limit_seconds: float | None = None,
    progress_callback: ProgressCallback | None = None,
    checkpoint_interval_seconds: float = 30.0,
    phase_memory_query: MemoryQuery | None = None,
) -> BranchAndBoundResult:
    """Resolve ``instance`` por Branch-and-Bound best-first.

    O primeiro vértice fica fixo e os estados são priorizados pelo limite das
    duas arestas incidentes por vértice apresentado na Aula 12, respeitando as
    arestas fixas e proibidas pela rota parcial. O prazo é verificado em pontos
    seguros do laço principal e da geração de filhos. Ao expirar, a função
    devolve a melhor solução viável já encontrada e ``status="timeout"``.

    Args:
        instance: Instância com matriz de custos já calculada.
        initial_route_strategy: Estratégia que produz a incumbente inicial.
        time_limit_seconds: Prazo monotônico para inicialização mais busca.
            ``None`` desabilita o prazo; zero provoca timeout cooperativo assim
            que a rota inicial estiver disponível.
        progress_callback: Função opcional que persiste um retrato da busca.
        checkpoint_interval_seconds: Intervalo monotônico entre retratos.
        phase_memory_query: Consulta opcional do pico residente do processo,
            usada para observar a memória depois das fases das aproximações.

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

    with collect_approximation_profile(phase_memory_query) as approximation_profile:
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

    mst_profile = approximation_profile.value("mst")
    matching_profile = approximation_profile.value("matching")
    eulerian_profile = approximation_profile.value("eulerian_circuit")
    shortcut_profile = approximation_profile.value("shortcut")

    generated_nodes = 0
    expanded_nodes = 0
    pruned_nodes = 0
    max_depth = 0
    lower_bound_calls = 0
    lower_bound_seconds = 0.0
    checkpoint_calls = 0
    checkpoint_seconds = 0.0
    incident_vertices: tuple[tuple[int, ...], ...] | None = None
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
            generated_nodes=generated_nodes,
            expanded_nodes=expanded_nodes,
            pruned_nodes=pruned_nodes,
            max_depth=max_depth,
            initialization_seconds=initialization_seconds,
            search_seconds=measured_at - search_started,
            solver_total_seconds=measured_at - solver_started,
            lower_bound_calls=lower_bound_calls,
            lower_bound_seconds=lower_bound_seconds,
            checkpoint_calls=checkpoint_calls,
            checkpoint_seconds=checkpoint_seconds,
            mst_calls=mst_profile.calls,
            mst_seconds=mst_profile.seconds,
            mst_process_peak_bytes=mst_profile.process_peak_bytes,
            matching_calls=matching_profile.calls,
            matching_seconds=matching_profile.seconds,
            matching_process_peak_bytes=matching_profile.process_peak_bytes,
            eulerian_circuit_calls=eulerian_profile.calls,
            eulerian_circuit_seconds=eulerian_profile.seconds,
            eulerian_circuit_process_peak_bytes=eulerian_profile.process_peak_bytes,
            shortcut_calls=shortcut_profile.calls,
            shortcut_seconds=shortcut_profile.seconds,
            shortcut_process_peak_bytes=shortcut_profile.process_peak_bytes,
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

    def lower_bound(current: int, remaining_mask: int, cost_so_far: int) -> int:
        """Limita inferiormente uma extensão e mede a chamada completa."""

        nonlocal incident_vertices, lower_bound_calls, lower_bound_seconds
        lower_bound_calls += 1
        call_started = perf_counter()
        try:
            check_deadline(call_started)
            if remaining_mask == 0:
                return cost_so_far + distances[current][0]
            if incident_vertices is None:
                incident_vertices = _incident_vertices_by_cost(distances)
            bound = _two_edges_lower_bound(
                distances,
                incident_vertices,
                current,
                remaining_mask,
                cost_so_far,
            )
            # Um estado inviável pode ser podado com segurança usando o limite
            # superior corrente. Como a incumbente só diminui, ele continuará
            # podável quando sair da fila.
            return best_cost if bound is None else bound
        finally:
            lower_bound_seconds += perf_counter() - call_started

    status: SolverStatus = "optimal"
    try:
        maybe_checkpoint(force=True)
        check_deadline()
        all_except_origin = ((1 << dimension) - 1) ^ 1
        root_bound = lower_bound(0, all_except_origin, 0)
        insertion_order = count()
        root_node = _RouteNode(vertex=0, parent=None, depth=0)
        # Prefixos que chegam ao mesmo (vértice atual, conjunto restante)
        # possuem exatamente as mesmas continuações. Logo, somente o menor
        # custo parcial pode levar a uma solução melhor.
        best_state_cost: dict[tuple[int, int], int] = {(0, all_except_origin): 0}
        frontier: list[tuple[int, int, int, int, _RouteNode]] = []
        heappush(
            frontier,
            (root_bound, next(insertion_order), all_except_origin, 0, root_node),
        )
        generated_nodes += 1

        while frontier:
            check_deadline()
            maybe_checkpoint()
            bound, _, remaining_mask, cost_so_far, route_node = heappop(frontier)
            current = route_node.vertex

            # Uma rota de menor custo pode ter alcançado o mesmo estado depois
            # que esta entrada foi inserida na heap.
            if cost_so_far != best_state_cost.get((current, remaining_mask)):
                pruned_nodes += 1
                continue

            if bound >= best_cost:
                # Como este é o menor limite da heap, toda a fronteira restante
                # também está provadamente dominada pela incumbente.
                pruned_nodes += len(frontier) + 1
                break

            if remaining_mask == 0:
                best_cost = bound
                best_route = _materialize_route(route_node)
                continue

            expanded_nodes += 1
            for next_vertex in range(1, dimension):
                check_deadline()
                next_bit = 1 << next_vertex
                if not remaining_mask & next_bit:
                    continue

                child_remaining = remaining_mask ^ next_bit
                child_cost = cost_so_far + distances[current][next_vertex]
                child_depth = route_node.depth + 1
                max_depth = max(max_depth, child_depth)
                generated_nodes += 1

                child_state = (next_vertex, child_remaining)
                previous_cost = best_state_cost.get(child_state)
                if previous_cost is not None and child_cost >= previous_cost:
                    pruned_nodes += 1
                    continue
                best_state_cost[child_state] = child_cost

                child_bound = lower_bound(next_vertex, child_remaining, child_cost)
                if child_bound >= best_cost:
                    pruned_nodes += 1
                    continue

                child_node = _RouteNode(
                    vertex=next_vertex,
                    parent=route_node,
                    depth=child_depth,
                )
                heappush(
                    frontier,
                    (
                        child_bound,
                        next(insertion_order),
                        child_remaining,
                        child_cost,
                        child_node,
                    ),
                )
    except _DeadlineExceeded:
        status = "timeout"

    return make_result(status)
