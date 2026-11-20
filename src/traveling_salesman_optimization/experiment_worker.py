"""Processo isolado que executa uma única combinação experimental."""

from __future__ import annotations

import argparse
import traceback
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any

from traveling_salesman_optimization.branch_and_bound import (
    BranchAndBoundResult,
    solve_branch_and_bound,
)
from traveling_salesman_optimization.experiment_io import (
    atomic_write_json,
    atomic_write_text,
    read_json,
)
from traveling_salesman_optimization.initial_solutions import INITIAL_ROUTE_STRATEGIES
from traveling_salesman_optimization.process_metrics import PeakMemorySampler
from traveling_salesman_optimization.tsplib import TSPInstance, read_tsplib

NA = "NA"


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")


def _write_tour(path: Path, instance: TSPInstance, result: BranchAndBoundResult) -> None:
    route = result.route[:-1]
    lines = [
        f"NAME: {path.stem}",
        "TYPE: TOUR",
        f"DIMENSION: {instance.dimension}",
        f"COMMENT: best_route_cost={result.cost}",
        "TOUR_SECTION",
        *(str(vertex_id) for vertex_id in route),
        "-1",
        "EOF",
        "",
    ]
    atomic_write_text(path, "\n".join(lines))


def _validate_route(instance: TSPInstance, result: BranchAndBoundResult) -> None:
    if result.route[0] != result.route[-1]:
        raise RuntimeError("a rota retornada não fecha na origem")
    if len(result.route) != instance.dimension + 1:
        raise RuntimeError("a rota retornada tem dimensão incorreta")
    if set(result.route[:-1]) != set(instance.vertex_ids):
        raise RuntimeError("a rota retornada não é uma permutação dos vértices")
    index_by_id = {vertex_id: index for index, vertex_id in enumerate(instance.vertex_ids)}
    route_indices = tuple(index_by_id[vertex_id] for vertex_id in result.route[:-1])
    if instance.route_cost(route_indices) != result.cost:
        raise RuntimeError("o custo coletado diverge do custo recalculado da rota")
    if result.status == "optimal" and result.optimal_cost != result.cost:
        raise RuntimeError("resultado ótimo sem custo ótimo consistente")


def _record_from_result(
    spec: dict[str, Any],
    instance: TSPInstance,
    result: BranchAndBoundResult,
    sampler: PeakMemorySampler,
    *,
    started_at: str,
    instance_load_seconds: float,
) -> dict[str, Any]:
    return {
        "schema_version": spec["schema_version"],
        "attempt_id": spec["attempt_id"],
        "run_id": spec["run_id"],
        "config_id": spec["config_id"],
        "instance_name": instance.name,
        "instance_path": spec["instance_path"],
        "instance_sha256": spec["instance_sha256"],
        "dimension": instance.dimension,
        "initialization_strategy": spec["initialization_strategy"],
        "repetition": spec["repetition"],
        "initial_route_cost": result.initial_cost,
        "best_route_cost": result.cost,
        "optimal_cost": result.cost if result.status == "optimal" else NA,
        "route_vertex_ids": list(result.route[:-1]),
        "status": result.status,
        "instance_load_seconds": instance_load_seconds,
        "initialization_seconds": result.initialization_seconds,
        "search_seconds": result.search_seconds,
        "solver_total_seconds": result.solver_total_seconds,
        "generated_nodes": result.generated_nodes,
        "expanded_nodes": result.expanded_nodes,
        "pruned_nodes": result.pruned_nodes,
        "max_depth": result.max_depth,
        "peak_memory_bytes": sampler.peak_bytes(),
        "memory_unit": "bytes",
        "memory_measurement_method": sampler.method,
        "lower_bound_calls": result.lower_bound_calls,
        "lower_bound_seconds": result.lower_bound_seconds,
        "checkpoint_calls": result.checkpoint_calls,
        "checkpoint_seconds": result.checkpoint_seconds,
        "mst_calls": result.mst_calls,
        "mst_seconds": result.mst_seconds,
        "mst_process_peak_bytes": result.mst_process_peak_bytes,
        "matching_calls": result.matching_calls,
        "matching_seconds": result.matching_seconds,
        "matching_process_peak_bytes": result.matching_process_peak_bytes,
        "eulerian_circuit_calls": result.eulerian_circuit_calls,
        "eulerian_circuit_seconds": result.eulerian_circuit_seconds,
        "eulerian_circuit_process_peak_bytes": result.eulerian_circuit_process_peak_bytes,
        "shortcut_calls": result.shortcut_calls,
        "shortcut_seconds": result.shortcut_seconds,
        "shortcut_process_peak_bytes": result.shortcut_process_peak_bytes,
        "time_limit_seconds": spec["time_limit_seconds"],
        "started_at_utc": started_at,
        "finished_at_utc": "" if result.status == "running" else _utc_now(),
        "route_file": spec["route_file"],
        "checkpoint_file": spec["checkpoint_file"],
        "result_file": spec["result_file"],
        "log_file": spec["log_file"],
        "termination": "running" if result.status == "running" else "cooperative",
        "worker_exit_code": NA,
        "executor_wall_seconds": NA,
        "error_type": "",
        "error_message": "",
    }


def _empty_error_record(
    spec: dict[str, Any], sampler: PeakMemorySampler, started_at: str
) -> dict[str, Any]:
    return {
        "schema_version": spec["schema_version"],
        "attempt_id": spec["attempt_id"],
        "run_id": spec["run_id"],
        "config_id": spec["config_id"],
        "instance_name": Path(spec["instance_path"]).stem,
        "instance_path": spec["instance_path"],
        "instance_sha256": spec["instance_sha256"],
        "dimension": NA,
        "initialization_strategy": spec["initialization_strategy"],
        "repetition": spec["repetition"],
        "initial_route_cost": NA,
        "best_route_cost": NA,
        "optimal_cost": NA,
        "status": "error",
        "instance_load_seconds": NA,
        "initialization_seconds": NA,
        "search_seconds": NA,
        "solver_total_seconds": NA,
        "generated_nodes": 0,
        "expanded_nodes": 0,
        "pruned_nodes": 0,
        "max_depth": 0,
        "peak_memory_bytes": sampler.peak_bytes(),
        "memory_unit": "bytes",
        "memory_measurement_method": sampler.method,
        "lower_bound_calls": 0,
        "lower_bound_seconds": 0.0,
        "checkpoint_calls": 0,
        "checkpoint_seconds": 0.0,
        "mst_calls": 0,
        "mst_seconds": 0.0,
        "mst_process_peak_bytes": 0,
        "matching_calls": 0,
        "matching_seconds": 0.0,
        "matching_process_peak_bytes": 0,
        "eulerian_circuit_calls": 0,
        "eulerian_circuit_seconds": 0.0,
        "eulerian_circuit_process_peak_bytes": 0,
        "shortcut_calls": 0,
        "shortcut_seconds": 0.0,
        "shortcut_process_peak_bytes": 0,
        "time_limit_seconds": spec["time_limit_seconds"],
        "started_at_utc": started_at,
        "finished_at_utc": _utc_now(),
        "route_file": "",
        "checkpoint_file": spec["checkpoint_file"],
        "result_file": spec["result_file"],
        "log_file": spec["log_file"],
        "termination": "worker_error",
        "worker_exit_code": NA,
        "executor_wall_seconds": NA,
        "error_type": "",
        "error_message": "",
    }


def run_spec(spec_path: Path) -> int:
    """Executa uma especificação e grava checkpoint/resultado sem anexar ao CSV."""

    spec = read_json(spec_path)
    output_dir = Path(spec["output_dir"])
    checkpoint_path = output_dir / spec["checkpoint_file"]
    result_path = output_dir / spec["result_file"]
    route_path = output_dir / spec["route_file"]
    sampler = PeakMemorySampler.create()
    started_at = _utc_now()
    latest_record: dict[str, Any] | None = None
    worker_started = perf_counter()

    try:
        load_started = perf_counter()
        instance = read_tsplib(spec["instance_path"])
        instance_load_seconds = perf_counter() - load_started
        strategy = INITIAL_ROUTE_STRATEGIES[spec["initialization_strategy"]]
        remaining_seconds = max(
            0.0,
            float(spec["time_limit_seconds"]) - (perf_counter() - worker_started),
        )

        def save_progress(progress: BranchAndBoundResult) -> None:
            nonlocal latest_record
            record = _record_from_result(
                spec,
                instance,
                progress,
                sampler,
                started_at=started_at,
                instance_load_seconds=instance_load_seconds,
            )
            _write_tour(route_path, instance, progress)
            atomic_write_json(checkpoint_path, {"record": record})
            latest_record = record

        result = solve_branch_and_bound(
            instance,
            strategy,
            time_limit_seconds=remaining_seconds,
            progress_callback=save_progress,
            checkpoint_interval_seconds=float(spec["checkpoint_interval_seconds"]),
            phase_memory_query=sampler.peak_bytes,
        )
        _validate_route(instance, result)
        final_record = _record_from_result(
            spec,
            instance,
            result,
            sampler,
            started_at=started_at,
            instance_load_seconds=instance_load_seconds,
        )
        _write_tour(route_path, instance, result)
        atomic_write_json(checkpoint_path, {"record": final_record})
        atomic_write_json(result_path, {"record": final_record})
        return 0
    except Exception as error:
        traceback.print_exc()
        record = latest_record or _empty_error_record(spec, sampler, started_at)
        record.update(
            {
                "status": "error",
                "optimal_cost": NA,
                "finished_at_utc": _utc_now(),
                "peak_memory_bytes": sampler.peak_bytes(),
                "termination": "worker_error",
                "error_type": type(error).__name__,
                "error_message": str(error),
            }
        )
        try:
            atomic_write_json(checkpoint_path, {"record": record})
            atomic_write_json(result_path, {"record": record})
        except OSError:
            traceback.print_exc()
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path, help="especificação JSON de uma execução")
    return run_spec(parser.parse_args().spec)


if __name__ == "__main__":
    raise SystemExit(main())
