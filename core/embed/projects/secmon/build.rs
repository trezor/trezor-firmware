use xbuild::Result;

fn main() -> Result<()> {
    xbuild::build_and_link("secmon", |lib| {
        lib.import_lib("sec")?;

        lib.add_include(".");

        lib.add_source("main.c");

        // Merkle-tree layout uses a module header (TRZM); otherwise legacy TSEC.
        if cfg!(feature = "pq_secure_boot") {
            lib.add_define("PQ_SECURE_BOOT", Some("1"));
            lib.add_source("module_header.S");
        } else {
            lib.add_source("header.S");
        }

        lib.add_sources_in_dir(
            "../../sys/smcall/stm32",
            ["smcall_dispatch.c", "smcall_probe.c", "smcall_verifiers.c"],
        );

        // The Merkle-tree layout has no legacy vendor header (the secmon module
        // header replaces it). Other builds keep the vendor header.
        if !cfg!(feature = "pq_secure_boot") {
            lib.embed_binary(
                xbuild::vendor_header_path("../../models", "secmon")?,
                "vendorheader",
            )?;
        }

        Ok(())
    })
}
