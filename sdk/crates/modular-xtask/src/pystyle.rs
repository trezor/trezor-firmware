//! Python style tooling (`black`, `isort`, `autoflake`, `flake8`, `pyright`)
//! for an app's own `tests/` directory.

use crate::{args::ProjectArgs, helpers};
use anyhow::{Result, ensure};
use std::process::Command;

/// Runs `black`, `isort`, `flake8`, and `pyright` (plus `autoflake` when not
/// `check_only`) against the app's `tests/` directory. With `check_only`,
/// `black`/`isort` run in check mode instead of rewriting files in place.
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

    let mut cmd = Command::new("black");
    cmd.arg("--fast").arg(&project_dir);
    if check_only {
        cmd.arg("--check");
    }

    println!("xtask: Running black formatter");
    println!("\x1b[1;90m{}\x1b[0m", helpers::command_args_to_string(&cmd));

    let status = cmd.status().expect("Failed to run black");
    ensure!(status.success(), "`black` failed with status: {status}",);

    let mut cmd = Command::new("isort");
    cmd.arg(&test_dir);
    cmd.current_dir(&project_dir);
    if check_only {
        cmd.arg("--check-only");
    }

    println!("xtask: Running isort");
    println!("\x1b[1;90m{}\x1b[0m", helpers::command_args_to_string(&cmd));

    let status = cmd.status().expect("Failed to run isort");
    ensure!(status.success(), "`isort` failed with status: {status}",);

    if !check_only {
        let mut cmd = Command::new("autoflake");
        cmd.arg("-i")
            .arg("--remove-all-unused-imports")
            .arg("-r")
            .arg(&test_dir)
            .current_dir(&project_dir);
        println!("xtask: Running autoflake");
        println!("\x1b[1;90m{}\x1b[0m", helpers::command_args_to_string(&cmd));
        let status = cmd.status().expect("Failed to run autoflake");
        ensure!(status.success(), "`autoflake` failed with status: {status}",);
    }

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
