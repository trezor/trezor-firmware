use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("flash/inc");

    lib.add_source("flash/flash_utils.c");

    lib.add_source("../../vendor/trezor-storage/flash_area.c");

    if cfg!(feature = "mcu_stm32f4") {
        lib.add_defines([
            ("FLASH_BIT_ACCESS", Some("1")),
            ("FLASH_BLOCK_WORDS", Some("1")),
        ]);

        lib.add_source("flash/stm32f4/flash_layout.c");

        if cfg!(feature = "emulator") {
            lib.add_define("STM32F427xx", None);
            lib.add_sources(["flash/unix/flash.c", "flash/unix/flash_otp.c"]);
        } else {
            lib.add_sources(["flash/stm32f4/flash.c", "flash/stm32f4/flash_otp.c"]);
        }
    } else if cfg!(feature = "mcu_stm32u5") {
        lib.add_defines([("FLASH_BLOCK_WORDS", Some("4"))]);

        lib.add_source("flash/stm32u5/flash_layout.c");

        if cfg!(feature = "emulator") {
            if cfg!(feature = "mcu_stm32u5g") {
                lib.add_define("STM32U5G9xx", None);
            } else if cfg!(feature = "mcu_stm32u58") {
                lib.add_define("STM32U585xx", None);
            } else {
                bail_unsupported!();
            }

            lib.add_sources(["flash/unix/flash.c", "flash/unix/flash_otp.c"]);
        } else {
            lib.add_defines([
                ("USE_FLASH_BURST", Some("1")),
                ("FLASH_BURST_WORDS", Some("32")),
                ("FLASH_BURST_SIZE", Some("128")),
            ]);

            lib.add_sources(["flash/stm32u5/flash.c", "flash/stm32u5/flash_otp.c"]);
        }
    } else {
        bail_unsupported!();
    }

    Ok(())
}
