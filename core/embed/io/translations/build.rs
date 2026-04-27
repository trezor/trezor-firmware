use xbuild::{CLibrary, Result};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("translations/inc");
    lib.add_source("translations/translations.c");

    Ok(())
}
