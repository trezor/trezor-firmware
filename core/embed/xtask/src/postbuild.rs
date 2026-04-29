use anyhow::{Context, Result, ensure};
use std::{
    fs,
    path::{Path, PathBuf},
    process,
};

use crate::{
    args::Component,
    config::{ModelConfig, TargetProfile},
    helpers,
    model::Model,
};

/// Extracts appropriate sections from the ELF file and creates a raw unsigned binary.
/// Section lists are read from the component's `target.toml`; model-specific split
/// behaviour is controlled by `model_config`.
pub fn elf_to_bin(
    source: &Path,
    component: Component,
    model_config: &ModelConfig,
    production: bool,
) -> Result<PathBuf> {
    let target_profile = TargetProfile::load(component)?;

    match component {
        Component::Firmware => {
            if model_config.is_stm32f4() {
                // STM32F4 firmware flash is non-contiguous — two banks separated
                // by the storage area must be extracted and concatenated.
                // Part1 uses the same elf_sections as the flat (non-split) path.
                let pad_to = target_profile.split_pad_to.as_deref()
                    .ok_or_else(|| anyhow::anyhow!("firmware target.toml missing split_pad_to"))?;
                let part2_sections = target_profile.split_part2_sections.as_ref()
                    .ok_or_else(|| anyhow::anyhow!("firmware target.toml missing split_part2_sections"))?;
                let part1 = objcopy_ex(source, "part1", &target_profile.elf_sections, ["--pad-to", pad_to])?;
                let part2 = objcopy_ex(source, "part2", part2_sections, [] as [&str; 0])?;
                concat_files(part1.with_extension("ubin"), [part1, part2])
            } else {
                objcopy(source, &target_profile.elf_sections)
            }
        }

        Component::Prodtest => {
            if model_config.secmon {
                // On secmon models prodtest is a secmon-signed body with a plain
                // vendor header prepended. The body is signed before concatenation.
                let body_sections = target_profile.secmon_body_sections.as_ref()
                    .ok_or_else(|| anyhow::anyhow!("prodtest target.toml missing secmon_body_sections"))?;
                let header_sections = target_profile.secmon_header_sections.as_ref()
                    .ok_or_else(|| anyhow::anyhow!("prodtest target.toml missing secmon_header_sections"))?;
                let body_bin = objcopy_ex(source, "body.bin", body_sections, [] as [&str; 0])?;
                sign_binary(&body_bin, component, model_config, production)?;
                let header_bin = objcopy_ex(source, "header.bin", header_sections, [] as [&str; 0])?;
                concat_files(source.with_extension("bin"), [header_bin, body_bin])
            } else {
                objcopy(source, &target_profile.elf_sections)
            }
        }

        _ => objcopy(source, &target_profile.elf_sections),
    }
}

pub fn sign_binary(
    binary: &Path,
    component: Component,
    model_config: &ModelConfig,
    production: bool,
) -> Result<()> {
    let header_tool = match component {
        Component::Bootloader | Component::BootloaderCi => model_config
            .bootloader_header_tool
            .as_deref()
            .unwrap_or("headertool"),
        _ => "headertool",
    };

    println!(
        "xtask: Signing binary `{}`",
        binary
            .file_name()
            .context("Failed to get binary file name")?
            .to_string_lossy()
    );

    let mut cmd = process::Command::new(header_tool);

    if !production {
        // Use dev keys for signing
        cmd.arg("-D");
    }

    cmd.arg(binary);

    let status = cmd.status().context("Failed to execute headertool")?;

    ensure!(status.success(), "headertool failed with status: {status}");

    Ok(())
}

/// Extracts specified sections from an ELF file into a raw binary using objcopy.
/// The output file is created in the same directory as the input with the same name but .bin extension.
fn objcopy<S, I>(input: &Path, sections: I) -> Result<PathBuf>
where
    S: AsRef<str>,
    I: IntoIterator<Item = S>,
{
    objcopy_ex(input, "bin", sections, [] as [&str; 0])
}

/// A more flexible version of objcopy that allows specifying extra arguments
/// and a custom output extension.
fn objcopy_ex<S1, S2, I1, I2>(
    input: &Path,
    output_extension: &str,
    sections: I1,
    extra_args: I2,
) -> Result<PathBuf>
where
    S1: AsRef<str>,
    S2: AsRef<str>,
    I1: IntoIterator<Item = S1>,
    I2: IntoIterator<Item = S2>,
{
    let output = input.with_extension(output_extension);

    let mut cmd = process::Command::new("arm-none-eabi-objcopy");

    cmd.arg("-O").arg("binary");

    for section in sections {
        cmd.arg("-j").arg(section.as_ref());
    }

    for arg in extra_args {
        cmd.arg(arg.as_ref());
    }

    cmd.arg(input).arg(&output);

    let status = cmd.status().context("Failed to execute objcopy")?;

    ensure!(status.success(), "objcopy failed with status: {status}");

    println!(
        "xtask: Created `{}` with objcopy",
        output
            .file_name()
            .context("Failed to get output file name")?
            .to_string_lossy()
    );

    Ok(output)
}

/// Concatenates multiple binary files into one. The output file is created
/// if it doesn't exist, or overwritten if it does.
fn concat_files<P, I>(output: impl AsRef<Path>, parts: I) -> Result<PathBuf>
where
    P: AsRef<Path>,
    I: IntoIterator<Item = P>,
{
    let output = output.as_ref();

    // Create output file and copy parts into it sequentially
    let mut output_file = fs::File::create(output)
        .with_context(|| format!("Failed to create `{}`", output.display()))?;

    for part in parts {
        let part = part.as_ref();
        let mut part_file =
            fs::File::open(part).with_context(|| format!("Failed to open `{}`", part.display()))?;

        std::io::copy(&mut part_file, &mut output_file).with_context(|| {
            format!(
                "Failed to copy `{}` to `{}`",
                part.display(),
                output.display()
            )
        })?;
    }

    println!(
        "xtask: Created `{}` by concatenating parts",
        output
            .file_name()
            .context("Failed to get output file name")?
            .to_string_lossy()
    );

    Ok(output.to_path_buf())
}

/// Merges multiple compile_commands.json files into one.
/// Files are given in priority order (first = highest priority).
/// Each source file's entry is taken from the highest-priority file that
/// contains it; lower-priority duplicates are skipped.
pub fn merge_compile_commands(inputs: &[&Path], output: &Path) -> Result<()> {
    use std::collections::HashSet;

    let mut seen_files: HashSet<String> = HashSet::new();
    let mut merged: Vec<serde_json::Value> = Vec::new();

    for input in inputs {
        if !input.exists() {
            continue;
        }

        let content = fs::read_to_string(input)
            .with_context(|| format!("Failed to read `{}`", input.display()))?;
        let entries: Vec<serde_json::Value> = serde_json::from_str(&content)
            .with_context(|| format!("Failed to parse `{}`", input.display()))?;

        for entry in entries {
            let file_key = entry
                .get("file")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_owned();

            if seen_files.insert(file_key) {
                merged.push(entry);
            }
        }
    }

    let json = serde_json::to_string_pretty(&merged)
        .context("Failed to serialize merged compile_commands")?;
    fs::write(output, json).with_context(|| format!("Failed to write `{}`", output.display()))?;

    Ok(())
}

/// Publishes a built binary by copying it to the `published` directory with a name that includes
pub fn publish_artifact(
    binary: &Path,
    component: Component,
    model: Model,
    version_file: &Path,
) -> Result<()> {
    let pub_dir = helpers::publish_dir()?;
    helpers::ensure_directory(&pub_dir)?;

    let name = format!(
        "{}-{}-{}-{}{}.bin",
        component.binary_name(),
        model.model_id(),
        &helpers::parse_version_file(version_file)?,
        &helpers::git_revision()?[..8],
        if helpers::git_modified()? {
            "-dirty"
        } else {
            ""
        }
    );

    std::fs::copy(binary, pub_dir.join(&name)).with_context(|| {
        format!(
            "Failed to copy `{}` to `{}`",
            binary.display(),
            pub_dir.join(&name).display()
        )
    })?;

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::merge_compile_commands;
    use serde_json::Value;
    use std::fs;

    #[test]
    fn merge_compile_commands_prefers_first_input_for_duplicates() {
        let dir = tempfile::tempdir().unwrap();
        let first = dir.path().join("first.json");
        let second = dir.path().join("second.json");
        let output = dir.path().join("merged.json");

        fs::write(
            &first,
            r#"[
  {"file":"src/main.c","command":"cc -DFIRST","directory":"/tmp"},
  {"file":"src/other.c","command":"cc -DOTHER","directory":"/tmp"}
]"#,
        )
        .unwrap();
        fs::write(
            &second,
            r#"[
  {"file":"src/main.c","command":"cc -DSECOND","directory":"/tmp"},
  {"file":"src/new.c","command":"cc -DNEW","directory":"/tmp"}
]"#,
        )
        .unwrap();

        merge_compile_commands(&[first.as_path(), second.as_path()], &output).unwrap();

        let merged: Vec<Value> =
            serde_json::from_str(&fs::read_to_string(output).unwrap()).unwrap();
        assert_eq!(merged.len(), 3);
        assert_eq!(merged[0]["command"], "cc -DFIRST");
        assert_eq!(merged[1]["file"], "src/other.c");
        assert_eq!(merged[2]["file"], "src/new.c");
    }
}
