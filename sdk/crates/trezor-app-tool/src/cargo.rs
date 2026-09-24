//! `cargo build`/`test`/`clippy`/... wrappers driven by [`BuildArgs`]/
//! [`UnitTestArgs`], plus the post-build steps a `build` also runs: binary
//! conversion, artifact publishing, and app proof/RootPacket generation.

use anyhow::{Context, Result, ensure};
use cargo_metadata::Package;
use std::{ffi::OsStr, path::PathBuf, process};

use crate::{
    apptree,
    args::{BuildArgs, TestArgs},
    artifacts, helpers, image,
};

/// Builds the selected app(s) for the model/language/profile in `args` in a
/// single `cargo build`, then converts each resulting ELF to the app binary
/// format, publishes both as artifacts, and (unless `args.production`)
/// generates the dev-signed app proofs and RootPacket needed to load them.
pub fn build(args: BuildArgs) -> Result<()> {
    build_packages(&args)?;
    Ok(())
}

/// Builds the selected app(s) and returns a vector of tuples containing
/// each package and the path to its resulting binary.
pub fn build_packages(args: &BuildArgs) -> Result<Vec<(Package, PathBuf)>> {
    let target_arch = helpers::resolve_target_arch(args.model, args.arch, args.emulator)?;
    let packages = helpers::selected_packages(&args.package)?;

    // Build the component(s)
    run_cargo_subcommand("build", &args, &packages, None::<&[&str]>)?;

    let mut pairs = Vec::new();

    for package in &packages {
        let elf_path = helpers::elf_path(&args, package)?;

        let bin_path = image::convert_elf_to_bin(&elf_path, package, args.model)?;
        let artifact_name = helpers::artifact_name(
            package,
            args.lang,
            args.model,
            Some(target_arch),
            args.emulator,
        )?;

        artifacts::publish_artifact(&elf_path, &format!("{}.elf", artifact_name))?;
        let binary = artifacts::publish_artifact(&bin_path, &format!("{}.bin", artifact_name))?;

        pairs.push((package.clone(), binary));
    }

    apptree::generate()?;

    Ok(pairs)
}

/// Runs `cargo clippy` with the feature/profile/target configuration for `args`.
pub fn clippy(args: BuildArgs) -> Result<()> {
    let packages = helpers::selected_packages(&args.package)?;
    run_cargo_subcommand("clippy", &args, &packages, None::<&[&str]>)
}

/// Runs `cargo check` with the feature/profile/target configuration for `args`.
pub fn check(args: BuildArgs) -> Result<()> {
    let packages = helpers::selected_packages(&args.package)?;
    run_cargo_subcommand("check", &args, &packages, None::<&[&str]>)
}

/// Runs `cargo size -A` with the feature/profile/target configuration for `args`.
pub fn size(args: BuildArgs) -> Result<()> {
    let packages = helpers::selected_packages(&args.package)?;
    run_cargo_subcommand("size", &args, &packages, Some(&["-A"]))
}

/// Runs `cargo test` (host-target unit tests, not the app's own `no_std`
/// build) with the `test` feature enabled, restricted to `args.test` if given.
pub fn test(args: TestArgs) -> Result<()> {
    let features = [
        args.model.feature_name(),
        args.lang.feature_name(),
        "test",
        "log_level_debug",
    ];

    let packages = helpers::selected_packages(&args.package)?;

    let mut cmd = process::Command::new("cargo");
    cmd.arg("test");
    for package in &packages {
        cmd.arg("-p").arg(&package.name);
    }
    cmd.args(["--features", &features.join(",")])
        .arg(&args.test);

    println!("app-tool: Running cargo test");
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

/// Runs `cargo clean` in the calling project's root.
pub fn clean() -> Result<()> {
    let mut cmd = process::Command::new("cargo");
    cmd.arg("clean");
    cmd.current_dir(helpers::root_dir()?);

    println!("app-tool: Running cargo clean");
    println!("\x1b[1;90m{}\x1b[0m", helpers::command_args_to_string(&cmd));

    let status = cmd.status().context("Failed to spawn `cargo clean`")?;
    ensure!(
        status.success(),
        "`cargo clean` failed with status: {status}",
    );

    Ok(())
}

fn run_cargo_subcommand<S, I>(
    subcommand: &str,
    args: &BuildArgs,
    packages: &[Package],
    extra_args: Option<I>,
) -> Result<()>
where
    I: IntoIterator<Item = S>,
    S: AsRef<OsStr>,
{
    let mut cmd = process::Command::new("cargo");
    cmd.arg(subcommand);

    args.configure_cargo(&mut cmd, packages)?;
    if let Some(extra_args) = extra_args {
        cmd.arg("--").args(extra_args);
    }

    println!("app-tool: Running cargo {}", subcommand);
    println!("\x1b[1;90m{}\x1b[0m", helpers::command_args_to_string(&cmd));

    let status = cmd
        .current_dir(helpers::root_dir()?)
        .status()
        .context(format!("Failed to spawn `cargo {}`", subcommand))?;

    ensure!(
        status.success(),
        "`cargo {subcommand}` failed with status: {status}"
    );

    Ok(())
}
