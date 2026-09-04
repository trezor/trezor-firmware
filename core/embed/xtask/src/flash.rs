use std::path::Path;
use std::{fs, process};

use anyhow::{Context, Result, ensure};

use crate::args::{FlashArgs, FlashEraseArgs, FlashSection, Model, ResetArgs};
use crate::helpers;

/// Flashes the specified project to the device using OpenOCD.
pub fn flash(args: FlashArgs) -> Result<()> {
    ensure!(
        args.project.flashable(),
        "Flashing is not supported for `{}`",
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

    let flash_start = args.project.flash_start_symbol()?;
    let memory_ld = args.model.model_memory_ld()?;
    let address = helpers::read_symbol(&memory_ld, flash_start)?;

    println!(
        "Flashing `{}` to address 0x{:08X}",
        binary.display(),
        address
    );

    let flash_instruction = build_flash_write_instruction(&binary, address)?;

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

fn build_flash_write_instruction(binary: &Path, address: u32) -> Result<String> {
    Ok(format!(
        "init; reset halt; flash write_image erase {} 0x{:X}; exit",
        tcl_quote_path(binary)?,
        address
    ))
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

    use super::{build_flash_erase_instruction, build_flash_write_instruction, tcl_quote_path};
    use crate::args::FlashSection;

    #[test]
    fn builds_flash_write_instruction() {
        let instruction =
            build_flash_write_instruction(Path::new("/tmp/fw.bin"), 0x0800_4000).unwrap();

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
