//! Per-model pq_secure (Merkle-tree) bundles.
//!
//! A bundle is one model's set of files -- bootloader, one or more firmware
//! variants and the nRF image -- described by its `bundle.json`. A tree
//! firmware image is only installable next to a bootloader whose signed header
//! commits to its `firmware_root`, so `xtask build firmware` on a tree model
//! produces a bundle rather than one binary. Re-signing rewrites only the boot
//! header, never the bootloader code. See docs/core/build/xtask.md.

use std::path::{Path, PathBuf};
use std::{fs, process};

use anyhow::{Context, Result, bail, ensure};
use clap::ValueEnum;
use owo_colors::OwoColorize;
use serde::Deserialize;

use crate::args::Project;
use crate::config::BoardConfig;
use crate::model::Model;
use crate::options::ResolvedBuildArgs;
use crate::{cargo, helpers, release};

/// One variant of a bundle: one leaf of the founder firmware tree.
#[derive(ValueEnum, Clone, Copy, PartialEq, Eq, Debug)]
#[value(rename_all = "kebab-case")]
pub enum Variant {
    Universal,
    BtcOnly,
    /// Unofficial slot: the leaf zeroes the app size, code_hash and version.
    Custom,
    /// Its own project, not a firmware variant, but a leaf of the same tree.
    Prodtest,
}

/// Which bootloader binary a bundle folds its `firmware_root` into.
///
/// Must have been built with the same key selection the bundle is signed
/// with (`--bootloader-devel`); signing rewrites the header, not the code.
#[derive(ValueEnum, Deserialize, Clone, Copy, PartialEq, Eq, Debug, Default)]
#[value(rename_all = "kebab-case")]
#[serde(rename_all = "kebab-case")]
pub enum BootloaderSource {
    /// The fresh bootloader for this model, else the prebuilt binary.
    #[default]
    Auto,
    /// Fresh: `build/artifacts/<MODEL>/bootloader.bin`; an error if absent.
    Fresh,
    /// The prebuilt binary in `models/<MODEL>/bootloaders/` -- what a
    /// production release folds.
    Prebuilt,
}

/// Every variant of a full bundle; the founder tree must contain them all.
pub const ALL_VARIANTS: [Variant; 4] = [
    Variant::Universal,
    Variant::BtcOnly,
    Variant::Custom,
    Variant::Prodtest,
];

impl Variant {
    /// Name in the bundle directory and in bundle.json.
    pub fn name(self) -> &'static str {
        match self {
            Variant::Universal => "universal",
            Variant::BtcOnly => "btc-only",
            Variant::Custom => "custom",
            Variant::Prodtest => "prodtest",
        }
    }

    /// The variant a bundle directory names, as recorded in bundle.json.
    pub fn from_name(name: &str) -> Option<Variant> {
        ALL_VARIANTS.into_iter().find(|v| v.name() == name)
    }

    /// Which project builds this variant.
    pub fn project(self) -> Project {
        match self {
            Variant::Prodtest => Project::Prodtest,
            _ => Project::Firmware,
        }
    }

    /// The built artifact this variant is collected from.
    fn artifact(self) -> &'static str {
        match self {
            Variant::Prodtest => "prodtest.bin",
            _ => "firmware.bin",
        }
    }

    /// Point a resolved arg set at this variant via the existing build flags.
    fn apply(self, args: &mut ResolvedBuildArgs) {
        args.project = self.project();
        args.btc_only = matches!(self, Variant::BtcOnly);
        args.unsafe_fw = matches!(self, Variant::Custom);
    }
}

/// Bundle manifest magic, and the layout version bundle and release
/// manifests share; must match the signer (`firmware_pq_sign.py`), which
/// states its own copy.
const BUNDLE_MAGIC: &str = "TRZL";
pub(crate) const FORMAT_VERSION: u64 = 1;

/// The bootloader's filename inside a bundle, as the writer names it.
pub(crate) const DEFAULT_BOOTLOADER_FILE: &str = "bootloader.bin";

/// Where a build assembles what it signs. A plain build signs in place;
/// `artifacts/release/` belongs to `xtask release` alone.
#[derive(Clone, Copy, PartialEq, Eq)]
pub enum Dest {
    /// `build/artifacts/<MODEL>/` -- the canonical bundle.
    Artifacts,
    /// `build/artifacts/release/<MODEL>/` -- one model's bundle in a release
    /// being cut.
    Release,
}

/// Whether a bundle is signed as it is built, or prepared for a later
/// ceremony (prepare / sign / attach, see docs/core/build/xtask.md).
#[derive(Clone, Copy, PartialEq, Eq)]
pub enum SignStage {
    /// Fold and sign in one step, with development keys.
    Inline,
    /// Fold only; leave the signature region zero for a later `attach`.
    PrepareOnly,
}

/// One variant of a bundle, as its manifest records it.
struct VariantEntry {
    variant: Variant,
    firmware_type: u32,
    file: String,
}

/// What a signed bundle records about itself, from its `bundle.json`.
/// Routing only -- the boot-header signature is the trust root.
pub struct BundleManifest {
    /// Model id, from the signer's reading of the signed boot header.
    model: String,
    /// The bootloader image's name within the bundle.
    bootloader_file: String,
    /// Every variant: hardened `firmware_type` codeword and recorded filename.
    variants: Vec<VariantEntry>,
    /// Where `firmware_type` sits in the bootloader image, probed by the
    /// signer.
    firmware_type_offset: usize,
    firmware_type_len: usize,
    /// The value a bare bootloader carries.
    firmware_type_bare: u32,
}

impl BundleManifest {
    pub fn load(dir: &Path) -> Result<BundleManifest> {
        let path = dir.join("bundle.json");
        let text = fs::read_to_string(&path)
            .with_context(|| format!("Failed to read {}", path.display()))?;
        let json: serde_json::Value = serde_json::from_str(&text)
            .with_context(|| format!("Failed to parse {}", path.display()))?;

        // Identify the document before reading anything out of it.
        let format = json
            .get("format")
            .and_then(|v| v.as_str())
            .with_context(|| {
                format!(
                    "{} has no `format` -- it predates the versioned bundle \
                     manifest, rebuild it",
                    path.display()
                )
            })?;
        ensure!(
            format == BUNDLE_MAGIC,
            "{} is not a bundle manifest: format `{format}`, expected `{BUNDLE_MAGIC}`",
            path.display(),
        );
        let version = json
            .get("format_version")
            .and_then(|v| v.as_u64())
            .with_context(|| format!("{} has no `format_version`", path.display()))?;
        ensure!(
            version == FORMAT_VERSION,
            "{} is bundle manifest v{version}, but this xtask speaks \
             v{FORMAT_VERSION} -- rebuild the bundle (or update xtask)",
            path.display(),
        );

        let model = json
            .get("model")
            .and_then(|v| v.as_str())
            .with_context(|| format!("{} records no model", path.display()))?
            .to_string();

        let bootloader = json
            .get("bootloader")
            .with_context(|| format!("{} records no bootloader", path.display()))?;
        let bootloader_file = bootloader
            .get("file")
            .and_then(|v| v.as_str())
            .with_context(|| format!("{} names no bootloader file", path.display()))?
            .to_string();

        let ft = bootloader
            .get("firmware_type")
            .with_context(|| format!("{} records no firmware_type field", path.display()))?;
        let offset = ft
            .get("offset")
            .and_then(|v| v.as_u64())
            .context("bundle records no firmware_type offset")?;
        let len = ft
            .get("len")
            .and_then(|v| v.as_u64())
            .context("bundle records no firmware_type len")?;
        let bare = ft
            .get("bare")
            .and_then(|v| v.as_u64())
            .context("bundle records no bare firmware_type")?;

        let mut variants = Vec::new();
        for entry in json
            .get("variants")
            .and_then(|v| v.as_array())
            .context("bundle has no variants")?
        {
            let name = entry
                .get("variant")
                .and_then(|v| v.as_str())
                .context("a bundle variant records no variant name")?;
            let variant =
                Variant::from_name(name).with_context(|| format!("unknown variant `{name}`"))?;
            let firmware_type = entry
                .get("firmware_type")
                .and_then(|v| v.as_u64())
                .with_context(|| format!("variant `{name}` records no firmware_type"))?;
            let file = entry
                .get("file")
                .and_then(|v| v.as_str())
                .with_context(|| format!("variant `{name}` names no file"))?
                .to_string();
            variants.push(VariantEntry {
                variant,
                firmware_type: u32::try_from(firmware_type)?,
                file,
            });
        }

        Ok(BundleManifest {
            model,
            bootloader_file,
            variants,
            firmware_type_offset: usize::try_from(offset)?,
            firmware_type_len: usize::try_from(len)?,
            firmware_type_bare: u32::try_from(bare)?,
        })
    }

    /// The model this bundle is for, as the signed boot header spells it.
    pub fn model(&self) -> &str {
        &self.model
    }

    pub fn variants(&self) -> impl Iterator<Item = Variant> + '_ {
        self.variants.iter().map(|e| e.variant)
    }

    /// The image filename this bundle recorded for `variant`.
    fn firmware_file(&self, variant: Variant) -> Result<&str> {
        self.variants
            .iter()
            .find(|e| e.variant == variant)
            .map(|e| e.file.as_str())
            .with_context(|| {
                format!(
                    "`{}` is not in this bundle ({})",
                    variant.name(),
                    self.names()
                )
            })
    }

    pub fn names(&self) -> String {
        self.variants()
            .map(|v| v.name())
            .collect::<Vec<_>>()
            .join(", ")
    }

    fn firmware_type(&self, variant: Variant) -> Result<u32> {
        self.variants
            .iter()
            .find(|e| e.variant == variant)
            .map(|e| e.firmware_type)
            .with_context(|| {
                format!(
                    "`{}` is not in this bundle ({})",
                    variant.name(),
                    self.names()
                )
            })
    }

    /// Write a copy of the bundle bootloader stamped for `variant`.
    /// `firmware_type` is unauthenticated, so this needs no key.
    pub fn stamp(&self, dir: &Path, variant: Variant) -> Result<PathBuf> {
        let firmware_type = self.firmware_type(variant)?;
        let src = dir.join(&self.bootloader_file);
        let mut image =
            fs::read(&src).with_context(|| format!("Failed to read {}", src.display()))?;

        let at = self.firmware_type_offset;
        let len = self.firmware_type_len;
        ensure!(len == 4, "firmware_type_len is {len}, expected 4");
        let field = image.get(at..at + len).with_context(|| {
            format!(
                "{} is shorter than its firmware_type field at {at}..{}",
                src.display(),
                at + len
            )
        })?;
        let current = u32::from_le_bytes(field.try_into()?);
        let bare = self.firmware_type_bare;
        let path = src.display();
        // A bundle is signed bare; anything else means a stale bundle.json.
        ensure!(
            current == bare,
            "{path} already carries firmware_type 0x{current:08X} at offset {at}, \
             but a bundle is signed bare (0x{bare:08X}) -- bundle.json does not \
             match this bootloader",
        );
        image[at..at + len].copy_from_slice(&firmware_type.to_le_bytes());

        let out = dir.join(format!("bootloader-{}.bin", variant.name()));
        fs::write(&out, &image).with_context(|| format!("Failed to write {}", out.display()))?;
        Ok(out)
    }
}

/// The files of a pq_secure bundle that one install writes. Bootloader and
/// firmware are a pair: the header vouches only for the root this firmware
/// folds to.
pub struct BundleFiles {
    /// The bundle bootloader, provisioned for `variant` when there is one.
    pub bootloader: PathBuf,
    /// The firmware image, absent when only the bootloader was asked for.
    pub firmware: Option<PathBuf>,
    /// The variant this install provisions the device for, `None` for a bare
    /// bootloader.
    pub variant: Option<Variant>,
}

/// Resolve what to install from a model's bundle, stamping `firmware_type`
/// into the bootloader for the variant being installed.
pub fn resolve_bundle_files(
    model: Model,
    project: Project,
    variant: Option<Variant>,
) -> Result<BundleFiles> {
    let model_id = model.model_id();

    // A bare bootloader needs no bundle; bare is the state of a fresh device.
    if project == Project::Bootloader && variant.is_none() {
        // Whatever last wrote `artifacts/<MODEL>/bootloader.bin` is canonical.
        let bootloader = helpers::artifacts_dir(model)?.join("bootloader.bin");
        ensure!(
            bootloader.exists(),
            "no bootloader for {model_id} -- build one first:\n             \
             xtask build bootloader -m {model_id} --bootloader-devel",
        );
        return Ok(BundleFiles {
            bootloader,
            firmware: None,
            variant: None,
        });
    }

    // No signing here: `bundle.json` marks the binaries as a signed bundle,
    // and `xtask build bootloader` removes it.
    let dir = helpers::artifacts_dir(model)?;
    ensure!(
        dir.join("bundle.json").exists(),
        "no installable bundle in {dir} -- those binaries are not a signed bundle \
         (a bare `build bootloader` invalidates it). Build or cut one:\n             \
         xtask build firmware -m {model_id} --bootloader-devel",
        dir = dir.display(),
    );
    let bundle = BundleManifest::load(&dir)?;

    if project == Project::Bootloader {
        let variant = variant.expect("bare bootloader handled above");
        return Ok(BundleFiles {
            bootloader: bundle.stamp(&dir, variant)?,
            firmware: None,
            variant: Some(variant),
        });
    }

    let variant = pick_variant(project, variant, &bundle)?;
    Ok(BundleFiles {
        bootloader: bundle.stamp(&dir, variant)?,
        firmware: Some(dir.join(bundle.firmware_file(variant)?)),
        variant: Some(variant),
    })
}

/// Which variant of a bundle to install: an explicit choice wins, then the
/// project, then the bundle's only firmware variant.
pub fn pick_variant(
    project: Project,
    requested: Option<Variant>,
    bundle: &BundleManifest,
) -> Result<Variant> {
    if let Some(variant) = requested {
        ensure!(
            variant.project() == project,
            "`{}` is built by `{}`, not `{}`",
            variant.name(),
            variant.project().binary_name(),
            project.binary_name()
        );
        return Ok(variant);
    }

    let mut candidates = bundle.variants().filter(|v| v.project() == project);
    let first = candidates.next().with_context(|| {
        format!(
            "this bundle holds no `{}` variant (it has {})",
            project.binary_name(),
            bundle.names()
        )
    })?;
    ensure!(
        candidates.next().is_none(),
        "this bundle holds several firmware variants ({}), so --variant has to \
         say which one to install",
        bundle.names()
    );
    Ok(first)
}

/// Which variant the request as given selects.
pub fn selected_variant(args: &ResolvedBuildArgs) -> Variant {
    if matches!(args.project, Project::Prodtest) {
        return Variant::Prodtest;
    }
    if args.unsafe_fw {
        Variant::Custom
    } else if args.btc_only {
        Variant::BtcOnly
    } else {
        Variant::Universal
    }
}

/// Whether this build produces a Merkle-tree bundle (never for the emulator).
pub fn applies(args: &ResolvedBuildArgs) -> Result<bool> {
    Ok(!args.emulator && args.model.config()?.has_feature("pq_secure_boot"))
}

/// Build the variants into one model's bundle, then sign it with development
/// keys or prepare it for a later ceremony.
pub fn build_bundle(
    args: &ResolvedBuildArgs,
    variants: &[Variant],
    sign: SignStage,
    dest: Dest,
    // None: the signer's development default.
    sigmask: Option<u8>,
) -> Result<()> {
    // Only an inline signature needs keys; preparing needs none.
    if sign == SignStage::Inline && !args.bootloader_devel {
        bail!(
            "signing inline needs development keys -- pass --bootloader-devel, \
             or use `xtask release` (without it) to PREPARE an unsigned release \
             for a founder ceremony to sign"
        );
    }

    let out = match dest {
        Dest::Artifacts => helpers::artifacts_dir(args.model)?,
        Dest::Release => release::bundle_dir(args.model)?,
    };
    fs::create_dir_all(&out).with_context(|| format!("Failed to create {}", out.display()))?;

    println!(
        "xtask: pq_secure bundle for {} -- variants: {}",
        args.model.model_id(),
        variants
            .iter()
            .map(|v| v.name())
            .collect::<Vec<_>>()
            .join(", ")
    );

    // Resolved first: a missing bootloader should not cost four builds.
    let bootloader = select_bootloader(args, args.bootloader)?;

    let mut firmwares: Vec<PathBuf> = Vec::new();
    for variant in variants {
        let mut variant_args = args.clone();
        variant.apply(&mut variant_args);

        println!(
            "{}",
            format!("xtask: building variant `{}`", variant.name())
                .bold()
                .dimmed()
        );
        cargo::build_project(variant_args.clone())?;

        // Keep universal's secmon beside the bundle: the custom slot's leaf
        // commits to the whole secmon entry, so promotion needs these bytes.
        if *variant == Variant::Universal && dest == Dest::Release {
            for name in ["secmon.bin", "secmon_api.o"] {
                let src = helpers::artifacts_dir(args.model)?.join(name);
                ensure!(
                    src.exists(),
                    "{} is missing -- the custom slot commits to the secmon, so \
                     the bundle has to keep the one it signed over",
                    src.display()
                );
                let dst = out.join(name);
                fs::copy(&src, &dst).with_context(|| {
                    format!("Failed to keep {} -> {}", src.display(), dst.display())
                })?;
            }
        }

        // Variants share one artifact slot; copy each out under its own name.
        let built = helpers::artifacts_dir(args.model)?.join(variant.artifact());
        let dst = match dest {
            Dest::Artifacts => built.clone(),
            Dest::Release => out.join(format!("{}.bin", variant.name())),
        };
        if dst != built {
            fs::copy(&built, &dst).with_context(|| {
                format!("Failed to collect {} -> {}", built.display(), dst.display())
            })?;
        }
        firmwares.push(dst);
    }

    // fs::copy onto the same path truncates the file.
    let bootloader_out = out.join(DEFAULT_BOOTLOADER_FILE);
    if bootloader != bootloader_out {
        fs::copy(&bootloader, &bootloader_out).with_context(|| {
            format!(
                "Failed to copy {} -> {}",
                bootloader.display(),
                bootloader_out.display()
            )
        })?;
    }

    // The nRF is a peer leaf of the same model tree.
    let nrf = stage_nrf_image(args, &out)?;
    let config = args.model.config()?;
    let floors = release_floors()?;

    run_signer(
        &out,
        &firmwares,
        nrf.as_deref(),
        config.nrf_pq_native,
        sign,
        sigmask,
        &floors,
    )?;
    match dest {
        // Signed in place; pack the archive `upload` installs.
        Dest::Artifacts => {
            pack_bundle_archive(args.model)?;
        }
        // A release publishes only once its signatures are attached.
        Dest::Release => {}
    }

    println!(
        "{}",
        format!("xtask: bundle ready in {}", out.display()).green()
    );
    Ok(())
}

/// Build a CUSTOM firmware and fold it into the prebuilt, already-signed
/// root. A custom leaf is code-independent, so it belongs in the one
/// founder-signed custom slot; nothing here is signed.
pub fn build_presigned(args: &ResolvedBuildArgs) -> Result<()> {
    let models_dir = helpers::workspace_dir()?.join("models");
    let release_manifest = release::prebuilt_release_manifest(args.bootloader_devel)?;
    ensure!(
        release_manifest.exists(),
        "a custom build folds into the prebuilt release, but {} does not exist \
         -- cut and promote one first:\n             \
         xtask release {}--promote",
        release_manifest.display(),
        if args.bootloader_devel {
            "--bootloader-devel "
        } else {
            ""
        },
    );

    let model_id = args.model.model_id();
    let body = release::read_model_entry(&release_manifest, model_id)?;

    // Assembled in artifacts/ like every other build; nothing is signed.
    let out = helpers::artifacts_dir(args.model)?;
    fs::create_dir_all(&out)?;

    println!(
        "{}",
        format!(
            "xtask: presigned custom build for {model_id} -- folding into the prebuilt release"
        )
        .bold()
        .dimmed()
    );

    let mut variant_args = args.clone();
    Variant::Custom.apply(&mut variant_args);
    // The custom slot commits to the secmon the release was signed over.
    variant_args.prebuilt_secmon = true;
    cargo::build_project(variant_args)?;

    let firmware = out.join(Variant::Custom.artifact());

    // The promoted bootloader already carries the root this image folds to.
    let bootloader = models_dir.join(model_id).join("bootloaders").join(format!(
        "bootloader_{model_id}{}.bin",
        if args.bootloader_devel { "_devel" } else { "" }
    ));
    fs::copy(&bootloader, out.join(DEFAULT_BOOTLOADER_FILE))
        .with_context(|| format!("Failed to copy {}", bootloader.display()))?;

    copy_signed_coprocessors(model_id, &body, &out)?;
    presign(&firmware, &release_manifest, model_id)?;

    // Derived from the prebuilt release's body, trimmed to the one variant present.
    publish_manifest(
        args.model,
        body,
        &out,
        &[(Variant::Custom, Variant::Custom.artifact())],
    )?;
    pack_bundle_archive(args.model)?;
    // Publish like a signed bundle does, so `flash` and `upload` agree.
    publish_bootloader(args.model, &out)?;
    publish_images(
        args.model,
        &out,
        &[Variant::Custom],
        &BundleManifest::load(&out)?,
    )?;

    println!(
        "{}",
        format!(
            "xtask: presigned custom firmware ready in {}",
            out.display()
        )
        .green()
    );
    Ok(())
}

/// Copy each co-processor image the prebuilt release's body names into the
/// bundle dir. The promoted (signed) image, not the bare one: the body records
/// its hash. Absent is an error, not a skip.
fn copy_signed_coprocessors(model_id: &str, body: &serde_json::Value, out: &Path) -> Result<()> {
    for entry in body
        .get("coprocessors")
        .and_then(|v| v.as_array())
        .cloned()
        .unwrap_or_default()
    {
        let Some(name) = entry.get("file").and_then(|v| v.as_str()) else {
            continue;
        };
        let src = helpers::workspace_dir()?
            .join("models")
            .join(model_id)
            .join(name);
        ensure!(
            src.exists(),
            "the prebuilt release lists co-processor image {name}, but {} is not \
             there -- promote a release for {model_id} first:\n             \
             xtask release --promote",
            src.display(),
        );
        fs::copy(&src, out.join(name))
            .with_context(|| format!("Failed to copy {}", src.display()))?;
        println!("xtask: co-processor {name} taken from the promoted set");
    }
    Ok(())
}

/// Fill the manifest, check the leaf against the prebuilt release's custom slot
/// and bake the co-path. Keyless.
fn presign(firmware: &Path, release_manifest: &Path, model_id: &str) -> Result<()> {
    let tool = helpers::workspace_dir()?
        .join("../tools/trezor_core_tools/firmware_pq_presign.py")
        .canonicalize()
        .context("Failed to locate firmware_pq_presign.py")?;

    let status = process::Command::new("python3")
        .arg(&tool)
        .args(["--firmware".as_ref(), firmware.as_os_str()])
        .args(["--release".as_ref(), release_manifest.as_os_str()])
        .args(["--model", model_id])
        .status()
        .context("Failed to spawn firmware_pq_presign.py")?;
    ensure!(
        status.success(),
        "firmware_pq_presign.py failed: {status} -- this image does not fold into \
         the prebuilt release's custom slot"
    );
    Ok(())
}

/// Publish a signed bundle's firmware images over the canonical build
/// artifacts. Never called for an unsigned bundle.
pub(crate) fn publish_images(
    model: Model,
    out: &Path,
    variants: &[Variant],
    bundle: &BundleManifest,
) -> Result<()> {
    // Variants sharing a slot: the first in ALL_VARIANTS order (universal)
    // wins.
    let mut taken: Vec<&str> = Vec::new();
    let mut published: Vec<(Variant, &str)> = Vec::new();
    for variant in variants {
        let slot = variant.artifact();
        if taken.contains(&slot) {
            continue;
        }
        taken.push(slot);
        let src = out.join(bundle.firmware_file(*variant)?);
        let dst = helpers::artifacts_dir(model)?.join(slot);
        // fs::copy onto the same path truncates the file.
        if src != dst {
            fs::copy(&src, &dst).with_context(|| {
                format!("Failed to publish {} -> {}", src.display(), dst.display())
            })?;
            println!("xtask: {} published to {}", variant.name(), dst.display());
        }
        published.push((*variant, slot));
    }
    let src = out.join("bundle.json");
    let text =
        fs::read_to_string(&src).with_context(|| format!("Failed to read {}", src.display()))?;
    let doc: serde_json::Value = serde_json::from_str(&text)
        .with_context(|| format!("{} is not valid JSON", src.display()))?;
    publish_manifest(model, doc, out, &published)
}

/// Publish the bundle manifest rewritten to what was published: variants
/// filtered to those present, filenames rewritten to their slot names.
/// `coprocessors` is kept and their images published alongside.
fn publish_manifest(
    model: Model,
    mut doc: serde_json::Value,
    coproc_src: &Path,
    published: &[(Variant, &str)],
) -> Result<()> {
    let keep: Vec<serde_json::Value> = doc
        .get("variants")
        .and_then(|v| v.as_array())
        .context("bundle has no variants")?
        .iter()
        .filter_map(|entry| {
            let name = entry.get("variant").and_then(|v| v.as_str())?;
            let slot = published
                .iter()
                .find(|(v, _)| v.name() == name)
                .map(|(_, slot)| *slot)?;
            let mut entry = entry.clone();
            entry["file"] = serde_json::Value::String(slot.to_string());
            Some(entry)
        })
        .collect();

    doc["variants"] = serde_json::Value::Array(keep);

    // The co-processor images travel with the manifest that names them.
    for entry in doc
        .get("coprocessors")
        .and_then(|v| v.as_array())
        .cloned()
        .unwrap_or_default()
    {
        let Some(name) = entry.get("file").and_then(|v| v.as_str()) else {
            continue;
        };
        let src = coproc_src.join(name);
        let dst = helpers::artifacts_dir(model)?.join(name);
        // Already in place when the build assembled there.
        if src != dst {
            fs::copy(&src, &dst).with_context(|| {
                format!("Failed to publish {} -> {}", src.display(), dst.display())
            })?;
            println!("xtask: {name} published to {}", dst.display());
        }
    }

    let dst = helpers::artifacts_dir(model)?.join("bundle.json");
    fs::write(&dst, serde_json::to_string_pretty(&doc)? + "\n")
        .with_context(|| format!("Failed to write {}", dst.display()))?;
    Ok(())
}

/// Pack the published bundle into its archive, `bundle.zip`: the file `xtask
/// upload` hands to trezorctl.
pub fn pack_bundle_archive(model: Model) -> Result<PathBuf> {
    let tool = helpers::workspace_dir()?
        .join("../tools/trezor_core_tools/release_pack.py")
        .canonicalize()
        .context("Failed to locate release_pack.py")?;
    let dir = helpers::artifacts_dir(model)?;
    let out = dir.join("bundle.zip");
    let status = process::Command::new("python3")
        .arg(&tool)
        .args(["--bundle".as_ref(), dir.as_os_str()])
        .args(["--out".as_ref(), out.as_os_str()])
        .status()
        .context("Failed to spawn release_pack.py")?;
    ensure!(status.success(), "release_pack.py failed: {status}");
    Ok(out)
}

/// Invalidate the published bundle after a bare bootloader build: the
/// firmware beside it folds to the old root, so removing `bundle.json` says
/// they are no longer a signed bundle, and `bundle.zip` (packed from it) goes
/// with it.
pub fn invalidate_bundle(model: Model) -> Result<()> {
    let dir = helpers::artifacts_dir(model)?;
    for name in ["bundle.json", "bundle.zip"] {
        let path = dir.join(name);
        if path.exists() {
            fs::remove_file(&path)
                .with_context(|| format!("Failed to remove {}", path.display()))?;
            println!(
                "xtask: {} removed -- a bare bootloader does not vouch for the \
                 firmware beside it",
                path.display()
            );
        }
    }
    Ok(())
}

pub(crate) fn publish_bootloader(model: Model, out: &Path) -> Result<()> {
    let dst = helpers::artifacts_dir(model)?.join("bootloader.bin");
    let src = out.join(DEFAULT_BOOTLOADER_FILE);
    // See publish_images: copying onto the same path truncates it.
    if src == dst {
        return Ok(());
    }
    fs::create_dir_all(dst.parent().context("artifacts dir has no parent")?)?;
    fs::copy(&src, &dst)
        .with_context(|| format!("Failed to publish {} -> {}", src.display(), dst.display()))?;
    println!("xtask: bootloader published to {}", dst.display());
    Ok(())
}

/// The bootloader whose header this bundle folds `firmware_root` into.
/// Never built here.
fn select_bootloader(args: &ResolvedBuildArgs, source: BootloaderSource) -> Result<PathBuf> {
    let fresh = helpers::artifacts_dir(args.model)?.join("bootloader.bin");

    let chosen = match source {
        BootloaderSource::Fresh => {
            ensure!(
                fresh.exists(),
                "no fresh bootloader at {} -- it is not built implicitly:\n             \
                 xtask build bootloader -m {} --bootloader-devel",
                fresh.display(),
                args.model.model_id()
            );
            fresh
        }
        BootloaderSource::Prebuilt => prebuilt_bootloader(args)?,
        BootloaderSource::Auto => {
            if fresh.exists() {
                fresh
            } else {
                prebuilt_bootloader(args)?
            }
        }
    };

    // The age only means something for a file xtask wrote itself.
    let (which, age) = if chosen.starts_with(helpers::artifacts_dir(args.model)?) {
        ("fresh", file_age(&chosen))
    } else {
        ("prebuilt", String::new())
    };
    println!(
        "xtask: folding the {which} bootloader {}{age} (its header is re-signed, its code is not rebuilt)",
        chosen.display(),
    );

    check_bootloader_pool(&chosen, args.bootloader_devel)?;
    Ok(chosen)
}

/// Fail closed unless the bootloader's compiled-in founder pool matches the
/// keys this bundle is signed with. Signing rewrites the header and cannot
/// touch the pool, so nothing downstream can catch a mismatch.
fn check_bootloader_pool(bootloader: &Path, devel_build: bool) -> Result<()> {
    let script =
        helpers::workspace_dir()?.join("../tools/trezor_core_tools/bootloader_provenance.py");
    let out = process::Command::new("python3")
        .arg(&script)
        .arg(bootloader)
        .output()
        .context("failed to run bootloader_provenance.py")?;
    ensure!(
        out.status.success(),
        "bootloader_provenance.py failed: {}",
        String::from_utf8_lossy(&out.stderr).trim()
    );
    let stdout = String::from_utf8_lossy(&out.stdout);
    let field = |k: &str| {
        stdout
            .lines()
            .find_map(|l| l.strip_prefix(k))
            .map(str::to_string)
    };
    let pool = field("pool=").context("bootloader_provenance.py printed no pool")?;
    let digest = field("code_sha256=").context("bootloader_provenance.py printed no digest")?;

    println!("xtask: bootloader founder pool `{pool}`, code sha256 {digest}");

    // A production release must positively carry the production pool
    // (`unknown` has no pool linked at all); a devel cut must merely not.
    if devel_build {
        ensure!(
            pool != "production",
            "this bootloader trusts the production founder pool, but the \
             bundle is being signed with development keys.\n             \
             Rebuild it -- xtask build bootloader --bootloader-devel -- or \
             pick the other source with --bootloader."
        );
    } else {
        ensure!(
            pool == "production",
            "this bootloader's founder pool is `{pool}`, not `production`, but \
             the bundle is being signed with production keys.\n             \
             The pool is compiled in, so signing cannot correct it and the \
             ceremony cannot see it -- the device would verify OTA boot \
             headers against the wrong keys, or (for `unknown`) against none \
             at all.\n             \
             Rebuild it -- xtask build bootloader -- or pick the other source \
             with --bootloader."
        );
    }
    Ok(())
}

/// ` (built N minutes ago)`, or nothing if the age cannot be read.
fn file_age(path: &Path) -> String {
    let Ok(elapsed) = fs::metadata(path)
        .and_then(|m| m.modified())
        .map(|t| t.elapsed())
    else {
        return String::new();
    };
    let Ok(elapsed) = elapsed else {
        return String::new();
    };
    let mins = elapsed.as_secs() / 60;
    match mins {
        0 => " (built just now)".to_string(),
        1 => " (built 1 minute ago)".to_string(),
        m if m < 90 => format!(" (built {m} minutes ago)"),
        m if m < 60 * 48 => format!(" (built {} hours ago)", m / 60),
        m => format!(" (built {} days ago)", m / (60 * 24)),
    }
}

/// The prebuilt bootloader whose header this bundle folds into. It must
/// have been built with the same key selection as this firmware.
fn prebuilt_bootloader(args: &ResolvedBuildArgs) -> Result<PathBuf> {
    let model_id = args.model.model_id();
    let suffix = if args.bootloader_devel { "_devel" } else { "" };
    let path = helpers::workspace_dir()?
        .join("models")
        .join(model_id)
        .join("bootloaders")
        .join(format!("bootloader_{model_id}{suffix}.bin"));

    ensure!(
        path.exists(),
        "no prebuilt bootloader at {} -- a tree bundle folds its firmware_root \
         into a bootloader header, so one has to exist to sign against",
        path.display()
    );
    Ok(path)
}

/// The boot header's release version and floors, in release numbers (the header
/// version is the universal firmware_version, stamped by the signer). Both sit
/// next to that version in projects/firmware/version.h; FIX_VERSION is the same
/// storage-format floor the legacy image header carries.
struct ReleaseFloors {
    /// The firmware VERSION; the release version when no universal or
    /// bitcoin-only image carries it (a prodtest-only build).
    release_version: String,
    fix_version: String,
    min_prev_version: String,
}

fn release_floors() -> Result<ReleaseFloors> {
    let version_h = helpers::workspace_dir()?.join("projects/firmware/version.h");
    let read = |prefix| -> Result<String> {
        Ok(helpers::parse_version_defines(&version_h, prefix)?.join("."))
    };
    Ok(ReleaseFloors {
        release_version: read("VERSION")?,
        fix_version: read("FIX_VERSION")?,
        min_prev_version: read("MIN_PREV_VERSION")?,
    })
}

/// Fold `firmware_root` over the built variants into the bootloader header,
/// re-sign it, and bake each variant's co-path into its image. The crypto
/// stays in Python (`firmware_pq_sign.py`), as with `headertool`.
fn run_signer(
    out: &Path,
    firmwares: &[PathBuf],
    nrf: Option<&Path>,
    nrf_pq_native: bool,
    stage: SignStage,
    sigmask: Option<u8>,
    floors: &ReleaseFloors,
) -> Result<()> {
    let signer = helpers::workspace_dir()?
        .join("../tools/trezor_core_tools/firmware_pq_sign.py")
        .canonicalize()
        .context("Failed to locate firmware_pq_sign.py")?;

    // The assembled paths: each image keeps its build name.
    let mut cmd = process::Command::new("python3");
    cmd.arg(&signer);
    for firmware in firmwares {
        cmd.args(["--firmware".as_ref(), firmware.as_os_str()]);
    }
    cmd.args([
        "--bootloader".as_ref(),
        out.join(DEFAULT_BOOTLOADER_FILE).as_os_str(),
    ]);
    cmd.args([
        "--manifest-out".as_ref(),
        out.join("bundle.json").as_os_str(),
    ]);
    cmd.args(["--release-version", &floors.release_version]);
    cmd.args(["--fix-version", &floors.fix_version]);
    cmd.args(["--min-prev-version", &floors.min_prev_version]);
    // `sigmask` is authenticated, so it is fixed at prepare time.
    if let Some(mask) = sigmask {
        cmd.args(["--sigmask", &format!("0x{mask:02x}")]);
    }
    // No archive here: `release_pack.py` packs once everything is finished.
    if stage == SignStage::PrepareOnly {
        cmd.arg("--unsigned");
    }

    if let Some(nrf) = nrf {
        cmd.args(["--nrf".as_ref(), nrf.as_os_str()]);
        if nrf_pq_native {
            cmd.arg("--nrf-pq-native");
        }
    }

    let what = match stage {
        SignStage::Inline => "signing the bundle",
        SignStage::PrepareOnly => "preparing the bundle (unsigned)",
    };
    println!("{}", format!("xtask: {what}").bold().dimmed());
    let status = cmd
        .status()
        .context("Failed to spawn firmware_pq_sign.py")?;
    ensure!(status.success(), "firmware_pq_sign.py failed: {status}");
    Ok(())
}

/// Copy the model's prebuilt nRF image into the bundle, padded to the
/// 16-byte flash write block the OTA upload engine needs. The padding is
/// outside the signed region, so the fold does not depend on it.
fn stage_nrf_image(args: &ResolvedBuildArgs, out: &Path) -> Result<Option<PathBuf>> {
    let suffix = if args.bootloader_devel { "-dev" } else { "" };
    // The `-bare` build output is the bundle input; the signer's output is
    // committed under the signed name and would be refused as input.
    let prebuilt = helpers::workspace_dir()?
        .join("models")
        .join(args.model.model_id())
        .join(format!("trezor-ble{suffix}-bare.bin"));

    if !prebuilt.exists() {
        // A board with an nRF must commit its slot; without one the bundle
        // signs an empty model path.
        let model_config = args.model.config()?;
        let board_id = args
            .board
            .clone()
            .unwrap_or_else(|| model_config.default_board.clone());
        let board = BoardConfig::load(&model_config.model_id, &board_id)?;
        ensure!(
            !board.peripherals.iter().any(|p| p.name == "nrf"),
            "no nRF image at {} -- board {board_id} of {} has an nRF co-processor, so \
             the bundle must commit its slot. Build the nordic project and commit \
             the bare image, or pass a board without one",
            prebuilt.display(),
            args.model.model_id()
        );
        return Ok(None);
    }

    warn_if_nrf_stale(&prebuilt)?;

    let raw =
        fs::read(&prebuilt).with_context(|| format!("Failed to read {}", prebuilt.display()))?;
    // Staged under the signed name, the one the bundle records.
    let padded = out.join(format!("trezor-ble{suffix}.bin"));
    let mut bytes = raw;
    bytes.resize(bytes.len().next_multiple_of(16), 0);
    fs::write(&padded, &bytes).with_context(|| format!("Failed to write {}", padded.display()))?;

    println!(
        "xtask: nRF image {} staged as a model-tree leaf",
        prebuilt.display()
    );
    Ok(Some(padded))
}

/// Warn when a fresher nRF build sits unstaged in nordic/; building the nRF
/// does not update the prebuilt image.
fn warn_if_nrf_stale(prebuilt: &Path) -> Result<()> {
    let fresh = helpers::workspace_dir()?
        .join("../../nordic/trezor/build/trezor-ble/zephyr/zephyr.trz.bin");
    let (Ok(b), Ok(c)) = (fs::metadata(&fresh), fs::metadata(prebuilt)) else {
        return Ok(());
    };
    let (Ok(bt), Ok(ct)) = (b.modified(), c.modified()) else {
        return Ok(());
    };
    if bt <= ct {
        return Ok(());
    }
    println!(
        "{}",
        format!(
            "WARNING: a newer nRF build exists but was never staged:\n                 fresh   {}\n    signing {}\n  The tree leaf and the embedded coreapp \
             image will both be the OLDER one. Re-run the nRF build with -d -s \
             (build_sign_flash.sh) to stage it.",
            fresh.display(),
            prebuilt.display()
        )
        .yellow()
    );
    Ok(())
}
