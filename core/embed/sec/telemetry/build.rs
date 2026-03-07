// Defines sec/telemetry_bytes module
pub fn def_module(lib: &mut cbuild::CLibrary) {
    lib.add_public_include("telemetry/inc");

    lib.add_public_define("USE_TELEMETRY", Some("1"));

    if cfg!(feature = "mcu_stm32u5") {
        lib.add_source("telemetry/stm32u5/telemetry.c");
    } else if cfg!(feature = "mcu_stm32f4") {
        lib.add_source("telemetry/unix/telemetry.c");
    } else {
        unimplemented!();
    }
}
