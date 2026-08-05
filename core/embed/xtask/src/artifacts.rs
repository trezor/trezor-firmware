use std::fs;
use std::os::unix;
use std::path::{Path, PathBuf};

use anyhow::{Context, Result};

use crate::helpers;
use crate::options::ResolvedBuildArgs;

/// Returns whether a filesystem entry exists without following symlinks, so
/// broken symlinks are still treated as present and can be replaced.
fn path_entry_exists(path: &Path) -> Result<bool> {
    match fs::symlink_metadata(path) {
        Ok(_) => Ok(true),
        Err(err) if err.kind() == std::io::ErrorKind::NotFound => Ok(false),
        Err(err) => {
            Err(err).with_context(|| format!("Failed to read metadata for `{}`", path.display()))
        }
    }
}

/// Copies `src` to `dst` if `src` exists and is newer than `dst`.
fn copy_if_newer(src: &Path, dst: &Path) -> Result<bool> {
    if !path_entry_exists(src)? {
        return Ok(false);
    }

    if src.symlink_metadata()?.file_type().is_symlink() {
        let target = fs::read_link(src)?;
        if path_entry_exists(dst)? {
            fs::remove_file(dst).with_context(|| {
                format!("Failed to remove existing symlink `{}`", dst.display())
            })?;
        }
        unix::fs::symlink(&target, dst).with_context(|| {
            format!(
                "Failed to create symlink `{}` -> `{}`",
                dst.display(),
                target.display()
            )
        })?;
        return Ok(true);
    }

    if path_entry_exists(dst)? {
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
pub fn collect_artifacts(args: &ResolvedBuildArgs, is_dependency: bool) -> Result<()> {
    let artifact_dir = helpers::build_dir()?
        .join("artifacts")
        .join(args.model.model_id());

    helpers::ensure_directory(&artifact_dir)?;

    let name = args.project.artifact_name(args.emulator);
    let binary_name = args.project.binary_name();
    let profile_dir = helpers::profile_dir(args)?;
    let elf = helpers::elf_path(args)?;
    let package = args.project.package_name(args.emulator);
    let compile_commands = profile_dir.join(format!("{package}.cc.json"));

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
            profile_dir.join(format!("{binary_name}.map")),
            format!("{name}.map"),
        ));
    } else {
        let mpy_files = "mpy-files";
        artifacts.push((profile_dir.join(mpy_files), mpy_files.to_string()));
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

    if path_entry_exists(&latest_symlink)? {
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
