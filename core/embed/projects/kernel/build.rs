use std::path::PathBuf;

use xbuild::{CLibrary, Result};

fn main() -> Result<()> {
    xbuild::build_and_link("kernel", |lib| {
        lib.import_lib("io")?;

        lib.add_source("main.c");

        lib.add_sources_in_dir(
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

    if cfg!(feature = "unsafe_fw") {
        // A CUSTOM build is presigned, so it must embed the committed secmon its
        // signed leaf covers. Which pair depends on the signing key set; the
        // binary and its veneer object must travel together.
        let (bin, api) = if cfg!(feature = "bootloader_devel") {
            ("secmon_DEV.bin", "secmon_api_DEV.o")
        } else {
            ("secmon.bin", "secmon_api.o")
        };
        lib.add_object(dir.join(api));
        lib.embed_binary(dir.join(bin), "secmon")?;
    } else if cfg!(feature = "bootloader_devel") {
        // Take the freshly-built secmon from Cargo's profile directory.
        let dir = xbuild::cargo_profile_dir()?;
        lib.add_object(dir.join("secmon_api.o"));
        lib.embed_binary(dir.join("secmon.bin"), "secmon")?;
    } else {
        // Take officially released secmon
        lib.add_object(dir.join("secmon_api.o"));
        lib.embed_binary(dir.join("secmon.bin"), "secmon")?;
    }

    Ok(())
}
