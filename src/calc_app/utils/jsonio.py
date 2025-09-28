# src/calc_app/jsonio.py
from pathlib import Path
from typing import Any, Tuple
import json
import tempfile
import os

def read_json(path: Path) -> Tuple[bool, Any]:
    """
    Returns (ok, data). ok=False if file missing or invalid JSON.
    """
    try:
        with path.open("r", encoding="utf-8") as f:
            return True, json.load(f)
    except FileNotFoundError:
        return False, None
    except Exception:
        return False, None

def write_json_atomic(path: Path, data: Any) -> None:
    """
    Write JSON atomically: write to temp file, then replace.
    Creates parent dirs as needed.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name, dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass
