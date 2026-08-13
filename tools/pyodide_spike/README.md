# Pyodide install spike

**Status: complete.** This is the "Phase 0 remainder" from `napari_browser_handoff.md`
(§8) — the one genuinely untested assumption in the whole napari-in-the-browser
roadmap. Every prior claim about what would/wouldn't install under Pyodide was
inferred from wheel metadata; this spike actually ran it, inside a real Pyodide
runtime driven by Node.js via [`pytest-pyodide`](https://github.com/pyodide/pytest-pyodide).

Not wired into CI or the regular `pytest src/napari/...` regression suite — this
is one-off de-risking, not a permanent regression gate. `tools/` is not excluded
from ruff, so `test_micropip_install.py` is linted/formatted like the rest of the
repo.

## Setup

```bash
cd tools/pyodide_spike
npm install                     # downloads a local Pyodide distribution into
                                 # node_modules/pyodide (pinned in package.json /
                                 # package-lock.json — currently pyodide 314.0.3,
                                 # which requires Node >= 18; tested with v25.9.0)
pip install -r requirements-spike.txt
```

## Run

```bash
# from the repo root, with napari's dev venv active
python -m pytest tools/pyodide_spike/test_micropip_install.py \
    --dist-dir=tools/pyodide_spike/node_modules/pyodide --rt=node -v -s
```

`--rt=node` runs Python inside Pyodide via Node.js (using `pexpect` to drive
`node_test_driver.js`, shipped with `pytest-pyodide`) rather than a real browser
via Selenium/Playwright. This is sufficient for everything this spike asks — pure
Python-level "does it import, does it construct" questions, no DOM/WebGL — and
avoids installing browser drivers entirely.

Both committed tests reflect this branch's **current, real** state (not a
hypothetical future one): they build a wheel from the checked-out source tree on
the fly (`napari_wheel` fixture), so re-running after further commits always
tests what's actually on disk.

## Findings

### Stage A — plain `micropip.install("napari")` against real PyPI

**Confirmed, exactly as the handoff doc inferred:** fails before any napari code
executes, because napari's published dependency `vispy<0.17,>=0.16.2` has no
Emscripten/Pyodide wheel (one Cython extension, `vispy.visuals.text._sdf_cpu`,
with no wasm build). Exact error, `keep_going=True` to enumerate every blocker at
once rather than stopping at the first:

```
ValueError: Can't find a pure Python 3 wheel for: 'vispy<0.17,>=0.16.2',
'psutil>=5.9.4', 'vispy>=0.6.4', 'tornado>=6.2', 'psutil>=5.7',
'tornado>=6.4.1', 'pyzmq>=25', 'tornado>=6.4.1', 'pyzmq>=25.0', 'pyzmq>=25.0'
```

The duplicated/differently-pinned entries come from multiple things in the
dependency tree wanting the same package — e.g. `tornado`/`pyzmq` are pulled in
by `napari-console`'s `qtconsole`/`ipykernel` chain, not by napari itself.

**New finding, not in the handoff doc:** `napari-svg>=0.1.8` — listed in the
handoff's "pure wheels" table — actually declares its own `vispy>=0.6.4`
dependency and fails resolution on that basis too. It was assumed clean because
nobody had tried resolving its *own* metadata, only napari's. (Separately
confirmed: `napari-svg` installs and imports fine with `deps=False`, and
`import napari` succeeds without it at all — it's not a hard import-time
dependency of `napari.__init__`, just unusable for SVG export without a working
vispy-derived color/marker pipeline.)

micropip failure is atomic — no partial environment is left behind on failure.

### Stage B — a wheel built from *this branch*, curated deps, `vispy` blocked

This branch's `decouple-core-from-vispy` lineage already fixed the vispy problem
in Stage A. So Stage B installs a wheel built from the checked-out source
(`micropip.install(url, deps=False)`), then manually installs a curated
dependency set skipping `vispy` and `napari-console` entirely, to isolate what
core actually needs.

**Every dependency in the curated list installs cleanly** — numpy, scipy,
pandas, Pillow, scikit-image, PyYAML, pydantic(+extra-types, +settings),
jsonschema, lazy_loader, platformdirs, Pygments, toolz, tqdm, wrapt, imageio,
app-model, cachey, dask, npe2, pint, tifffile, napari-plugin-engine, psygnal,
typing_extensions, certifi, **and magicgui**.

**New finding: `magicgui` is a hard, unconditional import**, not something
`ViewerModel` can do without. `napari/layers/base/base.py:16` does
`import magicgui as mgui` at module level — not deferred, not optional — so it
must be present just to construct any `Layer` subclass, confirming the handoff's
prediction that a real web frontend needs a magicgui backend, but sharpening it:
this isn't only relevant "for plugin UIs," it's on napari's own core layer
construction path.

**New finding, more precise than the handoff's:** `qtpy` and `superqt` install
fine as pure-Python wheels (as the handoff predicted, "installs but unusable"),
but the failure is *more eager* than "unusable at runtime" — `import qtpy` and
`import superqt` each raise `QtBindingsNotFoundError: No Qt bindings could be
found` **at bare import time**, before any GUI object is touched. `magicgui`
itself, however, imports cleanly standalone (`import magicgui: OK`) even with no
Qt bindings installed at all — it doesn't eagerly import `qtpy`/`superqt` at its
own top level, so a headless `ViewerModel` session can have `magicgui` installed
without tripping this.

**The headline finding — a real blocker invisible to wheel-metadata analysis:**
`napari/settings/_application.py:7` does an unconditional
`from psutil import virtual_memory`. **`psutil` has no Pyodide wheel at all** —
confirmed absent from this Pyodide build's `pyodide-lock.json` package index
(354 built-in packages, `psutil`/`tornado`/`pyzmq` all absent). This blocks
`from napari.components import ViewerModel` outright:

```
ModuleNotFoundError: No module named 'psutil'
```

This is genuinely new information: the handoff doc's §8 says "psutil is already
handled (fallback + `sys_platform != 'emscripten'` marker)" — **but that fix
(`54db16d0e`, "Make psutil optional behind `total_memory_bytes()`") lives on the
sibling `modjular/refactor/decouple-core-from-qt` branch, not on this branch's
`decouple-core-from-vispy` lineage.** `pyproject.toml` on *this* branch still
declares `"psutil>=5.9.4"` with no environment marker. The handoff's own
inference was correct about the *eventual* state, but conflated which branch it
lands on — a real trap for whoever merges these branches later, since Phase 0
success looked, from wheel metadata alone, like it only depended on the vispy
branch.

`test_stage_b_local_wheel_still_blocked_by_psutil` asserts on this exact,
current failure — it is expected to keep failing (in the "this is what's
documented" sense — the test itself passes by asserting the failure text) until
the psutil fix is merged into this branch's lineage too.

### Stage C — with both fixes combined (manually verified, not an automated test)

To confirm the *combination* actually works end-to-end rather than assuming it
from the two findings above, `54db16d0e` was cherry-picked from
`modjular/refactor/decouple-core-from-qt` onto a disposable scratch worktree
(`git worktree add ... --detach`, cherry-pick, build wheel, test, then
`git worktree remove --force` — this branch's own commit history was never
touched). Result, with a `builtins.__import__` guard actively raising
`ModuleNotFoundError` for any `vispy`/`vispy.*` import (mirroring the vispy
branch's own acceptance test in the handoff doc §3):

```
local napari wheel (deps=False): OK
core deps installed
import napari (vispy BLOCKED): OK
ViewerModel(): OK
add_image(colormap=viridis): OK
add_shapes(polygon): OK
vispy in sys.modules: False
```

**This is the spike's success criterion, met:** `ViewerModel`, `add_image`, and
`add_shapes` (exercising the vendored `viridis` colormap and the vendored
concave-polygon `Triangulation`, per the vispy branch's own acceptance test) all
execute correctly inside a real Pyodide/Node sandbox, with `vispy` confirmed
never imported. This is not automated as a committed test because it requires
cherry-picking a commit from a different branch by hash, which would be fragile
to pin permanently — it's recorded here as a one-time manual verification. It
should be re-run once both branches are actually merged, at which point it can
become the automated `test_stage_b_...` case (replacing the current
"expected failure" assertion with a success assertion).

## Net conclusion

The whole roadmap's foundational premise — a vispy-free napari core can actually
run inside Pyodide — is now **experimentally confirmed**, not just inferred. The
remaining gap before Phase 0 is fully closed on a single branch is small and
mechanical: merge or cherry-pick `54db16d0e` (psutil-optional) from
`decouple-core-from-qt` into whatever branch eventually ships this. No other
surprises turned up in Stage B/C beyond magicgui's hard-import status and the
tightened understanding of the qtpy/superqt/napari-svg situations documented
above — no npe2 entry-point discovery weirdness, no dask threading issues, no
single-threaded/no-GIL wasm quirks were observed in the paths this spike
exercised (construction + `add_image` + `add_shapes` only; broader plugin
discovery and dask-array-backed layers are untested by this spike).
