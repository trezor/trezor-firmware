use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("image/inc");

    if cfg!(feature = "secmon_verification") {
        lib.add_define("USE_SECMON_VERIFICATION", Some("1"));
    }

    // The boot header is portable (parse/hash/verify over a buffer, no flash),
    // so it is shared rather than per-MCU; the emulator and host tests build
    // it too.
    if cfg!(feature = "boot_ucb") {
        lib.add_source("image/boot_header.c");
    }

    // The firmware Merkle-tree scheme: same portability, but only a
    // pq_secure_boot model uses it.
    if cfg!(feature = "pq_secure_boot") {
        lib.add_sources([
            "image/boot_header_consent.c",
            "image/firmware_manifest.c",
            "image/fw_variant.c",
            "image/merkle.c",
            "image/model_tree.c",
            "image/tree_update.c",
        ]);
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

    // Legacy vendor/image/secmon header verification; a Merkle-tree build
    // verifies boot headers and manifests instead.
    if !cfg!(feature = "pq_secure_boot") {
        lib.add_source("image/image.c");
    }

    Ok(())
}
