use anyhow::{anyhow, ensure, Context, Result};
use cargo_metadata::MetadataCommand;
use std::process::Command;
use std::{
    env,
    ffi::OsStr,
    path::{Path, PathBuf},
};

use crate::args::{BuildArgs, Model};

/// Returns the path to the built ELF file for the given build arguments.
pub fn elf_path(args: &BuildArgs) -> Result<PathBuf> {
    let elf_name = args.app.as_str();
    Ok(profile_dir(args)?.join(elf_name))
}

/// Returns the profile output directory (e.g. `build/thumbv7em-none-eabihf/release`).
pub fn profile_dir(args: &BuildArgs) -> Result<PathBuf> {
    let mut path = build_dir()?;
    if !args.emulator {
        path = path.join(args.model.target_triple());
    }

    let profile_dir = if args.debug { "debug" } else { "release" };

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

/// Returns the cargo workspace root directory.
pub fn workspace_dir() -> Result<PathBuf> {
    let path = Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .context("Unable to resolve workspace root")?
        .to_path_buf();
    Ok(path)
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

pub fn uv_python<I, S>(script: &Path, args: I) -> Result<()>
where
    I: IntoIterator<Item = S>,
    S: AsRef<OsStr>,
{
    let mut cmd = Command::new("uv");
    cmd.arg("run").arg("python").arg(script).args(args);
    cmd.current_dir(env!("CARGO_MANIFEST_DIR"));
    let status = cmd.status().context("Failed to execute objcopy")?;
    ensure!(status.success(), "objcopy failed with status: {status}");
    Ok(())
}

pub fn command_args_to_string(cmd: &Command) -> String {
    let mut parts = vec![cmd.get_program().to_string_lossy().into_owned()];
    parts.extend(cmd.get_args().map(|arg| arg.to_string_lossy().into_owned()));
    parts.join(" ")
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

        assert!(error
            .to_string()
            .contains("Failed to parse version from file"));
    }
}
