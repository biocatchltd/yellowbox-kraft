#!/bin/sh
# run various linters
set -e
echo "running black..."
python -m ruff format . --check
echo "running ruff..."
python -m ruff check .
echo "running mypy..."
python3 -m mypy --show-error-codes yellowbox_kraft
