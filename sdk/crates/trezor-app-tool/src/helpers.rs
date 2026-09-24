//! Path/directory helpers shared across the other modules: locating the
//! calling project's cargo workspace, telling a workspace app apart from a
//! standalone one, and resolving the build/profile/artifact directories a
//! given [`BuildArgs`] invocation reads from or writes to.

use anyhow::{Context, Result, anyhow, ensure};
use cargo_metadata::{MetadataCommand, Package};
use std::path::{Path, PathBuf};

use crate::args::{BuildArgs, Language, Model, TargetArch};

/// Returns the [`TargetArch`] of the emulator built on the current host,
/// or an error if the host OS/CPU combination is not supported.
pub fn emulator_target_arch() -> Result<TargetArch> {
    if cfg!(all(target_os = "linux", target_arch = "x86_64")) {
        Ok(TargetArch::LinuxX86_64)
    } else if cfg!(all(target_os = "macos", target_arch = "aarch64")) {
        Ok(TargetArch::MacosAarch64)
    } else {
        Err(anyhow!(
            "Unsupported emulator host: {}-{}",
            std::env::consts::OS,
            std::env::consts::ARCH
        ))
    }
}

/// Resolves the architecture a build targets from the model, an explicit
/// `--arch`, and the emulator flag. An unspecified emulator architecture
/// defaults to the current host; an unspecified firmware architecture
/// defaults to the model's, so a firmware build needs at least one of
/// `--model`/`--arch`. Fails when the given architecture does not match
/// the emulator flag or the model.
pub fn resolve_target_arch(
    model: Option<Model>,
    target_arch: Option<TargetArch>,
    emulator: bool,
) -> Result<TargetArch> {
    let arch = match target_arch {
        Some(arch) => arch,
        None if emulator => emulator_target_arch()?,
        None => model
            .ok_or_else(|| anyhow!("Either --model or --arch must be specified"))?
            .target_arch(),
    };

    ensure!(
        arch.is_emulator() == emulator,
        "Architecture '{}' is {} an emulator architecture",
        arch.name(),
        if emulator { "not" } else { "only" }
    );

    if !emulator {
        if let Some(model) = model {
            ensure!(
                model.target_arch() == arch,
                "Model '{}' requires architecture '{}', not '{}'",
                model.model_id(),
                model.target_arch().name(),
                arch.name()
            );
        }
    }

    Ok(arch)
}

// Returns the artifact name (file name with extension) for the given package, language, model,
// target architecture, and emulator flag.
pub fn artifact_name(
    package: &Package,
    language: Language,
    model: Option<Model>,
    target_arch: Option<TargetArch>,
    emulator: bool,
) -> Result<String> {
    let app_id = package
        .metadata
        .get("trezor")
        .and_then(|metadata| metadata.get("id"))
        .and_then(|id| id.as_str())
        .ok_or_else(|| anyhow!("id not found in Cargo.toml"))?;
    let arch = resolve_target_arch(model, target_arch, emulator)?;

    Ok(format!(
        "{}-{}-{}-{}-{}",
        app_id,
        package.version,
        language.name(),
        model.map_or("all", Model::model_id),
        arch.name(),
    ))
}

/// Returns the path to the built ELF file of `package` for the given build arguments.
pub fn elf_path(args: &BuildArgs, package: &Package) -> Result<PathBuf> {
    Ok(profile_dir(args)?.join(&package.name))
}

/// Returns the profile output directory (e.g. `build/thumbv7em-none-eabihf/release`).
pub fn profile_dir(args: &BuildArgs) -> Result<PathBuf> {
    let mut path = build_dir()?;
    if let Some(target_triple) = args.target_triple() {
        path = path.join(target_triple);
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

/// Returns the directory containing `package`'s manifest.
pub fn package_dir(package: &Package) -> Result<&Path> {
    package
        .manifest_path
        .parent()
        .with_context(|| format!("Failed to resolve package directory of '{}'", package.name))
        .map(|path| path.as_std_path())
}

/// Returns the app packages selected by `names`, or every app package in
/// the workspace when `names` is empty. A standalone app is a one-member
/// workspace to cargo, so it needs no `-p` either way. Only packages with a
/// `[package.metadata.trezor]` table count as apps, so a shared library
/// crate added to the workspace is never treated as one.
pub fn selected_packages(names: &[String]) -> Result<Vec<Package>> {
    let metadata = MetadataCommand::new()
        .no_deps()
        .exec()
        .context("Failed to read cargo metadata")?;

    let members = metadata.workspace_packages();

    if names.is_empty() {
        let apps: Vec<Package> = members
            .into_iter()
            .filter(|p| p.metadata.get("trezor").is_some())
            .cloned()
            .collect();
        ensure!(
            !apps.is_empty(),
            "No app package (with `[package.metadata.trezor]`) found in the workspace"
        );
        return Ok(apps);
    }

    names
        .iter()
        .map(|name| {
            members
                .iter()
                .find(|p| p.name == *name)
                .map(|p| (*p).clone())
                .ok_or_else(|| anyhow!("Package '{}' not found in the workspace", name))
        })
        .collect()
}

/// Returns the directory where built artifacts for a specific model
/// should be stored.
pub fn artifacts_dir() -> Result<PathBuf> {
    let dir = build_dir()?.join("artifacts");
    ensure_directory(&dir)?;
    Ok(dir)
}

/// Checks if the given directory exists, and creates it if it doesn't.
pub fn ensure_directory(path: &Path) -> Result<()> {
    std::fs::create_dir_all(path)
        .with_context(|| format!("Failed to create directory {}", path.display()))?;
    Ok(())
}
/*
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
}*/

/// Formats a [`std::process::Command`] as a shell-quoted string (program,
/// arguments, and any environment variables set on it) suitable for
/// printing to show the user the exact command being run.
///
/// ```
/// use modular_app-tool::helpers::command_args_to_string;
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

    #[test]
    fn resolve_target_arch_emulator_defaults_to_host() {
        let host = emulator_target_arch().unwrap();
        assert!(host.is_emulator());
        assert_eq!(
            resolve_target_arch(Some(Model::T3W1), None, true).unwrap(),
            host
        );
        assert_eq!(resolve_target_arch(None, None, true).unwrap(), host);
    }

    #[test]
    fn resolve_target_arch_firmware_defaults_to_model() {
        assert_eq!(
            resolve_target_arch(Some(Model::T3T1), None, false).unwrap(),
            TargetArch::Armv8m
        );
    }

    #[test]
    fn resolve_target_arch_firmware_requires_model_or_arch() {
        assert!(resolve_target_arch(None, None, false).is_err());
        assert_eq!(
            resolve_target_arch(None, Some(TargetArch::Armv8m), false).unwrap(),
            TargetArch::Armv8m
        );
    }

    #[test]
    fn resolve_target_arch_rejects_emulator_mismatch() {
        assert!(resolve_target_arch(None, Some(TargetArch::Armv8m), true).is_err());
        assert!(resolve_target_arch(None, Some(TargetArch::LinuxX86_64), false).is_err());
    }

    #[test]
    fn resolve_target_arch_accepts_explicit_emulator_arch() {
        assert_eq!(
            resolve_target_arch(Some(Model::T3W1), Some(TargetArch::MacosAarch64), true).unwrap(),
            TargetArch::MacosAarch64
        );
    }
}
