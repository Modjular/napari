"""Qt processors.

Non-Qt processors can be found in `napari/_app_model/injection/_processors.py`.
"""

from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Optional,
)

from magicgui.widgets import FunctionGui, Widget
from qtpy.QtWidgets import QWidget

from napari import viewer
from napari._app_model.injection._providers import _provide_viewer_or_raise

if TYPE_CHECKING:
    from collections.abc import Callable


def _add_plugin_dock_widget(
    widget_name_tuple: tuple[FunctionGui | QWidget | Widget, str],
    viewer: viewer.Viewer | None = None,
) -> None:
    if viewer is None:
        viewer = _provide_viewer_or_raise(
            msg='Widgets cannot be opened in headless mode.',
        )
    widget, full_name = widget_name_tuple
    viewer.window.add_dock_widget(widget, name=full_name)


QPROCESSORS: dict[object, Callable] = {
    Optional[
        tuple[FunctionGui | QWidget | Widget, str]
    ]: _add_plugin_dock_widget,
}
