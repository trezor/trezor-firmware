use std::fs;
use std::path::{Path, PathBuf};

use anyhow::{Context, Result, ensure};
use clap::ValueEnum;

use crate::args::{CombineArgs, Model, Project};
use crate::{helpers, postbuild};

const COMBINED_PREFIX: &str = "combined-";

/// Where `xtask combine` writes a project's combined image, and so where
/// `xtask flash --combined` reads it from.
pub fn combined_artifact(model: Model, project: Project) -> Result<PathBuf> {
    Ok(helpers::artifacts_dir(model)?
        .join(format!("{COMBINED_PREFIX}{}.bin", project.binary_name())))
}

/// The flash address a combined image starts at: the boardloader's, since
/// the image runs from the bottom of the boot chain up.
fn combined_start(memory_ld: &str) -> Result<u32> {
    helpers::read_symbol_from_content(memory_ld, "BOARDLOADER_START")
}

/// Where a combined image lands in flash, as `(address, bytes)` pairs: one
/// segment from [`combined_start`], gaps included, exactly as [`combine`] laid
/// it out.
pub fn combined_segments<'a>(memory_ld: &str, image: &'a [u8]) -> Result<Vec<(u32, &'a [u8])>> {
    Ok(vec![(combined_start(memory_ld)?, image)])
}

/// Byte used to pad the gaps between combined sections. Matches the original
/// `combine_firmware.py`, which padded with zero bytes.
const SECTION_PADDING: u8 = 0x00;

/// Byte used to pad a region the boot chain ERASES on first boot.
///
/// Flash reads as 0xFF when erased, so padding such a region with anything else
/// makes the device stop matching the image the moment it boots -- and a
/// factory line that verifies by reading flash back would fail. Padded with the
/// erased value, the erase is a no-op (`boot_ucb_erase` even skips it) and the
/// image stays byte-identical.
const ERASED_PADDING: u8 = 0xFF;

fn load_binary(model: Model, project: Project) -> Result<Vec<u8>> {
    let path = helpers::artifacts_dir(model)?.join(format!("{}.bin", project.binary_name()));
    println!("Loading `{}`", path.display());
    let data = fs::read(&path)
        .with_context(|| format!("Failed to read binary file `{}`", path.display()))?;
    Ok(data)
}

/// Overwrite the UCB region with the erased byte, if this model has one.
///
/// The region falls in the gap between the boardloader and the bootloader, so
/// it is already padding; this only corrects the value. See [`ERASED_PADDING`].
fn erase_boot_ucb(binary: &mut [u8], memory_ld: &Path, base: u32) -> Result<()> {
    let content = fs::read_to_string(memory_ld)
        .with_context(|| format!("Failed to read `{}`", memory_ld.display()))?;
    let Ok(start) = helpers::read_symbol_from_content(&content, "BOOTUCB_START") else {
        return Ok(());
    };
    let size = helpers::read_symbol_from_content(&content, "BOOTUCB_MAXSIZE")?;

    let from = (start - base) as usize;
    let to = from + size as usize;
    ensure!(
        to <= binary.len(),
        "the UCB region (0x{start:X}..0x{:X}) runs past the combined image",
        start + size,
    );
    binary[from..to].fill(ERASED_PADDING);
    println!(
        "Padding the UCB region 0x{start:X}..0x{:X} with 0x{ERASED_PADDING:02X} (erased state)",
        start + size
    );
    Ok(())
}

/// Places `data` at `offset` within `binary`, padding any preceding gap with
/// [`SECTION_PADDING`]. Each section must start at or after the current end of
/// the image, otherwise the sections would overlap.
fn place_section(binary: &mut Vec<u8>, offset: usize, data: &[u8]) -> Result<()> {
    ensure!(
        binary.len() <= offset,
        "combined sections overlap: next section starts at 0x{:X} but image is already 0x{:X} bytes",
        offset,
        binary.len()
    );
    binary.resize(offset, SECTION_PADDING);
    binary.extend_from_slice(data);
    Ok(())
}

/// The projects a combined image holds ABOVE the boardloader, in flash order.
/// Where each one lands comes from [`helpers::project_segments`]. `None` if the
/// project cannot head a combined image.
///
/// This is the single source of truth for what can be combined. `flash
/// --combined` asks the same question through [`supported`] rather than keeping
/// its own list, so the two cannot disagree about which projects are valid.
fn projects(project: Project) -> Option<&'static [Project]> {
    Some(match project {
        Project::Bootloader => &[Project::Bootloader],
        Project::BootloaderCi => &[Project::BootloaderCi],
        Project::Firmware => &[Project::Bootloader, Project::Firmware],
        Project::Prodtest => &[Project::Bootloader, Project::Prodtest],
        _ => return None,
    })
}

/// Whether a combined image can be built for `project` -- see [`projects`].
pub fn supported(project: Project) -> bool {
    projects(project).is_some()
}

/// The projects that can head a combined image, as a comma-separated list.
/// Derived from [`projects`] so error messages cannot name a stale set.
pub fn supported_projects() -> String {
    Project::value_variants()
        .iter()
        .filter(|p| supported(**p))
        .map(|p| p.binary_name())
        .collect::<Vec<_>>()
        .join(", ")
}

/// Combines multiple firmware projects into a single binary for flashing.
///
/// The combined image starts at `BOARDLOADER_START` (the address it is flashed
/// to) and places every project at its real offset within flash, padding the
/// gaps between them. Which projects those are comes from [`projects`].
pub fn combine(args: CombineArgs) -> Result<()> {
    let memory_ld = args.model.model_memory_ld()?;
    let content = fs::read_to_string(&memory_ld)
        .with_context(|| format!("Failed to read `{}`", memory_ld.display()))?;

    // All offsets are relative to the boardloader, which sits at the start of
    // the combined image.
    let base = combined_start(&content)?;

    let projects = projects(args.project).ok_or_else(|| {
        anyhow::anyhow!(
            "Combining is not supported for `{}` -- only {}",
            args.project.binary_name(),
            supported_projects()
        )
    })?;

    let mut binary = Vec::new();

    for project in [Project::Boardloader].iter().chain(projects) {
        let data = load_binary(args.model, *project)?;
        for (address, segment) in helpers::project_segments(&content, *project, &data)? {
            place_section(&mut binary, (address - base) as usize, segment)?;
        }
    }

    erase_boot_ucb(&mut binary, &memory_ld, base)?;

    // Save the combined binary to the artifacts directory
    let artifact_dir = helpers::artifacts_dir(args.model)?;
    helpers::ensure_directory(&artifact_dir)?;

    let output_path = combined_artifact(args.model, args.project)?;
    println!("Writing combined binary to `{}`", output_path.display());
    fs::write(&output_path, &binary).with_context(|| {
        format!(
            "Failed to write combined binary to `{}`",
            output_path.display()
        )
    })?;

    // Publish the combined binary to the `pub` directory
    let version_file = helpers::get_version_file(args.project)?;
    postbuild::publish_artifact(
        &output_path,
        args.project,
        args.model,
        &version_file,
        Some(COMBINED_PREFIX),
        None,
    )?;

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::{
        ERASED_PADDING, SECTION_PADDING, combined_segments, erase_boot_ucb, place_section,
    };

    /// A combined image is written whole from the boardloader, gaps included.
    #[test]
    fn combined_image_is_one_segment_from_the_boardloader() {
        let image = [1u8; 32];
        let segments = combined_segments("BOARDLOADER_START = 0xc004000;\n", &image).unwrap();

        assert_eq!(segments, vec![(0x0c00_4000, &image[..])]);
    }

    #[test]
    fn places_sections_at_their_offsets_and_pads_gaps() {
        let mut binary = Vec::new();
        place_section(&mut binary, 0, &[1, 2, 3]).unwrap();
        // Gap from 3 to 8 must be padded with the padding byte.
        place_section(&mut binary, 8, &[4, 5]).unwrap();

        assert_eq!(
            binary,
            [
                1,
                2,
                3,
                SECTION_PADDING,
                SECTION_PADDING,
                SECTION_PADDING,
                SECTION_PADDING,
                SECTION_PADDING,
                4,
                5
            ]
        );
    }

    /// The UCB region must end up 0xFF even though the gap around it is 0x00:
    /// the boot chain erases it, and the image has to stay byte-identical.
    #[test]
    fn pads_the_ucb_region_with_the_erased_byte() {
        let dir = tempfile::tempdir().unwrap();
        let memory_ld = dir.path().join("memory.ld");
        std::fs::write(
            &memory_ld,
            "BOOTUCB_START = 0xc01c000;\nBOOTUCB_MAXSIZE = 0x4;\n",
        )
        .unwrap();

        let base = 0xc01_b000;
        let mut binary = vec![SECTION_PADDING; 0x2000];
        binary[0] = 0xAA;
        erase_boot_ucb(&mut binary, &memory_ld, base).unwrap();

        assert_eq!(binary[0], 0xAA, "sections outside the region are untouched");
        assert_eq!(&binary[0x1000..0x1004], &[ERASED_PADDING; 4]);
        assert_eq!(binary[0x1004], SECTION_PADDING, "and nothing beyond it");
    }

    /// A model without a UCB region is left alone.
    #[test]
    fn leaves_images_without_a_ucb_region_alone() {
        let dir = tempfile::tempdir().unwrap();
        let memory_ld = dir.path().join("memory.ld");
        std::fs::write(&memory_ld, "BOOTLOADER_START = 0x8020000;\n").unwrap();

        let mut binary = vec![SECTION_PADDING; 16];
        erase_boot_ucb(&mut binary, &memory_ld, 0x800_0000).unwrap();

        assert_eq!(binary, vec![SECTION_PADDING; 16]);
    }

    #[test]
    fn rejects_overlapping_sections() {
        let mut binary = Vec::new();
        place_section(&mut binary, 0, &[1, 2, 3, 4]).unwrap();
        // Offset 2 falls inside the already-placed first section.
        assert!(place_section(&mut binary, 2, &[5, 6]).is_err());
    }
}
