"""The Window class is the primary entry to the napari GUI.

`Window` is dispatched, based on `napari._backend.get_backend()`, to a
concrete backend implementation -- today, always
:class:`napari._qt.qt_main_window.Window`. `WindowProtocol` documents the
surface a backend's `Window` must provide; a backend doesn't need to
subclass it explicitly, since `Protocol` conformance is structural.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from napari._backend import Backend, get_backend

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

    import numpy as np

__all__ = ['Window', 'WindowProtocol']


@runtime_checkable
class WindowProtocol(Protocol):
    """The `Window` surface napari's core and plugins rely on.

    Deliberately excludes the deprecated `qt_viewer` property and the
    private `_qt_viewer` attribute some code still reaches through directly
    -- neither is part of the cross-backend contract.
    """

    def export_figure(
        self, path: str | None = None, scale: float = 1, flash: bool = True
    ) -> np.ndarray: ...

    def export_rois(
        self,
        rois: list[np.ndarray],
        paths: str | Path | list[str | Path] | None = None,
        scale: float = 1.0,
    ) -> list: ...

    def screenshot(
        self,
        path: str | Path | None = None,
        size: tuple[int, int] | None = None,
        scale: float | None = None,
        flash: bool = True,
        canvas_only: bool = False,
    ) -> np.ndarray: ...

    def show(self, *, block: bool = False) -> None: ...

    def close(self) -> None: ...

    def add_plugin_dock_widget(
        self,
        plugin_name: str,
        widget_name: str | None = None,
        tabify: bool = False,
    ) -> tuple[Any, Any]: ...

    def add_dock_widget(
        self,
        widget: Any,
        *,
        name: str = '',
        area: str | None = None,
        allowed_areas: Sequence[str] | None = None,
        tabify: bool = False,
        **kwargs: Any,
    ) -> Any: ...

    @property
    def dock_widgets(self) -> Mapping[str, Any]: ...

    def remove_dock_widget(self, widget: Any, menu: Any = None) -> None: ...

    def add_function_widget(
        self,
        function: Any,
        *,
        magic_kwargs: dict | None = None,
        name: str = '',
        area: str | None = None,
        allowed_areas: Sequence[str] | None = None,
    ) -> Any: ...

    def resize(self, width: int, height: int) -> None: ...

    def set_geometry(
        self, left: int, top: int, width: int, height: int
    ) -> None: ...

    def geometry(self) -> tuple[int, int, int, int]: ...

    def activate(self) -> None: ...


def _resolve_window_cls() -> type:
    backend = get_backend()
    if backend == Backend.qt:
        from napari._qt import Window as _QtWindow

        return _QtWindow
    raise RuntimeError(f'Unknown napari GUI backend: {backend!r}')


try:
    Window = _resolve_window_cls()

except (ImportError, RuntimeError) as e:
    err = e

    class Window:  # type: ignore
        def __init__(self, *args, **kwargs) -> None:
            pass

        def close(self):
            pass

        def __getattr__(self, name):
            raise type(err)(
                'An error occured when importing Qt dependencies.  Cannot show napari window.  See cause above'
            ) from err
