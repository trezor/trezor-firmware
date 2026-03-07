// Defines io/translations module
pub fn def_module(lib: &mut cbuild::CLibrary) {
    lib.add_public_include("translations/inc");
    lib.add_source("translations/translations.c");
}
