#!/bin/bash

PROJECT_NAME="VectorGraphics"
FILE_DIR_NAME="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$FILE_DIR_NAME")"
VENV_DIR="$PROJECT_DIR/Venv"
INTERPRETER_PATH="$VENV_DIR/$PROJECT_NAME/bin/python3"

cd "$PROJECT_DIR"
"$INTERPRETER_PATH" -m "$PROJECT_NAME.main_cli" "$@"

