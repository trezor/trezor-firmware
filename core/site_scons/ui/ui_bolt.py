from __future__ import annotations

from .common import add_font


def init_ui(
    stage: str,
    config: list[str],
    defines: list[str | tuple[str, str]],
    sources: list[str],
    rust_features: list[str],
):

    rust_features.append("layout_bolt")

    if stage == "bootloader":
        pass
    if stage == "bootloader_ci":
        add_font("NORMAL", "Font_TTHoves_Regular_21", defines, sources)
        add_font("BOLD", "Font_TTHoves_Bold_17_upper", defines, sources)
    if stage == "prodtest":
        add_font("BOLD", "Font_Roboto_Bold_20", defines, sources)
    if stage == "firmware":
        rust_features.append("ui_blurring")
        rust_features.append("ui_jpeg_decoder")


def get_ui_layout() -> str:
    return "UI_LAYOUT_BOLT"


def get_ui_layout_path() -> str:
    return "trezor/ui/layouts/bolt/"
