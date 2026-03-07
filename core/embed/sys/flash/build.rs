// Defines sys/flash module
pub fn def_module(lib: &mut cbuild::CLibrary) {
    lib.add_public_include("flash/inc");

    lib.add_source("flash/flash_utils.c");

    lib.add_source("../../vendor/trezor-storage/flash_area.c");

    if cfg!(feature = "mcu_stm32u5") {
        lib.add_sources(&[
            "flash/stm32u5/flash.c",
            "flash/stm32u5/flash_layout.c",
            "flash/stm32u5/flash_otp.c",
        ]);

        lib.add_public_defines(&[
            ("FLASH_BLOCK_WORDS", Some("4")),
            ("USE_FLASH_BURST", Some("1")),
            ("FLASH_BURST_WORDS", Some("32")),
            ("FLASH_BURST_SIZE", Some("128")),
        ]);
    } else if cfg!(feature = "mcu_stm32f4") {
        lib.add_sources(&[
            "flash/stm32f4/flash.c",
            "flash/stm32f4/flash_layout.c",
            "flash/stm32f4/flash_otp.c",
        ]);

        lib.add_public_defines(&[
            ("FLASH_BLOCK_WORDS", Some("1")),
            ("FLASH_BIT_ACCESS", Some("1")),
        ]);
    } else if cfg!(feature = "mcu_emulator") {
        lib.add_sources(&["flash/unix/flash.c", "flash/unix/flash_otp.c"]);

        // HACK: !@# define according to the current model
        lib.add_define("STM32F427xx", None);
        lib.add_source("flash/stm32f4/flash_layout.c");

        lib.add_public_define("FLASH_BIT_ACCESS", Some("1"));
    } else {
        unimplemented!();
    }
}
