from __future__ import annotations

from .. import get_hw_model_as_number
from ..stm32u5_common import stm32u5_common_files


def configure(
    env: dict,
    features_wanted: list[str],
    defines: list[str | tuple[str, str]],
    sources: list[str],
    paths: list[str],
) -> list[str]:
    features_available: list[str] = []
    board = "D002/boards/stm32u5a9j-dk.h"
    display = "dsi.c"
    hw_model = get_hw_model_as_number("D002")
    hw_revision = 0

    mcu = "STM32U5A9xx"
    linker_script = """embed/trezorhal/stm32u5/linker/u5a/{target}.ld"""

    stm32u5_common_files(env, defines, sources, paths)

    env.get("ENV")[
        "CPU_ASFLAGS"
    ] = "-mthumb -mcpu=cortex-m33 -mfloat-abi=hard -mfpu=fpv5-sp-d16 "
    env.get("ENV")[
        "CPU_CCFLAGS"
    ] = "-mthumb -mcpu=cortex-m33 -mfloat-abi=hard -mfpu=fpv5-sp-d16 -mtune=cortex-m33 -mcmse "
    env.get("ENV")["RUST_TARGET"] = "thumbv8m.main-none-eabihf"

    defines += [mcu]
    defines += [
        f'TREZOR_BOARD=\\"{board}\\"',
    ]
    defines += [
        f"HW_MODEL={hw_model}",
    ]
    defines += [
        f"HW_REVISION={hw_revision}",
    ]

    if "new_rendering" in features_wanted:
        sources += [
            "embed/trezorhal/xdisplay_legacy.c",
            "embed/trezorhal/stm32u5/xdisplay/stm32u5a9j-dk/display_driver.c",
            "embed/trezorhal/stm32u5/xdisplay/stm32u5a9j-dk/display_fb.c",
            "embed/trezorhal/stm32u5/xdisplay/stm32u5a9j-dk/display_ltdc_dsi.c",
        ]
    else:
        sources += [
            f"embed/trezorhal/stm32u5/displays/{display}",
        ]

    if "input" in features_wanted:
        sources += ["embed/trezorhal/stm32u5/i2c_bus.c"]
        sources += ["embed/trezorhal/stm32u5/touch/sitronix.c"]
        features_available.append("touch")

    # if "sd_card" in features_wanted:
    #     sources += ['embed/trezorhal/sdcard.c', ]
    #     sources += ['embed/extmod/modtrezorio/ff.c', ]
    #     sources += ['embed/extmod/modtrezorio/ffunicode.c', ]
    #     features_available.append("sd_card")

    if "sbu" in features_wanted:
        sources += [
            "embed/trezorhal/stm32u5/sbu.c",
        ]
        features_available.append("sbu")

    if "usb" in features_wanted:
        sources += [
            "embed/trezorhal/stm32u5/usb/usb_class_hid.c",
            "embed/trezorhal/stm32u5/usb/usb_class_vcp.c",
            "embed/trezorhal/stm32u5/usb/usb_class_webusb.c",
            "embed/trezorhal/stm32u5/usb/usb.c",
            "embed/trezorhal/stm32u5/usb/usbd_conf.c",
            "embed/trezorhal/stm32u5/usb/usbd_core.c",
            "embed/trezorhal/stm32u5/usb/usbd_ctlreq.c",
            "embed/trezorhal/stm32u5/usb/usbd_ioreq.c",
            "vendor/stm32u5xx_hal_driver/Src/stm32u5xx_ll_usb.c",
        ]
        features_available.append("usb")

    defines += ["USE_DMA2D", "FRAMEBUFFER", "FRAMEBUFFER32BIT", "UI_COLOR_32BIT"]
    if "new_rendering" in features_wanted:
        sources += ["embed/trezorhal/stm32u5/dma2d_bitblt.c"]
    else:
        sources += ["embed/trezorhal/stm32u5/dma2d.c"]
    features_available.append("dma2d")
    features_available.append("framebuffer")
    features_available.append("framebuffer32bit")
    features_available.append("ui_color_32bit")

    if "new_rendering" in features_wanted:
        defines += ["XFRAMEBUFFER"]
        defines += ["DISPLAY_RGBA8888"]
        features_available.append("xframebuffer")
        features_available.append("display_rgba8888")

    env.get("ENV")["LINKER_SCRIPT"] = linker_script

    defs = env.get("CPPDEFINES_IMPLICIT")
    defs += ["__ARM_FEATURE_CMSE=3"]

    return features_available
