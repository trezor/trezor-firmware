use anyhow::{Context, Result, ensure};
use std::{
    fs,
    {path::Path, process},
};

use crate::{
    args::{FlashArgs, FlashEraseArgs, FlashSection},
    helpers,
};

/// Flashes the specified project to the device using OpenOCD.
pub fn flash(args: FlashArgs) -> Result<()> {
    ensure!(
        args.project.flashable(),
        "Flashing is not supported for `{}`",
        args.project.binary_name()
    );

    let binary =
        helpers::artifacts_dir(args.model)?.join(format!("{}.bin", args.project.binary_name()));

    let binary = binary
        .canonicalize()
        .with_context(|| format!("Failed to locate `{}` for flashing", binary.display()))?;

    let flash_start = args.project.flash_start_symbol()?;
    let memory_ld = args.model.model_memory_ld()?;
    let address = helpers::read_symbol(&memory_ld, flash_start)?;

    println!(
        "Flashing `{}` to address 0x{:08X}",
        binary.display(),
        address
    );

    let flash_instruction = build_flash_write_instruction(&binary, address);
    let model_config = args.model.config()?;

    let status = process::Command::new("openocd")
        .args(["-f", "interface/stlink.cfg"])
        .args(["-c", "transport select hla_swd"])
        .args(["-f", model_config.openocd_target()?])
        .arg("-c")
        .arg(flash_instruction)
        .status()
        .context("Failed to spawn `openocd`")?;

    ensure!(status.success(), "`openocd` failed with status: {status}");

    Ok(())
}

/// Erase specified flash section using OpenOCD. The section boundaries are determined
/// by reading symbols from the model's memory.ld file.
pub fn flash_erase(args: FlashEraseArgs) -> Result<()> {
    let mem_ld = args.model.model_memory_ld()?;
    let content = fs::read_to_string(&mem_ld)
        .with_context(|| format!("Failed to read `{}`", mem_ld.display()))?;
    let instr = build_flash_erase_instruction(&content, args.section)?;
    let model_config = args.model.config()?;

    let status = process::Command::new("openocd")
        .args(["-f", "interface/stlink.cfg"])
        .args(["-c", "transport select hla_swd"])
        .args(["-f", model_config.openocd_target()?])
        .arg("-c")
        .arg(instr)
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
    use super::{build_flash_erase_instruction, build_flash_write_instruction};
    use crate::args::FlashSection;
    use std::path::Path;

    #[test]
    fn builds_flash_write_instruction() {
        let instruction = build_flash_write_instruction(Path::new("/tmp/fw.bin"), 0x0800_4000);

        assert_eq!(
            instruction,
            "init; reset halt; flash write_image erase /tmp/fw.bin 0x8004000; exit"
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
