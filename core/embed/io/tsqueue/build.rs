// Defines io/tsqueue module
pub fn def_module(lib: &mut cbuild::CLibrary) {
    lib.add_public_include("tsqueue/inc");
    lib.add_source("tsqueue/tsqueue.c");
}
