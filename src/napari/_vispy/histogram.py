"""Vispy canvas hosting a histogram visual.

This exists so that the Qt histogram widget can consume vispy the same way
every other part of ``napari._qt`` does -- through ``napari._vispy`` -- rather
than importing ``vispy.scene`` directly.

It is deliberately a thin wrapper over the canvas/viewbox/visual trio, not a
renderer-agnostic histogram abstraction. A second rendering backend should
grow from the canvas protocol shared with the rest of the layer visuals, not
from a bespoke interface invented here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from vispy.scene import SceneCanvas, ViewBox

from napari._vispy.visuals.histogram import HistogramVisual

if TYPE_CHECKING:
    from qtpy.QtWidgets import QWidget


class VispyHistogramCanvas:
    """A vispy ``SceneCanvas`` displaying a single :class:`HistogramVisual`.

    Parameters
    ----------
    size : tuple of int
        Initial canvas size in pixels.
    bgcolor : str
        Initial canvas background colour, as a hex string.
    """

    def __init__(self, *, size: tuple[int, int], bgcolor: str) -> None:
        self._scene_canvas = SceneCanvas(
            size=size,
            bgcolor=bgcolor,
            keys=None,
        )

        self._view = ViewBox(parent=self._scene_canvas.scene)
        self._scene_canvas.central_widget.add_widget(self._view)

        self._histogram_visual = HistogramVisual()
        self._histogram_visual.parent = self._view.scene

        self._view.camera = 'panzoom'
        self._view.camera.set_range(x=(0, 1), y=(0, 1), margin=0.01)
        # Disable viewbox interaction to prevent accidental pan/zoom
        self._view.interactive = False

    @property
    def native(self) -> QWidget:
        """The backend-native widget, for embedding in a Qt layout."""
        return self._scene_canvas.native

    @property
    def histogram_visual(self) -> HistogramVisual:
        """The underlying visual. Exposed for tests and introspection."""
        return self._histogram_visual

    @property
    def bgcolor(self) -> Any:
        return self._scene_canvas.bgcolor

    @bgcolor.setter
    def bgcolor(self, color: str) -> None:
        self._scene_canvas.bgcolor = color

    def set_style(self, **kwargs: Any) -> None:
        """Set the histogram visual's colours. See `HistogramVisual.set_style`."""
        self._histogram_visual.set_style(**kwargs)

    def set_data(self, **kwargs: Any) -> None:
        """Set the histogram data. See `HistogramVisual.set_data`.

        Called with no arguments to clear the histogram.
        """
        self._histogram_visual.set_data(**kwargs)

    def update(self) -> None:
        """Request a redraw."""
        self._scene_canvas.update()

    def close(self) -> None:
        """Tear down the visual and the canvas."""
        self._histogram_visual.destroy()
        self._scene_canvas.close()
