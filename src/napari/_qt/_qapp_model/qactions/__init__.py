from __future__ import annotations

from functools import lru_cache, partial
from itertools import chain
from typing import TYPE_CHECKING

from napari._qt._qapp_model.injection._qprocessors import QPROCESSORS
from napari._qt._qapp_model.injection._qproviders import QPROVIDERS

if TYPE_CHECKING:
    from app_model.expressions import Context

# Submodules should be able to import from most modules, so to
# avoid circular imports, don't import submodules at the top level here,
# import them inside the init_qactions function.


@lru_cache  # see docstring: connects listeners once, replays are idempotent
def _register_qt_plugin_actions() -> None:
    """Register Qt-specific plugin sample/widget actions (samples menu,
    plugin widgets submenu) and keep them in sync with plugin state.

    Called by `_QtMainWindow.__init__` on every Window construction --
    deliberately *not* folded into `init_qactions`, whose static menubar
    actions truly must only ever be registered once (app-model raises on a
    duplicate command id). A plugin can gain new contributions after this
    first runs (most plugins declare everything upfront, but dynamic/test
    plugins can mutate their manifest in place without emitting a
    registration event), so callers that need to pick that up call
    `_register_qt_plugin_actions.cache_clear()` then this again -- safe to
    do without touching `init_qactions`' own cache. `_register_qt_actions`
    itself tolerates being called more than once for the same manifest.

    napari.plugins._npe2 stays Qt-agnostic by not importing us; instead we
    listen for the same npe2 plugin-manager events it does, scoped to just
    this Qt-specific half of plugin action registration.
    """
    from npe2 import plugin_manager as pm

    from napari._qt._qplugins import _register_qt_actions
    from napari.plugins._npe2 import iter_enabled_manifests

    def _on_plugin_enablement_change_qt(
        enabled: set[str], disabled: set[str]
    ) -> None:
        manifests = (
            pm.get_manifest(name) for name in enabled if name in pm.instance()
        )
        for mf in iter_enabled_manifests(manifests):
            _register_qt_actions(mf)

    def _on_plugins_registered_qt(manifests) -> None:
        for mf in iter_enabled_manifests(manifests):
            _register_qt_actions(mf)

    pm.instance().events.enablement_changed.connect(
        _on_plugin_enablement_change_qt
    )
    pm.instance().events.plugins_registered.connect(_on_plugins_registered_qt)

    # replay for plugins already registered/enabled before this call (the
    # common case -- plugin discovery runs in Viewer.__init__, before
    # Window.__init__ / init_qactions)
    for mf in iter_enabled_manifests(pm.instance().iter_manifests()):
        _register_qt_actions(mf)


@lru_cache  # only call once
def init_qactions() -> None:
    """Initialize all Qt-based Actions with app-model

    This function will be called in _QtMainWindow.__init__().  It should only
    be called once (hence the lru_cache decorator).

    It is responsible for:
    - injecting Qt-specific names into the application injection_store namespace
      (this is what allows functions to be declared with annotations like
      `def foo(window: Window)` or `def foo(qt_viewer: QtViewer)`)
    - registering provider functions for the names added to the namespace
    - registering Qt-dependent actions with app-model (i.e. Q_*_ACTIONS actions).
    """
    from napari._app_model import get_app_model
    from napari._qt._qapp_model.qactions._debug import (
        DEBUG_SUBMENUS,
        Q_DEBUG_ACTIONS,
    )
    from napari._qt._qapp_model.qactions._file import (
        Q_FILE_ACTIONS,
    )
    from napari._qt._qapp_model.qactions._help import Q_HELP_ACTIONS
    from napari._qt._qapp_model.qactions._layerlist_context import (
        Q_LAYERLIST_CONTEXT_ACTIONS,
    )
    from napari._qt._qapp_model.qactions._layers_actions import (
        LAYERS_ACTIONS,
        LAYERS_SUBMENUS,
    )
    from napari._qt._qapp_model.qactions._plugins import Q_PLUGINS_ACTIONS
    from napari._qt._qapp_model.qactions._view import (
        Q_VIEW_ACTIONS,
    )
    from napari._qt._qapp_model.qactions._window import Q_WINDOW_ACTIONS
    from napari._qt.qt_main_window import Window
    from napari._qt.qt_viewer import QtViewer

    # update the namespace with the Qt-specific types/providers/processors
    app = get_app_model()
    store = app.injection_store
    store.namespace = {
        **store.namespace,
        'Window': Window,
        'QtViewer': QtViewer,
    }

    # Qt-specific providers/processors
    app.injection_store.register(
        processors=QPROCESSORS,
        providers=QPROVIDERS,
    )

    # Note: Qt-specific plugin sample/widget actions (samples menu, plugin
    # widgets submenu) are NOT registered here -- see
    # _register_qt_plugin_actions, called separately by _QtMainWindow so it
    # can run on every Window construction, independently of this function's
    # one-shot cache.

    # register menubar actions
    app.register_actions(
        chain(
            Q_DEBUG_ACTIONS,
            Q_FILE_ACTIONS,
            Q_HELP_ACTIONS,
            Q_PLUGINS_ACTIONS,
            Q_VIEW_ACTIONS,
            LAYERS_ACTIONS,
            Q_LAYERLIST_CONTEXT_ACTIONS,
            Q_WINDOW_ACTIONS,
        )
    )

    # register menubar submenus
    app.menus.append_menu_items(chain(DEBUG_SUBMENUS, LAYERS_SUBMENUS))


def add_dummy_actions(context: Context) -> None:
    """Register dummy 'Empty' actions for all contributable menus.

    Each action is registered with its own `when` condition, that
    ensures the action is not visible once the menu is populated.
    The context key used in the `when` condition is also added to
    the given `context` and assigned to a partial function that
    returns True if the menu is empty, and otherwise False.


    Parameters
    ----------
    context : Context
        context to store functional keys used in `when` conditions
    """
    from napari._app_model import get_app_model
    from napari._app_model.constants._menus import MenuId
    from napari._app_model.utils import get_dummy_action, is_empty_menu

    app = get_app_model()

    actions = []
    for menu_id in MenuId.contributables():
        dummmy_action, context_key = get_dummy_action(menu_id)
        if dummmy_action.id not in app.commands:
            actions.append(dummmy_action)
        # NOTE: even if action is already registered, the `context` instance
        # may be new e.g. when closing and relaunching a viewer
        # in a notebook. Context key should be assigned regardless
        context[context_key] = partial(is_empty_menu, menu_id)
    app.register_actions(actions)
