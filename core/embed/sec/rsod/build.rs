use xbuild::{CLibrary, Result};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("rsod/inc");

    lib.add_source("rsod/rsod_special.c");

    Ok(())
}
