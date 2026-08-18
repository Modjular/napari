"""Pyodide install spike for the napari-in-the-browser roadmap (Phase 0).

Nothing about running napari under Pyodide had ever been executed before this
spike -- every claim in `napari_browser_handoff.md` about what would/wouldn't
install was inferred from wheel metadata. This module runs the real thing,
inside an actual Pyodide runtime driven by Node.js via `pytest-pyodide`.

Setup
-----
    cd tools/pyodide_spike
    npm install                          # fetches a local Pyodide distribution
                                          # into node_modules/pyodide (pinned in
                                          # package.json/package-lock.json)
    pip install -r requirements-spike.txt

Run (from the repo root, with napari's own dev venv active)::

    python -m pytest tools/pyodide_spike/test_micropip_install.py \\
        --dist-dir=tools/pyodide_spike/node_modules/pyodide --rt=node -v -s

Two stages, recorded in full in README.md:

* **Stage A** -- plain `micropip.install("napari")` against real PyPI.
  Expected and confirmed to fail: napari's PyPI release still depends on
  `vispy`, which has no Emscripten/Pyodide wheel.
* **Stage B** -- a wheel built from *this branch* (core vispy-free, and now
  psutil-free too -- see below) installed with `deps=False`, plus a curated
  set of dependencies that do have Pyodide wheels, skipping `vispy` and
  `napari-console`. Constructs a real `ViewerModel`, adds an image and a
  concave-polygon shape, with `vispy` import actively blocked via a
  `builtins.__import__` guard the whole time.

  This originally stopped short of a working `ViewerModel`: `psutil` has no
  Pyodide wheel either, and `napari/settings/_application.py` did an
  unconditional `from psutil import virtual_memory`. That's what commit
  `54db16d0e` ("Make psutil optional behind total_memory_bytes()", cherry-picked
  here from the sibling `decouple-core-from-qt` branch) fixes -- confirmed by
  manually cherry-picking it onto a scratch worktree before it was merged onto
  this branch for real; see README.md for that verification note.
"""

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

# Vetted against real PyPI/Pyodide package availability during this spike
# (see README.md "Stage B dependency table"). Deliberately excludes `vispy`
# and `napari-console` (no Pyodide wheels) and `qtpy`/`superqt`/`PyOpenGL`
# (install fine as inert pure-Python wheels but aren't needed for a headless
# ViewerModel and raise QtBindingsNotFoundError if actually imported).
STAGE_B_DEPS = [
    'numpy',
    'scipy',
    'pandas',
    'Pillow',
    'scikit-image',
    'PyYAML',
    'pydantic',
    'pydantic-extra-types',
    'pydantic-settings',
    'jsonschema',
    'lazy_loader',
    'platformdirs',
    'Pygments',
    'toolz',
    'tqdm',
    'wrapt',
    'imageio',
    'app-model',
    'cachey',
    'dask',
    'npe2',
    'pint',
    'tifffile',
    'napari-plugin-engine',
    'psygnal',
    'typing_extensions',
    'certifi',
    'magicgui',
]


@pytest.fixture(scope='session')
def napari_wheel(request, tmp_path_factory):
    """Build a wheel from this checked-out branch and serve it alongside
    the Pyodide distribution, so micropip can fetch it by URL from inside
    the sandbox (micropip has no notion of a local editable install).
    """
    dist_dir = request.config.getoption('--dist-dir')
    if not dist_dir:
        pytest.skip(
            'pass --dist-dir=tools/pyodide_spike/node_modules/pyodide '
            '(after `npm install` in tools/pyodide_spike/)'
        )
    dist_dir = Path(dist_dir)

    build_dir = tmp_path_factory.mktemp('napari_wheel_build')
    subprocess.run(
        [sys.executable, '-m', 'build', '--wheel', '--outdir', str(build_dir)],
        cwd=REPO_ROOT,
        check=True,
    )
    wheel = next(build_dir.glob('napari-*.whl'))
    dest = dist_dir / wheel.name
    dest.write_bytes(wheel.read_bytes())
    try:
        yield wheel.name
    finally:
        dest.unlink(missing_ok=True)


def test_stage_a_pypi_napari_fails_on_vispy(selenium):
    """Real PyPI napari still requires vispy, which has no Pyodide wheel."""
    code = """
import micropip
try:
    await micropip.install("napari", keep_going=True)
    result = "UNEXPECTED SUCCESS"
except Exception as e:
    result = f"{type(e).__name__}: {e}"
result
"""
    result = selenium.run_async(code)
    print(f'\n=== STAGE A RESULT ===\n{result}\n=== END ===')
    assert "Can't find a pure Python 3 wheel" in result
    assert 'vispy' in result


def test_stage_b_local_wheel_viewer_model_works(selenium, napari_wheel):
    """A wheel built from this branch, with vispy blocked at import time,
    actually constructs a ViewerModel and adds layers inside real Pyodide.

    Exercises the vendored `viridis` colormap (`add_image`) and the vendored
    concave-polygon `Triangulation` (`add_shapes`) -- the same two vispy-free
    code paths the `decouple-core-from-vispy` branch's own acceptance test
    checks, just run for real instead of with a mocked import guard on CPython.
    """
    code = f"""
import micropip

log = []
await micropip.install("{selenium.base_url}/{napari_wheel}", deps=False)
log.append("local napari wheel (deps=False): OK")

for dep in {STAGE_B_DEPS!r}:
    await micropip.install(dep)
log.append("core deps installed (vispy, napari-console, psutil skipped)")

import sys, builtins
real_import = builtins.__import__
def guard(name, *a, **k):
    if name == "vispy" or name.startswith("vispy."):
        raise ModuleNotFoundError(f"No module named '{{name}}' (blocked by spike)")
    return real_import(name, *a, **k)
builtins.__import__ = guard

import napari
log.append("import napari (vispy BLOCKED): OK")

import numpy as np
from napari.components import ViewerModel
v = ViewerModel()
log.append("ViewerModel(): OK")
v.add_image(np.random.rand(4, 16, 16), colormap='viridis')
log.append("add_image(colormap=viridis): OK")
v.add_shapes(
    [np.array([[0., 0.], [0., 9.], [9., 9.], [3., 4.], [9., 0.]])],
    shape_type='polygon',
)
log.append("add_shapes(polygon): OK")
log.append(f"vispy in sys.modules: {{'vispy' in sys.modules}}")

"\\n".join(log)
"""
    result = selenium.run_async(code)
    print(f'\n=== STAGE B RESULT ===\n{result}\n=== END ===')
    assert 'add_shapes(polygon): OK' in result
    assert 'vispy in sys.modules: False' in result
