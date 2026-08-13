"""Error reporting for event callbacks.

Vendored and adapted from ``vispy.util.logs._handle_exception`` so that
napari's event system -- the foundation of the Qt-free model layer -- does not
import vispy, a rendering library unavailable on some target platforms.

Adaptations from the original: it logs through napari's own logger rather than
vispy's, and the ``node=`` reporting path (used by vispy's scene graph, never
by napari) has been dropped.

vispy is distributed under the 3-clause BSD licence:
Copyright (c) Vispy Development Team. All Rights Reserved.
"""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


def handle_callback_error(
    ignore_callback_errors: bool,
    print_callback_errors: str,
    obj: Any,
    cb_event: tuple[Callable, Any],
) -> None:
    """Report an exception raised inside an event callback.

    Must be called from within an ``except`` block.

    Parameters
    ----------
    ignore_callback_errors : bool
        If False, re-raise the active exception instead of reporting it.
    print_callback_errors : str
        One of ``'never'``, ``'first'``, ``'reminders'`` or ``'always'``.
        ``'first'`` logs only the first occurrence of a given callback/event
        pair; ``'reminders'`` additionally logs on a logarithmic schedule
        (the 2nd, 4th, 8th, ... occurrence).
    obj : Any
        The emitter. Used to hold the per-emitter occurrence registry.
    cb_event : tuple
        The ``(callback, event)`` pair that raised.
    """
    if not hasattr(obj, '_napari_err_registry'):
        obj._napari_err_registry = {}
    registry = obj._napari_err_registry

    cb, event = cb_event

    # Mirror what an unhandled exception would leave behind, so that
    # post-mortem debugging (`pdb.pm()`, `sys.last_traceback`) still works.
    type_, value, tb = sys.exc_info()
    if tb is not None:
        tb = tb.tb_next  # skip *this* frame
    sys.last_type = type_
    sys.last_value = value
    sys.last_traceback = tb
    del tb

    if not ignore_callback_errors:
        raise

    if print_callback_errors == 'never':
        return

    this_print: str | int | None = 'full'
    if print_callback_errors in ('first', 'reminders'):
        key = repr(cb) + repr(event)
        if key in registry:
            registry[key] += 1
            if print_callback_errors == 'first':
                this_print = None
            else:  # reminders
                ii = registry[key]
                # Log on powers of two: 1, 2, 4, 8, ...
                this_print = (
                    ii if ii == 2 ** int(ii.bit_length() - 1) else None
                )
        else:
            registry[key] = 1

    if this_print == 'full':
        # This function is only ever called from inside an `except` block, so
        # the active exception is the one we want to attach.
        logger.error('Invoking %s for %s', cb, event, exc_info=True)  # noqa: LOG014
    elif this_print is not None:
        logger.error('Invoking %s repeat %s', cb, this_print)
