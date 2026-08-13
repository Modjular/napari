from unittest.mock import patch

import pytest

from napari.window import WindowProtocol, _resolve_window_cls


def test_window_satisfies_protocol(make_napari_viewer):
    viewer = make_napari_viewer()
    assert isinstance(viewer.window, WindowProtocol)


def test_resolve_window_cls_unknown_backend_raises():
    with (
        patch('napari.window.get_backend', return_value='bogus'),
        pytest.raises(RuntimeError, match='Unknown napari GUI backend'),
    ):
        _resolve_window_cls()
