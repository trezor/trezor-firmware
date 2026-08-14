//! Path/directory helpers shared across the other modules: locating the
//! calling project's cargo workspace, telling a workspace app apart from a
//! standalone one, and resolving the build/profile/artifact directories a
//! given [`BuildArgs`] invocation reads from or writes to.

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

/// Returns the cargo workspace root directory, or the project root if it's not in a workspace.
pub fn root_dir() -> Result<PathBuf> {
    let metadata = MetadataCommand::new()
        .no_deps()
        .exec()
        .context("Failed to read cargo metadata")?;

    Ok(metadata.workspace_root.into_std_path_buf())
}

/// Returns whether the calling project is a cargo workspace with multiple
/// app packages (like this repository's `sdk/apps`), as opposed to a
/// standalone single-package app repository consuming modular-xtask as a
/// path dependency.
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

/// Returns the metadata of the workspace package named `package_name`.
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

/// Returns the package name of a standalone (non-workspace) app. Fails if
/// the calling project is actually a workspace; see [`is_workspace`].
pub fn standalone_project_name() -> Result<String> {
    ensure!(
        !is_workspace()?,
        "Not a standalone project (multiple packages found in workspace)"
    );

    MetadataCommand::new()
        .no_deps()
        .exec()
        .context("Failed to read cargo metadata")?
        .packages
        .first()
        .map(|p| p.name.clone())
        .ok_or_else(|| anyhow!("Failed to determine standalone project name"))
}

/// Returns the directory where built artifacts for a specific model
/// should be stored.
pub fn artifacts_dir(model: Model, emulator: bool) -> Result<PathBuf> {
    let model_dir = format!("{}{}", model.model_id(), if emulator { "-emu" } else { "" });
    Ok(build_dir()?.join("artifacts").join(model_dir))
}

/// Updates the `artifacts/latest` symlink to point at `model_dir`, mirroring
/// core/embed/xtask's own `artifacts/latest` convenience symlink. Kept as a
/// separate directory per model/emulator combination (see `artifacts_dir`)
/// rather than merged like core/embed/xtask's, since the Merkle-proof and
/// RootPacket generation in `postbuild.rs` bundles every `.elf` found in a
/// single artifact directory into one ring -- firmware and emulator builds
/// (or builds for different models) must not land in the same directory.
pub fn update_latest_symlink(model_dir: &Path) -> Result<()> {
    let latest_symlink = model_dir
        .parent()
        .context("Failed to get artifact parent directory")?
        .join("latest");

    if latest_symlink.symlink_metadata().is_ok() {
        std::fs::remove_file(&latest_symlink).with_context(|| {
            format!(
                "Failed to remove existing symlink `{}`",
                latest_symlink.display()
            )
        })?;
    }

    std::os::unix::fs::symlink(model_dir, &latest_symlink).with_context(|| {
        format!(
            "Failed to create symlink `{}` -> `{}`",
            latest_symlink.display(),
            model_dir.display()
        )
    })?;

    Ok(())
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

/// Formats a [`std::process::Command`] as a shell-quoted string (program,
/// arguments, and any environment variables set on it) suitable for
/// printing to show the user the exact command being run.
///
/// ```
/// use modular_xtask::helpers::command_args_to_string;
/// use std::process::Command;
///
/// let mut cmd = Command::new("cargo");
/// cmd.env("RUSTFLAGS", "-C target-cpu=cortex-m33");
/// cmd.args(["build", "--release"]);
///
/// assert_eq!(
///     command_args_to_string(&cmd),
///     "RUSTFLAGS='-C target-cpu=cortex-m33' cargo build --release"
/// );
/// ```
pub fn command_args_to_string(cmd: &std::process::Command) -> String {
    let envs: Vec<_> = cmd
        .get_envs()
        .map(|(k, v)| {
            let key = k.to_string_lossy();
            let val = v
                .map(|v| {
                    let s = v.to_string_lossy();
                    // Always quote the value for shell compatibility
                    format!("'{}'", s.replace('\'', "'\\''"))
                })
                .unwrap_or_else(|| "''".to_string());
            format!("{}={}", key, val)
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

#[cfg(test)]
mod tests {
    use super::*;
    use std::process::Command;

    #[test]
    fn formats_program_and_args() {
        let mut cmd = Command::new("cargo");
        cmd.args(["build", "--release"]);
        assert_eq!(command_args_to_string(&cmd), "cargo build --release");
    }

    #[test]
    fn quotes_env_vars_and_places_them_before_the_command() {
        let mut cmd = Command::new("cargo");
        cmd.env("RUSTFLAGS", "-C target-cpu=cortex-m33");
        cmd.arg("build");
        assert_eq!(
            command_args_to_string(&cmd),
            "RUSTFLAGS='-C target-cpu=cortex-m33' cargo build"
        );
    }

    #[test]
    fn escapes_single_quotes_in_env_values() {
        let mut cmd = Command::new("sh");
        cmd.env("MSG", "it's here");
        assert_eq!(command_args_to_string(&cmd), r#"MSG='it'\''s here' sh"#);
    }

    #[test]
    fn no_env_vars_omits_the_leading_space() {
        let cmd = Command::new("ls");
        assert_eq!(command_args_to_string(&cmd), "ls");
    }
}
