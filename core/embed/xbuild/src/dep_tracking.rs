use std::cell::Cell;
use std::fs;
use std::io::{self, Write};
use std::path::{Path, PathBuf};
use std::time::SystemTime;

use color_eyre::Result;
use color_eyre::eyre::{WrapErr, ensure};

use crate::cargo_out;
use crate::helpers::{
    delete_file_if_exists, emit_rerun_if_changed, ensure_parent_directory, trace,
};

/// Runs a command with dependency tracking and optional C compiler dependency
/// file support.
///
/// Executes the command if any input is newer than any output, any output is
/// missing, or the command arguments have changed (tracked via a .dep file).
//
/// The .dep file, named after the first output with a .dep extension (e.g.,
/// build/main.o.dep), records arguments and dependencies and is
/// updated on each run.
///
/// # Arguments
/// * `cmd` - The command to run.
/// * `inputs` - Input files to check for changes.
/// * `outputs` - Output files to check for existence and modification time.
///
/// # Returns
/// * `Result<()>` - Ok if the command was run or skipped successfully, Err
///   otherwise.
pub fn run_command<I, O, In, Out>(
    cmd: &mut std::process::Command,
    inputs: In,
    outputs: Out,
) -> Result<()>
where
    In: IntoIterator<Item = I>,
    Out: IntoIterator<Item = O>,
    I: AsRef<Path>,
    O: AsRef<Path>,
{
    run_command_with_cc_dep(cmd, inputs, outputs, None)
}

/// Runs a command with dependency tracking and optional C compiler dependency
/// file support.
///
/// Executes the command if any input is newer than any output, any output is
/// missing, or the command arguments have changed (tracked via a .dep file).
//
/// The .dep file, named after the first output with a .dep extension (e.g.,
/// build/main.o.dep), records arguments and dependencies and is
/// updated on each run.
///
/// If `cc_dep`` is given, it should be a dependency file (e.g., .d from
/// a C compiler); if missing or if any of its dependencies are newer
/// than the outputs, the command is re-run.
///
/// # Arguments
/// * `cmd` - The command to run.
/// * `inputs` - Input files to check for changes.
/// * `outputs` - Output files to check for existence and modification time.
/// * `cc_dep` - Optional path to a C compiler dependency file.
///
/// # Returns
/// * `Result<()>` - Ok if the command was run or skipped successfully, Err
///   otherwise.
pub fn run_command_with_cc_dep<I, O, In, Out>(
    cmd: &mut std::process::Command,
    inputs: In,
    outputs: Out,
    cc_dep: Option<&Path>,
) -> Result<()>
where
    In: IntoIterator<Item = I>,
    Out: IntoIterator<Item = O>,
    I: AsRef<Path>,
    O: AsRef<Path>,
{
    // Collect command arguments for dependency tracking
    let args = command_to_dep_string(cmd);

    let outputs: Vec<O> = outputs.into_iter().collect();
    ensure!(
        !outputs.is_empty(),
        "run_command requires at least one output file"
    );
    let diag_path = diag_file_path(&outputs[0]);

    let executed = Cell::new(false);

    run_if_changed(inputs, &outputs, Some(args.as_str()), cc_dep, || {
        executed.set(true);

        // Run the command
        let cmd_output = cmd
            .output()
            .with_context(|| format!("Failed to execute {:?}", cmd))?;

        // Report the command's own diagnostics - warnings on success, errors on
        // failure - before turning the exit status into an error.
        report_command_output(&cmd_output, true);

        // Check if the command executed successfully
        ensure!(
            cmd_output.status.success(),
            command_failed_error(cmd, cmd_output.status)
        );

        remember_diagnostics(&diag_path, &diagnostics_text(&cmd_output, true))?;

        trace!("@@ command executed: {:?}", cmd);

        Ok(())
    })?;

    if !executed.get() {
        replay_diagnostics(&diag_path);
    }

    Ok(())
}

/// Runs a command with dependency tracking and captures its stdout to an
/// output file.
///
/// Executes the command if any input is newer than any output, any output is
/// missing, or the command arguments have changed (tracked via a .dep file).
//
/// The .dep file, named after the first output with a .dep extension (e.g.,
/// build/main.o.dep), records arguments and dependencies and is
/// updated on each run.
///
/// # Arguments
/// * `cmd` - The command to run.
/// * `inputs` - Input files to check for changes.
/// * `output` - Output file to check for existence and modification time.
///
/// # Returns
/// * `Result<()>` - Ok if the command was run or skipped successfully, Err
///   otherwise.
pub fn run_command_to_file<I, O, In>(
    cmd: &mut std::process::Command,
    inputs: In,
    output: O,
) -> Result<()>
where
    In: IntoIterator<Item = I>,
    I: AsRef<Path>,
    O: AsRef<Path>,
{
    // Collect command arguments for dependency tracking
    let args = command_to_dep_string(cmd);

    let diag_path = diag_file_path(&output);
    let executed = Cell::new(false);

    run_if_changed(inputs, [&output], Some(&args), None, || {
        executed.set(true);

        // Remove existing output file to ensure we don't accidentally read
        // stale data if the command fails
        delete_file_if_exists(&output)?;

        // Run the command
        let cmd_output = cmd
            .output()
            .with_context(|| format!("Failed to execute {:?}", cmd))?;

        // Only stderr is reported here - stdout is the payload written below
        report_command_output(&cmd_output, false);

        // Check if the command executed successfully
        ensure!(
            cmd_output.status.success(),
            command_failed_error(cmd, cmd_output.status)
        );

        remember_diagnostics(&diag_path, &diagnostics_text(&cmd_output, false))?;

        // Ensure the output directory exists before writing the output
        ensure_parent_directory(output.as_ref())?;

        // Write the command's stdout to the output file
        fs::write(&output, &cmd_output.stdout)
            .with_context(|| format!("Failed to write to {}", output.as_ref().display()))?;

        trace!("@@ command executed: {:?}", cmd);

        Ok(())
    })?;

    if !executed.get() {
        replay_diagnostics(&diag_path);
    }

    Ok(())
}

/// Checks if any of the input files are newer than any of the output files.
///
/// Returns true if any input file is newer than the oldest output file, or if
/// any output is missing.
///
/// # Arguments
/// * `inputs` - Slice of input file paths.
/// * `outputs` - Slice of output file paths.
///
/// # Returns
/// * `bool` - True if inputs are newer or outputs are missing, false otherwise.
pub fn needs_rebuild<I, O>(inputs: &[I], outputs: &[O]) -> bool
where
    I: AsRef<Path>,
    O: AsRef<Path>,
{
    let modified_time = |path: &Path| fs::metadata(path).and_then(|meta| meta.modified());

    let mut newest_input = SystemTime::UNIX_EPOCH;
    for input in inputs {
        let modified = match modified_time(input.as_ref()) {
            Ok(time) => time,
            Err(_) => return true,
        };
        newest_input = newest_input.max(modified);
    }

    let mut oldest_output = None::<SystemTime>;
    for output in outputs {
        let modified = match modified_time(output.as_ref()) {
            Ok(time) => time,
            Err(_) => return true,
        };

        oldest_output = Some(match oldest_output {
            Some(oldest) => oldest.min(modified),
            None => modified,
        });
    }

    match oldest_output {
        Some(oldest) => newest_input > oldest,
        None => true,
    }
}

/// Constructs the path of the file remembering an output's diagnostics.
fn diag_file_path(output: impl AsRef<Path>) -> PathBuf {
    let mut diag_path = output.as_ref().as_os_str().to_os_string();
    diag_path.push(".diag");
    PathBuf::from(diag_path)
}

/// Collects the streams of `cmd_output` that carry diagnostics rather than
/// payload.
fn diagnostics_text(cmd_output: &std::process::Output, with_stdout: bool) -> String {
    let stdout: &[u8] = if with_stdout { &cmd_output.stdout } else { &[] };

    let mut text = String::from_utf8_lossy(stdout).into_owned();
    text.push_str(&String::from_utf8_lossy(&cmd_output.stderr));
    text
}

/// Remembers a command's diagnostics beside its output, or clears the previous
/// ones when this run had nothing to say.
///
/// Cargo does this for `rustc`: a warning is shown on every build until the
/// source is fixed, not only on the build that happened to compile it. Build
/// scripts get no such service - a warning is reported once and then vanishes as
/// soon as the object file is up to date - so it is stored here and replayed by
/// [`replay_diagnostics`].
///
/// Only reached once the command has succeeded. A failed command leaves whatever
/// was here before, which is harmless: its outputs have been deleted, so the
/// next build recompiles it and overwrites this file rather than replaying it.
fn remember_diagnostics(diag_path: &Path, text: &str) -> Result<()> {
    if text.trim().is_empty() {
        return delete_file_if_exists(diag_path);
    }

    ensure_parent_directory(diag_path)?;
    fs::write(diag_path, text).with_context(|| format!("Failed to write {}", diag_path.display()))
}

/// Re-emits the diagnostics remembered for an output that did not need
/// rebuilding, so an unfixed warning survives a cached build.
fn replay_diagnostics(diag_path: &Path) {
    if let Ok(text) = fs::read_to_string(diag_path) {
        cargo_out::warning(text);
    }
}

/// Constructs a dependency file path for the given output file.
fn dep_file_path(output: impl AsRef<Path>) -> PathBuf {
    let mut dep_path = output.as_ref().as_os_str().to_os_string();
    dep_path.push(".dep");
    PathBuf::from(dep_path)
}

fn path_to_string(path: impl AsRef<Path>) -> String {
    path.as_ref().to_string_lossy().into_owned()
}

fn dep_file_contents(
    inputs: &[impl AsRef<Path>],
    outputs: &[impl AsRef<Path>],
    args: Option<&str>,
) -> String {
    std::iter::once("--args--".to_owned())
        .chain(args.into_iter().flat_map(str::lines).map(str::to_owned))
        .chain(std::iter::once("--inputs--".to_owned()))
        .chain(inputs.iter().map(path_to_string))
        .chain(std::iter::once("--outputs--".to_owned()))
        .chain(outputs.iter().map(path_to_string))
        .chain(std::iter::once(String::new()))
        .collect::<Vec<_>>()
        .join("\n")
}

/// Converts a Command name and its arguments to a string representation for
/// dependency tracking
fn command_to_dep_string(cmd: &std::process::Command) -> String {
    let mut text = String::new();
    text.push_str(&cmd.get_program().to_string_lossy());
    text.push('\n');
    for arg in cmd.get_args() {
        let arg = arg.to_string_lossy();
        // Diagnostic coloring has no effect on the produced artifacts, so
        // toggling it must not invalidate the dependency cache.
        if arg.starts_with("-fdiagnostics-color") {
            continue;
        }
        text.push_str(&arg);
        text.push('\n');
    }
    text
}

/// Converts a .d file content to a list of dependency paths
fn cc_dep_paths(cc_dep: &str) -> impl Iterator<Item = &str> {
    cc_dep.lines().flat_map(|line| {
        line.split(':')
            .next_back()
            .unwrap_or("")
            .split_whitespace()
            .filter(|path| *path != "\\")
    })
}

/// Runs a function with dependency tracking.
///
/// Executes the function if any input is newer than any output, any output is
/// missing, or the command arguments have changed (tracked via a `.dep` file).
/// The `.dep` file, named after the first output with a `.dep` extension (e.g.,
/// `build/main.o.dep`), records arguments and dependencies and is updated on
/// each run.
///
/// If `cc_dep` is given, it should be a dependency file (e.g., `.d` from a C
/// compiler); if missing or if any of its dependencies are newer than the
/// outputs, the function is re-run.
pub fn run_if_changed<I, O, In, Out, F>(
    inputs: In,
    outputs: Out,
    args: Option<&str>,
    cc_dep: Option<&Path>,
    run_once: F,
) -> Result<()>
where
    In: IntoIterator<Item = I>,
    Out: IntoIterator<Item = O>,
    I: AsRef<Path>,
    O: AsRef<Path>,
    F: FnOnce() -> Result<()>,
{
    let inputs: Vec<I> = inputs.into_iter().collect();
    let outputs: Vec<O> = outputs.into_iter().collect();

    ensure!(
        !outputs.is_empty(),
        "run_if_changed requires at least one output file"
    );

    emit_rerun_if_changed(&inputs);

    let dep_content = dep_file_contents(&inputs, &outputs, args);

    let dep_path = dep_file_path(&outputs[0]);

    let dep_changed =
        !matches!(fs::read_to_string(&dep_path), Ok(content) if content == dep_content);

    let output_missing = outputs.iter().any(|out| !out.as_ref().exists());

    let outputs_stale = needs_rebuild(&inputs, &outputs);

    let cc_dep_missing = cc_dep
        .as_ref()
        .map(|d| !d.to_path_buf().exists())
        .unwrap_or(false);

    let mut cc_dep_newer = false;

    if !cc_dep_missing {
        // If a .d file is provided, check if any of the dependencies
        // it lists are newer than the outputs

        if let Some(cc_dep) = cc_dep {
            let cc_dep = fs::read_to_string(cc_dep)
                .with_context(|| format!("Failed to read .d file {}", cc_dep.display()))?;

            let h_files = cc_dep_paths(&cc_dep).map(PathBuf::from).collect::<Vec<_>>();

            cc_dep_newer = needs_rebuild(&h_files, &outputs);
        }
    }

    let should_run =
        dep_changed || output_missing || outputs_stale || cc_dep_newer || cc_dep_missing;

    if should_run {
        // Delete the existing .dep file so we don't accidentally
        // read stale data next time if the function fails before
        // writing a new .dep file.
        delete_file_if_exists(&dep_path)?;

        ensure_parent_directory(&dep_path)?;

        // Delete outputs before running to avoid accidentally
        // reading stale data if the function fails (or tools
        // doesn't regenerate all outputs properly)
        for output in outputs {
            delete_file_if_exists(&output)?;
        }

        run_once()?;

        // Write the .dep file to track the command
        fs::write(&dep_path, dep_content)
            .with_context(|| format!("Failed to write dep file to {}", dep_path.display()))?;
    }

    if let Some(cc_dep) = cc_dep {
        ensure!(
            cc_dep.exists(),
            "Expected .d file {} does not exist",
            cc_dep.display()
        );

        // Add the .d file as a dependency to trigger re-run when it changes
        if let Ok(content) = fs::read_to_string(cc_dep) {
            let files = cc_dep_paths(&content).map(PathBuf::from);
            emit_rerun_if_changed(files);
        }
    }

    Ok(())
}

/// Reports a command's captured output to the user.
///
/// Which channel carries it depends on the outcome, because Cargo treats a build
/// script's streams differently depending on whether the script fails:
///
/// * A **failed** command's output goes straight to stderr, which Cargo shows
///   verbatim. Writing it as-is rather than folding it into an error message
///   keeps the compiler's own formatting - carets, colors, multi-line context -
///   and keeps the error reporter from swallowing all but the first line.
///
/// * A **successful** command's output goes through `cargo::warning=`. Cargo
///   hides a successful build script's stderr outright and never replays it from
///   a cached run, so a warning written there would be lost precisely when
///   nothing else reports it - the build went green and no one is looking. One
///   directive per line reads chunkier than the raw form, but visible beats
///   well-formatted and unread.
///
/// `with_stdout` says whether stdout carries diagnostics too. It does for most
/// tools, but not for a command whose stdout *is* the artifact being captured.
pub fn report_command_output(cmd_output: &std::process::Output, with_stdout: bool) {
    let stdout: &[u8] = if with_stdout { &cmd_output.stdout } else { &[] };

    if cmd_output.status.success() {
        // An empty message emits nothing, so a quiet command stays quiet.
        cargo_out::warning(diagnostics_text(cmd_output, with_stdout));
        return;
    }

    let stderr = io::stderr();
    let mut lock = stderr.lock();
    let _ = lock.write_all(stdout);
    let _ = lock.write_all(&cmd_output.stderr);
    let _ = lock.flush();
}

/// Builds the short one-line error for a command that exited with a failure
/// status
fn command_failed_error(cmd: &std::process::Command, status: std::process::ExitStatus) -> String {
    format!(
        "{} failed with {}",
        cmd.get_program().to_string_lossy(),
        status
    )
}
