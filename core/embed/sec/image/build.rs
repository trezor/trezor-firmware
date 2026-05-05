use xbuild::{CLibrary, Result};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("image/inc");

    if cfg!(feature = "secmon_verification") {
        lib.add_define("USE_SECMON_VERIFICATION", Some("1"));
    }

    if cfg!(feature = "boot_ucb") {
        lib.add_sources(["image/boot_header.c", "image/boot_ucb.c"]);

        // USE_BOOT_UCB symbol is already define in sys layer
    }

    lib.add_sources(["image/image.c", "image/boot_image.c"]);

    Ok(())
}
