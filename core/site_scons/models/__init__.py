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
    imported_module = importlib.import_module(f"models.{model}")
    return imported_module.configure_board(
        revision, features_wanted, env, defines, sources, paths
    )


def has_emulator(model: str) -> bool:
    imported_module = importlib.import_module(f"models.{model}")
    return hasattr(imported_module, "emulator")


def get_model_ui(model: str) -> str:
    imported_module = importlib.import_module(f"models.{model}")
    return imported_module.get_model_ui()


def get_model_ui_conf(model: str) -> str:
    imported_module = importlib.import_module(f"models.{model}")
    return imported_module.get_model_ui_conf()
