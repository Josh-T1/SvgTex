#!/bin/bash

FILE_DIR_NAME="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$FILE_DIR_NAME")"

cd "$PROJECT_DIR"
python -m VectorGraphics.main_cli "$@"

