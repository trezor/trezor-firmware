use std::path::PathBuf;
use xbuild::Result;

fn main() -> Result<()> {
    xbuild::build(|lib| {
        lib.import_lib("io")?;

        lib.add_includes(["."]);

        lib.add_source("trezor_api_v1_impl.c");

        lib.add_rust_bindings(|builder| {
            Ok(builder
                .header("trezor_api.h")
                .allowlist_type("trezor_api_v1_t")
                .allowlist_type("trezor_api_getter_t")
                .allowlist_type("sysevents_t")
                .allowlist_type("syshandle_mask_t")
                .allowlist_var("SYS_HANDLE_IPC0")
                .allowlist_var("LOG_LEVEL_ERROR")
                .allowlist_var("LOG_LEVEL_WRN")
                .allowlist_var("LOG_LEVEL_INFO")
                .allowlist_var("LOG_LEVEL_DEBUG"))
        })?;

        lib.set_rust_bindings_output(api_bindings_path()?);

        Ok(())
    })
}

fn api_bindings_path() -> Result<PathBuf> {
    let out_dir = xbuild::path_from_env("OUT_DIR")?;
    Ok(out_dir.join("../../../trezor-api.rs"))
}
