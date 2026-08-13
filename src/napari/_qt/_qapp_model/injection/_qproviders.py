"""Qt providers.

Non-Qt providers can be found in `napari/_app_model/injection/_providers.py`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from napari._app_model import get_app_model

if TYPE_CHECKING:
    from collections.abc import Callable

    from napari._qt.qt_main_window import Window
    from napari._qt.qt_viewer import QtViewer


def _provide_qt_viewer() -> QtViewer | None:
    from napari._qt.qt_main_window import _QtMainWindow

    if _qmainwin := _QtMainWindow.current():
        return _qmainwin._qt_viewer
    return None


def _provide_qt_viewer_or_raise(msg: str = '') -> QtViewer:
    qt_viewer = _provide_qt_viewer()
    if qt_viewer:
        return qt_viewer
    if msg:
        msg = ' ' + msg
    raise RuntimeError(f'No current `QtViewer` found.{msg}')


def _provide_window() -> Window | None:
    from napari._qt.qt_main_window import _QtMainWindow

    if _qmainwin := _QtMainWindow.current():
        return _qmainwin._window
    return None


def _provide_window_or_raise(msg: str = '') -> Window:
    window = _provide_window()
    if window:
        return window
    if msg:
        msg = ' ' + msg
    raise RuntimeError(f'No current `Window` found.{msg}')


def register_qt_types() -> None:
    from napari._qt.qt_viewer import QtViewer

    app = get_app_model()
    if 'QtViewer' not in app.injection_store.namespace:
        app.injection_store.namespace = {
            **app.injection_store.namespace,
            'QtViewer': QtViewer,
        }


# syntax could be simplified after
# https://github.com/tlambert03/in-n-out/issues/31
QPROVIDERS: list[tuple[Callable]] = [
    (_provide_qt_viewer,),
    (_provide_window,),
]
