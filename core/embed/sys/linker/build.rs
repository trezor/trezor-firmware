use xbuild::CLibrary;

pub fn def_module(lib: &mut CLibrary) {
    lib.add_include("linker/inc");

    lib.add_source("linker/linker_utils.c");
}
