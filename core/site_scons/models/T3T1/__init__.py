from __future__ import annotations

from typing import Optional

from .trezor_t3t1_revE import configure as configure_revE
from .trezor_t3t1_v4 import configure as configure_v4


def configure_board(
    revision: Optional[int | str],
    features_wanted: list[str],
    env: dict,  # type: ignore
    defines: list[str | tuple[str, str]],
    sources: list[str],
    paths: list[str],
):
    if revision is None:
        revision = "E"
    if revision == 4:
        return configure_v4(env, features_wanted, defines, sources, paths)
    elif revision == "E":
        return configure_revE(env, features_wanted, defines, sources, paths)
    raise Exception("Unknown model_t3t1_version")
