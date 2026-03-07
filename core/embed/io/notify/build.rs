// Defines io/notify module
pub fn def_module(lib: &mut cbuild::CLibrary) {
    lib.add_public_include("notify/inc");
    lib.add_source("notify/notify.c");
}
