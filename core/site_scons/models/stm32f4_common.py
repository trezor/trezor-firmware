from __future__ import annotations


def stm32f4_common_files(env, features_wanted, defines, sources, paths):
    features_available: list[str] = []

    defines += [
        ("STM32_HAL_H", "<stm32f4xx.h>"),
        ("FLASH_BLOCK_WORDS", "1"),
        ("FLASH_BIT_ACCESS", "1"),
    ]

    paths += [
        "embed/io/notify/inc",
        "embed/io/tsqueue/inc",
        "embed/sec/monoctr/inc",
        "embed/sec/random_delays/inc",
        "embed/sec/rng/inc",
        "embed/sec/secure_aes/inc",
        "embed/sec/time_estimate/inc",
        "embed/sys/bsp/stm32f4",
        "embed/sys/inc",
        "embed/sys/irq/inc",
        "embed/sys/linker/inc",
        "embed/sys/mpu/inc",
        "embed/sys/pvd/inc",
        "embed/sys/rng/inc",
        "embed/sec/board_capabilities/inc",
        "embed/sec/secret/inc",
        "embed/sec/unit_properties/inc",
        "embed/sys/stack/inc",
        "embed/sys/startup/inc",
        "embed/sys/syscall/inc",
        "embed/sys/task/inc",
        "embed/sys/time/inc",
        "embed/util/cpuid/inc",
        "embed/util/flash/inc",
        "embed/util/fwutils/inc",
        "embed/util/option_bytes/inc",
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
        "embed/io/notify/notify.c",
        "embed/io/tsqueue/tsqueue.c",
        "embed/sec/board_capabilities/stm32/board_capabilities.c",
        "embed/sec/monoctr/stm32f4/monoctr.c",
        "embed/sec/random_delays/stm32/random_delays.c",
        "embed/sec/rng/rng_strong.c",
        "embed/sec/secret/stm32f4/secret.c",
        "embed/sec/secret/stm32f4/secret_keys.c",
        "embed/sec/secret/secret_keys_common.c",
        "embed/sec/storage/stm32f4/storage_salt.c",
        "embed/sec/time_estimate/stm32/time_estimate.c",
        "embed/sec/unit_properties/stm32/unit_properties.c",
        "embed/sys/irq/stm32/irq.c",
        "embed/sys/linker/linker_utils.c",
        "embed/sys/mpu/stm32f4/mpu.c",
        "embed/sys/pvd/stm32/pvd.c",
        "embed/sys/rng/stm32/rng.c",
        "embed/sys/stack/stm32/stack_utils.c",
        "embed/sys/startup/stm32/bootutils.c",
        "embed/sys/startup/stm32/sysutils.c",
        "embed/sys/startup/stm32f4/reset_flags.c",
        "embed/sys/startup/stm32f4/startup_init.c",
        "embed/sys/startup/stm32f4/vectortable.S",
        "embed/sys/syscall/stm32/syscall_context.c",
        "embed/sys/syscall/stm32/syscall_dispatch.c",
        "embed/sys/syscall/stm32/syscall_ipc.c",
        "embed/sys/syscall/stm32/syscall_probe.c",
        "embed/sys/syscall/stm32/syscall_stubs.c",
        "embed/sys/syscall/stm32/syscall_verifiers.c",
        "embed/sys/task/stm32/applet.c",
        "embed/sys/task/stm32/coreapp.c",
        "embed/sys/task/stm32/systask.c",
        "embed/sys/task/stm32/system.c",
        "embed/sys/time/stm32/systick.c",
        "embed/sys/time/stm32/systimer.c",
        "embed/sys/task/sysevent.c",
        "embed/util/cpuid/stm32/cpuid.c",
        "embed/util/flash/stm32f4/flash.c",
        "embed/util/flash/stm32f4/flash_layout.c",
        "embed/util/flash/stm32f4/flash_otp.c",
        "embed/util/fwutils/fwutils.c",
        "embed/util/option_bytes/stm32f4/option_bytes.c",
    ]

    if "dbg_console" in features_wanted:
        sources += [
            "embed/sys/dbg/dbg_console.c",
            "embed/sys/dbg/syslog.c",
            "embed/sys/dbg/stm32/dbg_console_backend.c",
        ]
        paths += ["embed/sys/dbg/inc"]
        defines += [("USE_DBG_CONSOLE", "1")]
        features_available.append("dbg_console")

        if env.get("DBG_CONSOLE") == "VCP" and "usb" in features_wanted:
            features_wanted += ["usb_iface_vcp"]
            defines += ["USE_DBG_CONSOLE_VCP"]
        elif env.get("DBG_CONSOLE") == "SWO":
            defines += ["USE_DBG_CONSOLE_SWO"]
        elif env.get("DBG_CONSOLE") == "SYSTEM_VIEW":
            features_wanted += ["system_view"]
            defines += ["USE_DBG_CONSOLE_SYSTEM_VIEW"]

    if "usb" in features_wanted:
        sources += [
            "embed/io/usb/stm32/usb_class_hid.c",
            "embed/io/usb/stm32/usb_class_vcp.c",
            "embed/io/usb/stm32/usb_class_webusb.c",
            "embed/io/usb/stm32/usb.c",
            "embed/io/usb/stm32/usb_rbuf.c",
            "embed/io/usb/stm32/usbd_conf.c",
            "embed/io/usb/stm32/usbd_core.c",
            "embed/io/usb/stm32/usbd_ctlreq.c",
            "embed/io/usb/stm32/usbd_ioreq.c",
            "embed/io/usb/usb_config.c",
            "vendor/micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Src/stm32f4xx_ll_usb.c",
        ]
        features_available.append("usb")
        paths += ["embed/io/usb/inc"]
        defines += [("USE_USB", "1")]

        if "usb_iface_wire" in features_wanted:
            defines += [("USE_USB_IFACE_WIRE", "1")]
        if "usb_iface_debug" in features_wanted:
            defines += [("USE_USB_IFACE_DEBUG", "1")]
        if "usb_iface_webauthn" in features_wanted:
            defines += [("USE_USB_IFACE_WEBAUTHN", "1")]
        if "usb_iface_vcp" in features_wanted:
            defines += [("USE_USB_IFACE_VCP", "1")]

    if "system_view" in features_wanted:
        sources += [
            "embed/sys/dbg/stm32/systemview/config/SEGGER_SYSVIEW_Config_NoOS.c",
            "embed/sys/dbg/stm32/systemview/segger/SEGGER_SYSVIEW.c",
            "embed/sys/dbg/stm32/systemview/segger/SEGGER_RTT.c",
            "embed/sys/dbg/stm32/systemview/segger/SEGGER_RTT_ASM_ARMv7M.S",
        ]
        paths += [
            "embed/sys/dbg/stm32/systemview/config",
            "embed/sys/dbg/stm32/systemview/segger",
        ]
        defines += [("USE_SYSTEM_VIEW", "1")]

    env.get("ENV")["SUFFIX"] = "stm32f4"
    env.get("ENV")["LINKER_SCRIPT"] = """embed/sys/linker/stm32f4/{target}.ld"""
    env.get("ENV")["MEMORY_LAYOUT"] = "memory.ld"

    return features_available
