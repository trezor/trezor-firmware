use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("irq/inc");
    lib.add_rust_bindings(add_rust_bindings)?;

    if cfg!(feature = "emulator") {
        // No implementation
    } else if cfg!(feature = "mcu_stm32") {
        lib.add_source("irq/stm32/irq.c");
    } else {
        bail_unsupported!();
    }

    Ok(())
}

fn add_rust_bindings(builder: bindgen::Builder) -> Result<bindgen::Builder> {
    let builder = builder
        .header("irq/inc/sys/irq.h")
        .allowlist_function("irq_lock_fn")
        .allowlist_function("irq_unlock_fn")
        .allowlist_type("irq_key_t");

    Ok(builder)
}
