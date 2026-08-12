#!/usr/bin/env bash
# Idempotent bootstrap for the D3D Manager Tool (CustomTkinter desktop app).
# Safe to run repeatedly: installs system packages only when missing and
# refreshes Python dependencies inside a local virtualenv.
set -euo pipefail

cd "$(dirname "$0")/.."

# System packages: Tk runtime for the Tkinter GUI, venv support, and
# Noto CJK fonts so the Traditional Chinese UI renders instead of tofu boxes.
need_apt=0
for pkg in python3-tk python3-venv fonts-noto-cjk; do
  dpkg -s "$pkg" >/dev/null 2>&1 || need_apt=1
done
if [ "$need_apt" -eq 1 ]; then
  sudo apt-get update -qq
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
    python3-tk python3-venv fonts-noto-cjk
fi

# Python virtualenv (git-ignored). Holds customtkinter and its deps.
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
. .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo "install.sh complete: run the app with '.venv/bin/python app.py'"
