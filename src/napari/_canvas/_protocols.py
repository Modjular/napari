"""Protocols describing the renderer-agnostic shape of a napari canvas.

`CanvasProtocol` documents the surface `napari._vispy.canvas.VispyCanvas`
already provides today. `cursor`, `screenshot`, and `forward_key_event` are
declared but deliberately left backend-defined in what they accept/return
(`Any`): there is no vispy-generic or Qt-generic equivalent to share for
setting a native cursor value, grabbing a framebuffer, or forwarding a
native key event into a renderer's own event system -- each backend
implements these however its own platform requires, the same way
`WindowProtocol.screenshot` is just a signature with no shared body.
`qthrottled`-based mouse-move throttling is, by contrast, permanently
excluded rather than declared loosely: throttling a callback is an internal
performance detail each backend handles its own way (e.g. a web backend
would use `requestAnimationFrame`), not something a second backend needs to
conform to at all.

`LayerVisualProtocol` and `OverlayVisualProtocol` document the surfaces of
`napari._vispy.layers.base.VispyBaseLayer` and
`napari._vispy.overlays.base.VispyBaseOverlay` respectively -- the per-layer
and per-overlay visual objects a `CanvasProtocol` implementation creates and
drives. Conformance is currently verified only against the Image layer path
(`VispyImageLayer` and the viewer-level overlays that attach to it), per the
project's "proof of architecture, not shipping product" scope for this phase
-- see `_canvas/_tests/test_protocols.py`. Other layer types (Labels, Points,
Shapes, Surface, Vectors, Tracks) already subclass `VispyBaseLayer` and so
structurally satisfy `LayerVisualProtocol` too, but that isn't asserted here.

A backend does not need to subclass these Protocols explicitly, since
`Protocol` conformance is structural -- this mirrors `napari.window`'s
`WindowProtocol` precedent.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from napari.components import ViewerModel
    from napari.layers import Layer

__all__ = ['CanvasProtocol', 'LayerVisualProtocol', 'OverlayVisualProtocol']


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

    @property
    def cursor(self) -> Any: ...

    @cursor.setter
    def cursor(self, value: Any) -> None: ...

    def screenshot(self) -> Any: ...

    def forward_key_event(self, event_type: str, event: Any) -> None: ...

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


@runtime_checkable
class LayerVisualProtocol(Protocol):
    """The renderer-agnostic surface of a single layer's visual object.

    Mirrors `napari._vispy.layers.base.VispyBaseLayer`: 12 event
    connections funnel into ~11 handlers here (note all five transform
    events -- scale, translate, rotate, shear, affine -- funnel into the
    single `_on_matrix_change`; there is no `_on_scale_change`).
    """

    layer: Any

    @property
    def world_units(self) -> Any: ...

    @world_units.setter
    def world_units(self, value: Any) -> None: ...

    @property
    def translate(self) -> Any: ...

    @property
    def scale(self) -> Any: ...

    @property
    def order(self) -> int: ...

    @order.setter
    def order(self, order: int) -> None: ...

    def _on_data_change(self) -> None: ...

    def _on_refresh_change(self) -> None: ...

    def _on_visible_change(self) -> None: ...

    def _on_opacity_change(self) -> None: ...

    def _on_blending_change(self, event: Any = None) -> None: ...

    def _on_matrix_change(self) -> None: ...

    def _on_experimental_clipping_planes_change(self) -> None: ...

    def _on_camera_move(self, event: Any = None) -> None: ...

    def reset(self) -> None: ...

    def _on_poll(self, event: Any = None) -> None: ...

    def close(self) -> None: ...


@runtime_checkable
class OverlayVisualProtocol(Protocol):
    """The renderer-agnostic surface of a single overlay's visual object.

    Mirrors `napari._vispy.overlays.base.VispyBaseOverlay`, the base class
    shared by every overlay visual (scale bar, text, axes, bounding box,
    colorbar, and the canvas/scene-space subclasses built on top of it).
    """

    overlay: Any

    def _on_visible_change(self) -> None: ...

    def _on_opacity_change(self) -> None: ...

    def _on_blending_change(self) -> None: ...

    def reset(self) -> None: ...

    def close(self) -> None: ...
