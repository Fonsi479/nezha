#!/bin/zsh
set -eu
cd -- "$(dirname -- "$0")"
exec python3 deploy/three-vps/open_dashboard.py
