//! `xtask release`: every variant of every tree model, cut together.
//!
//! A release is the cross-model output in `build/artifacts/release/`: one
//! bundle directory per model, the release manifest that indexes them, the
//! signature set and the release archive. See docs/core/build/xtask.md.

use std::path::{Path, PathBuf};
use std::{fs, process};

use anyhow::{Context, Result, bail, ensure};
use clap::ValueEnum;
use owo_colors::OwoColorize;

use crate::args::{BuildArgs, Project, ReleaseArgs};
use crate::bundle::{
    self, ALL_VARIANTS, BundleManifest, DEFAULT_BOOTLOADER_FILE, Dest, FORMAT_VERSION, SignStage,
};
use crate::helpers;
use crate::model::Model;
use crate::options::ResolvedBuildArgs;

/// Release magic: a release manifest indexes one bundle manifest per model.
const RELEASE_MAGIC: &str = "TRZL-set";

/// Where a release is cut: `build/artifacts/release/`.
fn release_dir() -> Result<PathBuf> {
    // Normalised: cargo reports the target dir as `core/embed/../build`.
    let dir = helpers::release_dir()?;
    Ok(dir.canonicalize().unwrap_or(dir))
}

/// Where a model's bundle is assembled in a release:
/// `build/artifacts/release/<MODEL>/`, with its archive alongside it as
/// `<MODEL>.zip`.
pub fn bundle_dir(model: Model) -> Result<PathBuf> {
    Ok(release_dir()?.join(model.model_id()))
}

/// One model's bundle manifest, from a release manifest.
pub fn read_model_entry(manifest: &Path, model_id: &str) -> Result<serde_json::Value> {
    let raw = fs::read_to_string(manifest)
        .with_context(|| format!("Failed to read {}", manifest.display()))?;
    let doc: serde_json::Value = serde_json::from_str(&raw)
        .with_context(|| format!("{} is not valid JSON", manifest.display()))?;
    let expected = RELEASE_MAGIC;
    let format = doc
        .get("format")
        .and_then(|v| v.as_str())
        .with_context(|| {
            format!(
                "{} has no `format` -- it predates the versioned release manifest, \
                 re-promote it",
                manifest.display()
            )
        })?;
    ensure!(
        format == expected,
        "{} is not a release manifest: format `{format}`, expected `{expected}`",
        manifest.display(),
    );
    let version = doc
        .get("format_version")
        .and_then(|v| v.as_u64())
        .with_context(|| format!("{} has no `format_version`", manifest.display()))?;
    ensure!(
        version == FORMAT_VERSION,
        "{} is release manifest v{version}, but this xtask speaks v{FORMAT_VERSION} \
         -- re-promote it (or update xtask)",
        manifest.display(),
    );
    doc.get("models")
        .and_then(|m| m.get(model_id))
        .cloned()
        .with_context(|| {
            format!(
                "{} has no entry for {model_id} -- promote a release for it first",
                manifest.display()
            )
        })
}

/// The release manifest `artifacts/release/release[_devel].json`, which
/// promotion commits.
fn release_manifest_path(devel_build: bool) -> Result<PathBuf> {
    Ok(release_dir()?.join(release_manifest_name(devel_build)))
}

/// The promoted release manifest `models/release[_devel].json` a presigned
/// custom build folds into.
pub fn prebuilt_release_manifest(devel_build: bool) -> Result<PathBuf> {
    Ok(helpers::workspace_dir()?
        .join("models")
        .join(release_manifest_name(devel_build)))
}

/// `release.json` for production keys, `release_devel.json` for development.
fn release_manifest_name(devel_build: bool) -> String {
    let suffix = if devel_build { "_devel" } else { "" };
    format!("release{suffix}.json")
}

/// Pack every model's bundle into one publishable release archive. The packer
/// (`release_pack.py`) names it `release[-devel].zip` from the signatures it
/// finds, since xtask cannot verify them.
fn write_release_archive(manifest: &Path, devel_build: bool) -> Result<()> {
    let packer = helpers::workspace_dir()?
        .join("../tools/trezor_core_tools/release_pack.py")
        .canonicalize()
        .context("Failed to locate release_pack.py")?;
    let dir = release_dir()?;
    let status = process::Command::new("python3")
        .arg(&packer)
        .args(["--release".as_ref(), manifest.as_os_str()])
        .args(["--dir".as_ref(), dir.as_os_str()])
        .args(["--out-dir".as_ref(), dir.as_os_str()])
        .args(if devel_build {
            vec!["--devel-build"]
        } else {
            vec![]
        })
        .status()
        .context("Failed to spawn release_pack.py")?;
    ensure!(status.success(), "release_pack.py failed: {status}");
    Ok(())
}

/// Sign a prepared release with development keys -- the ceremony's stand-in.
fn devsign(manifest: &Path, dir: &Path, out: &Path) -> Result<()> {
    let tool = helpers::workspace_dir()?
        .join("../tools/trezor_core_tools/firmware_pq_devsign.py")
        .canonicalize()
        .context("Failed to locate firmware_pq_devsign.py")?;
    let status = process::Command::new("python3")
        .arg(&tool)
        .args(["--manifest".as_ref(), manifest.as_os_str()])
        .args(["--dir".as_ref(), dir.as_os_str()])
        .args(["--out".as_ref(), out.as_os_str()])
        .status()
        .context("Failed to spawn firmware_pq_devsign.py")?;
    ensure!(status.success(), "firmware_pq_devsign.py failed: {status}");
    Ok(())
}

/// Patch founder signatures into a prepared release. Signatures land in
/// unauthenticated space, so nothing the prepare stage folded is invalidated.
fn attach(manifest: &Path, dir: &Path, signatures: &Path) -> Result<()> {
    let tool = helpers::workspace_dir()?
        .join("../tools/trezor_core_tools/firmware_pq_attach.py")
        .canonicalize()
        .context("Failed to locate firmware_pq_attach.py")?;
    let status = process::Command::new("python3")
        .arg(&tool)
        .args(["--manifest".as_ref(), manifest.as_os_str()])
        .args(["--dir".as_ref(), dir.as_os_str()])
        .args(["--signatures".as_ref(), signatures.as_os_str()])
        .status()
        .context("Failed to spawn firmware_pq_attach.py")?;
    ensure!(status.success(), "firmware_pq_attach.py failed: {status}");
    Ok(())
}

/// Write the release manifest: every model's `bundle.json` in one file keyed
/// by model id. Models are independent trees, each with its own root and
/// signature.
fn write_release_manifest(models: &[Model], devel_build: bool) -> Result<PathBuf> {
    let mut entries = serde_json::Map::new();
    for model in models {
        let per_model = bundle_dir(*model)?.join("bundle.json");
        let raw = fs::read_to_string(&per_model)
            .with_context(|| format!("Failed to read {}", per_model.display()))?;
        let body: serde_json::Value = serde_json::from_str(&raw)
            .with_context(|| format!("{} is not valid JSON", per_model.display()))?;
        entries.insert(model.model_id().to_string(), body);
    }

    let mut doc = serde_json::Map::new();
    // Per-model bodies keep their own `format` tags: `build_presigned` lifts
    // one out as a standalone bundle manifest.
    doc.insert(
        "format".to_string(),
        serde_json::Value::String(RELEASE_MAGIC.to_string()),
    );
    doc.insert(
        "format_version".to_string(),
        serde_json::Value::from(FORMAT_VERSION),
    );
    doc.insert("models".to_string(), serde_json::Value::Object(entries));

    let path = release_manifest_path(devel_build)?;
    fs::create_dir_all(path.parent().context("release manifest has no parent")?)?;
    fs::write(&path, serde_json::to_string_pretty(&doc)? + "\n")
        .with_context(|| format!("Failed to write {}", path.display()))?;
    println!(
        "{}",
        format!("xtask: release manifest written to {}", path.display()).green()
    );
    Ok(path)
}

/// Copy a release into `models/` as the prebuilt reference a presigned
/// custom build reads. Release manifest, bootloader, secmon pair and nRF image
/// are copied together and re-verified by `presigned_check`.
fn promote(models: &[Model], devel_build: bool) -> Result<()> {
    let models_dir = helpers::workspace_dir()?.join("models");
    let suffix = if devel_build { "_devel" } else { "" };

    let manifest = release_manifest_path(devel_build)?;
    let manifest_dst = prebuilt_release_manifest(devel_build)?;
    fs::copy(&manifest, &manifest_dst).with_context(|| {
        format!(
            "Failed to copy {} -> {}",
            manifest.display(),
            manifest_dst.display()
        )
    })?;
    println!("  release manifest -> {}", manifest_dst.display());

    for model in models {
        let out = bundle_dir(*model)?;
        let id = model.model_id();

        // The signed bootloader replaces the prebuilt one.
        let bl_dst = models_dir
            .join(id)
            .join("bootloaders")
            .join(format!("bootloader_{id}{suffix}.bin"));
        fs::copy(out.join(DEFAULT_BOOTLOADER_FILE), &bl_dst)
            .with_context(|| format!("Failed to write {}", bl_dst.display()))?;
        println!("  {id} bootloader -> {}", bl_dst.display());

        // The secmon travels as a pair: the kernel links the veneer object.
        let secmon_dir = models_dir.join(id).join("secmon");
        let (bin_name, api_name) = if devel_build {
            ("secmon_DEV.bin", "secmon_api_DEV.o")
        } else {
            ("secmon.bin", "secmon_api.o")
        };
        // From the release, not `artifacts/`: the secmon the custom slot was
        // signed over.
        for (src_name, dst_name) in [("secmon.bin", bin_name), ("secmon_api.o", api_name)] {
            let src = out.join(src_name);
            if !src.exists() {
                bail!(
                    "{} is missing -- the release must keep the secmon its custom \
                     slot was signed over, so re-cut the release",
                    src.display()
                );
            }
            let dst = secmon_dir.join(dst_name);
            fs::copy(&src, &dst).with_context(|| format!("Failed to write {}", dst.display()))?;
            println!("  {id} {dst_name} -> {}", dst.display());
        }

        // On a PQ-native model signing rewrites the nRF image, so the release
        // copy is committed. It lands beside `trezor-ble{suffix}-bare.bin`,
        // never on it: the bare image is the next release's input.
        let nrf_suffix = if devel_build { "-dev" } else { "" };
        let nrf_name = format!("trezor-ble{nrf_suffix}.bin");
        let nrf_src = out.join(&nrf_name);
        if nrf_src.exists() {
            let nrf_dst = models_dir.join(id).join(&nrf_name);
            fs::copy(&nrf_src, &nrf_dst)
                .with_context(|| format!("Failed to write {}", nrf_dst.display()))?;
            println!("  {id} {nrf_name} -> {}", nrf_dst.display());
        }
    }

    // Verified now; a wrong combination otherwise fails only at a later
    // presigned build.
    println!("{}", "xtask: verifying the promoted set".bold().dimmed());
    let checker = helpers::workspace_dir()?
        .join("../tools/trezor_core_tools/presigned_check.py")
        .canonicalize()
        .context("Failed to locate presigned_check.py")?;
    let status = process::Command::new("python3")
        .arg("-m")
        .arg("trezor_core_tools.presigned_check")
        .env(
            "PYTHONPATH",
            checker
                .parent()
                .and_then(|p| p.parent())
                .context("presigned_check has no package parent")?,
        )
        .status()
        .context("Failed to spawn presigned_check")?;
    ensure!(
        status.success(),
        "the promoted set does not hang together -- see the failures above. \
         The files are written; re-promote from a consistent release rather \
         than shipping this one."
    );

    println!("{}", "xtask: promoted and verified".green());
    Ok(())
}

/// Cut a complete pq_secure release: every variant of every tree model, each
/// in its own signed founder tree. See docs/core/build/xtask.md.
pub fn release(args: ReleaseArgs) -> Result<()> {
    let models: Vec<Model> = Model::value_variants()
        .iter()
        .copied()
        .filter(|m| {
            m.config()
                .map(|c| c.has_feature("pq_secure_boot"))
                .unwrap_or(false)
        })
        .collect();
    ensure!(
        !models.is_empty(),
        "no model uses the Merkle-tree layout, so there is nothing to release"
    );
    println!(
        "xtask: releasing every tree model: {}",
        models
            .iter()
            .map(|m| m.model_id())
            .collect::<Vec<_>>()
            .join(", ")
    );

    let mut devel_build: Option<bool> = None;
    for model in &models {
        let model = *model;
        let build_args = BuildArgs {
            project: Project::Firmware,
            model,
            emulator: false,
            preset: args.preset.clone(),
            options: args.options.clone(),
        };
        let resolved = ResolvedBuildArgs::from_build_args(&build_args)?;
        ensure!(
            bundle::applies(&resolved)?,
            "{} does not use the Merkle-tree layout, so it has no release to cut",
            model.model_id()
        );
        // `--bootloader-devel` picks the founder pool, `--production` the
        // translation/coin-definition keys. Neither would enforce secure boot
        // while accepting data signed with keys from this repository.
        ensure!(
            resolved.bootloader_devel || resolved.production,
            "a release built without --bootloader-devel carries PRODUCTION \
             founder keys, but without --production it also carries \
             DEVELOPMENT translation and coin-definition keys -- it would \
             enforce secure boot while accepting data signed with keys from \
             this repository.\n             \
             Pass --production to cut a real release, or --bootloader-devel \
             for a development one."
        );
        // Prepare: every model is folded before any is signed.
        bundle::build_bundle(
            &resolved,
            &ALL_VARIANTS,
            SignStage::PrepareOnly,
            Dest::Release,
            args.sigmask,
        )?;
        devel_build = Some(resolved.bootloader_devel);
    }

    // One run, one key selection.
    let devel_build = devel_build.context("no model was released")?;
    let manifest = write_release_manifest(&models, devel_build)?;
    let dir = release_dir()?;
    // Sign + attach only for a development cut; a production release stops
    // here unsigned, and `attach` completes it after the ceremony.
    if devel_build {
        let signatures = dir.join("signatures-devel.json");
        devsign(&manifest, &dir, &signatures)?;
        attach(&manifest, &dir, &signatures)?;
        // Publish each model's now-signed bootloader for `flash`/`upload`.
        for model in &models {
            let out = bundle_dir(*model)?;
            bundle::publish_bootloader(*model, &out)?;
            bundle::publish_images(*model, &out, &ALL_VARIANTS, &BundleManifest::load(&out)?)?;
            // Repacked: `bundle.zip` is a view of the published bundle.
            bundle::pack_bundle_archive(*model)?;
        }
    } else {
        println!(
            "{}",
            "xtask: prepared UNSIGNED -- sign the recorded modelRoots, then \
             `firmware_pq_attach.py --manifest <manifest> --dir <dir> \
             --signatures <sigs>`"
                .bold()
                .dimmed()
        );
    }

    // Packed last; the packer names the archive from the signing state.
    write_release_archive(&manifest, devel_build)?;
    if args.promote {
        // Promotion needs a signed release.
        ensure!(
            devel_build,
            "this release was prepared UNSIGNED, so there is nothing to \
             promote yet -- attach the ceremony's signatures first, then \
             promote the signed release"
        );
        promote(&models, devel_build)?;
    }
    Ok(())
}
