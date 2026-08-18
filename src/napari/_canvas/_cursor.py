"""Pure decision logic for what cursor a canvas should display.

Extracted from `napari._vispy.canvas.VispyCanvas._on_cursor`: which "kind"
of cursor applies (and at what pixel size) depends only on the napari
cursor/camera/canvas-size model state, not on how any particular backend
renders that kind. Mapping a `CursorSpec` to an actual cursor value (a Qt
`QCursor`/`QPixmap` today; a CSS cursor string for a hypothetical web
backend) stays backend-specific, so `CanvasProtocol.cursor` is left loosely
typed rather than sharing a cursor *value* type across backends.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

__all__ = ['CursorSpec', 'compute_cursor_spec']

CursorKind = Literal[
    'cross', 'circle', 'circle_frozen', 'square', 'crosshair', 'named'
]


@dataclass(frozen=True)
class CursorSpec:
    """Which cursor kind a backend should display, and at what size.

    `name` is only meaningful when `kind == 'named'`: it carries through
    the raw napari cursor style string (e.g. a plugin-defined style) for a
    backend to look up in its own name-to-cursor mapping.
    """

    kind: CursorKind
    size: int = 0
    name: str = ''


def compute_cursor_spec(
    cursor_style: str,
    cursor_size: float,
    scaled: bool,
    zoom: float,
    canvas_size: tuple[int, int],
) -> CursorSpec:
    """Decide which cursor kind/size applies for the current napari state.

    Parameters
    ----------
    cursor_style : str
        `viewer.cursor.style`.
    cursor_size : float
        `viewer.cursor.size`, in canvas pixels before any zoom scaling.
    scaled : bool
        `viewer.cursor.scaled` -- whether size should scale with zoom.
    zoom : float
        `viewer.scene.camera.zoom`.
    canvas_size : tuple[int, int]
        The canvas's current size, used to reject a brush cursor too big
        or too small to render sensibly.
    """
    if cursor_style in {'square', 'circle', 'circle_frozen'}:
        size = cursor_size
        if scaled:
            size *= zoom
        size = int(size)

        # make sure the square/circle fits within the current canvas
        if (
            size < 8 or size > (min(canvas_size) - 4)
        ) and cursor_style != 'circle_frozen':
            return CursorSpec(kind='cross')
        if cursor_style.startswith('circle'):
            if cursor_style == 'circle_frozen':
                return CursorSpec(kind='circle_frozen', size=size)
            return CursorSpec(kind='circle', size=size)
        return CursorSpec(kind='square', size=size)
    if cursor_style == 'crosshair':
        return CursorSpec(kind='crosshair')
    return CursorSpec(kind='named', name=cursor_style)
