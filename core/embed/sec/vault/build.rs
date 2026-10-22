use xbuild::{CLibrary, Result};
pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("vault/inc");
    if cfg!(feature = "kernel_mode") || cfg!(feature = "emulator") {
        lib.add_source("vault/seal.c");
    }
    Ok(())
}
