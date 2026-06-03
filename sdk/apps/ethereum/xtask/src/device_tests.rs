use anyhow::{Context, Result, ensure};
use std::process;

use crate::{args::DeviceTestArgs, helpers};

pub fn device_tests(args: DeviceTestArgs) -> Result<()> {
    let binary = helpers::artifacts_dir(args.model, args.lang, args.emulator)?
        .join(format!("{}.elf", &args.app));

    let binary = binary
        .canonicalize()
        .with_context(|| format!("Failed to locate `{}` for upload", binary.display()))?;

    let status = process::Command::new("uv")
        .args([
            "run",
            "pytest",
            &format!("--app={}", binary.display()),
            &format!("--lang={}", args.lang.name()),
            "--ui=test",
            "--verbose",
            args.test.as_str(),
        ])
        .env("TREZOR_TRANSLATIONS_DIR", "translations")
        .status()
        .context("Failed to spawn `pytest`")?;

    ensure!(status.success(), "`pytest` failed with status: {}", status);
    Ok(())
}
