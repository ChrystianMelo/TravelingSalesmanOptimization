"""Algoritmos aproximativos usados como warm-start do TSP geométrico.

As rotas usam índices internos, começam no índice zero e não repetem a
origem no fim. O custo deve ser calculado pela matriz ``EUC_2D`` centralizada
em :mod:`traveling_salesman_optimization.tsplib`.
"""

from __future__ import annotations

from math import inf

import networkx as nx

from traveling_salesman_optimization.phase_profiling import profiled_phase
from traveling_salesman_optimization.tsplib import DistanceMatrix, TSPInstance

Edge = tuple[int, int]


@profiled_phase("mst")
def _minimum_spanning_tree_edges(distances: DistanceMatrix) -> tuple[Edge, ...]:
    """Calcula uma AGM por Prim denso em ``O(n²)`` tempo e ``O(n)`` espaço.

    A matriz do TSP representa um grafo completo, portanto uma fila de
    prioridade não reduz o custo quadrático de examinar as arestas. Em caso de
    empate, o menor vértice e depois o menor pai são escolhidos para que os
    experimentos sejam reproduzíveis.

    Args:
        distances: Matriz simétrica de custos do grafo completo.

    Returns:
        Arestas ``(pai, filho)`` da árvore enraizada no vértice zero.

    Raises:
        ValueError: Se a matriz não for quadrada.
    """

    dimension = len(distances)
    if any(len(row) != dimension for row in distances):
        raise ValueError("a matriz de distâncias deve ser quadrada")
    if dimension <= 1:
        return ()

    in_tree = [False] * dimension
    cheapest_connection = [inf] * dimension
    parent = [-1] * dimension
    cheapest_connection[0] = 0
    tree_edges: list[Edge] = []

    for _ in range(dimension):
        vertex = min(
            (candidate for candidate in range(dimension) if not in_tree[candidate]),
            key=lambda candidate: (cheapest_connection[candidate], candidate),
        )
        in_tree[vertex] = True
        if parent[vertex] != -1:
            tree_edges.append((parent[vertex], vertex))

        for target in range(dimension):
            if in_tree[target]:
                continue
            weight = distances[vertex][target]
            if weight < cheapest_connection[target] or (
                weight == cheapest_connection[target]
                and (parent[target] == -1 or vertex < parent[target])
            ):
                cheapest_connection[target] = weight
                parent[target] = vertex

    return tuple(tree_edges)


def twice_around_tree_route(instance: TSPInstance) -> tuple[int, ...]:
    """Constrói a rota 2-aproximada ``twice-around-the-tree``.

    A função calcula uma árvore geradora mínima, duplica suas arestas,
    constrói explicitamente o circuito euleriano por Hierholzer e elimina
    visitas repetidas por atalhos. Para custos métricos, seu custo é no máximo
    duas vezes o ótimo.

    Args:
        instance: Instância geométrica com a matriz de custos pronta.

    Returns:
        Permutação dos índices internos, iniciada em zero.
    """

    dimension = instance.dimension
    tree_edges = _minimum_spanning_tree_edges(instance.distances)
    duplicated_tree_edges = tuple(edge for edge in tree_edges for _ in range(2))
    eulerian_circuit = _eulerian_circuit(dimension, duplicated_tree_edges)
    return _eulerian_to_hamiltonian(eulerian_circuit, dimension)


@profiled_phase("matching")
def _minimum_weight_perfect_matching(
    odd_vertices: tuple[int, ...], distances: DistanceMatrix
) -> tuple[Edge, ...]:
    """Emparelha perfeitamente os vértices ímpares com peso total mínimo.

    O conjunto possui cardinalidade par pelo lema do aperto de mãos. O grafo
    completo induzido é entregue ao Blossom do NetworkX, que encontra um
    emparelhamento de cardinalidade máxima e, entre eles, o de peso mínimo.

    Args:
        odd_vertices: Vértices de grau ímpar da AGM.
        distances: Matriz de custos usada como peso das arestas.

    Returns:
        Pares normalizados e ordenados, um por aresta do emparelhamento.

    Raises:
        ValueError: Se a quantidade de vértices for ímpar ou houver repetição.
        RuntimeError: Se a biblioteca não devolver um emparelhamento perfeito.
    """

    if len(odd_vertices) % 2:
        raise ValueError("um emparelhamento perfeito exige cardinalidade par")
    if len(set(odd_vertices)) != len(odd_vertices):
        raise ValueError("os vértices do emparelhamento devem ser distintos")
    if not odd_vertices:
        return ()

    graph = nx.Graph()
    graph.add_nodes_from(odd_vertices)
    for position, source in enumerate(odd_vertices):
        for target in odd_vertices[position + 1 :]:
            graph.add_edge(source, target, weight=distances[source][target])

    matching = nx.algorithms.matching.min_weight_matching(graph, weight="weight")
    if len(matching) * 2 != len(odd_vertices):
        raise RuntimeError("não foi possível construir um emparelhamento perfeito")
    return tuple(sorted((min(source, target), max(source, target)) for source, target in matching))


@profiled_phase("eulerian_circuit")
def _eulerian_circuit(dimension: int, edges: tuple[Edge, ...]) -> tuple[int, ...]:
    """Constrói por Hierholzer um circuito euleriano em um multigrafo.

    IDs próprios de aresta distinguem arestas paralelas da AGM e do matching.
    A lista retornada repete o vértice zero no fim quando há alguma aresta.
    """

    if dimension == 0:
        return ()
    if not edges:
        return (0,)

    adjacency: list[list[tuple[int, int]]] = [[] for _ in range(dimension)]
    for edge_id, (source, target) in enumerate(edges):
        adjacency[source].append((target, edge_id))
        adjacency[target].append((source, edge_id))
    for neighbors in adjacency:
        neighbors.sort(key=lambda item: (item[0], item[1]), reverse=True)

    used_edge = [False] * len(edges)
    stack = [0]
    reverse_circuit: list[int] = []
    while stack:
        vertex = stack[-1]
        while adjacency[vertex] and used_edge[adjacency[vertex][-1][1]]:
            adjacency[vertex].pop()
        if not adjacency[vertex]:
            reverse_circuit.append(stack.pop())
            continue
        neighbor, edge_id = adjacency[vertex].pop()
        if not used_edge[edge_id]:
            used_edge[edge_id] = True
            stack.append(neighbor)

    if not all(used_edge):
        raise RuntimeError("o multigrafo euleriano deve ser conexo")
    return tuple(reversed(reverse_circuit))


@profiled_phase("shortcut")
def _eulerian_to_hamiltonian(circuit: tuple[int, ...], dimension: int) -> tuple[int, ...]:
    """Remove repetições de um circuito euleriano por ``shortcutting``.

    Somente a primeira ocorrência de cada vértice é mantida. A origem que
    fecha o circuito euleriano não é repetida na rota retornada, seguindo a
    representação interna do projeto.

    Args:
        circuit: Sequência de vértices do circuito euleriano.
        dimension: Quantidade de vértices que a rota deve conter.

    Returns:
        Permutação na ordem da primeira visita de cada vértice.

    Raises:
        ValueError: Se a dimensão for negativa ou o circuito contiver um
            vértice fora do intervalo esperado.
        RuntimeError: Se o circuito não visitar todos os vértices.
    """

    if dimension < 0:
        raise ValueError("a dimensão não pode ser negativa")

    route: list[int] = []
    visited = [False] * dimension
    for vertex in circuit:
        if vertex < 0 or vertex >= dimension:
            raise ValueError("o circuito euleriano contém um vértice inválido")
        if not visited[vertex]:
            visited[vertex] = True
            route.append(vertex)

    if len(route) != dimension:
        raise RuntimeError("o circuito euleriano não visitou todos os vértices")
    return tuple(route)


def christofides_route(instance: TSPInstance) -> tuple[int, ...]:
    """Constrói uma rota pela aproximação de Christofides.

    São executadas as quatro etapas da Aula 13: AGM; matching perfeito mínimo
    entre os vértices de grau ímpar; circuito euleriano no multigrafo formado
    pela união; e remoção das repetições por atalhos. Para custos métricos,
    a rota custa no máximo ``1,5`` vez o ótimo.

    Args:
        instance: Instância geométrica com a matriz de custos pronta.

    Returns:
        Permutação dos índices internos, iniciada em zero.

    Raises:
        RuntimeError: Se alguma invariância da construção for violada.
    """

    dimension = instance.dimension
    if dimension <= 1:
        return tuple(range(dimension))

    tree_edges = _minimum_spanning_tree_edges(instance.distances)
    degrees = [0] * dimension
    for source, target in tree_edges:
        degrees[source] += 1
        degrees[target] += 1
    odd_vertices = tuple(vertex for vertex, degree in enumerate(degrees) if degree % 2)
    matching = _minimum_weight_perfect_matching(odd_vertices, instance.distances)
    matched_vertices = tuple(vertex for edge in matching for vertex in edge)
    if len(matched_vertices) != len(set(matched_vertices)) or set(matched_vertices) != set(
        odd_vertices
    ):
        raise RuntimeError("o matching deve cobrir cada vértice ímpar exatamente uma vez")
    eulerian_circuit = _eulerian_circuit(dimension, tree_edges + matching)
    return _eulerian_to_hamiltonian(eulerian_circuit, dimension)
