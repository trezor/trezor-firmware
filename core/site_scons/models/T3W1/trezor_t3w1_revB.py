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
    board = "T3W1/boards/trezor_t3w1_revB.h"
    hw_model = get_hw_model_as_number("T3W1")
    hw_revision = 1

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
        ("USE_LSE", "1"),
        ("FIXED_HW_DEINIT", "1"),
        ("TERMINAL_FONT_SCALE", "2"),
        ("TERMINAL_X_PADDING", "4"),
        ("TERMINAL_Y_PADDING", "12"),
    ]

    sources += [
        "embed/io/display/ltdc_dsi/display_driver.c",
        "embed/io/display/ltdc_dsi/panels/lx250a2401a/lx250a2401a.c",
        "embed/io/display/ltdc_dsi/display_fb.c",
        "embed/io/display/ltdc_dsi/display_fb_rgb888.c",
        "embed/io/display/ltdc_dsi/display_gfxmmu.c",
        "embed/io/display/fb_queue/fb_queue.c",
    ]
    paths += ["embed/io/display/inc"]

    features_available.append("backlight")
    defines += [("USE_BACKLIGHT", "1")]
    sources += ["embed/io/backlight/stm32u5/tps61062.c"]
    paths += ["embed/io/backlight/inc"]

    if "input" in features_wanted:
        sources += ["embed/io/touch/ft6x36/ft6x36.c"]
        sources += ["embed/io/touch/ft6x36/panels/lx250a2410a.c"]
        sources += ["embed/io/touch/touch_fsm.c"]
        paths += ["embed/io/touch/inc"]
        features_available.append("touch")
        sources += ["embed/io/button/stm32/button.c"]
        sources += ["embed/io/button/button_fsm.c"]
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

    if "ble" in features_wanted:
        sources += ["embed/io/ble/stm32/ble.c"]
        paths += ["embed/io/ble/inc"]
        features_available.append("ble")
        defines += [("USE_BLE", "1")]
        sources += ["embed/io/nrf/stm32u5/nrf.c"]
        sources += ["embed/io/nrf/stm32u5/nrf_test.c"]
        sources += ["embed/io/nrf/crc8.c"]
        paths += ["embed/io/nrf/inc"]
        sources += [
            "vendor/stm32u5xx_hal_driver/Src/stm32u5xx_hal_uart.c",
            "vendor/stm32u5xx_hal_driver/Src/stm32u5xx_hal_uart_ex.c",
        ]

    if "nfc" in features_wanted:
        sources += ["embed/io/nfc/st25r3916b/nfc.c"]
        sources += ["embed/io/nfc/st25r3916b/ndef.c"]
        sources += ["embed/io/nfc/st25r3916b/card_emulation.c"]
        sources += ["embed/io/nfc/rfal/source/st25r3916/rfal_rfst25r3916.c"]
        sources += ["embed/io/nfc/rfal/source/rfal_analogConfig.c"]
        sources += ["embed/io/nfc/rfal/source/rfal_nfc.c"]
        sources += ["embed/io/nfc/rfal/source/rfal_nfca.c"]
        sources += ["embed/io/nfc/rfal/source/rfal_nfcb.c"]
        sources += ["embed/io/nfc/rfal/source/rfal_nfcf.c"]
        sources += ["embed/io/nfc/rfal/source/rfal_nfcv.c"]
        sources += ["embed/io/nfc/rfal/source/rfal_isoDep.c"]
        sources += ["embed/io/nfc/rfal/source/rfal_nfcDep.c"]
        sources += ["embed/io/nfc/rfal/source/rfal_st25tb.c"]
        sources += ["embed/io/nfc/rfal/source/rfal_t1t.c"]
        sources += ["embed/io/nfc/rfal/source/rfal_t2t.c"]
        sources += ["embed/io/nfc/rfal/source/rfal_iso15693_2.c"]
        sources += ["embed/io/nfc/rfal/source/rfal_crc.c"]
        sources += ["embed/io/nfc/rfal/source/st25r3916/st25r3916.c"]
        sources += ["embed/io/nfc/rfal/source/st25r3916/st25r3916_com.c"]
        sources += ["embed/io/nfc/rfal/source/st25r3916/st25r3916_led.c"]
        sources += ["embed/io/nfc/rfal/source/st25r3916/st25r3916_irq.c"]
        paths += ["embed/io/nfc/inc/"]
        paths += ["embed/io/nfc/st25r3916b/"]
        paths += ["embed/io/nfc/rfal/source"]
        paths += ["embed/io/nfc/rfal/source/st25r3916"]
        paths += ["embed/io/nfc/rfal/include/"]
        defines += [("USE_NFC", "1")]

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

    if "tropic" in features_wanted:
        sources += ["embed/sec/tropic/tropic.c"]
        sources += ["embed/sec/tropic/stm32/tropic01.c"]
        sources += ["vendor/libtropic/src/libtropic.c"]
        sources += ["vendor/libtropic/src/lt_crc16.c"]
        sources += ["vendor/libtropic/src/lt_l1_port_wrap.c"]
        sources += ["vendor/libtropic/src/lt_l1.c"]
        sources += ["vendor/libtropic/src/lt_l2.c"]
        sources += ["vendor/libtropic/src/lt_l2_frame_check.c"]
        sources += ["vendor/libtropic/src/lt_l3.c"]
        sources += ["vendor/libtropic/src/lt_hkdf.c"]
        sources += ["vendor/libtropic/src/lt_random.c"]
        sources += [
            "vendor/libtropic/hal/crypto/trezor_crypto/lt_crypto_trezor_aesgcm.c"
        ]
        sources += [
            "vendor/libtropic/hal/crypto/trezor_crypto/lt_crypto_trezor_ed25519.c"
        ]
        sources += [
            "vendor/libtropic/hal/crypto/trezor_crypto/lt_crypto_trezor_sha256.c"
        ]
        sources += [
            "vendor/libtropic/hal/crypto/trezor_crypto/lt_crypto_trezor_x25519.c"
        ]
        paths += ["embed/sec/tropic/inc"]
        paths += ["vendor/libtropic/include"]
        paths += ["vendor/libtropic/src"]
        defines += [("USE_TROPIC", "1")]
        defines += [("LT_USE_TREZOR_CRYPTO", "1")]

    if "sbu" in features_wanted:
        sources += ["embed/io/sbu/stm32/sbu.c"]
        paths += ["embed/io/sbu/inc"]
        features_available.append("sbu")
        defines += [("USE_SBU", "1")]

    if "rgb_led" in features_wanted:
        sources += ["embed/io/rgb_led/stm32u5/rgb_led_lp.c"]
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
        defines += [("USE_USB", "1")]

    if "hw_revision" in features_wanted:
        defines += [("USE_HW_REVISION", "1")]
        paths += ["embed/util/hw_revision/inc"]
        sources += ["embed/util/hw_revision/stm32/hw_revision.c"]

    defines += [
        "FRAMEBUFFER",
        "DISPLAY_RGBA8888",
        ("UI_COLOR_32BIT", "1"),
        ("USE_RGB_COLORS", "1"),
        ("DISPLAY_RESX", "380"),
        ("DISPLAY_RESY", "520"),
    ]
    features_available.append("ui_color_32bit")
    features_available.append("framebuffer")
    features_available.append("display_rgba8888")

    defines += [
        "USE_DMA2D",
    ]
    features_available.append("dma2d")
    sources += ["embed/gfx/bitblt/stm32/dma2d_bitblt.c"]

    defines += ["USE_HW_JPEG_DECODER"]
    features_available.append("hw_jpeg_decoder")
    sources += [
        "embed/gfx/jpegdec/stm32u5/jpegdec.c",
    ]

    defines += [
        ("USE_HASH_PROCESSOR", "1"),
        ("USE_STORAGE_HWKEY", "1"),
        ("USE_TAMPER", "1"),
        ("USE_FLASH_BURST", "1"),
        ("USE_OEM_KEYS_CHECK", "1"),
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
