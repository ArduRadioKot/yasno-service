#!/bin/sh
# Исправляет shebang в pip/pip3, если venv был скопирован из другого проекта.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/.venv/bin/python3.14"
[ -x "$PY" ] || PY="$ROOT/.venv/bin/python"
for script in "$ROOT/.venv/bin/pip" "$ROOT/.venv/bin/pip3"; do
  [ -f "$script" ] && printf '%s\n' "#!$PY" | cat - "$(tail -n +2 "$script")" > "$script.tmp" && mv "$script.tmp" "$script" && chmod +x "$script"
done
