"""Auto-repeat behaviour of the vispy key-event adapter.

Moved here from ``napari/utils/_tests/test_key_bindings.py`` along with the
adapter itself: these drive ``napari._vispy.key_bindings.on_key_press`` with
vispy-shaped events, so they need vispy. The core keymap tests do not.
"""

import types

import pytest
from vispy.util import keys

from napari._vispy.key_bindings import on_key_press
from napari.utils.key_bindings import KeymapHandler, KeymapProvider


def _key_event(name, *, auto_repeat, modifiers=()):
    """Minimal stand-in for the vispy key event `on_key_press` consumes."""
    return types.SimpleNamespace(
        key=types.SimpleNamespace(name=name),
        modifiers=list(modifiers),
        native=types.SimpleNamespace(isAutoRepeat=lambda: auto_repeat),
        handled=False,
    )


def _press(handler, name, *, held_for=0, modifiers=()):
    """Send one real press followed by `held_for` auto-repeats."""
    on_key_press(
        handler, _key_event(name, auto_repeat=False, modifiers=modifiers)
    )
    for _ in range(held_for):
        on_key_press(
            handler, _key_event(name, auto_repeat=True, modifiers=modifiers)
        )


def _handler_with_provider():
    """A fresh handler and its own provider class, isolated per test."""

    class Foo(KeymapProvider): ...

    handler = KeymapHandler()
    handler.keymap_providers = [Foo()]
    return handler, Foo


@pytest.mark.parametrize('key', ['Up', 'Down', 'Left', 'Right'])
def test_navigation_keys_autorepeat_however_they_are_bound(key):
    """Held navigation keys repeat even when bound through `bind_key` (#9203).

    The old `repeatables` set held the nav keys as `str` literals, which never
    `==`-match the `KeyBinding` tested against them, so a nav key bound via
    `bind_key` fired once no matter how long it was held.
    """
    handler, Foo = _handler_with_provider()
    presses = []

    @Foo.bind_key(key)
    def _count(x):
        presses.append(1)

    _press(handler, key, held_for=4)
    assert len(presses) == 5  # initial press plus every auto-repeat


def test_non_navigation_keys_still_do_not_autorepeat():
    """The exemption is scoped: an ordinary bound key still fires once."""
    handler, Foo = _handler_with_provider()
    presses = []

    @Foo.bind_key('K')
    def _count(x):
        presses.append(1)

    _press(handler, 'K', held_for=4)
    assert len(presses) == 1  # auto-repeats filtered out


def test_modified_navigation_keys_still_do_not_autorepeat():
    """A modified arrow is a different KeyBinding than the bare one, so it stays
    filtered -- pinning the exemption to exactly the four bare nav keys.

    Uses Alt, not Control: vispy's CONTROL maps to KeyMod.CtrlCmd, spelled
    `Meta+` on macOS but `Ctrl+` by `bind_key`, so a Control test would miss the
    binding for reasons unrelated to auto-repeat.
    """
    handler, Foo = _handler_with_provider()
    presses = []

    @Foo.bind_key('Alt+Up')
    def _count(x):
        presses.append(1)

    _press(handler, 'Up', held_for=4, modifiers=[keys.ALT])
    assert len(presses) == 1  # bound and fired, but auto-repeats filtered out
