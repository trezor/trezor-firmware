use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("vault_kek/inc");
    lib.add_include("vault/inc");

    if cfg!(feature = "emulator") {
        // The emulator vault seals with a software-only key (vault/seal.c).
    } else if cfg!(feature = "mcu_stm32u5") {
        lib.add_define("USE_VAULT_KEK", Some("1"));
        // Compiled out unless SECURE_MODE; a secmon kernel gets the smcall stub.
        lib.add_source("vault_kek/stm32u5/vault_kek.c");
    } else {
        bail_unsupported!();
    }

    Ok(())
}
