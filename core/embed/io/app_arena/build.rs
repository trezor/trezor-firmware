use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("app_arena/inc");
    lib.add_rust_bindings(add_rust_bindings)?;

    // USE_APP_LOADING is defined in sys layer
    lib.add_sources([
        "app_arena/app_arena.c",
        "app_arena/app_header.c",
        "app_arena/app_root.c",
        "app_arena/root_packet.c",
    ]);

    if cfg!(feature = "emulator") {
        lib.add_source("app_arena/unix/app_loader.c");
    } else if cfg!(feature = "mcu_stm32u5") {
        lib.add_sources(["app_arena/stm32u5/app_loader.c"]);
    } else {
        bail_unsupported!();
    }

    Ok(())
}

fn add_rust_bindings(builder: bindgen::Builder) -> Result<bindgen::Builder> {
    let builder = builder
        .header("app_arena/inc/io/app_arena.h")
        .allowlist_function("app_get_heap");

    Ok(builder)
}
