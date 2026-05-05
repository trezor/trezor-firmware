use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("secure_aes/inc");

    if cfg!(feature = "emulator") {
        lib.add_source("secure_aes/unix/secure_aes.c");
    } else if cfg!(feature = "mcu_stm32u5") {
        lib.add_source("secure_aes/stm32u5/secure_aes.c");
        lib.add_source("secure_aes/stm32u5/secure_aes_unpriv.c");
    } else {
        bail_unsupported!();
    }

    Ok(())
}
