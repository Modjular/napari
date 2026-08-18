"""Pure-numpy transform math extracted from the vispy layer-visual backend.

`compute_layer_transforms` is a byte-for-byte port of the pure-numpy span of
`napari._vispy.layers.base.VispyBaseLayer._on_matrix_change` -- ZYX-to-XYZ
axis reversal, pint unit scaling, half-pixel centering for array-like 2D
layers, 3D multiscale downsample offsets, and a compensating inverse offset
so overlays don't inherit the texture offset. It touches nothing vispy- or
Qt-specific: every input is either a plain value or a napari `Layer` model
attribute, and the two outputs are plain 4x4 numpy arrays for the caller to
apply to whatever transform object its renderer uses.

This is the single highest-risk extraction in the whole browser roadmap:
get the axis convention or the pixel-centering offset wrong and images sit
half a pixel off their overlays -- silently. `_canvas/_tests/test_transforms.py`
checks each branch (identity, pure scale/translate/rotate, multiscale in
both 2D and 3D) against independently-computed expected values, not by
re-invoking this function. Not called from anywhere yet.

Deliberately excludes the "is the cached world_to_layer_units_scale stale"
reset check that used to precede this logic in `_on_matrix_change`
(`base.py:209-211`): that's a stateful cache-invalidation concern that
belongs to the `VispyBaseLayer` instance holding the cache, not to a pure
transform-computation function. Callers must pass an already-current
`world_to_layer_units_scale`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from collections.abc import Sequence

    import numpy.typing as npt

    from napari.layers import Layer

__all__ = ['compute_layer_transforms']


def compute_layer_transforms(
    layer: Layer,
    world_to_layer_units_scale: Sequence[float],
    array_like: bool,
) -> tuple[npt.NDArray, npt.NDArray]:
    """Compute a layer visual's affine and child transform matrices.

    Parameters
    ----------
    layer : napari.layers.Layer
        The layer model to compute transforms for.
    world_to_layer_units_scale : Sequence[float]
        Per-(layer)-dimension scale factor between the layer's own units and
        the viewer's shared world units, already refreshed to match
        `layer.ndim` (see the module docstring for why this isn't done here).
    array_like : bool
        Whether the visual being positioned represents array-like (e.g.
        image/labels texture) data -- only these get the half-pixel
        centering and multiscale offset treatment.

    Returns
    -------
    affine_matrix : np.ndarray
        A 4x4 matrix positioning the layer's own visual node.
    child_matrix : np.ndarray
        A 4x4 matrix to apply to the visual node's children (e.g. overlays)
        so they don't inherit texture-only offsets.
    """
    dims_displayed = layer._slice_input.displayed

    # mypy: layer._transforms.simplified cannot be None
    transform = layer._transforms.simplified.set_slice(dims_displayed)
    # convert NumPy axis ordering to VisPy axis ordering
    # by reversing the axes order and flipping the linear
    # matrix
    units_scale = [world_to_layer_units_scale[x] for x in dims_displayed][::-1]
    translate = transform.translate[::-1] * units_scale
    matrix = transform.linear_matrix[::-1, ::-1].T * units_scale

    # The following accounts for the offset between samples at different
    # resolutions of 3D multi-scale array-like layers (e.g. images).
    # The 2D case is handled differently because that has more complex support
    # (multiple levels, partial field-of-view) that also currently interacts
    # with how pixels are centered (see further below).
    if (
        array_like
        and layer._slice_input.ndisplay == 3
        and layer.multiscale
        and hasattr(layer, 'downsample_factors')
    ):
        # Use the rendered level's downsample factor: 3D shows the
        # lowest level by default, but locked_data_level (and 3D
        # sub-volume tiles) can select any level. The data-space
        # offset is mapped to world units with the layer scale.
        layer_scale = np.asarray(layer.scale)[dims_displayed][::-1]
        data_level: int = getattr(layer, 'data_level', 0)
        # grab the downscale factors for this level
        level_factors = layer.downsample_factors[data_level]
        # keep only the displayed factors, then invert to match VisPy
        # axis ordering
        displayed_downsample = level_factors[dims_displayed][::-1]
        # finally, adjust translate by half a pixel per downscale level
        translate += (displayed_downsample - 1) / 2 * layer_scale

    # Embed in the top left corner of a 4x4 affine matrix
    affine_matrix = np.eye(4)
    affine_matrix[: matrix.shape[0], : matrix.shape[1]] = matrix
    affine_matrix[-1, : len(translate)] = translate

    child_offset = np.zeros(len(dims_displayed))

    if array_like and layer._slice_input.ndisplay == 3 and layer.multiscale:
        # In 3D, sub-volume tiles have nonzero corner_pixels[0].
        # The volume node transform positions the tile correctly,
        # but child nodes (bounding box overlay) should not inherit
        # this offset — undo it so overlays stay at the full data
        # extent.
        cp0 = layer.corner_pixels[0][dims_displayed][::-1]
        if np.any(cp0 != 0):
            child_offset = -cp0.astype(float)

    if array_like and layer._slice_input.ndisplay == 2:
        # Perform pixel offset to shift origin from top left corner
        # of pixel to center of pixel.
        # Note this offset is only required for array like data in
        # 2D.
        offset_matrix = layer._data_to_world.set_slice(
            dims_displayed
        ).linear_matrix
        offset = -offset_matrix @ np.ones(offset_matrix.shape[1]) / 2
        # Convert NumPy axis ordering to VisPy axis ordering
        # and embed in full affine matrix
        affine_offset = np.eye(4)
        affine_offset[-1, : len(offset)] = offset[::-1] * units_scale
        affine_matrix = affine_matrix @ affine_offset
        if layer.multiscale:
            # For performance reasons, when displaying multiscale images,
            # only the part of the data that is visible on the canvas is
            # sent as a texture to the GPU. This means that the texture
            # gets an additional transform, to position the texture
            # correctly offset from the origin of the full data. However,
            # child nodes, which include overlays such as bounding boxes,
            # should *not* receive this offset, so we undo it here:
            child_offset = (
                np.ones(offset_matrix.shape[1]) / 2
                - layer.corner_pixels[0][dims_displayed][::-1]
            )
        else:
            child_offset = np.full(offset_matrix.shape[1], 1 / 2)

    child_matrix = np.eye(4)
    child_matrix[-1, : len(child_offset)] = child_offset

    return affine_matrix, child_matrix
