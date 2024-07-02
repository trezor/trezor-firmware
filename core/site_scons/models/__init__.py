from __future__ import annotations

import importlib
from typing import Optional


def get_hw_model_as_number(hw_model: str) -> int:
    return int.from_bytes(hw_model.encode(), "little")


def configure_board(
    model: str,
    revision: Optional[str | int],
    features_wanted: list[str],
    env: dict,  # type: ignore
    defines: list[str | tuple[str, str]],
    sources: list[str],
    paths: list[str],
) -> list[str]:
    imported_module = importlib.import_module("models." + get_model_identifier(model))
    return imported_module.configure_board(
        revision, features_wanted, env, defines, sources, paths
    )


def get_model_identifier(model: str) -> str:
    if model == "1":
        return "T1B1"
    elif model == "T":
        return "T2T1"
    elif model == "R":
        return "T2B1"
    elif model == "T3T1":
        return "T3T1"
    elif model == "T3B1":
        return "T3B1"
    elif model == "DISC1":
        return "D001"
    elif model == "DISC2":
        return "D002"
    else:
        return model
