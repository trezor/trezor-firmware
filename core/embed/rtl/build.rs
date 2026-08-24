use xbuild::{Result, scm_revision};

fn main() -> Result<()> {
    xbuild::build(|lib| {
        lib.import_lib("models")?;

        lib.add_include("inc");

        lib.add_define("SCM_REVISION_SHORT_INIT", Some(&get_scm_revision_short()?));

        lib.add_sources([
            "cli.c",
            "error_handling.c",
            "scm_revision.c",
            "strutils.c",
            "unit_test.c",
        ]);

        if cfg!(any(feature = "sprintf", not(feature = "production"))) {
            lib.add_source("printf.c");
        }

        add_uzlib(lib);

        if cfg!(feature = "error_shims") {
            lib.add_source("error_shims.c");
        }

        lib.add_rust_bindings(add_rust_bindings)?;

        Ok(())
    })
}

/// Extracts the first four bytes of SCM_REVISION and formats them
/// as a C initializer list, e.g. {0x12, 0x34, 0x56, 0x78}.
fn get_scm_revision_short() -> Result<String> {
    let revision = scm_revision()?;

    let init_val = hex::decode(&revision[..8])?
        .iter()
        .map(|byte| format!("0x{byte:02x},"))
        .collect::<String>();

    Ok(format!("{{{}}}", init_val))
}

fn add_uzlib(lib: &mut xbuild::CLibrary) {
    let uzlib_path = "../../vendor/micropython/lib/uzlib";

    lib.add_include(uzlib_path);

    lib.add_sources_in_dir(uzlib_path, ["adler32.c", "crc32.c", "tinflate.c"]);
}

fn add_rust_bindings(builder: bindgen::Builder) -> Result<bindgen::Builder> {
    let builder = builder
        .header("inc/rtl/sysexit.h")
        .allowlist_function("system_exit")
        .allowlist_function("system_exit_error_ex")
        .allowlist_function("system_exit_fatal_ex");
    Ok(builder)
}
