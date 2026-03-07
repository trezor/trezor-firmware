// Defines sys/mpu module
pub fn def_module(lib: &mut cbuild::CLibrary) {
    lib.add_public_includes(&["mpu/inc"]);

    if cfg!(feature = "mcu_stm32f4") {
        lib.add_source("mpu/stm32f4/mpu.c");
    } else if cfg!(feature = "mcu_stm32u5") {
        lib.add_source("mpu/stm32u5/mpu.c");
    } else if cfg!(feature = "mcu_emulator") {
        lib.add_source("mpu/unix/mpu.c");
    } else {
        unimplemented!();
    }
}
