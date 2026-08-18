from napari._canvas import CanvasProtocol
from napari._vispy.canvas import VispyCanvas


def test_vispy_canvas_satisfies_canvas_protocol(qt_viewer):
    assert isinstance(qt_viewer.canvas, VispyCanvas)
    assert isinstance(qt_viewer.canvas, CanvasProtocol)
