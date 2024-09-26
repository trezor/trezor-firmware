from __future__ import annotations

from typing import Optional

from . import emulator, trezor_r_v3, trezor_r_v4, trezor_r_v6, trezor_r_v10


def configure_board(
    revision: Optional[int | str],
    features_wanted: list[str],
    env: dict,  # type: ignore
    defines: list[str | tuple[str, str]],
    sources: list[str],
    paths: list[str],
):
    # Set default revision if None
    revision = revision or 10

    # Mapping of revisions to their respective configurations
    revision_map = {
        "emulator": emulator,
        3: trezor_r_v3,
        4: trezor_r_v4,
        6: trezor_r_v6,
        10: trezor_r_v10,
    }

    module = revision_map.get(revision)

    if module:
        return module.configure(env, features_wanted, defines, sources, paths)

    raise Exception("Unknown model_r_version")


def get_model_ui() -> str:
    return "tr"


def get_model_ui_conf() -> list[str]:
    return ["bootloader_empty_lock"]
