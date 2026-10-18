#!/bin/zsh
set -e
converter_root="${0:A:h}"
exec "$converter_root/.venv/bin/python" "$converter_root/car-converter/convert_car.py" "$@"
