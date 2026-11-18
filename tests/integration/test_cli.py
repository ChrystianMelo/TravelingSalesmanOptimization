from pathlib import Path

from traveling_salesman_optimization.main import main


def test_cli_prints_solution(tmp_path: Path, capsys: object) -> None:
    instance_path = tmp_path / "crossing.tsp"
    instance_path.write_text(
        """NAME: crossing
TYPE: TSP
DIMENSION: 4
EDGE_WEIGHT_TYPE: EUC_2D
NODE_COORD_SECTION
100 0 0
8 10 10
55 0 10
21 10 0
EOF
""",
        encoding="utf-8",
    )

    assert main([str(instance_path)]) == 0

    output = capsys.readouterr().out  # type: ignore[attr-defined]
    assert "instância: crossing" in output
    assert "custo: 40" in output
    assert "rota: 100" in output
    assert "nós expandidos:" in output
    assert "nós podados:" in output
