from napari._canvas._cursor import compute_cursor_spec


def test_named_style_passthrough():
    spec = compute_cursor_spec(
        cursor_style='pointing',
        cursor_size=1,
        scaled=False,
        zoom=1,
        canvas_size=(800, 600),
    )
    assert spec.kind == 'named'
    assert spec.name == 'pointing'


def test_crosshair():
    spec = compute_cursor_spec(
        cursor_style='crosshair',
        cursor_size=1,
        scaled=False,
        zoom=1,
        canvas_size=(800, 600),
    )
    assert spec.kind == 'crosshair'


def test_square_within_bounds():
    spec = compute_cursor_spec(
        cursor_style='square',
        cursor_size=20,
        scaled=False,
        zoom=1,
        canvas_size=(800, 600),
    )
    assert spec.kind == 'square'
    assert spec.size == 20


def test_circle_within_bounds():
    spec = compute_cursor_spec(
        cursor_style='circle',
        cursor_size=20,
        scaled=False,
        zoom=1,
        canvas_size=(800, 600),
    )
    assert spec.kind == 'circle'
    assert spec.size == 20


def test_circle_frozen_ignores_size_rejection():
    """circle_frozen is exempt from the too-small/too-large rejection."""
    spec = compute_cursor_spec(
        cursor_style='circle_frozen',
        cursor_size=1,  # would be rejected for plain 'circle'
        scaled=False,
        zoom=1,
        canvas_size=(800, 600),
    )
    assert spec.kind == 'circle_frozen'
    assert spec.size == 1


def test_size_scaled_by_zoom():
    spec = compute_cursor_spec(
        cursor_style='square',
        cursor_size=10,
        scaled=True,
        zoom=2.0,
        canvas_size=(800, 600),
    )
    assert spec.size == 20


def test_too_small_rejects_to_cross():
    spec = compute_cursor_spec(
        cursor_style='circle',
        cursor_size=1,
        scaled=False,
        zoom=1,
        canvas_size=(800, 600),
    )
    assert spec.kind == 'cross'


def test_too_large_for_canvas_rejects_to_cross():
    spec = compute_cursor_spec(
        cursor_style='square',
        cursor_size=100,
        scaled=False,
        zoom=1,
        canvas_size=(50, 600),
    )
    assert spec.kind == 'cross'
