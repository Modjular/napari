"""Registration/lookup semantics only -- deliberately does not use real
napari Layer/Overlay model classes, to prove VisualRegistry has no
dependency on them (or on napari._vispy) at all: any model/visual class
pairing works."""

import pytest

from napari._canvas import VisualRegistry


class _FakeModel:
    """Stands in for a second backend's model type (e.g. a napari Layer)."""


class _FakeModelSubclass(_FakeModel):
    """A subclass with no visual of its own registered."""


class _FakeVisual:
    """Accepts either calling convention: create_layer_visual passes the
    model positionally, create_overlay_visual passes it as `overlay=`."""

    def __init__(self, *args, **kwargs):
        if args:
            self.model, *rest = args
            self.args = tuple(rest)
        else:
            self.model = kwargs.pop('overlay')
            self.args = ()
        self.kwargs = kwargs


def test_third_party_layer_and_overlay_registration():
    """A second backend can populate its own registry with no _vispy involved."""
    registry = VisualRegistry()
    registry.register_layer_visual(_FakeModel, _FakeVisual)
    registry.register_overlay_visual(_FakeModel, _FakeVisual)

    fake_layer = _FakeModel()
    visual = registry.create_layer_visual(fake_layer, 'extra_arg', kw=1)
    assert isinstance(visual, _FakeVisual)
    assert visual.model is fake_layer
    assert visual.args == ('extra_arg',)
    assert visual.kwargs == {'kw': 1}

    fake_overlay = _FakeModel()
    overlay_visual = registry.create_overlay_visual(fake_overlay, kw=2)
    assert isinstance(overlay_visual, _FakeVisual)
    assert overlay_visual.model is fake_overlay
    assert overlay_visual.kwargs == {'kw': 2}


def test_layer_and_overlay_registries_are_independent():
    registry = VisualRegistry()
    registry.register_layer_visual(_FakeModel, _FakeVisual)

    with pytest.raises(TypeError, match='No visual registered'):
        registry.create_overlay_visual(_FakeModel())


def test_mro_walk_finds_closest_registered_parent():
    registry = VisualRegistry()
    registry.register_layer_visual(_FakeModel, _FakeVisual)

    # _FakeModelSubclass has no visual of its own registered: the registry
    # should fall back to the closest registered parent class.
    subclass_instance = _FakeModelSubclass()
    visual = registry.create_layer_visual(subclass_instance)
    assert isinstance(visual, _FakeVisual)
    assert visual.model is subclass_instance


def test_create_layer_visual_raises_for_unregistered_type():
    registry = VisualRegistry()
    with pytest.raises(TypeError, match='No visual registered'):
        registry.create_layer_visual(_FakeModel())


def test_create_overlay_visual_raises_for_unregistered_type():
    registry = VisualRegistry()
    with pytest.raises(TypeError, match='No visual registered'):
        registry.create_overlay_visual(_FakeModel())
