from __future__ import annotations


def stm32f4_common_files(env, defines, sources, paths):
    defines += [
        ("STM32_HAL_H", '"<stm32f4xx.h>"'),
        ("FLASH_BLOCK_WORDS", "1"),
        ("FLASH_BIT_ACCESS", "1"),
        ("CONFIDENTIAL", ""),
    ]

    paths += [
        "embed/trezorhal/stm32f4",
        "vendor/micropython/lib/cmsis/inc",
        "vendor/micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Inc",
        "vendor/micropython/lib/stm32lib/CMSIS/STM32F4xx/Include",
    ]

    sources += [
        "vendor/micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal.c",
        "vendor/micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_cortex.c",
        "vendor/micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_flash.c",
        "vendor/micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_flash_ex.c",
        "vendor/micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_gpio.c",
        "vendor/micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_i2c.c",
        "vendor/micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_ltdc.c",
        "vendor/micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_pcd.c",
        "vendor/micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_pcd_ex.c",
        "vendor/micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_pwr.c",
        "vendor/micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_rcc.c",
        "vendor/micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_rcc_ex.c",
        "vendor/micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_sd.c",
        "vendor/micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_spi.c",
        "vendor/micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_sram.c",
        "vendor/micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_sdram.c",
        "vendor/micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_tim.c",
        "vendor/micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_hal_tim_ex.c",
        "vendor/micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_ll_fmc.c",
        "vendor/micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_ll_sdmmc.c",
    ]

    sources += [
        "embed/trezorhal/stm32f4/board_capabilities.c",
        "embed/trezorhal/stm32f4/boot_args.c",
        "embed/trezorhal/stm32f4/common.c",
        "embed/trezorhal/stm32f4/fault_handlers.c",
        "embed/trezorhal/stm32f4/flash.c",
        "embed/trezorhal/stm32f4/flash_otp.c",
        "embed/trezorhal/stm32f4/lowlevel.c",
        "embed/trezorhal/stm32f4/mpu.c",
        "embed/trezorhal/stm32f4/platform.c",
        "embed/trezorhal/stm32f4/secret.c",
        "embed/trezorhal/stm32f4/systick.c",
        "embed/trezorhal/stm32f4/supervise.c",
        "embed/trezorhal/stm32f4/time_estimate.c",
        "embed/trezorhal/stm32f4/random_delays.c",
        "embed/trezorhal/stm32f4/rng.c",
        "embed/trezorhal/stm32f4/vectortable.s",
    ]

    # boardloader needs separate assembler for some function unencumbered by various FW+bootloader hacks
    # this helps to prevent making a bug in boardloader which may be hard to fix since it's locked with write-protect
    env_constraints = env.get("CONSTRAINTS")
    if env_constraints and "limited_util_s" in env_constraints:
        sources += [
            "embed/trezorhal/stm32f4/limited_util.s",
        ]
    else:
        sources += [
            "embed/trezorhal/stm32f4/util.s",
        ]

    env.get("ENV")["SUFFIX"] = "stm32f4"
    env.get("ENV")["LINKER_SCRIPT"] = "stm32f4"
