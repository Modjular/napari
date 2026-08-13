"""Translation of vispy key events into app-model key bindings.

This adapter lives in the vispy backend rather than in
``napari.utils.key_bindings`` because both the input type (a vispy key event)
and the auto-repeat check (``event.native.isAutoRepeat()``, a Qt call) are
frontend concerns. The core keymap machinery, ``KeymapHandler.press_key`` and
``.release_key``, takes an app-model ``KeyBinding`` and knows nothing about
either.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app_model.types import KeyCode, KeyMod
from vispy.util import keys

from napari.utils.key_bindings import KEY_SUBS, coerce_keybinding

if TYPE_CHECKING:
    from app_model.types import KeyBinding

    from napari.utils.key_bindings import KeymapHandler

_VISPY_SPECIAL_KEYS = [
    keys.SHIFT,
    keys.CONTROL,
    keys.ALT,
    keys.META,
    keys.UP,
    keys.DOWN,
    keys.LEFT,
    keys.RIGHT,
    keys.PAGEUP,
    keys.PAGEDOWN,
    keys.INSERT,
    keys.DELETE,
    keys.HOME,
    keys.END,
    keys.ESCAPE,
    keys.BACKSPACE,
    keys.F1,
    keys.F2,
    keys.F3,
    keys.F4,
    keys.F5,
    keys.F6,
    keys.F7,
    keys.F8,
    keys.F9,
    keys.F10,
    keys.F11,
    keys.F12,
    keys.SPACE,
    keys.ENTER,
    keys.TAB,
]

_VISPY_MODS = {
    keys.CONTROL: KeyMod.CtrlCmd,
    keys.SHIFT: KeyMod.Shift,
    keys.ALT: KeyMod.Alt,
    keys.META: KeyMod.WinCtrl,
}


def _vispy2appmodel(event) -> KeyBinding:
    key, modifiers = event.key.name, event.modifiers
    if len(key) == 1 and key.isalpha():  # it's a letter
        key = key.upper()
        cond = lambda m: True  # noqa: E731
    elif key in _VISPY_SPECIAL_KEYS:
        # remove redundant information i.e. an output of 'Shift-Shift'
        cond = lambda m: m != key  # noqa: E731
    else:
        # Shift is consumed to transform key

        # bug found on OSX: Command will cause Shift to not
        # transform the key so do not consume it
        # note: 'Control' is OSX Command key
        cond = lambda m: m != 'Shift' or 'Control' in modifiers  # noqa: E731

    kb = KeyCode.from_string(KEY_SUBS.get(key, key))

    for key in filter(lambda key: key in modifiers and cond(key), _VISPY_MODS):
        kb |= _VISPY_MODS[key]

    return coerce_keybinding(kb)


def on_key_press(handler: KeymapHandler, event) -> None:
    """Dispatch a vispy key press event through ``handler``.

    Parameters
    ----------
    handler : KeymapHandler
        The handler holding the keymap chain to dispatch against.
    event : vispy.util.event.Event
        The vispy key press event that triggered this call.
    """
    from napari.utils.action_manager import action_manager
    from napari.utils.key_bindings import KeyBinding

    if event.key is None:
        # TODO determine when None key could be sent.
        return

    kb = _vispy2appmodel(event)

    repeatables = {
        *action_manager._get_repeatable_shortcuts(handler.keymap_chain),
        # Nav keys are exempt however they were bound. They must be
        # KeyBinding, not str: the set is tested against a KeyBinding, which
        # never compares equal to a str, so str literals here silently never
        # matched and no key bound via bind_key() auto-repeated. See #9203.
        *(KeyBinding.from_str(key) for key in ('Up', 'Down', 'Left', 'Right')),
    }

    if (
        event.native is not None
        and event.native.isAutoRepeat()
        and kb not in repeatables
    ) or event.key is None:
        # pass if no key is present or if the shortcut combo is held down,
        # unless the combo being held down is one of the autorepeatables or
        # one of the navigation keys (helps with scrolling).
        return

    event.handled = handler.press_key(kb)


def on_key_release(handler: KeymapHandler, event) -> None:
    """Dispatch a vispy key release event through ``handler``.

    Parameters
    ----------
    handler : KeymapHandler
        The handler holding the keymap chain to dispatch against.
    event : vispy.util.event.Event
        The vispy key release event that triggered this call.
    """
    if event.key is None or (
        # on linux press down is treated as multiple press and release
        event.native is not None and event.native.isAutoRepeat()
    ):
        return
    kb = _vispy2appmodel(event)
    event.handled = handler.release_key(kb)
