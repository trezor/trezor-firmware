// Defines sys/startup module
pub fn def_module(lib: &mut cbuild::CLibrary) {
    lib.add_public_include("startup/inc");

    if cfg!(feature = "mcu_emulator") {
        lib.add_source("startup/unix/bootutils.c");
        return;
    };

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
        unimplemented!();
    }
}
