"""napari GUI backend selection.

Selects which concrete implementation `napari.window.Window` and
`napari._event_loop.run` dispatch to. Only the `qt` backend exists today --
this module exists to give a second backend somewhere to plug into later,
without every dispatch site needing its own ad-hoc `try/except ImportError`.

Known limitation: `napari.window` and `napari._event_loop` resolve the
backend once, at first import (see those modules), so calling `set_backend`
after either has already been imported has no effect. This is acceptable for
now because no second backend exists yet to switch to; revisit once one does.
"""

import os
from enum import StrEnum


class Backend(StrEnum):
    """The GUI backends napari can dispatch its `Window`/event loop to."""

    qt = 'qt'


_backend: Backend = Backend(os.environ.get('NAPARI_BACKEND', Backend.qt))


def get_backend() -> Backend:
    """Get the napari GUI backend currently selected."""
    return _backend


def set_backend(backend: Backend | str) -> Backend:
    """Set the napari GUI backend to use.

    Parameters
    ----------
    backend : Backend or str
        The backend to select.

    Returns
    -------
    Backend
        The previously selected backend.
    """
    global _backend
    prev = _backend
    _backend = Backend(backend)
    return prev
