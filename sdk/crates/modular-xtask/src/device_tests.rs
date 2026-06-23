use crate::{args::DeviceTestsArgs, helpers};
use anyhow::{Context, Result, ensure};
use std::process;

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
        args.test.as_str(),
    ]);

    if args.emulator {
        cmd.arg("--ui=test");
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

    if args.emulator {
        let mut port = 8000;
        let max_tries = 10;
        let mut spawned = false;

        for _ in 0..max_tries {
            let mut cmd = process::Command::new("uv");
            cmd.args([
                "run",
                "--",
                project_dir
                    .join("tests")
                    .join("show_results.py")
                    .to_str()
                    .unwrap(),
                "--port",
                &port.to_string(),
            ])
            .current_dir(&project_dir);

            println!("xtask: Showing device test results (port {port})");
            println!("\x1b[1;90m{}\x1b[0m", helpers::command_args_to_string(&cmd));

            match cmd.spawn() {
                Ok(_) => {
                    spawned = true;
                    break;
                }
                Err(e) => {
                    if let Some(os_err) = e.raw_os_error() {
                        if os_err == 98 {
                            port += 1;
                            continue;
                        }
                    }
                    return Err(e).context("Failed to spawn `show_results.py`");
                }
            }
        }

        if !spawned {
            anyhow::bail!(
                "Could not start show_results.py on any port in range 8000-{}",
                8000 + max_tries - 1
            );
        }
    }
    Ok(())
}
