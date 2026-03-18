#!/bin/bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

VENV_DIR="${PROJECT_DIR}/.venv"

if [ ! -d "$VENV_DIR" ]; then
  echo "Создание виртуального окружения..."
  python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

echo "Установка зависимостей..."
pip install -r requirements.txt

echo "Запуск Streamlit..."
streamlit run app/dashboard.py
