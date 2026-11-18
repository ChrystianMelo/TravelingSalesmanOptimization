"""Estratégias substituíveis para inicializar o limite superior."""

from collections.abc import Sequence
from typing import Protocol

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


# O executor resolve nomes para funções por este registro. Novas estratégias
# entram pela mesma interface sem exigir condicionais no solver ou no worker.
INITIAL_ROUTE_STRATEGIES: dict[str, InitialRouteStrategy] = {
    "trivial": trivial_initial_route,
}
