from pathlib import Path

import pytest

from traveling_salesman_optimization.tsplib import calculate_route_cost, read_tsplib


def write_tsplib_instance(tmp_path: Path, contents: str) -> Path:
    path = tmp_path / "instance.tsp"
    path.write_text(contents, encoding="utf-8")
    return path


def test_read_tsplib_preserves_ids_order_and_uses_tsplib_rounding(tmp_path: Path) -> None:
    path = write_tsplib_instance(
        tmp_path,
        """NAME: rounding
TYPE: TSP
DIMENSION: 3
EDGE_WEIGHT_TYPE: EUC_2D
NODE_COORD_SECTION
42 0 0
7 1 1
99 4 5
EOF
""",
    )

    instance = read_tsplib(path)

    assert instance.name == "rounding"
    assert instance.vertex_ids == (42, 7, 99)
    assert instance.coordinates == ((0.0, 0.0), (1.0, 1.0), (4.0, 5.0))
    assert instance.distances == ((0, 1, 6), (1, 0, 5), (6, 5, 0))
    assert instance.route_cost((0, 1, 2)) == 12
    assert calculate_route_cost(instance.distances, (0, 1, 2)) == 12


def test_read_tsplib_rejects_incompatible_instances(tmp_path: Path) -> None:
    invalid_instances = (
        (
            "DIMENSION: 1\nEDGE_WEIGHT_TYPE: MAN_2D\nNODE_COORD_SECTION\n1 0 0\n",
            "EUC_2D",
        ),
        (
            "DIMENSION: 2\nEDGE_WEIGHT_TYPE: EUC_2D\nNODE_COORD_SECTION\n1 0 0\n",
            "DIMENSION declara 2",
        ),
        (
            "DIMENSION: 2\nEDGE_WEIGHT_TYPE: EUC_2D\nNODE_COORD_SECTION\n1 0 0\n1 2 2\n",
            "IDs",
        ),
    )

    for contents, message in invalid_instances:
        with pytest.raises(ValueError, match=message):
            read_tsplib(write_tsplib_instance(tmp_path, contents))
