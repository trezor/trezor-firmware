use anyhow::{Context, Result, ensure};
use std::process;

use crate::args::UploadArgs;
use crate::helpers::artifacts_dir;

pub fn upload(args: UploadArgs) -> Result<()> {
    ensure!(
        args.component.uploadable(),
        "trezorctl upload is not supported for `{}`",
        args.component.binary_name()
    );

    let binary = artifacts_dir(args.model)?.join(format!("{}.bin", args.component.binary_name()));

    let binary = binary
        .canonicalize()
        .with_context(|| format!("Failed to locate `{}` for upload", binary.display()))?;

    println!(
        "Uploading `{}` to device using `trezorctl`",
        binary.display()
    );

    let status = process::Command::new("trezorctl")
        .args(["fw", "update", "-s", "-f"])
        .arg(binary)
        .status()
        .context("Failed to spawn `trezorctl`")?;

    ensure!(status.success(), "`trezorctl` failed with status: {status}");

    Ok(())
}
