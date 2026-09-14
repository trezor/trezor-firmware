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
        lib.add_source("flash/stm32u5/flash_layout.c");

        // Uniform 8 KiB pages across the whole STM32U5 family, and the same
        // value flash/unix/flash.c uses to build its emulated sector table.
        // Consumed by flash_layout_ucb.c, which needs it at compile time and
        // cannot read the HAL's FLASH_PAGE_SIZE on an emulator build.
        lib.add_define("FLASH_LAYOUT_PAGE_SIZE", Some("0x2000"));

        if cfg!(feature = "emulator") {
            // TODO: do not use FLASH_BIT_ACCESS for emulating STM32U5
            // (keeping it for backward compatibility with the SCons build system,
            // but we should reconsider this in the future)
            lib.add_defines([
                ("FLASH_BIT_ACCESS", Some("1")),
                ("FLASH_BLOCK_WORDS", Some("1")),
            ]);

            if cfg!(feature = "mcu_stm32u5g") {
                lib.add_define("STM32U5G9xx", None);
            } else if cfg!(feature = "mcu_stm32u5a") {
                lib.add_define("STM32U5A5xx", None);
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
                ("FLASH_BLOCK_WORDS", Some("4")),
            ]);

            lib.add_sources(["flash/stm32u5/flash.c", "flash/stm32u5/flash_otp.c"]);
        }
    } else {
        bail_unsupported!();
    }

    if cfg!(feature = "boot_ucb") {
        // Where a staged image lives follows from the model's firmware region,
        // not from the MCU, so this is shared rather than copied per family.
        // It does need a uniform page size (set just above per MCU); an MCU
        // with mixed sector sizes could not express the areas this way, which
        // is why the guard is here and not a silent fallback.
        if !cfg!(feature = "mcu_stm32u5") {
            bail_unsupported!();
        }
        lib.add_source("flash/flash_layout_ucb.c");
    }

    Ok(())
}
