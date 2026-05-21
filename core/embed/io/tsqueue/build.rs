use xbuild::{CLibrary, Result};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("tsqueue/inc");
    lib.add_source("tsqueue/tsqueue.c");

    Ok(())
}
