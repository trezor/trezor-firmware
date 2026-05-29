use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("secret_keys/inc");

    lib.add_define("USE_SECRET_KEYS", Some("1"));

    lib.add_source("secret_keys/secret_keys_common.c");

    if cfg!(feature = "nrf_auth") {
        lib.add_define("USE_NRF_AUTH", Some("1"));
    }

    if cfg!(feature = "emulator") {
        lib.add_source("secret_keys/unix/secret_keys.c");
    } else if cfg!(feature = "mcu_stm32f4") {
        lib.add_source("secret_keys/stm32f4/secret_keys.c");
    } else if cfg!(feature = "mcu_stm32u5") {
        lib.add_source("secret_keys/stm32u5/secret_keys.c");
    } else {
        bail_unsupported!();
    }

    Ok(())
}
