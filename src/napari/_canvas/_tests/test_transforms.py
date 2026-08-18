"""Tests for compute_layer_transforms -- see _canvas/_transforms.py's module
docstring for why this is the highest-risk extraction in the roadmap.

No vispy or Qt import anywhere in this file: layers are built through
napari.components.ViewerModel (pure core model) purely to get a real,
correctly-populated `layer._slice_input`/`corner_pixels`/`downsample_factors`
without reaching into private slicing internals. Expected values are computed
independently in each test, not by re-invoking compute_layer_transforms.
"""

import numpy as np

from napari._canvas._transforms import compute_layer_transforms
from napari.components import ViewerModel


def _add_2d_image(ndisplay=2, **kwargs):
    viewer = ViewerModel()
    layer = viewer.add_image(np.zeros((10, 10)), **kwargs)
    viewer.dims.ndisplay = ndisplay
    return layer


def _add_multiscale_image(shapes, ndisplay):
    viewer = ViewerModel()
    data = [np.zeros(s) for s in shapes]
    layer = viewer.add_image(data, multiscale=True)
    viewer.dims.ndisplay = ndisplay
    return layer


def _expected_affine_no_array_like(layer, dims_displayed, units_scale):
    """Independent re-derivation of the linear-transform-only embedding,
    written separately from compute_layer_transforms's implementation."""
    transform = layer._transforms.simplified.set_slice(dims_displayed)
    translate = transform.translate[::-1] * units_scale
    matrix = transform.linear_matrix[::-1, ::-1].T * units_scale
    affine = np.eye(4)
    affine[: matrix.shape[0], : matrix.shape[1]] = matrix
    affine[-1, : len(translate)] = translate
    return affine


def test_identity_2d_array_like():
    """A fresh Image layer's array_like 2D path applies exactly the
    half-pixel centering offset, hand-derived here from first principles."""
    layer = _add_2d_image()

    affine, child = compute_layer_transforms(layer, (1, 1), array_like=True)

    expected_affine = np.eye(4)
    expected_affine[-1, :2] = [-0.5, -0.5]
    expected_child = np.eye(4)
    expected_child[-1, :2] = [0.5, 0.5]

    np.testing.assert_allclose(affine, expected_affine)
    np.testing.assert_allclose(child, expected_child)


def test_pure_scale_not_array_like():
    layer = _add_2d_image()
    layer.scale = (2.0, 3.0)
    dims_displayed = layer._slice_input.displayed

    affine, child = compute_layer_transforms(layer, (1, 1), array_like=False)

    expected = _expected_affine_no_array_like(layer, dims_displayed, (1, 1))
    np.testing.assert_allclose(affine, expected)
    # array_like=False never touches child_offset
    np.testing.assert_allclose(child, np.eye(4))


def test_pure_translate_not_array_like():
    layer = _add_2d_image()
    layer.translate = (5.0, -2.0)
    dims_displayed = layer._slice_input.displayed

    affine, _ = compute_layer_transforms(layer, (1, 1), array_like=False)

    expected = _expected_affine_no_array_like(layer, dims_displayed, (1, 1))
    np.testing.assert_allclose(affine, expected)
    # world convention (y, x) reversed to vispy convention (x, y)
    np.testing.assert_allclose(affine[-1, :2], [-2.0, 5.0])


def test_composed_scale_translate_rotate_not_array_like():
    layer = _add_2d_image()
    layer.scale = (2.0, 3.0)
    layer.translate = (5.0, -2.0)
    layer.rotate = 30
    dims_displayed = layer._slice_input.displayed

    affine, _ = compute_layer_transforms(layer, (1, 1), array_like=False)

    expected = _expected_affine_no_array_like(layer, dims_displayed, (1, 1))
    np.testing.assert_allclose(affine, expected)


def test_non_unit_world_to_layer_units_scale():
    layer = _add_2d_image()
    layer.scale = (2.0, 3.0)
    dims_displayed = layer._slice_input.displayed
    units_scale = (2.0, 0.5)

    affine, _ = compute_layer_transforms(layer, units_scale, array_like=False)

    expected = _expected_affine_no_array_like(
        layer, dims_displayed, [units_scale[x] for x in dims_displayed][::-1]
    )
    np.testing.assert_allclose(affine, expected)
    # sanity: this should differ from the unit-scale case
    unit_affine, _ = compute_layer_transforms(layer, (1, 1), array_like=False)
    assert not np.allclose(affine, unit_affine)


def test_multiscale_3d_translate_offset():
    """3D multiscale rendering offsets translate by half a pixel per
    downscale level (on top of the level's own data-to-world scaling, which
    the model transform -- not this function -- is responsible for), so
    overlays don't sit a level's width off."""
    layer = _add_multiscale_image([(8, 8, 8), (4, 4, 4)], ndisplay=3)
    layer.data_level = 1
    dims_displayed = layer._slice_input.displayed

    affine, _ = compute_layer_transforms(layer, (1, 1, 1), array_like=True)

    # the base linear transform + translate, exactly as in the non-array-like
    # case -- the model's own per-level data-to-world scaling lives here,
    # not in compute_layer_transforms's own downsample-offset addition
    base = _expected_affine_no_array_like(layer, dims_displayed, (1, 1, 1))

    layer_scale = np.asarray(layer.scale)[dims_displayed][::-1]
    level_factors = layer.downsample_factors[layer.data_level]
    displayed_downsample = level_factors[dims_displayed][::-1]
    expected_downsample_offset = (displayed_downsample - 1) / 2 * layer_scale

    np.testing.assert_allclose(affine[:3, :3], base[:3, :3])
    np.testing.assert_allclose(
        affine[-1, :3], base[-1, :3] + expected_downsample_offset
    )


def test_multiscale_3d_child_offset_from_corner_pixels():
    """3D sub-volume tiles have nonzero corner_pixels[0]; child nodes
    (e.g. bounding box overlays) must not inherit that offset."""
    layer = _add_multiscale_image([(8, 8, 8), (4, 4, 4)], ndisplay=3)
    layer.data_level = 0  # isolate from the downsample-offset branch
    layer.corner_pixels = np.array([[1, 2, 3], [7, 8, 9]])
    dims_displayed = layer._slice_input.displayed

    _, child = compute_layer_transforms(layer, (1, 1, 1), array_like=True)

    expected_child_offset = -layer.corner_pixels[0][dims_displayed][
        ::-1
    ].astype(float)
    np.testing.assert_allclose(child[-1, :3], expected_child_offset)


def test_multiscale_2d_child_offset():
    layer = _add_multiscale_image([(8, 8), (4, 4)], ndisplay=2)
    layer.corner_pixels = np.array([[1, 2], [7, 8]])
    dims_displayed = layer._slice_input.displayed

    _, child = compute_layer_transforms(layer, (1, 1), array_like=True)

    offset_matrix = layer._data_to_world.set_slice(
        dims_displayed
    ).linear_matrix
    expected_child_offset = (
        np.ones(offset_matrix.shape[1]) / 2
        - layer.corner_pixels[0][dims_displayed][::-1]
    )
    np.testing.assert_allclose(child[-1, :2], expected_child_offset)


def test_idempotent():
    """Calling twice on unchanged layer state must not mutate anything and
    must yield bit-identical output."""
    layer = _add_2d_image()
    layer.scale = (2.0, 3.0)
    layer.translate = (5.0, -2.0)
    scale_before = tuple(layer.scale)
    translate_before = tuple(layer.translate)

    affine1, child1 = compute_layer_transforms(layer, (1, 1), array_like=True)
    affine2, child2 = compute_layer_transforms(layer, (1, 1), array_like=True)

    assert np.array_equal(affine1, affine2)
    assert np.array_equal(child1, child2)
    assert tuple(layer.scale) == scale_before
    assert tuple(layer.translate) == translate_before
