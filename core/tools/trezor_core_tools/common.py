from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).parent.resolve()
CORE = HERE.parent.parent

MODELS_DIR = CORE / "embed" / "models"


def get_layout_for_model(model: str) -> Path:
    return MODELS_DIR / model / f"model_{model}.h"

def get_linkerscript_for_model(model: str) -> Path:
    return MODELS_DIR / model / f"memory.ld"
