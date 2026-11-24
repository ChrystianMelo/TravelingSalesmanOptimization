"""Gera os gráficos de regressão do relatório a partir do painel final.

O arquivo de saida usa apenas o ambiente ``picture`` do LaTeX para manter a
figura vetorial sem acrescentar uma dependencia de plotagem ao projeto.
"""

from __future__ import annotations

import csv
import hashlib
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "experiments" / "results" / "final" / "results.csv"
OUTPUT = ROOT / "docs" / "report" / "figures" / "complexity-regressions.tex"
EXPECTED_SHA256 = "0fa7992af87a84ff8eee41614bf6f5e9b07ecbbae2682d09f249b53fc2cda345"

TIME_COLOUR = (0.10, 0.32, 0.55)
RAW_COLOUR = (0.43, 0.57, 0.69)
CENSORED_COLOUR = (0.78, 0.30, 0.12)
GRID_COLOUR = (0.84, 0.84, 0.84)


def _read_rows() -> list[dict[str, str]]:
    digest = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    if digest != EXPECTED_SHA256:
        raise RuntimeError(f"SHA-256 inesperado para {SOURCE}: {digest}")
    with SOURCE.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 75:
        raise RuntimeError(f"esperadas 75 linhas na versão final, encontradas {len(rows)}")
    return rows


def _fit_points(rows: list[dict[str, str]], target: str) -> list[tuple[float, float]]:
    by_instance: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_instance[row["instance_sha256"]].append(row)

    points: list[tuple[float, float]] = []
    for group in by_instance.values():
        if len(group) == 5 and all(row["status"] == "optimal" for row in group):
            dimension = float(group[0]["dimension"])
            points.append((dimension, median(float(row[target]) for row in group)))
    points.sort()
    if len(points) != 10:
        raise RuntimeError(f"esperadas 10 medianas pareadas, encontradas {len(points)}")
    return points


def _log_regression(points: list[tuple[float, float]]) -> dict[str, float]:
    xs = [math.log(x) for x, _ in points]
    ys = [math.log(y) for _, y in points]
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    denominator = sum((x - mean_x) ** 2 for x in xs)
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True)) / denominator
    intercept = mean_y - slope * mean_x
    predicted = [intercept + slope * x for x in xs]
    residual_sum = sum((actual - fitted) ** 2 for actual, fitted in zip(ys, predicted, strict=True))
    total_sum = sum((actual - mean_y) ** 2 for actual in ys)
    return {
        "coefficient": math.exp(intercept),
        "slope": slope,
        "r_squared": 1.0 - residual_sum / total_sum,
        "rmse": math.sqrt(residual_sum / len(ys)),
    }


def _colour(rgb: tuple[float, float, float]) -> str:
    return "\\color[rgb]{" + ",".join(f"{component:.2f}" for component in rgb) + "}"


def _line(x1: float, y1: float, x2: float, y2: float) -> str:
    middle_x = (x1 + x2) / 2
    middle_y = (y1 + y2) / 2
    return f"\\qbezier({x1:.2f},{y1:.2f})({middle_x:.2f},{middle_y:.2f})({x2:.2f},{y2:.2f})"


def _triangle(x: float, y: float, radius: float = 2.6) -> list[str]:
    left = (x - radius, y - radius * 0.75)
    right = (x + radius, y - radius * 0.75)
    top = (x, y + radius)
    return [
        _line(*left, *right),
        _line(*right, *top),
        _line(*top, *left),
    ]


def _map_log(value: float, minimum: float, maximum: float, start: float, span: float) -> float:
    fraction = (math.log(value) - math.log(minimum)) / (math.log(maximum) - math.log(minimum))
    return start + fraction * span


def _decimal(value: float, digits: int) -> str:
    return f"{value:.{digits}f}".replace(".", "{,}")


def _scientific(value: float, digits: int) -> tuple[str, int]:
    exponent = math.floor(math.log10(abs(value)))
    mantissa = value / (10**exponent)
    return _decimal(mantissa, digits), exponent


def _panel(
    *,
    origin: float,
    title: str,
    y_label: str,
    y_limits: tuple[float, float],
    y_ticks: list[tuple[float, str]],
    completed: list[tuple[float, float]],
    censored: list[tuple[float, float]],
    medians: list[tuple[float, float]],
    model: dict[str, float],
    equation: str,
    aggregate_censored: Counter[int] | None = None,
) -> list[str]:
    left = origin + 47
    bottom = 39.0
    width = 188.0
    height = 116.0
    x_min, x_max = 9.0, 75.0
    y_min, y_max = y_limits

    def x_position(value: float) -> float:
        return _map_log(value, x_min, x_max, left, width)

    def y_position(value: float) -> float:
        return _map_log(value, y_min, y_max, bottom, height)

    quality = (
        f"$R^2={_decimal(model['r_squared'], 3)}$; "
        f"$\\mathrm{{RMSE}}_{{\\log}}={_decimal(model['rmse'], 3)}$"
    )
    output = [
        f"\\put({origin + 141:.1f},205){{\\makebox(0,0){{\\small\\bfseries {title}}}}}",
        f"\\put({origin + 52:.1f},188){{\\makebox(0,0)[l]{{\\scriptsize {equation}}}}}",
        f"\\put({origin + 52:.1f},177){{\\makebox(0,0)[l]{{\\scriptsize {quality}}}}}",
        "{",
        _colour(GRID_COLOUR),
        "\\linethickness{0.25pt}",
    ]

    for tick, label in y_ticks:
        y = y_position(tick)
        output.extend(
            [
                _line(left, y, left + width, y),
                (f"\\put({left - 5:.2f},{y:.2f}){{\\makebox(0,0)[r]{{\\tiny {label}}}}}"),
            ]
        )
    for tick in (10, 20, 30, 50, 70):
        x = x_position(tick)
        output.extend(
            [
                _line(x, bottom, x, bottom + height),
                f"\\put({x:.2f},{bottom - 8:.2f}){{\\makebox(0,0){{\\tiny {tick}}}}}",
            ]
        )
    output.append("}")

    output.extend(["{", _colour(TIME_COLOUR), "\\linethickness{1.15pt}"])
    fit_start = 10.0
    fit_end = 30.0
    predicted_start = model["coefficient"] * fit_start ** model["slope"]
    predicted_end = model["coefficient"] * fit_end ** model["slope"]
    output.append(
        _line(
            x_position(fit_start),
            y_position(predicted_start),
            x_position(fit_end),
            y_position(predicted_end),
        )
    )
    output.append("}")

    output.extend(["{", _colour(RAW_COLOUR), "\\linethickness{0.45pt}"])
    for dimension, value in completed:
        output.append(
            f"\\put({x_position(dimension):.2f},{y_position(value):.2f}){{\\circle{{2.50}}}}"
        )
    output.append("}")

    output.extend(["{", _colour(CENSORED_COLOUR), "\\linethickness{0.70pt}"])
    if aggregate_censored is None:
        for dimension, value in censored:
            output.extend(_triangle(x_position(dimension), y_position(value)))
    else:
        for dimension, count in sorted(aggregate_censored.items()):
            x = x_position(float(dimension))
            y = y_position(1800.0)
            output.extend(_triangle(x, y))
            label_offset = -5 if dimension == 51 else (6 if dimension == 52 else 4)
            output.append(
                f"\\put({x + label_offset:.2f},{y + 6:.2f})"
                f"{{\\makebox(0,0)[l]{{\\tiny $\\times${count}}}}}"
            )
    output.append("}")

    output.extend(["{", _colour(TIME_COLOUR)])
    for dimension, value in medians:
        output.append(
            f"\\put({x_position(dimension):.2f},{y_position(value):.2f}){{\\circle*{{3.40}}}}"
        )
    output.append("}")

    output.extend(
        [
            "\\linethickness{0.55pt}",
            _line(left, bottom, left + width, bottom),
            _line(left, bottom, left, bottom + height),
            (
                f"\\put({origin + 141:.1f},20)"
                "{\\makebox(0,0){\\scriptsize Dimensão $n$ (escala log)}}"
            ),
            (
                f"\\put({origin + 8:.1f},{bottom + height / 2:.2f})"
                f"{{\\rotatebox{{90}}{{\\makebox(0,0){{\\scriptsize {y_label}}}}}}}"
            ),
        ]
    )
    return output


def _render(rows: list[dict[str, str]]) -> str:
    time_medians = _fit_points(rows, "solver_total_seconds")
    memory_medians = _fit_points(rows, "peak_memory_bytes")
    time_model = _log_regression(time_medians)
    memory_model = _log_regression(memory_medians)

    expected = (
        (time_model, 9.542218, 0.882937, 1.348002),
        (memory_model, 4.449258, 0.771573, 0.939223),
    )
    for model, slope, r_squared, rmse in expected:
        if not (
            math.isclose(model["slope"], slope, abs_tol=5e-7)
            and math.isclose(model["r_squared"], r_squared, abs_tol=5e-7)
            and math.isclose(model["rmse"], rmse, abs_tol=5e-7)
        ):
            raise RuntimeError(f"regressao inesperada: {model}")

    completed_time = [
        (float(row["dimension"]), float(row["solver_total_seconds"]))
        for row in rows
        if row["status"] == "optimal"
    ]
    completed_memory = [
        (float(row["dimension"]), float(row["peak_memory_bytes"]) / (1024**2))
        for row in rows
        if row["status"] == "optimal"
    ]
    censored_memory = [
        (float(row["dimension"]), float(row["peak_memory_bytes"]) / (1024**2))
        for row in rows
        if row["status"] == "timeout"
    ]
    timeout_counts = Counter(int(row["dimension"]) for row in rows if row["status"] == "timeout")

    time_mantissa, time_exponent = _scientific(time_model["coefficient"], 2)
    time_equation = (
        f"$t={time_mantissa}\\!\\times\\!10^{{{time_exponent}}}"
        f"n^{{{_decimal(time_model['slope'], 3)}}}$ s"
    )
    memory_equation = (
        f"$m={_decimal(memory_model['coefficient'], 2)}"
        f"n^{{{_decimal(memory_model['slope'], 3)}}}$ bytes"
    )

    memory_model_mib = dict(memory_model)
    memory_model_mib["coefficient"] /= 1024**2

    lines = [
        "% Gerado por scripts/generate_report_plots.py; nao editar manualmente.",
        f"% Fonte: {SOURCE.relative_to(ROOT).as_posix()}",
        f"% SHA-256: {EXPECTED_SHA256}",
        "% Ajuste: medianas das dez instancias com 5/5 provas; timeouts excluidos.",
        "\\begingroup",
        "\\setlength{\\unitlength}{1pt}",
        "\\begin{picture}(510,215)",
    ]
    lines.extend(
        _panel(
            origin=0.0,
            title="(a) Tempo",
            y_label="Tempo do solver (s; escala log)",
            y_limits=(0.003, 3000.0),
            y_ticks=[
                (0.01, "0,01"),
                (0.1, "0,1"),
                (1.0, "1"),
                (10.0, "10"),
                (100.0, "100"),
                (1000.0, "1.000"),
            ],
            completed=completed_time,
            censored=[],
            medians=time_medians,
            model=time_model,
            equation=time_equation,
            aggregate_censored=timeout_counts,
        )
    )
    lines.extend(
        _panel(
            origin=255.0,
            title="(b) Memória",
            y_label="Pico residente (MiB; escala log)",
            y_limits=(8.0, 16384.0),
            y_ticks=[
                (32.0, "32"),
                (128.0, "128"),
                (512.0, "512"),
                (2048.0, "2.048"),
                (8192.0, "8.192"),
            ],
            completed=completed_memory,
            censored=censored_memory,
            medians=[(dimension, value / (1024**2)) for dimension, value in memory_medians],
            model=memory_model_mib,
            equation=memory_equation,
        )
    )

    lines.extend(
        [
            "{",
            _colour(RAW_COLOUR),
            "\\put(61,5){\\circle{2.50}}",
            "}",
            "\\put(67,5){\\makebox(0,0)[l]{\\tiny prova (54)}}",
            "{",
            _colour(TIME_COLOUR),
            "\\put(173,5){\\circle*{3.40}}",
            "}",
            "\\put(180,5){\\makebox(0,0)[l]{\\tiny mediana no ajuste (10)}}",
            "{",
            _colour(CENSORED_COLOUR),
            "\\linethickness{0.70pt}",
            *_triangle(334, 5),
            "}",
            "\\put(341,5){\\makebox(0,0)[l]{\\tiny timeout (21; excluído)}}",
            "\\end{picture}",
            "\\endgroup",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    rows = _read_rows()
    OUTPUT.write_text(_render(rows), encoding="utf-8", newline="\n")
    print(f"Figura atualizada em {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
