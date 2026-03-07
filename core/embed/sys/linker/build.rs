// Defines sys/linker module
pub fn def_module(lib: &mut cbuild::CLibrary) {
    lib.add_public_include("linker/inc");

    lib.add_source("linker/linker_utils.c");
}
