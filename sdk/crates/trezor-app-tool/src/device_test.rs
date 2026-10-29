//! Runs an app's Python device-test suite (pytest) against an already-built
//! artifact and an already-running Trezor emulator or physical device.

use crate::{
    args::{DeviceTestArgs, UiMode},
    cargo, helpers, pygen,
};
use anyhow::{Context, Result};
use cargo_metadata::Package;
use std::{path::Path, process};

/// Runs `pytest` against the app in artifacts folder.
/// Requires a Trezor emulator or physical device to already be
/// running and reachable; this does not start one itself.
pub fn test(args: DeviceTestArgs) -> Result<()> {
    let packages = cargo::build_packages(&args.build)?;

    for (package, app_path) in &packages {
        test_package(package, app_path, &args)?;
    }

    Ok(())
}

fn test_package(package: &Package, app_path: &Path, args: &DeviceTestArgs) -> Result<()> {
    let lang = args.device_lang.unwrap_or(args.build.lang);

    let package_dir = helpers::package_dir(package)?;
    pygen::generate(package_dir)?;

    let mut cmd = process::Command::new("uv");
    cmd.args([
        "run",
        "pytest",
        &format!("--app={}", app_path.display()),
        "--verbose",
        &format!("--lang={}", lang.name()),
        args.test.as_str(),
    ]);

    cmd.args(ui_args(args.ui));

    cmd.env("TREZOR_TRANSLATIONS_DIR", package_dir.join("translations"))
        .current_dir(package_dir);

    println!("app-tool: Running device tests");
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

/// Pytest flags for UI screenshot testing, as in Core's `test_emu_ui*` targets.
fn ui_args(ui: Option<UiMode>) -> &'static [&'static str] {
    match ui {
        None => &[],
        Some(UiMode::Test) => &["--ui=test", "--ui-check-missing", "--do-master-diff"],
        Some(UiMode::Record) => &["--ui=record", "--ui-check-missing", "--do-master-diff"],
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::args::{Cli, Cmd};
    use clap::Parser;

    fn parse_ui(args: &[&str]) -> Option<UiMode> {
        let cli = Cli::try_parse_from([&["app-tool", "device-test"], args].concat()).unwrap();
        match cli.command {
            Cmd::DeviceTest(args) => args.ui,
            _ => unreachable!(),
        }
    }

    #[test]
    fn bare_ui_means_test() {
        assert_eq!(parse_ui(&[]), None);
        assert_eq!(parse_ui(&["--ui"]), Some(UiMode::Test));
        assert_eq!(parse_ui(&["--ui", "test"]), Some(UiMode::Test));
        assert_eq!(parse_ui(&["--ui=record"]), Some(UiMode::Record));
        assert_eq!(parse_ui(&["--ui", "--lang", "en"]), Some(UiMode::Test));
    }

    #[test]
    fn ui_args_per_mode() {
        assert!(ui_args(None).is_empty());
        assert_eq!(
            ui_args(Some(UiMode::Test)),
            ["--ui=test", "--ui-check-missing", "--do-master-diff"]
        );
        assert_eq!(
            ui_args(Some(UiMode::Record)),
            ["--ui=record", "--ui-check-missing", "--do-master-diff"]
        );
    }
}
