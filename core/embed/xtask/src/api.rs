use anyhow::{Context, bail, ensure};
use std::fs;
use tempfile::NamedTempFile;

use crate::{args::BuildArgs, cargo, helpers, model::Model};

const SUPPORTED_MODELS: &[Model] = &[Model::T3W1];
const BINDINGS_FILE: &str = "trezor-api.rs";

pub fn check_bindings() -> anyhow::Result<()> {
    println!("Checking API bindings...");

    for model in SUPPORTED_MODELS {
        let mut reference_file: Option<NamedTempFile> = None;

        for emulator in [true, false] {
            println!("Building for {:?} (emulator: {})...", model, emulator);

            let args = BuildArgs {
                project: crate::args::Project::Firmware,
                model: *model,
                emulator,
                apps: true,
                ..Default::default()
            };

            let profile_dir = helpers::profile_dir(&args)?;
            cargo::build(args)?;

            let bindings_path = profile_dir.join(BINDINGS_FILE);
            ensure!(
                bindings_path.exists(),
                "Expected bindings file not found at {:?}",
                bindings_path
            );

            match &reference_file {
                None => {
                    let tmp = NamedTempFile::new()
                        .context("Failed to create temporary reference file")?;
                    fs::copy(&bindings_path, tmp.path()).with_context(|| {
                        format!(
                            "Failed to copy bindings to temp file from {:?}",
                            bindings_path
                        )
                    })?;
                    reference_file = Some(tmp);
                }
                Some(reference) => {
                    let ref_content =
                        fs::read(reference.path()).context("Failed to read reference temp file")?;
                    let cur_content = fs::read(&bindings_path).with_context(|| {
                        format!("Failed to read bindings file at {:?}", bindings_path)
                    })?;
                    ensure!(
                        ref_content == cur_content,
                        "Bindings file for {:?} differs between emulator and non-emulator builds",
                        model
                    );
                }
            }
        }

        // Compare with the committed bindings in the SDK
        let sdk_bindings_path = helpers::workspace_dir()?
            .join("../../sdk/crates/trezor-app-sdk/src/low_level_api/ffi.rs");

        let generated_content = fs::read(reference_file.as_ref().unwrap().path())
            .context("Failed to read generated bindings temp file")?;

        ensure!(
            sdk_bindings_path.exists(),
            "SDK bindings file not found at {:?}",
            sdk_bindings_path
        );

        let sdk_content = fs::read(&sdk_bindings_path)
            .with_context(|| format!("Failed to read SDK bindings at {:?}", sdk_bindings_path))?;

        if generated_content != sdk_content {
            fs::write(&sdk_bindings_path, &generated_content).with_context(|| {
                format!("Failed to update SDK bindings at {:?}", sdk_bindings_path)
            })?;
            bail!(
                "SDK bindings for {:?} were outdated and have been updated at {:?}. \
                     Please commit the updated file.",
                model,
                sdk_bindings_path
            );
        }
    }

    println!("All API bindings are consistent and up to date.");
    Ok(())
}
