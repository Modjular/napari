"""Conversion from napari colormaps to vispy colormaps.

This lives in the vispy backend rather than in ``napari.utils.colormaps``
because vispy colormaps are a rendering concern: every caller is a vispy
visual, and the model layer must stay importable without vispy.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from vispy.color import Colormap as VispyColormap

if TYPE_CHECKING:
    from napari.utils.colormaps import Colormap


def _napari_cmap_to_vispy(colormap: Colormap) -> VispyColormap:
    """Convert a napari colormap to its equivalent vispy colormap."""
    cmap_args = colormap.model_dump()
    cmap_args.pop('name')
    cmap_args['bad_color'] = cmap_args.pop('nan_color')
    return VispyColormap(**cmap_args)
