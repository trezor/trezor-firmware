// Defines sec/optiga module
pub fn def_module(lib: &mut cbuild::CLibrary) {
    lib.add_public_include("optiga/inc");

    lib.add_public_define("USE_OPTIGA", Some("1"));

    if cfg!(feature = "mcu_stm32") {
        lib.add_sources(&[
            "optiga/stm32/optiga_hal.c",
            "optiga/optiga_commands.c",
            "optiga/optiga_init.c",
            "optiga/optiga_transport.c",
            "optiga/optiga.c",
        ]);
    } else if cfg!(feature = "mcu_emulator") {
        lib.add_sources(&["optiga/unix/optiga_hal.c", "optiga/unix/optiga.c"]);
    } else {
        unimplemented!();
    }
}
