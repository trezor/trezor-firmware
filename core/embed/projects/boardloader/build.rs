use xbuild::Result;

fn main() -> Result<()> {
    xbuild::build_and_link("boardloader", |lib| {
        lib.import_lib("io");

        lib.add_include(".");

        lib.add_sources(["main.c", "bld_version.c"]);

        if cfg!(feature = "sd_card_update") {
            lib.add_source("sd_update.c");
        }

        Ok(())
    })
}
