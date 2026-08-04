use anyhow::{Context, Result, anyhow, ensure};
use cargo_metadata::{MetadataCommand, Package};
use std::path::{Path, PathBuf};

use crate::args::{BuildArgs, Model};

/// Returns the path to the built ELF file for the given build arguments.
pub fn elf_path(args: &BuildArgs) -> Result<PathBuf> {
    let elf_name = if is_workspace()? {
        args.project.clone()
    } else {
        standalone_project_name()?
    };

    Ok(profile_dir(args)?.join(elf_name))
}

/// Returns the profile output directory (e.g. `build/thumbv7em-none-eabihf/release`).
pub fn profile_dir(args: &BuildArgs) -> Result<PathBuf> {
    let mut path = build_dir()?;
    if !args.emulator {
        path = path.join(args.model.target_triple());
    }

    let profile_dir = if args.debug { "debug-fw" } else { "release-fw" };

    Ok(path.join(profile_dir))
}

/// Returns the directory where Cargo build artifacts are stored
pub fn build_dir() -> Result<PathBuf> {
    let metadata = MetadataCommand::new()
        .no_deps()
        .exec()
        .context("Failed to read cargo metadata")?;

    Ok(metadata.target_directory.into_std_path_buf())
}

// Returns the cargo workspace root directory or the project root if it's not in a workspace.
pub fn root_dir() -> Result<PathBuf> {
    let metadata = MetadataCommand::new()
        .no_deps()
        .exec()
        .context("Failed to read cargo metadata")?;

    Ok(metadata.workspace_root.into_std_path_buf())
}

pub fn is_workspace() -> Result<bool> {
    let metadata = MetadataCommand::new()
        .no_deps()
        .exec()
        .context("Failed to read cargo metadata")?;

    let workspace_root = metadata.workspace_root.as_std_path();
    let packages = metadata.packages;

    if packages.len() == 1
        && packages[0].manifest_path.as_std_path().parent() == Some(workspace_root)
    {
        // If there's only one package, treat it as a non-workspace project
        Ok(false)
    } else {
        Ok(true)
    }
}

pub fn app_package(package_name: &str) -> Result<Package> {
    let metadata = MetadataCommand::new()
        .no_deps()
        .exec()
        .context("Failed to read cargo metadata")?;

    // Find the package with the specified name
    metadata
        .packages
        .into_iter()
        .find(|p| p.name == package_name)
        .ok_or_else(|| anyhow!("Package '{}' not found in the workspace", package_name))
}

pub fn standalone_project_name() -> Result<String> {
    ensure!(
        !is_workspace()?,
        "Not a standalone project (multiple packages found in workspace)"
    );

    Ok(MetadataCommand::new()
        .no_deps()
        .exec()
        .context("Failed to read cargo metadata")?
        .packages
        .get(0)
        .map(|p| p.name.clone())
        .ok_or_else(|| anyhow!("Failed to determine standalone project name"))?)
}

/// Returns the directory where built artifacts for a specific model
/// should be stored.
pub fn artifacts_dir(model: Model, emulator: bool) -> Result<PathBuf> {
    let model_dir = format!("{}{}", model.model_id(), if emulator { "-emu" } else { "" });
    Ok(build_dir()?.join("artifacts").join(model_dir))
}

/// Checks if the given directory exists, and creates it if it doesn't.
pub fn ensure_directory(path: &Path) -> Result<()> {
    std::fs::create_dir_all(path)
        .with_context(|| format!("Failed to create directory {}", path.display()))?;
    Ok(())
}

/// Returns the current Git revision hash.
pub fn git_revision() -> Result<String> {
    let output = std::process::Command::new("git")
        .args(["rev-parse", "HEAD"])
        .output()
        .context("Failed to execute git command")?;

    if !output.status.success() {
        return Err(anyhow::anyhow!(
            "Git command failed with status {}",
            output.status
        ));
    }

    let hash = String::from_utf8(output.stdout)?.trim().to_string();
    Ok(hash)
}

/// Returns true if there are uncommitted changes in the Git repository.
pub fn git_modified() -> Result<bool> {
    let output = std::process::Command::new("git")
        .args(["diff", "--name-status"])
        .output()
        .context("Failed to execute git command")?;

    if !output.status.success() {
        return Err(anyhow::anyhow!(
            "Git command failed with status {}",
            output.status
        ));
    }

    let modified = !output.stdout.is_empty();
    Ok(modified)
}

pub fn command_args_to_string(cmd: &std::process::Command) -> String {
    let envs: Vec<_> = cmd
        .get_envs()
        .filter_map(|(k, v)| {
            let key = k.to_string_lossy();
            let val = v
                .map(|v| {
                    let s = v.to_string_lossy();
                    // Always quote the value for shell compatibility
                    format!("'{}'", s.replace('\'', "'\\''"))
                })
                .unwrap_or_else(|| "''".to_string());
            Some(format!("{}={}", key, val))
        })
        .collect();

    let mut parts = vec![cmd.get_program().to_string_lossy().into_owned()];
    parts.extend(cmd.get_args().map(|arg| arg.to_string_lossy().into_owned()));

    if !envs.is_empty() {
        format!("{} {}", envs.join(" "), parts.join(" "))
    } else {
        parts.join(" ")
    }
}
