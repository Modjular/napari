"""Host system introspection, with fallbacks for restricted environments.

``psutil`` is a compiled package with no wheel for some platforms napari wants
to run on (notably Emscripten/WASM, where there is no OS to query in the first
place). It is only used to size caches, so a missing ``psutil`` should degrade
to a reasonable guess rather than prevent napari from being imported.
"""

from __future__ import annotations

# Used when the real amount of system memory cannot be determined. Deliberately
# conservative: every consumer takes a fraction of this to size a cache, so
# guessing low wastes some performance while guessing high risks exhausting
# memory on a small machine.
_FALLBACK_TOTAL_MEMORY = 4 * 1024**3  # 4 GiB


def total_memory_bytes() -> int:
    """Return total system memory in bytes.

    Falls back to a fixed, conservative estimate when ``psutil`` is not
    installed or cannot query the host.
    """
    try:
        from psutil import virtual_memory
    except ImportError:
        return _FALLBACK_TOTAL_MEMORY

    try:
        return int(virtual_memory().total)
    except Exception:  # noqa: BLE001  # pragma: no cover
        # psutil raises assorted OSError subclasses on locked-down or
        # virtualised hosts; none of them should stop napari from starting.
        return _FALLBACK_TOTAL_MEMORY
