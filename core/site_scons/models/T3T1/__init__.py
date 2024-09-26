from __future__ import annotations

from typing import Optional

from . import emulator, trezor_t3t1_revE, trezor_t3t1_v4


def configure_board(
    revision: Optional[int | str],
    features_wanted: list[str],
    env: dict,  # type: ignore
    defines: list[str | tuple[str, str]],
    sources: list[str],
    paths: list[str],
):
    # Set default revision if None
    revision = revision or "E"

    # Mapping of revisions to their respective configurations
    revision_map = {
        "emulator": emulator,
        4: trezor_t3t1_v4,
        "E": trezor_t3t1_revE,
    }

    module = revision_map.get(revision)

    if module:
        return module.configure(env, features_wanted, defines, sources, paths)

    raise Exception("Unknown model_r_version")


def get_model_ui() -> str:
    return "mercury"


def get_model_ui_conf() -> list[str]:
    return []
