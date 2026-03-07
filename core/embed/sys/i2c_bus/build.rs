// Defines sys/i2c_bus module
pub fn def_module(lib: &mut cbuild::CLibrary) {
    lib.add_public_include("i2c_bus/inc");

    if cfg!(feature = "mcu_emulator") {
        return;
    }

    if cfg!(feature = "mcu_stm32f4") {
        lib.add_source("i2c_bus/stm32f4/i2c_bus.c");
    } else if cfg!(feature = "mcu_stm32u5") {
        lib.add_source("i2c_bus/stm32u5/i2c_bus.c");
    } else {
        unimplemented!();
    }
}
