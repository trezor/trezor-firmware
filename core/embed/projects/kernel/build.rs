use std::{env, path::PathBuf};

use xbuild::{CLibrary, Result};

fn main() -> Result<()> {
    xbuild::build_and_link("kernel", |lib| {
        lib.import_lib("io")?;

        lib.add_source("main.c");

        lib.add_sources_from_folder(
            "../../sys/syscall/stm32",
            [
                "syscall_context.c",
                "syscall_dispatch.c",
                "syscall_ipc.c",
                "syscall_probe.c",
                "syscall_verifiers.c",
            ],
        );

        lib.embed_binary(
            xbuild::vendor_header_path("../../models", "kernel")?,
            "vendorheader",
        )?;

        if cfg!(feature = "secmon_layout") {
            embed_secmon_binary(lib)?;
        }

        Ok(())
    })
}

fn embed_secmon_binary(lib: &mut CLibrary) -> Result<()> {
    let model_id = xbuild::current_model_id()?;
    let dir = PathBuf::from(format!("../../models/{}/secmon", model_id));

    if cfg!(feature = "bootloader_devel") {
        if cfg!(feature = "unsafe_fw") {
            lib.add_object(&dir.join("secmon_api_DEV.o"));
            lib.embed_binary(&dir.join("secmon_DEV.bin"), "secmon")?;
        } else {
            // Take recently built secmon from the output directory
            let dir = PathBuf::from(env::var("OUT_DIR").unwrap()).join("../../..");
            lib.add_object(&dir.join("secmon_api.o"));
            lib.embed_binary(&dir.join("secmon.bin"), "secmon")?;
        }
    } else {
        // Take officially released secmon
        lib.add_object(&dir.join("secmon_api.o"));
        lib.embed_binary(&dir.join("secmon.bin"), "secmon")?;
    }

    Ok(())
}
