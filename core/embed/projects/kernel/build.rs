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
    let out_dir = PathBuf::from(env::var("OUT_DIR").unwrap());

    let secmon_api = out_dir.join("../../../secmon_api.o");
    lib.add_object(secmon_api);

    let secmon_bin = out_dir.join("../../../secmon.bin");
    lib.embed_binary(&secmon_bin, "secmon")
}
