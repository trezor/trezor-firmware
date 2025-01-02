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
    board = "T3W1/boards/trezor_t3w1_revA.h"
    hw_model = get_hw_model_as_number("T3W1")
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
        ("HSE_VALUE", "32000000"),
        ("USE_HSE", "1"),
        ("FIXED_HW_DEINIT", "1"),
    ]

    sources += [
        "embed/io/display/ltdc_dsi/display_driver.c",
        "embed/io/display/ltdc_dsi/panels/lx200d2406a/lx200d2406a.c",
        "embed/io/display/ltdc_dsi/display_fb.c",
        "embed/io/display/ltdc_dsi/display_fb_rgb565.c",
        "embed/io/display/fb_queue/fb_queue.c",
        "embed/io/display/backlight/stm32/backlight_pwm.c",
    ]

    paths += ["embed/io/display/inc"]
    features_available.append("backlight")
    defines += [("USE_BACKLIGHT", "1")]

    if "input" in features_wanted:
        sources += ["embed/io/touch/ft6x36/ft6x36.c"]
        sources += ["embed/io/touch/ft6x36/panels/lhs200kb-if21.c"]
        paths += ["embed/io/touch/inc"]
        features_available.append("touch")
        sources += ["embed/io/button/stm32/button.c"]
        paths += ["embed/io/button/inc"]
        features_available.append("button")
        defines += [
            ("USE_TOUCH", "1"),
            ("USE_BUTTON", "1"),
        ]

    sources += ["embed/io/i2c_bus/stm32u5/i2c_bus.c"]
    paths += ["embed/io/i2c_bus/inc"]
    defines += [("USE_I2C", "1")]

    if "haptic" in features_wanted:
        sources += [
            "embed/io/haptic/drv2625/drv2625.c",
        ]
        paths += ["embed/io/haptic/inc"]
        features_available.append("haptic")
        defines += ["USE_HAPTIC=1"]

    # if "ble" in features_wanted:
    #     sources += ["embed/trezorhal/stm32f4/ble/ble_hal.c"]
    #     sources += ["embed/trezorhal/stm32f4/ble/dfu.c"]
    #     sources += ["embed/trezorhal/stm32f4/ble/fwu.c"]
    #     sources += ["embed/trezorhal/stm32f4/ble/ble.c"]
    #     sources += ["embed/trezorhal/stm32f4/ble/messages.c"]
    #     sources += [
    #         "vendor/micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_uart.c"
    #     ]
    #     features_available.append("ble")
    #     defines += [("USE_BLE", "1")]

    if "ble" in features_wanted:
        sources += [
            "vendor/micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_dma.c"
        ]

    if "optiga" in features_wanted:
        sources += ["embed/sec/optiga/stm32/optiga_hal.c"]
        sources += ["embed/sec/optiga/optiga.c"]
        sources += ["embed/sec/optiga/optiga_commands.c"]
        sources += ["embed/sec/optiga/optiga_transport.c"]
        sources += ["vendor/trezor-crypto/hash_to_curve.c"]
        paths += ["embed/sec/optiga/inc"]
        features_available.append("optiga")
        defines += [("USE_OPTIGA", "1")]

    if "sbu" in features_wanted:
        sources += ["embed/io/sbu/stm32/sbu.c"]
        paths += ["embed/io/sbu/inc"]
        features_available.append("sbu")
        defines += [("USE_SBU", "1")]

    if "rgb_led" in features_wanted:
        sources += ["embed/io/rgb_led/stm32/rgb_led.c"]
        paths += ["embed/io/rgb_led/inc"]
        features_available.append("rgb_led")
        defines += [("USE_RGB_LED", "1")]

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

    defines += [
        "USE_DMA2D",
        ("USE_RGB_COLORS", "1"),
    ]
    sources += ["embed/gfx/bitblt/stm32/dma2d_bitblt.c"]

    features_available.append("dma2d")

    defines += ["FRAMEBUFFER"]
    defines += ["DISPLAY_RGB565"]
    features_available.append("framebuffer")
    features_available.append("display_rgb565")

    defines += [
        ("USE_HASH_PROCESSOR", "1"),
        ("USE_STORAGE_HWKEY", "1"),
        ("USE_TAMPER", "1"),
        ("USE_FLASH_BURST", "1"),
        ("USE_OEM_KEYS_CHECK", "1"),
        ("USE_RESET_TO_BOOT", "1"),
    ]

    sources += [
        "embed/sys/powerctl/npm1300/npm1300.c",
        "embed/sys/powerctl/stwlc38/stwlc38.c",
        "embed/sys/powerctl/stwlc38/stwlc38_patching.c",
        "embed/sys/powerctl/stm32u5/powerctl.c",
        "embed/sys/powerctl/stm32u5/powerctl_suspend.c",
        "embed/sys/powerctl/wakeup_flags.c",
    ]
    paths += ["embed/sys/powerctl/inc"]
    defines += [("USE_POWERCTL", "1")]

    env.get("ENV")["LINKER_SCRIPT"] = linker_script

    defs = env.get("CPPDEFINES_IMPLICIT")
    defs += ["__ARM_FEATURE_CMSE=3"]

    return features_available
