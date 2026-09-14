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
        // A CUSTOM build is PRESIGNED: it folds into an already-signed
        // firmware_root instead of cutting a new tree, so it must embed the
        // secmon that root was signed over -- the COMMITTED one. The secmon is
        // founder-bound even for custom (only the kernel+coreapp is unbound), so
        // its code_hash sits inside the signed custom leaf; a freshly built
        // secmon matches only by luck, and when it does not, the failure is a
        // fold mismatch at install rather than anything visible here.
        //
        // Which committed pair depends on the key set that signed the root, not
        // on the variant. The binary and its veneer object travel together: the
        // kernel links the veneer and secure-faults if the two drift.
        let (bin, api) = if cfg!(feature = "bootloader_devel") {
            ("secmon_DEV.bin", "secmon_api_DEV.o")
        } else {
            ("secmon.bin", "secmon_api.o")
        };
        lib.add_object(dir.join(api));
        lib.embed_binary(dir.join(bin), "secmon")?;
    } else if cfg!(feature = "bootloader_devel") {
        // Take the freshly-built secmon from Cargo's profile directory: a dev
        // release cuts its own tree, so the secmon it signs over is the one just
        // built.
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
