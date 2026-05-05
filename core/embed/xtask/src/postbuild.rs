use anyhow::{Context, Result, ensure};
use std::{
    fs,
    path::{Path, PathBuf},
    process,
};

use crate::{
    args::{Component, Model},
    helpers,
};

/// Extracts appropriate sections from the ELF file and creates a raw unsigned binary.
pub fn elf_to_bin(
    source: &Path,
    component: Component,
    model: Model,
    production: bool,
) -> Result<PathBuf> {
    match component {
        Component::Boardloader => objcopy(
            source,
            [
                ".vector_table",
                ".text",
                ".data",
                ".rodata",
                ".capabilities",
            ],
        ),

        Component::Bootloader | Component::BootloaderCi => {
            objcopy(source, [".header", ".flash", ".data"])
        }

        Component::Secmon => objcopy(
            source,
            [".secmon_header", ".flash", ".data", ".gnu.sgstubs"],
        ),

        Component::Kernel => objcopy(source, [".flash", ".data"]),

        Component::Firmware => {
            if model == Model::T2T1 || model == Model::T2B1 {
                // On STM32F427 models, the firmware is not contiguous in flash.
                // It is split into two parts, with the storage area in between.
                // We therefore extract the two parts separately and concatenate them.
                let part1 = objcopy_ex(
                    source,
                    "part1",
                    [".vendorheader", ".header", ".flash", ".data"],
                    ["--pad-to", "0x08100000"],
                )?;
                let part2 = objcopy_ex(source, "part2", [".flash2"], [] as [&str; 0])?;
                concat_files(part1.with_extension("ubin"), [part1, part2])
            } else {
                objcopy(source, [".vendorheader", ".header", ".flash", ".data"])
            }
        }

        Component::Prodtest => {
            if model == Model::T3W1 {
                let body_bin = objcopy_ex(
                    source,
                    "body.bin",
                    [".secmon_header", ".flash", ".data"],
                    [] as [&str; 0],
                )?;

                sign_binary(&body_bin, Component::Prodtest, model, production)?;

                let header_bin = objcopy_ex(
                    source,
                    "header.bin",
                    [".vendorheader", ".header"],
                    [] as [&str; 0],
                )?;

                concat_files(source.with_extension("bin"), [header_bin, body_bin])
            } else {
                objcopy(source, [".vendorheader", ".header", ".flash", ".data"])
            }
        }
    }
}

pub fn sign_binary(binary: &Path, target: Component, model: Model, production: bool) -> Result<()> {
    println!(
        "xtask: Signing binary `{}`",
        binary
            .file_name()
            .context("Failed to get binary file name")?
            .to_string_lossy()
    );

    let header_tool = header_tool_name(target, model);

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

fn header_tool_name(target: Component, model: Model) -> &'static str {
    match (target, model) {
        (Component::Bootloader, Model::T3W1)
        | (Component::BootloaderCi, Model::T3W1)
        | (Component::Bootloader, Model::D002)
        | (Component::BootloaderCi, Model::D002) => "headertool_pq",
        _ => "headertool",
    }
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
/// and output extension. Used for the special case of the firmware on
/// STM32F427 models, where we need to extract two separate parts of
/// the ELF and concatenate them.
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
    use super::{header_tool_name, merge_compile_commands};
    use crate::args::{Component, Model};
    use serde_json::Value;
    use std::fs;

    #[test]
    fn picks_pq_header_tool_only_for_supported_targets() {
        assert_eq!(
            header_tool_name(Component::Bootloader, Model::T3W1),
            "headertool_pq"
        );
        assert_eq!(
            header_tool_name(Component::BootloaderCi, Model::D002),
            "headertool_pq"
        );
        assert_eq!(
            header_tool_name(Component::Firmware, Model::T3W1),
            "headertool"
        );
    }

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
