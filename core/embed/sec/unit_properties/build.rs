// Define sec/unit_properties module
pub fn def_module(lib: &mut cbuild::CLibrary) {
    lib.add_public_include("unit_properties/inc");

    if cfg!(feature = "mcu_emulator") {
        lib.add_source("unit_properties/unix/unit_properties.c");
        return;
    }

    if cfg!(feature = "mcu_stm32") {
        lib.add_source("unit_properties/stm32/unit_properties.c");
    } else {
        unimplemented!();
    }
}
