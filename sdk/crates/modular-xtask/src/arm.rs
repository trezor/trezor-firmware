use crate::{helpers, tools};
use anyhow::{Context, Ok, Result, ensure};
use std::ffi::OsStr;
use std::path::PathBuf;
use std::{path::Path, process};

pub use crate::tools::zero_symnames;

pub fn objcopy<S, I>(input: &Path, output_extension: &str, extra_args: I) -> Result<PathBuf>
where
    I: IntoIterator<Item = S>,
    S: AsRef<OsStr>,
{
    let ext = input.extension().and_then(OsStr::to_str).unwrap_or("");
    let output = input.with_extension(format!("{ext}{output_extension}"));

    let args: Vec<_> = [
        input.as_os_str().to_os_string(),
        output.as_os_str().to_os_string(),
    ]
    .into_iter()
    .chain(extra_args.into_iter().map(|s| s.as_ref().to_os_string()))
    .collect();

    _ = run_arm_subcommand("objcopy", args)?;

    Ok(output)
}

pub fn read_elf<S, I>(input: &Path, extra_args: I) -> Result<()>
where
    I: IntoIterator<Item = S>,
    S: AsRef<OsStr>,
{
    let args: Vec<_> = std::iter::once(input.as_os_str().to_os_string())
        .chain(extra_args.into_iter().map(|s| s.as_ref().to_os_string()))
        .collect();
    run_arm_subcommand("readelf", args)?;
    Ok(())
}

pub fn size<S, I>(input: &Path, extra_args: I) -> Result<()>
where
    I: IntoIterator<Item = S>,
    S: AsRef<OsStr>,
{
    let args: Vec<_> = std::iter::once(input.as_os_str().to_os_string())
        .chain(extra_args.into_iter().map(|s| s.as_ref().to_os_string()))
        .collect();
    run_arm_subcommand("size", args)?;
    Ok(())
}

fn run_arm_subcommand<S, I>(subcommand: &str, args: I) -> Result<()>
where
    I: IntoIterator<Item = S>,
    S: AsRef<OsStr>,
{
    let mut cmd = process::Command::new(format!("arm-none-eabi-{}", subcommand));
    cmd.args(args);

    println!("xtask: Running arm {}", subcommand);
    println!("\x1b[1;90m{}\x1b[0m", helpers::command_args_to_string(&cmd));

    let status = cmd
        .status()
        .context(format!("Failed to execute {}", subcommand))?;
    ensure!(
        status.success(),
        "{} failed with status: {}",
        subcommand,
        status
    );
    Ok(())
}

fn run_arm_subcommand_output<S, I>(subcommand: &str, args: I) -> Result<std::process::Output>
where
    I: IntoIterator<Item = S>,
    S: AsRef<OsStr>,
{
    let mut cmd = process::Command::new(format!("arm-none-eabi-{}", subcommand));
    cmd.args(args);

    println!("xtask: Running arm {}", subcommand);
    println!("\x1b[1;90m{}\x1b[0m", helpers::command_args_to_string(&cmd));

    let output = cmd
        .output()
        .context(format!("Failed to execute {}", subcommand))?;
    ensure!(
        output.status.success(),
        "{} failed with status: {}",
        subcommand,
        output.status
    );
    Ok(output)
}

pub fn print_elf_sections(input: &Path) -> Result<()> {
    let output = run_arm_subcommand_output("readelf", [input.as_os_str(), "-S".as_ref()])?;
    tools::print_elf_sections(&output)?;
    Ok(())
}
