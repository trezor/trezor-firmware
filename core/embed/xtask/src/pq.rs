//! Building a pq_secure (Merkle-tree) firmware release.
//!
//! A tree firmware image is only installable next to a bootloader whose signed
//! header commits to its `firmware_root`, so `xtask build firmware` on a tree
//! model produces a release rather than one binary. Re-signing rewrites only
//! the boot header, never the bootloader code. See docs/core/build/xtask.md.

use std::path::{Path, PathBuf};
use std::{fs, process};

use anyhow::{Context, Result, bail, ensure};
use clap::ValueEnum;
use owo_colors::OwoColorize;

use crate::args::{BuildArgs, Project, ReleaseArgs};
use crate::model::Model;
use crate::options::ResolvedBuildArgs;
use crate::{cargo, helpers};

/// One variant of a release: one leaf of the founder firmware tree.
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

/// Which bootloader binary a release folds its `firmware_root` into.
///
/// Must have been built with the same key selection the release is signed
/// with (`--bootloader-devel`); signing rewrites the header, not the code.
#[derive(ValueEnum, Clone, Copy, PartialEq, Eq, Debug, Default)]
#[value(rename_all = "kebab-case")]
pub enum BootloaderSource {
    /// The last built bootloader for this model, else the committed binary.
    #[default]
    Auto,
    /// `build/artifacts/<MODEL>/bootloader.bin`; an error if absent.
    Built,
    /// The committed binary in `models/<MODEL>/bootloaders/` -- what a
    /// production release folds.
    Committed,
}

/// Every variant of a full release; the founder tree must contain them all.
pub const ALL_VARIANTS: [Variant; 4] = [
    Variant::Universal,
    Variant::BtcOnly,
    Variant::Custom,
    Variant::Prodtest,
];

impl Variant {
    /// Name in the release directory and in bundle.json.
    pub fn name(self) -> &'static str {
        match self {
            Variant::Universal => "universal",
            Variant::BtcOnly => "btc-only",
            Variant::Custom => "custom",
            Variant::Prodtest => "prodtest",
        }
    }

    /// The variant a release directory names, as recorded in bundle.json.
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

/// Where a model's release is assembled: `build-xtask/tree/<MODEL>/`, with the
/// portable zip alongside it as `<MODEL>.zip`.
pub fn release_dir(model: Model) -> Result<PathBuf> {
    // Normalised: cargo reports the target dir as `core/embed/../build-xtask`.
    let build_dir = helpers::build_dir()?;
    let build_dir = build_dir.canonicalize().unwrap_or(build_dir);
    Ok(build_dir.join("tree").join(model.model_id()))
}

/// Release container magic and layout version; must match the signer
/// (`firmware_pq_sign.py`), which states its own copy.
const CONTAINER_MAGIC: &str = "TRZL";
const CONTAINER_VERSION: u64 = 1;

/// The bootloader's filename inside a release, as the writer names it.
const DEFAULT_BOOTLOADER_FILE: &str = "bootloader.bin";

/// Where a build assembles what it signs. A plain build signs in place;
/// `tree/` belongs to `xtask release` alone.
#[derive(Clone, Copy, PartialEq, Eq)]
pub enum Dest {
    /// `build/artifacts/<MODEL>/` -- the canonical install set.
    Artifacts,
    /// `build/tree/<MODEL>/` -- a release being cut.
    Release,
}

/// Whether a release is signed as it is built, or prepared for a later
/// ceremony (prepare / sign / attach, see docs/core/build/xtask.md).
#[derive(Clone, Copy, PartialEq, Eq)]
pub enum SignStage {
    /// Fold and sign in one step, with development keys.
    Inline,
    /// Fold only; leave the signature region zero for a later `attach`.
    PrepareOnly,
}

/// One variant of a release, as the container records it.
struct VariantEntry {
    variant: Variant,
    firmware_type: u32,
    file: String,
}

/// What a signed release records about itself, from its `bundle.json`.
/// Routing only -- the boot-header signature is the trust root.
pub struct ReleaseManifest {
    /// Model id, from the signer's reading of the signed boot header.
    model: String,
    /// The bootloader image's name within the release.
    bootloader_file: String,
    /// Every variant: hardened `firmware_type` codeword and recorded filename.
    variants: Vec<VariantEntry>,
    /// Where `firmware_type` sits in the bootloader image, probed by the
    /// signer.
    firmware_type_offset: usize,
    firmware_type_len: usize,
    /// The value a bare release carries.
    firmware_type_bare: u32,
}

impl ReleaseManifest {
    pub fn load(dir: &Path) -> Result<ReleaseManifest> {
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
                    "{} has no `format` -- it predates the versioned release \
                     container, rebuild it",
                    path.display()
                )
            })?;
        ensure!(
            format == CONTAINER_MAGIC,
            "{} is not a release container: format `{format}`, expected `{CONTAINER_MAGIC}`",
            path.display(),
        );
        let version = json
            .get("format_version")
            .and_then(|v| v.as_u64())
            .with_context(|| format!("{} has no `format_version`", path.display()))?;
        ensure!(
            version == CONTAINER_VERSION,
            "{} is release container v{version}, but this xtask speaks \
             v{CONTAINER_VERSION} -- rebuild the release (or update xtask)",
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
            .context("release bundle records no firmware_type offset")?;
        let len = ft
            .get("len")
            .and_then(|v| v.as_u64())
            .context("release bundle records no firmware_type len")?;
        let bare = ft
            .get("bare")
            .and_then(|v| v.as_u64())
            .context("release bundle records no bare firmware_type")?;

        let mut variants = Vec::new();
        for entry in json
            .get("variants")
            .and_then(|v| v.as_array())
            .context("release bundle has no variants")?
        {
            let name = entry
                .get("variant")
                .and_then(|v| v.as_str())
                .context("a release variant records no variant name")?;
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

        Ok(ReleaseManifest {
            model,
            bootloader_file,
            variants,
            firmware_type_offset: usize::try_from(offset)?,
            firmware_type_len: usize::try_from(len)?,
            firmware_type_bare: u32::try_from(bare)?,
        })
    }

    /// The model this release is for, as the signed boot header spells it.
    pub fn model(&self) -> &str {
        &self.model
    }

    pub fn variants(&self) -> impl Iterator<Item = Variant> + '_ {
        self.variants.iter().map(|e| e.variant)
    }

    /// The image filename this release recorded for `variant`.
    fn firmware_file(&self, variant: Variant) -> Result<&str> {
        self.variants
            .iter()
            .find(|e| e.variant == variant)
            .map(|e| e.file.as_str())
            .with_context(|| {
                format!(
                    "`{}` is not in this release ({})",
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
                    "`{}` is not in this release ({})",
                    variant.name(),
                    self.names()
                )
            })
    }

    /// Write a copy of the release bootloader stamped for `variant`.
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
        // A release is signed bare; anything else means a stale bundle.json.
        ensure!(
            current == bare,
            "{path} already carries firmware_type 0x{current:08X} at offset {at}, \
             but a release is signed bare (0x{bare:08X}) -- bundle.json does not \
             match this bootloader",
        );
        image[at..at + len].copy_from_slice(&firmware_type.to_le_bytes());

        let out = dir.join(format!("bootloader-{}.bin", variant.name()));
        fs::write(&out, &image).with_context(|| format!("Failed to write {}", out.display()))?;
        Ok(out)
    }
}

/// The images a pq_secure release contributes to one install. Bootloader and
/// firmware are a pair: the header vouches only for the root this firmware
/// folds to.
pub struct ReleaseInstall {
    /// The release bootloader, provisioned for `variant` when there is one.
    pub bootloader: PathBuf,
    /// The firmware image, absent when only the bootloader was asked for.
    pub firmware: Option<PathBuf>,
    /// The variant this install provisions the device for, `None` for a bare
    /// bootloader.
    pub variant: Option<Variant>,
}

/// Resolve what to install from a model's release, stamping `firmware_type`
/// into the bootloader for the variant being installed.
pub fn resolve_install(
    model: Model,
    project: Project,
    variant: Option<Variant>,
) -> Result<ReleaseInstall> {
    let model_id = model.model_id();

    // A bare bootloader needs no release; bare is the state of a fresh device.
    if project == Project::Bootloader && variant.is_none() {
        // Whatever last wrote `artifacts/<MODEL>/bootloader.bin` is canonical.
        let bootloader = helpers::artifacts_dir(model)?.join("bootloader.bin");
        ensure!(
            bootloader.exists(),
            "no bootloader for {model_id} -- build one first:\n             \
             xtask build bootloader -m {model_id} --bootloader-devel",
        );
        return Ok(ReleaseInstall {
            bootloader,
            firmware: None,
            variant: None,
        });
    }

    // No signing here: `bundle.json` marks the published binaries as a signed
    // set, and `xtask build bootloader` removes it.
    let dir = helpers::artifacts_dir(model)?;
    ensure!(
        dir.join("bundle.json").exists(),
        "no installable release in {dir} -- those binaries are not a signed set \
         (a bare `build bootloader` invalidates it). Build or cut one:\n             \
         xtask build firmware -m {model_id} --bootloader-devel",
        dir = dir.display(),
    );
    let release = ReleaseManifest::load(&dir)?;

    if project == Project::Bootloader {
        let variant = variant.expect("bare bootloader handled above");
        return Ok(ReleaseInstall {
            bootloader: release.stamp(&dir, variant)?,
            firmware: None,
            variant: Some(variant),
        });
    }

    let variant = pick_variant(project, variant, &release)?;
    Ok(ReleaseInstall {
        bootloader: release.stamp(&dir, variant)?,
        firmware: Some(dir.join(release.firmware_file(variant)?)),
        variant: Some(variant),
    })
}

/// Which variant of a release to install: an explicit choice wins, then the
/// project, then the release's only firmware variant.
pub fn pick_variant(
    project: Project,
    requested: Option<Variant>,
    release: &ReleaseManifest,
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

    let mut candidates = release.variants().filter(|v| v.project() == project);
    let first = candidates.next().with_context(|| {
        format!(
            "this release holds no `{}` variant (it has {})",
            project.binary_name(),
            release.names()
        )
    })?;
    ensure!(
        candidates.next().is_none(),
        "this release holds several firmware variants ({}), so --variant has to \
         say which one to install",
        release.names()
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

/// Whether this build produces a Merkle-tree release (never for the emulator).
pub fn applies(args: &ResolvedBuildArgs) -> Result<bool> {
    Ok(!args.emulator && args.model.config()?.has_feature("pq_secure_boot"))
}

/// Build, sign and bundle a release with development keys.
pub fn build_release(
    args: &ResolvedBuildArgs,
    variants: &[Variant],
    bootloader: BootloaderSource,
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
        Dest::Release => release_dir(args.model)?,
    };
    fs::create_dir_all(&out).with_context(|| format!("Failed to create {}", out.display()))?;

    println!(
        "xtask: pq_secure release for {} -- variants: {}",
        args.model.model_id(),
        variants
            .iter()
            .map(|v| v.name())
            .collect::<Vec<_>>()
            .join(", ")
    );

    // Resolved first: a missing bootloader should not cost four builds.
    let bootloader = release_bootloader(args, bootloader)?;

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

        // Keep universal's secmon beside the release: the custom slot's leaf
        // commits to the whole secmon entry, so promotion needs these bytes.
        if *variant == Variant::Universal && dest == Dest::Release {
            for name in ["secmon.bin", "secmon_api.o"] {
                let src = helpers::artifacts_dir(args.model)?.join(name);
                ensure!(
                    src.exists(),
                    "{} is missing -- the custom slot commits to the secmon, so \
                     the release has to keep the one it signed over",
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
    let nrf_pq_native = args.model.config()?.nrf_pq_native;

    run_signer(
        &out,
        &firmwares,
        nrf.as_deref(),
        nrf_pq_native,
        sign,
        sigmask,
    )?;
    match dest {
        // Signed in place; pack the container `upload` installs.
        Dest::Artifacts => {
            pack_install_zip(args.model)?;
        }
        // A release publishes only once its signatures are attached.
        Dest::Release => {}
    }

    println!(
        "{}",
        format!("xtask: release ready in {}", out.display()).green()
    );
    Ok(())
}

/// Build a CUSTOM firmware and fold it into the committed, already-signed
/// root. A custom leaf is code-independent, so it belongs in the one
/// founder-signed custom slot; nothing here is signed.
pub fn build_presigned(args: &ResolvedBuildArgs) -> Result<()> {
    let models_dir = helpers::workspace_dir()?.join("models");
    let bundle_src = models_dir.join(bundle_name(args.bootloader_devel));
    ensure!(
        bundle_src.exists(),
        "a custom build folds into the committed release, but {} does not exist \
         -- cut and promote one first:\n             \
         xtask release {}--promote",
        bundle_src.display(),
        if args.bootloader_devel {
            "--bootloader-devel "
        } else {
            ""
        },
    );

    let model_id = args.model.model_id();
    let body = read_model_entry(&bundle_src, model_id)?;

    // Assembled in artifacts/ like every other build; nothing is signed.
    let out = helpers::artifacts_dir(args.model)?;
    fs::create_dir_all(&out)?;

    println!(
        "{}",
        format!(
            "xtask: presigned custom build for {model_id} -- folding into the committed release"
        )
        .bold()
        .dimmed()
    );

    let mut variant_args = args.clone();
    Variant::Custom.apply(&mut variant_args);
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
    presign(&firmware, &bundle_src, model_id)?;

    // Derived from the committed body, trimmed to the one variant present.
    publish_manifest(
        args.model,
        body,
        &out,
        &[(Variant::Custom, Variant::Custom.artifact())],
    )?;
    pack_install_zip(args.model)?;
    // Publish like a signed release does, so `flash` and `upload` agree.
    publish_bootloader(args.model, &out)?;
    publish_images(
        args.model,
        &out,
        &[Variant::Custom],
        &ReleaseManifest::load(&out)?,
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

/// Copy each co-processor image the committed body names into the release
/// dir. The promoted (signed) image, not the bare one: the body records its
/// hash. Absent is an error, not a skip.
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
            "the committed bundle lists co-processor image {name}, but {} is not \
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

/// One model's entry from a cross-model bundle.
fn read_model_entry(bundle: &Path, model_id: &str) -> Result<serde_json::Value> {
    let raw = fs::read_to_string(bundle)
        .with_context(|| format!("Failed to read {}", bundle.display()))?;
    let doc: serde_json::Value = serde_json::from_str(&raw)
        .with_context(|| format!("{} is not valid JSON", bundle.display()))?;
    let expected = format!("{CONTAINER_MAGIC}-set");
    let format = doc
        .get("format")
        .and_then(|v| v.as_str())
        .with_context(|| {
            format!(
                "{} has no `format` -- it predates the versioned release container, \
                 re-promote it",
                bundle.display()
            )
        })?;
    ensure!(
        format == expected,
        "{} is not a cross-model release set: format `{format}`, expected `{expected}`",
        bundle.display(),
    );
    let version = doc
        .get("format_version")
        .and_then(|v| v.as_u64())
        .with_context(|| format!("{} has no `format_version`", bundle.display()))?;
    ensure!(
        version == CONTAINER_VERSION,
        "{} is release set v{version}, but this xtask speaks v{CONTAINER_VERSION} \
         -- re-promote it (or update xtask)",
        bundle.display(),
    );
    doc.get("models")
        .and_then(|m| m.get(model_id))
        .cloned()
        .with_context(|| {
            format!(
                "{} has no entry for {model_id} -- promote a release for it first",
                bundle.display()
            )
        })
}

/// Fill the manifest, check the leaf against the committed custom slot and
/// bake the co-path. Keyless.
fn presign(firmware: &Path, bundle: &Path, model_id: &str) -> Result<()> {
    let tool = helpers::workspace_dir()?
        .join("../tools/trezor_core_tools/firmware_pq_presign.py")
        .canonicalize()
        .context("Failed to locate firmware_pq_presign.py")?;

    let status = process::Command::new("python3")
        .arg(&tool)
        .args(["--firmware".as_ref(), firmware.as_os_str()])
        .args(["--bundle".as_ref(), bundle.as_os_str()])
        .args(["--model", model_id])
        .status()
        .context("Failed to spawn firmware_pq_presign.py")?;
    ensure!(
        status.success(),
        "firmware_pq_presign.py failed: {status} -- this image does not fold into \
         the committed custom slot"
    );
    Ok(())
}

/// The cross-model bundle `tree/bundle[_devel].json`, which promotion commits.
fn tree_bundle(model_devel: bool) -> Result<PathBuf> {
    Ok(helpers::build_dir()?
        .join("tree")
        .join(bundle_name(model_devel)))
}

/// `bundle.json` for production keys, `bundle_devel.json` for development.
fn bundle_name(devel: bool) -> String {
    let suffix = if devel { "_devel" } else { "" };
    format!("bundle{suffix}.json")
}

/// Pack every released model into one model-free publishable container. The
/// packer (`release_pack.py`) names it `release[-devel].zip` from the
/// signatures it finds, since xtask cannot verify them.
fn write_release_container(set_path: &Path, devel_build: bool) -> Result<()> {
    let packer = helpers::workspace_dir()?
        .join("../tools/trezor_core_tools/release_pack.py")
        .canonicalize()
        .context("Failed to locate release_pack.py")?;
    let tree = helpers::build_dir()?.join("tree");
    let tree = tree.canonicalize().unwrap_or(tree);
    let status = process::Command::new("python3")
        .arg(&packer)
        .args(["--set".as_ref(), set_path.as_os_str()])
        .args(["--tree".as_ref(), tree.as_os_str()])
        .args(["--out-dir".as_ref(), tree.as_os_str()])
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

/// Publish a signed release's firmware images over the canonical build
/// artifacts. Never called for an unsigned release.
fn publish_images(
    model: Model,
    out: &Path,
    variants: &[Variant],
    release: &ReleaseManifest,
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
        let src = out.join(release.firmware_file(*variant)?);
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

/// Publish the release manifest rewritten to what was published: variants
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
        .context("release bundle has no variants")?
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

/// Pack the published set into `install.zip`, the file `xtask upload` hands
/// to trezorctl.
pub fn pack_install_zip(model: Model) -> Result<PathBuf> {
    let tool = helpers::workspace_dir()?
        .join("../tools/trezor_core_tools/release_pack.py")
        .canonicalize()
        .context("Failed to locate release_pack.py")?;
    let dir = helpers::artifacts_dir(model)?;
    let out = dir.join("install.zip");
    let status = process::Command::new("python3")
        .arg(&tool)
        .args(["--single".as_ref(), dir.as_os_str()])
        .args(["--out".as_ref(), out.as_os_str()])
        .status()
        .context("Failed to spawn release_pack.py")?;
    ensure!(status.success(), "release_pack.py failed: {status}");
    Ok(out)
}

/// Invalidate the published install set after a bare bootloader build: the
/// firmware beside it folds to the old root, so removing `bundle.json` says
/// they are no longer a signed set.
pub fn invalidate_install_set(model: Model) -> Result<()> {
    let manifest = helpers::artifacts_dir(model)?.join("bundle.json");
    if manifest.exists() {
        fs::remove_file(&manifest)
            .with_context(|| format!("Failed to remove {}", manifest.display()))?;
        println!(
            "xtask: {} removed -- a bare bootloader does not vouch for the \
             firmware beside it",
            manifest.display()
        );
    }
    Ok(())
}

fn publish_bootloader(model: Model, out: &Path) -> Result<()> {
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

/// Sign a prepared release with development keys -- the ceremony's stand-in.
fn devsign(bundle: &Path, tree: &Path, out: &Path) -> Result<()> {
    let tool = helpers::workspace_dir()?
        .join("../tools/trezor_core_tools/firmware_pq_devsign.py")
        .canonicalize()
        .context("Failed to locate firmware_pq_devsign.py")?;
    let status = process::Command::new("python3")
        .arg(&tool)
        .args(["--bundle".as_ref(), bundle.as_os_str()])
        .args(["--tree".as_ref(), tree.as_os_str()])
        .args(["--out".as_ref(), out.as_os_str()])
        .status()
        .context("Failed to spawn firmware_pq_devsign.py")?;
    ensure!(status.success(), "firmware_pq_devsign.py failed: {status}");
    Ok(())
}

/// Patch founder signatures into a prepared release. Signatures land in
/// unauthenticated space, so nothing the prepare stage folded is invalidated.
fn attach(bundle: &Path, tree: &Path, signatures: &Path) -> Result<()> {
    let tool = helpers::workspace_dir()?
        .join("../tools/trezor_core_tools/firmware_pq_attach.py")
        .canonicalize()
        .context("Failed to locate firmware_pq_attach.py")?;
    let status = process::Command::new("python3")
        .arg(&tool)
        .args(["--bundle".as_ref(), bundle.as_os_str()])
        .args(["--tree".as_ref(), tree.as_os_str()])
        .args(["--signatures".as_ref(), signatures.as_os_str()])
        .status()
        .context("Failed to spawn firmware_pq_attach.py")?;
    ensure!(status.success(), "firmware_pq_attach.py failed: {status}");
    Ok(())
}

/// Merge every model's `bundle.json` into one file keyed by model id. Models
/// are independent trees, each with its own root and signature.
fn write_aggregate_bundle(models: &[Model], devel: bool) -> Result<PathBuf> {
    let mut entries = serde_json::Map::new();
    for model in models {
        let per_model = release_dir(*model)?.join("bundle.json");
        let raw = fs::read_to_string(&per_model)
            .with_context(|| format!("Failed to read {}", per_model.display()))?;
        let body: serde_json::Value = serde_json::from_str(&raw)
            .with_context(|| format!("{} is not valid JSON", per_model.display()))?;
        entries.insert(model.model_id().to_string(), body);
    }

    let mut doc = serde_json::Map::new();
    // Per-model bodies keep their own `format` tags: `build_presigned` lifts
    // one out as a standalone manifest.
    doc.insert(
        "format".to_string(),
        serde_json::Value::String(format!("{CONTAINER_MAGIC}-set")),
    );
    doc.insert(
        "format_version".to_string(),
        serde_json::Value::from(CONTAINER_VERSION),
    );
    doc.insert("models".to_string(), serde_json::Value::Object(entries));

    let path = tree_bundle(devel)?;
    fs::create_dir_all(path.parent().context("bundle has no parent")?)?;
    fs::write(&path, serde_json::to_string_pretty(&doc)? + "\n")
        .with_context(|| format!("Failed to write {}", path.display()))?;
    println!(
        "{}",
        format!("xtask: cross-model bundle written to {}", path.display()).green()
    );
    Ok(path)
}

/// Copy a release into `models/` as the committed reference a presigned
/// custom build reads. Bundle, bootloader, secmon pair and nRF image are
/// copied together and re-verified by `presigned_check`.
fn promote(models: &[Model], devel: bool) -> Result<()> {
    let models_dir = helpers::workspace_dir()?.join("models");
    let suffix = if devel { "_devel" } else { "" };

    let bundle = tree_bundle(devel)?;
    let bundle_dst = models_dir.join(bundle_name(devel));
    fs::copy(&bundle, &bundle_dst).with_context(|| {
        format!(
            "Failed to copy {} -> {}",
            bundle.display(),
            bundle_dst.display()
        )
    })?;
    println!("  bundle    -> {}", bundle_dst.display());

    for model in models {
        let out = release_dir(*model)?;
        let id = model.model_id();

        // The signed bootloader replaces the committed one.
        let bl_dst = models_dir
            .join(id)
            .join("bootloaders")
            .join(format!("bootloader_{id}{suffix}.bin"));
        fs::copy(out.join(DEFAULT_BOOTLOADER_FILE), &bl_dst)
            .with_context(|| format!("Failed to write {}", bl_dst.display()))?;
        println!("  {id} bootloader -> {}", bl_dst.display());

        // The secmon travels as a pair: the kernel links the veneer object.
        let secmon_dir = models_dir.join(id).join("secmon");
        let (bin_name, api_name) = if devel {
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
        let nrf_suffix = if devel { "-dev" } else { "" };
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

/// The bootloader whose header this release folds `firmware_root` into.
/// Never built here.
fn release_bootloader(args: &ResolvedBuildArgs, source: BootloaderSource) -> Result<PathBuf> {
    let built = helpers::artifacts_dir(args.model)?.join("bootloader.bin");

    let chosen = match source {
        BootloaderSource::Built => {
            ensure!(
                built.exists(),
                "no built bootloader at {} -- it is not built implicitly:\n             \
                 xtask build bootloader -m {} --bootloader-devel",
                built.display(),
                args.model.model_id()
            );
            built
        }
        BootloaderSource::Committed => committed_bootloader(args)?,
        BootloaderSource::Auto => {
            if built.exists() {
                built
            } else {
                committed_bootloader(args)?
            }
        }
    };

    // The age only means something for a file xtask wrote itself.
    let (which, age) = if chosen.starts_with(helpers::artifacts_dir(args.model)?) {
        ("built", file_age(&chosen))
    } else {
        ("committed", String::new())
    };
    println!(
        "xtask: folding the {which} bootloader {}{age} (its header is re-signed, its code is not rebuilt)",
        chosen.display(),
    );

    check_bootloader_pool(&chosen, args.bootloader_devel)?;
    Ok(chosen)
}

/// Fail closed unless the bootloader's compiled-in founder pool matches the
/// keys this release is signed with. Signing rewrites the header and cannot
/// touch the pool, so nothing downstream can catch a mismatch.
fn check_bootloader_pool(bootloader: &Path, devel: bool) -> Result<()> {
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
    if devel {
        ensure!(
            pool != "production",
            "this bootloader trusts the production founder pool, but the \
             release is being cut with development keys.\n             \
             Rebuild it -- xtask build bootloader --bootloader-devel -- or \
             pick the other source with --bootloader."
        );
    } else {
        ensure!(
            pool == "production",
            "this bootloader's founder pool is `{pool}`, not `production`, but \
             the release is being cut with production keys.\n             \
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

/// The committed bootloader whose header this release folds into. It must
/// have been built with the same key selection as this firmware.
fn committed_bootloader(args: &ResolvedBuildArgs) -> Result<PathBuf> {
    let model_id = args.model.model_id();
    let suffix = if args.bootloader_devel { "_devel" } else { "" };
    let path = helpers::workspace_dir()?
        .join("models")
        .join(model_id)
        .join("bootloaders")
        .join(format!("bootloader_{model_id}{suffix}.bin"));

    ensure!(
        path.exists(),
        "no committed bootloader at {} -- a tree release folds its firmware_root \
         into a bootloader header, so one has to exist to sign against",
        path.display()
    );
    Ok(path)
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
        SignStage::Inline => "signing the release",
        SignStage::PrepareOnly => "preparing the release (unsigned)",
    };
    println!("{}", format!("xtask: {what}").bold().dimmed());
    let status = cmd
        .status()
        .context("Failed to spawn firmware_pq_sign.py")?;
    ensure!(status.success(), "firmware_pq_sign.py failed: {status}");
    Ok(())
}

/// Copy the model's committed nRF image into the release, padded to the
/// 16-byte flash write block the OTA upload engine needs. The padding is
/// outside the signed region, so the fold does not depend on it.
fn stage_nrf_image(args: &ResolvedBuildArgs, out: &Path) -> Result<Option<PathBuf>> {
    let suffix = if args.bootloader_devel { "-dev" } else { "" };
    // The `-bare` build output is the release input; the signer's output is
    // committed under the signed name and would be refused as input.
    let committed = helpers::workspace_dir()?
        .join("models")
        .join(args.model.model_id())
        .join(format!("trezor-ble{suffix}-bare.bin"));

    if !committed.exists() {
        return Ok(None);
    }

    warn_if_nrf_stale(&committed)?;

    let raw =
        fs::read(&committed).with_context(|| format!("Failed to read {}", committed.display()))?;
    // Staged under the signed name, the one the bundle records.
    let padded = out.join(format!("trezor-ble{suffix}.bin"));
    let mut bytes = raw;
    bytes.resize(bytes.len().next_multiple_of(16), 0);
    fs::write(&padded, &bytes).with_context(|| format!("Failed to write {}", padded.display()))?;

    println!(
        "xtask: nRF image {} staged as a model-tree leaf",
        committed.display()
    );
    Ok(Some(padded))
}

/// Warn when a fresher nRF build sits unstaged in nordic/; building the nRF
/// does not update the committed image.
fn warn_if_nrf_stale(committed: &Path) -> Result<()> {
    let built = helpers::workspace_dir()?
        .join("../../nordic/trezor/build/trezor-ble/zephyr/zephyr.trz.bin");
    let (Ok(b), Ok(c)) = (fs::metadata(&built), fs::metadata(committed)) else {
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
            "WARNING: a newer nRF build exists but was never staged:\n                 built   {}\n    signing {}\n  The tree leaf and the embedded coreapp \
             image will both be the OLDER one. Re-run the nRF build with -d -s \
             (build_sign_flash.sh) to stage it.",
            built.display(),
            committed.display()
        )
        .yellow()
    );
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

    let mut devel: Option<bool> = None;
    for model in &models {
        let model = *model;
        let build_args = BuildArgs {
            project: Project::Firmware,
            model,
            emulator: false,
            preset: args.preset.clone(),
            bootloader: args.bootloader,
            options: args.options.clone(),
        };
        let resolved = ResolvedBuildArgs::from_build_args(&build_args)?;
        ensure!(
            applies(&resolved)?,
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
        build_release(
            &resolved,
            &ALL_VARIANTS,
            args.bootloader,
            SignStage::PrepareOnly,
            Dest::Release,
            args.sigmask,
        )?;
        devel = Some(resolved.bootloader_devel);
    }

    // One run, one key selection.
    let devel = devel.context("no model was released")?;
    let set_path = write_aggregate_bundle(&models, devel)?;
    let tree = set_path
        .parent()
        .context("the cross-model bundle has no parent")?
        .to_path_buf();
    // Sign + attach only for a development cut; a production release stops
    // here unsigned, and `attach` completes it after the ceremony.
    if devel {
        let signatures = tree.join("signatures-devel.json");
        devsign(&set_path, &tree, &signatures)?;
        attach(&set_path, &tree, &signatures)?;
        // Publish each model's now-signed bootloader for `flash`/`upload`.
        for model in &models {
            let out = release_dir(*model)?;
            publish_bootloader(*model, &out)?;
            publish_images(*model, &out, &ALL_VARIANTS, &ReleaseManifest::load(&out)?)?;
            // Repacked: `install.zip` is a view of the published set.
            pack_install_zip(*model)?;
        }
    } else {
        println!(
            "{}",
            "xtask: prepared UNSIGNED -- sign the recorded modelRoots, then \
             `firmware_pq_attach.py --bundle <set> --tree <dir> \
             --signatures <sigs>`"
                .bold()
                .dimmed()
        );
    }

    // Packed last; the packer names the container from the signing state.
    write_release_container(&set_path, devel)?;
    if args.promote {
        // Promotion needs a signed release.
        ensure!(
            devel,
            "this release was prepared UNSIGNED, so there is nothing to \
             promote yet -- attach the ceremony's signatures first, then \
             promote the signed release"
        );
        promote(&models, devel)?;
    }
    Ok(())
}
