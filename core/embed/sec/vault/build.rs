use xbuild::{CLibrary, Result};
pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("vault/inc");
    lib.add_define("USE_VAULT", Some("1"));
    if cfg!(feature = "kernel_mode") || cfg!(feature = "emulator") {
        lib.add_source("vault/seal.c");
        lib.add_source("vault/vault.c");
    }
    Ok(())
}
