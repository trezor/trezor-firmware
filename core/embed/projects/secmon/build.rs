use xbuild::Result;

fn main() -> Result<()> {
    xbuild::build_and_link("secmon", |lib| {
        lib.import_lib("sec")?;

        lib.add_include(".");

        lib.add_source("main.c");

        // Merkle-tree layout: code only (no legacy TSEC header).
        if cfg!(not(feature = "pq_secure_boot")) {
            lib.add_source("header.S");
        }

        lib.add_sources_in_dir(
            "../../sys/smcall/stm32",
            ["smcall_dispatch.c", "smcall_probe.c", "smcall_verifiers.c"],
        );

        // No legacy vendor header in the Merkle-tree layout.
        if !cfg!(feature = "pq_secure_boot") {
            lib.embed_binary(
                xbuild::vendor_header_path("../../models", "secmon")?,
                "vendorheader",
            )?;
        }

        Ok(())
    })
}
