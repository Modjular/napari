"""Renderer-agnostic constraints on what dtype a GPU texture can hold.

Every GPU-backed renderer needs to coerce array data into a small set of
texture-friendly dtypes before uploading it -- this isn't a vispy-specific
concern, just phrased in vispy's terms historically because vispy was the
only renderer that existed. No GL/vispy calls happen here; the actual GL
querying (`get_gl_extensions`, `get_max_texture_sizes`) stays in
`napari._vispy.utils.gl`, since building a GL context to query it *is*
genuinely renderer-specific.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

import numpy as np

if TYPE_CHECKING:
    import numpy.typing as npt

__all__ = ['fix_data_dtype', 'texture_dtypes']

texture_dtypes = [
    np.dtype(np.uint8),
    np.dtype(np.uint16),
    np.dtype(np.float32),
]


def fix_data_dtype(data: npt.NDArray) -> npt.NDArray:
    """Makes sure the dtype of the data is acceptable for a GPU texture.

    Acceptable types are uint8, uint16, float32.

    Parameters
    ----------
    data : np.ndarray
        Data that will need to be of right type.

    Returns
    -------
    np.ndarray
        Data that is of right type and will be passed to the renderer.
    """

    dtype = np.dtype(data.dtype)
    if dtype in texture_dtypes:
        return data

    try:
        dtype_ = cast(
            'type[np.unsignedinteger[Any] | np.floating[Any]]',
            {
                'i': np.float32,
                'f': np.float32,
                'u': np.uint16,
                'b': np.uint8,
            }[dtype.kind],
        )
        if dtype_ == np.uint16 and dtype.itemsize > 2:
            dtype_ = np.float32
    except KeyError as e:  # not an int or float
        raise TypeError(
            f'type {dtype} not allowed for texture; must be one of {set(texture_dtypes)}'
        ) from e
    return data.astype(dtype_)
