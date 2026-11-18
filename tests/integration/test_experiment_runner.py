import csv
from pathlib import Path

from traveling_salesman_optimization.experiment_runner import main
from traveling_salesman_optimization.tsplib import read_tsplib

INSTANCE_TEXT = """NAME: crossing
TYPE: TSP
DIMENSION: 4
EDGE_WEIGHT_TYPE: EUC_2D
NODE_COORD_SECTION
100 0 0
8 10 10
55 0 10
21 10 0
EOF
"""


def _write_instance(path: Path, contents: str = INSTANCE_TEXT) -> Path:
    path.write_text(contents, encoding="utf-8")
    return path


def _read_rows(output_dir: Path) -> list[dict[str, str]]:
    with (output_dir / "results.csv").open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def _read_tour(path: Path) -> tuple[int, ...]:
    lines = path.read_text(encoding="utf-8").splitlines()
    start = lines.index("TOUR_SECTION") + 1
    end = lines.index("-1", start)
    return tuple(int(value) for value in lines[start:end])


def _common_arguments(instance: Path, output_dir: Path) -> list[str]:
    return [
        str(instance),
        "--output-dir",
        str(output_dir),
        "--timeout-seconds",
        "5",
        "--checkpoint-interval-seconds",
        "0.01",
        "--external-grace-seconds",
        "3",
    ]


def test_runner_collects_resumes_and_explicitly_reruns(tmp_path: Path) -> None:
    instance_path = _write_instance(tmp_path / "crossing.tsp")
    output_dir = tmp_path / "results"
    arguments = _common_arguments(instance_path, output_dir)

    assert main(arguments) == 0
    first_csv = (output_dir / "results.csv").read_bytes()
    rows = _read_rows(output_dir)
    assert len(rows) == 1
    row = rows[0]
    assert row["status"] == "optimal"
    assert row["initialization_strategy"] == "trivial"
    assert row["dimension"] == "4"
    assert row["initial_route_cost"] == "48"
    assert row["best_route_cost"] == row["optimal_cost"] == "40"
    assert int(row["peak_memory_bytes"]) > 0
    assert row["memory_unit"] == "bytes"
    assert int(row["lower_bound_calls"]) > 0
    assert int(row["mst_calls"]) > 0
    assert Path(output_dir / row["checkpoint_file"]).is_file()
    assert Path(output_dir / row["result_file"]).is_file()

    route = _read_tour(output_dir / row["route_file"])
    instance = read_tsplib(instance_path)
    index_by_id = {vertex_id: index for index, vertex_id in enumerate(instance.vertex_ids)}
    assert instance.route_cost(tuple(index_by_id[vertex_id] for vertex_id in route)) == 40

    assert main(arguments) == 0
    assert (output_dir / "results.csv").read_bytes() == first_csv

    assert main([*arguments, "--rerun"]) == 0
    assert len(_read_rows(output_dir)) == 1
    assert len(list((output_dir / "configurations").glob("*.json"))) == 1
    assert len(list((output_dir / "invocations").glob("*.json"))) == 3


def test_timeout_keeps_partial_metrics_and_feasible_route(tmp_path: Path) -> None:
    instance_path = _write_instance(tmp_path / "crossing.tsp")
    output_dir = tmp_path / "timeout-results"
    arguments = _common_arguments(instance_path, output_dir)
    timeout_position = arguments.index("5")
    arguments[timeout_position] = "0"

    assert main(arguments) == 0
    row = _read_rows(output_dir)[0]
    assert row["status"] == "timeout"
    assert row["optimal_cost"] == "NA"
    assert row["initial_route_cost"] == row["best_route_cost"] == "48"
    assert row["expanded_nodes"] == row["pruned_nodes"] == "0"
    assert float(row["solver_total_seconds"]) >= 0

    route = _read_tour(output_dir / row["route_file"])
    instance = read_tsplib(instance_path)
    index_by_id = {vertex_id: index for index, vertex_id in enumerate(instance.vertex_ids)}
    assert instance.route_cost(tuple(index_by_id[vertex_id] for vertex_id in route)) == 48


def test_individual_failure_is_recorded_and_batch_continues(tmp_path: Path) -> None:
    instances = tmp_path / "instances"
    instances.mkdir()
    _write_instance(instances / "good.tsp")
    _write_instance(instances / "bad.tsp", "not a TSPLIB instance\n")
    output_dir = tmp_path / "mixed-results"

    assert main(_common_arguments(instances, output_dir)) == 1
    rows = _read_rows(output_dir)
    assert len(rows) == 2
    assert {row["status"] for row in rows} == {"error", "optimal"}
    error = next(row for row in rows if row["status"] == "error")
    assert error["error_type"] == "ValueError"
    assert error["optimal_cost"] == "NA"
