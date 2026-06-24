#!/usr/bin/env bash
set -euo pipefail

PYTHONPATH=src python3 -m unittest discover -s tests
PYTHONPATH=src python3 -m tellygrab.cli --help >/dev/null
if [[ "${TELLYGRAB_SKIP_DOCTOR:-0}" != "1" ]]; then
  PYTHONPATH=src python3 -m tellygrab.cli doctor
fi
