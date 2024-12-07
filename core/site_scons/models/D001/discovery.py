from __future__ import annotations

from .. import get_hw_model_as_number
from ..stm32f4_common import stm32f4_common_files


def configure(
    env: dict,
    features_wanted: list[str],
    defines: list[str | tuple[str, str]],
    sources: list[str],
    paths: list[str],
) -> list[str]:
    features_available: list[str] = []
    board = "D001/boards/stm32f429i-disc1.h"
    hw_model = get_hw_model_as_number("D001")
    hw_revision = 0

    mcu = "STM32F429xx"

    stm32f4_common_files(env, defines, sources, paths)

    env.get("ENV")[
        "CPU_ASFLAGS"
    ] = "-mthumb -mcpu=cortex-m4 -mfloat-abi=hard -mfpu=fpv4-sp-d16"
    env.get("ENV")[
        "CPU_CCFLAGS"
    ] = "-mthumb -mcpu=cortex-m4 -mfloat-abi=hard -mfpu=fpv4-sp-d16 -mtune=cortex-m4 "
    env.get("ENV")["RUST_TARGET"] = "thumbv7em-none-eabihf"

    defines += [
        mcu,
        ("TREZOR_BOARD", f'"{board}"'),
        ("HW_MODEL", str(hw_model)),
        ("HW_REVISION", str(hw_revision)),
        ("HSE_VALUE", "8000000"),
        ("USE_HSE", "1"),
    ]

    sources += [
        "embed/io/display/stm32f429i-disc1/display_driver.c",
        "embed/io/display/stm32f429i-disc1/display_ltdc.c",
        "embed/io/display/stm32f429i-disc1/ili9341_spi.c",
    ]
    paths += ["embed/io/display/inc"]

    sources += ["embed/gfx/bitblt/stm32/dma2d_bitblt.c"]

    sources += [
        "vendor/micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_dma2d.c"
    ]
    sources += [
        "vendor/micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_dma.c"
    ]
    defines += ["USE_DMA2D"]
    defines += [("USE_RGB_COLORS", "1")]
    features_available.append("dma2d")

    defines += ["FRAMEBUFFER"]
    defines += ["DISPLAY_RGB565"]
    features_available.append("framebuffer")
    features_available.append("display_rgb565")

    sources += ["embed/sys/sdram/stm32f429i-disc1/sdram_bsp.c"]
    paths += ["embed/sys/sdram/inc"]
    defines += [("USE_SDRAM", "1")]

    if "input" in features_wanted:
        sources += ["embed/io/i2c_bus/stm32f4/i2c_bus.c"]
        sources += ["embed/io/touch/stmpe811/stmpe811.c"]
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
            "vendor/micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_ll_usb.c",
        ]
        features_available.append("usb")
        paths += ["embed/io/usb/inc"]

    defines += [("USE_PVD", "1")]

    return features_available
