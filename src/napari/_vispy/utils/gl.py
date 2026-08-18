"""OpenGL Utilities."""

from __future__ import annotations

from contextlib import contextmanager
from functools import lru_cache
from typing import TYPE_CHECKING

from vispy.app import Canvas
from vispy.gloo import gl
from vispy.gloo.context import get_current_canvas

from napari._canvas._texture import fix_data_dtype, texture_dtypes

if TYPE_CHECKING:
    from collections.abc import Generator

__all__ = [
    'fix_data_dtype',
    'get_gl_extensions',
    'get_max_texture_sizes',
    'texture_dtypes',
]


@contextmanager
def _opengl_context() -> Generator[None, None, None]:
    """Assure we are running with a valid OpenGL context.

    Only create a Canvas is one doesn't exist. Creating and closing a
    Canvas causes vispy to process Qt events which can cause problems.
    Ideally call opengl_context() on start after creating your first
    Canvas. However it will work either way.
    """
    canvas = Canvas(show=False) if get_current_canvas() is None else None
    try:
        yield
    finally:
        if canvas is not None:
            canvas.close()


@lru_cache(maxsize=1)
def get_gl_extensions() -> str:
    """Get basic info about the Gl capabilities of this machine"""
    with _opengl_context():
        return gl.glGetParameter(gl.GL_EXTENSIONS)


@lru_cache
def get_max_texture_sizes() -> tuple[int, int]:
    """Return the maximum texture sizes for 2D and 3D rendering.

    If this function is called without an OpenGL context it will create a
    temporary non-visible Canvas. Either way the lru_cache means subsequent
    calls to thing function will return the original values without
    actually running again.

    Returns
    -------
    Tuple[int, int]
        The max textures sizes for (2d, 3d) rendering.
    """
    with _opengl_context():
        max_size_2d = gl.glGetParameter(gl.GL_MAX_TEXTURE_SIZE)

    if not max_size_2d:
        max_size_2d = None

    # vispy/gloo doesn't provide the GL_MAX_3D_TEXTURE_SIZE location,
    # but it can be found in this list of constants
    # http://pyopengl.sourceforge.net/documentation/pydoc/OpenGL.GL.html
    with _opengl_context():
        GL_MAX_3D_TEXTURE_SIZE = 32883
        max_size_3d = gl.glGetParameter(GL_MAX_3D_TEXTURE_SIZE)

    if not max_size_3d:
        max_size_3d = None

    return max_size_2d, max_size_3d


# blend_func parameters are multiplying:
# - source color
# - destination color
# - source alpha
# - destination alpha
# they do not apply to min/max blending equation

BLENDING_MODES = {
    'opaque': {
        'depth_test': True,
        'cull_face': False,
        'blend': False,
    },
    'translucent': {
        'depth_test': True,
        'cull_face': False,
        'blend': True,
        'blend_func': ('src_alpha', 'one_minus_src_alpha', 'one', 'one'),
        'blend_equation': 'func_add',
    },
    'translucent_no_depth': {
        'depth_test': False,
        'cull_face': False,
        'blend': True,
        'blend_func': ('src_alpha', 'one_minus_src_alpha', 'one', 'one'),
        'blend_equation': 'func_add',  # see vispy/vispy#2324
    },
    'additive': {
        'depth_test': False,
        'cull_face': False,
        'blend': True,
        'blend_func': ('src_alpha', 'dst_alpha', 'one', 'one'),
        'blend_equation': 'func_add',
    },
    'minimum': {
        'depth_test': False,
        'cull_face': False,
        'blend': True,
        'blend_equation': 'min',
    },
    'multiplicative': {
        'depth_test': False,
        'cull_face': False,
        'blend': True,
        'blend_func': ('dst_color', 'zero', 'one', 'one'),
        'blend_equation': 'func_add',
    },
}
