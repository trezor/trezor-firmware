use anyhow::{Context, Result, anyhow, ensure};
use cargo_metadata::MetadataCommand;
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

/// Parses a version file and returns the version string in the format "major.minor.patch".
pub fn parse_version_file(file_name: &Path) -> Result<String> {
    let content = std::fs::read_to_string(file_name)
        .with_context(|| format!("Failed to read version file: {}", file_name.display()))?;

    let parse_symbol = |symbol_name: &str| -> Result<String> {
        let prefix = format!("#define {symbol_name} ");

        for line in content.lines() {
            if let Some(value) = line.strip_prefix(&prefix) {
                return Ok(value.trim().to_string());
            }
        }

        Err(anyhow!(
            "Failed to parse version from file: {}",
            file_name.display()
        ))
    };

    let major = parse_symbol("VERSION_MAJOR")?;
    let minor = parse_symbol("VERSION_MINOR")?;
    let patch = parse_symbol("VERSION_PATCH")?;

    Ok(format!("{}.{}.{}", major, minor, patch))
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

#[cfg(test)]
mod tests {
    use super::parse_version_file;
    use std::fs;

    #[test]
    fn parses_version_file_symbols() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("version.h");
        fs::write(
            &path,
            "#define VERSION_MAJOR 2\n#define VERSION_MINOR 8\n#define VERSION_PATCH 1\n",
        )
        .unwrap();

        let version = parse_version_file(&path).unwrap();

        assert_eq!(version, "2.8.1");
    }

    #[test]
    fn errors_when_version_symbol_is_missing() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("version.h");
        fs::write(&path, "#define VERSION_MAJOR 2\n#define VERSION_MINOR 8\n").unwrap();

        let error = parse_version_file(&path).unwrap_err();

        assert!(
            error
                .to_string()
                .contains("Failed to parse version from file")
        );
    }
}
