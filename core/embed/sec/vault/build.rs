use std::env;

use xbuild::{CLibrary, Result, cargo_out};
pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("vault/inc");
    lib.add_define("USE_VAULT", Some("1"));
    if cfg!(feature = "kernel_mode") || cfg!(feature = "emulator") {
        lib.add_source("vault/seal.c");
        lib.add_source("vault/vault.c");
    }
    // Emulator only: seed-derived operations run on a card (or its model),
    // see card/vault_card.c.
    cargo_out::rerun_if_env_changed("TREZOR_VAULT_CARD");
    if cfg!(feature = "emulator") && env::var("TREZOR_VAULT_CARD").is_ok_and(|v| v == "1") {
        lib.add_define("VAULT_CARD", Some("1"));
        lib.add_source("vault/card/vault_card.c");
        lib.add_source("vault/card/transport_tcp.c");
    }
    Ok(())
}
