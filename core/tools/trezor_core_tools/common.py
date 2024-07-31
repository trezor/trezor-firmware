from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).parent.resolve()
CORE = HERE.parent.parent

MODELS_DIR = CORE / "embed" / "models"

MODELS_DICT = {
    "1": "T1B1",
    "T": "T2T1",
    "R": "T2B1",
    "DISC1": "D001",
    "DISC2": "D002",
}


def get_layout_for_model(model: str) -> Path:
    model = MODELS_DICT.get(model, model)
    return MODELS_DIR / model / f"model_{model}.h"
