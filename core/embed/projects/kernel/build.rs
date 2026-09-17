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
    let prebuilt = PathBuf::from(format!("../../models/{}/secmon", model_id));
    // Fresh: the secmon built as this kernel's dependency, in Cargo's profile
    // directory.
    let fresh = xbuild::cargo_profile_dir()?;

    let (dir, bin, api) = if cfg!(feature = "prebuilt_secmon") {
        // A custom build folded into an already-signed release: its custom slot
        // commits to the secmon that release was signed over. The binary and its
        // veneer object travel together, per signing key set.
        if cfg!(feature = "bootloader_devel") {
            (prebuilt, "secmon_DEV.bin", "secmon_api_DEV.o")
        } else {
            (prebuilt, "secmon.bin", "secmon_api.o")
        }
    } else if cfg!(feature = "pq_secure_boot") {
        // A Merkle-tree release signs whatever secmon it embeds; use the one
        // it built.
        (fresh, "secmon.bin", "secmon_api.o")
    } else if cfg!(feature = "bootloader_devel") {
        if cfg!(feature = "unsafe_fw") {
            (prebuilt, "secmon_DEV.bin", "secmon_api_DEV.o")
        } else {
            // Take recently built secmon from Cargo's profile directory
            (fresh, "secmon.bin", "secmon_api.o")
        }
    } else {
        // Take officially released secmon
        (prebuilt, "secmon.bin", "secmon_api.o")
    };

    lib.add_object(dir.join(api));
    lib.embed_binary(dir.join(bin), "secmon")?;

    Ok(())
}
