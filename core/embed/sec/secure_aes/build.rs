use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("secure_aes/inc");

    if cfg!(feature = "emulator") {
        lib.add_source("secure_aes/unix/secure_aes.c");
    } else if cfg!(feature = "mcu_stm32u5") || cfg!(feature = "mcu_stm32h5") {
        // Shared M33 SAES driver for STM32U5 and STM32H5. init/deinit differ
        // (STM32U5 SHSI vs STM32H5 kernel-clock + BUSY wait) and are #if-guarded
        // inside secure_aes.c.
        lib.add_source("secure_aes/stm32u5/secure_aes.c");
        // The unprivileged-applet SAES path (secure_aes_unpriv) is only used for
        // NORCOW_MIN_VERSION <= 5, which only the STM32U5 targets use.
        if cfg!(feature = "mcu_stm32u5") {
            lib.add_source("secure_aes/stm32u5/secure_aes_unpriv.c");
        }
    } else {
        bail_unsupported!();
    }

    Ok(())
}
