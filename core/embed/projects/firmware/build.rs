use std::{env, path::PathBuf};

use xbuild::{CLibrary, Result, bail_unsupported};

fn main() -> Result<()> {
    xbuild::build_and_link("firmware", |lib| {
        lib.import_lib("io")?;
        lib.import_lib("upymod")?;

        lib.add_includes(["."]);

        lib.add_include("../../rust"); // Cyclic dependency

        lib.add_sources(["main.c", "header.S", "boot_image_embdata.c"]);

        if cfg!(feature = "mcu_stm32") {
            lib.add_source("stm32/vectortable.S");
        } else {
            bail_unsupported!()
        }

        if cfg!(feature = "app_loading") {
            lib.add_source("../../api/trezor_api_v1_impl.c");
        }

        lib.embed_binary(
            xbuild::vendor_header_path("../../models", "firmware")?,
            "vendorheader",
        )?;

        embed_bootloader_binary(lib)?;
        embed_kernel_binary(lib)?;

        if cfg!(feature = "nrf") {
            embed_nrf_app_binary(lib)?;
        }

        // Do we need to shuffle the order of source files in obj_program?
        // TODO !@# random.Random(SCM_REVISION).shuffle(obj_program)

        Ok(())
    })
}

fn embed_kernel_binary(lib: &mut CLibrary) -> Result<()> {
    let out_dir = PathBuf::from(env::var("OUT_DIR").unwrap());
    let kernel = out_dir.join("../../../kernel.bin");
    lib.embed_binary(&kernel, "kernel")
}

fn embed_bootloader_binary(lib: &mut CLibrary) -> Result<()> {
    let model_id = xbuild::current_model_id()?;
    let model_dir = format!("../../models/{}", model_id);
    let suffix = if cfg!(feature = "bootloader_devel") || cfg!(feature = "bootloader_qa") {
        "_qa"
    } else {
        ""
    };

    let bootloader = format!("{model_dir}/bootloaders/bootloader_{model_id}{suffix}.bin");

    if cfg!(feature = "boot_ucb") {
        // embed uncompressed bootloader image
        lib.embed_binary(bootloader, "bootloader")?;
    } else {
        lib.embed_compressed_binary(bootloader, "bootloader")?;
    }

    if cfg!(feature = "bootloader_qa") {
        lib.add_define("BOOTLOADER_QA", Some("1"));
    }

    Ok(())
}

fn embed_nrf_app_binary(lib: &mut CLibrary) -> Result<()> {
    let model_id = xbuild::current_model_id()?;
    let model_dir = format!("../../models/{}", model_id);
    let suffix = if cfg!(feature = "bootloader_devel") {
        "-dev"
    } else {
        ""
    };
    let nrf_app = format!("{model_dir}/trezor-ble{suffix}.bin");
    lib.embed_binary(&nrf_app, "nrf_app")
}
