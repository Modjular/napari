"""A backend-agnostic registry mapping model classes to visual classes.

Promotes the MRO-walk-first-match dispatch that used to live as two plain
module-level dicts in `napari._vispy.utils.visual` (`layer_to_visual`,
`overlay_to_visual`) into a reusable class. The dispatch mechanism itself --
"find the closest registered parent class of this model object's type" --
has nothing to do with vispy; only the *entries* (which concrete visual
class handles which model class) are backend-specific, and those are still
registered by `napari._vispy` alone.

A second backend would populate its own `VisualRegistry` instance the same
way `napari._vispy` does, without needing to touch this module at all --
`test_registry.py::test_third_party_layer_and_visual_registration` proves
this by registering a throwaway fake layer/visual pair from the test itself.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from napari._canvas._protocols import (
        LayerVisualProtocol,
        OverlayVisualProtocol,
    )
    from napari.components.overlays import Overlay
    from napari.layers import Layer

__all__ = ['VisualRegistry']

_M = TypeVar('_M')
_V = TypeVar('_V')


def _lookup_by_mro(mapping: dict[type[_M], _V], obj: _M) -> _V:
    for cls in obj.__class__.mro():
        if cls in mapping:
            return mapping[cls]
    raise TypeError(
        f'No visual registered for {type(obj)} or any parent class'
    )


class VisualRegistry:
    """Maps napari model classes to the visual classes that render them.

    Two independent registries live on one instance -- layers and overlays
    -- since a model object is always unambiguously one or the other, but
    the lookup/registration mechanism is identical for both.
    """

    def __init__(self) -> None:
        self._layer_visuals: dict[type[Layer], type[LayerVisualProtocol]] = {}
        self._overlay_visuals: dict[
            type[Overlay], type[OverlayVisualProtocol]
        ] = {}

    def register_layer_visual(
        self, layer_cls: type[Layer], visual_cls: type[LayerVisualProtocol]
    ) -> None:
        self._layer_visuals[layer_cls] = visual_cls

    def register_overlay_visual(
        self,
        overlay_cls: type[Overlay],
        visual_cls: type[OverlayVisualProtocol],
    ) -> None:
        self._overlay_visuals[overlay_cls] = visual_cls

    def create_layer_visual(
        self, layer: Layer, *args: Any, **kwargs: Any
    ) -> LayerVisualProtocol:
        """Create the visual for `layer`, based on its closest registered type."""
        visual_cls = _lookup_by_mro(self._layer_visuals, layer)
        return visual_cls(layer, *args, **kwargs)

    def create_overlay_visual(
        self, overlay: Overlay, **kwargs: Any
    ) -> OverlayVisualProtocol:
        """Create the visual for `overlay`, based on its closest registered type."""
        visual_cls = _lookup_by_mro(self._overlay_visuals, overlay)
        return visual_cls(overlay=overlay, **kwargs)
