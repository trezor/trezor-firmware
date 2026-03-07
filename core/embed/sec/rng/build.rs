// Defines sec/rng module
pub fn def_module(lib: &mut cbuild::CLibrary) {
    lib.add_public_include("rng/inc");

    lib.add_source("rng/rng_strong.c")
}
