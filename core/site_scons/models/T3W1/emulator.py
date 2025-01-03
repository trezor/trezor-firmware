from __future__ import annotations

from .. import get_hw_model_as_number


def configure(
    env: dict,
    features_wanted: list[str],
    defines: list[str | tuple[str, str]],
    sources: list[str],
    paths: list[str],
) -> list[str]:

    features_available: list[str] = []
    board = "T3W1/boards/t3w1-unix.h"
    hw_model = get_hw_model_as_number("T3W1")
    hw_revision = 0
    mcu = "STM32U5G9xx"

    defines += [
        "FRAMEBUFFER",
        ("USE_RGB_COLORS", "1"),
        "DISPLAY_RGBA8888",
        "UI_COLOR_32BIT",
        ("DISPLAY_RESX", "380"),
        ("DISPLAY_RESY", "520"),
    ]
    features_available.append("framebuffer")
    features_available.append("display_rgba8888")
    features_available.append("ui_color_32bit")

    defines += [
        mcu,
        ("TREZOR_BOARD", f'"{board}"'),
        ("HW_MODEL", str(hw_model)),
        ("HW_REVISION", str(hw_revision)),
        ("MCU_TYPE", mcu),
        # todo change to blockwise flash when implemented in unix
        ("FLASH_BIT_ACCESS", "1"),
        ("FLASH_BLOCK_WORDS", "1"),
    ]

    if "sbu" in features_wanted:
        sources += ["embed/io/sbu/unix/sbu.c"]
        paths += ["embed/io/sbu/inc"]
        defines += [("USE_SBU", "1")]

    if "optiga" in features_wanted:
        sources += ["embed/sec/optiga/unix/optiga_hal.c"]
        sources += ["embed/sec/optiga/unix/optiga.c"]
        paths += ["embed/sec/optiga/inc"]
        features_available.append("optiga")
        defines += [("USE_OPTIGA", "1")]

    if "input" in features_wanted:
        sources += ["embed/io/touch/unix/touch.c"]
        paths += ["embed/io/touch/inc"]
        features_available.append("touch")
        defines += [("USE_TOUCH", "1")]

    features_available.append("backlight")
    defines += [("USE_BACKLIGHT", "1")]

    sources += ["embed/util/flash/stm32u5/flash_layout.c"]

    return features_available
