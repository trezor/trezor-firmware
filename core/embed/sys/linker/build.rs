use xbuild::{CLibrary, Result};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("linker/inc");

    lib.add_source("linker/linker_utils.c");

    Ok(())
}
