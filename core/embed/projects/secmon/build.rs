use xbuild::Result;

fn main() -> Result<()> {
    xbuild::build_and_link("secmon", |lib| {
        lib.import_lib("sec")?;

        lib.add_include(".");

        lib.add_sources(["main.c", "header.S"]);

        lib.add_sources_from_folder(
            "../../sys/smcall/stm32",
            ["smcall_dispatch.c", "smcall_probe.c", "smcall_verifiers.c"],
        );

        lib.embed_binary(
            xbuild::vendor_header_path("../../models", "secmon")?,
            "vendorheader",
        )?;

        Ok(())
    })
}
