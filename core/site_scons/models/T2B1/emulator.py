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
    board = "T2B1/boards/t2b1-unix.h"
    hw_model = get_hw_model_as_number("T2B1")
    hw_revision = 0
    mcu = "STM32F427xx"

    defines += [
        "FRAMEBUFFER",
        "DISPLAY_MONO",
        ("DISPLAY_RESX", "128"),
        ("DISPLAY_RESY", "64"),
    ]
    features_available.append("framebuffer")
    features_available.append("display_mono")

    defines += [
        mcu,
        ("TREZOR_BOARD", f'"{board}"'),
        ("HW_MODEL", str(hw_model)),
        ("HW_REVISION", str(hw_revision)),
        ("MCU_TYPE", mcu),
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
        sources += ["embed/io/button/unix/button.c"]
        sources += ["embed/io/button/button_fsm.c"]
        paths += ["embed/io/button/inc"]
        features_available.append("button")
        defines += [("USE_BUTTON", "1")]

    sources += ["embed/util/flash/stm32f4/flash_layout.c"]

    return features_available
