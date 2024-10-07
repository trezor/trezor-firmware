from __future__ import annotations

from typing import Optional

from . import emulator, trezor_t3w1_d1


def configure_board(
    revision: Optional[int | str],
    features_wanted: list[str],
    env: dict,  # type: ignore
    defines: list[str | tuple[str, str]],
    sources: list[str],
    paths: list[str],
):
    # Set default revision if None
    revision = revision or "d1"

    # Mapping of revisions to their respective configurations
    revision_map = {
        "emulator": emulator,
        "d1": trezor_t3w1_d1,
    }

    module = revision_map.get(revision)

    if module:
        return module.configure(env, features_wanted, defines, sources, paths)

    raise Exception("Unknown model_r_version")


def get_model_ui() -> str:
    return "tt"


def get_model_ui_conf() -> list[str]:
    return []
