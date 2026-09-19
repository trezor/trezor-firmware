use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("haptic/inc");

    lib.add_define("USE_HAPTIC", Some("1"));

    if cfg!(feature = "emulator") {
        lib.add_source("haptic/unix/haptic.c");
    } else if cfg!(feature = "mcu_stm32") {
        lib.add_source("haptic/drv262x/drv262x.c");
    } else {
        bail_unsupported!();
    }

    lib.add_rust_bindings(|builder| {
        Ok(builder
            .header("haptic/inc/io/haptic.h")
            .allowlist_type("haptic_effect_t")
            .allowlist_function("haptic_play")
            .allowlist_function("haptic_play_custom"))
    })?;

    Ok(())
}
