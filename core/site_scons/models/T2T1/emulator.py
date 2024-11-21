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
    board = "T2T1/boards/t2t1-unix.h"
    hw_model = get_hw_model_as_number("T2T1")
    hw_revision = 0
    mcu = "STM32F427xx"

    defines += ["DISPLAY_RGB565"]
    features_available.append("display_rgb565")
    defines += [("USE_RGB_COLORS", "1")]

    defines += [
        mcu,
        ("TREZOR_BOARD", f'"{board}"'),
        ("HW_MODEL", str(hw_model)),
        ("HW_REVISION", str(hw_revision)),
        ("MCU_TYPE", mcu),
        ("FLASH_BIT_ACCESS", "1"),
        ("FLASH_BLOCK_WORDS", "1"),
    ]

    if "sd_card" in features_wanted:
        features_available.append("sd_card")
        sources += [
            "embed/io/sdcard/unix/sdcard.c",
            "embed/upymod/modtrezorio/ff.c",
            "embed/upymod/modtrezorio/ffunicode.c",
        ]
        paths += ["embed/io/sdcard/inc"]
        defines += [("USE_SD_CARD", "1")]

    if "sbu" in features_wanted:
        sources += ["embed/io/sbu/unix/sbu.c"]
        paths += ["embed/io/sbu/inc"]
        defines += [("USE_SBU", "1")]

    if "input" in features_wanted:
        sources += ["embed/io/touch/unix/touch.c"]
        paths += ["embed/io/touch/inc"]
        features_available.append("touch")
        defines += [("USE_TOUCH", "1")]

    features_available.append("backlight")
    defines += [("USE_BACKLIGHT", "1")]

    sources += ["embed/util/flash/stm32f4/flash_layout.c"]

    return features_available
