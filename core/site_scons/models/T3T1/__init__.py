from __future__ import annotations

from types import ModuleType
from typing import Optional

from . import emulator, trezor_t3t1_revE


def configure_board(
    revision: Optional[str],
    features_wanted: list[str],
    env: dict,
    defines: list[str | tuple[str, str]],
    sources: list[str],
    paths: list[str],
):
    defines += (("MODEL_HEADER", '"T3T1/model_T3T1.h"'),)
    defines += (("VERSIONS_HEADER", '"T3T1/versions.h"'),)

    # Set default revision if None
    revision = revision or "E"

    # Mapping of revisions to their respective configurations
    revision_map: dict[str, ModuleType] = {
        "emulator": emulator,
        "E": trezor_t3t1_revE,
    }

    module = revision_map.get(revision)

    if module:
        return module.configure(env, features_wanted, defines, sources, paths)

    raise Exception("Unknown model_r_version")


def get_model_ui() -> str:
    return "delizia"


def get_model_ui_conf() -> list[str]:
    return []
