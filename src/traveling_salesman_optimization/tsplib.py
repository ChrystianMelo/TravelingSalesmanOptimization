"""Leitura de instâncias TSPLIB EUC_2D e cálculo centralizado de custos."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from math import hypot
from pathlib import Path

DistanceMatrix = tuple[tuple[int, ...], ...]


@dataclass(frozen=True, slots=True)
class TSPInstance:
    """Representa uma instância geométrica e sua matriz de custos.

    ``vertex_ids[i]``, ``coordinates[i]`` e ``distances[i]`` se referem ao
    mesmo vértice. Os IDs originais não são renumerados; os algoritmos usam
    internamente os índices de ``0`` a ``dimension - 1``.

    Attributes:
        name: Nome declarado no arquivo TSPLIB.
        vertex_ids: IDs originais, na ordem de ``NODE_COORD_SECTION``.
        coordinates: Pares ``(x, y)`` na mesma ordem dos IDs.
        distances: Matriz simétrica de custos inteiros, com diagonal zero.
    """

    name: str
    vertex_ids: tuple[int, ...]
    coordinates: tuple[tuple[float, float], ...]
    distances: DistanceMatrix

    @property
    def dimension(self) -> int:
        return len(self.vertex_ids)

    def route_cost(self, route: Sequence[int]) -> int:
        """Calcula o custo de uma rota dada por índices internos.

        Args:
            route: Sequência de índices da matriz. A origem não precisa ser
                repetida no fim.

        Returns:
            Soma das arestas consecutivas e da aresta de retorno à origem.
        """

        return calculate_route_cost(self.distances, route)


def calculate_route_cost(distances: DistanceMatrix, route: Sequence[int]) -> int:
    """Calcula o custo de um ciclo sobre uma matriz de distâncias.

    Args:
        distances: Matriz quadrada em que ``distances[i][j]`` é o custo da
            aresta entre os índices ``i`` e ``j``.
        route: Índices na ordem de visita. A função fecha o ciclo
            implicitamente; portanto, a representação usual não repete a
            origem no fim.

    Returns:
        Custo total do ciclo. Rotas vazias ou unitárias custam zero.

    Raises:
        IndexError: Se algum índice da rota não existir na matriz.
    """

    if len(route) < 2:
        return 0
    return (
        sum(distances[source][target] for source, target in zip(route, route[1:], strict=False))
        + (distances[route[-1]][route[0]])
    )


def _build_distance_matrix(
    coordinates: Sequence[tuple[float, float]],
) -> DistanceMatrix:
    """Constrói a matriz EUC_2D simétrica em tempo e espaço quadráticos.

    Cada custo é calculado uma única vez por ``int(hypot(dx, dy) + 0.5)``,
    que é a regra ``nint`` da TSPLIB, e copiado para a posição simétrica.

    Args:
        coordinates: Coordenadas na ordem original dos vértices.

    Returns:
        Matriz imutável de custos inteiros com diagonal zero.
    """

    dimension = len(coordinates)
    matrix = [[0] * dimension for _ in range(dimension)]
    for source in range(dimension):
        source_x, source_y = coordinates[source]
        for target in range(source + 1, dimension):
            target_x, target_y = coordinates[target]
            distance = int(hypot(source_x - target_x, source_y - target_y) + 0.5)
            matrix[source][target] = distance
            matrix[target][source] = distance
    return tuple(tuple(row) for row in matrix)


def _parse_header(line: str) -> tuple[str, str]:
    """Separa uma linha de cabeçalho TSPLIB, com ou sem dois-pontos."""

    if ":" in line:
        key, value = line.split(":", maxsplit=1)
    else:
        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            raise ValueError(f"cabeçalho TSPLIB inválido: {line!r}")
        key, value = parts
    return key.strip().upper(), value.strip()


def read_tsplib(path: str | Path) -> TSPInstance:
    """Lê e valida uma instância TSPLIB ``EUC_2D``.

    IDs e ordem das linhas de ``NODE_COORD_SECTION`` são preservados. Campos
    desconhecidos do cabeçalho são aceitos, como permite o formato. A matriz
    completa de distâncias é construída uma vez durante a leitura para que
    todos os algoritmos usem exatamente os mesmos custos.

    Args:
        path: Caminho do arquivo ``.tsp``, codificado em UTF-8 com ou sem BOM.

    Returns:
        Instância com IDs, coordenadas e matriz na ordem do arquivo.

    Raises:
        ValueError: Se o arquivo não puder ser lido, se não for ``EUC_2D``,
            se faltar uma seção obrigatória, se houver IDs duplicados ou se
            ``DIMENSION`` divergir da quantidade de coordenadas.
    """

    source = Path(path)
    headers: dict[str, str] = {}
    vertex_ids: list[int] = []
    coordinates: list[tuple[float, float]] = []
    in_coordinates = False

    try:
        lines = source.read_text(encoding="utf-8-sig").splitlines()
    except OSError as error:
        raise ValueError(f"não foi possível ler {source}: {error}") from error

    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line:
            continue
        upper_line = line.upper()
        if upper_line == "EOF":
            break
        if upper_line == "NODE_COORD_SECTION":
            in_coordinates = True
            continue

        if not in_coordinates:
            key, value = _parse_header(line)
            headers[key] = value
            continue

        fields = line.split()
        if len(fields) != 3:
            raise ValueError(f"linha {line_number}: coordenada deve conter ID, X e Y")
        try:
            vertex_id = int(fields[0])
            coordinate = (float(fields[1]), float(fields[2]))
        except ValueError as error:
            raise ValueError(f"linha {line_number}: coordenada inválida") from error
        vertex_ids.append(vertex_id)
        coordinates.append(coordinate)

    if not in_coordinates:
        raise ValueError("NODE_COORD_SECTION ausente")
    if headers.get("EDGE_WEIGHT_TYPE", "").upper() != "EUC_2D":
        raise ValueError("somente instâncias EDGE_WEIGHT_TYPE EUC_2D são aceitas")
    if not vertex_ids:
        raise ValueError("a instância não possui vértices")
    if len(set(vertex_ids)) != len(vertex_ids):
        raise ValueError("os IDs dos vértices devem ser únicos")

    try:
        declared_dimension = int(headers["DIMENSION"])
    except KeyError as error:
        raise ValueError("DIMENSION ausente") from error
    except ValueError as error:
        raise ValueError("DIMENSION deve ser um inteiro") from error
    if declared_dimension != len(vertex_ids):
        raise ValueError(
            f"DIMENSION declara {declared_dimension}, mas foram lidos {len(vertex_ids)} vértices"
        )

    coordinate_tuple = tuple(coordinates)
    return TSPInstance(
        name=headers.get("NAME", source.stem),
        vertex_ids=tuple(vertex_ids),
        coordinates=coordinate_tuple,
        distances=_build_distance_matrix(coordinate_tuple),
    )
