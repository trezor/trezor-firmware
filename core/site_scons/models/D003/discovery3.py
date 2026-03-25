from __future__ import annotations

from .. import get_hw_model_as_number
from ..stm32u3_common import stm32u3_common_files


def configure(
    env: dict,
    features_wanted: list[str],
    defines: list[str | tuple[str, str]],
    sources: list[str],
    paths: list[str],
) -> list[str]:
    features_available: list[str] = []
    board = "D003/boards/nucleo.h"
    hw_model = get_hw_model_as_number("D003")
    hw_revision = 0

    mcu = "STM32U385xx"
    linker_script = """embed/sys/linker/stm32u38/{target}.ld"""
    memory_layout = "memory.ld"

    features_available += stm32u3_common_files(
        env, features_wanted, defines, sources, paths
    )

    ENV = env.get("ENV")
    assert ENV

    ENV["CPU_ASFLAGS"] = "-mthumb -mcpu=cortex-m33 -mfloat-abi=hard -mfpu=fpv5-sp-d16 "
    ENV["CPU_CCFLAGS"] = (
        "-mthumb -mcpu=cortex-m33 -mfloat-abi=hard -mfpu=fpv5-sp-d16 -mtune=cortex-m33 "
    )
    ENV["RUST_TARGET"] = "thumbv8m.main-none-eabihf"

    if "secure_domain" in features_wanted:
        ENV["CPU_CCFLAGS"] += "-mcmse "

    if "secmon_layout" in features_wanted:
        defines += [("USE_SECMON_LAYOUT", "1")]
        memory_layout = "memory_secmon.ld"
        features_available.append("secmon_layout")

    defines += [
        mcu,
        ("TREZOR_BOARD", f'"{board}"'),
        ("HW_MODEL", str(hw_model)),
        ("HW_REVISION", str(hw_revision)),
        ("USE_BOOTARGS_RSOD", "1"),
        ("LOCKABLE_BOOTLOADER", "1"),
        ("USE_SECMON_VERIFICATION", "1"),
    ]

    paths += ["embed/sec/secret/inc"]
    sources += ["embed/sec/secret/stm32u5/secret.c"]
    defines += [("USE_SECRET", "1")]

    paths += ["embed/sec/secret_keys/inc"]
    sources += ["embed/sec/secret_keys/stm32u5/secret_keys.c"]
    sources += ["embed/sec/secret_keys/secret_keys_common.c"]
    defines += [("USE_SECRET_KEYS", "1")]

    if "boot_ucb" in features_wanted:
        sources += ["embed/sec/image/boot_header.c"]
        sources += ["embed/sec/image/boot_ucb.c"]
        defines += [("USE_BOOT_UCB", "1")]
        features_available.append("boot_ucb")

    if "display" in features_wanted:
        sources += [
            "embed/io/display/dummy/display_driver.c",
        ]
        paths += ["embed/io/display/inc"]
        defines += [("USE_DISPLAY", "1")]

    if "input" in features_wanted:
        sources += ["embed/io/button/stm32/button.c"]
        sources += ["embed/io/button/button_poll.c"]
        paths += ["embed/io/button/inc"]
        features_available.append("button")
        defines += [("USE_BUTTON", "1")]

    if "nfc" in features_wanted:
        sources += ["embed/io/nfc/st25/nfc.c"]
        sources += ["embed/io/nfc/st25/ndef.c"]
        sources += ["embed/io/nfc/st25/card_emulation.c"]
        sources += ["embed/io/nfc/st25/rfal004/source/st25r200/rfal_rfst25r200.c"]
        sources += ["embed/io/nfc/st25/rfal004/source/rfal_analogConfig.c"]
        sources += ["embed/io/nfc/st25/rfal004/source/rfal_nfc.c"]
        sources += ["embed/io/nfc/st25/rfal004/source/rfal_nfca.c"]
        sources += ["embed/io/nfc/st25/rfal004/source/rfal_nfcb.c"]
        sources += ["embed/io/nfc/st25/rfal004/source/rfal_nfcf.c"]
        sources += ["embed/io/nfc/st25/rfal004/source/rfal_nfcv.c"]
        sources += ["embed/io/nfc/st25/rfal004/source/rfal_isoDep.c"]
        sources += ["embed/io/nfc/st25/rfal004/source/rfal_nfcDep.c"]
        sources += ["embed/io/nfc/st25/rfal004/source/rfal_st25tb.c"]
        sources += ["embed/io/nfc/st25/rfal004/source/rfal_t1t.c"]
        sources += ["embed/io/nfc/st25/rfal004/source/rfal_t2t.c"]
        sources += ["embed/io/nfc/st25/rfal004/source/rfal_iso15693_2.c"]
        sources += ["embed/io/nfc/st25/rfal004/source/rfal_crc.c"]
        sources += ["embed/io/nfc/st25/rfal004/source/st25r200/st25r200.c"]
        sources += ["embed/io/nfc/st25/rfal004/source/st25r200/st25r200_com.c"]
        sources += ["embed/io/nfc/st25/rfal004/source/st25r200/st25r200_irq.c"]
        paths += ["embed/io/nfc/inc/"]
        paths += ["embed/io/nfc/st25/"]
        paths += ["embed/io/nfc/st25/rfal004/source"]
        paths += ["embed/io/nfc/st25/rfal004/source/st25r200"]
        paths += ["embed/io/nfc/st25/rfal004/include/"]
        defines += [("USE_NFC", "1")]

    defines += [
        "DISPLAY_RGB565",
        ("USE_RGB_COLORS", "1"),
        ("DISPLAY_RESX", "240"),
        ("DISPLAY_RESY", "240"),
    ]
    features_available.append("display_rgb565")

    defines += [
        "USE_HASH_PROCESSOR=1",
        "USE_STORAGE_HWKEY=1",
        "USE_OEM_KEYS_CHECK=1",
    ]

    ENV["LINKER_SCRIPT"] = linker_script
    ENV["MEMORY_LAYOUT"] = memory_layout

    return features_available
