use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("startup/inc");

    lib.add_source("startup/startup_args.c");

    if cfg!(feature = "emulator") {
        lib.add_source("startup/unix/bootutils.c");
    } else {
        if cfg!(feature = "mcu_stm32") {
            lib.add_source("startup/stm32/bootutils.c");
            lib.add_source("startup/stm32/sysutils.c");
        }

        if cfg!(feature = "mcu_stm32u5") {
            lib.add_source("startup/stm32u5/startup_init.c");
            lib.add_source("startup/stm32u5/reset_flags.c");
            lib.add_source("startup/stm32u5/vectortable.S");
        } else if cfg!(feature = "mcu_stm32f4") {
            lib.add_source("startup/stm32f4/startup_init.c");
            lib.add_source("startup/stm32f4/reset_flags.c");
            lib.add_source("startup/stm32f4/vectortable.S");
        } else {
            bail_unsupported!();
        }
    }

    Ok(())
}
