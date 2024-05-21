from __future__ import annotations

from typing import Optional

from .emulator import configure as emul
from .trezor_1 import configure


def configure_board(
    revision: Optional[int | str],
    features_wanted: list[str],
    env: dict,  # type: ignore
    defines: list[str | tuple[str, str]],
    sources: list[str],
    paths: list[str],
):
    if revision == "emulator":
        return emul(env, features_wanted, defines, sources, paths)
    else:
        return configure(env, features_wanted, defines, sources, paths)
