use bindgen::EnumVariation;
use std::path::PathBuf;
use xbuild::Result;

fn main() -> Result<()> {
    xbuild::build(|lib| {
        lib.import_lib("sec")?;

        lib.add_includes(["."]);

        lib.add_source("trezor_api_v1_impl.c");

        lib.add_rust_bindings(|builder| {
            Ok(builder
                .header("trezor_api.h")
                .no_debug(".*")
                .no_copy(".*")
                .derive_default(true)
                .default_enum_style(EnumVariation::Rust {
                    non_exhaustive: false,
                })
                .raw_line("#![allow(non_snake_case)]")
                .raw_line("#![allow(non_camel_case_types)]")
                .raw_line("#![allow(non_upper_case_globals)]")
                .raw_line("#![allow(dead_code)]")
                .allowlist_type("trezor_api_v1_t")
                .allowlist_type("trezor_api_getter_t")
                .allowlist_type("sysevents_t")
                .allowlist_type("syshandle_mask_t")
                .allowlist_var("SYSHANDLE__IPC0"))
        })?;

        lib.set_rust_bindings_output(api_bindings_path()?);

        Ok(())
    })
}

fn api_bindings_path() -> Result<PathBuf> {
    let out_dir = xbuild::path_from_env("OUT_DIR")?;
    Ok(out_dir.join("../../../trezor-api.rs"))
}
