use anyhow::{Context, Result, ensure};
use std::fs;

use crate::{
    args::{CombineArgs, Model, Project},
    helpers, postbuild,
};

const COMBINED_PREFIX: &str = "combined-";

/// Byte used to pad the gaps between combined sections. Matches the original
/// `combine_firmware.py`, which padded with zero bytes.
const SECTION_PADDING: u8 = 0x00;

fn load_binary(model: Model, project: Project) -> Result<Vec<u8>> {
    let path = helpers::artifacts_dir(model)?.join(format!("{}.bin", project.binary_name()));
    println!("Loading `{}`", path.display());
    let data = fs::read(&path)
        .with_context(|| format!("Failed to read binary file `{}`", path.display()))?;
    Ok(data)
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

/// Combines multiple firmware projects into a single binary for flashing.
///
/// The combined image starts at `BOARDLOADER_START` (the address it is flashed
/// to) and places every section at its real offset within flash, padding the
/// gaps between sections.
pub fn combine(args: CombineArgs) -> Result<()> {
    let memory_ld = args.model.model_memory_ld()?;

    // All offsets are relative to the boardloader, which sits at the start of
    // the combined image.
    let base = helpers::read_symbol(&memory_ld, "BOARDLOADER_START")?;
    let offset_of = |symbol: &str| -> Result<usize> {
        Ok((helpers::read_symbol(&memory_ld, symbol)? - base) as usize)
    };

    let mut binary = Vec::new();

    place_section(
        &mut binary,
        0,
        &load_binary(args.model, Project::Boardloader)?,
    )?;

    let bootloader_off = offset_of("BOOTLOADER_START")?;

    match args.project {
        Project::Bootloader => {
            place_section(
                &mut binary,
                bootloader_off,
                &load_binary(args.model, Project::Bootloader)?,
            )?;
        }

        Project::BootloaderCi => {
            place_section(
                &mut binary,
                bootloader_off,
                &load_binary(args.model, Project::BootloaderCi)?,
            )?;
        }

        Project::Firmware => {
            place_section(
                &mut binary,
                bootloader_off,
                &load_binary(args.model, Project::Bootloader)?,
            )?;
            place_section(
                &mut binary,
                offset_of("FIRMWARE_START")?,
                &load_binary(args.model, Project::Firmware)?,
            )?;
        }

        Project::Prodtest => {
            place_section(
                &mut binary,
                bootloader_off,
                &load_binary(args.model, Project::Bootloader)?,
            )?;
            place_section(
                &mut binary,
                offset_of("FIRMWARE_START")?,
                &load_binary(args.model, Project::Prodtest)?,
            )?;
        }

        _ => anyhow::bail!(
            "Combining is not supported for `{}`",
            args.project.binary_name()
        ),
    }

    // Save the combined binary to the artifacts directory
    let artifact_dir = helpers::artifacts_dir(args.model)?;
    helpers::ensure_directory(&artifact_dir)?;

    let output_path = artifact_dir.join(format!(
        "{}{}.bin",
        COMBINED_PREFIX,
        args.project.binary_name()
    ));
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
    use super::{SECTION_PADDING, place_section};

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

    #[test]
    fn rejects_overlapping_sections() {
        let mut binary = Vec::new();
        place_section(&mut binary, 0, &[1, 2, 3, 4]).unwrap();
        // Offset 2 falls inside the already-placed first section.
        assert!(place_section(&mut binary, 2, &[5, 6]).is_err());
    }
}
