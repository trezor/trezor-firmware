use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("time/inc");
    lib.add_rust_bindings(add_rust_bindings)?;

    if cfg!(feature = "emulator") {
        lib.add_sources(["time/unix/systick.c", "time/unix/systimer.c"]);
    } else if cfg!(feature = "mcu_stm32") {
        lib.add_sources(["time/stm32/systick.c", "time/stm32/systimer.c"]);
    } else {
        bail_unsupported!();
    }

    if cfg!(feature = "rtc") {
        lib.add_define("USE_RTC", Some("1"));

        if cfg!(feature = "emulator") {
            lib.add_source("time/unix/rtc.c");
        } else if cfg!(feature = "mcu_stm32u5") {
            lib.add_sources(["time/stm32u5/rtc_scheduler.c", "time/stm32u5/rtc.c"]);
        } else {
            bail_unsupported!();
        }
    }

    Ok(())
}

fn add_rust_bindings(builder: bindgen::Builder) -> Result<bindgen::Builder> {
    let builder = builder
        .header("time/inc/sys/systick.h")
        .allowlist_function("systick_ms")
        .allowlist_function("systick_us")
        .allowlist_function("systick_delay_ms")
        .allowlist_function("systick_delay_us");
    Ok(builder)
}
