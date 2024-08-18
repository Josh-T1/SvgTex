#!/bin/bash
PROJECT_NAME="VectorGraphics"
FILE_DIR_NAME="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$FILE_DIR_NAME")"
VENV_DIR="$PROJECT_DIR/Venv"
INTERPRETER_PATH="$VENV_DIR/$PROJECT_NAME/bin/python3"
CURRENT_DIR="$(pwd)"

full_path=""
while [[ "$#" -gt 0 ]]; do
    case $1 in
        -f|--file)
            file_arg="$2"
            shift 2
            ((num=num-2))
            ;;
        *)
            shift 1
            ;;
    esac
done
            
if [[ -n "$file_arg" ]]; then
    full_path="$(realpath "$file_arg" 2>/dev/null)"
fi

cd "$PROJECT_DIR"
if [[ -n "$full_path" ]]; then
    "$INTERPRETER_PATH" -m "$PROJECT_NAME.cli" "--file" "$full_path"
else
    "$INTERPRETER_PATH" -m "$PROJECT_NAME.cli"
fi
cd "$CURRENT_DIR"
