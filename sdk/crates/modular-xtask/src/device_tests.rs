//! Runs an app's Python device-test suite (pytest) against an already-built
//! artifact and an already-running Trezor emulator or physical device.

use crate::{args::DeviceTestsArgs, helpers};
use anyhow::{Context, Result, ensure};
use std::process;

/// Runs `pytest` against the app image already published for
/// `args.model`/`args.emulator` (see [`crate::postbuild::publish_artifact`]),
/// restricted to `args.test` if given, with the running Core set to
/// `args.lang`. Requires a Trezor emulator or physical device to already be
/// running and reachable; this does not start one itself. Pass `args.ui` to
/// additionally enable UI screenshot testing (`--ui=test --ui-check-missing
/// --do-master-diff`).
pub fn device_tests(args: &DeviceTestsArgs) -> Result<()> {
    let mut project_dir = helpers::root_dir()?;
    if helpers::is_workspace()? {
        ensure!(
            !args.project.is_empty(),
            "Project name must be specified when running device tests in a workspace"
        );
        project_dir = project_dir.join(&args.project);
    }
    let app = if helpers::is_workspace()? {
        args.project.clone()
    } else {
        helpers::standalone_project_name()?
    };

    let binary = helpers::artifacts_dir(args.model, args.emulator)?.join(format!("{}.elf", &app));

    let binary = binary
        .canonicalize()
        .with_context(|| format!("Failed to locate `{}` for upload", binary.display()))?;

    let mut cmd = process::Command::new("uv");
    cmd.args([
        "run",
        "pytest",
        &format!("--app={}", binary.display()),
        "--verbose",
        &format!("--lang={}", args.lang),
        args.test.as_str(),
    ]);

    if args.ui {
        cmd.args(["--ui=test", "--ui-check-missing", "--do-master-diff"]);
    }

    cmd.env("TREZOR_TRANSLATIONS_DIR", project_dir.join("translations"))
        .current_dir(&project_dir);

    println!("xtask: Running device tests");
    println!("\x1b[1;90m{}\x1b[0m", helpers::command_args_to_string(&cmd));

    let status = cmd.status().context("Failed to spawn `pytest`")?;

    match status.code() {
        Some(0) | Some(1) => {
            // 0 = all tests passed, 1 = some tests failed (pytest convention)
            // Continue as normal
        }
        Some(code) => {
            // pytest exited with an unexpected code
            anyhow::bail!("pytest exited with unexpected code: {}", code);
        }
        None => {
            // pytest did not exit normally (e.g., killed by signal)
            anyhow::bail!("pytest did not exit normally (terminated by signal or unknown error)");
        }
    }

    Ok(())
}
