use std::{env, path::PathBuf};

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

    if cfg!(feature = "bootloader_devel") {
        // Take the freshly-built secmon from the output directory. A CUSTOM
        // (unsafe_fw) firmware embeds the SAME dev secmon as the founder's other
        // variants, so its manifest secmon code_hash matches the founder-signed
        // custom leaf -- only the kernel+coreapp (app) is founder-unbound. (The
        // secmon SOURCE and the firmware VARIANT are independent axes: custom is
        // a manifest variant, not a different secmon. A third-party creator
        // building against an officially-released secmon uses the else branch.)
        let dir = PathBuf::from(env::var("OUT_DIR").unwrap()).join("../../..");
        lib.add_object(dir.join("secmon_api.o"));
        lib.embed_binary(dir.join("secmon.bin"), "secmon")?;
    } else {
        // Take officially released secmon
        lib.add_object(dir.join("secmon_api.o"));
        lib.embed_binary(dir.join("secmon.bin"), "secmon")?;
    }

    Ok(())
}
