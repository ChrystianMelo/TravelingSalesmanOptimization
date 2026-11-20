"""Instrumenta fases das aproximações sem acoplar métricas aos algoritmos."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from functools import wraps
from time import perf_counter
from typing import ParamSpec, TypeVar

PhaseName = str
MemoryQuery = Callable[[], int]
P = ParamSpec("P")
R = TypeVar("R")


@dataclass(slots=True)
class PhaseMeasurement:
    """Acumula chamadas, duração e high-water mark observado de uma fase."""

    calls: int = 0
    seconds: float = 0.0
    process_peak_bytes: int = 0


@dataclass(slots=True)
class ApproximationProfile:
    """Perfil mutável usado somente durante a construção da rota inicial.

    ``process_peak_bytes`` não é memória exclusiva nem incremental da fase. É o
    pico residente do processo observado logo depois de cada chamada, com o
    mesmo método usado pelo worker para a métrica global.
    """

    memory_query: MemoryQuery | None = None
    measurements: dict[PhaseName, PhaseMeasurement] = field(default_factory=dict)

    @contextmanager
    def measure(self, phase: PhaseName) -> Iterator[None]:
        measurement = self.measurements.setdefault(phase, PhaseMeasurement())
        measurement.calls += 1
        started = perf_counter()
        try:
            yield
        finally:
            measurement.seconds += perf_counter() - started
            if self.memory_query is not None:
                try:
                    measurement.process_peak_bytes = max(
                        measurement.process_peak_bytes,
                        int(self.memory_query()),
                    )
                except (OSError, RuntimeError, TypeError, ValueError):
                    # A instrumentação não deve invalidar uma rota correta se a
                    # consulta de memória deixar de estar disponível.
                    pass

    def value(self, phase: PhaseName) -> PhaseMeasurement:
        """Retorna a medição da fase ou um valor vazio imutável pelo chamador."""

        measurement = self.measurements.get(phase)
        if measurement is None:
            return PhaseMeasurement()
        return PhaseMeasurement(
            calls=measurement.calls,
            seconds=measurement.seconds,
            process_peak_bytes=measurement.process_peak_bytes,
        )


_ACTIVE_PROFILE: ContextVar[ApproximationProfile | None] = ContextVar(
    "active_approximation_profile",
    default=None,
)


@contextmanager
def collect_approximation_profile(
    memory_query: MemoryQuery | None = None,
) -> Iterator[ApproximationProfile]:
    """Ativa um perfil apenas no contexto lógico da chamada corrente."""

    profile = ApproximationProfile(memory_query=memory_query)
    token = _ACTIVE_PROFILE.set(profile)
    try:
        yield profile
    finally:
        _ACTIVE_PROFILE.reset(token)


def profiled_phase(phase: PhaseName) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decora uma subrotina sem alterar seu contrato quando não há coletor."""

    def decorate(function: Callable[P, R]) -> Callable[P, R]:
        @wraps(function)
        def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
            profile = _ACTIVE_PROFILE.get()
            if profile is None:
                return function(*args, **kwargs)
            with profile.measure(phase):
                return function(*args, **kwargs)

        return wrapped

    return decorate
