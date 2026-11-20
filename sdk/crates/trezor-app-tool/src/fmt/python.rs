//! Python style tooling (`ruff`, `flake8`, `pyright`) for an app's own
//! `tests/` directory.

use crate::helpers;
use anyhow::{Context, Result, ensure};
use std::{path::Path, process::Command};

/// Runs `ruff` (lint + format) and `flake8` on the `tests/` directory of
/// the app at `package_dir`, then `pyright` from `package_dir` so it picks
/// up the app's `pyrightconfig.json`. With `check_only`, `ruff` runs in
/// check mode instead of rewriting files in place.
pub fn format(package_dir: &Path, check_only: bool) -> Result<()> {
    let dir = package_dir.join("tests");

    let mut cmd = Command::new("ruff");
    cmd.arg("check");
    if !check_only {
        cmd.arg("--fix");
    }
    cmd.arg(&dir);

    println!("app-tool: Running ruff check");
    println!("\x1b[1;90m{}\x1b[0m", helpers::command_args_to_string(&cmd));

    let status = cmd.status().context("Failed to spawn `ruff check`")?;
    ensure!(
        status.success(),
        "`ruff check` failed with status: {status}",
    );

    let mut cmd = Command::new("ruff");
    cmd.arg("format");
    if check_only {
        cmd.arg("--check");
    }
    cmd.arg(&dir);

    println!("app-tool: Running ruff format");
    println!("\x1b[1;90m{}\x1b[0m", helpers::command_args_to_string(&cmd));

    let status = cmd.status().context("Failed to spawn `ruff format`")?;
    ensure!(
        status.success(),
        "`ruff format` failed with status: {status}",
    );

    let mut cmd = Command::new("flake8");
    cmd.arg(&dir);
    println!("app-tool: Running flake8");
    println!("\x1b[1;90m{}\x1b[0m", helpers::command_args_to_string(&cmd));
    let status = cmd.status().context("Failed to spawn `flake8`")?;
    ensure!(status.success(), "`flake8` failed with status: {status}",);

    let mut cmd = Command::new("pyright");
    cmd.current_dir(package_dir);
    println!("app-tool: Running pyright");
    println!("\x1b[1;90m{}\x1b[0m", helpers::command_args_to_string(&cmd));
    let status = cmd.status().context("Failed to spawn `pyright`")?;
    ensure!(status.success(), "`pyright` failed with status: {status}",);
    Ok(())
}
