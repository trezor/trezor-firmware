from __future__ import annotations


def unix_common_files(env, features_wanted, defines, sources, paths):
    features_available: list[str] = []

    defines += [
        ("FLASH_BLOCK_WORDS", "1"),
        ("FLASH_BIT_ACCESS", "1"),
    ]

    paths += [
        "embed/io/notify/inc",
        "embed/io/display/inc",
        "embed/sec/random_delays/inc",
        "embed/sec/time_estimate/inc",
        "embed/sys/bsp/inc",
        "embed/sys/inc",
        "embed/sec/rng/inc",
        "embed/sec/monoctr/inc",
        "embed/sec/secret/inc",
        "embed/sec/unit_properties/inc",
        "embed/sys/irq/inc",
        "embed/sys/mpu/inc",
        "embed/sys/rng/inc",
        "embed/sys/startup/inc",
        "embed/sys/task/inc",
        "embed/sys/time/inc",
        "embed/util/board_capabilities/inc",
        "embed/util/cpuid/inc",
        "embed/util/flash/inc",
        "embed/util/fwutils/inc",
    ]

    sources += [
        "embed/io/display/unix/display_driver.c",
        "embed/io/notify/notify.c",
        "embed/io/usb/unix/sock.c",
        "embed/sec/random_delays/unix/random_delays.c",
        "embed/sec/secret/unix/secret.c",
        "embed/sec/secret/unix/secret_keys.c",
        "embed/sec/secret/secret_keys_common.c",
        "embed/sec/storage/unix/storage_salt.c",
        "embed/sec/monoctr/unix/monoctr.c",
        "embed/sec/rng/rng_strong.c",
        "embed/sec/time_estimate/unix/time_estimate.c",
        "embed/sec/unit_properties/unix/unit_properties.c",
        "embed/sys/mpu/unix/mpu.c",
        "embed/sys/rng/unix/rng.c",
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
    ]

    if "usb" in features_wanted:
        sources += [
            "embed/io/usb/unix/usb.c",
            "embed/io/usb/usb_config.c",
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

    if "dbg_console" in features_wanted:
        sources += [
            "embed/sys/dbg/dbg_console.c",
            "embed/sys/dbg/syslog.c",
            "embed/sys/dbg/unix/dbg_console_backend.c",
        ]
        paths += ["embed/sys/dbg/inc"]
        defines += [("USE_DBG_CONSOLE", "1")]
        features_available.append("dbg_console")

    return features_available
