//! Building a pq_secure (Merkle-tree) firmware release.
//!
//! A legacy firmware image is self-contained: build it, sign it, install it.
//! A Merkle-tree release is not. Authenticity is the fold of a variant's
//! manifest leaf up to the `firmware_root` that the SIGNED BOOT HEADER commits
//! to, so a firmware image is only meaningful next to a bootloader whose header
//! names the tree it belongs to. `xtask build firmware` on a tree model
//! therefore produces a release directory rather than one binary.
//!
//! Two consequences shape everything here:
//!
//! * `firmware_root` is a root over the VARIANT SET. Building one variant is
//!   not a subset of building four -- it yields a one-leaf tree with a
//!   different root, and so a different boot header. Build scope and signing
//!   are one decision, not two.
//!
//! * Re-signing rewrites the boot HEADER, not the bootloader CODE. So the
//!   committed bootloader binary is reused as-is and only its header is folded
//!   and re-signed; the emitted bootloader.bin still differs from the committed
//!   one, and phase 1 of an OTA installs exactly that difference as a
//!   header-only update. Nothing needs the bootloader recompiled.

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
///
/// Also the value type of `--variant`, so clap validates the name and lists
/// the choices.
#[derive(ValueEnum, Clone, Copy, PartialEq, Eq, Debug)]
#[value(rename_all = "kebab-case")]
pub enum Variant {
    Universal,
    BtcOnly,
    /// The unofficial slot. Its authenticity leaf zeroes the app's size,
    /// code_hash and version, so any locally built app folds to the one
    /// founder-signed custom leaf.
    Custom,
    /// Its own project rather than a firmware variant -- a single secure module
    /// -- but still a leaf of the same tree.
    Prodtest,
}

/// Which bootloader binary a release folds its `firmware_root` into.
///
/// Signing rewrites the boot HEADER, not the CODE, so this decides which code
/// the release's header ends up vouching for -- and a device runs exactly that
/// code. Whichever is chosen must have been built with the same key selection
/// as the release is signed with (`--bootloader-devel`), or the device will
/// trust a different set of founder keys than the release was signed with and
/// verify nothing.
#[derive(ValueEnum, Clone, Copy, PartialEq, Eq, Debug, Default)]
#[value(rename_all = "kebab-case")]
pub enum BootloaderSource {
    /// The bootloader you last built for this model, falling back to the
    /// committed binary when there is none.
    #[default]
    Auto,
    /// The bootloader you last built for this model
    /// (`build/artifacts/<MODEL>/bootloader.bin`). Errors if absent -- it is
    /// never built implicitly, so `xtask build bootloader` first.
    Built,
    /// The committed binary in `models/<MODEL>/bootloaders/`. What a production
    /// release must fold: there the founder-signed bootloader is a released
    /// artifact whose exact bytes have to be signed over, and a local rebuild
    /// would be the wrong thing.
    Committed,
}

/// Every variant of a full release. The founder tree must contain all of them
/// or a released co-path folds to nothing.
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

    /// Which project builds this variant, and so which `xtask flash <PROJECT>`
    /// installs it.
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

    /// Point a resolved arg set at this variant.
    ///
    /// Variant selection rides the EXISTING build flags rather than a new
    /// `--variant`: `--btc-only` and `--unsafe-fw` already mean exactly this,
    /// and a second way to say it would be a second thing to keep in sync.
    fn apply(self, args: &mut ResolvedBuildArgs) {
        args.project = self.project();
        args.btc_only = matches!(self, Variant::BtcOnly);
        args.unsafe_fw = matches!(self, Variant::Custom);
    }
}

/// Where a model's release is assembled: `build-xtask/tree/<MODEL>/`, with the
/// portable zip alongside it as `<MODEL>.zip`.
pub fn release_dir(model: Model) -> Result<PathBuf> {
    // Normalised, because cargo reports its target directory as
    // `core/embed/../build-xtask` and every path printed from here -- the
    // release dir, the zip -- would carry that `..` through and read as if it
    // were somewhere else.
    let build_dir = helpers::build_dir()?;
    let build_dir = build_dir.canonicalize().unwrap_or(build_dir);
    Ok(build_dir.join("tree").join(model.model_id()))
}

/// What a signed release records about itself, read from its `bundle.json`.
pub struct ReleaseManifest {
    /// Which model this release is for, from the signer's reading of the SIGNED
    /// boot header. Recorded so a release directory is self-describing; the
    /// per-model file used to say so only by being the value of a model-keyed
    /// entry in the aggregate, which a presigned build then dropped.
    model: String,
    /// The bootloader image's name within the release.
    bootloader_file: String,
    /// Every variant in the release: its hardened `firmware_type` codeword,
    /// and the image's own filename. The name is RECORDED, not derived from the
    /// variant -- a resigned build keeps the name it was built under
    /// (`firmware.bin`), and deriving `<variant>.bin` would look for a file
    /// nobody wrote.
    variants: Vec<VariantEntry>,
    /// Where that field sits in the bootloader image, and how wide it is. Both
    /// recorded by the signer, which locates the field by probing its own
    /// build, so nothing here needs to know the boot-header layout -- or the
    /// codewords, which stay in the device headers and the signer.
    firmware_type_offset: usize,
    firmware_type_len: usize,
    /// The value a bare release carries. Read from the bundle rather than
    /// known, so the codewords stay in the device headers and the signer.
    firmware_type_bare: u32,
}

impl ReleaseManifest {
    pub fn load(dir: &Path) -> Result<ReleaseManifest> {
        let path = dir.join("bundle.json");
        let text = fs::read_to_string(&path)
            .with_context(|| format!("Failed to read {}", path.display()))?;
        let json: serde_json::Value = serde_json::from_str(&text)
            .with_context(|| format!("Failed to parse {}", path.display()))?;

        // Identify the document BEFORE reading anything out of it. A release
        // cut by an older tool is refused by version rather than diagnosed one
        // missing field at a time, which is what used to happen.
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

        // Grouped under the bootloader because they describe THAT binary: the
        // offset is into it, and the bare value is what it currently carries.
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
            // The variant's own name, not its filename. Recovering identity by
            // stripping `.bin` made the writer's naming a claim about what the
            // image IS; the signer now records the name it derived from the
            // folded manifest's codeword.
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

    /// Write a copy of the release bootloader provisioned for `variant`, and
    /// return its path.
    ///
    /// This is the whole of "installing" a boot header by debugger:
    /// `firmware_type` is unauthenticated, so stamping it needs no key and
    /// leaves the signature intact -- it is the same byte the bootloader writes
    /// for itself when it installs firmware over the wire.
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
        // A release is signed bare, so anything else means the offset and the
        // image disagree -- a stale bundle.json next to a different bootloader.
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

/// The images a pq_secure release contributes to one install.
///
/// Bootloader and firmware come as a PAIR because they are one unit: the
/// bootloader's signed header carries the `firmware_root` the firmware folds up
/// to, and rebuilding the firmware changes that root -- so the bootloader
/// already on a device vouches only for the previous build. Installing one
/// without the other is not useful.
pub struct ReleaseInstall {
    /// The release bootloader, provisioned for `variant` when there is one.
    pub bootloader: PathBuf,
    /// The firmware image, absent when only the bootloader was asked for.
    pub firmware: Option<PathBuf>,
    /// The variant this install provisions the device for, `None` for a bare
    /// bootloader.
    pub variant: Option<Variant>,
}

/// Resolve what to install from a model's release, stamping the bootloader for
/// the variant being installed.
///
/// `firmware_type` is the provisioning marker an over-the-wire install would
/// have written; a debugger flash or a factory image has nobody to write it, so
/// it is stamped here. Asking for the bootloader ALONE leaves it bare unless a
/// variant is named -- bare is the legitimate state of a fresh device, which
/// then takes its firmware over the wire.
pub fn resolve_install(
    model: Model,
    project: Project,
    variant: Option<Variant>,
) -> Result<ReleaseInstall> {
    let model_id = model.model_id();

    // A BARE bootloader needs no release. The built binary is signed on its own
    // and its `firmware_root` commits to nothing, which is the right state for a
    // fresh device: it reads as unprovisioned and takes its firmware over the
    // wire, which brings its own header. Only stamping a variant needs the
    // bundle (for the codeword and the offset), and only firmware needs the
    // tree. Prefer a release's folded bootloader when one is there -- the
    // firmware beside it verifies against that header -- and otherwise fall back
    // to the freshly built one rather than refusing.
    if project == Project::Bootloader && variant.is_none() {
        // ONE canonical bootloader binary: whatever last wrote
        // `artifacts/<MODEL>/bootloader.bin`. `xtask build bootloader` writes
        // it, and cutting a release writes its folded+signed bootloader back
        // over it, so "flash the bootloader" always means the last one
        // produced -- with no source to choose and no way for a build to be
        // silently ignored in favour of an older release copy.
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

    // Installed straight from the published artifacts -- no signing here.
    // `xtask build` and `xtask release` both sign, and both publish the result
    // to `artifacts/<MODEL>/`, so what is there IS the last thing produced.
    // Signing a third time would re-cut a one-variant tree over an image that
    // already folds correctly, and throw away a multi-variant release's proof
    // doing it.
    //
    // `bundle.json` is the token saying these binaries form an installable SET:
    // it is published together with them, and `xtask build bootloader` removes
    // it, because a freshly built BARE bootloader no longer vouches for the
    // firmware sitting beside it.
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

/// Which variant of a release to install.
///
/// An explicit choice wins. Otherwise the project names it -- prodtest is its
/// own variant -- and a release holding a single firmware variant needs
/// nothing.
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
    // Asking for prodtest names the variant outright -- it is a project, not a
    // firmware build flag.
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

/// Whether this build produces a Merkle-tree release.
///
/// Emulator builds never do, whatever the model: there is no bootloader to
/// carry a signed `firmware_root` and no flash for a tree to be installed into,
/// so the unix binary is the whole artifact.
pub fn applies(args: &ResolvedBuildArgs) -> Result<bool> {
    Ok(!args.emulator && args.model.config()?.has_feature("pq_secure_boot"))
}

/// Build, sign and bundle a release.
///
/// The dev path: sign locally with development keys over whatever variants were
/// built. A release for a founder-keyed device cannot be signed here (no keys),
/// and is a separate mode -- see the `--presigned` and `--production` work.
pub fn build_release(
    args: &ResolvedBuildArgs,
    variants: &[Variant],
    bootloader: BootloaderSource,
) -> Result<()> {
    // Checked before anything is built: signing is the last step, and finding
    // out then would waste four builds. Only an inline signature needs keys --
    // PREPARING a release needs none, which is the whole point of the split.
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

    // Resolved before anything is built: it is only a path lookup, and finding
    // out afterwards that there is no bootloader to fold would waste every
    // firmware build.
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

        // Keep the UNIVERSAL variant's secmon beside the release: it is the one
        // promotion commits, and therefore the one a presigned custom build
        // embeds. The custom slot's leaf commits the WHOLE secmon entry, so
        // that build only folds if the secmon it embeds is byte-identical to
        // the one the slot was signed over.
        //
        // The secmon is NOT variant-dependent -- nothing in it reads a variant
        // -- so every variant now builds the same bytes and "universal's" is
        // simply "the" secmon. It is pinned to universal anyway rather than
        // left to whichever variant ran last: that is what silently broke
        // before, when `artifacts/secmon.bin` held prodtest's by the time
        // promotion copied it, and pinning keeps this correct if a future
        // feature ever does reach the secmon.
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

        // A release builds several variants into ONE artifact slot, so each has
        // to be copied out under its own name before the next overwrites it. A
        // build produces one variant and signs it where it lies -- the container
        // records each image's `file`, so it keeps its build name.
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

    // Signing rewrites the header in place, so when the chosen bootloader
    // already sits at the destination there is nothing to copy -- and copying a
    // file onto itself would truncate it.
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

    // The nRF is a peer leaf of the same model tree, so it rides the one
    // boot-header signature. Whether its own MCUboot verifies that tree is
    // fixed per model, not chosen per build.
    let nrf = stage_nrf_image(args, &out)?;
    let nrf_pq_native = args.model.config()?.nrf_pq_native;

    run_signer(&out, &firmwares, nrf.as_deref(), nrf_pq_native, sign)?;
    match dest {
        // Signed where it lies: already the canonical set, nothing to publish.
        // Pack the container `upload` installs so every consumer finds it.
        Dest::Artifacts => {
            pack_install_zip(args.model)?;
        }
        // A release PREPARES; it publishes once its signatures are attached,
        // which `release()` does after the signing stage. Nothing to do here.
        Dest::Release => {}
    }

    println!(
        "{}",
        format!("xtask: release ready in {}", out.display()).green()
    );
    Ok(())
}

/// The bootloader whose header this release folds `firmware_root` into.
///
/// Never built here: a release builds firmware, and quietly rebuilding the
/// bootloader as a side effect of `build prodtest` would be a surprise. The
/// choice is reported, with the file's age, because it decides which code the
/// device ends up running -- a stale pick is the difference between testing
/// your bootloader change and testing last week's.
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

    // The age is only meaningful for the artifact xtask wrote itself. On the
    // committed binary the timestamp says when git last checked it out, which
    // would read as if it had just been built.
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

/// Does the code we are about to fold trust the key pool this release is signed
/// with?
///
/// Signing rewrites the header; it cannot touch the pool, which is a
/// compile-time choice (`BOOTLOADER_DEVEL`) leaving no trace in the header. So
/// the ceremony cannot see it, and neither can the flag check above: that one
/// says which keys this RELEASE uses, not which keys the BINARY trusts. Get
/// them out of step and the device runs code that verifies OTA boot headers
/// against the other pool -- and the development private halves are in this
/// repository, so a production release folding a devel build would accept
/// firmware signed by anyone, while rejecting the real signer's.
///
/// One `xtask build bootloader --bootloader-devel` is enough to leave such a
/// binary in artifacts/, where `BootloaderSource::Auto` prefers it from then
/// on. Nothing rebuilds it here (a release builds firmware only), so the stale
/// pick can outlive any memory of that build.
///
/// The digest is over the CODE, not the file: the file changes as soon as the
/// header is re-signed, while the code digest is exactly what the signed leaf
/// commits to, so it is the value a ceremony can pin and re-check afterwards.
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

    // A production release must POSITIVELY carry the production pool. devel,
    // mixed and unknown are all rejected, because none of them is evidence that
    // the code trusts the keys this release is signed with -- and the whole
    // point of the check is that nothing downstream can tell. `unknown` in
    // particular is not a benign "old binary": a bootloader with no founder
    // pool linked cannot verify an OTA boot header at all, so it is not a
    // working production artifact regardless of the key question.
    //
    // A devel cut is only required not to carry the PRODUCTION pool. The
    // asymmetry is deliberate: a devel release that turns out unverifiable is a
    // developer's problem, discovered on their own bench, while a production
    // one reaches users -- so only the latter has to justify itself.
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

/// ` (built N minutes ago)`, or nothing if the age cannot be read. Only
/// meaningful for a file xtask produced -- see the caller.
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

/// The committed bootloader whose header this release folds into./// The
/// committed bootloader whose header this release folds into.
///
/// Reused rather than rebuilt, which is sound because signing rewrites only the
/// header. It does mean the committed binary must have been built with the same
/// key selection as this firmware -- mixing them produces an image whose kernel
/// SecureFaults on its first instruction, since the kernel embeds one secmon
/// and the header vouches for another.
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
/// re-sign it, and bake each variant's co-path into its own image.
///
/// The crypto stays in Python: this is the same relationship xtask already has
/// with `headertool`, and the signer is what a founder ceremony runs too.
) -> Result<()> {
    let signer = helpers::workspace_dir()?
        .join("../tools/trezor_core_tools/firmware_pq_sign.py")
        .canonicalize()
        .context("Failed to locate firmware_pq_sign.py")?;

    // The assembled paths, not names rebuilt from variants: a build signs each
    // image where it lies, so the filename is the build's, not the variant's.
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
    // No archive here. Packing is one job in one place -- `release_pack.py`,
    // driven by `pack_install_zip` for an install set and by the release for
    // its containers -- so an archive is never cut before the thing it packs is
    // finished. Preparing additionally leaves the signature region zero.
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

/// Put the model's committed nRF image into the release, padded, and return it.
///
/// Padded to the 16-byte flash write block because the OTA upload engine needs
/// a flash-aligned length while an MCUboot image is an arbitrary one. The
/// padding is inert: MCUboot reads by its own header sizes and ignores trailing
/// bytes, and the model-tree leaf covers only the signed region, so the fold
/// does not depend on it. Copied rather than padded in place so the committed
/// source is never modified.
fn stage_nrf_image(args: &ResolvedBuildArgs, out: &Path) -> Result<Option<PathBuf>> {
    let suffix = if args.bootloader_devel { "-dev" } else { "" };
    let committed = helpers::workspace_dir()?
        .join("models")
        .join(args.model.model_id())
        .join(format!("trezor-ble{suffix}.bin"));

    if !committed.exists() {
        return Ok(None);
    }

    warn_if_nrf_stale(&committed)?;

    let raw =
        fs::read(&committed).with_context(|| format!("Failed to read {}", committed.display()))?;
    let padded = out.join(committed.file_name().expect("nRF image has a file name"));
    let mut bytes = raw;
    bytes.resize(bytes.len().next_multiple_of(16), 0);
    fs::write(&padded, &bytes).with_context(|| format!("Failed to write {}", padded.display()))?;

    println!(
        "xtask: nRF image {} staged as a model-tree leaf",
        committed.display()
    );
    Ok(Some(padded))
}

/// Warn when a fresher nRF build is sitting in nordic/ unstaged.
///
/// Building the nRF does not update the committed image -- build_sign_flash.sh
/// -d -s does that copy -- so it is entirely possible to sign a leaf weeks
/// older than the image just built, with nothing to say so. That silence has
/// already cost one debugging session.
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

/// Cut a complete pq_secure release: every variant, in one signed founder tree.
///
/// With no model, every model using the layout is released. They are
/// independent, not joint: each carries its own firmware_root in its own signed
/// bootloader header, so releasing one leaves the others' signatures alone.
/// Doing them together is a convenience, and deliberately so -- a shared root
/// across models would turn every single-model release into an all-model
/// re-sign.
pub fn release(args: ReleaseArgs) -> Result<()> {
    let models: Vec<Model> = match args.model {
        Some(model) => vec![model],
        None => {
            let all: Vec<Model> = Model::value_variants()
                .iter()
                .copied()
                .filter(|m| {
                    m.config()
                        .map(|c| c.has_feature("pq_secure_boot"))
                        .unwrap_or(false)
                })
                .collect();
            ensure!(
                !all.is_empty(),
                "no model uses the Merkle-tree layout, so there is nothing to release"
            );
            println!(
                "xtask: releasing every tree model: {}",
                all.iter()
                    .map(|m| m.model_id())
                    .collect::<Vec<_>>()
                    .join(", ")
            );
            all
        }
    };

    let mut devel: Option<bool> = None;
    for model in &models {
        let model = *model;
        let build_args = BuildArgs {
            project: Project::Firmware,
            model,
            emulator: false,
            preset: args.preset.clone(),
            // Not read from here: build_release takes the source directly, so
            // the per-model BuildArgs only has to carry the build itself.
            bootloader: args.bootloader,
            options: args.options.clone(),
        };
        let resolved = ResolvedBuildArgs::from_build_args(&build_args)?;
        ensure!(
            applies(&resolved)?,
            "{} does not use the Merkle-tree layout, so it has no release to cut",
            model.model_id()
        );
        // The two flags select key sets on DIFFERENT axes, and exactly one
        // pairing is dangerous. `--bootloader-devel` picks the founder pool the
        // boot chain trusts (root_keys.h, on BOOTLOADER_DEVEL); `--production`
        // picks the keys that sign translations and coin definitions (the
        // dev_keys cargo feature). With NEITHER, a release carries production
        // founder keys and DEVELOPMENT data keys: secure boot really is
        // enforced, so it looks shippable, yet it accepts translations and
        // definitions signed with private halves checked into this repository.
        //
        // The other three pairings are fine -- fully development, fully
        // production, or devel founder keys with production data keys (which is
        // incoherent, but a build carrying the devel pool has no secure boot to
        // undermine anyway).
        //
        // Stated as a requirement rather than left to omission, because the
        // dangerous case is the one you get by typing nothing. Checked for a
        // RELEASE only: a release is the artifact that reaches real devices,
        // while a local `xtask build` of one project is a development
        // convenience that should not need ceremony flags.
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
        // PREPARE. Every model is folded before any of them is signed, which
        // is the order a ceremony runs in -- signing model 1 while model 2 has
        // not been built yet is not a thing an airgapped step can do.
        build_release(
            &resolved,
            &ALL_VARIANTS,
            args.bootloader,
            SignStage::PrepareOnly,
            Dest::Release,
        )?;
        devel = Some(resolved.bootloader_devel);
    }

    // Every model in one run is signed with the same key selection, so the
    // aggregate belongs to that one key set.
    let devel = devel.context("no model was released")?;
    let set_path = write_aggregate_bundle(&models, devel)?;
    let tree = set_path
        .parent()
        .context("the cross-model bundle has no parent")?
        .to_path_buf();

    // SIGN + ATTACH, but only for a development cut. A production release stops
    // here, unsigned, because the founder key is not in this process -- the
    // container it just wrote IS the signing request, and `attach` completes it
    // once the ceremony returns a signature set.
    if devel {
        let signatures = tree.join("signatures-devel.json");
        devsign(&set_path, &tree, &signatures)?;
        attach(&set_path, &tree, &signatures)?;
        // Now that the signatures are on, each model's bootloader is the
        // current one -- publish it so `flash`/`upload` see it.
        for model in &models {
            let out = release_dir(*model)?;
            publish_bootloader(*model, &out)?;
            publish_images(*model, &out, &ALL_VARIANTS, &ReleaseManifest::load(&out)?)?;
            // Repacked with them: `install.zip` is a view of the published set,
            // and anything reading it directly -- the OTA harness -- would
            // otherwise install whatever a previous build left there.
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

    // Packed LAST, so every archive holds the finished artifacts. The packer
    // names the container, because only it can read the signing state off the
    // signatures.
    write_release_container(&set_path, devel)?;
    if args.promote {
        // Promotion commits the reference set a presigned custom build folds
        // into, so it needs a SIGNED release. A production run deliberately
        // stops before signing, so it cannot promote in the same command --
        // promote after the ceremony's signatures have been attached.
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
