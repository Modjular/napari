import gc

from napari.utils import _viewer_registry
from napari.utils._viewer_registry import (
    lookup_viewer_for_widget,
    register_widget_viewer,
    unregister_widget,
)


class _FakeViewer:
    pass


class _FakeWidget:
    pass


class _FakeWidgetWithNative:
    def __init__(self):
        self.native = _FakeWidget()


def test_register_lookup_unregister_roundtrip():
    widget = _FakeWidget()
    viewer = _FakeViewer()

    assert lookup_viewer_for_widget(widget) is None

    register_widget_viewer(widget, viewer)
    assert lookup_viewer_for_widget(widget) is viewer

    unregister_widget(widget)
    assert lookup_viewer_for_widget(widget) is None


def test_native_aliasing():
    widget = _FakeWidgetWithNative()
    viewer = _FakeViewer()

    register_widget_viewer(widget, viewer)
    # looking up either the wrapper or its native widget resolves
    assert lookup_viewer_for_widget(widget) is viewer
    assert lookup_viewer_for_widget(widget.native) is viewer

    unregister_widget(widget)
    assert lookup_viewer_for_widget(widget) is None
    assert lookup_viewer_for_widget(widget.native) is None


def test_weakref_gc_clears_entry():
    viewer = _FakeViewer()
    widget = _FakeWidget()
    register_widget_viewer(widget, viewer)
    assert lookup_viewer_for_widget(widget) is viewer

    size_before = len(_viewer_registry._WIDGET_VIEWERS)
    del widget
    gc.collect()

    assert len(_viewer_registry._WIDGET_VIEWERS) == size_before - 1
