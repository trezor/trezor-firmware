from __future__ import annotations

from typing import Optional

from .discovery import configure


def configure_board(
    revision: Optional[int | str],
    features_wanted: list[str],
    env: dict,  # type: ignore
    defines: list[str | tuple[str, str]],
    sources: list[str],
    paths: list[str],
):
    return configure(env, features_wanted, defines, sources, paths)
