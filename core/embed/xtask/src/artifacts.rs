use anyhow::{Context, Result};
use std::{
    fs,
    path::{Path, PathBuf},
};

use crate::{args::BuildArgs, helpers};

/// Copies `src` to `dst` if `src` exists and is newer than `dst`.
fn copy_if_newer(src: &Path, dst: &Path) -> Result<bool> {
    if !src.exists() {
        return Ok(false);
    }

    if dst.exists() {
        let src_modified = src
            .metadata()
            .and_then(|m| m.modified())
            .context("Failed to read source mtime")?;
        let dst_modified = dst
            .metadata()
            .and_then(|m| m.modified())
            .context("Failed to read destination mtime")?;
        if src_modified <= dst_modified {
            return Ok(false);
        }
    }

    fs::copy(src, dst)
        .with_context(|| format!("Failed to copy `{}` -> `{}`", src.display(), dst.display()))?;
    Ok(true)
}

/// Collects build artifacts into `build-xtask/artifacts/{MODEL_ID}/`.
/// When `is_dependency` is true, the `.bin` file is skipped (only ELF, MAP,
/// and compile_commands are collected).
pub fn collect_artifacts(args: &BuildArgs, is_dependency: bool) -> Result<()> {
    let artifact_dir = helpers::build_dir()?
        .join("artifacts")
        .join(args.model.model_id());

    helpers::ensure_directory(&artifact_dir)?;

    let name = args.component.artifact_name(args.emulator);
    let binary_name = args.component.binary_name();
    let profile = helpers::profile_dir(args)?;
    let elf = helpers::elf_path(args)?;
    let package = args.component.package_name(args.emulator);
    let compile_commands = profile.join(format!("{package}.cc.json"));

    let elf_ext = if args.emulator { "" } else { ".elf" };

    let mut artifacts: Vec<(PathBuf, String)> = vec![
        (elf.clone(), format!("{name}{elf_ext}")),
        (compile_commands, format!("{name}.cc.json")),
    ];

    if !args.emulator {
        if !is_dependency {
            let ubin = elf.with_extension("ubin");
            let bin = elf.with_extension("bin");
            // Prefer .ubin (firmware on T2T1/T2B1), fall back to .bin
            let bin_src = if ubin.exists() { ubin } else { bin };

            artifacts.push((bin_src, format!("{name}.bin")));
        }
        artifacts.push((
            profile.join(format!("{binary_name}.map")),
            format!("{name}.map"),
        ));
    }

    for (src, dst_name) in &artifacts {
        let dst = artifact_dir.join(dst_name);
        copy_if_newer(src, &dst)?;
    }

    update_latest_symlink(&artifact_dir)?;

    Ok(())
}

fn update_latest_symlink(artifact_dir: &Path) -> Result<()> {
    let latest_symlink = artifact_dir
        .parent()
        .context("Failed to get artifact parent directory")?
        .join("latest");

    if latest_symlink.exists() {
        fs::remove_file(&latest_symlink).with_context(|| {
            format!(
                "Failed to remove existing symlink `{}`",
                latest_symlink.display()
            )
        })?;
    }

    std::os::unix::fs::symlink(artifact_dir, &latest_symlink).with_context(|| {
        format!(
            "Failed to create symlink `{}` -> `{}`",
            latest_symlink.display(),
            artifact_dir.display()
        )
    })?;

    Ok(())
}
