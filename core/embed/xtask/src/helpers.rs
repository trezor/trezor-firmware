use anyhow::{Context, Result};
use cargo_metadata::MetadataCommand;
use std::{
    env,
    path::{Path, PathBuf},
};

use crate::args::{BuildArgs, Model};

pub fn elf_path(args: &BuildArgs) -> Result<PathBuf> {
    let elf_name = args.component.package_name(args.emulator);
    Ok(profile_dir(args)?.join(elf_name))
}

/// Returns the profile output directory (e.g. `target/thumbv7em-none-eabihf/release`).
pub fn profile_dir(args: &BuildArgs) -> Result<PathBuf> {
    let mut path = target_dir()?;
    if !args.emulator {
        path = path.join(args.model.target_triple());
    }

    let is_release = !args.debug.unwrap_or(args.emulator);
    let profile_dir = if is_release { "release" } else { "debug" };

    Ok(path.join(profile_dir))
}

pub fn target_dir() -> Result<PathBuf> {
    let metadata = MetadataCommand::new()
        .no_deps()
        .exec()
        .context("Failed to read cargo metadata")?;

    Ok(metadata.target_directory.into_std_path_buf())
}

pub fn workspace_dir() -> Result<PathBuf> {
    let path = Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .context("Unable to resolve workspace root")?
        .to_path_buf();
    Ok(path)
}

pub fn artifacts_dir(model: Model) -> Result<PathBuf> {
    Ok(target_dir()?.join("artifacts").join(model.model_id()))
}

/*pub fn model_dir(model: Model) -> Result<PathBuf> {
    Ok(workspace_dir()?
        .join("embed")
        .join("models")
        .join(model.model_id()))
}*/
