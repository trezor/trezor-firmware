use xbuild::{CLibrary, Result};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("notify/inc");
    lib.add_source("notify/notify.c");

    Ok(())
}
