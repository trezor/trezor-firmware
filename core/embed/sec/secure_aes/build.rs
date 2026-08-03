use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("secure_aes/inc");

    if cfg!(feature = "emulator") {
        lib.add_source("secure_aes/unix/secure_aes.c");
    } else if cfg!(feature = "mcu_stm32u5") {
        lib.add_source("secure_aes/stm32u5/secure_aes.c");
        lib.add_source("secure_aes/stm32u5/secure_aes_unpriv.c");
    } else if cfg!(feature = "mcu_stm32h5") {
        // The unprivileged-applet SAES path (secure_aes_unpriv) is only used for
        // NORCOW_MIN_VERSION <= 5; H5 targets use a newer NORCOW, so only the
        // main driver is needed for now.
        lib.add_source("secure_aes/stm32h5/secure_aes.c");
    } else {
        bail_unsupported!();
    }

    Ok(())
}
