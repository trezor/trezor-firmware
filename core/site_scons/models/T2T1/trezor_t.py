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
    board = "T2T1/boards/trezor_t.h"
    hw_model = get_hw_model_as_number("T2T1")
    hw_revision = 0

    defines += ["DISPLAY_RGB565"]
    features_available.append("display_rgb565")
    defines += ["USE_RGB_COLORS=1"]

    mcu = "STM32F427xx"

    stm32f4_common_files(env, defines, sources, paths)

    env.get("ENV")[
        "CPU_ASFLAGS"
    ] = "-mthumb -mcpu=cortex-m4 -mfloat-abi=hard -mfpu=fpv4-sp-d16"
    env.get("ENV")[
        "CPU_CCFLAGS"
    ] = "-mthumb -mcpu=cortex-m4 -mfloat-abi=hard -mfpu=fpv4-sp-d16 -mtune=cortex-m4 "
    env.get("ENV")["RUST_TARGET"] = "thumbv7em-none-eabihf"

    defines += [mcu]
    defines += [f'TREZOR_BOARD=\\"{board}\\"']
    defines += [f"HW_MODEL={hw_model}"]
    defines += [f"HW_REVISION={hw_revision}"]

    sources += ["embed/trezorhal/stm32f4/xdisplay/st-7789/display_nofb.c"]
    sources += ["embed/trezorhal/stm32f4/xdisplay/st-7789/display_driver.c"]
    sources += ["embed/trezorhal/stm32f4/xdisplay/st-7789/display_io.c"]
    sources += ["embed/trezorhal/stm32f4/xdisplay/st-7789/display_panel.c"]
    sources += ["embed/trezorhal/stm32f4/xdisplay/st-7789/panels/tf15411a.c"]
    sources += ["embed/trezorhal/stm32f4/xdisplay/st-7789/panels/154a.c"]
    sources += ["embed/trezorhal/stm32f4/xdisplay/st-7789/panels/lx154a2411.c"]
    sources += ["embed/trezorhal/stm32f4/xdisplay/st-7789/panels/lx154a2422.c"]

    sources += ["embed/trezorhal/stm32f4/backlight_pwm.c"]

    features_available.append("backlight")
    defines += ["USE_BACKLIGHT=1"]

    if "input" in features_wanted:
        sources += ["embed/trezorhal/stm32f4/i2c_bus.c"]
        sources += ["embed/trezorhal/stm32f4/touch/ft6x36.c"]
        features_available.append("touch")
        defines += ["USE_TOUCH=1"]
        defines += ["USE_I2C=1"]

    if "sd_card" in features_wanted:
        sources += ["embed/trezorhal/stm32f4/sdcard.c"]
        sources += ["embed/extmod/modtrezorio/ff.c"]
        sources += ["embed/extmod/modtrezorio/ffunicode.c"]
        sources += [
            "vendor/micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_dma.c"
        ]
        features_available.append("sd_card")
        defines += ["USE_SD_CARD=1"]

    if "sbu" in features_wanted:
        sources += ["embed/trezorhal/stm32f4/sbu.c"]
        features_available.append("sbu")
        defines += ["USE_SBU=1"]

    if "usb" in features_wanted:
        sources += [
            "embed/trezorhal/stm32f4/usb/usb_class_hid.c",
            "embed/trezorhal/stm32f4/usb/usb_class_vcp.c",
            "embed/trezorhal/stm32f4/usb/usb_class_webusb.c",
            "embed/trezorhal/stm32f4/usb/usb.c",
            "embed/trezorhal/stm32f4/usb/usbd_conf.c",
            "embed/trezorhal/stm32f4/usb/usbd_core.c",
            "embed/trezorhal/stm32f4/usb/usbd_ctlreq.c",
            "embed/trezorhal/stm32f4/usb/usbd_ioreq.c",
            "vendor/micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_ll_usb.c",
        ]
        features_available.append("usb")

    if "dma2d" in features_wanted:
        defines += ["USE_DMA2D"]
        sources += ["embed/trezorhal/stm32u5/dma2d_bitblt.c"]
        sources += [
            "vendor/micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_dma2d.c"
        ]
        features_available.append("dma2d")

    defines += ["USE_PVD=1"]

    return features_available
