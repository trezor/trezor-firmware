//! Debug probe access through OpenOCD.
//!
//! Everything that talks to the device goes through the operations here --
//! write, erase, reset and read -- so the rest of xtask never builds OpenOCD
//! scripts or parses its log. Each operation is one OpenOCD session over an
//! ST-Link.

use std::io::Write;
use std::ops::RangeInclusive;
use std::path::{Path, PathBuf};
use std::{fs, process};

use anyhow::{Context, Result, anyhow, bail, ensure};

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

/// Halts the device and reads `(address, size)` ranges of memory, returning
/// the bytes of each.
///
/// A read that fails (e.g. read-protected memory) does not fail the others;
/// its result carries OpenOCD's error message instead. Every read goes through
/// a temporary file, which `dump_image` writes -- unlike console output, that
/// works the same in every OpenOCD build.
pub fn read_memory(model: Model, reads: &[(u32, u32)]) -> Result<Vec<Result<Vec<u8>, String>>> {
    let dir = TempDir::new()?;
    let files = (0..reads.len())
        .map(|i| {
            (
                dir.0.join(format!("read-{i}.bin")),
                dir.0.join(format!("read-{i}.err")),
            )
        })
        .collect::<Vec<_>>();

    let script = build_read_script(reads, &files)?;
    // The log is only shown if OpenOCD itself fails; the results are in files.
    run_captured(model, &script)?;

    Ok(reads
        .iter()
        .zip(&files)
        .map(|(read, files)| read_result(*read, files))
        .collect())
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

/// Like [`run`], but returns OpenOCD's output (stdout and stderr, where its
/// log goes) instead of showing it -- unless OpenOCD fails, when the output is
/// printed to explain the failure.
fn run_captured(model: Model, script: &str) -> Result<String> {
    let output = command(model, script)?
        .output()
        .context("Failed to spawn `openocd`")?;

    let mut text = String::from_utf8_lossy(&output.stdout).into_owned();
    text.push_str(&String::from_utf8_lossy(&output.stderr));

    if !output.status.success() {
        eprint!("{text}");
        bail!("`openocd` failed with status: {}", output.status);
    }

    Ok(text)
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

/// Script dumping each read to its data file, or, if the read fails, the
/// error message to its error file.
///
/// The target is resumed before exiting: OpenOCD leaves it halted otherwise,
/// and a refused device would stay frozen until power-cycled.
fn build_read_script(reads: &[(u32, u32)], files: &[(PathBuf, PathBuf)]) -> Result<String> {
    let mut script = String::from("init; reset halt; ");
    for ((address, size), (data, error)) in reads.iter().zip(files) {
        script.push_str(&format!(
            "if {{[catch {{dump_image {} 0x{address:X} {size}}} e]}} \
             {{set f [open {} w]; puts -nonewline $f $e; close $f}}; ",
            tcl_quote_path(data)?,
            tcl_quote_path(error)?,
        ));
    }
    script.push_str("resume; exit");
    Ok(script)
}

/// The bytes a read script dumped for `(address, size)`, or why there are none.
fn read_result(
    (address, size): (u32, u32),
    (data, error): &(PathBuf, PathBuf),
) -> Result<Vec<u8>, String> {
    if let Ok(message) = fs::read_to_string(error) {
        return Err(message);
    }
    match fs::read(data) {
        Ok(bytes) if bytes.len() == size as usize => Ok(bytes),
        Ok(bytes) => Err(format!(
            "read {} of {size} bytes at 0x{address:08X}",
            bytes.len()
        )),
        Err(_) => Err(format!("no data read at 0x{address:08X}")),
    }
}

#[cfg(test)]
mod tests {
    use std::fs;
    use std::path::{Path, PathBuf};

    use super::{
        build_erase_script, build_read_script, build_write_script, read_result, tcl_quote_path,
    };

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

    #[test]
    fn builds_read_script() {
        let files = [
            (PathBuf::from("/tmp/r0.bin"), PathBuf::from("/tmp/r0.err")),
            (PathBuf::from("/tmp/r1.bin"), PathBuf::from("/tmp/r1.err")),
        ];

        assert_eq!(
            build_read_script(&[(0xE004_4000, 4), (0x0C01_BF00, 0x100)], &files).unwrap(),
            "init; reset halt; \
             if {[catch {dump_image {/tmp/r0.bin} 0xE0044000 4} e]} \
             {set f [open {/tmp/r0.err} w]; puts -nonewline $f $e; close $f}; \
             if {[catch {dump_image {/tmp/r1.bin} 0xC01BF00 256} e]} \
             {set f [open {/tmp/r1.err} w]; puts -nonewline $f $e; close $f}; \
             resume; exit"
        );
    }

    fn files(dir: &Path) -> (PathBuf, PathBuf) {
        (dir.join("read.bin"), dir.join("read.err"))
    }

    #[test]
    fn returns_the_dumped_bytes() {
        let dir = tempfile::tempdir().unwrap();
        let files = files(dir.path());
        fs::write(&files.0, b"TRZC").unwrap();

        assert_eq!(read_result((0x1000, 4), &files), Ok(b"TRZC".to_vec()));
    }

    #[test]
    fn keeps_a_failed_read() {
        let dir = tempfile::tempdir().unwrap();
        let files = files(dir.path());
        fs::write(&files.1, "Failed to read memory").unwrap();

        assert_eq!(
            read_result((0x1000, 4), &files),
            Err("Failed to read memory".to_string())
        );
    }

    #[test]
    fn rejects_a_short_or_missing_read() {
        let dir = tempfile::tempdir().unwrap();
        let files = files(dir.path());

        assert!(read_result((0x1000, 4), &files).is_err());
        fs::write(&files.0, b"TR").unwrap();
        assert!(read_result((0x1000, 4), &files).is_err());
    }
}
