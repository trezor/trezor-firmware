use xbuild::{CLibrary, Result};
pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("vault/inc");
    lib.add_define("USE_VAULT", Some("1"));
    if cfg!(feature = "kernel_mode") || cfg!(feature = "emulator") {
        // Secrets are sealed into client-held blobs on every model. U5 wraps
        // the per-boot key with the BHK via vault_kek (in-kernel, or in secmon
        // through an smcall); F4 and the emulator use a software key.
        lib.add_source("vault/seal.c");
        lib.add_source("vault/vault.c");
    }
    Ok(())
}
