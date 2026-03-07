// Defines io/suspend module
pub fn def_module(lib: &mut cbuild::CLibrary) {
    lib.add_public_include("suspend/inc");

    //TODO!@# USE_SUSPEND duplicated with sec/suspend
    lib.add_public_define("USE_SUSPEND", Some("1"));

    if cfg!(feature = "mcu_stm32u5") {
        lib.add_sources(&["suspend/stm32u5/suspend_io.c", "suspend/stm32u5/suspend.c"]);
    } else {
        unimplemented!()
    }
}
