use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("image/inc");

    if cfg!(feature = "secmon_verification") {
        lib.add_define("USE_SECMON_VERIFICATION", Some("1"));
    }

    // The boot header is portable (parse/hash/verify over a buffer, no flash),
    // so it is shared rather than per-MCU; the emulator and the fw_merkle
    // harnesses build it too.
    if cfg!(feature = "boot_ucb") {
        lib.add_sources(["image/boot_header.c", "image/boot_header_merkle.c"]);
    }

    if cfg!(feature = "emulator") {
        // Like the stm32 side: the UCB areas only exist under USE_BOOT_UCB.
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
