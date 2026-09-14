//! `cargo build`/`test`/`clippy`/... wrappers driven by [`BuildArgs`]/
//! [`UnitTestArgs`], plus the post-build steps a `build` also runs: binary
//! conversion, artifact publishing, and app proof/RootPacket generation.

use anyhow::{Context, Result, ensure};
use std::{ffi::OsStr, path::PathBuf, process};

use crate::{
    args::{BuildArgs, UnitTestArgs},
    binary, helpers, linker, postbuild, tools,
};

/// Resolves `args.project` (see [`helpers::resolve_project_name`]) and
/// (re)generates its linker package (see [`linker::generate`]) -- the
/// package that actually produces the linked ELF/`.so`, whether `args`
/// targets a member of an app workspace or a standalone app, neither of
/// which have a `[[bin]]` target of their own to build/link. Returns the
/// resolved project name alongside the generated package's own name and
/// manifest path, all three of which [`crate::args::BuildArgs::configure_cargo_linked`]
/// needs.
fn generate_linker_package(args: &BuildArgs) -> Result<(String, String, PathBuf)> {
    let project = helpers::resolve_project_name(&args.project)?;
    let app_manifest_dir = helpers::app_manifest_dir(&project)?;
    let (package, manifest_path) = linker::generate(&project, &app_manifest_dir)?;
    Ok((project, package, manifest_path))
}

/// Builds the app for the model/language/profile in `args`, then converts
/// the resulting ELF to the app binary format, publishes both as artifacts,
/// and (unless `args.production`) generates the dev-signed app proofs and
/// RootPacket needed to load it.
pub fn build(args: &BuildArgs) -> Result<()> {
    let (project, package, manifest_path) = generate_linker_package(args)?;

    run_cargo_subcommand(
        "build",
        |cmd| args.configure_cargo_linked(cmd, &project, &package, &manifest_path),
        None::<&[&str]>,
    )?;

    let elf_path = helpers::elf_path(args)?;
    let app_package = helpers::app_package(&project)?;
    let bin_path = binary::convert_elf_to_bin(&elf_path, &app_package)?;

    postbuild::publish_artifact(&elf_path, &project, args.model, args.emulator)?;
    postbuild::publish_artifact(&bin_path, &project, args.model, args.emulator)?;

    if args.production {
        // The proofs would have to be covered by a production-signed RootPacket.
        println!("xtask: Skipping app proofs (production build, dev keys not applicable)");
    } else {
        postbuild::generate_app_proofs(args.model, args.emulator)?;
    }

    Ok(())
}

/// Runs `cargo clippy` with the feature/profile/target configuration for
/// `args`, against the app package directly -- linting doesn't need the
/// final linked artifact.
pub fn clippy(args: &BuildArgs) -> Result<()> {
    run_cargo_subcommand(
        "clippy",
        |cmd| args.configure_cargo_check(cmd),
        None::<&[&str]>,
    )
}

/// Runs `cargo check` with the feature/profile/target configuration for
/// `args`, against the app package directly -- see [`clippy`].
pub fn check(args: &BuildArgs) -> Result<()> {
    run_cargo_subcommand(
        "check",
        |cmd| args.configure_cargo_check(cmd),
        None::<&[&str]>,
    )
}

/// Runs `cargo size -A` with the feature/profile/target configuration for
/// `args`, against the linked artifact (see [`generate_linker_package`]).
pub fn size(args: &BuildArgs) -> Result<()> {
    let (project, package, manifest_path) = generate_linker_package(args)?;
    run_cargo_subcommand(
        "size",
        |cmd| args.configure_cargo_linked(cmd, &project, &package, &manifest_path),
        Some(&["-A"]),
    )
}

/// Runs `cargo nm` with the feature/profile/target configuration for `args`
/// and prints a size-sorted, symbol-grouped breakdown of the resulting ELF.
pub fn nm(args: &BuildArgs) -> Result<()> {
    let (project, package, manifest_path) = generate_linker_package(args)?;
    let output = run_cargo_subcommand_output(
        "nm",
        |cmd| args.configure_cargo_linked(cmd, &project, &package, &manifest_path),
        Some(&["--size-sort", "--print-size", "--demangle"]),
    )?;
    let elf = helpers::elf_path(args)?;

    tools::group_nm(&output.stdout, Some(&elf), 50, 500, 2, "llvm-addr2line")?;
    Ok(())
}

/// Runs `cargo test` (host-target unit tests, not the app's own `no_std`
/// build) with the `test` feature enabled, restricted to `args.test` if given.
pub fn test(args: &UnitTestArgs) -> Result<()> {
    let features = [
        args.model.feature_name(),
        args.lang.feature_name(),
        "test",
        "log_level_debug",
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
        .arg(&args.test);

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

/// Runs `cargo clean` in the calling project's root.
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

/// Runs `cargo fmt` in the calling project's root, or `cargo fmt -- --check`
/// if `check_only` is set.
pub fn fmt(check_only: bool) -> Result<()> {
    let mut cmd = process::Command::new("cargo");
    cmd.arg("fmt");
    if check_only {
        cmd.arg("--").arg("--check");
    }
    cmd.current_dir(helpers::root_dir()?);

    println!("xtask: Running cargo fmt");
    println!("\x1b[1;90m{}\x1b[0m", helpers::command_args_to_string(&cmd));

    let status = cmd.status().context("Failed to spawn `cargo fmt`")?;
    ensure!(status.success(), "`cargo fmt` failed with status: {status}",);

    Ok(())
}

fn run_cargo_subcommand_output<S, I>(
    subcommand: &str,
    configure: impl FnOnce(&mut process::Command) -> Result<()>,
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
    configure(&mut cmd)?;
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
    configure: impl FnOnce(&mut process::Command) -> Result<()>,
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
    configure(&mut cmd)?;
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

    Ok(())
}
