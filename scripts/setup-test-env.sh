#!/usr/bin/env bash
# Prepare the environment so the sciappkit test suite can run Qt headless.
#
# Installs:
#   1. The system libraries PySide6's Qt platform plugins need (offscreen
#      works with libEGL/libGL; the xcb plugin additionally needs the
#      xcb-cursor / xkbcommon-x11 libraries to run under xvfb).
#   2. The Python dependencies (sciappkit + its [dev] extra).
#
# Safe to re-run. Intended for CI and for Claude Code web sessions
# (wired up as a SessionStart hook in .claude/settings.json).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> Installing system libraries for headless Qt"
if command -v apt-get >/dev/null 2>&1; then
    SUDO=""
    if [ "$(id -u)" -ne 0 ]; then SUDO="sudo"; fi
    $SUDO apt-get update -qq || true
    $SUDO apt-get install -y -qq \
        libegl1 libgl1 libglx-mesa0 \
        libxkbcommon0 libxkbcommon-x11-0 \
        libdbus-1-3 libfontconfig1 libxrender1 \
        libxcb-cursor0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \
        libxcb-render-util0 libxcb-shape0 libxcb-xinerama0 libxcb-xkb1 \
        xvfb || true
else
    echo "    (apt-get not found; skipping system libraries)"
fi

echo "==> Installing Python dependencies"
python3 -m pip install --quiet --upgrade pip
python3 -m pip install --quiet -e "${REPO_ROOT}[dev]"

echo "==> Verifying headless Qt + matplotlib"
QT_QPA_PLATFORM=offscreen python3 - <<'PY'
from PySide6.QtWidgets import QApplication
app = QApplication([])
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
FigureCanvasQTAgg(Figure())
import sciappkit
print(f"OK: sciappkit {sciappkit.__version__}, Qt headless + matplotlib qtagg ready")
PY

echo "==> Done. Run the suite with:  QT_QPA_PLATFORM=offscreen pytest"
