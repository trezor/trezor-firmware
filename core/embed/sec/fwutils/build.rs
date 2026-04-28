use xbuild::{CLibrary, Result};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("fwutils/inc");

    lib.add_source("fwutils/fwutils.c");

    Ok(())
}
