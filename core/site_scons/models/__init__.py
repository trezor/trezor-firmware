from __future__ import annotations

import importlib
from typing import Optional


def get_hw_model_as_number(hw_model: str) -> int:
    return int.from_bytes(hw_model.encode(), "little")


def configure_board(
    model: str,
    revision: Optional[str],
    features_wanted: list[str],
    env: dict,
    defines: list[str | tuple[str, str]],
    sources: list[str],
    paths: list[str],
) -> list[str]:
    imported_module = importlib.import_module(f"models.{model}")

    features_available = imported_module.configure_board(
        revision, features_wanted, env, defines, sources, paths
    )

    _configure_common_modules(
        env, features_available, features_wanted, defines, sources, paths
    )

    return features_available


def _configure_common_modules(
    env: dict,
    features_available: list[str],
    features_wanted: list[str],
    defines: list[str | tuple[str, str]],
    sources: list[str],
    paths: list[str],
) -> None:

    if "kernel_mode" in features_wanted:
        defines += [("KERNEL_MODE", "1")]
        paths += ["vendor"]
        sources += ["vendor/trezor-storage/flash_area.c"]

    if "secure_mode" in features_wanted:
        defines += [("SECURE_MODE", "1")]

    if "storage" in features_wanted:
        paths += ["embed/sec/storage/inc"]
        paths += ["vendor"]
        defines += [("USE_STORAGE", "1")]

        if "secure_mode" in features_wanted:
            sources += [
                "embed/sec/storage/storage_setup.c",
                "vendor/trezor-storage/norcow.c",
                "vendor/trezor-storage/storage.c",
                "vendor/trezor-storage/storage_utils.c",
            ]

        features_available.append("storage")


def has_emulator(model: str) -> bool:
    imported_module = importlib.import_module(f"models.{model}")
    return hasattr(imported_module, "emulator")


def get_model_ui(model: str) -> str:
    imported_module = importlib.import_module(f"models.{model}")
    return imported_module.get_model_ui()


def get_model_ui_conf(model: str) -> str:
    imported_module = importlib.import_module(f"models.{model}")
    return imported_module.get_model_ui_conf()
