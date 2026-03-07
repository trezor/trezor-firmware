// Defines sec/image module
pub fn def_module(lib: &mut cbuild::CLibrary) {
    lib.add_public_include("image/inc");

    //HACK!@#: where to find version.h
    lib.add_include("../projects/boardloader");

    if cfg!(feature = "boot_ucb") {
        lib.add_sources(&["image/boot_header.c", "image/boot_ucb.c"]);

        // (defined in sys layer)
        // lib.add_public_define("USE_BOOT_UCB", Some("1"));
    }

    lib.add_sources(&["image/image.c", "image/boot_image.c"]);
}
