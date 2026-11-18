"""Interface de linha de comando do solver exato."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from traveling_salesman_optimization.branch_and_bound import solve_branch_and_bound
from traveling_salesman_optimization.tsplib import read_tsplib


def main(arguments: Sequence[str] | None = None) -> int:
    """Executa a interface de linha de comando para uma instância TSPLIB.

    Args:
        arguments: Argumentos sem o nome do programa. Quando ``None``, o
            ``argparse`` usa ``sys.argv``.

    Returns:
        Zero depois que a instância é resolvida e o resultado é impresso.
    """

    parser = argparse.ArgumentParser(
        description="Resolve uma instância TSPLIB EUC_2D por Branch-and-Bound."
    )
    parser.add_argument("instance", help="caminho para o arquivo .tsp")
    args = parser.parse_args(arguments)

    instance = read_tsplib(args.instance)
    result = solve_branch_and_bound(instance)
    print(f"instância: {instance.name}")
    print(f"custo: {result.cost}")
    print("rota: " + " -> ".join(map(str, result.route)))
    print(f"nós expandidos: {result.expanded_nodes}")
    print(f"nós podados: {result.pruned_nodes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
