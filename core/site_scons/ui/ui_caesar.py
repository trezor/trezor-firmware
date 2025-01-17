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

    font_normal = None
    font_demibold = None
    font_bold = None
    font_mono = None
    font_big = None
    font_normal_upper = None
    font_bold_upper = None
    font_sub = None

    if stage == "bootloader":
        font_normal = "Font_PixelOperator_Regular_8"
        font_demibold = "Font_PixelOperator_Regular_8"
        font_bold = "Font_PixelOperator_Bold_8"
        font_mono = "Font_PixelOperator_Regular_8"
        font_big = "Font_PixelOperator_Regular_8"
        font_normal_upper = "Font_PixelOperator_Regular_8_upper"
        if "bootloader_empty_lock" in config:
            rust_features.append("ui_empty_lock")
    if stage == "prodtest":
        font_bold = "Font_PixelOperator_Bold_8"
    if stage == "firmware":
        font_normal = "Font_PixelOperator_Regular_8"
        font_demibold = "Font_Unifont_Bold_16"
        font_bold = "Font_PixelOperator_Bold_8"
        font_mono = "Font_PixelOperatorMono_Regular_8"
        font_big = "Font_Unifont_Regular_16"
        font_normal_upper = "Font_PixelOperator_Regular_8_upper"
        font_bold_upper = "Font_PixelOperator_Bold_8_upper"

    # fonts
    add_font("NORMAL", font_normal, defines, sources)
    add_font("BOLD", font_bold, defines, sources)
    add_font("DEMIBOLD", font_demibold, defines, sources)
    add_font("MONO", font_mono, defines, sources)
    add_font("BIG", font_big, defines, sources)
    add_font("NORMAL_UPPER", font_normal_upper, defines, sources)
    add_font("BOLD_UPPER", font_bold_upper, defines, sources)
    add_font("SUB", font_sub, defines, sources)


def get_ui_layout() -> str:
    return "UI_LAYOUT_CAESAR"


def get_ui_layout_path() -> str:
    return "trezor/ui/layouts/caesar/"
