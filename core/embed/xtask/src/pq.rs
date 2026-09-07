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
    /// Every variant in the release, each with the `firmware_type` byte the
    /// bootloader must carry for the device to boot that variant.
    variants: Vec<(Variant, u8)>,
    /// Where that byte sits in `bootloader.bin`. Recorded by the signer, which
    /// locates it by probing its own build, so nothing here needs to know the
    /// boot-header layout.
    firmware_type_offset: usize,
}

impl ReleaseManifest {
    pub fn load(dir: &Path) -> Result<ReleaseManifest> {
        let path = dir.join("bundle.json");
        let text = fs::read_to_string(&path)
            .with_context(|| format!("Failed to read {}", path.display()))?;
        let json: serde_json::Value = serde_json::from_str(&text)
            .with_context(|| format!("Failed to parse {}", path.display()))?;

        let offset = json
            .get("firmware_type_offset")
            .and_then(|v| v.as_u64())
            .context("release bundle has no firmware_type_offset -- it was signed by an older tool, rebuild it")?;

        let mut variants = Vec::new();
        for entry in json
            .get("variants")
            .and_then(|v| v.as_array())
            .context("release bundle has no variants")?
        {
            let name = entry
                .get("firmware")
                .and_then(|v| v.as_str())
                .context("a release variant has no firmware name")?;
            let name = name.strip_suffix(".bin").unwrap_or(name);
            let variant =
                Variant::from_name(name).with_context(|| format!("unknown variant `{name}`"))?;
            let firmware_type = entry
                .get("firmware_type")
                .and_then(|v| v.as_u64())
                .with_context(|| format!("variant `{name}` records no firmware_type"))?;
            variants.push((variant, u8::try_from(firmware_type)?));
        }

        Ok(ReleaseManifest {
            variants,
            firmware_type_offset: usize::try_from(offset)?,
        })
    }

    pub fn variants(&self) -> impl Iterator<Item = Variant> + '_ {
        self.variants.iter().map(|(v, _)| *v)
    }

    pub fn names(&self) -> String {
        self.variants()
            .map(|v| v.name())
            .collect::<Vec<_>>()
            .join(", ")
    }

    fn firmware_type(&self, variant: Variant) -> Result<u8> {
        self.variants
            .iter()
            .find(|(v, _)| *v == variant)
            .map(|(_, t)| *t)
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
        let src = dir.join("bootloader.bin");
        let mut image =
            fs::read(&src).with_context(|| format!("Failed to read {}", src.display()))?;

        let at = self.firmware_type_offset;
        let current = *image.get(at).with_context(|| {
            format!(
                "{} is shorter than its firmware_type offset {at}",
                src.display()
            )
        })?;
        // A release is signed bare, so anything else means the offset and the
        // image disagree -- a stale bundle.json next to a different bootloader.
        ensure!(
            current == 0,
            "{} already carries firmware_type {current} at offset {at}, but a \
             release is signed bare -- bundle.json does not match this bootloader",
            src.display(),
        );
        image[at] = firmware_type;

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
    let dir = release_dir(model)?;
    let model_id = model.model_id();
    ensure!(
        dir.exists(),
        "no pq_secure release at {dir} -- build one first:\n             \
         xtask build firmware -m {model_id} --bootloader-devel",
        dir = dir.display(),
    );
    let release = ReleaseManifest::load(&dir)?;

    if project == Project::Bootloader {
        let (bootloader, variant) = match variant {
            None => (dir.join("bootloader.bin"), None),
            Some(variant) => (release.stamp(&dir, variant)?, Some(variant)),
        };
        return Ok(ReleaseInstall {
            bootloader,
            firmware: None,
            variant,
        });
    }

    let variant = pick_variant(project, variant, &release)?;
    Ok(ReleaseInstall {
        bootloader: release.stamp(&dir, variant)?,
        firmware: Some(dir.join(format!("{}.bin", variant.name()))),
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
    // out then would waste four builds.
    if !args.bootloader_devel {
        bail!(
            "a tree release has to be signed, and only development keys are \
             available here -- pass --bootloader-devel, or build for a \
             founder-keyed device once --presigned lands"
        );
    }

    let out = release_dir(args.model)?;
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

        // Each build overwrites artifacts/<MODEL>/{firmware,prodtest}.bin, so
        // take a copy under the variant's own name before the next one runs.
        let built = helpers::artifacts_dir(args.model)?.join(variant.artifact());
        let dst = out.join(format!("{}.bin", variant.name()));
        fs::copy(&built, &dst).with_context(|| {
            format!("Failed to collect {} -> {}", built.display(), dst.display())
        })?;
    }

    let bootloader_out = out.join("bootloader.bin");
    fs::copy(&bootloader, &bootloader_out).with_context(|| {
        format!(
            "Failed to copy {} -> {}",
            bootloader.display(),
            bootloader_out.display()
        )
    })?;

    // The nRF is a peer leaf of the same model tree, so it rides the one
    // boot-header signature. Whether its own MCUboot verifies that tree is
    // fixed per model, not chosen per build.
    let nrf = stage_nrf_image(args, &out)?;
    let nrf_pq_native = args.model.config()?.nrf_pq_native;

    sign(&out, variants, nrf.as_deref(), nrf_pq_native)?;

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
    Ok(chosen)
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
fn sign(out: &Path, variants: &[Variant], nrf: Option<&Path>, nrf_pq_native: bool) -> Result<()> {
    let signer = helpers::workspace_dir()?
        .join("../tools/trezor_core_tools/firmware_pq_sign.py")
        .canonicalize()
        .context("Failed to locate firmware_pq_sign.py")?;

    let mut cmd = process::Command::new("python3");
    cmd.arg(&signer);
    for variant in variants {
        cmd.args([
            "--firmware".as_ref(),
            out.join(format!("{}.bin", variant.name())).as_os_str(),
        ]);
    }
    cmd.args([
        "--bootloader".as_ref(),
        out.join("bootloader.bin").as_os_str(),
    ]);
    cmd.args([
        "--manifest-out".as_ref(),
        out.join("bundle.json").as_os_str(),
    ]);
    cmd.args(["--zip-out".as_ref(), out.with_extension("zip").as_os_str()]);

    if let Some(nrf) = nrf {
        cmd.args(["--nrf".as_ref(), nrf.as_os_str()]);
        if nrf_pq_native {
            cmd.arg("--nrf-pq-native");
        }
    }

    println!("{}", "xtask: signing the release".bold().dimmed());
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

    for model in models {
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
        build_release(&resolved, &ALL_VARIANTS, args.bootloader)?;
    }
    Ok(())
}
