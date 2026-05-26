use anyhow::{Context, Result, anyhow};
use cargo_metadata::MetadataCommand;
use std::{
    env, fs,
    path::{Path, PathBuf},
};

use crate::args::{BuildArgs, Component, Model};

/// Returns the path to the built ELF file for the given build arguments.
pub fn elf_path(args: &BuildArgs) -> Result<PathBuf> {
    let elf_name = args.component.package_name(args.emulator);
    Ok(profile_dir(args)?.join(elf_name))
}

/// Returns the profile output directory (e.g. `build/thumbv7em-none-eabihf/release`).
pub fn profile_dir(args: &BuildArgs) -> Result<PathBuf> {
    let mut path = build_dir()?;
    if !args.emulator {
        path = path.join(args.model.target_triple());
    }

    Ok(path.join(args.profile_name()))
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
pub fn artifacts_dir(model: Model) -> Result<PathBuf> {
    Ok(build_dir()?.join("artifacts").join(model.model_id()))
}

/// Returns the directory where built versioned artifacts should be published.
pub fn publish_dir() -> Result<PathBuf> {
    Ok(build_dir()?.join("artifacts").join("pub"))
}

/// Returns the host target triple (e.g. `x86_64-unknown-linux-gnu`) by querying `rustc -vV`.
pub fn host_triple() -> Result<String> {
    let output = std::process::Command::new("rustc")
        .args(["-vV"])
        .output()
        .context("Failed to run `rustc -vV`")?;
    let stdout = String::from_utf8(output.stdout).context("rustc -vV output is not UTF-8")?;
    for line in stdout.lines() {
        if let Some(triple) = line.strip_prefix("host: ") {
            return Ok(triple.trim().to_string());
        }
    }
    anyhow::bail!("could not determine host triple from `rustc -vV` output")
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

/// Reads symbol from memory.ld file and parse it as an address.
pub fn read_symbol(file: &Path, symbol: &str) -> Result<u32> {
    let content =
        fs::read_to_string(file).with_context(|| format!("Failed to read `{}`", file.display()))?;
    read_symbol_from_content(&content, symbol)
        .with_context(|| format!("Failed to resolve `{symbol}` from `{}`", file.display()))
}

pub fn read_symbol_from_content(content: &str, symbol: &str) -> Result<u32> {
    let prefix = format!("{symbol} =");

    let value = content
        .lines()
        .map(str::trim)
        .find_map(|line| line.strip_prefix(&prefix))
        .map(|value| value.trim().trim_end_matches(';').trim())
        .with_context(|| format!("Address `{symbol}` not found"))?;

    parse_address(value).with_context(|| format!("Invalid address `{value}` for `{symbol}`"))
}

/// Parses a string as a u32 address, supporting both decimal and
/// hexadecimal formats.
fn parse_address(value: &str) -> Result<u32> {
    if let Some(hex) = value
        .strip_prefix("0x")
        .or_else(|| value.strip_prefix("0X"))
    {
        Ok(u32::from_str_radix(hex, 16)?)
    } else {
        Ok(value.parse()?)
    }
}

pub fn get_version_file(component: Component) -> Result<PathBuf> {
    Ok(workspace_dir()?
        .join("projects")
        .join(component.binary_name())
        .join("version.h"))
}

#[cfg(test)]
mod tests {
    use super::{parse_address, parse_version_file, read_symbol_from_content};
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

    #[test]
    fn parses_decimal_and_hex_addresses() {
        assert_eq!(parse_address("1234").unwrap(), 1234);
        assert_eq!(parse_address("0x1234").unwrap(), 0x1234);
        assert_eq!(parse_address("0X1234").unwrap(), 0x1234);
    }

    #[test]
    fn reads_symbol_values_from_memory_ld_content() {
        let content = "BOOTLOADER_START = 0x8000000;\nFIRMWARE_START = 134217984;\n";

        assert_eq!(
            read_symbol_from_content(content, "BOOTLOADER_START").unwrap(),
            0x0800_0000
        );
        assert_eq!(
            read_symbol_from_content(content, "FIRMWARE_START").unwrap(),
            134_217_984
        );
    }
}
