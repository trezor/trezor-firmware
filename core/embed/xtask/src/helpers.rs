use std::path::{Path, PathBuf};
use std::{env, fs};

use anyhow::{Context, Result, anyhow};
use cargo_metadata::MetadataCommand;

use crate::args::{Model, PrintVersionArgs, Project};
use crate::options::ResolvedBuildArgs;

/// Returns the path to the built ELF file for the given build arguments.
pub fn elf_path(args: &ResolvedBuildArgs) -> Result<PathBuf> {
    let elf_name = args.project.package_name();
    Ok(profile_dir(args)?.join(elf_name))
}

/// Returns the explicit `--target` triple passed to cargo, if any.
///
/// Hardware builds target the model's MCU. Emulator builds normally rely on
/// cargo's implicit host target, except with ASAN, where an explicit host
/// triple is needed to keep the sanitizer rustflags out of proc-macros and
/// build scripts (see `features::configure_cargo`). Cargo places the output
/// under `build/<triple>/` whenever a target is given, so `profile_dir` must
/// follow the same rule.
pub fn target_triple(args: &ResolvedBuildArgs) -> Result<Option<String>> {
    if !args.emulator {
        let model_config = args.model.config()?;
        return Ok(Some(model_config.target_triple()?.to_owned()));
    }
    if args.asan {
        return Ok(Some(host_triple()?));
    }
    Ok(None)
}

/// Returns the profile output directory (e.g.
/// `build/thumbv7em-none-eabihf/release`).
pub fn profile_dir(args: &ResolvedBuildArgs) -> Result<PathBuf> {
    let mut path = build_dir()?;
    if let Some(triple) = target_triple(args)? {
        path = path.join(triple);
    }

    let name = match args.cargo_profile_name() {
        "dev" => "debug", // Cargo uses "debug" folder for dev profile
        name => name,
    };

    Ok(path.join(name))
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

/// Returns the host target triple (e.g. `x86_64-unknown-linux-gnu`) by querying
/// `rustc -vV`.
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

/// Parses a version file and returns the version string in the format
/// "major.minor.patch".
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

/// Splits a project's binary into the flash segments it occupies, as
/// `(address, bytes)` pairs in ascending address order.
///
/// Most binaries are one contiguous segment at the project's flash start
/// symbol. The exception is the firmware area on models where it is split into
/// two parts (`FIRMWARE_P1_*` and `FIRMWARE_P2_*` in memory.ld, STM32F4): the
/// image is one logical blob, the same one the bootloader receives on upload,
/// but the bytes past `FIRMWARE_P1_MAXSIZE` belong at `FIRMWARE_P2_START`, not
/// right after part 1 -- between the two parts lie the secret, assets and
/// storage sectors.
pub fn project_segments<'a>(
    memory_ld: &str,
    project: Project,
    image: &'a [u8],
) -> Result<Vec<(u32, &'a [u8])>> {
    let start_symbol = project.flash_start_symbol()?;
    let start = read_symbol_from_content(memory_ld, start_symbol)?;

    if start_symbol != "FIRMWARE_START" {
        return Ok(vec![(start, image)]);
    }
    let Ok(p1_size) = read_symbol_from_content(memory_ld, "FIRMWARE_P1_MAXSIZE") else {
        return Ok(vec![(start, image)]);
    };

    let p1_start = read_symbol_from_content(memory_ld, "FIRMWARE_P1_START")?;
    if image.len() <= p1_size as usize {
        return Ok(vec![(p1_start, image)]);
    }

    let p2_start = read_symbol_from_content(memory_ld, "FIRMWARE_P2_START")?;
    let p2_size = read_symbol_from_content(memory_ld, "FIRMWARE_P2_MAXSIZE")?;
    let (part1, part2) = image.split_at(p1_size as usize);
    anyhow::ensure!(
        part2.len() <= p2_size as usize,
        "firmware image ({} bytes) does not fit FIRMWARE_P1 + FIRMWARE_P2 ({} bytes)",
        image.len(),
        p1_size as usize + p2_size as usize
    );

    Ok(vec![(p1_start, part1), (p2_start, part2)])
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

pub fn get_version_file(project: Project) -> Result<PathBuf> {
    Ok(workspace_dir()?
        .join("projects")
        .join(project.binary_name())
        .join("version.h"))
}

pub fn print_version(args: PrintVersionArgs) -> Result<()> {
    let version_str = parse_version_file(&get_version_file(args.project)?)?;
    println!("{}", version_str);
    Ok(())
}

#[cfg(test)]
mod tests {
    use std::fs;

    use super::{parse_address, parse_version_file, project_segments, read_symbol_from_content};
    use crate::args::Project;

    const SPLIT_MEMORY_LD: &str = "FIRMWARE_START = 0x8040000;\n\
        FIRMWARE_P1_START = 0x8040000;\nFIRMWARE_P1_MAXSIZE = 0x10;\n\
        FIRMWARE_P2_START = 0x8120000;\nFIRMWARE_P2_MAXSIZE = 0x8;\n";

    #[test]
    fn segments_without_split_is_one_segment() {
        let image = [1u8; 32];
        let segments =
            project_segments("FIRMWARE_START = 0x8010000;\n", Project::Firmware, &image).unwrap();

        assert_eq!(segments, vec![(0x0801_0000, &image[..])]);
    }

    #[test]
    fn segments_fitting_part1_is_one_segment() {
        let image = [1u8; 0x10];
        let segments = project_segments(SPLIT_MEMORY_LD, Project::Firmware, &image).unwrap();

        assert_eq!(segments, vec![(0x0804_0000, &image[..])]);
    }

    #[test]
    fn segments_places_tail_at_part2() {
        let image: Vec<u8> = (0..0x14).collect();
        let segments = project_segments(SPLIT_MEMORY_LD, Project::Firmware, &image).unwrap();

        assert_eq!(
            segments,
            vec![(0x0804_0000, &image[..0x10]), (0x0812_0000, &image[0x10..])]
        );
    }

    #[test]
    fn segments_rejects_image_larger_than_both_parts() {
        let image = [1u8; 0x19];
        let error = project_segments(SPLIT_MEMORY_LD, Project::Firmware, &image).unwrap_err();

        assert!(error.to_string().contains("does not fit"));
    }

    /// Prodtest shares the firmware area, so the same split applies to it.
    #[test]
    fn segments_split_prodtest_like_firmware() {
        let image: Vec<u8> = (0..0x14).collect();
        let segments = project_segments(SPLIT_MEMORY_LD, Project::Prodtest, &image).unwrap();

        assert_eq!(
            segments,
            vec![(0x0804_0000, &image[..0x10]), (0x0812_0000, &image[0x10..])]
        );
    }

    /// Only the firmware area is split; other projects stay one segment at
    /// their own start symbol, however large.
    #[test]
    fn segments_of_other_projects_are_never_split() {
        let memory_ld = format!("{SPLIT_MEMORY_LD}BOOTLOADER_START = 0x8020000;\n");
        let image = [1u8; 0x20];
        let segments = project_segments(&memory_ld, Project::Bootloader, &image).unwrap();

        assert_eq!(segments, vec![(0x0802_0000, &image[..])]);
    }

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
