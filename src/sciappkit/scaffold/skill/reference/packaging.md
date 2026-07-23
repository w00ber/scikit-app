# Packaging & releases (PyInstaller + GitHub Actions)

`create-sciapp` provisions all of this in every generated project:
`<pkg>.spec`, `<pkg>_launcher.py`, and `.github/workflows/build.yml`.
This reference explains the choices so you can adapt them safely. The
patterns are lifted from the framework's two ancestor apps (Diagrammer,
graphulator), including fixes for traps they hit in production.

## The spec (`<pkg>.spec`)

- **Entry point is a launcher shim** (`<pkg>_launcher.py`), not
  `__main__.py`: PyInstaller analyzes a *script*, and `__main__.py`'s
  relative import (`from .app import main`) fails when frozen as the
  top-level script. The shim does the absolute import.
- **Version is parsed textually** from `src/<pkg>/__init__.py`, never
  imported — importing would pull PySide6/matplotlib into PyInstaller's
  spec-evaluation process.
- **`datas` mirrors `[tool.setuptools.package-data]`** (`defaults.yaml`,
  `icons/`). PyInstaller does not read pyproject package-data; keep the two
  lists in sync when you add bundled files. At runtime, always resolve
  bundled files relative to `__file__`, never the CWD.
- **Qt excludes**: the generated list drops the heavyweight Qt modules a
  default sciappkit app never loads (WebEngine, Qml/Quick, 3D, Charts,
  Multimedia, …). Remove the WebEngine entries if the app uses
  `MarkdownEditor(backend="web")`. **Never exclude stdlib modules that
  dependencies import at load time** — matplotlib needs `unittest.mock`
  via its import chain, so excluding `unittest` breaks the frozen app.
- **matplotlib backend hiddenimports** (`backend_agg/svg/pdf`): since
  PyInstaller 5.0 the matplotlib hook only bundles backends it sees
  imported literally. sciappkit's exporters import them lazily via
  `savefig(format=...)`, so they must be listed or frozen exports fail
  (pyinstaller/pyinstaller#6760).
- **Icons**: `EXE(icon=...)` takes the Windows `.ico` (CI generates it
  from the `icons/` PNG ladder with Pillow); `BUNDLE(icon=...)` takes a
  macOS `.icns` at `src/<pkg>/icons/app.icns` (build with `iconutil`, see
  the generated `icons/README.md`). Both optional — without them the app
  still gets its runtime `QIcon` from `set_app_icon`.
- One-folder build (`COLLECT`) + mac `.app` `BUNDLE` with
  `CFBundleShortVersionString` from the parsed version.

## The workflow (`.github/workflows/build.yml`)

Trigger surface:

- `push: tags: ["v*"]` — the release path: test → build matrix → attach
  zips to the tag's GitHub release.
- `workflow_dispatch` with an optional `release_tag` input — rebuilds and
  (re)attaches assets to an *existing* release without regenerating its
  notes; with the input blank it just builds artifacts.

Job structure and the two traps it avoids:

1. `test` gates the platform builds: headless suite on ubuntu
   (`QT_QPA_PLATFORM=offscreen`) after installing Qt's system libs via apt.
2. `build` matrix (macos-latest, windows-latest) runs PyInstaller and
   uploads **workflow artifacts only** — build jobs never touch the
   release.
3. `release` is the **single release writer**, attaching every zip in one
   `softprops/action-gh-release@v2` call. Why single-writer:
   - per-platform release steps racing to mutate the same release can 404
     during finalize and silently drop an upload (a real lost-asset bug);
   - parallel `gh release create --draft` calls each spawn a *new* draft,
     because drafts have no realized tag ref to deduplicate on.
   `needs: build` means one failed platform blocks the whole release
   rather than shipping it partially.

Until sciappkit is on PyPI, the workflow installs it from git
(`pip install "sciappkit @ git+https://github.com/w00ber/scikit-app"`)
before the app — drop that line after M4 (publish).

## Optional: version-bump workflow

For a tag-driven release flow without local tagging, add a
`workflow_dispatch` workflow with a `level: [patch, minor, major]` choice
input that bumps `__version__` (+ pyproject), commits, tags `v<version>`,
and pushes — the tag push then triggers the build workflow. graphulator's
`bump-version.yml` is the reference implementation.

## Local builds (macOS / conda)

`pip install pyinstaller && pyinstaller <pkg>.spec` inside the app's env.
Under conda/miniforge, a stray `DYLD_LIBRARY_PATH` (Homebrew or other
SDKs) can break the frozen app's library resolution — unset it in the
shell you build from.
