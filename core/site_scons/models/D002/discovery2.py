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
    board = "D002/boards/stm32u5g9j-dk.h"
    hw_model = get_hw_model_as_number("D002")
    hw_revision = 0

    mcu = "STM32U5G9xx"
    linker_script = """embed/sys/linker/stm32u5g/{target}.ld"""

    stm32u5_common_files(env, defines, sources, paths)

    env.get("ENV")[
        "CPU_ASFLAGS"
    ] = "-mthumb -mcpu=cortex-m33 -mfloat-abi=hard -mfpu=fpv5-sp-d16 "
    env.get("ENV")[
        "CPU_CCFLAGS"
    ] = "-mthumb -mcpu=cortex-m33 -mfloat-abi=hard -mfpu=fpv5-sp-d16 -mtune=cortex-m33 -mcmse "
    env.get("ENV")["RUST_TARGET"] = "thumbv8m.main-none-eabihf"

    defines += [
        mcu,
        ("TREZOR_BOARD", f'"{board}"'),
        ("HW_MODEL", str(hw_model)),
        ("HW_REVISION", str(hw_revision)),
        ("HSE_VALUE", "16000000"),
        ("USE_HSE", "1"),
    ]

    sources += [
        "embed/io/display/ltdc_dsi/display_driver.c",
        "embed/io/display/ltdc_dsi/panels/stm32u5a9j-dk/stm32u5a9j-dk.c",
        "embed/io/display/ltdc_dsi/display_fb.c",
        "embed/io/display/ltdc_dsi/display_fb_rgb888.c",
        # "embed/io/display/ltdc_dsi/display_gfxmmu.c",
        "embed/io/display/fb_queue/fb_queue.c",
    ]
    paths += ["embed/io/display/inc"]

    if "input" in features_wanted:
        sources += ["embed/io/i2c_bus/stm32u5/i2c_bus.c"]
        sources += ["embed/io/touch/sitronix/sitronix.c"]
        paths += ["embed/io/i2c_bus/inc"]
        paths += ["embed/io/touch/inc"]
        features_available.append("touch")
        defines += [
            ("USE_TOUCH", "1"),
            ("USE_I2C", "1"),
        ]

    if "usb" in features_wanted:
        sources += [
            "embed/io/usb/stm32/usb_class_hid.c",
            "embed/io/usb/stm32/usb_class_vcp.c",
            "embed/io/usb/stm32/usb_class_webusb.c",
            "embed/io/usb/stm32/usb.c",
            "embed/io/usb/stm32/usbd_conf.c",
            "embed/io/usb/stm32/usbd_core.c",
            "embed/io/usb/stm32/usbd_ctlreq.c",
            "embed/io/usb/stm32/usbd_ioreq.c",
            "vendor/stm32u5xx_hal_driver/Src/stm32u5xx_ll_usb.c",
        ]
        features_available.append("usb")
        paths += ["embed/io/usb/inc"]
        defines += [("USE_USB", "1")]

    defines += [
        "FRAMEBUFFER",
        "DISPLAY_RGBA8888",
        ("UI_COLOR_32BIT", "1"),
        ("USE_RGB_COLORS", "1"),
        ("DISPLAY_RESX", "240"),
        ("DISPLAY_RESY", "240"),
    ]
    features_available.append("framebuffer")
    features_available.append("display_rgba8888")
    features_available.append("ui_color_32bit")

    defines += ["USE_DMA2D"]
    features_available.append("dma2d")
    sources += ["embed/gfx/bitblt/stm32/dma2d_bitblt.c"]

    defines += [
        "USE_HASH_PROCESSOR=1",
        "USE_STORAGE_HWKEY=1",
        "USE_TAMPER=1",
        "USE_FLASH_BURST=1",
        "USE_OEM_KEYS_CHECK=1",
        "USE_RESET_TO_BOOT=1",
    ]

    env.get("ENV")["LINKER_SCRIPT"] = linker_script

    defs = env.get("CPPDEFINES_IMPLICIT")
    defs += ["__ARM_FEATURE_CMSE=3"]

    return features_available
