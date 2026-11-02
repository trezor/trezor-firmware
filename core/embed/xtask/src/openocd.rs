//! Debug probe access through OpenOCD.
//!
//! Everything that talks to the device goes through the operations here --
//! write, erase and reset -- so the rest of xtask never builds OpenOCD
//! scripts or parses its log. Each operation is one OpenOCD session over an
//! ST-Link.

use std::io::Write;
use std::ops::RangeInclusive;
use std::path::{Path, PathBuf};
use std::{fs, process};

use anyhow::{Context, Result, anyhow, ensure};

use crate::args::Model;

/// Writes `(address, bytes)` segments, each to its own address.
///
/// Every segment goes through a temporary file, since `flash write_image`
/// takes a whole file.
pub fn write(model: Model, segments: &[(u32, &[u8])]) -> Result<()> {
    let dir = TempDir::new()?;
    let mut files = Vec::new();
    for (i, (address, data)) in segments.iter().enumerate() {
        let path = dir.0.join(format!("segment-{i}.bin"));
        fs::File::create_new(&path)
            .and_then(|mut file| file.write_all(data))
            .with_context(|| format!("Failed to write `{}`", path.display()))?;
        files.push((path, *address));
    }

    run(model, &build_write_script(&files)?)
}

/// Erases the whole flash.
pub fn erase_all(model: Model) -> Result<()> {
    run(
        model,
        "init; reset halt; flash info 0; flash erase_sector 0 0 last; flash erase_check 0; exit",
    )
}

/// Erases the given ranges of flash sectors.
pub fn erase_sectors(model: Model, sectors: &[RangeInclusive<u32>]) -> Result<()> {
    run(model, &build_erase_script(sectors))
}

/// Resets the device and lets it run.
pub fn reset(model: Model) -> Result<()> {
    run(model, "init; reset; exit")
}

/// OpenOCD's target config for the model's MCU.
fn target_config(model: Model) -> Result<&'static str> {
    match model.config()?.mcu.as_str() {
        "stm32f427" | "stm32f429" => Ok("target/stm32f4x.cfg"),
        "stm32u58" | "stm32u5g" | "stm32u5a" => Ok("target/stm32u5x.cfg"),
        mcu => Err(anyhow!("Unknown MCU: {mcu}")),
    }
}

/// Runs an OpenOCD script against the connected device for the given model.
fn run(model: Model, script: &str) -> Result<()> {
    let status = command(model, script)?
        .status()
        .context("Failed to spawn `openocd`")?;

    ensure!(status.success(), "`openocd` failed with status: {status}");

    Ok(())
}

fn command(model: Model, script: &str) -> Result<process::Command> {
    let mut command = process::Command::new("openocd");
    command
        .args(["-f", "interface/stlink.cfg"])
        .args(["-c", "transport select hla_swd"])
        .args(["-f", target_config(model)?])
        .arg("-c")
        .arg(script);
    Ok(command)
}

/// A freshly created directory under the system temp dir, removed on drop.
///
/// `create` fails if the path already exists, so nothing planted there
/// beforehand (a file, or a symlink elsewhere) is ever written through. On Unix
/// the directory is owner-only from the start, so no other user can swap a
/// segment file before OpenOCD reads it.
struct TempDir(PathBuf);

impl TempDir {
    fn new() -> Result<Self> {
        let nanos = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map_or(0, |d| d.subsec_nanos());
        let path = std::env::temp_dir().join(format!("xtask-flash-{}-{nanos:08x}", process::id()));
        let mut builder = fs::DirBuilder::new();
        #[cfg(unix)]
        std::os::unix::fs::DirBuilderExt::mode(&mut builder, 0o700);
        builder
            .create(&path)
            .with_context(|| format!("Failed to create `{}`", path.display()))?;
        Ok(Self(path))
    }
}

impl Drop for TempDir {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
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

fn build_write_script(files: &[(PathBuf, u32)]) -> Result<String> {
    let mut script = String::from("init; reset halt; ");
    for (path, address) in files {
        script.push_str(&format!(
            "flash write_image erase {} 0x{:X}; ",
            tcl_quote_path(path)?,
            address
        ));
    }
    script.push_str("exit");
    Ok(script)
}

fn build_erase_script(sectors: &[RangeInclusive<u32>]) -> String {
    let mut script = String::from("init; reset halt; flash info 0; ");
    for range in sectors {
        script.push_str(&format!(
            "flash erase_sector 0 {} {}; ",
            range.start(),
            range.end()
        ));
    }
    script.push_str("exit");
    script
}

#[cfg(test)]
mod tests {
    use std::path::{Path, PathBuf};

    use super::{build_erase_script, build_write_script, tcl_quote_path};

    #[test]
    fn builds_write_script() {
        let script = build_write_script(&[(PathBuf::from("/tmp/fw.bin"), 0x0800_4000)]).unwrap();

        assert_eq!(
            script,
            "init; reset halt; flash write_image erase {/tmp/fw.bin} 0x8004000; exit"
        );
    }

    #[test]
    fn builds_write_script_for_several_segments() {
        let script = build_write_script(&[
            (PathBuf::from("/tmp/p1.bin"), 0x0804_0000),
            (PathBuf::from("/tmp/p2.bin"), 0x0812_0000),
        ])
        .unwrap();

        assert_eq!(
            script,
            "init; reset halt; flash write_image erase {/tmp/p1.bin} 0x8040000; \
             flash write_image erase {/tmp/p2.bin} 0x8120000; exit"
        );
    }

    /// `--file` accepts any path the user types, and openocd parses the `-c`
    /// script as Tcl: unquoted, a space would split the filename into two Tcl
    /// words and `[...]` would be command substitution.
    #[test]
    fn quotes_paths_that_tcl_would_otherwise_reparse() {
        let script =
            build_write_script(&[(PathBuf::from("/my builds/fw [v2].bin"), 0x0800_4000)]).unwrap();

        assert_eq!(
            script,
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
    fn builds_erase_script() {
        assert_eq!(
            build_erase_script(&[5..=10, 11..=18]),
            "init; reset halt; flash info 0; \
             flash erase_sector 0 5 10; flash erase_sector 0 11 18; exit"
        );
    }
}
