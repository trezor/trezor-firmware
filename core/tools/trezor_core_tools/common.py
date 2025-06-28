from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).parent.resolve()
CORE = HERE.parent.parent

MODELS_DIR = CORE / "embed" / "models"


def get_layout_for_model(model: str, secmon: bool) -> Path:
    if secmon:
        return MODELS_DIR / model / "memory_secmon.h"
    else:
        return MODELS_DIR / model / "memory.h"


def get_linkerscript_for_model(model: str, secmon: bool) -> Path:
    if secmon:
        return MODELS_DIR / model / "memory_secmon.ld"
    else:
        return MODELS_DIR / model / "memory.ld"
