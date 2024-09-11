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
    board = "T3T1/boards/t3t1-unix.h"
    hw_model = get_hw_model_as_number("T3T1")
    hw_revision = 0
    mcu = "STM32FU585xx"

    if "new_rendering" in features_wanted:
        defines += ["XFRAMEBUFFER", "DISPLAY_RGB565"]
        features_available.append("xframebuffer")
        features_available.append("display_rgb565")

    defines += [mcu]
    defines += [f'TREZOR_BOARD=\\"{board}\\"']
    defines += [f"HW_MODEL={hw_model}"]
    defines += [f"HW_REVISION={hw_revision}"]
    defines += [f"MCU_TYPE={mcu}"]
    # todo change to blockwise flash when implemented in unix
    defines += ["FLASH_BIT_ACCESS=1"]
    defines += ["FLASH_BLOCK_WORDS=1"]

    if "dma2d" in features_wanted:
        features_available.append("dma2d")
        if "new_rendering" in features_wanted:
            sources += [
                "embed/trezorhal/unix/dma2d_bitblt.c",
            ]
        else:
            sources += ["embed/lib/dma2d_emul.c"]
        defines += ["USE_DMA2D"]

    if "sd_card" in features_wanted:
        features_available.append("sd_card")
        sources += [
            "embed/trezorhal/unix/sdcard.c",
            "embed/extmod/modtrezorio/ff.c",
            "embed/extmod/modtrezorio/ffunicode.c",
        ]

    if "sbu" in features_wanted:
        sources += ["embed/trezorhal/unix/sbu.c"]

    if "optiga_hal" in features_wanted:
        sources += ["embed/trezorhal/unix/optiga_hal.c"]

    if "optiga" in features_wanted:
        sources += ["embed/trezorhal/unix/optiga.c"]
        features_available.append("optiga")

    if "tropic" in features_wanted:
        sources += [
            "vendor/libtropic/src/libtropic.c",
            "vendor/libtropic/src/lt_crc16.c",
            "vendor/libtropic/src/lt_hkdf.c",
            "vendor/libtropic/src/lt_l1.c",
            "vendor/libtropic/src/lt_l1_port_wrap.c",
            "vendor/libtropic/src/lt_l2.c",
            "vendor/libtropic/src/lt_l2_frame_check.c",
            "vendor/libtropic/src/lt_l3.c",
            "vendor/libtropic/src/lt_random.c",
            "vendor/libtropic/hal/port/unix/lt_port_unix.c",
            "vendor/libtropic/hal/crypto/trezor_crypto/lt_crypto_trezor_aesgcm.c",
            "vendor/libtropic/hal/crypto/trezor_crypto/lt_crypto_trezor_ed25519.c",
            "vendor/libtropic/hal/crypto/trezor_crypto/lt_crypto_trezor_sha256.c",
            "vendor/libtropic/hal/crypto/trezor_crypto/lt_crypto_trezor_x25519.c",
        ]
        defines += ["USE_TREZOR_CRYPTO"]
        features_available.append("tropic")

    if "input" in features_wanted:
        sources += ["embed/trezorhal/unix/touch.c"]
        features_available.append("touch")

    features_available.append("backlight")

    sources += ["embed/models/T3T1/model_T3T1_layout.c"]

    return features_available
