from unittest.mock import MagicMock

import pytest
from qtpy.QtWidgets import QWidget

from napari._qt._qapp_model.injection._qprocessors import (
    _add_plugin_dock_widget,
)


def test_add_plugin_dock_widget(qtbot):
    widget = QWidget()
    viewer = MagicMock()
    qtbot.addWidget(widget)
    with pytest.raises(RuntimeError, match='No current `Viewer` found'):
        _add_plugin_dock_widget((widget, 'widget'))
    _add_plugin_dock_widget((widget, 'widget'), viewer)
    viewer.window.add_dock_widget.assert_called_with(widget, name='widget')
