//! Trezor-specific build helpers.
//!
//! This module contains functions that are specific to the Trezor firmware
//! project: model detection, vendor header resolution, linker script
//! selection, and the top-level `build_and_link()` entry point that ties
//! them together.

use std::{
    env, fs,
    path::{Path, PathBuf},
};

use color_eyre::{
    Result,
    eyre::{WrapErr, bail},
};

use crate::CLibrary;
use crate::helpers::{is_rust_analyzer, links_name};

fn package_name() -> Result<String> {
    Ok(env::var("CARGO_PKG_NAME")?)
}

/// Returns the current model id (T2T1, ..) from the DEP_MODELS_MODEL
/// environment variable emitted by the `models` crate's build script.
///
/// The variable is empty when no model feature is selected; that is treated as
/// an error since callers need a concrete model.
pub fn current_model_id() -> Result<String> {
    let model = env::var("DEP_MODELS_MODEL").unwrap_or_default();
    if model.is_empty() {
        bail!(
            "DEP_MODELS_MODEL is unset or empty — is `models` a direct dependency with a model feature selected?"
        );
    }
    Ok(model)
}

/// Returns the sorted list of model ids found in `models_dir` — the names of
/// subdirectories that contain a `model.toml`. Emits `rerun-if-changed` for the
/// directory and each `model.toml` so callers rebuild when the model set changes.
pub fn model_ids(models_dir: &Path) -> Result<Vec<String>> {
    println!("cargo::rerun-if-changed={}", models_dir.display());
    let mut models = Vec::new();
    for entry in fs::read_dir(models_dir).context("Failed to read models directory")? {
        let entry = entry?;
        let model_toml = entry.path().join("model.toml");
        if !model_toml.exists() {
            continue;
        }
        println!("cargo::rerun-if-changed={}", model_toml.display());
        models.push(entry.file_name().to_string_lossy().into_owned());
    }
    models.sort();
    Ok(models)
}

/// Returns the path to the vendor header binary for the given build target.
///
/// The vendor is selected based on the build configuration (production,
/// development, QA) and the target type (prodtest vs everything else).
pub fn vendor_header_path(models_dir: impl AsRef<Path>, target: &str) -> Result<PathBuf> {
    if let Ok(vendor_header) = env::var("VENDOR_HEADER")
        && !vendor_header.is_empty()
    {
        println!("cargo:warning=Using custom vendor header: {vendor_header}");
        return Ok(PathBuf::from(vendor_header));
    }

    let vendor = if target == "prodtest" {
        get_prodtest_vendor()?
    } else {
        // firmware, secmon and kernel all must use the same vendor header
        get_firmware_vendor()?
    };

    Ok(models_dir
        .as_ref()
        .join(current_model_id()?)
        .join("vendorheader")
        .join(format!("vendorheader_{}.bin", vendor)))
}

fn is_bitcoin_only() -> bool {
    !has_feature("universal_fw")
}

fn get_firmware_vendor() -> Result<&'static str> {
    Ok(if has_feature("bootloader_devel") {
        if has_feature("unsafe_fw") {
            "unsafe_signed_dev"
        } else {
            "dev_DO_NOT_SIGN_signed_dev"
        }
    } else if !has_feature("production") {
        "unsafe_signed_prod"
    } else if current_model_id()? == "T2T1" {
        "satoshilabs_signed_prod"
    } else if is_bitcoin_only() {
        "trezor_btconly_signed_prod"
    } else {
        "trezor_signed_prod"
    })
}

fn get_prodtest_vendor() -> Result<&'static str> {
    Ok(if has_feature("bootloader_devel") {
        "prodtest_DO_NOT_SIGN_signed_dev"
    } else if has_feature("production") {
        "prodtest_signed_prod"
    } else {
        "unsafe_signed_prod"
    })
}

/// Entry point for build scripts that compile C libraries.
///
/// Creates a [`CLibrary`], passes it to the provided closure,
/// then compiles the library. Also installs the error reporting handler.
pub fn build(f: impl FnOnce(&mut CLibrary) -> Result<()>) -> Result<()> {
    color_eyre::install()?;

    let mut lib = CLibrary::new();
    configure_compiler_defaults(&mut lib);

    f(&mut lib)?;

    lib.generate_rust_bindings(!has_feature("emulator"))?;
    lib.export_library_metadata()?;

    if !is_rust_analyzer() {
        lib.compile()?;
        lib.generate_compile_commands()?;

        // Building test binary?
        if has_feature("test") {
            lib.link_as("firmware")?;
        }
    }

    Ok(())
}

/// Entry point for build scripts that compile and link a top-level binary.
///
/// Creates a [`CLibrary`], passes it to the provided closure,
/// compiles the library, and links it as the specified binary type.
pub fn build_and_link(target: &str, f: impl FnOnce(&mut CLibrary) -> Result<()>) -> Result<()> {
    color_eyre::install()?;

    let mut lib = CLibrary::new();
    configure_compiler_defaults(&mut lib);

    f(&mut lib)?;

    lib.generate_rust_bindings(!has_feature("emulator"))?;
    lib.export_library_metadata()?;

    if !is_rust_analyzer() {
        lib.compile()?;
        lib.generate_compile_commands()?;
        lib.merge_compile_commands()?;
    }

    lib.link_as(target)?;

    Ok(())
}

fn configure_compiler_defaults(lib: &mut CLibrary) {
    if !has_feature("emulator") {
        // Override the default `-fno-omit-frame-pointer` from the `cc` crate
        // which causes binary size to increase on embedded targets.
        lib.add_private_flag("-fomit-frame-pointer");
    }
}

impl CLibrary {
    fn link_as(&self, binary_type: &str) -> Result<()> {
        let this_lib = links_name()?;
        let package_name = package_name()?;

        // `+whole-archive` forces the linker to include all object files
        // from the specified archive, even if they are not referenced by
        // any other object file. This is necessary for linking symbols that
        // are not referenced but expected to be present at runtime
        // (e.g., image headers, PRODTEST_CLI_CMD() handlers ).
        //
        // `+whole-archive` also helps with cyclic dependencies,
        // that we have between `upymod`, `rtl` and `sys` crates.
        // Using `rustc-link-lib` keeps the whole-archive selection scoped
        // to each archive instead of toggling global linker state.
        std::iter::once(this_lib.as_str())
            .chain(self.get_libs())
            .for_each(|dep| println!("cargo:rustc-link-lib=static:+whole-archive={dep}"));

        self.get_external_libs()
            .into_iter()
            .for_each(|dep| println!("cargo:rustc-link-arg=-l{dep}"));

        if has_feature("emulator") {
            println!("cargo:rustc-link-lib=c");
            println!("cargo:rustc-link-lib=m");
            println!("cargo:rustc-link-lib=dl");
            println!("cargo:rustc-link-lib=pthread");
        } else {
            println!("cargo:rustc-link-arg=-lm");
            println!("cargo:rustc-link-arg=-lgcc");
            println!("cargo:rustc-link-arg=-lc_nano");

            // Include the linker script that defines memory layout constants
            // according to the current model.
            let memory_ld = {
                let suffix = if has_feature("secmon_layout") {
                    "_secmon"
                } else {
                    ""
                };

                let model_id = current_model_id()?;
                format!("models/{model_id}/memory{suffix}.ld")
            };

            println!("cargo:rustc-link-arg=-T{memory_ld}");
            println!("cargo:rerun-if-changed={memory_ld}");

            // Include the linker script that defines the layout of the
            // final binary according to the selected binary type. The
            // Merkle-tree layout (pq_secure_boot feature) uses a separate
            // `{binary_type}_pq.ld` variant so the legacy layout is preserved.
            // Only the modules whose layout changes have a _pq variant; the
            // bootloader keeps its layout (it only gains verification code).
            let ld_suffix = if has_feature("pq_secure_boot")
                && matches!(binary_type, "firmware" | "secmon" | "kernel" | "prodtest")
            {
                "_pq"
            } else {
                ""
            };
            let target_ld = if has_feature("mcu_stm32u5g") {
                format!("sys/linker/stm32u5g/{binary_type}{ld_suffix}.ld")
            } else if has_feature("mcu_stm32u5a") {
                format!("sys/linker/stm32u5a/{binary_type}.ld")
            } else if has_feature("mcu_stm32u58") {
                format!("sys/linker/stm32u58/{binary_type}.ld")
            } else if has_feature("mcu_stm32f4") {
                format!("sys/linker/stm32f4/{binary_type}.ld")
            } else {
                bail!("Unsupported configuration");
            };

            println!("cargo:rustc-link-arg=-T{target_ld}");
            println!("cargo:rerun-if-changed={target_ld}");

            // Generate a map file for the final binary in the same directory
            // as the final binary.
            let out_dir = PathBuf::from(env::var("OUT_DIR").unwrap());
            let map_file = out_dir.join(format!("../../../{package_name}.map"));
            println!("cargo:rustc-link-arg=-Wl,-Map={}", map_file.display());

            // Instruct the linker to perform garbage collection of
            // unused sections to minimize the final binary size.
            println!("cargo:rustc-link-arg=-Wl,--gc-sections");

            println!("cargo:rustc-link-arg=-nostdlib");

            if binary_type == "secmon" {
                // Generate an import library for the CMSE veneer functions
                // in the same directory as the final binary. The Kernel will link
                // against this import library to call the secure monitor API.

                let implib_file = out_dir.join("../../../secmon_api.o");
                println!("cargo:rustc-link-arg=-Wl,-cmse-implib");
                println!(
                    "cargo:rustc-link-arg=-Wl,--out-implib={}",
                    implib_file.display()
                );
            }
        }

        Ok(())
    }
}

// Checks if the given feature is enabled in the current build.
// This is done by checking for the presence of an environment variable
// named `CARGO_FEATURE_<FEATURE_NAME>`, where `<FEATURE_NAME>` is the
// uppercase version of the feature name with non-alphanumeric characters
// replaced by underscores.
fn has_feature(feature: &str) -> bool {
    let env_name = format!("CARGO_FEATURE_{}", feature_to_env_name(feature));
    env::var_os(env_name).is_some()
}

// Converts a feature name to the corresponding environment variable name.
fn feature_to_env_name(feature: &str) -> String {
    feature
        .chars()
        .map(|ch| {
            if ch.is_ascii_alphanumeric() {
                ch.to_ascii_uppercase()
            } else {
                '_'
            }
        })
        .collect()
}
