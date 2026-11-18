"""Medição portátil do pico de memória residente do processo worker."""

from __future__ import annotations

import os
import sys
import tracemalloc
from dataclasses import dataclass


@dataclass(slots=True)
class PeakMemorySampler:
    """Consulta o high-water mark de memória com a melhor API disponível."""

    method: str
    _windows_query: object | None = None
    _fallback_peak: int = 0

    @classmethod
    def create(cls) -> PeakMemorySampler:
        if os.name == "nt":
            try:
                return cls(
                    method="Windows GetProcessMemoryInfo PeakWorkingSetSize",
                    _windows_query=_make_windows_query(),
                )
            except (AttributeError, OSError):
                pass
        else:
            try:
                import resource

                resource.getrusage(resource.RUSAGE_SELF)
                unit = "bytes" if sys.platform == "darwin" else "KiB"
                return cls(method=f"getrusage(RUSAGE_SELF).ru_maxrss ({unit})")
            except ImportError:
                pass

        tracemalloc.start()
        return cls(method="tracemalloc Python allocation peak (fallback)")

    def peak_bytes(self) -> int:
        """Retorna o maior pico conhecido, sempre normalizado para bytes."""

        measured = 0
        if self._windows_query is not None:
            measured = int(self._windows_query())  # type: ignore[operator]
        elif self.method.startswith("getrusage"):
            import resource

            raw = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
            measured = raw if sys.platform == "darwin" else raw * 1024
        else:
            _, measured = tracemalloc.get_traced_memory()
        self._fallback_peak = max(self._fallback_peak, measured)
        return self._fallback_peak


def _make_windows_query() -> object:
    """Cria uma função que consulta ``PeakWorkingSetSize`` do processo atual."""

    import ctypes
    from ctypes import wintypes

    class ProcessMemoryCounters(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    get_current_process = ctypes.windll.kernel32.GetCurrentProcess
    get_current_process.restype = wintypes.HANDLE
    get_process_memory_info = ctypes.windll.psapi.GetProcessMemoryInfo
    get_process_memory_info.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(ProcessMemoryCounters),
        wintypes.DWORD,
    ]
    get_process_memory_info.restype = wintypes.BOOL
    process = get_current_process()

    def query() -> int:
        counters = ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        if not get_process_memory_info(process, ctypes.byref(counters), counters.cb):
            raise OSError(ctypes.get_last_error(), "GetProcessMemoryInfo falhou")
        return int(counters.PeakWorkingSetSize)

    query()
    return query
