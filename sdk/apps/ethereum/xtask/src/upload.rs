use anyhow::{Context, Result, ensure};
use std::process;

use crate::{args::UploadArgs, helpers};

pub fn upload(args: UploadArgs) -> Result<u64> {
    let binary =
        helpers::artifacts_dir(args.model, args.lang, args.emulator)?.join(format!("{}.elf", &args.app));

    let binary = binary
        .canonicalize()
        .with_context(|| format!("Failed to locate `{}` for upload", binary.display()))?;

    println!(
        "Uploading `{}` to device using `trezorctl`",
        binary.display()
    );

    let output = process::Command::new("uv")
        .args(["run", "trezorctl", "extapp", "load"])
        .arg(&binary)
        .output()
        .context("Failed to spawn `trezorctl`")?;

    ensure!(
        output.status.success(),
        "`trezorctl` failed with status: {}",
        output.status
    );

    let stdout = String::from_utf8_lossy(&output.stdout);
    print!("{stdout}");

    let app_hash = stdout
        .lines()
        .find(|l| l.starts_with("Loaded app hash: "))
        .and_then(|l| l.strip_prefix("Loaded app hash: "))
        .map(|s| s.trim())
        .context("Could not parse app hash from trezorctl output")?;

    let app_hash = u64::from_str_radix(app_hash, 16)
        .with_context(|| format!("Failed to parse app hash as hex: {app_hash}"))?;

    println!("App hash: {app_hash:#018x}");

    Ok(app_hash)
}
