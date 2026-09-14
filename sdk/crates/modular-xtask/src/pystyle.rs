//! Python style tooling (`ruff`, `flake8`, `pyright`) for an app's own
//! `tests/` directory.

use crate::{args::ProjectArgs, helpers};
use anyhow::{Result, ensure};
use std::process::Command;

/// Runs `ruff` (lint + format), `flake8`, and `pyright` against the app's
/// `tests/` directory. With `check_only`, `ruff` runs in check mode instead
/// of rewriting files in place.
pub fn run(args: &ProjectArgs, check_only: bool) -> Result<()> {
    let mut project_dir = helpers::root_dir()?;
    if helpers::is_workspace()? {
        ensure!(
            !args.project.is_empty(),
            "Project name must be specified when running py-style in a workspace"
        );
        project_dir = project_dir.join(&args.project);
    }
    let test_dir = project_dir.join("tests");

    let mut cmd = Command::new("ruff");
    cmd.arg("check");
    if !check_only {
        cmd.arg("--fix");
    }
    cmd.arg(&test_dir);

    println!("xtask: Running ruff check");
    println!("\x1b[1;90m{}\x1b[0m", helpers::command_args_to_string(&cmd));

    let status = cmd.status().expect("Failed to run ruff check");
    ensure!(
        status.success(),
        "`ruff check` failed with status: {status}",
    );

    let mut cmd = Command::new("ruff");
    cmd.arg("format");
    if check_only {
        cmd.arg("--check");
    }
    cmd.arg(&test_dir);

    println!("xtask: Running ruff format");
    println!("\x1b[1;90m{}\x1b[0m", helpers::command_args_to_string(&cmd));

    let status = cmd.status().expect("Failed to run ruff format");
    ensure!(
        status.success(),
        "`ruff format` failed with status: {status}",
    );

    let mut cmd = Command::new("flake8");
    cmd.arg(&test_dir);
    cmd.current_dir(&project_dir);
    println!("xtask: Running flake8");
    println!("\x1b[1;90m{}\x1b[0m", helpers::command_args_to_string(&cmd));
    let status = cmd.status().expect("Failed to run flake8");
    ensure!(status.success(), "`flake8` failed with status: {status}",);

    let mut cmd = Command::new("pyright");
    cmd.current_dir(&project_dir);
    println!("xtask: Running pyright");
    println!("\x1b[1;90m{}\x1b[0m", helpers::command_args_to_string(&cmd));
    let status = cmd.status().expect("Failed to run pyright");
    ensure!(status.success(), "`pyright` failed with status: {status}",);
    Ok(())
}
