// Defines sec/rsod module
pub fn def_module(lib: &mut cbuild::CLibrary) {
    lib.add_public_include("rsod/inc");

    lib.add_source("rsod/rsod_special.c");
}
