fn main() {
    let mut lib = cbuild::CLibrary::new();

    lib.use_lib("io");

    lib.add_include(".");

    lib.add_source("main.c");
    lib.add_source("bld_version.c");

    if cfg!(feature = "sd_card_update") {
        lib.add_source("sd_update.c");
    }

    lib.build();

    cbuild::emit_linker_args("boardloader");
}
