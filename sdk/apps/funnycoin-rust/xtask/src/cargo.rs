use anyhow::{Context, Ok, Result, ensure};
use std::ffi::OsStr;
use std::process;

use crate::{
    args::{BuildArgs, UnitTestArgs},
    arm, helpers, postbuild, tools,
};

pub fn build(args: BuildArgs) -> Result<()> {
    // Build the component
    run_cargo_subcommand("build", &args, None::<&[&str]>)?;
    let orig = helpers::elf_path(&args)?;

    if !args.emulator && !args.debug {
        nm(args.clone())?;
        let tmp = arm::objcopy(
            &orig,
            "min",
            [
                "--remove-section=.rel.text",
                "--remove-section=.debug*",
                "--remove-section=.rel.debug*",
                "--strip-debug",
                "--discard-locals",
            ],
        )?;

        postbuild::zero_symnames(&tmp, ["applet_main"], true)?;

        let min = arm::objcopy(&tmp, "", ["--strip-unneeded"])?;
        arm::size(&min, ["-A"])?;
        arm::size(&min, ["-B"])?;

        arm::print_elf_sections(&min)?;

        postbuild::publish_artifact(&min, &args.app, args.model, args.emulator)?;
    } else {
        run_cargo_subcommand("size", &args, Some(&["-A"]))?;
        run_cargo_subcommand("size", &args, Some(&["-B"]))?;
        postbuild::publish_artifact(&orig, &args.app, args.model, args.emulator)?;
    };

    Ok(())
}

pub fn clippy(args: BuildArgs) -> Result<()> {
    run_cargo_subcommand("clippy", &args, None::<&[&str]>)
}

pub fn check(args: BuildArgs) -> Result<()> {
    run_cargo_subcommand("check", &args, None::<&[&str]>)
}

pub fn size(args: BuildArgs) -> Result<()> {
    run_cargo_subcommand("size", &args, Some(&["-A"]))
}

pub fn nm(args: BuildArgs) -> Result<()> {
    let output = run_cargo_subcommand_output(
        "nm",
        &args,
        Some(&["--size-sort", "--print-size", "--demangle"]),
    )?;
    let elf = helpers::elf_path(&args)?;

    tools::group_nm(&output.stdout, Some(&elf), 50, 500, 2, "llvm-addr2line")?;
    Ok(())
}

pub fn test(args: UnitTestArgs) -> Result<()> {
    let features = vec![
        args.model.feature_name(),
        args.lang.feature_name(),
        "test",
        "log_level_trace",
    ];

    let status = process::Command::new("cargo")
        .arg("test")
        .args(["--features", &features.join(",")])
        .arg("--verbose")
        .current_dir(helpers::workspace_dir()?)
        .status()
        .context("Failed to spawn `cargo test`")?;
    ensure!(
        status.success(),
        "`cargo test` failed with status: {status}",
    );
    Ok(())
}

pub fn clean() -> Result<()> {
    let status = process::Command::new("cargo")
        .arg("clean")
        .current_dir(helpers::workspace_dir()?)
        .status()
        .context("Failed to spawn `cargo clean`")?;

    ensure!(
        status.success(),
        "`cargo clean` failed with status: {status}",
    );

    Ok(())
}

pub fn fmt() -> Result<()> {
    let status = process::Command::new("cargo")
        .arg("fmt")
        .current_dir(helpers::workspace_dir()?)
        .status()
        .context("Failed to spawn `cargo fmt`")?;

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
        .status()
        .context(format!("Failed to spawn `cargo {}`", subcommand))?;

    ensure!(
        status.success(),
        "`cargo {subcommand}` failed with status: {status}"
    );

    return Ok(());
}
