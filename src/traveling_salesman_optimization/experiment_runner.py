"""Executor reproduzível de lotes isolados do Branch-and-Bound."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import platform
import subprocess
import sys
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any

from traveling_salesman_optimization.experiment_io import (
    atomic_write_json,
    atomic_write_text,
    read_json,
)
from traveling_salesman_optimization.initial_solutions import INITIAL_ROUTE_STRATEGIES

SCHEMA_VERSION = "1"
DEFAULT_TIMEOUT_SECONDS = 1_800.0
DEFAULT_CHECKPOINT_INTERVAL_SECONDS = 30.0
DEFAULT_EXTERNAL_GRACE_SECONDS = 10.0
COMPLETED_STATUSES = {"optimal", "timeout"}
NA = "NA"

CSV_FIELDS = [
    "schema_version",
    "run_id",
    "config_id",
    "instance_name",
    "instance_path",
    "instance_sha256",
    "dimension",
    "initialization_strategy",
    "repetition",
    "initial_route_cost",
    "best_route_cost",
    "optimal_cost",
    "status",
    "instance_load_seconds",
    "initialization_seconds",
    "search_seconds",
    "solver_total_seconds",
    "expanded_nodes",
    "pruned_nodes",
    "max_depth",
    "peak_memory_bytes",
    "memory_unit",
    "memory_measurement_method",
    "lower_bound_calls",
    "lower_bound_seconds",
    "mst_calls",
    "mst_computations",
    "mst_cache_hits",
    "mst_seconds",
    "checkpoint_calls",
    "checkpoint_seconds",
    "time_limit_seconds",
    "started_at_utc",
    "finished_at_utc",
    "route_file",
    "checkpoint_file",
    "result_file",
    "log_file",
    "termination",
    "worker_exit_code",
    "executor_wall_seconds",
    "error_type",
    "error_message",
]


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")


def _nonnegative_float(value: str) -> float:
    number = float(value)
    if number < 0:
        raise argparse.ArgumentTypeError("o valor deve ser não negativo")
    return number


def _positive_float(value: str) -> float:
    number = float(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("o valor deve ser positivo")
    return number


def _positive_int(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("o valor deve ser positivo")
    return number


def discover_instances(inputs: Sequence[Path]) -> list[Path]:
    """Expande arquivos e pastas recursivamente, em ordem determinística."""

    discovered: dict[str, Path] = {}
    for supplied in inputs:
        path = supplied.expanduser().resolve()
        if path.is_file():
            if path.suffix.lower() != ".tsp":
                raise ValueError(f"o arquivo não possui extensão .tsp: {path}")
            discovered[os.path.normcase(str(path))] = path
        elif path.is_dir():
            for candidate in path.rglob("*"):
                if candidate.is_file() and candidate.suffix.lower() == ".tsp":
                    resolved = candidate.resolve()
                    discovered[os.path.normcase(str(resolved))] = resolved
        else:
            raise ValueError(f"entrada inexistente: {path}")
    if not discovered:
        raise ValueError("nenhuma instância .tsp foi encontrada")
    return [discovered[key] for key in sorted(discovered)]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _identifier(value: dict[str, Any], length: int = 16) -> str:
    serialized = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(serialized.encode("ascii")).hexdigest()[:length]


def _git_environment(root: Path) -> dict[str, Any]:
    def git(*arguments: str) -> str | None:
        try:
            completed = subprocess.run(
                ["git", *arguments],
                cwd=root,
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        return completed.stdout.strip() if completed.returncode == 0 else None

    status = git("status", "--porcelain")
    return {
        "commit": git("rev-parse", "HEAD"),
        "branch": git("branch", "--show-current"),
        "dirty": None if status is None else bool(status),
    }


def _environment(root: Path) -> dict[str, Any]:
    return {
        "captured_at_utc": _utc_now(),
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "python_executable": sys.executable,
        "cpu_count": os.cpu_count(),
        "python_hash_seed": os.environ.get("PYTHONHASHSEED", "not set"),
        "working_directory": str(root),
        "git": _git_environment(root),
    }


def _load_results(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames != CSV_FIELDS:
            raise ValueError(f"cabeçalho incompatível em {path}; use outra pasta ou migre o CSV")
        rows = list(reader)
    run_ids = [row["run_id"] for row in rows]
    if len(run_ids) != len(set(run_ids)):
        raise ValueError(f"{path} contém run_id duplicado")
    return rows


def _save_results(path: Path, rows: Sequence[dict[str, Any]]) -> None:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=CSV_FIELDS, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({field: row.get(field, NA) for field in CSV_FIELDS})
    atomic_write_text(path, buffer.getvalue())


def _fallback_record(spec: dict[str, Any], *, status: str, message: str) -> dict[str, Any]:
    record = {field: NA for field in CSV_FIELDS}
    record.update(
        {
            "schema_version": SCHEMA_VERSION,
            "attempt_id": spec["attempt_id"],
            "run_id": spec["run_id"],
            "config_id": spec["config_id"],
            "instance_name": Path(spec["instance_path"]).stem,
            "instance_path": spec["instance_path"],
            "instance_sha256": spec["instance_sha256"],
            "initialization_strategy": spec["initialization_strategy"],
            "repetition": spec["repetition"],
            "status": status,
            "time_limit_seconds": spec["time_limit_seconds"],
            "started_at_utc": "",
            "finished_at_utc": _utc_now(),
            "checkpoint_file": spec["checkpoint_file"],
            "result_file": spec["result_file"],
            "log_file": spec["log_file"],
            "termination": "executor_fallback",
            "error_type": "MissingWorkerResult",
            "error_message": message,
            "optimal_cost": NA,
        }
    )
    return record


def _load_worker_record(path: Path, attempt_id: str) -> dict[str, Any] | None:
    if not path.exists():
        return None
    payload = read_json(path)
    record = payload.get("record")
    if not isinstance(record, dict):
        raise ValueError(f"resultado sem objeto record: {path}")
    if record.get("attempt_id") != attempt_id:
        return None
    return record


def _terminate_process(process: subprocess.Popen[bytes]) -> str:
    process.terminate()
    try:
        process.wait(timeout=2)
        return "external_timeout_terminate"
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
        return "external_timeout_kill"


def _execute_one(spec: dict[str, Any], output_dir: Path, root: Path) -> dict[str, Any]:
    spec_path = output_dir / "specs" / f"{spec['run_id']}.json"
    result_path = output_dir / spec["result_file"]
    checkpoint_path = output_dir / spec["checkpoint_file"]
    log_path = output_dir / spec["log_file"]
    atomic_write_json(spec_path, spec)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    command = [
        sys.executable,
        "-m",
        "traveling_salesman_optimization.experiment_worker",
        str(spec_path),
    ]
    execution_started = perf_counter()
    externally_stopped = False
    user_interrupted = False
    termination = "cooperative"
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            command,
            cwd=root,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        try:
            process.wait(
                timeout=float(spec["time_limit_seconds"]) + float(spec["external_grace_seconds"])
            )
        except subprocess.TimeoutExpired:
            externally_stopped = True
            termination = _terminate_process(process)
        except KeyboardInterrupt:
            user_interrupted = True
            termination = _terminate_process(process)

    executor_wall_seconds = perf_counter() - execution_started
    worker_exit_code = process.returncode
    record = _load_worker_record(result_path, spec["attempt_id"])
    if record is None:
        record = _load_worker_record(checkpoint_path, spec["attempt_id"])

    if record is None:
        status = "timeout" if externally_stopped else "error"
        record = _fallback_record(
            spec,
            status=status,
            message="o worker terminou sem resultado nem checkpoint legível",
        )
    if externally_stopped:
        record.update(
            {
                "status": "timeout",
                "optimal_cost": NA,
                "finished_at_utc": _utc_now(),
                "termination": termination,
                "error_type": "",
                "error_message": "",
            }
        )
    elif user_interrupted:
        record.update(
            {
                "status": "error",
                "optimal_cost": NA,
                "finished_at_utc": _utc_now(),
                "termination": termination,
                "error_type": "KeyboardInterrupt",
                "error_message": "lote interrompido pelo usuário",
            }
        )
    elif record.get("status") == "running":
        record.update(
            {
                "status": "error",
                "optimal_cost": NA,
                "finished_at_utc": _utc_now(),
                "termination": "incomplete_worker_result",
                "error_type": "IncompleteWorkerResult",
                "error_message": "o worker terminou deixando apenas um checkpoint em andamento",
            }
        )

    record["worker_exit_code"] = worker_exit_code
    record["executor_wall_seconds"] = executor_wall_seconds
    if externally_stopped:
        record["termination"] = termination
    if user_interrupted:
        record["termination"] = "user_interrupt"
        record["_batch_interrupted"] = True
    atomic_write_json(result_path, {"record": record})
    return record


def _make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "inputs",
        nargs="+",
        type=Path,
        help="arquivos .tsp e/ou pastas pesquisadas recursivamente",
    )
    parser.add_argument("--output-dir", required=True, type=Path, help="pasta de saída")
    parser.add_argument("--repetitions", type=_positive_int, default=1)
    parser.add_argument(
        "--timeout-seconds",
        type=_nonnegative_float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="prazo por execução (padrão: 1800)",
    )
    parser.add_argument(
        "--checkpoint-interval-seconds",
        type=_positive_float,
        default=DEFAULT_CHECKPOINT_INTERVAL_SECONDS,
    )
    parser.add_argument(
        "--external-grace-seconds",
        type=_nonnegative_float,
        default=DEFAULT_EXTERNAL_GRACE_SECONDS,
        help="margem para encerramento cooperativo antes da interrupção externa",
    )
    parser.add_argument(
        "--strategy",
        choices=sorted(INITIAL_ROUTE_STRATEGIES),
        default="trivial",
        help="estratégia de inicialização do limite superior",
    )
    parser.add_argument(
        "--rerun",
        action="store_true",
        help="repete e substitui execuções já concluídas na mesma configuração",
    )
    return parser


def main(arguments: Sequence[str] | None = None) -> int:
    parser = _make_parser()
    args = parser.parse_args(arguments)
    try:
        instances = discover_instances(args.inputs)
    except (OSError, ValueError) as error:
        parser.error(str(error))

    root = Path(__file__).resolve().parents[2]
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    results_path = output_dir / "results.csv"
    try:
        rows: list[dict[str, Any]] = list(_load_results(results_path))
    except (OSError, ValueError) as error:
        parser.error(str(error))
    row_positions = {row["run_id"]: position for position, row in enumerate(rows)}

    canonical_config = {
        "schema_version": SCHEMA_VERSION,
        "algorithm": "branch_and_bound_best_first",
        "initialization_strategy": args.strategy,
        "time_limit_seconds": args.timeout_seconds,
        "checkpoint_interval_seconds": args.checkpoint_interval_seconds,
        "external_grace_seconds": args.external_grace_seconds,
        "duration_clock": "time.perf_counter (monotonic)",
        "instrumentation_version": 1,
    }
    config_id = _identifier(canonical_config)
    config_path = output_dir / "configurations" / f"config-{config_id}.json"
    if not config_path.exists():
        atomic_write_json(
            config_path,
            {
                "config_id": config_id,
                "configuration": canonical_config,
                "environment": _environment(root),
            },
        )

    instance_metadata = [
        {
            "path": str(path),
            "sha256": _sha256(path),
            "size_bytes": path.stat().st_size,
        }
        for path in instances
    ]
    invocation_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ") + f"-{uuid.uuid4().hex[:8]}"
    atomic_write_json(
        output_dir / "invocations" / f"invocation-{invocation_id}.json",
        {
            "invocation_id": invocation_id,
            "created_at_utc": _utc_now(),
            "config_id": config_id,
            "repetitions": args.repetitions,
            "rerun": args.rerun,
            "instances": instance_metadata,
            "command": [sys.executable, "-m", __name__, *(arguments or sys.argv[1:])],
        },
    )

    planned: dict[str, dict[str, Any]] = {}
    for metadata in instance_metadata:
        for repetition in range(1, args.repetitions + 1):
            run_id = _identifier(
                {
                    "config_id": config_id,
                    "instance_sha256": metadata["sha256"],
                    "instance_path": metadata["path"],
                    "repetition": repetition,
                },
                length=20,
            )
            planned[run_id] = {
                "schema_version": SCHEMA_VERSION,
                "attempt_id": uuid.uuid4().hex,
                "run_id": run_id,
                "config_id": config_id,
                "instance_path": metadata["path"],
                "instance_sha256": metadata["sha256"],
                "initialization_strategy": args.strategy,
                "repetition": repetition,
                "time_limit_seconds": args.timeout_seconds,
                "checkpoint_interval_seconds": args.checkpoint_interval_seconds,
                "external_grace_seconds": args.external_grace_seconds,
                "output_dir": str(output_dir),
                "route_file": f"routes/{run_id}.tour",
                "checkpoint_file": f"checkpoints/{run_id}.json",
                "result_file": f"runs/{run_id}.json",
                "log_file": f"logs/{run_id}.log",
            }

    errors = 0
    executed = 0
    skipped = 0
    for run_id, spec in planned.items():
        previous_position = row_positions.get(run_id)
        previous = rows[previous_position] if previous_position is not None else None
        if not args.rerun and previous is not None and previous["status"] in COMPLETED_STATUSES:
            print(f"SKIP {run_id} {Path(spec['instance_path']).name} rep={spec['repetition']}")
            skipped += 1
            continue

        print(f"RUN  {run_id} {Path(spec['instance_path']).name} rep={spec['repetition']}")
        try:
            record = _execute_one(spec, output_dir, root)
        except Exception as error:
            record = _fallback_record(spec, status="error", message=str(error))
            record["error_type"] = type(error).__name__
        if previous_position is None:
            row_positions[run_id] = len(rows)
            rows.append(record)
        else:
            rows[previous_position] = record
        _save_results(results_path, rows)
        executed += 1
        if record["status"] == "error":
            errors += 1
        print(
            f"DONE {run_id} status={record['status']} "
            f"best={record['best_route_cost']} total={record['solver_total_seconds']}s"
        )
        if record.get("_batch_interrupted"):
            print("SUMMARY lote interrompido pelo usuário; checkpoint preservado")
            print(f"CSV {results_path}")
            return 130

    print(f"SUMMARY executed={executed} skipped={skipped} errors={errors}")
    print(f"CSV {results_path}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
