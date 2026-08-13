"""Backend-agnostic providers.

Qt-specific providers can be found in
`napari/_qt/_qapp_model/injection/_qproviders.py`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from napari import components, layers, viewer
from napari.utils._proxies import PublicOnlyProxy
from napari.viewer import ViewerModel

if TYPE_CHECKING:
    from collections.abc import Callable


def _provide_viewer(public_proxy: bool = True) -> viewer.Viewer | None:
    """Provide `PublicOnlyProxy` (allows internal napari access) of current viewer."""
    if current_viewer := viewer.current_viewer():
        if public_proxy:
            return PublicOnlyProxy(current_viewer)
        return current_viewer
    return None


def _provide_viewer_model(public_proxy: bool = True) -> ViewerModel | None:
    """Provide a Viewer (subclass of ViewerModel) if ViewerModel is needed."""
    return _provide_viewer(public_proxy)


def _provide_viewer_or_raise(
    msg: str = '', public_proxy: bool = False
) -> viewer.Viewer:
    viewer = _provide_viewer(public_proxy)
    if viewer:
        return viewer
    if msg:
        msg = ' ' + msg
    raise RuntimeError(f'No current `Viewer` found.{msg}')


def _provide_active_layer() -> layers.Layer | None:
    return v.layers.selection.active if (v := _provide_viewer()) else None


def _provide_active_layer_list() -> components.LayerList | None:
    return v.layers if (v := _provide_viewer()) else None


# syntax could be simplified after
# https://github.com/tlambert03/in-n-out/issues/31
PROVIDERS: list[tuple[Callable]] = [
    (_provide_viewer,),
    (_provide_viewer_model,),
    (_provide_active_layer,),
    (_provide_active_layer_list,),
]
