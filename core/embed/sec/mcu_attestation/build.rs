use xbuild::{CLibrary, Result};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("mcu_attestation/inc");

    lib.add_define("USE_MCU_ATTESTATION", Some("1"));

    lib.add_source("mcu_attestation/mcu_attestation.c");

    Ok(())
}
