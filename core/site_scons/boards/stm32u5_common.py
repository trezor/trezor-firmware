from __future__ import annotations


def stm32u5_common_files(env, defines, sources, paths):
    defines += [
        ("STM32_HAL_H", '"<stm32u5xx.h>"'),
    ]

    paths += [
        "embed/trezorhal/stm32u5",
        "vendor/micropython/lib/stm32lib/STM32U5xx_HAL_Driver/Inc",
        "vendor/micropython/lib/stm32lib/CMSIS/STM32U5xx/Include",
    ]

    sources += [
        "vendor/micropython/lib/stm32lib/STM32U5xx_HAL_Driver/Src/stm32u5xx_hal.c",
        "vendor/micropython/lib/stm32lib/STM32U5xx_HAL_Driver/Src/stm32u5xx_hal_cortex.c",
        "vendor/micropython/lib/stm32lib/STM32U5xx_HAL_Driver/Src/stm32u5xx_hal_dma.c",
        "vendor/micropython/lib/stm32lib/STM32U5xx_HAL_Driver/Src/stm32u5xx_hal_dma2d.c",
        "vendor/micropython/lib/stm32lib/STM32U5xx_HAL_Driver/Src/stm32u5xx_hal_dsi.c",
        "vendor/micropython/lib/stm32lib/STM32U5xx_HAL_Driver/Src/stm32u5xx_hal_flash.c",
        "vendor/micropython/lib/stm32lib/STM32U5xx_HAL_Driver/Src/stm32u5xx_hal_flash_ex.c",
        "vendor/micropython/lib/stm32lib/STM32U5xx_HAL_Driver/Src/stm32u5xx_hal_gfxmmu.c",
        "vendor/micropython/lib/stm32lib/STM32U5xx_HAL_Driver/Src/stm32u5xx_hal_gpio.c",
        "vendor/micropython/lib/stm32lib/STM32U5xx_HAL_Driver/Src/stm32u5xx_hal_i2c.c",
        "vendor/micropython/lib/stm32lib/STM32U5xx_HAL_Driver/Src/stm32u5xx_hal_i2c_ex.c",
        "vendor/micropython/lib/stm32lib/STM32U5xx_HAL_Driver/Src/stm32u5xx_hal_icache.c",
        "vendor/micropython/lib/stm32lib/STM32U5xx_HAL_Driver/Src/stm32u5xx_hal_ltdc.c",
        "vendor/micropython/lib/stm32lib/STM32U5xx_HAL_Driver/Src/stm32u5xx_hal_ltdc_ex.c",
        "vendor/micropython/lib/stm32lib/STM32U5xx_HAL_Driver/Src/stm32u5xx_hal_pcd.c",
        "vendor/micropython/lib/stm32lib/STM32U5xx_HAL_Driver/Src/stm32u5xx_hal_pcd_ex.c",
        "vendor/micropython/lib/stm32lib/STM32U5xx_HAL_Driver/Src/stm32u5xx_hal_pwr.c",
        "vendor/micropython/lib/stm32lib/STM32U5xx_HAL_Driver/Src/stm32u5xx_hal_pwr_ex.c",
        "vendor/micropython/lib/stm32lib/STM32U5xx_HAL_Driver/Src/stm32u5xx_hal_rcc.c",
        "vendor/micropython/lib/stm32lib/STM32U5xx_HAL_Driver/Src/stm32u5xx_hal_rcc_ex.c",
        "vendor/micropython/lib/stm32lib/STM32U5xx_HAL_Driver/Src/stm32u5xx_hal_sd.c",
        "vendor/micropython/lib/stm32lib/STM32U5xx_HAL_Driver/Src/stm32u5xx_hal_spi.c",
        "vendor/micropython/lib/stm32lib/STM32U5xx_HAL_Driver/Src/stm32u5xx_hal_sram.c",
        "vendor/micropython/lib/stm32lib/STM32U5xx_HAL_Driver/Src/stm32u5xx_hal_tim.c",
        "vendor/micropython/lib/stm32lib/STM32U5xx_HAL_Driver/Src/stm32u5xx_hal_tim_ex.c",
        "vendor/micropython/lib/stm32lib/STM32U5xx_HAL_Driver/Src/stm32u5xx_ll_fmc.c",
        "vendor/micropython/lib/stm32lib/STM32U5xx_HAL_Driver/Src/stm32u5xx_ll_sdmmc.c",
    ]

    sources += [
        "embed/trezorhal/stm32u5/board_capabilities.c",
        "embed/trezorhal/stm32u5/common.c",
        "embed/trezorhal/stm32u5/flash.c",
        "embed/trezorhal/stm32u5/lowlevel.c",
        "embed/trezorhal/stm32u5/mpu.c",
        "embed/trezorhal/stm32u5/platform.c",
        "embed/trezorhal/stm32u5/systick.c",
        "embed/trezorhal/stm32u5/random_delays.c",
        "embed/trezorhal/stm32u5/rng.c",
        "embed/trezorhal/stm32u5/vectortable.s",
    ]

    # boardloader needs separate assembler for some function unencumbered by various FW+bootloader hacks
    # this helps to prevent making a bug in boardloader which may be hard to fix since it's locked with write-protect
    env_constraints = env.get("CONSTRAINTS")
    if env_constraints and "limited_util_s" in env_constraints:
        sources += [
            "embed/trezorhal/stm32u5/limited_util.s",
        ]
    else:
        sources += [
            "embed/trezorhal/stm32u5/util.s",
        ]

    env.get("ENV")["RUST_INCLUDES"] = (
        "-I../trezorhal/stm32u5;"
        "-I../../vendor/micropython/lib/stm32lib/STM32U5xx_HAL_Driver/Inc;"
        "-I../../vendor/micropython/lib/stm32lib/CMSIS/STM32U5xx/Include;"
        "-DSTM32_HAL_H=<stm32u5xx.h>"
    )

    env.get("ENV")["SUFFIX"] = "stm32u5"
