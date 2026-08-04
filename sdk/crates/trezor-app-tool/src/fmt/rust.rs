use crate::helpers;
use anyhow::{Context, Result, ensure};
use cargo_metadata::Package;
use std::process;

/// Formats the Rust code of `packages` using `cargo fmt`. If `check_only`
/// is `true`, it will only check for formatting issues without modifying files.
pub fn format(check_only: bool, packages: &[Package]) -> Result<()> {
    let mut cmd = process::Command::new("cargo");
    cmd.arg("fmt");
    for package in packages {
        cmd.arg("-p").arg(&package.name);
    }
    if check_only {
        cmd.arg("--").arg("--check");
    }
    cmd.current_dir(helpers::root_dir()?);

    println!("app-tool: Running cargo fmt");
    println!("\x1b[1;90m{}\x1b[0m", helpers::command_args_to_string(&cmd));

    let status = cmd.status().context("Failed to spawn `cargo fmt`")?;
    ensure!(status.success(), "`cargo fmt` failed with status: {status}",);

    Ok(())
}
