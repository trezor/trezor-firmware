use anyhow::{Context, Result, ensure};
use owo_colors::OwoColorize;
use std::process;

use crate::{
    args::{BuildArgs, Component, TestArgs},
    artifacts, helpers, memusage, postbuild, prebuild,
};

pub fn build(args: BuildArgs) -> Result<()> {
    build_impl(args, false)?;

    if args.storage_insecure_testing_mode {
        println!(
            "{}",
            "STORAGE_INSECURE_TESTING_MODE enabled, DO NOT USE"
                .yellow()
                .bold()
        );
    }

    Ok(())
}

pub fn clippy(args: BuildArgs) -> Result<()> {
    run_cargo_subcommand("clippy", &args)
}

pub fn check(args: BuildArgs) -> Result<()> {
    run_cargo_subcommand("check", &args)
}

pub fn test(args: TestArgs) -> Result<()> {
    for package in &args.packages {
        let mut cmd = process::Command::new("cargo");

        let test_feature = match package.as_str() {
            "trezor_lib" | "crypto" => "test_with_new_crates",
            _ => "test",
        };

        cmd.arg("test")
            .args(["--package", package])
            .args(["--features", test_feature])
            .arg("--")
            .arg("--test-threads=1")
            .arg("--nocapture")
            .current_dir(helpers::workspace_dir()?);

        println!("xtask: Running test on `{}`", &package);
        println!("{}", command_args_to_string(&cmd).bold().dimmed());

        let status = cmd.status().context("Failed to spawn `cargo test`")?;

        ensure!(
            status.success(),
            "`cargo test` failed with status: {status}"
        );
    }

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

fn build_impl(args: BuildArgs, is_dependency: bool) -> Result<()> {
    if !args.emulator {
        // Recursively build dependencies (Firmware -> Kernel -> Secmon)
        if let Some(dependency) = args.component.dependency(args.model) {
            build_impl(
                BuildArgs {
                    component: dependency,
                    ..args
                },
                true,
            )?;
        }
    }

    // Prebuild steps
    if matches!(args.component, Component::Firmware) {
        prebuild::update_templates()?;
        prebuild::update_translations()?;
    }

    // Build the component
    run_cargo_subcommand("build", &args)?;

    let elf = helpers::elf_path(&args)?;

    if !args.emulator {
        let use_dev_keys = args.bootloader_devel || !args.production;

        // For hardware targets, we need to convert the ELF file into a raw
        // binary before signing it.
        let bin = postbuild::elf_to_bin(&elf, args.component, args.model, use_dev_keys)?;

        // Sign the binary except for those that don't have headers
        if !matches!(args.component, Component::Boardloader | Component::Kernel) {
            postbuild::sign_binary(&bin, args.component, args.model, use_dev_keys)?;
        }

        if args.component == Component::Firmware {
            let firwmare_cc_json = bin.with_extension("cc.json");
            let kernel_cc_json = bin.with_file_name("kernel").with_extension("cc.json");
            let secmon_cc_json = bin.with_file_name("secmon").with_extension("cc.json");

            postbuild::merge_compile_commands(
                &[&secmon_cc_json, &kernel_cc_json, &firwmare_cc_json],
                &firwmare_cc_json,
            )?;
        }

        // Copy the final binary to the `pub` directory
        if !matches!(args.component, Component::Secmon | Component::Kernel) {
            let version_file = helpers::get_version_file(args.component)?;
            postbuild::publish_artifact(&bin, args.component, args.model, &version_file, None)?;
        }
    }

    // Copy build artifacts (ELF, map files) to the `artifacts` directory
    artifacts::collect_artifacts(&args, is_dependency)?;

    // Print memory usage
    if !args.emulator && !is_dependency {
        let mapfile = elf
            .with_file_name(args.component.binary_name())
            .with_extension("map");
        memusage::print_memusage(&mapfile)?;
    }

    Ok(())
}

fn run_cargo_subcommand(subcommand: &str, args: &BuildArgs) -> Result<()> {
    let mut cmd = process::Command::new("cargo");

    cmd.arg(subcommand).current_dir(helpers::workspace_dir()?);

    args.configure_cargo(&mut cmd)
        .context(format!("Failed to construct {} command", subcommand))?;

    let component_name = format!("{:?}", args.component).to_lowercase();
    println!("xtask: Running {} on `{}`", subcommand, component_name);
    println!("{}", command_args_to_string(&cmd).bold().dimmed());

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
