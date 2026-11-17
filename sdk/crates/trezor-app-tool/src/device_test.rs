//! Runs an app's Python device-test suite (pytest) against an already-built
//! artifact and an already-running Trezor emulator or physical device.

use crate::{
    args::{DeviceTestArgs, UiMode},
    cargo, helpers, pygen,
};
use anyhow::{Context, Result, bail};
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

    cmd.current_dir(package_dir);

    println!("app-tool: Running device tests");
    println!("\x1b[1;90m{}\x1b[0m", helpers::command_args_to_string(&cmd));

    let status = cmd.status().context("Failed to spawn `pytest`")?;
    check_pytest_status(status.code())
}

/// Maps the pytest exit code to a result; only 0 (all tests passed) is success.
fn check_pytest_status(code: Option<i32>) -> Result<()> {
    match code {
        Some(0) => Ok(()),
        Some(1) => bail!("Device tests failed"),
        Some(code) => bail!("pytest exited with code {code}"),
        // e.g. killed by a signal
        None => bail!("pytest did not exit normally"),
    }
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

    #[test]
    fn pytest_status_only_zero_is_success() {
        assert!(check_pytest_status(Some(0)).is_ok());
        let error = check_pytest_status(Some(1)).unwrap_err();
        assert!(error.to_string().contains("Device tests failed"));
        assert!(check_pytest_status(Some(2)).is_err());
        assert!(check_pytest_status(None).is_err());
    }
    use clap::Parser;

    fn parse_ui(args: &[&str]) -> Option<UiMode> {
        let base = ["app-tool", "device-test", "-m", "t3w1"];
        let cli = Cli::try_parse_from([&base[..], args].concat()).unwrap();
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
