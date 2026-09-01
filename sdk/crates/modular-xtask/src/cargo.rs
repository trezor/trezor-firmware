//! `cargo build`/`test`/`clippy`/... wrappers driven by [`BuildArgs`]/
//! [`UnitTestArgs`], plus the post-build steps a `build` also runs: binary
//! conversion, artifact publishing, and app proof/RootPacket generation.

use anyhow::{Context, Result, ensure};
use std::{ffi::OsStr, path::PathBuf, process};

use crate::{
    args::{BuildArgs, UnitTestArgs},
    binary, helpers, linker, postbuild, tools,
};

/// Which package actually produces the linked ELF/`.so` for a given
/// [`BuildArgs`]: the generated linker package in a workspace (the app
/// package itself only ever builds as a library there -- see
/// [`crate::linker`]), or the app package directly for a standalone app
/// (which still builds straight to a `[[bin]]`, with its own root-level
/// `memory.x`).
enum LinkTarget {
    Linker { package: String, manifest_path: PathBuf },
    Direct,
}

/// Resolves [`LinkTarget`] for `args`, generating the linker package (see
/// [`linker::generate`]) when running in a workspace.
fn resolve_link_target(args: &BuildArgs) -> Result<LinkTarget> {
    if helpers::is_workspace()? {
        let (package, manifest_path) = linker::generate(&args.project)?;
        Ok(LinkTarget::Linker {
            package,
            manifest_path,
        })
    } else {
        Ok(LinkTarget::Direct)
    }
}

/// Builds the app for the model/language/profile in `args`, then converts
/// the resulting ELF to the app binary format, publishes both as artifacts,
/// and (unless `args.production`) generates the dev-signed app proofs and
/// RootPacket needed to load it.
pub fn build(args: &BuildArgs) -> Result<()> {
    // Build (and, in a workspace, link) the component.
    run_cargo_subcommand("build", args, resolve_link_target(args)?, None::<&[&str]>)?;

    let elf_path = helpers::elf_path(args)?;

    let app = if helpers::is_workspace()? {
        args.project.clone()
    } else {
        helpers::standalone_project_name()?
    };

    let app_package = helpers::app_package(&app)?;

    let bin_path = binary::convert_elf_to_bin(&elf_path, &app_package)?;

    postbuild::publish_artifact(&elf_path, &app, args.model, args.emulator)?;
    postbuild::publish_artifact(&bin_path, &app, args.model, args.emulator)?;

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
    run_cargo_subcommand("clippy", args, LinkTarget::Direct, None::<&[&str]>)
}

/// Runs `cargo check` with the feature/profile/target configuration for
/// `args`, against the app package directly -- see [`clippy`].
pub fn check(args: &BuildArgs) -> Result<()> {
    run_cargo_subcommand("check", args, LinkTarget::Direct, None::<&[&str]>)
}

/// Runs `cargo size -A` with the feature/profile/target configuration for
/// `args`, against the linked artifact (see [`resolve_link_target`]).
pub fn size(args: &BuildArgs) -> Result<()> {
    run_cargo_subcommand("size", args, resolve_link_target(args)?, Some(&["-A"]))
}

/// Runs `cargo nm` with the feature/profile/target configuration for `args`
/// and prints a size-sorted, symbol-grouped breakdown of the resulting ELF.
pub fn nm(args: &BuildArgs) -> Result<()> {
    let output = run_cargo_subcommand_output(
        "nm",
        args,
        resolve_link_target(args)?,
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
    args: &BuildArgs,
    target: LinkTarget,
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
    match target {
        LinkTarget::Linker {
            package,
            manifest_path,
        } => args.configure_cargo_linked(&mut cmd, &package, &manifest_path)?,
        LinkTarget::Direct => args.configure_cargo(&mut cmd)?,
    }
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
    target: LinkTarget,
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
    match target {
        LinkTarget::Linker {
            package,
            manifest_path,
        } => args.configure_cargo_linked(&mut cmd, &package, &manifest_path)?,
        LinkTarget::Direct => args.configure_cargo(&mut cmd)?,
    }
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
