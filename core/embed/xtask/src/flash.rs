use std::path::{Path, PathBuf};
use std::{fs, process};

use anyhow::{Context, Result, ensure};

use crate::args::{
    FlashArgs, FlashEraseArgs, FlashReadArgs, FlashSection, Model, Project, ResetArgs,
};
use crate::{combine, helpers};

/// Name of the flash dump written by [`flash_read()`] when no output file is
/// given.
const DEFAULT_DUMP_NAME: &str = "flash-dump.bin";

/// Flashes the specified project to the device using OpenOCD.
pub fn flash(args: FlashArgs) -> Result<()> {
    let (binary, flash_start, hint) = if args.combined {
        // A combined image always starts with the boardloader, no matter which
        // project it was combined for.
        (
            combine::combined_binary_path(args.model, args.project)?,
            Project::Boardloader.flash_start_symbol()?,
            format!(
                ", run `xtask combine --model {} {}` first",
                args.model.model_id().to_lowercase(),
                args.project.binary_name()
            ),
        )
    } else {
        ensure!(
            args.project.flashable(),
            "Flashing is not supported for `{}`",
            args.project.binary_name()
        );

        (
            helpers::artifacts_dir(args.model)?.join(format!("{}.bin", args.project.binary_name())),
            args.project.flash_start_symbol()?,
            String::new(),
        )
    };

    let binary = binary.canonicalize().with_context(|| {
        format!(
            "Failed to locate `{}` for flashing{}",
            binary.display(),
            hint
        )
    })?;

    let memory_ld = args.model.model_memory_ld()?;
    let address = helpers::read_symbol(&memory_ld, flash_start)?;

    println!(
        "Flashing `{}` to address 0x{:08X}",
        binary.display(),
        address
    );

    let flash_instruction = build_flash_write_instruction(&binary, address);

    run_openocd(args.model, &flash_instruction)
}

/// Erase specified flash section using OpenOCD. The section boundaries are
/// determined by reading symbols from the model's memory.ld file.
pub fn flash_erase(args: FlashEraseArgs) -> Result<()> {
    let mem_ld = args.model.model_memory_ld()?;
    let content = fs::read_to_string(&mem_ld)
        .with_context(|| format!("Failed to read `{}`", mem_ld.display()))?;
    let instr = build_flash_erase_instruction(&content, args.section)?;

    run_openocd(args.model, &instr)
}

/// Reads the whole flash of the connected device into a file using OpenOCD.
pub fn flash_read(args: FlashReadArgs) -> Result<()> {
    let output = match args.output {
        Some(path) => path,
        None => helpers::artifacts_dir(args.model)?.join(DEFAULT_DUMP_NAME),
    };
    let output = absolute_output_path(&output)?;

    println!(
        "Reading flash of `{:?}` into `{}`",
        args.model,
        output.display()
    );

    run_openocd(args.model, &build_flash_read_instruction(&output))?;

    let size = fs::metadata(&output)
        .with_context(|| format!("`openocd` did not write `{}`", output.display()))?
        .len();
    println!("Read {} bytes into `{}`", size, output.display());

    Ok(())
}

/// Makes `output` absolute, creating its parent directory if needed. OpenOCD
/// resolves relative paths against its own working directory, so it has to be
/// given an absolute one.
fn absolute_output_path(output: &Path) -> Result<PathBuf> {
    let parent = match output.parent() {
        Some(parent) if !parent.as_os_str().is_empty() => parent.to_path_buf(),
        // A bare file name is relative to the current directory.
        _ => PathBuf::from("."),
    };
    helpers::ensure_directory(&parent)?;

    let file_name = output
        .file_name()
        .with_context(|| format!("`{}` is not a valid output file", output.display()))?;

    let parent = parent
        .canonicalize()
        .with_context(|| format!("Failed to resolve `{}`", parent.display()))?;

    Ok(parent.join(file_name))
}

/// Resets the connected device using OpenOCD.
pub fn reset(args: ResetArgs) -> Result<()> {
    println!("Resetting `{:?}`", args.model);

    run_openocd(args.model, "init; reset; exit")
}

/// Runs OpenOCD instructions against the connected device for the given model.
fn run_openocd(model: Model, instructions: &str) -> Result<()> {
    let model_config = model.config()?;

    let status = process::Command::new("openocd")
        .args(["-f", "interface/stlink.cfg"])
        .args(["-c", "transport select hla_swd"])
        .args(["-f", model_config.openocd_target()?])
        .arg("-c")
        .arg(instructions)
        .status()
        .context("Failed to spawn `openocd`")?;

    ensure!(status.success(), "`openocd` failed with status: {status}");

    Ok(())
}

fn build_flash_write_instruction(binary: &Path, address: u32) -> String {
    format!(
        "init; reset halt; flash write_image erase {} 0x{:X}; exit",
        binary.display(),
        address
    )
}

/// Bank 0 spans the whole flash on every supported MCU, same as the
/// `flash-erase all` instruction relies on.
fn build_flash_read_instruction(output: &Path) -> String {
    format!(
        "init; reset halt; flash read_bank 0 {}; exit",
        output.display()
    )
}

fn build_flash_erase_instruction(content: &str, section: FlashSection) -> Result<String> {
    let mut instr = String::from("init; reset halt; flash info 0; ");

    let mut push_erase = |symbol_prefix: &str| {
        let start =
            helpers::read_symbol_from_content(content, &format!("{}_SECTOR_START", symbol_prefix))?;
        let end =
            helpers::read_symbol_from_content(content, &format!("{}_SECTOR_END", symbol_prefix))?;
        instr.push_str(&format!("flash erase_sector 0 {} {}; ", start, end));
        Ok::<(), anyhow::Error>(())
    };

    match section {
        FlashSection::All => {
            instr.push_str("flash erase_sector 0 0 last; flash erase_check 0; ");
        }
        FlashSection::Boardloader => push_erase("BOARDLOADER")?,
        FlashSection::Bootloader => push_erase("BOOTLOADER")?,
        FlashSection::Firmware => {
            if helpers::read_symbol_from_content(content, "FIRMWARE_P1_SECTOR_START").is_ok() {
                push_erase("FIRMWARE_P1")?;
                push_erase("FIRMWARE_P2")?;
            } else {
                push_erase("FIRMWARE")?;
            }
        }
        FlashSection::Storage => {
            push_erase("STORAGE_1")?;
            push_erase("STORAGE_2")?;
        }
    }

    instr.push_str("exit");
    Ok(instr)
}

#[cfg(test)]
mod tests {
    use std::path::Path;

    use super::{
        build_flash_erase_instruction, build_flash_read_instruction, build_flash_write_instruction,
    };
    use crate::args::FlashSection;

    #[test]
    fn builds_flash_write_instruction() {
        let instruction = build_flash_write_instruction(Path::new("/tmp/fw.bin"), 0x0800_4000);

        assert_eq!(
            instruction,
            "init; reset halt; flash write_image erase /tmp/fw.bin 0x8004000; exit"
        );
    }

    #[test]
    fn builds_flash_read_instruction_for_the_whole_bank() {
        let instruction = build_flash_read_instruction(Path::new("/tmp/dump.bin"));

        assert_eq!(
            instruction,
            "init; reset halt; flash read_bank 0 /tmp/dump.bin; exit"
        );
    }

    #[test]
    fn builds_firmware_erase_instruction_for_dual_bank_layouts() {
        let content = "\
FIRMWARE_P1_SECTOR_START = 5;\n\
FIRMWARE_P1_SECTOR_END = 10;\n\
FIRMWARE_P2_SECTOR_START = 11;\n\
FIRMWARE_P2_SECTOR_END = 18;\n";

        let instruction = build_flash_erase_instruction(content, FlashSection::Firmware).unwrap();

        assert!(instruction.contains("flash erase_sector 0 5 10;"));
        assert!(instruction.contains("flash erase_sector 0 11 18;"));
        assert!(instruction.ends_with("exit"));
    }

    #[test]
    fn builds_storage_erase_instruction() {
        let content = "\
STORAGE_1_SECTOR_START = 2;\n\
STORAGE_1_SECTOR_END = 3;\n\
STORAGE_2_SECTOR_START = 4;\n\
STORAGE_2_SECTOR_END = 5;\n";

        let instruction = build_flash_erase_instruction(content, FlashSection::Storage).unwrap();

        assert!(instruction.contains("flash erase_sector 0 2 3;"));
        assert!(instruction.contains("flash erase_sector 0 4 5;"));
    }
}
