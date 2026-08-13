import logging

# set vispy logger to show warning and errors only
vispy_logger = logging.getLogger('vispy')
vispy_logger.setLevel(logging.WARNING)


def use_qt_app_backend() -> None:
    """Bind vispy's application backend to the installed Qt bindings.

    This is deliberately *not* done at import time. Selecting the backend
    requires importing ``qtpy``, which would make ``import napari._vispy``
    pull in Qt globally and prevent any non-Qt frontend from using the vispy
    canvas. Callers that need a Qt-backed vispy app (currently only
    :class:`~napari._vispy.canvas.VispyCanvas`) invoke this explicitly.
    """
    from qtpy import API_NAME
    from vispy import app

    app.use_app(API_NAME)


from napari._vispy.camera import VispyCamera
from napari._vispy.canvas import VispyCanvas
from napari._vispy.overlays.interaction_box import (
    VispySelectionBoxOverlay,
    VispyTransformBoxOverlay,
)
from napari._vispy.overlays.labels_polygon import VispyLabelsPolygonOverlay
from napari._vispy.overlays.scale_bar import VispyScaleBarOverlay
from napari._vispy.overlays.scene_axes import VispySceneAxesOverlay
from napari._vispy.overlays.text import VispyTextOverlay
from napari._vispy.utils.visual import create_vispy_layer, create_vispy_overlay

__all__ = [
    'VispyCamera',
    'VispyCanvas',
    'VispyLabelsPolygonOverlay',
    'VispyScaleBarOverlay',
    'VispySceneAxesOverlay',
    'VispySelectionBoxOverlay',
    'VispyTextOverlay',
    'VispyTransformBoxOverlay',
    'create_vispy_layer',
    'create_vispy_overlay',
]
