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
    memory_layout = "memory.ld"

    features_available += stm32u5_common_files(
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
        ("HSE_VALUE", "16000000"),
        ("USE_HSE", "1"),
        ("USE_BOOTARGS_RSOD", "1"),
        ("LOCKABLE_BOOTLOADER", "1"),
        ("USE_SECMON_VERIFICATION", "1"),
    ]

    if "boot_ucb" in features_wanted:
        sources += ["embed/util/image/boot_header.c"]
        sources += ["embed/util/image/boot_ucb.c"]
        defines += [("USE_BOOT_UCB", "1")]
        features_available.append("boot_ucb")

    if "display" in features_wanted:
        sources += [
            "embed/io/display/ltdc_dsi/display_driver.c",
            "embed/io/display/ltdc_dsi/panels/stm32u5a9j-dk/stm32u5a9j-dk.c",
            "embed/io/display/ltdc_dsi/display_fb.c",
            "embed/io/display/ltdc_dsi/display_fb_rgb888.c",
            # "embed/io/display/ltdc_dsi/display_gfxmmu.c",
            "embed/io/display/fb_queue/fb_queue.c",
        ]
        paths += ["embed/io/display/inc"]
        defines += [("USE_DISPLAY", "1")]

        features_available.append("backlight")
        defines += [("USE_BACKLIGHT", "1")]
        sources += ["embed/io/backlight/stm32/backlight_pin.c"]
        paths += ["embed/io/backlight/inc"]

    if "input" in features_wanted:
        sources += ["embed/sys/i2c_bus/stm32u5/i2c_bus.c"]
        sources += ["embed/io/touch/sitronix/touch.c"]
        sources += ["embed/io/touch/sitronix/sitronix.c"]
        sources += ["embed/io/touch/touch_poll.c"]
        paths += ["embed/sys/i2c_bus/inc"]
        paths += ["embed/io/touch/inc"]
        features_available.append("touch")
        defines += [
            ("USE_TOUCH", "1"),
            ("USE_I2C", "1"),
        ]

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
    ]

    ENV["LINKER_SCRIPT"] = linker_script
    ENV["MEMORY_LAYOUT"] = memory_layout

    return features_available
