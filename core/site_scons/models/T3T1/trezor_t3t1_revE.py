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
    hw_model = get_hw_model_as_number("T3T1")
    hw_revision = 0

    features_available.append("framebuffer")
    features_available.append("display_rgb565")
    defines += [
        ("DISPLAY_RGB565", "1"),
        ("FRAMEBUFFER", "1"),
        ("USE_RGB_COLORS", "1"),
        ("DISPLAY_RESX", "240"),
        ("DISPLAY_RESY", "240"),
    ]

    mcu = "STM32U585xx"
    linker_script = """embed/sys/linker/stm32u58/{target}.ld"""

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
    ]

    sources += ["embed/io/display/st-7789/display_fb.c"]
    sources += ["embed/io/display/st-7789/display_driver.c"]
    sources += ["embed/io/display/st-7789/display_io.c"]
    sources += ["embed/io/display/st-7789/display_panel.c"]
    sources += ["embed/io/display/st-7789/panels/lx154a2482.c"]
    sources += ["embed/io/display/fb_queue/fb_queue.c"]
    paths += ["embed/io/display/inc"]

    features_available.append("backlight")
    defines += [("USE_BACKLIGHT", "1")]
    sources += ["embed/io/backlight/stm32/tps61043.c"]
    paths += ["embed/io/backlight/inc"]

    env_constraints = env.get("CONSTRAINTS")
    if not (env_constraints and "limited_util_s" in env_constraints):
        sources += ["embed/io/display/bg_copy/stm32u5/bg_copy.c"]

    if "input" in features_wanted:
        sources += ["embed/io/i2c_bus/stm32u5/i2c_bus.c"]
        sources += ["embed/io/touch/ft6x36/ft6x36.c"]
        sources += ["embed/io/touch/touch_fsm.c"]
        sources += ["embed/io/touch/ft6x36/panels/lx154a2422cpt23.c"]
        paths += ["embed/io/i2c_bus/inc"]
        paths += ["embed/io/touch/inc"]
        features_available.append("touch")
        defines += [("USE_TOUCH", "1")]
        defines += [("USE_I2C", "1")]

    if "haptic" in features_wanted:
        sources += [
            "embed/io/haptic/drv2625/drv2625.c",
        ]
        paths += ["embed/io/haptic/inc"]
        features_available.append("haptic")
        defines += [("USE_HAPTIC", "1")]

    if "sd_card" in features_wanted:
        sources += ["embed/io/sdcard/stm32u5/sdcard.c"]
        sources += ["embed/upymod/modtrezorio/ff.c"]
        sources += ["embed/upymod/modtrezorio/ffunicode.c"]
        sources += ["vendor/stm32u5xx_hal_driver/Src/stm32u5xx_hal_sd.c"]
        sources += ["vendor/stm32u5xx_hal_driver/Src/stm32u5xx_ll_sdmmc.c"]
        paths += ["embed/io/sdcard/inc"]
        features_available.append("sd_card")
        defines += [("USE_SD_CARD", "1")]

    if "sbu" in features_wanted:
        sources += ["embed/io/sbu/stm32/sbu.c"]
        paths += ["embed/io/sbu/inc"]
        features_available.append("sbu")
        defines += [("USE_SBU", "1")]

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

    if "dma2d" in features_wanted:
        defines += [("USE_DMA2D", "1")]
        sources += ["embed/gfx/bitblt/stm32/dma2d_bitblt.c"]
        features_available.append("dma2d")

    if "optiga" in features_wanted:
        sources += ["embed/sec/optiga/stm32/optiga_hal.c"]
        sources += ["embed/sec/optiga/optiga.c"]
        sources += ["embed/sec/optiga/optiga_commands.c"]
        sources += ["embed/sec/optiga/optiga_config.c"]
        sources += ["embed/sec/optiga/optiga_transport.c"]
        sources += ["vendor/trezor-crypto/hash_to_curve.c"]
        paths += ["embed/sec/optiga/inc"]
        features_available.append("optiga")
        defines += [("USE_OPTIGA", "1")]

    if "hw_revision" in features_wanted:
        defines += [("USE_HW_REVISION", "1")]
        paths += ["embed/util/hw_revision/inc"]
        sources += ["embed/util/hw_revision/stm32/hw_revision.c"]

    defines += [
        ("USE_HASH_PROCESSOR", "1"),
        ("USE_STORAGE_HWKEY", "1"),
        ("USE_TAMPER", "1"),
        ("USE_FLASH_BURST", "1"),
        ("USE_OEM_KEYS_CHECK", "1"),
        ("USE_PVD", "1"),
    ]

    env.get("ENV")["TREZOR_BOARD"] = board
    env.get("ENV")["MCU_TYPE"] = mcu
    env.get("ENV")["LINKER_SCRIPT"] = linker_script

    defs = env.get("CPPDEFINES_IMPLICIT")
    defs += ["__ARM_FEATURE_CMSE=3"]

    return features_available
