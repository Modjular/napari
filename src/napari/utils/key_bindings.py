"""Key combinations are represented in the form ``[modifier-]key``,
e.g. ``a``, ``Control-c``, or ``Control-Alt-Delete``.
Valid modifiers are Control, Alt, Shift, and Meta.

Letters will always be read as upper-case.
Due to the native implementation of the key system, Shift pressed in
certain key combinations may yield inconsistent or unexpected results.
Therefore, it is not recommended to use Shift with non-letter keys. On OSX,
Control is swapped with Meta such that pressing Command reads as Control.

Special keys include Shift, Control, Alt, Meta, Up, Down, Left, Right,
PageUp, PageDown, Insert, Delete, Home, End, Escape, Backspace, F1,
F2, F3, F4, F5, F6, F7, F8, F9, F10, F11, F12, Space, Enter, and Tab

Functions take in only one argument: the parent that the function
was bound to.

By default, all functions are assumed to work on key presses only,
but can be denoted to work on release too by separating the function
into two statements with the yield keyword::

    @viewer.bind_key('h')
    def hello_world(viewer):
        # on key press
        viewer.status = 'hello world!'

        yield

        # on key release
        viewer.status = 'goodbye world :('

To create a keymap that will block others, ``bind_key(..., ...)```.
"""

import inspect
import time
from collections import ChainMap
from collections.abc import Callable, Mapping
from types import EllipsisType, MethodType
from typing import Union

from app_model.types import KeyBinding, KeyCode

__all__ = [
    'KeyBinding',
    'KeyBindingLike',
    'KeyCode',
    'Keymap',
    'KeymapHandler',
    'KeymapProvider',
    'bind_key',
    'coerce_keybinding',
]

KeyBindingLike = Union[KeyBinding, str, int]
Keymap = Mapping[KeyBinding | EllipsisType, Callable | EllipsisType]

# global user keymap; to be made public later in refactoring process
USER_KEYMAP: Mapping[str, Callable] = {}

KEY_SUBS = {
    'Super': 'Meta',
    'Command': 'Meta',
    'Cmd': 'Meta',
    'Control': 'Ctrl',
    'Option': 'Alt',
}

_UNDEFINED = object()

# TODO: add this to app-model instead
KeyBinding.__hash__ = lambda self: hash(str(self))


def coerce_keybinding(key_bind: KeyBindingLike) -> KeyBinding:
    """Convert a keybinding-like object to a KeyBinding.

    Parameters
    ----------
    key_bind : keybinding-like
        Object to coerce.

    Returns
    -------
    key_bind : KeyBinding
        Object as KeyBinding.
    """
    if isinstance(key_bind, str):
        for k, v in KEY_SUBS.items():
            key_bind = key_bind.replace(k, v)

    return KeyBinding.validate(key_bind)


def bind_key(
    keymap: Keymap,
    key_bind: KeyBindingLike | EllipsisType,
    func=_UNDEFINED,
    *,
    overwrite=False,
):
    """Bind a key combination to a keymap.

    Parameters
    ----------
    keymap : dict of str: callable
        Keymap to modify.
    key_bind : keybinding-like or ...
        Key combination.
        ``...`` acts as a wildcard if no key combinations can be matched
        in the keymap (this will overwrite all key combinations
        further down the lookup chain).
    func : callable, None, or ...
        Callable to bind to the key combination.
        If ``None`` is passed, unbind instead.
        ``...`` acts as a blocker, effectively unbinding the key
        combination for all keymaps further down the lookup chain.
    overwrite : bool, keyword-only, optional
        Whether to overwrite the key combination if it already exists.

    Returns
    -------
    unbound : callable or None
        Callable unbound by this operation, if any.

    Notes
    -----
    Key combinations are represented in the form ``[modifier-]key``,
    e.g. ``a``, ``Control-c``, or ``Control-Alt-Delete``.
    Valid modifiers are Control, Alt, Shift, and Meta.

    Letters will always be read as upper-case.
    Due to the native implementation of the key system, Shift pressed in
    certain key combinations may yield inconsistent or unexpected results.
    Therefore, it is not recommended to use Shift with non-letter keys. On OSX,
    Control is swapped with Meta such that pressing Command reads as Control.

    Special keys include Shift, Control, Alt, Meta, Up, Down, Left, Right,
    PageUp, PageDown, Insert, Delete, Home, End, Escape, Backspace, F1,
    F2, F3, F4, F5, F6, F7, F8, F9, F10, F11, F12, Space, Enter, and Tab

    Functions take in only one argument: the parent that the function
    was bound to.

    By default, all functions are assumed to work on key presses only,
    but can be denoted to work on release too by separating the function
    into two statements with the yield keyword::

        @viewer.bind_key('h')
        def hello_world(viewer):
            # on key press
            viewer.status = 'hello world!'

            yield

            # on key release
            viewer.status = 'goodbye world :('

    To create a keymap that will block others, ``bind_key(..., ...)```.
    """
    if func is _UNDEFINED:

        def inner(func):
            bind_key(keymap, key_bind, func, overwrite=overwrite)
            return func

        return inner

    if key_bind is not Ellipsis:
        key_bind = coerce_keybinding(key_bind)

    if func is not None and key_bind in keymap and not overwrite:
        raise ValueError(
            f"keybinding {key_bind!s} already used! specify 'overwrite=True' to bypass this check"
        )

    unbound = keymap.pop(key_bind, None)

    if func is not None:
        if func is not Ellipsis and not callable(func):
            raise TypeError("'func' must be a callable")
        keymap[key_bind] = func

    return unbound


def _get_user_keymap() -> Keymap:
    """Retrieve the current user keymap. The user keymap is global and takes precedent over all other keymaps.

    Returns
    -------
    user_keymap : dict of str: callable
        User keymap.
    """
    return USER_KEYMAP


def _bind_user_key(
    key_bind: KeyBindingLike, func=_UNDEFINED, *, overwrite=False
):
    """Bind a key combination to the user keymap.

    See ``bind_key`` docs for details.
    """
    return bind_key(_get_user_keymap(), key_bind, func, overwrite=overwrite)


class KeybindingDescriptor:
    """Descriptor which transforms ``func`` into a method with the first
    argument bound to ``class_keymap`` or ``keymap`` depending on if it was
    called from the class or the instance, respectively.

    Parameters
    ----------
    func : callable
        Function to bind.
    """

    def __init__(self, func) -> None:
        self.__func__ = func

    def __get__(self, instance, cls):
        keymap = instance.keymap if instance is not None else cls.class_keymap
        return MethodType(self.__func__, keymap)


class KeymapProvider:
    """Mix-in to add keymap functionality.

    Attributes
    ----------
    class_keymap : dict
        Class keymap.
    keymap : dict
        Instance keymap.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._keymap = {}

    @property
    def keymap(self):
        return self._keymap

    @keymap.setter
    def keymap(self, value):
        self._keymap = {coerce_keybinding(k): v for k, v in value.items()}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        if 'class_keymap' not in cls.__dict__:
            # if in __dict__, was defined in class and not inherited
            cls.class_keymap = {}
        else:
            cls.class_keymap = {
                coerce_keybinding(k): v for k, v in cls.class_keymap.items()
            }

    bind_key = KeybindingDescriptor(bind_key)


def _bind_keymap(keymap, instance):
    """Bind all functions in a keymap to an instance.

    Parameters
    ----------
    keymap : dict
        Keymap to bind.
    instance : object
        Instance to bind to.

    Returns
    -------
    bound_keymap : dict
        Keymap with functions bound to the instance.
    """
    bound_keymap = {
        key: MethodType(func, instance) if func is not Ellipsis else func
        for key, func in keymap.items()
    }
    return bound_keymap


class KeymapHandler:
    """Handle key mapping and calling functionality.

    Attributes
    ----------
    keymap_providers : list of KeymapProvider
        Classes that provide the keymaps for this class to handle.
    """

    def __init__(self) -> None:
        super().__init__()
        self._key_release_generators = {}
        self.keymap_providers = []

    @property
    def keymap_chain(self):
        """collections.ChainMap: Chain of keymaps from keymap providers."""
        maps = [_get_user_keymap()]

        for parent in self.keymap_providers:
            maps.append(_bind_keymap(parent.keymap, parent))
            # For parent and superclasses add inherited keybindings
            for cls in parent.__class__.__mro__:
                if hasattr(cls, 'class_keymap'):
                    maps.append(_bind_keymap(cls.class_keymap, parent))

        return ChainMap(*maps)

    @property
    def active_keymap(self):
        """dict: Active keymap, created by resolving the keymap chain."""
        active_keymap = self.keymap_chain
        keymaps = active_keymap.maps

        for i, keymap in enumerate(keymaps):
            if Ellipsis in keymap:  # catch-all key
                # trim all keymaps after catch-all
                active_keymap = ChainMap(*keymaps[: i + 1])
                break

        active_keymap_final = {
            k: func
            for k, func in active_keymap.items()
            if func is not Ellipsis
        }

        return active_keymap_final

    def press_key(self, key_bind: KeyBindingLike) -> bool:
        """Simulate a key press to activate a keybinding.

        Parameters
        ----------
        key_bind : keybinding-like
            Key combination.
        """
        key_bind = coerce_keybinding(key_bind)
        keymap = self.active_keymap
        if key_bind in keymap:
            func = keymap[key_bind]
        elif Ellipsis in keymap:  # catch-all
            func = keymap[...]
        else:
            return False

        if func is Ellipsis:  # blocker
            return False
        if not callable(func):
            raise TypeError(f'expected {func} to be callable')

        generator_or_callback = func()

        key = str(key_bind.parts[-1].key)

        if inspect.isgeneratorfunction(func):
            try:
                next(generator_or_callback)  # call function
            except StopIteration:  # only one statement
                pass
            else:
                self._key_release_generators[key] = generator_or_callback
        if isinstance(generator_or_callback, Callable):
            self._key_release_generators[key] = (
                generator_or_callback,
                time.time(),
            )
        return True

    def release_key(self, key_bind: KeyBindingLike) -> bool:
        """Simulate a key release for a keybinding.

        Parameters
        ----------
        key_bind : keybinding-like
            Key combination.
        """
        from napari.settings import get_settings

        key_bind = coerce_keybinding(key_bind)
        key = str(key_bind.parts[-1].key)
        try:
            val = self._key_release_generators[key]
            # val could be callback function with time to check
            # if it should be called or generator that need to make
            # additional step on key release
            if isinstance(val, tuple):
                callback, start = val
                if (
                    time.time() - start
                    > get_settings().application.hold_button_delay
                ):
                    callback()
            else:
                next(val)  # call function
        except KeyError:
            return False
        except StopIteration:
            pass
        return True
