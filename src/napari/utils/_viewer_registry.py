"""A backend-agnostic widget -> viewer registry.

Some code needs to recover "the `Viewer` this widget belongs to" starting
from an arbitrary frontend widget (e.g. magicgui's `find_viewer_ancestor`).
Historically that walked a Qt-specific widget parent chain -- this module
gives frontends a way to register that association directly instead, so
the lookup doesn't require Qt at all.

Scope: this only covers *directly registered* top-level widgets (whatever
was passed to `add_dock_widget`/`add_plugin_dock_widget`/`add_function_widget`),
not arbitrary descendants nested inside them. Finding the owning viewer for
an arbitrary nested widget still needs a frontend-specific walk (e.g. the
Qt parent-chain walk in `utils/_magicgui.py::find_viewer_ancestor`).
"""

from __future__ import annotations

from contextlib import suppress
from typing import TYPE_CHECKING
from weakref import WeakKeyDictionary

if TYPE_CHECKING:
    from napari.viewer import Viewer

_WIDGET_VIEWERS: WeakKeyDictionary[object, Viewer] = WeakKeyDictionary()


def register_widget_viewer(widget: object, viewer: Viewer) -> None:
    """Associate `widget` with the `Viewer` that owns it.

    Also registers under `widget.native` when present, so callers don't
    need to know whether they're holding a magicgui `Widget` or the
    underlying native widget it wraps. A `widget` that doesn't support weak
    references (e.g. a plain `list`, which some callers pass to combine
    multiple widgets into one dock) is silently skipped -- there's nothing
    to key a weak registry on.
    """
    with suppress(TypeError):
        _WIDGET_VIEWERS[widget] = viewer
    native = getattr(widget, 'native', None)
    if native is not None:
        with suppress(TypeError):
            _WIDGET_VIEWERS[native] = viewer


def unregister_widget(widget: object) -> None:
    """Remove any viewer association for `widget` (and its `.native`)."""
    with suppress(TypeError):
        _WIDGET_VIEWERS.pop(widget, None)
    native = getattr(widget, 'native', None)
    if native is not None:
        with suppress(TypeError):
            _WIDGET_VIEWERS.pop(native, None)


def lookup_viewer_for_widget(widget: object) -> Viewer | None:
    """Return the `Viewer` registered for `widget`, or `widget.native`."""
    with suppress(TypeError):
        viewer = _WIDGET_VIEWERS.get(widget)
        if viewer is not None:
            return viewer
    native = getattr(widget, 'native', None)
    if native is not None:
        with suppress(TypeError):
            return _WIDGET_VIEWERS.get(native)
    return None
