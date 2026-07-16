use std::{env, path::PathBuf};

use xbuild::{CLibrary, Result, bail_unsupported};

fn main() -> Result<()> {
    xbuild::build_and_link("firmware", |lib| {
        lib.import_lib("io")?;
        lib.import_lib("upymod")?;

        lib.add_includes(["."]);

        lib.add_include("../../rust"); // Cyclic dependency

        lib.add_sources(["main.c", "boot_image_embdata.c"]);

        // Firmware header: the Merkle-tree layout uses a module header (TRZM);
        // otherwise the legacy vendor header + image header.
        if cfg!(feature = "pq_secure_boot") {
            lib.add_source("module_header.S");
            // The firmware manifest ("firmware directory") at the image start.
            lib.add_source("manifest_header.S");
            // Stamp the authenticated firmware variant into the manifest. The
            // firmware variant is a binary axis (matches upymod's BITCOIN_ONLY
            // axis): the `universal_fw` feature => UNIVERSAL, its absence =>
            // BITCOIN_ONLY. The numeric values ARE fw_variant_t (sec/boot_header.h,
            // itself pinned to vendor_fw_type_t); a _Static_assert in main.c ties
            // these literals to the enum so the two cannot silently drift.
            let variant = if cfg!(feature = "universal_fw") {
                "2" // FW_VARIANT_UNIVERSAL
            } else {
                "3" // FW_VARIANT_BITCOIN_ONLY
            };
            lib.add_define("FW_VARIANT", Some(variant));
        } else {
            lib.add_source("header.S");
        }

        if cfg!(feature = "mcu_stm32") {
            lib.add_source("stm32/coreapp_header.S");
        } else {
            bail_unsupported!()
        }

        if cfg!(feature = "app_loading") {
            lib.add_source("../../api/trezor_api_v1_impl.c");
        }

        if cfg!(feature = "force_bootloader_upgrade") {
            lib.add_define("FORCE_BOOTLOADER_UPGRADE", Some("1"));
        }

        // The Merkle-tree layout has no legacy vendor header (the module header
        // replaces it). Other builds keep the vendor header.
        if !cfg!(feature = "pq_secure_boot") {
            lib.embed_binary(
                xbuild::vendor_header_path("../../models", "firmware")?,
                "vendorheader",
            )?;
        }

        // The Merkle-tree path does not bake the bootloader into the firmware
        // (it is installed separately via the boardloader/UCB mechanism).
        if !cfg!(feature = "pq_secure_boot") {
            embed_bootloader_binary(lib)?;
        }
        // In the Merkle-tree layout the secmon is a separate module, prefixed
        // before the module header (kernel.bin is code-only). It is excluded
        // from this module's hash but placed here so the kernel links correctly.
        if cfg!(feature = "pq_secure_boot") {
            // The prefixed secmon MUST be the exact same binary the kernel was
            // built against (see kernel/build.rs embed_secmon_binary) or the
            // kernel secure-faults, so mirror that selection here:
            //   - dev build: the freshly-built secmon (from source), so a normal
            //     dev build tracks the current secmon source;
            //   - dev + --unsafe-fw: the committed prebuilt dev secmon
            //     (secmon_DEV) -- a STABLE signed secmon the dev bundle's manifest
            //     commits -- so a custom build's kernel+coreapp can deviate while
            //     the secmon still conforms (and for compatibility testing);
            //   - release: the officially built secmon.
            let model_id = xbuild::current_model_id()?;
            let dir = PathBuf::from(format!("../../models/{}/secmon", model_id));
            if cfg!(feature = "bootloader_devel") {
                if cfg!(feature = "unsafe_fw") {
                    lib.embed_binary(dir.join("secmon_DEV.bin"), "secmon")?;
                } else {
                    let out_dir = PathBuf::from(env::var("OUT_DIR").unwrap());
                    lib.embed_binary(out_dir.join("../../../secmon.bin"), "secmon")?;
                }
            } else {
                lib.embed_binary(dir.join("secmon.bin"), "secmon")?;
            }
        }
        embed_kernel_binary(lib)?;

        if cfg!(feature = "nrf") {
            embed_nrf_app_binary(lib)?;
        }

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
