use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("image/inc");

    if cfg!(feature = "secmon_verification") {
        lib.add_define("USE_SECMON_VERIFICATION", Some("1"));
    }

    // The boot header itself is portable: parsing, hashing and signature
    // verification over a caller-supplied buffer, with no flash or MPU of its
    // own. So it is shared rather than per-MCU -- a bootloader emulator IS the
    // boot chain and cannot emulate anything without it, and the fw_merkle
    // harnesses already build these files for the host. Only the parts that
    // actually touch flash stay platform-specific.
    if cfg!(feature = "boot_ucb") {
        lib.add_sources(["image/boot_header.c", "image/boot_header_merkle.c"]);
    }

    if cfg!(feature = "emulator") {
        // Gated like the stm32 side below: the UCB areas it writes only exist
        // under USE_BOOT_UCB, so a model without the scheme must not pull this
        // in. (It was ungated while the file was a stub that referenced
        // nothing.)
        if cfg!(feature = "boot_ucb") {
            lib.add_source("image/unix/boot_ucb.c");
        }
    } else if cfg!(feature = "mcu_stm32") {
        if cfg!(feature = "boot_ucb") {
            // USE_BOOT_UCB symbol is already define in sys layer
            lib.add_source("image/stm32/boot_ucb.c");
        }
        lib.add_sources(["image/stm32/boot_image.c"]);
    } else {
        bail_unsupported!();
    }

    lib.add_sources(["image/image.c"]);

    Ok(())
}
