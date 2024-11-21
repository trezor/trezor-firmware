from __future__ import annotations


def stm32u5_common_files(env, defines, sources, paths):
    defines += [
        ("STM32_HAL_H", "<stm32u5xx.h>"),
        ("FLASH_BLOCK_WORDS", "4"),
        ("USE_TRUSTZONE", "1"),
        ("CONFIDENTIAL", '__attribute__((section(".confidential")))'),
    ]

    paths += [
        "embed/sec/entropy/inc",
        "embed/sec/hash_processor/inc",
        "embed/sec/monoctr/inc",
        "embed/sec/random_delays/inc",
        "embed/sec/rng/inc",
        "embed/sec/secret/inc",
        "embed/sec/secure_aes/inc",
        "embed/sec/time_estimate/inc",
        "embed/sys/irq/inc",
        "embed/sys/bsp/stm32u5",
        "embed/sys/mpu/inc",
        "embed/sys/pvd/inc",
        "embed/sys/startup/inc",
        "embed/sys/syscall/inc",
        "embed/sys/tamper/inc",
        "embed/sys/task/inc",
        "embed/sys/time/inc",
        "embed/sys/trustzone/inc",
        "embed/util/board_capabilities/inc",
        "embed/util/flash/inc",
        "embed/util/fwutils/inc",
        "embed/util/option_bytes/inc",
        "embed/util/unit_properties/inc",
        "vendor/stm32u5xx_hal_driver/Inc",
        "vendor/cmsis_device_u5/Include",
        "vendor/cmsis_5/CMSIS/Core/Include",
    ]

    sources += [
        "vendor/stm32u5xx_hal_driver/Src/stm32u5xx_hal.c",
        "vendor/stm32u5xx_hal_driver/Src/stm32u5xx_hal_cortex.c",
        "vendor/stm32u5xx_hal_driver/Src/stm32u5xx_hal_cryp.c",
        "vendor/stm32u5xx_hal_driver/Src/stm32u5xx_hal_dma2d.c",
        "vendor/stm32u5xx_hal_driver/Src/stm32u5xx_hal_dma.c",
        "vendor/stm32u5xx_hal_driver/Src/stm32u5xx_hal_dma_ex.c",
        "vendor/stm32u5xx_hal_driver/Src/stm32u5xx_hal_dsi.c",
        "vendor/stm32u5xx_hal_driver/Src/stm32u5xx_hal_exti.c",
        "vendor/stm32u5xx_hal_driver/Src/stm32u5xx_hal_flash.c",
        "vendor/stm32u5xx_hal_driver/Src/stm32u5xx_hal_flash_ex.c",
        "vendor/stm32u5xx_hal_driver/Src/stm32u5xx_hal_gfxmmu.c",
        "vendor/stm32u5xx_hal_driver/Src/stm32u5xx_hal_gpio.c",
        "vendor/stm32u5xx_hal_driver/Src/stm32u5xx_hal_gtzc.c",
        "vendor/stm32u5xx_hal_driver/Src/stm32u5xx_hal_hash.c",
        "vendor/stm32u5xx_hal_driver/Src/stm32u5xx_hal_hash_ex.c",
        "vendor/stm32u5xx_hal_driver/Src/stm32u5xx_hal_i2c.c",
        "vendor/stm32u5xx_hal_driver/Src/stm32u5xx_hal_i2c_ex.c",
        "vendor/stm32u5xx_hal_driver/Src/stm32u5xx_hal_icache.c",
        "vendor/stm32u5xx_hal_driver/Src/stm32u5xx_hal_ltdc.c",
        "vendor/stm32u5xx_hal_driver/Src/stm32u5xx_hal_ltdc_ex.c",
        "vendor/stm32u5xx_hal_driver/Src/stm32u5xx_hal_pcd.c",
        "vendor/stm32u5xx_hal_driver/Src/stm32u5xx_hal_pcd_ex.c",
        "vendor/stm32u5xx_hal_driver/Src/stm32u5xx_hal_pwr.c",
        "vendor/stm32u5xx_hal_driver/Src/stm32u5xx_hal_pwr_ex.c",
        "vendor/stm32u5xx_hal_driver/Src/stm32u5xx_hal_rcc.c",
        "vendor/stm32u5xx_hal_driver/Src/stm32u5xx_hal_rcc_ex.c",
        "vendor/stm32u5xx_hal_driver/Src/stm32u5xx_hal_rtc.c",
        "vendor/stm32u5xx_hal_driver/Src/stm32u5xx_hal_spi.c",
        "vendor/stm32u5xx_hal_driver/Src/stm32u5xx_hal_sram.c",
        "vendor/stm32u5xx_hal_driver/Src/stm32u5xx_hal_tim.c",
        "vendor/stm32u5xx_hal_driver/Src/stm32u5xx_hal_tim_ex.c",
        "vendor/stm32u5xx_hal_driver/Src/stm32u5xx_ll_fmc.c",
    ]

    sources += [
        "embed/sec/entropy/stm32u5/entropy.c",
        "embed/sec/hash_processor/stm32u5/hash_processor.c",
        "embed/sec/monoctr/stm32u5/monoctr.c",
        "embed/sec/random_delays/stm32/random_delays.c",
        "embed/sec/rng/stm32/rng.c",
        "embed/sec/secret/stm32u5/secret.c",
        "embed/sec/secure_aes/stm32u5/secure_aes.c",
        "embed/sec/time_estimate/stm32/time_estimate.c",
        "embed/sys/mpu/stm32u5/mpu.c",
        "embed/sys/pvd/stm32/pvd.c",
        "embed/sys/startup/stm32/bootutils.c",
        "embed/sys/startup/stm32u5/reset_flags.c",
        "embed/sys/startup/stm32u5/startup_init.c",
        "embed/sys/startup/stm32u5/vectortable.S",
        "embed/sys/syscall/stm32/syscall.c",
        "embed/sys/syscall/stm32/syscall_dispatch.c",
        "embed/sys/syscall/stm32/syscall_probe.c",
        "embed/sys/syscall/stm32/syscall_stubs.c",
        "embed/sys/syscall/stm32/syscall_verifiers.c",
        "embed/sys/tamper/stm32u5/tamper.c",
        "embed/sys/task/stm32/applet.c",
        "embed/sys/task/stm32/systask.c",
        "embed/sys/task/stm32/system.c",
        "embed/sys/time/stm32/systick.c",
        "embed/sys/time/stm32/systimer.c",
        "embed/sys/trustzone/stm32u5/trustzone.c",
        "embed/util/board_capabilities/stm32/board_capabilities.c",
        "embed/util/flash/stm32u5/flash.c",
        "embed/util/flash/stm32u5/flash_layout.c",
        "embed/util/flash/stm32u5/flash_otp.c",
        "embed/util/fwutils/fwutils.c",
        "embed/util/option_bytes/stm32u5/option_bytes.c",
        "embed/util/unit_properties/stm32/unit_properties.c",
    ]

    # boardloader needs separate assembler for some function unencumbered by various FW+bootloader hacks
    # this helps to prevent making a bug in boardloader which may be hard to fix since it's locked with write-protect
    env_constraints = env.get("CONSTRAINTS")
    if env_constraints and "limited_util_s" in env_constraints:
        sources += [
            "embed/sys/startup/stm32u5/limited_util.S",
        ]
    else:
        sources += [
            "embed/sys/startup/stm32u5/util.S",
        ]

    env.get("ENV")["SUFFIX"] = "stm32u5"
