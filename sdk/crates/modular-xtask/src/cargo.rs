use anyhow::{Context, Result, ensure};
use std::{ffi::OsStr, process};

use crate::{
    args::{BuildArgs, UnitTestArgs},
    binary, helpers, postbuild, tools,
};

pub fn build(args: &BuildArgs) -> Result<()> {
    // Build the component
    run_cargo_subcommand("build", args, None::<&[&str]>)?;

    let elf_path = helpers::elf_path(args)?;

    let app = if helpers::is_workspace()? {
        args.project.clone()
    } else {
        helpers::standalone_project_name()?
    };

    let app_package = helpers::app_package(&app)?;

    let bin_path = binary::convert_elf_to_bin(&elf_path, &app_package)?;

    println!("app is: {}", app);

    postbuild::publish_artifact(&elf_path, &app, args.model, args.emulator)?;
    postbuild::publish_artifact(&bin_path, &app, args.model, args.emulator)?;

    Ok(())
}

pub fn clippy(args: &BuildArgs) -> Result<()> {
    run_cargo_subcommand("clippy", args, None::<&[&str]>)
}

pub fn check(args: &BuildArgs) -> Result<()> {
    run_cargo_subcommand("check", args, None::<&[&str]>)
}

pub fn size(args: &BuildArgs) -> Result<()> {
    run_cargo_subcommand("size", args, Some(&["-A"]))
}

pub fn nm(args: &BuildArgs) -> Result<()> {
    let output = run_cargo_subcommand_output(
        "nm",
        args,
        Some(&["--size-sort", "--print-size", "--demangle"]),
    )?;
    let elf = helpers::elf_path(args)?;

    tools::group_nm(&output.stdout, Some(&elf), 50, 500, 2, "llvm-addr2line")?;
    Ok(())
}

pub fn test(args: &UnitTestArgs) -> Result<()> {
    let features = vec![
        args.model.feature_name(),
        args.lang.feature_name(),
        "test",
        "log_level_trace",
    ];

    let mut cmd = process::Command::new("cargo");
    cmd.arg("test");
    if helpers::is_workspace()? {
        ensure!(
            !args.project.is_empty(),
            "Project name must be specified when running tests in a workspace"
        );
        cmd.arg("-p").arg(&args.project);
    }
    cmd.args(["--features", &features.join(",")])
        .arg(args.test.to_string());

    println!("xtask: Running cargo test");
    println!("\x1b[1;90m{}\x1b[0m", helpers::command_args_to_string(&cmd));

    let status = cmd
        .current_dir(helpers::root_dir()?)
        .status()
        .context("Failed to spawn `cargo test`")?;
    ensure!(
        status.success(),
        "`cargo test` failed with status: {status}",
    );
    Ok(())
}

pub fn clean() -> Result<()> {
    let mut cmd = process::Command::new("cargo");
    cmd.arg("clean");
    cmd.current_dir(helpers::root_dir()?);

    println!("xtask: Running cargo clean");
    println!("\x1b[1;90m{}\x1b[0m", helpers::command_args_to_string(&cmd));

    let status = cmd.status().context("Failed to spawn `cargo clean`")?;
    ensure!(
        status.success(),
        "`cargo clean` failed with status: {status}",
    );

    Ok(())
}

pub fn fmt() -> Result<()> {
    let mut cmd = process::Command::new("cargo");
    cmd.arg("fmt");
    cmd.current_dir(helpers::root_dir()?);

    println!("xtask: Running cargo fmt");
    println!("\x1b[1;90m{}\x1b[0m", helpers::command_args_to_string(&cmd));

    let status = cmd.status().context("Failed to spawn `cargo fmt`")?;
    ensure!(status.success(), "`cargo fmt` failed with status: {status}",);

    Ok(())
}

fn run_cargo_subcommand_output<S, I>(
    subcommand: &str,
    args: &BuildArgs,
    extra_args: Option<I>,
) -> Result<process::Output>
where
    I: IntoIterator<Item = S>,
    S: AsRef<OsStr>,
{
    let mut cmd = process::Command::new("cargo");
    cmd.arg(subcommand);
    cmd.stderr(process::Stdio::inherit()); // warnings go to terminal
    cmd.stdout(process::Stdio::piped()); // nm output captured
    args.configure_cargo(&mut cmd)?;
    if let Some(extra_args) = extra_args {
        cmd.arg("--").args(extra_args);
    }

    println!("xtask: Running cargo {}", subcommand);
    println!("\x1b[1;90m{}\x1b[0m", helpers::command_args_to_string(&cmd));
    let output = cmd
        .output()
        .context(format!("Failed to execute cargo {subcommand}"))?;
    ensure!(
        output.status.success(),
        "cargo {subcommand} failed with status: {}",
        output.status
    );
    Ok(output)
}

fn run_cargo_subcommand<S, I>(
    subcommand: &str,
    args: &BuildArgs,
    extra_args: Option<I>,
) -> Result<()>
where
    I: IntoIterator<Item = S>,
    S: AsRef<OsStr>,
{
    let mut cmd = process::Command::new("cargo");
    cmd.arg(subcommand);
    // cmd.stderr(process::Stdio::inherit()); // warnings go to terminal
    // cmd.stdout(process::Stdio::piped());    // nm output captured
    args.configure_cargo(&mut cmd)?;
    if let Some(extra_args) = extra_args {
        cmd.arg("--").args(extra_args);
    }

    println!("xtask: Running cargo {}", subcommand);
    println!("\x1b[1;90m{}\x1b[0m", helpers::command_args_to_string(&cmd));

    let status = cmd
        .current_dir(helpers::root_dir()?)
        .status()
        .context(format!("Failed to spawn `cargo {}`", subcommand))?;

    ensure!(
        status.success(),
        "`cargo {subcommand}` failed with status: {status}"
    );

    return Ok(());
}
