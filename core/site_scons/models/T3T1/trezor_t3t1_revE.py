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
    board = "T3T1/boards/trezor_t3t1_revE.h"
    display = "st7789v.c"
    hw_model = get_hw_model_as_number("T3T1")
    hw_revision = 0
    features_available.append("disp_i8080_8bit_dw")
    features_available.append("framebuffer")
    defines += ["FRAMEBUFFER"]

    if "new_rendering" in features_wanted:
        features_available.append("xframebuffer")
        features_available.append("display_rgb565")
        defines += ["DISPLAY_RGB565"]
        defines += ["XFRAMEBUFFER"]

    mcu = "STM32U585xx"
    linker_script = "stm32u58"

    stm32u5_common_files(env, defines, sources, paths)

    env.get("ENV")[
        "CPU_ASFLAGS"
    ] = "-mthumb -mcpu=cortex-m33 -mfloat-abi=hard -mfpu=fpv5-sp-d16 "
    env.get("ENV")[
        "CPU_CCFLAGS"
    ] = "-mthumb -mcpu=cortex-m33 -mfloat-abi=hard -mfpu=fpv5-sp-d16 -mtune=cortex-m33 -mcmse "
    env.get("ENV")["RUST_TARGET"] = "thumbv8m.main-none-eabihf"

    defines += [mcu]
    defines += [f'TREZOR_BOARD=\\"{board}\\"']
    defines += [f"HW_MODEL={hw_model}"]
    defines += [f"HW_REVISION={hw_revision}"]
    sources += [
        "embed/models/T3T1/model_T3T1_layout.c",
    ]

    if "new_rendering" in features_wanted:
        sources += ["embed/trezorhal/xdisplay_legacy.c"]
        sources += ["embed/trezorhal/stm32u5/xdisplay/st-7789/display_fb.c"]
        sources += ["embed/trezorhal/stm32u5/xdisplay/st-7789/display_driver.c"]
        sources += ["embed/trezorhal/stm32u5/xdisplay/st-7789/display_io.c"]
        sources += ["embed/trezorhal/stm32u5/xdisplay/st-7789/display_panel.c"]
        sources += [
            "embed/trezorhal/stm32u5/xdisplay/st-7789/panels/lx154a2482.c",
        ]
    else:
        sources += [f"embed/trezorhal/stm32u5/displays/{display}"]
        sources += [
            "embed/trezorhal/stm32u5/displays/panels/lx154a2482.c",
        ]

    sources += ["embed/trezorhal/stm32u5/backlight_pwm.c"]

    env_constraints = env.get("CONSTRAINTS")
    if not (env_constraints and "limited_util_s" in env_constraints):
        sources += ["embed/trezorhal/stm32u5/bg_copy.c"]

    features_available.append("backlight")

    if "input" in features_wanted:
        sources += ["embed/trezorhal/stm32u5/i2c.c"]
        sources += ["embed/trezorhal/stm32u5/touch/ft6x36.c"]
        sources += ["embed/trezorhal/stm32u5/touch/panels/lx154a2422cpt23.c"]
        features_available.append("touch")

    if "haptic" in features_wanted:
        sources += [
            "embed/trezorhal/stm32u5/haptic/drv2625/drv2625.c",
        ]
        sources += [
            "vendor/stm32u5xx_hal_driver/Src/stm32u5xx_hal_tim.c",
            "vendor/stm32u5xx_hal_driver/Src/stm32u5xx_hal_tim_ex.c",
        ]
        features_available.append("haptic")

    if "sd_card" in features_wanted:
        sources += ["embed/trezorhal/stm32u5/sdcard.c"]
        sources += ["embed/extmod/modtrezorio/ff.c"]
        sources += ["embed/extmod/modtrezorio/ffunicode.c"]
        features_available.append("sd_card")
        sources += ["vendor/stm32u5xx_hal_driver/Src/stm32u5xx_hal_sd.c"]
        sources += ["vendor/stm32u5xx_hal_driver/Src/stm32u5xx_ll_sdmmc.c"]

    if "sbu" in features_wanted:
        sources += ["embed/trezorhal/stm32u5/sbu.c"]
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

    if "dma2d" in features_wanted:
        defines += ["USE_DMA2D"]
        if "new_rendering" in features_wanted:
            sources += ["embed/trezorhal/stm32u5/dma2d_bitblt.c"]
        else:
            sources += ["embed/trezorhal/stm32u5/dma2d.c"]
        features_available.append("dma2d")

    if "optiga" in features_wanted:
        defines += ["USE_OPTIGA=1"]
        sources += ["embed/trezorhal/stm32u5/optiga_hal.c"]
        sources += ["embed/trezorhal/optiga/optiga.c"]
        sources += ["embed/trezorhal/optiga/optiga_commands.c"]
        sources += ["embed/trezorhal/optiga/optiga_transport.c"]
        sources += ["vendor/trezor-crypto/hash_to_curve.c"]
        features_available.append("optiga")

    env.get("ENV")["TREZOR_BOARD"] = board
    env.get("ENV")["MCU_TYPE"] = mcu
    env.get("ENV")["LINKER_SCRIPT"] = linker_script

    defs = env.get("CPPDEFINES_IMPLICIT")
    defs += ["__ARM_FEATURE_CMSE=3"]

    return features_available
