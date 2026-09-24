use xbuild::Result;

fn main() -> Result<()> {
    xbuild::build(|lib| {
        lib.import_lib("io")?;

        // Compile a dummy source file to ensure the library is created
        // (=> metadata are passed to higher-level crates)
        lib.add_source("src/_dummy.c");

        Ok(())
    })
}
