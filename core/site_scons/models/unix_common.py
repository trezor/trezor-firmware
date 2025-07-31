from __future__ import annotations


def unix_common_files(env, defines, sources, paths):
    defines += [
        ("FLASH_BLOCK_WORDS", "1"),
        ("FLASH_BIT_ACCESS", "1"),
        ("CONFIDENTIAL", ""),
    ]

    paths += [
        "embed/io/display/inc",
        "embed/io/usb/inc",
        "embed/sec/random_delays/inc",
        "embed/sec/time_estimate/inc",
        "embed/sys/bsp/inc",
        "embed/sec/rng/inc",
        "embed/sec/monoctr/inc",
        "embed/sec/secret/inc",
        "embed/sys/irq/inc",
        "embed/sys/mpu/inc",
        "embed/sys/startup/inc",
        "embed/sys/task/inc",
        "embed/sys/time/inc",
        "embed/util/board_capabilities/inc",
        "embed/util/cpuid/inc",
        "embed/util/flash/inc",
        "embed/util/fwutils/inc",
        "embed/util/unit_properties/inc",
    ]

    sources += [
        "embed/io/display/unix/display_driver.c",
        "embed/io/usb/unix/usb.c",
        "embed/sec/random_delays/unix/random_delays.c",
        "embed/sec/secret/unix/secret.c",
        "embed/sec/secret/unix/secret_keys.c",
        "embed/sec/storage/unix/storage_salt.c",
        "embed/sec/monoctr/unix/monoctr.c",
        "embed/sec/rng/unix/rng.c",
        "embed/sec/time_estimate/unix/time_estimate.c",
        "embed/sys/mpu/unix/mpu.c",
        "embed/sys/startup/unix/bootutils.c",
        "embed/sys/task/sysevent.c",
        "embed/sys/task/unix/sdl_event.c",
        "embed/sys/task/unix/system.c",
        "embed/sys/task/unix/systask.c",
        "embed/sys/time/unix/systick.c",
        "embed/sys/time/unix/systimer.c",
        "embed/util/board_capabilities/unix/board_capabilities.c",
        "embed/util/cpuid/unix/cpuid.c",
        "embed/util/flash/unix/flash.c",
        "embed/util/flash/unix/flash_otp.c",
        "embed/util/fwutils/fwutils.c",
        "embed/util/unit_properties/unix/unit_properties.c",
    ]
