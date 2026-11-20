import csv
import hashlib
import json
from pathlib import Path

from traveling_salesman_optimization.empirical_analysis import (
    analyze_results,
    extract_instance_features,
)
from traveling_salesman_optimization.tsplib import read_tsplib


def _write_instance(path: Path, coordinates: tuple[tuple[float, float], ...]) -> Path:
    coordinate_lines = "\n".join(
        f"{index} {x} {y}" for index, (x, y) in enumerate(coordinates, start=1)
    )
    path.write_text(
        f"""NAME: analysis
TYPE: TSP
DIMENSION: {len(coordinates)}
EDGE_WEIGHT_TYPE: EUC_2D
NODE_COORD_SECTION
{coordinate_lines}
EOF
""",
        encoding="utf-8",
    )
    return path


def test_features_include_geometry_topology_and_metric_audit(tmp_path: Path) -> None:
    square = read_tsplib(
        _write_instance(tmp_path / "square.tsp", ((0, 0), (10, 0), (10, 10), (0, 10)))
    )
    nonmetric = read_tsplib(_write_instance(tmp_path / "line.tsp", ((0, 0), (1.49, 0), (2.98, 0))))

    square_features = extract_instance_features(square)
    nonmetric_features = extract_instance_features(nonmetric)

    assert square_features.aspect_ratio == 1.0
    assert square_features.convex_hull_fraction == 1.0
    assert square_features.mst_max_degree == 2
    assert square_features.nearest_neighbor_cv == 0.0
    assert square_features.triangle_violation_count == 0
    assert nonmetric_features.aspect_ratio is None
    assert nonmetric_features.triangle_violation_count == 1


def test_analysis_uses_only_certified_optima_and_compares_strategies(tmp_path: Path) -> None:
    instance_path = _write_instance(
        tmp_path / "square.tsp",
        ((0, 0), (10, 0), (10, 10), (0, 10)),
    )
    digest = hashlib.sha256(instance_path.read_bytes()).hexdigest()
    csv_path = tmp_path / "results.csv"
    fields = [
        "instance_path",
        "instance_sha256",
        "instance_name",
        "dimension",
        "initialization_strategy",
        "repetition",
        "status",
        "initial_route_cost",
        "best_route_cost",
        "optimal_cost",
        "initialization_seconds",
        "solver_total_seconds",
        "peak_memory_bytes",
        "generated_nodes",
        "expanded_nodes",
        "pruned_nodes",
    ]
    rows = [
        {
            "instance_path": str(instance_path),
            "instance_sha256": digest,
            "instance_name": "square",
            "dimension": 4,
            "initialization_strategy": "trivial",
            "repetition": 1,
            "status": "optimal",
            "initial_route_cost": 48,
            "best_route_cost": 40,
            "optimal_cost": 40,
            "initialization_seconds": 0.001,
            "solver_total_seconds": 0.01,
            "peak_memory_bytes": 1000,
            "generated_nodes": 10,
            "expanded_nodes": 5,
            "pruned_nodes": 4,
        },
        {
            "instance_path": str(instance_path),
            "instance_sha256": digest,
            "instance_name": "square",
            "dimension": 4,
            "initialization_strategy": "christofides",
            "repetition": 1,
            "status": "timeout",
            "initial_route_cost": 44,
            "best_route_cost": 44,
            "optimal_cost": "NA",
            "initialization_seconds": 0.002,
            "solver_total_seconds": 1.0,
            "peak_memory_bytes": 1100,
            "generated_nodes": 12,
            "expanded_nodes": 6,
            "pruned_nodes": 3,
        },
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    output_dir = tmp_path / "analysis"
    summary = analyze_results([csv_path], output_dir)

    with (output_dir / "enriched_results.csv").open(encoding="utf-8", newline="") as source:
        enriched = list(csv.DictReader(source))
    timeout = next(row for row in enriched if row["status"] == "timeout")

    assert timeout["reference_optimal_cost"] == "40.0"
    assert timeout["reference_optimal_source"] == "certified_peer_run"
    assert float(timeout["initial_gap_percent"]) == 10.0
    assert summary["nonmetric_instances"] == 0
    assert summary["warm_start_comparison"]["paired_instance_repetition_groups"] == 1
    assert json.loads((output_dir / "summary.json").read_text(encoding="utf-8")) == summary
