use xbuild::{CLibrary, Result, bail_unsupported};

fn main() -> Result<()> {
    xbuild::build_and_link("firmware", |lib| {
        lib.import_lib("io")?;
        lib.import_lib("upymod")?;

        lib.add_include("../../rust"); // Cyclic dependency

        if cfg!(feature = "app_loading") {
            lib.add_source("../../api/trezor_api_v1_impl.c");
        }

        if cfg!(feature = "force_bootloader_upgrade") {
            lib.add_define("FORCE_BOOTLOADER_UPGRADE", Some("1"));
        }

        if cfg!(feature = "emulator") {
            lib.add_sources(["src/unix/main.c", "src/unix/main_main.c"]);
        } else if cfg!(feature = "mcu_stm32") {
            lib.add_sources([
                "src/stm32/main.c",
                "src/stm32/header.S",
                "src/stm32/boot_image_embdata.c",
                "src/stm32/coreapp_header.S",
            ]);

            lib.embed_binary(
                xbuild::vendor_header_path("../../models", "firmware")?,
                "vendorheader",
            )?;

            embed_bootloader_binary(lib)?;
            embed_kernel_binary(lib)?;

            if cfg!(feature = "nrf") {
                embed_nrf_app_binary(lib)?;
            }
        } else {
            bail_unsupported!()
        }

        Ok(())
    })
}

fn embed_kernel_binary(lib: &mut CLibrary) -> Result<()> {
    let kernel = xbuild::cargo_profile_dir()?.join("kernel.bin");
    lib.embed_binary(&kernel, "kernel")
}

fn embed_bootloader_binary(lib: &mut CLibrary) -> Result<()> {
    let model_id = xbuild::current_model_id()?;
    let model_dir = format!("../../models/{}", model_id);
    let suffix = if cfg!(feature = "bootloader_devel") {
        "_devel"
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
