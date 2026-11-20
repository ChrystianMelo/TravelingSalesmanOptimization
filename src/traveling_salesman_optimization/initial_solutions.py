"""As cinco estratégias de warm-start exigidas para o Branch-and-Bound."""

from collections.abc import Sequence
from typing import Protocol

from traveling_salesman_optimization.approximation import (
    christofides_route,
    twice_around_tree_route,
)
from traveling_salesman_optimization.tsplib import TSPInstance


class InitialRouteStrategy(Protocol):
    """Contrato para uma estratégia substituível de limite superior.

    A estratégia deve retornar uma permutação dos índices internos da
    instância. O solver valida a permutação, gira o ciclo para fixar o índice
    zero como origem e calcula o custo com a função centralizada.
    """

    def __call__(self, instance: TSPInstance) -> Sequence[int]: ...


def trivial_initial_route(instance: TSPInstance) -> tuple[int, ...]:
    """Cria o cold start ``0, 1, ..., n - 1`` na ordem do arquivo.

    Args:
        instance: Instância cuja dimensão determina os índices da rota.

    Returns:
        Permutação trivial dos índices, sem repetir a origem no fim.
    """

    return tuple(range(instance.dimension))


def nearest_neighbor_initial_route(instance: TSPInstance) -> tuple[int, ...]:
    """Aplica a busca gulosa do Vizinho Mais Próximo a partir do índice zero.

    A cada passo é escolhido o vértice ainda não visitado de menor distância
    ao último. Empates são resolvidos pelo menor índice interno.

    Args:
        instance: Instância com a matriz de custos pronta.

    Returns:
        Permutação gulosa dos índices, sem repetir a origem no fim.
    """

    if instance.dimension == 0:
        return ()
    route = [0]
    unvisited = set(range(1, instance.dimension))
    while unvisited:
        current = route[-1]
        nearest = min(unvisited, key=lambda vertex: (instance.distances[current][vertex], vertex))
        route.append(nearest)
        unvisited.remove(nearest)
    return tuple(route)


def _cross_product(
    origin: tuple[float, float],
    first: tuple[float, float],
    second: tuple[float, float],
) -> float:
    """Retorna o produto vetorial de ``origin->first`` e ``origin->second``."""

    return (first[0] - origin[0]) * (second[1] - origin[1]) - (first[1] - origin[1]) * (
        second[0] - origin[0]
    )


def _convex_hull_vertices(instance: TSPInstance) -> tuple[int, ...]:
    """Encontra o fecho convexo por cadeia monotônica em ``O(n log n)``.

    Pontos colineares no interior de uma aresta e vértices com coordenadas
    duplicadas ficam fora da semente e são posteriormente inseridos pela
    heurística. Isso mantém um ciclo simples e garante que todos os índices
    originais ainda apareçam exatamente uma vez na rota final.
    """

    ordered_vertices = sorted(
        range(instance.dimension),
        key=lambda vertex: (*instance.coordinates[vertex], vertex),
    )
    unique_vertices: list[int] = []
    seen_coordinates: set[tuple[float, float]] = set()
    for vertex in ordered_vertices:
        coordinate = instance.coordinates[vertex]
        if coordinate not in seen_coordinates:
            seen_coordinates.add(coordinate)
            unique_vertices.append(vertex)

    if len(unique_vertices) <= 1:
        return tuple(unique_vertices)

    def half_hull(vertices: list[int]) -> list[int]:
        hull: list[int] = []
        for vertex in vertices:
            while (
                len(hull) >= 2
                and _cross_product(
                    instance.coordinates[hull[-2]],
                    instance.coordinates[hull[-1]],
                    instance.coordinates[vertex],
                )
                <= 0
            ):
                hull.pop()
            hull.append(vertex)
        return hull

    lower = half_hull(unique_vertices)
    upper = half_hull(list(reversed(unique_vertices)))
    return tuple(lower[:-1] + upper[:-1])


def convex_hull_insertion_initial_route(instance: TSPInstance) -> tuple[int, ...]:
    """Insere gulosamente os demais vértices no ciclo do fecho convexo.

    Em cada iteração, a busca considera todos os pares formados por um
    vértice restante e uma aresta do ciclo. É feita a inserção que causa o
    menor acréscimo ``d(a,v) + d(v,b) - d(a,b)`` no custo. Vértice e posição
    da aresta resolvem empates de modo determinístico.

    Args:
        instance: Instância geométrica com coordenadas e custos.

    Returns:
        Permutação dos índices, rotacionada para começar em zero.
    """

    if instance.dimension == 0:
        return ()
    route = list(_convex_hull_vertices(instance))
    if not route:
        route.append(0)
    remaining = set(range(instance.dimension)) - set(route)

    while remaining:
        increase, vertex, edge_position = min(
            (
                instance.distances[route[position]][candidate]
                + instance.distances[candidate][route[(position + 1) % len(route)]]
                - instance.distances[route[position]][route[(position + 1) % len(route)]],
                candidate,
                position,
            )
            for candidate in remaining
            for position in range(len(route))
        )
        del increase  # O valor escolhe a inserção, mas não precisa ser acumulado.
        route.insert(edge_position + 1, vertex)
        remaining.remove(vertex)

    origin_position = route.index(0)
    return tuple(route[origin_position:] + route[:origin_position])


# O executor resolve nomes para funções por este registro, sem condicionais no
# solver ou no worker. Os nomes também são persistidos nos resultados.
INITIAL_ROUTE_STRATEGIES: dict[str, InitialRouteStrategy] = {
    "christofides": christofides_route,
    "convex_hull": convex_hull_insertion_initial_route,
    "nearest_neighbor": nearest_neighbor_initial_route,
    "trivial": trivial_initial_route,
    "twice_around_tree": twice_around_tree_route,
}
