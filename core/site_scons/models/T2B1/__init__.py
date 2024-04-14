from __future__ import annotations

from typing import Optional

from .trezor_r_v3 import configure as configure_r3
from .trezor_r_v4 import configure as configure_r4
from .trezor_r_v6 import configure as configure_r6
from .trezor_r_v10 import configure as configure_r10


def configure_board(
    revision: Optional[int | str],
    features_wanted: list[str],
    env: dict,  # type: ignore
    defines: list[str | tuple[str, str]],
    sources: list[str],
    paths: list[str],
):
    if revision is None:
        revision = 10
    if revision == 3:
        return configure_r3(env, features_wanted, defines, sources, paths)
    elif revision == 4:
        return configure_r4(env, features_wanted, defines, sources, paths)
    elif revision == 6:
        return configure_r6(env, features_wanted, defines, sources, paths)
    elif revision == 10:
        return configure_r10(env, features_wanted, defines, sources, paths)
    raise Exception("Unknown model_r_version")
