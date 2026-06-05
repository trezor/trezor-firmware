use anyhow::{Context, Result};
use std::fs;

use crate::{
    args::{CombineArgs, Model, Project},
    helpers, postbuild,
};

const COMBINED_PREFIX: &str = "combined-";

fn load_binary(model: Model, project: Project) -> Result<Vec<u8>> {
    let path = helpers::artifacts_dir(model)?.join(format!("{}.bin", project.binary_name()));
    println!("Loading `{}`", path.display());
    let data = fs::read(&path)
        .with_context(|| format!("Failed to read binary file `{}`", path.display()))?;
    Ok(data)
}

/// Combines multiple firmware projects into a single binary for flashing.
pub fn combine(args: CombineArgs) -> Result<()> {
    let memory_ld = args.model.model_memory_ld()?;

    // Calculate the offset of boardloader from the start of flash
    let flash_start = helpers::read_symbol(&memory_ld, "FLASH_START")?;
    let boardloader_start = helpers::read_symbol(&memory_ld, "BOARDLOADER_START")?;
    let offset = boardloader_start - flash_start;

    // Create an binary with leading offset zeroes
    let mut binary = vec![0u8; offset as usize];

    binary.extend_from_slice(&load_binary(args.model, Project::Boardloader)?);

    match args.project {
        Project::Bootloader => {
            binary.extend_from_slice(&load_binary(args.model, Project::Bootloader)?);
        }

        Project::BootloaderCi => {
            binary.extend_from_slice(&load_binary(args.model, Project::BootloaderCi)?);
        }

        Project::Firmware => {
            binary.extend_from_slice(&load_binary(args.model, Project::Bootloader)?);
            binary.extend_from_slice(&load_binary(args.model, Project::Firmware)?);
        }

        Project::Prodtest => {
            binary.extend_from_slice(&load_binary(args.model, Project::Bootloader)?);
            binary.extend_from_slice(&load_binary(args.model, Project::Prodtest)?);
        }

        _ => anyhow::bail!(
            "Combining is not supported for `{}`",
            args.project.binary_name()
        ),
    }

    // Save the combined binary to the artifacts directory
    let artifact_dir = helpers::artifacts_dir(args.model)?;
    helpers::ensure_directory(&artifact_dir)?;

    let output_path = artifact_dir.join(format!(
        "{}{}.bin",
        COMBINED_PREFIX,
        args.project.binary_name()
    ));
    println!("Writing combined binary to `{}`", output_path.display());
    fs::write(&output_path, &binary).with_context(|| {
        format!(
            "Failed to write combined binary to `{}`",
            output_path.display()
        )
    })?;

    // Publish the combined binary to the `pub` directory
    let version_file = helpers::get_version_file(args.project)?;
    postbuild::publish_artifact(
        &output_path,
        args.project,
        args.model,
        &version_file,
        Some(COMBINED_PREFIX),
    )?;

    Ok(())
}
