from __future__ import annotations


def stm32f4_common_files(env, defines, sources, paths):
    defines += [
        ("STM32_HAL_H", "<stm32f4xx.h>"),
        ("FLASH_BLOCK_WORDS", "1"),
        ("FLASH_BIT_ACCESS", "1"),
        ("CONFIDENTIAL", ""),
    ]

    paths += [
        "embed/sec/entropy/inc",
        "embed/sec/monoctr/inc",
        "embed/sec/random_delays/inc",
        "embed/sec/rng/inc",
        "embed/sec/secure_aes/inc",
        "embed/sec/time_estimate/inc",
        "embed/sys/bsp/stm32f4",
        "embed/sys/irq/inc",
        "embed/sys/mpu/inc",
        "embed/sys/pvd/inc",
        "embed/sec/secret/inc",
        "embed/sys/startup/inc",
        "embed/sys/syscall/inc",
        "embed/sys/task/inc",
        "embed/sys/time/inc",
        "embed/util/board_capabilities/inc",
        "embed/util/flash/inc",
        "embed/util/fwutils/inc",
        "embed/util/option_bytes/inc",
        "embed/util/unit_properties/inc",
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
        "embed/sec/entropy/stm32f4/entropy.c",
        "embed/sec/monoctr/stm32f4/monoctr.c",
        "embed/sec/random_delays/stm32/random_delays.c",
        "embed/sec/rng/stm32/rng.c",
        "embed/sec/secret/stm32f4/secret.c",
        "embed/sec/time_estimate/stm32/time_estimate.c",
        "embed/sys/mpu/stm32f4/mpu.c",
        "embed/sys/pvd/stm32/pvd.c",
        "embed/sys/startup/stm32/bootutils.c",
        "embed/sys/startup/stm32f4/reset_flags.c",
        "embed/sys/startup/stm32f4/startup_init.c",
        "embed/sys/startup/stm32f4/vectortable.S",
        "embed/sys/syscall/stm32/syscall.c",
        "embed/sys/syscall/stm32/syscall_dispatch.c",
        "embed/sys/syscall/stm32/syscall_probe.c",
        "embed/sys/syscall/stm32/syscall_stubs.c",
        "embed/sys/syscall/stm32/syscall_verifiers.c",
        "embed/sys/task/stm32/applet.c",
        "embed/sys/task/stm32/systask.c",
        "embed/sys/task/stm32/system.c",
        "embed/sys/time/stm32/systick.c",
        "embed/sys/time/stm32/systimer.c",
        "embed/util/board_capabilities/stm32/board_capabilities.c",
        "embed/util/flash/stm32f4/flash.c",
        "embed/util/flash/stm32f4/flash_layout.c",
        "embed/util/flash/stm32f4/flash_otp.c",
        "embed/util/fwutils/fwutils.c",
        "embed/util/option_bytes/stm32f4/option_bytes.c",
        "embed/util/unit_properties/stm32/unit_properties.c",
    ]

    # boardloader needs separate assembler for some function unencumbered by various FW+bootloader hacks
    # this helps to prevent making a bug in boardloader which may be hard to fix since it's locked with write-protect
    env_constraints = env.get("CONSTRAINTS")
    if env_constraints and "limited_util_s" in env_constraints:
        sources += [
            "embed/sys/startup/stm32f4/limited_util.S",
        ]
    else:
        sources += [
            "embed/sys/startup/stm32f4/util.S",
        ]

    env.get("ENV")["SUFFIX"] = "stm32f4"
    env.get("ENV")["LINKER_SCRIPT"] = """embed/sys/linker/stm32f4/{target}.ld"""
