from __future__ import annotations

from types import ModuleType
from typing import Optional

from . import emulator, trezor_r_v10


def configure_board(
    revision: Optional[int | str],
    features_wanted: list[str],
    env: dict,
    defines: list[str | tuple[str, str]],
    sources: list[str],
    paths: list[str],
):
    defines += (("MODEL_HEADER", '"T2B1/model_T2B1.h"'),)
    defines += (("VERSIONS_HEADER", '"T2B1/versions.h"'),)

    # Set default revision if None
    revision = revision or 10

    # Mapping of revisions to their respective configurations
    revision_map: dict[int | str, ModuleType] = {
        "emulator": emulator,
        10: trezor_r_v10,
    }

    module = revision_map.get(revision)

    if module:
        return module.configure(env, features_wanted, defines, sources, paths)

    raise Exception("Unknown model_r_version")


def get_model_ui() -> str:
    return "caesar"


def get_model_ui_conf() -> list[str]:
    return ["bootloader_empty_lock"]
