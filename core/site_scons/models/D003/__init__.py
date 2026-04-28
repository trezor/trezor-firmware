from __future__ import annotations

from typing import Optional

from .discovery3_200 import configure


def configure_board(
    revision: Optional[str],
    features_wanted: list[str],
    env: dict,
    defines: list[str | tuple[str, str]],
    sources: list[str],
    paths: list[str],
):
    defines += (("MODEL_HEADER", '"D003/model_D003.h"'),)
    defines += (("VERSIONS_HEADER", '"D003/versions.h"'),)
    defines += (("OTP_LAYOUT_HEADER", '"D003/otp_layout.h"'),)
    defines += (("UNIT_PROPERTIES_CONTENT_HEADER", '"D003/unit_properties_content.h"'),)
    return configure(env, features_wanted, defines, sources, paths)


def get_model_ui() -> str:
    return "caesar"


def get_model_ui_conf() -> list[str]:
    return []
