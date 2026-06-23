#!/bin/sh
set -e
cd "$(dirname "$0")"

git config diff.csvjson.textconv 'csvjson -I -i 2'
git config diff.csvjson.cachetextconv true

echo "Configured csvjson diff driver. Requires csvjson on PATH (pip install csvkit)."
