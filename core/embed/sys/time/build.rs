// Define sys/time module
pub fn def_module(lib: &mut cbuild::CLibrary) {
    lib.add_public_include("time/inc");

    if cfg!(feature = "mcu_stm32") {
        lib.add_sources(&["time/stm32/systick.c", "time/stm32/systimer.c"]);
    } else if cfg!(feature = "mcu_emulator") {
        lib.add_sources(&["time/unix/systick.c", "time/unix/systimer.c"]);
    } else {
        unimplemented!();
    }

    if cfg!(feature = "rtc") {
        lib.add_public_define("USE_RTC", Some("1"));

        if cfg!(feature = "mcu_stm32u5") {
            lib.add_sources(&["time/stm32u5/rtc_scheduler.c", "time/stm32u5/rtc.c"]);
        } else {
            unimplemented!();
        }
    }
}
