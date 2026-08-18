"""Protocols describing the renderer-agnostic shape of a napari canvas.

`CanvasProtocol` documents the surface `napari._vispy.canvas.VispyCanvas`
already provides today, minus the parts that are inherently backend-specific
(cursor handling, screenshotting, key-event forwarding -- these reach into
Qt with no vispy-generic equivalent, and are addressed separately) and minus
`qthrottled`-based mouse-move throttling, which is deliberately never part of
this contract: throttling a callback is an internal performance detail each
backend handles its own way (e.g. a web backend would use
`requestAnimationFrame`), not something a second backend needs to conform to.

A backend does not need to subclass `CanvasProtocol` explicitly, since
`Protocol` conformance is structural -- this mirrors `napari.window`'s
`WindowProtocol` precedent.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from napari.components import ViewerModel
    from napari.layers import Layer

__all__ = ['CanvasProtocol']


@runtime_checkable
class CanvasProtocol(Protocol):
    """The renderer-agnostic surface of a napari canvas controller."""

    viewer: ViewerModel
    layer_to_visual: dict[Layer, Any]
    max_texture_sizes: tuple[int, int] | None

    @property
    def events(self) -> Any: ...

    @property
    def central_widget(self) -> Any: ...

    @property
    def size(self) -> tuple[int, int]: ...

    @size.setter
    def size(self, size: tuple[int, int]) -> None: ...

    def _on_bgcolor_change(self) -> None: ...

    def _on_interactive(self) -> None: ...

    def _on_boxzoom(
        self, zoom_area: tuple[tuple[float, float], tuple[float, float]]
    ) -> None: ...

    def _map_canvas2world(
        self, position: tuple[int, ...], view: Any
    ) -> tuple[float, float]: ...

    def _get_viewbox_at(self, position: Any) -> tuple[Any, Any]: ...

    def _on_mouse_double_click(self, event: Any) -> None: ...

    def _on_mouse_move(self, event: Any) -> None: ...

    def _on_mouse_press(self, event: Any) -> None: ...

    def _on_mouse_release(self, event: Any) -> None: ...

    def _on_mouse_wheel(self, event: Any) -> None: ...

    def _on_vispy_size_change(self, event: Any) -> None: ...

    def _on_model_size_change(self) -> None: ...

    def add_layer_visual_mapping(
        self, napari_layer: Layer, vispy_layer: Any
    ) -> None: ...

    def on_draw(self, event: Any = None) -> None: ...

    def _remove_layer(self, event: Any) -> None: ...

    def _reorder_layers(self) -> None: ...

    def _update_viewer_overlays(self) -> None: ...

    def _update_layer_overlays(self, layer: Layer) -> None: ...

    def _update_overlay_canvas_positions(self, event: Any = None) -> None: ...

    def _calculate_view_direction(
        self, event_pos: tuple[float, float]
    ) -> Any: ...

    def enable_dims_play(self, *args: Any) -> None: ...

    def _update_scenegraph(self, event: Any = None) -> None: ...

    def _update_grid_spacing(self) -> None: ...

    def _pause_scene_graph_update(self) -> None: ...

    def _resume_scene_graph_update(self) -> None: ...

    def font_info(self) -> Any: ...
