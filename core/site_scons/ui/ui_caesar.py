from __future__ import annotations

from .common import add_font


def init_ui(
    stage: str,
    config: list[str],
    defines: list[str | tuple[str, str]],
    sources: list[str],
    rust_features: list[str],
):

    rust_features.append("layout_caesar")

    if stage == "bootloader":
        if "bootloader_empty_lock" in config:
            rust_features.append("ui_empty_lock")
    if stage in ("bootloader_ci", "prodtest"):
        add_font("NORMAL", "Font_PixelOperator_Regular_8", defines, sources)
        add_font("BOLD", "Font_PixelOperator_Bold_8", defines, sources)
    if stage == "firmware":
        pass


def get_ui_layout() -> str:
    return "UI_LAYOUT_CAESAR"


def get_ui_layout_path() -> str:
    return "trezor/ui/layouts/caesar/"
