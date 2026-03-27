use crate::args::BuildArgs;
use anyhow::{Context, Result};
use cargo_metadata::MetadataCommand;
use std::env;
use std::path::PathBuf;

pub fn elf_path(args: &BuildArgs) -> Result<PathBuf> {
    let mut path = target_dir()?;
    if !args.emulator {
        path = path.join(args.model.target_triple());
    }

    let is_release = !args.debug.unwrap_or(args.emulator);
    let profile_dir = if is_release { "release" } else { "debug" };
    let elf_name = args.component.package_name(args.emulator);

    Ok(path.join(profile_dir).join(elf_name))
}

pub fn target_dir() -> Result<PathBuf> {
    let metadata = MetadataCommand::new()
        .no_deps()
        .exec()
        .context("Failed to read cargo metadata")?;

    Ok(metadata.target_directory.into_std_path_buf())
}

pub fn workspace_dir() -> Result<PathBuf> {
    let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .context("Unable to resolve workspace root")?
        .to_path_buf();
    Ok(path)
}
