use anyhow::{Context, Result, ensure};
use std::process;

use crate::args::{BuildArgs, Component, Model, TestArgs};
use crate::artifacts::collect_artifacts;
use crate::helpers::{elf_path, workspace_dir};
use crate::postbuild::{elf_to_bin, merge_compile_commands, sign_binary};

pub fn build(args: BuildArgs) -> Result<()> {
    build_impl(args, false)?;

    if args.storage_insecure_testing_mode {
        println!("\x1b[1;33m");
        // println!("#########################################################");
        println!("STORAGE_INSECURE_TESTING_MODE enabled, DO NOT USE");
        // println!("#########################################################");
        println!("\x1b[0m");
    }

    Ok(())
}

pub fn clippy(args: BuildArgs) -> Result<()> {
    run_cargo_subcommand("clippy", &args)
}

pub fn check(args: BuildArgs) -> Result<()> {
    run_cargo_subcommand("check", &args)
}

pub fn test(_args: TestArgs) -> Result<()> {
    unimplemented!();
}

pub fn clean() -> Result<()> {
    let status = process::Command::new("cargo")
        .arg("clean")
        .current_dir(workspace_dir()?)
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
        .current_dir(workspace_dir()?)
        .status()
        .context("Failed to spawn `cargo fmt`")?;

    ensure!(status.success(), "`cargo fmt` failed with status: {status}",);

    Ok(())
}

fn build_impl(args: BuildArgs, is_dependency: bool) -> Result<()> {
    if !args.emulator {
        // Recursively build dependencies (Firmware -> Kernel -> Secmon)
        if args.component == Component::Firmware {
            build_impl(
                BuildArgs {
                    component: Component::Kernel,
                    ..args
                },
                true,
            )?;
        } else if args.component == Component::Kernel && args.model == Model::T3W1 {
            // For the kernel, we need to build the secmon binary first in order to embed it into the kernel binary.
            build_impl(
                BuildArgs {
                    component: Component::Secmon,
                    ..args
                },
                true,
            )?;
        }
    }

    run_cargo_subcommand("build", &args)?;

    let elf = elf_path(&args)?;

    if !args.emulator {
        // For hardware targets, we need to convert the ELF file into a raw
        // binary before signing it.
        let bin = elf_to_bin(&elf, args.component, args.model)?;

        // Sign the binary except for those that don't have headers
        if !matches!(args.component, Component::Boardloader | Component::Kernel) {
            sign_binary(&bin, args.component, args.model, args.production)?;
        }

        if args.component == Component::Firmware {
            let firwmare_cc_json = bin.with_extension("cc.json");
            let kernel_cc_json = bin.with_file_name("kernel").with_extension("cc.json");
            let secmon_cc_json = bin.with_file_name("secmon").with_extension("cc.json");

            merge_compile_commands(
                &[&secmon_cc_json, &kernel_cc_json, &firwmare_cc_json],
                &firwmare_cc_json,
            )?;
        }
    }

    collect_artifacts(&args, is_dependency)?;

    Ok(())
}

fn run_cargo_subcommand(subcommand: &str, args: &BuildArgs) -> Result<()> {
    let mut cmd = process::Command::new("cargo");

    cmd.arg(subcommand).current_dir(workspace_dir()?);

    args.configure_cargo(&mut cmd)
        .context(format!("Failed to construct {} command", subcommand))?;

    if subcommand == "clippy" {
        // we don't need it anymore, since clippy is now run with the
        // same features as the regular build
        // cmd.args(["--features", "clippy"]);
    }

    let component_name = format!("{:?}", args.component).to_lowercase();
    println!("xtask: Running {} on `{}`", subcommand, component_name);
    println!("\x1b[1;90m{}\x1b[0m", command_args_to_string(&cmd));

    let status = cmd
        .status()
        .context(format!("Failed to spawn `cargo {}`", subcommand))?;

    ensure!(
        status.success(),
        "`cargo {subcommand}` failed with status: {status}"
    );

    Ok(())
}

fn command_args_to_string(cmd: &process::Command) -> String {
    let mut parts = vec![cmd.get_program().to_string_lossy().into_owned()];
    parts.extend(cmd.get_args().map(|arg| arg.to_string_lossy().into_owned()));
    parts.join(" ")
}
