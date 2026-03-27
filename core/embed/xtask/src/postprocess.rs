use anyhow::{Context, Result, bail};
use std::path::{Path, PathBuf};

use crate::args::{BuildArgs, Component, Model};
use crate::helpers::elf_path;

fn objcopy<S, I>(input: &Path, sections: I) -> Result<PathBuf>
where
    S: AsRef<str>,
    I: IntoIterator<Item = S>,
{
    objcopy_ex(input, "bin", sections, [] as [&str; 0])
}

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

    let mut cmd = std::process::Command::new("arm-none-eabi-objcopy");

    cmd.arg("-O").arg("binary");

    for section in sections {
        cmd.arg("-j").arg(section.as_ref());
    }

    for arg in extra_args {
        cmd.arg(arg.as_ref());
    }

    cmd.arg(input).arg(&output);

    let status = cmd.status().context("Failed to execute objcopy")?;
    if !status.success() {
        bail!("objcopy failed with status: {}", status);
    }

    println!(
        "xtask: Created `{}` with objcopy",
        output
            .file_name()
            .context("Failed to get output file name")?
            .to_string_lossy()
    );

    Ok(output)
}

fn concat_files<P, I>(output: impl AsRef<Path>, parts: I) -> Result<PathBuf>
where
    P: AsRef<Path>,
    I: IntoIterator<Item = P>,
{
    let output = output.as_ref();

    // Create output file and copy parts into it sequentially
    let mut output_file = std::fs::File::create(&output)
        .with_context(|| format!("Failed to create `{}`", output.display()))?;

    for part in parts {
        let part = part.as_ref();
        let mut part_file = std::fs::File::open(&part)
            .with_context(|| format!("Failed to open `{}`", part.display()))?;

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

pub fn elf_to_bin(source: &Path, component: Component, model: Model) -> Result<PathBuf> {
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
            // !@# fix for T3W1
            objcopy(source, [".vendorheader", ".header", ".flash", ".data"])
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

    let header_tool = match (target, model) {
        (Component::Bootloader, Model::T3W1) | (Component::BootloaderCi, Model::T3W1) => {
            "headertool_pq"
        }
        _ => "headertool",
    };

    let mut cmd = std::process::Command::new(header_tool);

    if !production {
        // Use dev keys for signing
        cmd.arg("-D");
    }

    cmd.arg(binary);

    let status = cmd.status().context("Failed to execute headertool")?;

    if !status.success() {
        bail!("headertool failed with status: {}", status);
    }

    Ok(())
}

#[allow(dead_code)]
pub fn print_binary_size(args: &BuildArgs) -> Result<()> {
    if args.emulator {
        return Ok(());
    }

    let binary_path = elf_path(args)?;

    std::fs::metadata(&binary_path)
        .with_context(|| format!("Built binary not found at `{}`", binary_path.display()))?;

    let mut cmd = std::process::Command::new("arm-none-eabi-size");
    cmd.arg(&binary_path);

    let status = cmd
        .status()
        .context("Failed to spawn `arm-none-eabi-size`")?;
    if !status.success() {
        bail!(
            "`arm-none-eabi-size` failed for `{}`",
            binary_path.display()
        );
    }

    Ok(())
}
