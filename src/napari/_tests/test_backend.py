import importlib

import pytest

from napari import _backend
from napari._backend import Backend, get_backend, set_backend


def test_get_set_backend_roundtrip():
    original = get_backend()
    try:
        prev = set_backend(Backend.qt)
        assert prev == original
        assert get_backend() == Backend.qt
    finally:
        set_backend(original)


def test_set_backend_accepts_str():
    original = get_backend()
    try:
        set_backend('qt')
        assert get_backend() == Backend.qt
    finally:
        set_backend(original)


def test_set_backend_unknown_raises():
    original = get_backend()
    with pytest.raises(ValueError, match='bogus'):
        set_backend('bogus')
    # a failed set_backend must not mutate the current backend
    assert get_backend() == original


def test_napari_backend_env_var_honored(monkeypatch):
    monkeypatch.setenv('NAPARI_BACKEND', 'qt')
    try:
        importlib.reload(_backend)
        assert _backend.get_backend() == _backend.Backend.qt
    finally:
        monkeypatch.delenv('NAPARI_BACKEND', raising=False)
        importlib.reload(_backend)


def test_napari_backend_env_var_unknown_raises(monkeypatch):
    monkeypatch.setenv('NAPARI_BACKEND', 'bogus')
    try:
        with pytest.raises(ValueError, match='bogus'):
            importlib.reload(_backend)
    finally:
        monkeypatch.delenv('NAPARI_BACKEND', raising=False)
        importlib.reload(_backend)
