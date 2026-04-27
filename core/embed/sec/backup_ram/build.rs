use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("backup_ram/inc");

    lib.add_define("USE_BACKUP_RAM", Some("1"));

    lib.add_source("backup_ram/backup_ram_crc.c");

    if cfg!(feature = "emulator") {
        lib.add_source("backup_ram/unix/backup_ram.c");
    } else if cfg!(feature = "mcu_stm32u5") {
        lib.add_source("backup_ram/stm32u5/backup_ram.c");
    } else {
        bail_unsupported!();
    }

    Ok(())
}
