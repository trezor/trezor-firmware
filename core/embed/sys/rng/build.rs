use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("rng/inc");

    if cfg!(feature = "emulator") {
        lib.add_define("USE_INSECURE_PRNG", Some("1"));

        lib.add_sources(["rng/unix/rng.c", "rng/unix/rng_mock.c"]);
    } else if cfg!(feature = "mcu_stm32") {
        lib.add_source("rng/stm32/rng.c");
    } else {
        bail_unsupported!();
    }

    Ok(())
}
