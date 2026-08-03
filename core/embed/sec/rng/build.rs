use xbuild::{CLibrary, Result};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("rng/inc");

    lib.add_source("rng/rng_strong.c");

    if cfg!(feature = "emulator") {
        lib.add_source("rng/unix/rng_mock.c");
    }

    Ok(())
}
