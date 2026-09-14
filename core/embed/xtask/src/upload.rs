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
    // Installed from the PUBLISHED set, the same one `xtask flash` uses, so a
    // build cannot reach the device by one path and not the other. `trezorctl
    // firmware update -f` takes a FILE, so that directory is packed here rather
    // than a second copy of the release being kept in step with it.
    //
    // The cut release in `tree/` is a publishable artifact, not the install
    // source: `xtask release` overwrites `tree/<MODEL>.zip` too, so installing
    // from there made "did my last build reach the device?" depend on which
    // command wrote that file last.
    let dir = helpers::artifacts_dir(args.model)?;
    ensure!(
        dir.join("bundle.json").exists(),
        "no installable release in {dir} -- those binaries are not a signed set \
         (a bare `build bootloader` invalidates it). Build or cut one:\n             \
         xtask build firmware -m {model} --bootloader-devel",
        dir = dir.display(),
        model = args.model.model_id(),
    );
    let bundle = pq::pack_install_zip(args.model)?;

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
