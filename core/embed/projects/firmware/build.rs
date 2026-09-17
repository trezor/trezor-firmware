use std::path::PathBuf;

use xbuild::{CLibrary, Result, bail, bail_unsupported};

fn main() -> Result<()> {
    xbuild::build_and_link("firmware", |lib| {
        lib.import_lib("io")?;
        lib.import_lib("upymod")?;

        lib.add_include("../../rust"); // Cyclic dependency

        if cfg!(feature = "app_loading") {
            lib.add_source("../../api/trezor_api_v1_impl.c");
        }

        if cfg!(feature = "force_bootloader_upgrade") {
            if cfg!(feature = "pq_secure_boot") {
                // The tree layout compiles the firmware's bootloader updater out.
                bail!("force_bootloader_upgrade is not supported with pq_secure_boot");
            }
            lib.add_define("FORCE_BOOTLOADER_UPGRADE", Some("1"));
        }

        if cfg!(feature = "emulator") {
            lib.add_sources(["src/unix/main.c", "src/unix/main_main.c"]);
        } else if cfg!(feature = "mcu_stm32") {
            lib.add_sources(["src/stm32/main.c", "src/stm32/coreapp_header.S"]);

            // Merkle-tree layout: a manifest at the image start; otherwise the
            // legacy vendor + image header.
            if cfg!(feature = "pq_secure_boot") {
                lib.add_source("src/stm32/manifest_header.S");
                // Authenticated variant stamped into the manifest. Must be a
                // hardened FW_VARIANT_SEC_* codeword (sec/boot_header.h);
                // static-asserted in main.c. `unsafe_fw` builds CUSTOM.
                let variant = if cfg!(feature = "unsafe_fw") {
                    "0x33333333" // FW_VARIANT_SEC_CUSTOM
                } else if cfg!(feature = "universal_fw") {
                    "0x5A5A5A5A" // FW_VARIANT_SEC_UNIVERSAL
                } else {
                    "0xA5A5A5A5" // FW_VARIANT_SEC_BITCOIN_ONLY
                };
                lib.add_define("FW_VARIANT", Some(variant));
            } else {
                lib.add_source("src/stm32/header.S");
            }

            // No legacy vendor header in the Merkle-tree layout, and the
            // bootloader is installed through the UCB rather than carried by the
            // firmware -- so neither the image nor the code to install it.
            if !cfg!(feature = "pq_secure_boot") {
                lib.embed_binary(
                    xbuild::vendor_header_path("../../models", "firmware")?,
                    "vendorheader",
                )?;
                lib.add_source("src/stm32/boot_image_embdata.c");
                embed_bootloader_binary(lib)?;
            }

            // Merkle-tree layout: the secmon module is prefixed so the kernel
            // links at its run address. It must be the exact binary the kernel
            // was built against (mirror kernel/build.rs embed_secmon_binary) or
            // the kernel secure-faults.
            if cfg!(feature = "pq_secure_boot") {
                let model_id = xbuild::current_model_id()?;
                let dir = PathBuf::from(format!("../../models/{}/secmon", model_id));
                if cfg!(feature = "unsafe_fw") {
                    let bin = if cfg!(feature = "bootloader_devel") {
                        "secmon_DEV.bin"
                    } else {
                        "secmon.bin"
                    };
                    lib.embed_binary(dir.join(bin), "secmon")?;
                } else if cfg!(feature = "bootloader_devel") {
                    let out_dir = xbuild::cargo_profile_dir()?;
                    lib.embed_binary(out_dir.join("secmon.bin"), "secmon")?;
                } else {
                    lib.embed_binary(dir.join("secmon.bin"), "secmon")?;
                }
            }

            embed_kernel_binary(lib)?;

            // Legacy layout only: under the Merkle-tree scheme the bootloader
            // installs the nRF.
            if cfg!(feature = "nrf") && !cfg!(feature = "pq_secure_boot") {
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
    // The bare nordic build output; the signed image beside it is a pq_secure
    // promote artifact.
    let nrf_app = format!("{model_dir}/trezor-ble{suffix}-bare.bin");
    lib.embed_binary(&nrf_app, "nrf_app")
}
