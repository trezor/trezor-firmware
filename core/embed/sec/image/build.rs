use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("image/inc");

    if cfg!(feature = "secmon_verification") {
        lib.add_define("USE_SECMON_VERIFICATION", Some("1"));
    }

    if cfg!(feature = "emulator") {
        lib.add_source("image/unix/boot_ucb.c")
    } else if cfg!(feature = "mcu_stm32") {
        if cfg!(feature = "boot_ucb") {
            lib.add_sources(["image/stm32/boot_header.c", "image/stm32/boot_ucb.c"]);
            // USE_BOOT_UCB symbol is already define in sys layer
        }
        lib.add_sources(["image/stm32/boot_image.c"]);
    } else {
        bail_unsupported!();
    }

    lib.add_sources(["image/image.c"]);

    Ok(())
}
