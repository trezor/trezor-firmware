use xbuild::Result;

fn main() -> Result<()> {
    xbuild::build_and_link("firmware", |lib| {
        lib.import_lib("io")?;
        lib.import_lib("upymod")?;

        lib.add_includes(["."]);

        lib.add_include("../../rust"); // Cyclic dependency

        lib.add_sources(["main.c", "main_main.c", "profile.c"]);

        Ok(())
    })
}
