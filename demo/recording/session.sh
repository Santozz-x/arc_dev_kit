#!/usr/bin/env bash
# Real terminal session: fresh venv -> pip install arc-devkit from PyPI ->
# live query + analysis of a real Arc Mainnet transaction.
# Every command below actually executes; nothing here is pre-recorded output.
set -e

prompt() {
  printf '\033[1;32m$\033[0m \033[1m%s\033[0m\n' "$1"
}

run() {
  prompt "$1"
  eval "$1"
  echo
}

clear
echo "Arc DevKit — Mainnet Demo: from a fresh venv to a live Arc Mainnet query"
echo "=========================================================================="
echo
sleep 1

run "python3 --version"
sleep 1

run "python3 -m venv .venv"
sleep 1

run "source .venv/bin/activate"
sleep 1

run "pip install --quiet --upgrade pip"
sleep 1

run "pip install arc-devkit==0.10.0"
sleep 1

run "python3 -c \"import arc_devkit; print('arc-devkit', arc_devkit.__version__)\""
sleep 1

run "python3 -c \"import arc_devkit.client; print(arc_devkit.client.__file__)\""
sleep 2

prompt "python3 mainnet_demo.py"
python3 mainnet_demo.py
echo
sleep 2

echo "=========================================================================="
echo "Session complete."
