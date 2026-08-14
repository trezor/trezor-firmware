//! Steps that run after a successful `cargo build`: publishing the built
//! ELF/bin as artifacts (see [`crate::helpers::artifacts_dir`]) and
//! generating the Merkle proofs and RootPacket needed to load them.

use crate::{args::Model, helpers};
use anyhow::{Context, Ok, Result, ensure};
use std::{
    path::{Path, PathBuf},
    process::Command,
};

/// Strips app-internal symbol names from a built ELF that shouldn't leak
/// into a published binary; see [`crate::tools::zero_symnames`].
pub use crate::tools::zero_symnames;

/// Python tool building the app Merkle proofs and the RootPacket(s), relative to the repo root.
const TREZORAPP_TOOL: &str = "core/tools/trezor_core_tools/trezorapp_tool.py";

/// Publishes `binary` by copying it into the artifacts directory for
/// `model`/`emulator` as `<app>.elf`, and updates the `latest` symlink to
/// point at that directory. Called once with the freshly built ELF and
/// again with the converted app image from [`crate::binary::convert_elf_to_bin`]
/// (which overwrites the first copy under the same name).
pub fn publish_artifact(binary: &Path, app: &str, model: Model, emulator: bool) -> Result<()> {
    let dir = helpers::artifacts_dir(model, emulator)?;
    helpers::ensure_directory(&dir)?;

    let name = format!("{}.elf", app);

    std::fs::copy(binary, dir.join(&name)).with_context(|| {
        format!(
            "Failed to copy `{}` to `{}`",
            binary.display(),
            dir.join(&name).display()
        )
    })?;

    helpers::update_latest_symlink(&dir)?;

    Ok(())
}

/// Writes a Merkle proof next to every app image published for the given model, together with
/// the dev-signed and timestamped RootPacket(s) needed to load them.
///
/// All published apps are passed to the tool at once: the proofs of a ring are only valid for
/// the RootPacket built from the whole ring, so rebuilding a single app has to rebuild the set.
///
/// TODO: temporary, only works for the in-tree sdk/apps workspace of a
/// trezor-firmware checkout -- it hardcodes that workspace's fixed depth
/// below the repo root to locate trezorapp_tool.py. A standalone app repo
/// (modular-xtask consumed as a path dependency from elsewhere) has no
/// trezor-firmware checkout at a known position relative to it, so proof/
/// RootPacket generation is skipped there (with a warning) instead of
/// attempted incorrectly. This whole shell-out to trezorapp_tool.py is
/// itself expected to be replaced by trezorctl functionality eventually.
pub fn generate_app_proofs(model: Model, emulator: bool) -> Result<()> {
    if !helpers::is_workspace()? {
        println!(
            "xtask: warning: not running in the sdk/apps workspace, skipping app proof/RootPacket generation"
        );
        return Ok(());
    }

    let dir = helpers::artifacts_dir(model, emulator)?;
    let apps = published_apps(&dir)?;
    ensure!(
        !apps.is_empty(),
        "No app image found in `{}`",
        dir.display()
    );

    // Hardcoded: the sdk/apps workspace root is always two levels below the
    // trezor-firmware repo root (<repo>/sdk/apps).
    let repo_root = helpers::root_dir()?
        .parent()
        .and_then(Path::parent)
        .context("Failed to resolve repo root from the sdk/apps workspace root")?
        .to_path_buf();

    let mut cmd = Command::new("uv");
    cmd.arg("run")
        .arg(repo_root.join(TREZORAPP_TOOL))
        .arg("build-dev-bundle")
        .args(&apps)
        .current_dir(&repo_root);

    println!("xtask: Building app proofs and dev-signed RootPacket");
    println!("\x1b[1;90m{}\x1b[0m", helpers::command_args_to_string(&cmd));

    let status = cmd
        .status()
        .context("Failed to spawn `trezorapp_tool.py`")?;
    ensure!(
        status.success(),
        "`trezorapp_tool.py build-dev-bundle` failed with status: {status}"
    );

    Ok(())
}

/// Returns the app images published in `dir`, sorted to keep the Merkle trees deterministic.
fn published_apps(dir: &Path) -> Result<Vec<PathBuf>> {
    let mut apps: Vec<PathBuf> = std::fs::read_dir(dir)
        .with_context(|| format!("Failed to read `{}`", dir.display()))?
        .filter_map(|entry| entry.ok().map(|entry| entry.path()))
        .filter(|path| path.extension().and_then(|ext| ext.to_str()) == Some("elf"))
        .collect();

    apps.sort();
    Ok(apps)
}
