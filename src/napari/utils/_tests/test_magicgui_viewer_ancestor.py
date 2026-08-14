"""find_viewer_ancestor's backend-agnostic registry path.

Deliberately separate from `_tests/test_magicgui.py`, which module-skips
without Qt bindings -- these tests assert `find_viewer_ancestor` works
*without* touching Qt at all, so they need to run even when Qt isn't
available.
"""

import builtins

from napari.utils._magicgui import find_viewer_ancestor
from napari.utils._viewer_registry import register_widget_viewer


class _FakeViewer:
    pass


class _FakeWidget:
    def parent(self):
        return None


def test_find_viewer_ancestor_uses_registry_first():
    widget = _FakeWidget()
    viewer = _FakeViewer()
    register_widget_viewer(widget, viewer)

    assert find_viewer_ancestor(widget) is viewer


def test_find_viewer_ancestor_falls_back_gracefully_without_qt(monkeypatch):
    """If Qt bindings aren't importable at all, a widget with no registry
    entry must fall back to current_viewer() instead of raising.
    """
    from napari.viewer import current_viewer

    expected = current_viewer()

    real_import = builtins.__import__

    def guard(name, *args, **kwargs):
        if name == 'napari._qt.widgets.qt_viewer_dock_widget':
            raise ImportError('simulated: no Qt bindings')
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, '__import__', guard)

    # unregistered widget, no viewer ancestor, Qt unavailable -> whatever
    # current_viewer() itself resolves to -- must not raise.
    assert find_viewer_ancestor(_FakeWidget()) is expected
