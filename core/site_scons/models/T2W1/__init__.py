from __future__ import annotations

from typing import Optional

from .t2w1 import configure


def configure_board(
    revision: Optional[int | str],
    features_wanted: list[str],
    env: dict,  # type: ignore
    defines: list[str | tuple[str, str]],
    sources: list[str],
    paths: list[str],
):
    defines += (("MODEL_HEADER", '"T2W1/model_T2W1.h"'),)
    defines += (("VERSIONS_HEADER", '"T2W1/versions.h"'),)

    return configure(env, features_wanted, defines, sources, paths)


def get_model_ui() -> str:
    return "bolt"


def get_model_ui_conf() -> list[str]:
    return []
