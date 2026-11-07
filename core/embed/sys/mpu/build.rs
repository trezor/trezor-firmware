use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("mpu/inc");

    if cfg!(feature = "emulator") {
        lib.add_source("mpu/unix/mpu.c");
    } else if cfg!(feature = "mcu_stm32f4") {
        lib.add_source("mpu/stm32f4/mpu.c");
    } else if cfg!(feature = "mcu_stm32u5") || cfg!(feature = "mcu_stm32h5") {
        // Shared ARMv8-M MPU driver for STM32U5 and STM32H5. The only
        // MCU-specific difference (the LL cortex header) is #if-guarded inside.
        lib.add_source("mpu/stm32u5/mpu.c");
    } else {
        bail_unsupported!();
    }

    Ok(())
}
