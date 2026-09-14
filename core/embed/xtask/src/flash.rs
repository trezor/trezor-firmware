use std::path::{Path, PathBuf};
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
    // by `xtask combine`, so it is written as-is from the boardloader address --
    // before any single-project binary is resolved, since it is not one.
    if args.combined {
        return flash_combined(&args);
    }

    // A pq_secure release is what boots on a Merkle-tree model; the per-project
    // artifacts are not installable. Boardloader and bootloader_ci are not part
    // of a release, so they keep reading their own artifact. An explicit --file
    // overrides the release: the caller named the exact bytes to write.
    if args.file.is_none()
        && args.model.config()?.has_feature("pq_secure_boot")
        && matches!(
            args.project,
            Project::Bootloader | Project::Firmware | Project::Prodtest
        )
    {
        return flash_release(&args);
    }

    ensure!(
        args.variant.is_none(),
        "--variant applies only to a pq_secure release; `{}` here is flashed as a \
         plain binary",
        args.project.binary_name()
    );

    // An explicitly given file replaces the build artifact; the address below is
    // still derived from the project + model, so a prebuilt binary lands exactly
    // where that project belongs.
    let binary = match args.file {
        Some(ref file) => file.clone(),
        None => {
            helpers::artifacts_dir(args.model)?.join(format!("{}.bin", args.project.binary_name()))
        }
    };

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
        &build_flash_write_instruction(&[(binary, address)])?,
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

    // `--file` names the combined image to write, the same way it replaces the
    // artifact on the single-project path: WHAT is written, never WHERE. The
    // address below stays the boardloader's, because that is what a combined
    // image starts at whatever produced it.
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

    // `?`: quoting the path is fallible since the Tcl-quoting validation landed
    // (a path that would break out of the braced word is rejected).
    run_openocd(
        args.model,
        &build_flash_write_instruction(&[(binary, address)])?,
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

    run_openocd(args.model, &build_flash_write_instruction(&images)?)
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

/// Quotes a path for interpolation into an OpenOCD `-c` script.
///
/// The script is handed to openocd as a single argv element, so no shell is
/// involved -- but openocd parses it as Tcl, where an unquoted path containing
/// a space becomes two words and `[`, `$` or `;` change the parse entirely.
/// Tcl braces suppress every substitution, so `{...}` is the correct quoting
/// and the braces are stripped before the command sees its argument.
///
/// What still has to be rejected, since brace quoting cannot express it:
///
/// * Braces, which would close or unbalance the group itself.
/// * Newlines: backslash-newline is the one substitution Tcl *does* perform
///   inside braces, and a raw newline would also break the `;`-separated
///   script.
/// * A path ENDING in a backslash. Interior backslashes are literal inside
///   braces, but Tcl does not count a brace that a backslash quotes when it
///   looks for the matching close brace -- and the close brace here is the one
///   this function appends. `foo\` would become `{foo\}`, whose `\}` is not the
///   terminator, so the rest of the command gets swallowed into the word.
///
/// Interior backslashes are therefore allowed: rejecting them would refuse
/// every Windows-style path for no reason.
fn tcl_quote_path(path: &Path) -> Result<String> {
    let path = path
        .to_str()
        .with_context(|| format!("path is not valid UTF-8: {}", path.display()))?;

    ensure!(
        !path.contains(['{', '}', '\n', '\r']),
        "path cannot be quoted for OpenOCD's Tcl parser \
         (contains a brace or newline): {path}"
    );
    ensure!(
        !path.ends_with('\\'),
        "path cannot be quoted for OpenOCD's Tcl parser \
         (ends in a backslash, which would escape the closing brace): {path}"
    );

    Ok(format!("{{{path}}}"))
}

fn build_flash_write_instruction(images: &[(PathBuf, u32)]) -> Result<String> {
    let mut instr = String::from("init; reset halt; ");
    for (binary, address) in images {
        instr.push_str(&format!(
            "flash write_image erase {} 0x{:X}; ",
            tcl_quote_path(binary)?,
            address
        ));
    }
    instr.push_str("exit");
    Ok(instr)
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

    use super::{build_flash_erase_instruction, build_flash_write_instruction, tcl_quote_path};
    use crate::args::FlashSection;

    #[test]
    fn builds_flash_write_instruction() {
        let instruction =
            build_flash_write_instruction(&[(PathBuf::from("/tmp/fw.bin"), 0x0800_4000)])
                .unwrap();

        assert_eq!(
            instruction,
            "init; reset halt; flash write_image erase {/tmp/fw.bin} 0x8004000; exit"
        );
    }

    /// `--file` accepts any path the user types, and openocd parses the `-c`
    /// script as Tcl: unquoted, a space would split the filename into two Tcl
    /// words and `[...]` would be command substitution.
    #[test]
    fn quotes_paths_that_tcl_would_otherwise_reparse() {
        let instruction =
            build_flash_write_instruction(Path::new("/my builds/fw [v2].bin"), 0x0800_4000)
                .unwrap();

        assert_eq!(
            instruction,
            "init; reset halt; flash write_image erase {/my builds/fw [v2].bin} 0x8004000; exit"
        );
    }

    #[test]
    fn rejects_paths_that_cannot_be_brace_quoted() {
        // A brace would end (or unbalance) the group itself; a newline is the
        // one thing Tcl still substitutes inside braces. A TRAILING backslash
        // would escape the closing brace this code appends, so the rest of the
        // command would be swallowed into the word.
        for bad in [
            "/tmp/fw{.bin",
            "/tmp/fw}.bin",
            "/tmp/fw\n.bin",
            "/tmp/fw\r.bin",
            "/tmp/builds\\",
        ] {
            assert!(
                tcl_quote_path(Path::new(bad)).is_err(),
                "expected {bad:?} to be rejected"
            );
        }

        assert!(tcl_quote_path(Path::new("/tmp/fw.bin")).is_ok());
        assert!(tcl_quote_path(Path::new("/my builds/fw.bin")).is_ok());
    }

    /// Interior backslashes are literal inside Tcl braces, so a Windows-style
    /// path must survive quoting untouched rather than being refused.
    #[test]
    fn accepts_interior_backslashes() {
        assert_eq!(
            tcl_quote_path(Path::new(r"C:\builds\fw.bin")).unwrap(),
            r"{C:\builds\fw.bin}"
        );
        // An even run of trailing backslashes still leaves the close brace
        // countable, but the check is deliberately conservative about the end
        // of the path -- only the interior case is guaranteed.
        assert_eq!(
            tcl_quote_path(Path::new(r"/my builds\v2/fw.bin")).unwrap(),
            r"{/my builds\v2/fw.bin}"
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
