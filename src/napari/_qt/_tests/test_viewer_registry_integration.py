from qtpy.QtWidgets import QWidget

from napari.utils._viewer_registry import lookup_viewer_for_widget


def test_add_dock_widget_registers_viewer(make_napari_viewer, qtbot):
    viewer = make_napari_viewer()
    widget = QWidget()
    qtbot.addWidget(widget)

    dock_widget = viewer.window.add_dock_widget(widget, name='test')

    assert lookup_viewer_for_widget(widget) is viewer
    assert lookup_viewer_for_widget(dock_widget) is viewer

    viewer.window.remove_dock_widget(widget)

    assert lookup_viewer_for_widget(widget) is None
    assert lookup_viewer_for_widget(dock_widget) is None


def test_add_function_widget_registers_viewer(make_napari_viewer, qtbot):
    viewer = make_napari_viewer()

    def do_nothing():
        pass

    dock_widget = viewer.window.add_function_widget(do_nothing)
    qtbot.addWidget(dock_widget)

    assert lookup_viewer_for_widget(dock_widget) is viewer
