use std::fs;
use std::ops::RangeInclusive;

use anyhow::{Context, Result, ensure};

use crate::args::{FlashArgs, FlashEraseArgs, FlashSection, Model, ResetArgs};
use crate::{combine, device, helpers, openocd};

/// Flashes the specified project to the device.
pub fn flash_project(args: FlashArgs) -> Result<()> {
    ensure!(
        args.project.flashable(),
        "Flashing is not supported for `{}`",
        args.project.binary_name()
    );

    // An explicitly given file replaces the build artifact; the addresses below
    // are still derived from the project + model, so a prebuilt binary lands
    // exactly where that project belongs.
    let binary = match args.file {
        Some(ref file) => file.clone(),
        None => {
            helpers::artifacts_dir(args.model)?.join(format!("{}.bin", args.project.binary_name()))
        }
    };

    let binary = binary
        .canonicalize()
        .with_context(|| format!("Failed to locate `{}` for flashing", binary.display()))?;

    let memory_ld = args.model.model_memory_ld()?;
    let content = fs::read_to_string(&memory_ld)
        .with_context(|| format!("Failed to read `{}`", memory_ld.display()))?;
    let image =
        fs::read(&binary).with_context(|| format!("Failed to read `{}`", binary.display()))?;
    let segments = helpers::project_segments(&content, args.project, &image)?;

    device::check(args.model, args.skip_device_check)?;

    println!("Flashing `{}`", binary.display());
    flash_segments(args.model, &segments)
}

/// Flash the combined image: the whole boot chain in one write.
///
/// Written byte for byte as `xtask combine` produced it, placed by
/// [`combine::combined_segments`]. The project name only says WHICH combined
/// image; the image always starts at the bottom of the chain, so nothing about
/// its contents is decided here.
pub fn flash_combined(args: FlashArgs) -> Result<()> {
    ensure!(
        combine::supported(args.project),
        "there is no combined image for `{}` -- a combined image runs from the \
         boardloader up to one of: {}",
        args.project.binary_name(),
        combine::supported_projects()
    );

    // `--file` names the combined image to write, the same way it replaces the
    // artifact on the single-project path: WHAT is written, never WHERE.
    let binary = match args.file {
        Some(ref file) => file
            .canonicalize()
            .with_context(|| format!("Failed to locate `{}` for flashing", file.display()))?,
        None => {
            let built = combine::combined_artifact(args.model, args.project)?;
            ensure!(
                built.exists(),
                "no combined image at {binary} -- build one first:\n             \
                 xtask combine {project} -m {model}",
                binary = built.display(),
                project = args.project.binary_name(),
                model = args.model.model_id(),
            );
            built
        }
    };

    let memory_ld = args.model.model_memory_ld()?;
    let content = fs::read_to_string(&memory_ld)
        .with_context(|| format!("Failed to read `{}`", memory_ld.display()))?;
    let image =
        fs::read(&binary).with_context(|| format!("Failed to read `{}`", binary.display()))?;
    let segments = combine::combined_segments(&content, &image)?;

    device::check(args.model, args.skip_device_check)?;

    println!(
        "Flashing the combined `{}` image `{}`",
        args.project.binary_name(),
        binary.display()
    );
    flash_segments(args.model, &segments)
}

/// Erase specified flash section. The section boundaries are determined by
/// reading symbols from the model's memory.ld file.
pub fn flash_erase(args: FlashEraseArgs) -> Result<()> {
    let mem_ld = args.model.model_memory_ld()?;
    let content = fs::read_to_string(&mem_ld)
        .with_context(|| format!("Failed to read `{}`", mem_ld.display()))?;
    let sectors = sectors_to_erase(&content, args.section)?;

    device::check(args.model, args.skip_device_check)?;
    match sectors {
        Some(sectors) => openocd::erase_sectors(args.model, &sectors),
        None => openocd::erase_all(args.model),
    }
}

/// Resets the connected device.
pub fn reset(args: ResetArgs) -> Result<()> {
    println!("Resetting `{:?}`", args.model);

    openocd::reset(args.model)
}

/// Flashes `(address, bytes)` segments, each written to its own address.
fn flash_segments(model: Model, segments: &[(u32, &[u8])]) -> Result<()> {
    for (i, (address, data)) in segments.iter().enumerate() {
        println!(
            "Writing segment {}/{} ({} bytes) to address 0x{:08X}",
            i + 1,
            segments.len(),
            data.len(),
            address
        );
    }

    openocd::write(model, segments)
}

/// The flash sector ranges making up `section`, or `None` for the whole flash.
fn sectors_to_erase(
    content: &str,
    section: FlashSection,
) -> Result<Option<Vec<RangeInclusive<u32>>>> {
    let sectors = |symbol_prefix: &str| -> Result<RangeInclusive<u32>> {
        let start =
            helpers::read_symbol_from_content(content, &format!("{}_SECTOR_START", symbol_prefix))?;
        let end =
            helpers::read_symbol_from_content(content, &format!("{}_SECTOR_END", symbol_prefix))?;
        Ok(start..=end)
    };

    let ranges = match section {
        FlashSection::All => return Ok(None),
        FlashSection::Boardloader => vec![sectors("BOARDLOADER")?],
        FlashSection::Bootloader => vec![sectors("BOOTLOADER")?],
        FlashSection::Firmware => {
            if helpers::read_symbol_from_content(content, "FIRMWARE_P1_SECTOR_START").is_ok() {
                vec![sectors("FIRMWARE_P1")?, sectors("FIRMWARE_P2")?]
            } else {
                vec![sectors("FIRMWARE")?]
            }
        }
        FlashSection::Storage => vec![sectors("STORAGE_1")?, sectors("STORAGE_2")?],
    };
    Ok(Some(ranges))
}

#[cfg(test)]
mod tests {
    use super::sectors_to_erase;
    use crate::args::FlashSection;

    #[test]
    fn erases_both_firmware_parts_on_dual_bank_layouts() {
        let content = "\
FIRMWARE_P1_SECTOR_START = 5;\n\
FIRMWARE_P1_SECTOR_END = 10;\n\
FIRMWARE_P2_SECTOR_START = 11;\n\
FIRMWARE_P2_SECTOR_END = 18;\n";

        assert_eq!(
            sectors_to_erase(content, FlashSection::Firmware).unwrap(),
            Some(vec![5..=10, 11..=18])
        );
    }

    #[test]
    fn erases_both_storage_areas() {
        let content = "\
STORAGE_1_SECTOR_START = 2;\n\
STORAGE_1_SECTOR_END = 3;\n\
STORAGE_2_SECTOR_START = 4;\n\
STORAGE_2_SECTOR_END = 5;\n";

        assert_eq!(
            sectors_to_erase(content, FlashSection::Storage).unwrap(),
            Some(vec![2..=3, 4..=5])
        );
    }

    #[test]
    fn erases_everything_for_all() {
        assert_eq!(sectors_to_erase("", FlashSection::All).unwrap(), None);
    }
}
