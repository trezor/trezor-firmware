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

    // On a tree model only the signed release is installable.
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

/// Install a pq_secure release bundle via trezorctl. No `-s`: the bundle
/// carries its own signatures, which trezorctl checks first.
fn upload_release(args: &UploadArgs) -> Result<()> {
    // From the published set, the same one `xtask flash` uses, packed because
    // trezorctl takes a file.
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

    // Firmware without an explicit variant is left to trezorctl, after checking
    // the release holds a firmware variant at all.
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
