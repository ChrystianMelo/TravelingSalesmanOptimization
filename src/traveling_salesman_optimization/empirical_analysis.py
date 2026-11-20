"""Enriquece resultados com características geométricas e modelos estatísticos."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from math import ceil, log, sqrt
from pathlib import Path
from statistics import fmean, pstdev
from typing import Any

from traveling_salesman_optimization.approximation import _minimum_spanning_tree_edges
from traveling_salesman_optimization.experiment_io import atomic_write_json, atomic_write_text
from traveling_salesman_optimization.initial_solutions import _convex_hull_vertices
from traveling_salesman_optimization.tsplib import TSPInstance, read_tsplib

NA_VALUES = {"", "NA", "N/A", "None", "null"}
FEATURE_FIELDS = [
    "aspect_ratio",
    "convex_hull_fraction",
    "spatial_entropy",
    "mst_max_degree",
    "nearest_neighbor_cv",
    "triangle_violation_count",
    "triangle_violation_fraction",
]
DERIVED_FIELDS = [
    *FEATURE_FIELDS,
    "reference_optimal_cost",
    "reference_optimal_source",
    "initial_gap_percent",
    "best_gap_percent",
]


@dataclass(frozen=True, slots=True)
class InstanceFeatures:
    """Características com definições estáveis para a análise de sensibilidade."""

    aspect_ratio: float | None
    convex_hull_fraction: float
    spatial_entropy: float
    mst_max_degree: int
    nearest_neighbor_cv: float
    triangle_violation_count: int
    triangle_violation_fraction: float


def _aspect_ratio(instance: TSPInstance) -> float | None:
    xs = [coordinate[0] for coordinate in instance.coordinates]
    ys = [coordinate[1] for coordinate in instance.coordinates]
    width = max(xs) - min(xs)
    height = max(ys) - min(ys)
    smaller = min(width, height)
    larger = max(width, height)
    if larger == 0:
        return 1.0
    if smaller == 0:
        return None
    return larger / smaller


def _spatial_entropy(instance: TSPInstance) -> float:
    """Entropia de Shannon normalizada em grade ``ceil(sqrt(n))`` quadrada."""

    dimension = instance.dimension
    if dimension <= 1:
        return 0.0
    grid_size = ceil(sqrt(dimension))
    xs = [coordinate[0] for coordinate in instance.coordinates]
    ys = [coordinate[1] for coordinate in instance.coordinates]
    minimum_x, maximum_x = min(xs), max(xs)
    minimum_y, maximum_y = min(ys), max(ys)

    def cell(value: float, minimum: float, maximum: float) -> int:
        if maximum == minimum:
            return 0
        normalized = (value - minimum) / (maximum - minimum)
        return min(grid_size - 1, int(normalized * grid_size))

    occupied = Counter(
        (cell(x, minimum_x, maximum_x), cell(y, minimum_y, maximum_y))
        for x, y in instance.coordinates
    )
    entropy = -sum((count / dimension) * log(count / dimension) for count in occupied.values())
    maximum_entropy = log(min(dimension, grid_size * grid_size))
    return 0.0 if maximum_entropy == 0 else entropy / maximum_entropy


def _mst_max_degree(instance: TSPInstance) -> int:
    if instance.dimension <= 1:
        return 0
    degrees = [0] * instance.dimension
    for source, target in _minimum_spanning_tree_edges(instance.distances):
        degrees[source] += 1
        degrees[target] += 1
    return max(degrees)


def _nearest_neighbor_cv(instance: TSPInstance) -> float:
    if instance.dimension <= 1:
        return 0.0
    nearest = [
        min(
            instance.distances[source][target]
            for target in range(instance.dimension)
            if target != source
        )
        for source in range(instance.dimension)
    ]
    mean = fmean(nearest)
    return 0.0 if mean == 0 else pstdev(nearest) / mean


def _triangle_violations(instance: TSPInstance) -> tuple[int, float]:
    dimension = instance.dimension
    possible = dimension * (dimension - 1) * (dimension - 2) // 2
    violations = 0
    distances = instance.distances
    for source in range(dimension):
        for target in range(source + 1, dimension):
            direct = distances[source][target]
            for middle in range(dimension):
                if middle not in (source, target) and direct > (
                    distances[source][middle] + distances[middle][target]
                ):
                    violations += 1
    return violations, 0.0 if possible == 0 else violations / possible


def extract_instance_features(instance: TSPInstance) -> InstanceFeatures:
    """Calcula as características solicitadas usando a matriz efetiva EUC_2D."""

    violations, violation_fraction = _triangle_violations(instance)
    hull_size = len(_convex_hull_vertices(instance))
    return InstanceFeatures(
        aspect_ratio=_aspect_ratio(instance),
        convex_hull_fraction=hull_size / instance.dimension,
        spatial_entropy=_spatial_entropy(instance),
        mst_max_degree=_mst_max_degree(instance),
        nearest_neighbor_cv=_nearest_neighbor_cv(instance),
        triangle_violation_count=violations,
        triangle_violation_fraction=violation_fraction,
    )


def _number(value: Any) -> float | None:
    if value is None or str(value) in NA_VALUES:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _linear_regression(xs: Sequence[float], ys: Sequence[float]) -> dict[str, Any] | None:
    if len(xs) < 2 or len(xs) != len(ys):
        return None
    mean_x = fmean(xs)
    mean_y = fmean(ys)
    denominator = sum((value - mean_x) ** 2 for value in xs)
    if denominator == 0:
        return None
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True)) / denominator
    intercept = mean_y - slope * mean_x
    predictions = [intercept + slope * x for x in xs]
    return _fit_quality(ys, predictions) | {"intercept": intercept, "slope": slope}


def _fit_quality(actual: Sequence[float], predicted: Sequence[float]) -> dict[str, Any]:
    residual_sum = sum(
        (value - estimate) ** 2 for value, estimate in zip(actual, predicted, strict=True)
    )
    mean = fmean(actual)
    total_sum = sum((value - mean) ** 2 for value in actual)
    r_squared = (
        1.0
        if total_sum == 0 and residual_sum == 0
        else (0.0 if total_sum == 0 else 1.0 - residual_sum / total_sum)
    )
    return {
        "observations": len(actual),
        "r_squared": r_squared,
        "rmse": sqrt(residual_sum / len(actual)),
    }


def _solve(matrix: list[list[float]], values: list[float]) -> list[float] | None:
    size = len(values)
    augmented = [row[:] + [value] for row, value in zip(matrix, values, strict=True)]
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1e-12:
            return None
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        divisor = augmented[column][column]
        augmented[column] = [value / divisor for value in augmented[column]]
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            augmented[row] = [
                value - factor * pivot_value
                for value, pivot_value in zip(augmented[row], augmented[column], strict=True)
            ]
    return [augmented[row][-1] for row in range(size)]


def _multiple_regression(
    rows: Sequence[dict[str, Any]],
) -> dict[str, Any] | None:
    names = [
        "intercept",
        "log_dimension",
        "log_aspect_ratio",
        "convex_hull_fraction",
        "spatial_entropy",
        "mst_max_degree",
        "nearest_neighbor_cv",
    ]
    design: list[list[float]] = []
    targets: list[float] = []
    for row in rows:
        dimension = _number(row.get("dimension"))
        aspect_ratio = _number(row.get("aspect_ratio"))
        duration = _number(row.get("solver_total_seconds"))
        predictors = [
            _number(row.get("convex_hull_fraction")),
            _number(row.get("spatial_entropy")),
            _number(row.get("mst_max_degree")),
            _number(row.get("nearest_neighbor_cv")),
        ]
        if (
            dimension is None
            or dimension <= 0
            or aspect_ratio is None
            or aspect_ratio <= 0
            or duration is None
            or duration <= 0
            or any(value is None for value in predictors)
        ):
            continue
        design.append(
            [
                1.0,
                log(dimension),
                log(aspect_ratio),
                *(float(value) for value in predictors if value is not None),
            ]
        )
        targets.append(log(duration))
    width = len(names)
    if len(design) <= width:
        return None
    normal = [[sum(row[i] * row[j] for row in design) for j in range(width)] for i in range(width)]
    for index in range(1, width):
        normal[index][index] += 1e-9
    right = [
        sum(row[index] * target for row, target in zip(design, targets, strict=True))
        for index in range(width)
    ]
    coefficients = _solve(normal, right)
    if coefficients is None:
        return None
    predictions = [
        sum(value * coefficient for value, coefficient in zip(row, coefficients, strict=True))
        for row in design
    ]
    return _fit_quality(targets, predictions) | {
        "target": "log(solver_total_seconds)",
        "coefficients": dict(zip(names, coefficients, strict=True)),
    }


def _regression_summary(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    completed = [row for row in rows if row.get("status") == "optimal"]

    def log_pairs(target: str) -> tuple[list[float], list[float]]:
        pairs = []
        for row in completed:
            dimension = _number(row.get("dimension"))
            value = _number(row.get(target))
            if dimension is not None and dimension > 0 and value is not None and value > 0:
                pairs.append((log(dimension), log(value)))
        return [pair[0] for pair in pairs], [pair[1] for pair in pairs]

    time_x, time_y = log_pairs("solver_total_seconds")
    memory_x, memory_y = log_pairs("peak_memory_bytes")
    return {
        "selection": "status=optimal; timeouts are censored and excluded",
        "log_time_by_log_dimension": _linear_regression(time_x, time_y),
        "log_memory_by_log_dimension": _linear_regression(memory_x, memory_y),
        "multiple_log_time_model": _multiple_regression(completed),
    }


def _strategy_summary(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    comparable: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in rows:
        strategy = str(row.get("initialization_strategy", "unknown"))
        grouped[strategy].append(row)
        comparable[(str(row.get("instance_sha256")), str(row.get("repetition")))].add(strategy)

    fields = [
        "initial_route_cost",
        "initialization_seconds",
        "solver_total_seconds",
        "generated_nodes",
        "expanded_nodes",
        "pruned_nodes",
        "initial_gap_percent",
    ]
    summary: dict[str, Any] = {}
    for strategy, strategy_rows in sorted(grouped.items()):
        aggregates = {}
        for field in fields:
            values = [
                value for row in strategy_rows if (value := _number(row.get(field))) is not None
            ]
            aggregates[f"mean_{field}"] = fmean(values) if values else None
        summary[strategy] = {"runs": len(strategy_rows), **aggregates}
    return {
        "strategies": summary,
        "paired_instance_repetition_groups": sum(
            len(strategies) > 1 for strategies in comparable.values()
        ),
    }


def _read_csvs(paths: Iterable[Path]) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    fields: list[str] = []
    for path in paths:
        with path.open(encoding="utf-8", newline="") as source:
            reader = csv.DictReader(source)
            for field in reader.fieldnames or []:
                if field not in fields:
                    fields.append(field)
            rows.extend(dict(row) for row in reader)
    if not rows:
        raise ValueError("nenhuma linha de resultado foi encontrada")
    return rows, fields


def _known_optima(path: Path | None) -> dict[str, float]:
    if path is None:
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("o arquivo de ótimos deve ser um objeto SHA-256 -> custo")
    result: dict[str, float] = {}
    for digest, value in payload.items():
        try:
            valid_digest = isinstance(digest, str) and len(digest) == 64 and int(digest, 16) >= 0
        except ValueError:
            valid_digest = False
        if not valid_digest or _number(value) is None:
            raise ValueError("ótimo externo deve usar uma chave SHA-256 e custo numérico")
        result[digest] = float(value)
    return result


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def analyze_results(
    csv_paths: Sequence[Path],
    output_dir: Path,
    *,
    known_optima_path: Path | None = None,
) -> dict[str, Any]:
    """Gera tabela enriquecida e resumo sem tratar incumbentes como ótimos."""

    rows, original_fields = _read_csvs(csv_paths)
    known = _known_optima(known_optima_path)
    certified_by_digest: dict[str, float] = {}
    for row in rows:
        if row.get("status") != "optimal":
            continue
        digest = str(row.get("instance_sha256", row.get("instance_path")))
        cost = _number(row.get("optimal_cost"))
        if cost is None:
            raise ValueError(f"execução optimal sem custo ótimo numérico: {digest}")
        previous = certified_by_digest.setdefault(digest, cost)
        if previous != cost:
            raise ValueError(f"custos ótimos certificados incompatíveis para {digest}")
        if digest in known and known[digest] != cost:
            raise ValueError(f"ótimo externo diverge da execução certificada para {digest}")

    feature_cache: dict[str, InstanceFeatures] = {}
    for row in rows:
        instance_path = Path(str(row["instance_path"]))
        digest = str(row.get("instance_sha256", instance_path))
        if digest not in feature_cache:
            if len(digest) == 64 and _sha256(instance_path) != digest:
                raise ValueError(
                    f"a instância atual diverge do SHA-256 registrado: {instance_path}"
                )
            feature_cache[digest] = extract_instance_features(read_tsplib(instance_path))
        row.update(asdict(feature_cache[digest]))

        own_certified = _number(row.get("optimal_cost")) if row.get("status") == "optimal" else None
        certified = certified_by_digest.get(digest)
        external = known.get(digest)
        reference = certified if certified is not None else external
        source = (
            "certified_run"
            if own_certified is not None
            else (
                "certified_peer_run"
                if certified is not None
                else ("known_optima_sha256" if external is not None else "NA")
            )
        )
        row["reference_optimal_cost"] = reference if reference is not None else "NA"
        row["reference_optimal_source"] = source
        for cost_field, gap_field in (
            ("initial_route_cost", "initial_gap_percent"),
            ("best_route_cost", "best_gap_percent"),
        ):
            cost = _number(row.get(cost_field))
            row[gap_field] = (
                100.0 * (cost - reference) / reference
                if cost is not None and reference is not None and reference > 0
                else "NA"
            )

    output_dir.mkdir(parents=True, exist_ok=True)
    fields = [
        *original_fields,
        *(field for field in DERIVED_FIELDS if field not in original_fields),
    ]
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    atomic_write_text(output_dir / "enriched_results.csv", buffer.getvalue())

    summary = {
        "source_csvs": [str(path.resolve()) for path in csv_paths],
        "known_optima_file": str(known_optima_path.resolve()) if known_optima_path else None,
        "runs": len(rows),
        "instances": len(feature_cache),
        "statuses": dict(Counter(str(row.get("status")) for row in rows)),
        "nonmetric_instances": sum(
            features.triangle_violation_count > 0 for features in feature_cache.values()
        ),
        "feature_definitions": {
            "aspect_ratio": "max(width,height)/min(width,height); null for a non-point line",
            "convex_hull_fraction": "extreme hull vertices / n",
            "spatial_entropy": "normalized Shannon entropy on a ceil(sqrt(n)) grid",
            "mst_max_degree": "maximum vertex degree in the deterministic Prim MST",
            "nearest_neighbor_cv": "population standard deviation / mean nearest-neighbor distance",
            "triangle_violation_fraction": (
                "violating unordered endpoint/middle triples / all such triples"
            ),
        },
        "regressions": _regression_summary(rows),
        "warm_start_comparison": _strategy_summary(rows),
    }
    atomic_write_json(output_dir / "summary.json", summary)
    return summary


def main(arguments: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", nargs="+", type=Path, help="results.csv de uma ou mais estratégias")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument(
        "--known-optima-json",
        type=Path,
        help="objeto JSON opcional que mapeia SHA-256 da instância para custo ótimo compatível",
    )
    args = parser.parse_args(arguments)
    analyze_results(args.csv, args.output_dir, known_optima_path=args.known_optima_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
