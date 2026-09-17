use std::process;

use anyhow::{Context, Result, ensure};

use crate::args::{Project, UploadArgs};
use crate::{bundle, helpers};

pub fn upload(args: UploadArgs) -> Result<()> {
    ensure!(
        args.project.uploadable(),
        "trezorctl upload is not supported for `{}`",
        args.project.binary_name()
    );

    // On a tree model only the signed bundle is installable.
    if args.model.config()?.has_feature("pq_secure_boot") {
        upload_bundle(&args)
    } else {
        upload_binary(&args)
    }
}

/// Install a plain signed binary via trezorctl.
fn upload_binary(args: &UploadArgs) -> Result<()> {
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

/// Install a pq_secure bundle via trezorctl. No `-s`: the bundle
/// carries its own signatures, which trezorctl checks first.
fn upload_bundle(args: &UploadArgs) -> Result<()> {
    // From the published bundle, the same one `xtask flash` uses, packed because
    // trezorctl takes a file.
    let dir = helpers::artifacts_dir(args.model)?;
    ensure!(
        dir.join("bundle.json").exists(),
        "no installable bundle in {dir} -- those binaries are not a signed bundle \
         (a bare `build bootloader` invalidates it). Build or cut one:\n             \
         xtask build firmware -m {model} --bootloader-devel",
        dir = dir.display(),
        model = args.model.model_id(),
    );
    let archive = bundle::pack_bundle_archive(args.model)?;

    let manifest = bundle::BundleManifest::load(&dir)?;

    // Firmware without an explicit variant is left to trezorctl, after checking
    // the bundle holds a firmware variant at all.
    let variant = match args.variant {
        Some(_) => Some(bundle::pick_variant(args.project, args.variant, &manifest)?),
        None if args.project == Project::Prodtest => {
            Some(bundle::pick_variant(args.project, None, &manifest)?)
        }
        None => {
            ensure!(
                manifest.variants().any(|v| v.project() == args.project),
                "this bundle holds no `{}` variant (it has {}) -- build one, or \
                 upload the project it does hold",
                args.project.binary_name(),
                manifest.names()
            );
            None
        }
    };
    let variant = variant.map(|v| v.name().to_string());

    println!(
        "Uploading `{}`{} to device using `trezorctl`",
        archive.display(),
        variant
            .as_deref()
            .map(|v| format!(" (variant {v})"))
            .unwrap_or_default()
    );

    let mut cmd = process::Command::new("trezorctl");
    cmd.args(["firmware", "update", "-f"]).arg(&archive);
    if let Some(variant) = &variant {
        cmd.args(["--variant", variant]);
    }

    let status = cmd.status().context("Failed to spawn `trezorctl`")?;
    ensure!(status.success(), "`trezorctl` failed with status: {status}");
    Ok(())
}
