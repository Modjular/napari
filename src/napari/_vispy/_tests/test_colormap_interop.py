"""Tests for napari <-> vispy colormap interoperability.

These live under ``_vispy`` rather than beside the other colormap tests in
``napari/utils/colormaps/_tests`` because they need vispy installed. The core
colormap machinery must be testable without it.
"""

import numpy as np
import pytest
from vispy.color import Colormap as VispyColormap

from napari._vispy.utils.colormap import _napari_cmap_to_vispy
from napari.utils.colormaps import Colormap
from napari.utils.colormaps.colormap_utils import (
    AVAILABLE_COLORMAPS,
    ensure_colormap,
)


@pytest.mark.parametrize('name', list(AVAILABLE_COLORMAPS.keys()))
def test_napari_colormap_matches_vispy_equivalent(name):
    """Every napari colormap must map identically to its vispy conversion."""
    if name in {'label_colormap', 'custom'}:
        pytest.skip(
            'label_colormap and custom are inadvertantly added to AVAILABLE_COLORMAPS but are not normal colormaps'
        )

    np.random.seed(0)
    cmap = AVAILABLE_COLORMAPS[name]
    values = np.random.rand(50)

    colors = cmap.map(values)
    vispy_colors = _napari_cmap_to_vispy(cmap).map(values)
    np.testing.assert_almost_equal(colors, vispy_colors, decimal=6)


def test_can_accept_vispy_colormaps():
    """Test that we can accept vispy colormaps."""
    colors = np.array([[0, 0, 0, 1], [0, 1, 0, 1], [0, 0, 1, 1]])
    vispy_cmap = VispyColormap(colors)
    cmap = ensure_colormap(vispy_cmap)
    assert isinstance(cmap, Colormap)
    np.testing.assert_almost_equal(cmap.colors, colors)


def test_can_accept_vispy_colormap_name_tuple():
    """Test that we can accept vispy colormap named type."""
    colors = np.array([[0, 0, 0, 1], [0, 1, 0, 1], [0, 0, 1, 1]])
    vispy_cmap = VispyColormap(colors)
    cmap = ensure_colormap(('special_name', vispy_cmap))
    assert isinstance(cmap, Colormap)
    np.testing.assert_almost_equal(cmap.colors, colors)
    assert cmap.name == 'special_name'


def test_can_accept_vispy_colormaps_in_dict():
    """Test that we can accept vispy colormaps in a dictionary."""
    colors_a = np.array([[0, 0, 0, 1], [0, 1, 0, 1], [0, 0, 1, 1]])
    colors_b = np.array([[0, 0, 0, 1], [1, 0, 0, 1], [0, 0, 1, 1]])
    vispy_cmap_a = VispyColormap(colors_a)
    vispy_cmap_b = VispyColormap(colors_b)
    with pytest.warns(UserWarning, match='Only the first item in a colormap'):
        cmap = ensure_colormap({'a': vispy_cmap_a, 'b': vispy_cmap_b})
    assert isinstance(cmap, Colormap)
    np.testing.assert_almost_equal(cmap.colors, colors_a)
    assert cmap.name == 'a'


def test_vendored_vispy_colormaps_match_vispy():
    """The vendored colormap data must reproduce vispy's originals exactly.

    Guards the generated `napari.utils.colormaps.vendored.vispy_colormaps`,
    which is excluded from lint and type-checking and so has no other net.
    """
    from vispy.color import get_colormaps

    from napari.utils.colormaps.vendored.vispy_colormaps import (
        VISPY_COLORMAPS,
    )

    upstream = {
        k: v
        for k, v in get_colormaps().items()
        if isinstance(v, VispyColormap)
    }

    # Order matters: it sets name-resolution precedence in
    # colormap_utils.vispy_or_mpl_colormap.
    assert list(upstream) == list(VISPY_COLORMAPS)

    values = np.linspace(0, 1, 512)
    for name, original in upstream.items():
        data = VISPY_COLORMAPS[name]
        np.testing.assert_array_equal(original.colors.rgba, data['colors'])
        np.testing.assert_array_equal(original._controls, data['controls'])
        rebuilt = VispyColormap(
            colors=np.array(data['colors']),
            controls=np.array(data['controls']),
        )
        np.testing.assert_array_equal(
            rebuilt.map(values), original.map(values)
        )
