use std::{
    fs,
    path::{Path, PathBuf},
    time::SystemTime,
};

use color_eyre::{
    Result,
    eyre::{WrapErr, ensure},
};

use crate::helpers::{delete_file_if_exists, emit_rerun_if_changed, ensure_parent_directory};

/// Runs a command with dependency tracking and optional C compiler dependency file support.
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
/// * `Result<()>` - Ok if the command was run or skipped successfully, Err otherwise.
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

/// Runs a command with dependency tracking and optional C compiler dependency file support.
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
/// * `Result<()>` - Ok if the command was run or skipped successfully, Err otherwise.
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

    run_if_changed(inputs, outputs, Some(args.as_str()), cc_dep, || {
        // Run the command
        let cmd_output = cmd
            .output()
            .with_context(|| format!("Failed to execute {:?}", cmd))?;

        // Check if the command executed successfully
        ensure!(
            cmd_output.status.success(),
            format_command_error(cmd, &cmd_output)
        );

        eprintln!("@@ command executed: {:?}", cmd);

        Ok(())
    })
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
/// * `Result<()>` - Ok if the command was run or skipped successfully, Err otherwise.
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

    run_if_changed(inputs, [&output], Some(&args), None, || {
        // Remove existing output file to ensure we don't accidentally read
        // stale data if the command fails
        delete_file_if_exists(&output)?;

        // Run the command
        let cmd_output = cmd
            .output()
            .with_context(|| format!("Failed to execute {:?}", cmd))?;

        // Check if the command executed successfully
        ensure!(
            cmd_output.status.success(),
            format_command_error(cmd, &cmd_output)
        );

        // Ensure the output directory exists before writing the output
        ensure_parent_directory(output.as_ref())?;

        // Write the command's stdout to the output file
        fs::write(&output, &cmd_output.stdout)
            .with_context(|| format!("Failed to write to {}", output.as_ref().display()))?;

        eprintln!("@@ command executed: {:?}", cmd);

        Ok(())
    })
}

/// Checks if any of the input files are newer than any of the output files.
///
/// Returns true if any input file is newer than the oldest output file, or if any output is missing.
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

/// Constructs a dependency file path for the given output file.
fn dep_file_path(output: impl AsRef<Path>) -> PathBuf {
    let mut dep_path = output.as_ref().as_os_str().to_os_string();
    dep_path.push(".dep");
    PathBuf::from(dep_path)
}

fn dep_file_contents(
    inputs: &[impl AsRef<Path>],
    outputs: &[impl AsRef<Path>],
    args: Option<&str>,
) -> String {
    let mut dep = String::new();
    dep.push_str("--args--\n");

    if let Some(args) = args {
        dep.push_str(args);
        if !dep.ends_with('\n') {
            dep.push('\n');
        }
    }

    dep.push_str("--inputs--\n");
    for input in inputs {
        dep.push_str(&input.as_ref().to_string_lossy());
        dep.push('\n');
    }

    dep.push_str("--outputs--\n");
    for output in outputs {
        dep.push_str(&output.as_ref().to_string_lossy());
        dep.push('\n');
    }

    dep
}

/// Converts a Command name and its arguments to a string representation for
/// dependency tracking
fn command_to_dep_string(cmd: &std::process::Command) -> String {
    let mut text = String::new();
    text.push_str(&cmd.get_program().to_string_lossy());
    text.push('\n');
    for arg in cmd.get_args() {
        text.push_str(&arg.to_string_lossy());
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
/// Executes the function if any input is newer than any output, any output is missing,
/// or the command arguments have changed (tracked via a `.dep` file). The `.dep` file,
/// named after the first output with a `.dep` extension (e.g., `build/main.o.dep`), records
/// arguments and dependencies and is updated on each run.
///
/// If `cc_dep` is given, it should be a dependency file (e.g., `.d` from a C compiler);
/// if missing or if any of its dependencies are newer than the outputs, the function is re-run.
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

// Formats the error message from a failed command execution, prioritizing
// stderr, then stdout, and finally a generic message if both are empty.
pub fn format_command_error(
    cmd: &std::process::Command,
    cmd_output: &std::process::Output,
) -> String {
    let stderr = String::from_utf8_lossy(&cmd_output.stderr)
        .trim()
        .to_string();
    let stdout = String::from_utf8_lossy(&cmd_output.stdout)
        .trim()
        .to_string();

    if !stderr.is_empty() {
        stderr
    } else if !stdout.is_empty() {
        stdout
    } else {
        format!("Failed to execute {}", cmd.get_program().to_string_lossy())
    }
}
