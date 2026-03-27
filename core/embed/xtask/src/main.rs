use anyhow::{Context, Result, bail};
use clap::Parser;

mod args;
mod helpers;
mod postprocess;

use args::{BuildArgs, Cli, Cmd, Component, Model};
use helpers::{elf_path, workspace_dir};
use postprocess::{elf_to_bin, sign_binary};

fn main() -> Result<()> {
    let cli = Cli::parse();

    match cli.command {
        Cmd::Build(args) => build(args)?,
        Cmd::Clippy(args) => clippy(args)?,
        Cmd::Check(args) => check(args)?,
        Cmd::Clean => clean()?,
        Cmd::Fmt => fmt()?,
    }

    Ok(())
}

fn build(args: BuildArgs) -> Result<()> {
    if !args.emulator {
        // Recursively build dependencies (Firmware -> Kernel -> Secmon)
        if args.component == Component::Firmware {
            build(BuildArgs {
                component: Component::Kernel,
                ..args
            })?;
        } else if args.component == Component::Kernel && args.model == Model::T3W1 {
            // For the kernel, we need to build the secmon binary first in order to embed it into the kernel binary.
            build(BuildArgs {
                component: Component::Secmon,
                ..args
            })?;
        }
    }

    run_cargo_subcommand("build", &args)?;

    let elf = elf_path(&args)?;

    if !args.emulator {
        // For hardware targets, we need to convert the ELF file into a raw
        // binary before signing it.
        let bin = elf_to_bin(&elf, args.component, args.model)?;

        // Sign the binary except for the boardloader and kernel, which
        // don't have headers
        match args.component {
            Component::Boardloader | Component::Kernel => (),
            _ => sign_binary(&bin, args.component, args.model, args.production)?,
        }
    }

    Ok(())
}

fn clippy(args: BuildArgs) -> Result<()> {
    run_cargo_subcommand("clippy", &args)
}

fn check(args: BuildArgs) -> Result<()> {
    run_cargo_subcommand("check", &args)
}

fn clean() -> Result<()> {
    let mut cmd = std::process::Command::new("cargo");
    cmd.arg("clean");
    cmd.current_dir(workspace_dir()?);

    let status = cmd.status().context("Failed to spawn `cargo clean`")?;
    if !status.success() {
        bail!("`cargo clean` failed");
    }

    Ok(())
}

fn fmt() -> Result<()> {
    let mut cmd = std::process::Command::new("cargo");
    cmd.arg("fmt");
    cmd.current_dir(workspace_dir()?);

    let status = cmd.status().context("Failed to spawn `cargo fmt`")?;
    if !status.success() {
        bail!("`cargo fmt` failed");
    }

    Ok(())
}

fn run_cargo_subcommand(subcommand: &str, args: &BuildArgs) -> Result<()> {
    let mut cmd = std::process::Command::new("cargo");
    cmd.arg(subcommand);
    cmd.current_dir(workspace_dir()?);

    args.configure_cargo(&mut cmd)
        .context(format!("Failed to construct {} command", subcommand))?;

    let component_name = format!("{:?}", args.component).to_lowercase();
    println!("xtask: Running {} on `{}`", subcommand, component_name);
    println!("\x1b[1;90m{}\x1b[0m", command_args_to_string(&cmd));

    let status = cmd
        .status()
        .context(format!("Failed to spawn `cargo {}`", subcommand))?;
    if !status.success() {
        let package = args.component.package_name(args.emulator);
        bail!("{} failed for `{}` package", subcommand, package);
    }

    Ok(())
}

fn command_args_to_string(cmd: &std::process::Command) -> String {
    let mut parts = vec![cmd.get_program().to_string_lossy().into_owned()];
    parts.extend(cmd.get_args().map(|arg| arg.to_string_lossy().into_owned()));
    parts.join(" ")
}
