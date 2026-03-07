// Defines sec/backup_ram module
pub fn def_module(lib: &mut cbuild::CLibrary) {
    lib.add_public_include("backup_ram/inc");

    lib.add_public_define("USE_BACKUP_RAM", Some("1"));

    if cfg!(feature = "mcu_emulator") {
        return;
    }

    if cfg!(feature = "mcu_stm32u5") {
        lib.add_source("backup_ram/stm32u5/backup_ram.c");
    } else {
        unimplemented!();
    }

    lib.add_source("backup_ram/backup_ram_crc.c");
}
