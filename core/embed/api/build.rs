use xbuild::Result;

fn main() -> Result<()> {
    xbuild::build(|lib| {
        lib.import_lib("io")?;
        Ok(())
    })
}
