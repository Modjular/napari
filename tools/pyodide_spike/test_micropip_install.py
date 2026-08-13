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

Three stages, recorded in full in README.md:

* **Stage A** -- plain `micropip.install("napari")` against real PyPI.
  Expected and confirmed to fail: napari's PyPI release still depends on
  `vispy`, which has no Emscripten/Pyodide wheel.
* **Stage B** -- a wheel built from *this branch* (core already vispy-free)
  installed with `deps=False`, plus a curated set of dependencies that do
  have Pyodide wheels, skipping `vispy` and `napari-console`. This is where
  the spike earns its keep: it surfaces a blocker invisible to static
  analysis -- `psutil` (imported unconditionally by
  `napari/settings/_application.py`) has no Pyodide wheel either, and the
  fix for that (`54db16d0e` "Make psutil optional behind
  total_memory_bytes()") lives on the *sibling* `decouple-core-from-qt`
  branch, not this one.
* **Stage C** (not automated here -- see README) -- manually verified by
  cherry-picking `54db16d0e` onto a scratch worktree: with both fixes
  combined, `ViewerModel()`, `add_image()`, and `add_shapes()` all succeed
  inside real Pyodide with `vispy` import actively blocked.
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


def test_stage_b_local_wheel_still_blocked_by_psutil(selenium, napari_wheel):
    """This branch's core is vispy-free, but napari/settings/_application.py
    still does an unconditional `from psutil import virtual_memory`, and
    psutil has no Pyodide wheel (confirmed absent from pyodide-lock.json's
    354-package index). This is expected to fail on THIS branch as checked
    out -- see README.md Stage C for confirmation that cherry-picking
    `54db16d0e` from `decouple-core-from-qt` resolves it.
    """
    code = f"""
import micropip

log = []
await micropip.install("{selenium.base_url}/{napari_wheel}", deps=False)
log.append("local napari wheel (deps=False): OK")

for dep in {STAGE_B_DEPS!r}:
    await micropip.install(dep)
log.append("core deps installed (vispy, napari-console, psutil skipped)")

try:
    from napari.components import ViewerModel
    log.append("UNEXPECTED SUCCESS: ViewerModel import worked without psutil")
except ModuleNotFoundError as e:
    log.append(f"EXPECTED FAILURE: {{type(e).__name__}}: {{e}}")

"\\n".join(log)
"""
    result = selenium.run_async(code)
    print(f'\n=== STAGE B RESULT ===\n{result}\n=== END ===')
    assert 'core deps installed' in result
    assert (
        "EXPECTED FAILURE: ModuleNotFoundError: No module named 'psutil'"
        in result
    )
