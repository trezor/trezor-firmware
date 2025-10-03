from __future__ import annotations

from .. import get_hw_model_as_number
from ..unix_common import unix_common_files


def configure(
    env: dict,
    features_wanted: list[str],
    defines: list[str | tuple[str, str]],
    sources: list[str],
    paths: list[str],
) -> list[str]:

    features_available: list[str] = []
    board = "T3W1/boards/t3w1-unix.h"
    hw_model = get_hw_model_as_number("T3W1")
    hw_revision = 0
    mcu = "STM32U5G9xx"

    features_available += unix_common_files(
        env, features_wanted, defines, sources, paths
    )

    defines += [
        "FRAMEBUFFER",
        ("USE_RGB_COLORS", "1"),
        "DISPLAY_RGBA8888",
        "UI_COLOR_32BIT",
        ("DISPLAY_RESX", "380"),
        ("DISPLAY_RESY", "520"),
        ("LOCKABLE_BOOTLOADER", "1"),
    ]
    features_available.append("framebuffer")
    features_available.append("display_rgba8888")
    features_available.append("ui_color_32bit")

    defines += [
        mcu,
        ("TREZOR_BOARD", f'"{board}"'),
        ("HW_MODEL", str(hw_model)),
        ("HW_REVISION", str(hw_revision)),
        ("MCU_TYPE", mcu),
        # todo change to blockwise flash when implemented in unix
        ("FLASH_BIT_ACCESS", "1"),
        ("FLASH_BLOCK_WORDS", "1"),
    ]

    if "sbu" in features_wanted:
        sources += ["embed/io/sbu/unix/sbu.c"]
        paths += ["embed/io/sbu/inc"]
        defines += [("USE_SBU", "1")]

    if "rgb_led" in features_wanted:
        sources += ["embed/io/rgb_led/unix/rgb_led.c"]
        paths += ["embed/io/rgb_led/inc"]
        features_available.append("rgb_led")
        defines += [("USE_RGB_LED", "1")]

    if "optiga" in features_wanted:
        sources += ["embed/sec/optiga/unix/optiga_hal.c"]
        sources += ["embed/sec/optiga/unix/optiga.c"]
        paths += ["embed/sec/optiga/inc"]
        features_available.append("optiga")
        defines += [("USE_OPTIGA", "1")]

    if "tropic" in features_wanted:
        sources += [
            "embed/sec/tropic/tropic.c",
            "embed/sec/tropic/unix/tropic01.c",
            "vendor/libtropic/src/libtropic.c",
            "vendor/libtropic/src/lt_asn1_der.c",
            "vendor/libtropic/src/lt_crc16.c",
            "vendor/libtropic/src/lt_hkdf.c",
            "vendor/libtropic/src/lt_l1.c",
            "vendor/libtropic/src/lt_l1_port_wrap.c",
            "vendor/libtropic/src/lt_l2.c",
            "vendor/libtropic/src/lt_l2_frame_check.c",
            "vendor/libtropic/src/lt_l3.c",
            "vendor/libtropic/src/lt_l3_process.c",
            "vendor/libtropic/src/lt_random.c",
            "vendor/libtropic/hal/port/unix/lt_port_unix_tcp.c",
            "vendor/libtropic/hal/crypto/trezor_crypto/lt_crypto_trezor_aesgcm.c",
            "vendor/libtropic/hal/crypto/trezor_crypto/lt_crypto_trezor_ecdsa.c",
            "vendor/libtropic/hal/crypto/trezor_crypto/lt_crypto_trezor_ed25519.c",
            "vendor/libtropic/hal/crypto/trezor_crypto/lt_crypto_trezor_sha256.c",
            "vendor/libtropic/hal/crypto/trezor_crypto/lt_crypto_trezor_x25519.c",
        ]
        paths += ["embed/sec/tropic/inc"]
        paths += ["vendor/libtropic/include"]
        paths += ["vendor/libtropic/src"]
        defines += ["USE_TREZOR_CRYPTO"]
        defines += [("LT_USE_TREZOR_CRYPTO", "1")]
        defines += [("LT_HELPERS", "1")]
        features_available.append("tropic")
        defines += [("USE_TROPIC", "1")]

        paths += ["vendor/libtropic/TROPIC01_fw_update_files/boot_v_1_0_1/fw_v_1_0_0"]
        defines += [("ABAB", "1")]

    if "input" in features_wanted:
        sources += ["embed/io/touch/unix/touch.c"]
        sources += ["embed/io/touch/touch_poll.c"]
        paths += ["embed/io/touch/inc"]
        features_available.append("touch")
        defines += [("USE_TOUCH", "1")]

        sources += ["embed/io/button/unix/button.c"]
        sources += ["embed/io/button/button_poll.c"]
        paths += ["embed/io/button/inc"]
        features_available.append("button")
        defines += [("USE_BUTTON", "1")]

    if "ble" in features_wanted:
        sources += ["embed/io/ble/unix/ble.c"]
        paths += ["embed/io/ble/inc"]
        features_available.append("ble")
        defines += [("USE_BLE", "1")]

    sources += [
        "embed/sys/power_manager/unix/power_manager.c",
    ]
    defines += [("USE_POWER_MANAGER", "1")]
    paths += ["embed/sys/power_manager/inc"]
    features_available.append("power_manager")

    paths += ["embed/sys/suspend/inc"]

    features_available.append("backlight")
    defines += [("USE_BACKLIGHT", "1")]

    sources += ["embed/util/flash/stm32u5/flash_layout.c"]

    defines += ["USE_HW_JPEG_DECODER"]
    features_available.append("hw_jpeg_decoder")
    sources += [
        "embed/gfx/jpegdec/unix/jpegdec.c",
    ]

    if "serial_number" in features_wanted:
        defines += [("USE_SERIAL_NUMBER", "1")]

    return features_available
