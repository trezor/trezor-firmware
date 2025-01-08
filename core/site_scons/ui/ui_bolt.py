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

    font_normal = None
    font_demibold = None
    font_bold = None
    font_mono = None
    font_big = None
    font_normal_upper = None
    font_bold_upper = None
    font_sub = None

    if stage == "bootloader":
        font_normal = "Font_TTHoves_Regular_21"
        font_demibold = "Font_TTHoves_Regular_21"
        font_bold = "Font_TTHoves_Bold_17_upper"
        font_mono = "Font_TTHoves_Regular_21"
        font_bold_upper = "Font_TTHoves_Bold_17_upper"
    if stage == "prodtest":
        font_bold = "Font_Roboto_Bold_20"
    if stage == "firmware":
        font_normal = "Font_TTHoves_Regular_21"
        font_demibold = "Font_TTHoves_DemiBold_21"
        font_mono = "Font_RobotoMono_Medium_20"
        font_bold_upper = "Font_TTHoves_Bold_17_upper"
        rust_features.append("ui_blurring")
        rust_features.append("ui_jpeg_decoder")

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
    return "UI_LAYOUT_BOLT"


def get_ui_layout_path() -> str:
    return "trezor/ui/layouts/bolt/"
