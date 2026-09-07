use std::path::PathBuf;
use std::{fs, process};

use anyhow::{Context, Result, ensure};

use crate::args::{FlashArgs, FlashEraseArgs, FlashSection, Model, Project, ResetArgs};
use crate::{combine, helpers, pq};

/// Flashes the specified project to the device using OpenOCD.
pub fn flash(args: FlashArgs) -> Result<()> {
    ensure!(
        args.project.flashable(),
        "Flashing is not supported for `{}`",
        args.project.binary_name()
    );

    // A combined image already holds the whole boot chain, stamped and assembled
    // by `xtask combine`, so it is written as-is from the boardloader address.
    if args.combined {
        return flash_combined(&args);
    }

    // A pq_secure release is what boots on a Merkle-tree model; the per-project
    // artifacts are not installable. Boardloader and bootloader_ci are not part
    // of a release, so they keep reading their own artifact.
    if args.model.config()?.has_feature("pq_secure_boot")
        && matches!(
            args.project,
            Project::Bootloader | Project::Firmware | Project::Prodtest
        )
    {
        return flash_release(&args);
    }

    ensure!(
        args.variant.is_none(),
        "--variant applies only to a pq_secure release, which `{}` on this model is not",
        args.project.binary_name()
    );

    let binary =
        helpers::artifacts_dir(args.model)?.join(format!("{}.bin", args.project.binary_name()));

    let binary = binary
        .canonicalize()
        .with_context(|| format!("Failed to locate `{}` for flashing", binary.display()))?;

    let address = project_address(&args, args.project)?;

    println!(
        "Flashing `{}` to address 0x{:08X}",
        binary.display(),
        address
    );

    run_openocd(
        args.model,
        &build_flash_write_instruction(&[(binary, address)]),
    )
}

/// Flash the combined image: the whole boot chain in one write.
///
/// The image is flashed byte for byte as `xtask combine` produced it, starting
/// at the boardloader. Everything about its contents was decided there --
/// which projects it holds and, on a Merkle-tree model, which variant its
/// bootloader is provisioned for -- so nothing is resolved or stamped here.
fn flash_combined(args: &FlashArgs) -> Result<()> {
    ensure!(
        combine::supported(args.project),
        "there is no combined image for `{}` -- a combined image runs from the \
         boardloader up to one of: {}",
        args.project.binary_name(),
        combine::supported_projects()
    );
    ensure!(
        args.variant.is_none(),
        "--variant belongs to `xtask combine`, which bakes the variant into the \
         image; by now it is already decided"
    );

    let binary = combine::combined_artifact(args.model, args.project)?;
    ensure!(
        binary.exists(),
        "no combined image at {binary} -- build one first:\n             \
         xtask combine {project} -m {model}",
        binary = binary.display(),
        project = args.project.binary_name(),
        model = args.model.model_id(),
    );

    // From the boardloader, not the project's own address: the project only
    // names WHICH combined image, since the image starts at the bottom of the
    // chain regardless.
    let address = project_address(args, Project::Boardloader)?;
    println!(
        "Flashing the combined `{}` image `{}` to address 0x{:08X}",
        args.project.binary_name(),
        binary.display(),
        address
    );

    run_openocd(
        args.model,
        &build_flash_write_instruction(&[(binary, address)]),
    )
}

/// Flash a pq_secure release with a debugger.
///
/// Bootloader and firmware are written in ONE OpenOCD run, so the device is
/// never left holding two halves of different builds -- see
/// [`pq::resolve_install`] for why they belong together and what gets stamped.
fn flash_release(args: &FlashArgs) -> Result<()> {
    let install = pq::resolve_install(args.model, args.project, args.variant)?;

    match install.variant {
        Some(variant) => println!(
            "Flashing the {} release, provisioned for `{}`",
            args.model.model_id(),
            variant.name()
        ),
        None => println!(
            "Flashing a BARE bootloader: the device will read as unprovisioned and needs \
             its firmware over the wire. Any firmware already installed stops booting. \
             Pass --variant to provision it instead."
        ),
    }

    let mut images = vec![(
        install.bootloader,
        project_address(args, Project::Bootloader)?,
    )];
    if let Some(firmware) = install.firmware {
        images.push((firmware, project_address(args, args.project)?));
    }
    for (image, address) in &images {
        println!("  {} -> 0x{:08X}", image.display(), address);
    }

    run_openocd(args.model, &build_flash_write_instruction(&images))
}

/// The flash address a project is written to, from the model's `memory.ld`.
fn project_address(args: &FlashArgs, project: Project) -> Result<u32> {
    let memory_ld = args.model.model_memory_ld()?;
    helpers::read_symbol(&memory_ld, project.flash_start_symbol()?)
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

fn build_flash_write_instruction(images: &[(PathBuf, u32)]) -> String {
    let mut instr = String::from("init; reset halt; ");
    for (binary, address) in images {
        instr.push_str(&format!(
            "flash write_image erase {} 0x{:X}; ",
            binary.display(),
            address
        ));
    }
    instr.push_str("exit");
    instr
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
    use std::path::PathBuf;

    use super::{build_flash_erase_instruction, build_flash_write_instruction};
    use crate::args::FlashSection;

    #[test]
    fn builds_flash_write_instruction() {
        let instruction =
            build_flash_write_instruction(&[(PathBuf::from("/tmp/fw.bin"), 0x0800_4000)]);

        assert_eq!(
            instruction,
            "init; reset halt; flash write_image erase /tmp/fw.bin 0x8004000; exit"
        );
    }

    /// A pq_secure release writes bootloader and firmware in ONE OpenOCD run.
    #[test]
    fn builds_flash_write_instruction_for_several_images() {
        let instruction = build_flash_write_instruction(&[
            (PathBuf::from("/tmp/bootloader.bin"), 0x0C01_E000),
            (PathBuf::from("/tmp/universal.bin"), 0x0C06_E000),
        ]);

        assert_eq!(
            instruction,
            "init; reset halt; \
             flash write_image erase /tmp/bootloader.bin 0xC01E000; \
             flash write_image erase /tmp/universal.bin 0xC06E000; exit"
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
