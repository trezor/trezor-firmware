use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("optiga/inc");

    lib.add_define("USE_OPTIGA", Some("1"));

    if cfg!(feature = "optiga_testing") {
        lib.add_define("USE_OPTIGA_TESTING", Some("1"));
    }

    lib.add_sources(["optiga/optiga_init.c"]);

    if cfg!(feature = "emulator") {
        lib.add_sources([
            "optiga/unix/optiga_commands.c",
            "optiga/unix/optiga_hal.c",
            "optiga/unix/optiga_transport.c",
            "optiga/unix/optiga.c",
        ]);
    } else if cfg!(feature = "mcu_stm32") {
        lib.add_sources([
            "optiga/optiga_commands.c",
            "optiga/optiga_transport.c",
            "optiga/optiga.c",
            "optiga/stm32/optiga_hal.c",
        ]);
    } else {
        bail_unsupported!();
    }

    Ok(())
}
