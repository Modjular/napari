import numpy as np

from napari._canvas import (
    CanvasProtocol,
    LayerVisualProtocol,
    OverlayVisualProtocol,
)
from napari._vispy.canvas import VispyCanvas
from napari._vispy.layers.image import VispyImageLayer
from napari._vispy.overlays.base import VispyBaseOverlay


def test_vispy_canvas_satisfies_canvas_protocol(qt_viewer):
    assert isinstance(qt_viewer.canvas, VispyCanvas)
    assert isinstance(qt_viewer.canvas, CanvasProtocol)


def test_vispy_image_layer_satisfies_layer_visual_protocol(qt_viewer):
    layer = qt_viewer.viewer.add_image(np.zeros((8, 8)))
    vispy_layer = qt_viewer.canvas.layer_to_visual[layer]

    assert isinstance(vispy_layer, VispyImageLayer)
    assert isinstance(vispy_layer, LayerVisualProtocol)


def test_image_path_overlays_satisfy_overlay_visual_protocol(qt_viewer):
    viewer = qt_viewer.viewer
    canvas = qt_viewer.canvas
    viewer.add_image(np.zeros((8, 8)))

    viewer.canvas.overlays.scale_bar.visible = True
    viewer.canvas.overlays.text.visible = True
    viewer.scene.overlays.axes.visible = True

    for overlay in (
        viewer.canvas.overlays.scale_bar,
        viewer.canvas.overlays.text,
        viewer.scene.overlays.axes,
    ):
        vispy_overlay = canvas._viewer_overlay_to_visual[overlay][0]
        assert isinstance(vispy_overlay, VispyBaseOverlay)
        assert isinstance(vispy_overlay, OverlayVisualProtocol)
