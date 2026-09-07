use std::process;

use anyhow::{Context, Result, ensure};

use crate::args::{Project, UploadArgs};
use crate::{helpers, pq};

pub fn upload(args: UploadArgs) -> Result<()> {
    ensure!(
        args.project.uploadable(),
        "trezorctl upload is not supported for `{}`",
        args.project.binary_name()
    );

    // On a tree model the per-project artifact is NOT installable: `xtask build`
    // emits a manifest template there, with zero code_hashes and a leaf that
    // folds to nothing. What installs is the signed release.
    if args.model.config()?.has_feature("pq_secure_boot") {
        return upload_release(&args);
    }

    let binary =
        helpers::artifacts_dir(args.model)?.join(format!("{}.bin", args.project.binary_name()));

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

/// Install a pq_secure release bundle.
///
/// Deliberately without `-s`, unlike the single-image path above: the bundle
/// carries a boot-header signature, every variant's fold to firmware_root and
/// per-module code hashes, and checking those before touching the device is
/// most of the reason the release is one file.
fn upload_release(args: &UploadArgs) -> Result<()> {
    let dir = pq::release_dir(args.model)?;
    let bundle = dir.with_extension("zip");

    ensure!(
        bundle.exists(),
        "no pq_secure release at {} -- build one first:\n             xtask build firmware -m {} --bootloader-devel",
        bundle.display(),
        args.model.model_id()
    );

    let release = pq::ReleaseManifest::load(&dir)?;

    // An explicit choice, and `upload prodtest` (whose project names its own
    // variant), are resolved against the release. Firmware without one is left
    // to trezorctl, which picks btc-only vs universal from the device's own
    // features -- but only after checking the release holds a firmware variant
    // at all. Without that check trezorctl takes the bundle's only variant, so
    // `upload firmware` against a prodtest-only release installed PRODTEST.
    let variant = match args.variant {
        Some(_) => Some(pq::pick_variant(args.project, args.variant, &release)?),
        None if args.project == Project::Prodtest => {
            Some(pq::pick_variant(args.project, None, &release)?)
        }
        None => {
            ensure!(
                release.variants().any(|v| v.project() == args.project),
                "this release holds no `{}` variant (it has {}) -- build one, or \
                 upload the project it does hold",
                args.project.binary_name(),
                release.names()
            );
            None
        }
    };
    let variant = variant.map(|v| v.name().to_string());

    println!(
        "Uploading `{}`{} to device using `trezorctl`",
        bundle.display(),
        variant
            .as_deref()
            .map(|v| format!(" (variant {v})"))
            .unwrap_or_default()
    );

    let mut cmd = process::Command::new("trezorctl");
    cmd.args(["firmware", "update", "-f"]).arg(&bundle);
    if let Some(variant) = &variant {
        cmd.args(["--variant", variant]);
    }

    let status = cmd.status().context("Failed to spawn `trezorctl`")?;
    ensure!(status.success(), "`trezorctl` failed with status: {status}");
    Ok(())
}
