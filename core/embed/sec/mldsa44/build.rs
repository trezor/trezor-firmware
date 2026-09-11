use xbuild::{CLibrary, Result};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("mldsa44/inc");

    lib.add_define("USE_MLDSA44", Some("1"));

    lib.add_source("mldsa44/mldsa44.c");

    Ok(())
}
