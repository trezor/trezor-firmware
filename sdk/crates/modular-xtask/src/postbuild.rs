use crate::{args::Model, helpers};
use anyhow::{Context, Ok, Result, ensure};
use std::{
    path::{Path, PathBuf},
    process::Command,
};

pub use crate::tools::zero_symnames;

/// Python tool building the app Merkle proofs and the RootPacket(s), relative to the repo root.
const TREZORAPP_TOOL: &str = "core/tools/trezor_core_tools/trezorapp_tool.py";

/// Publishes a built binary by copying it to the `published` directory with a name that includes
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

    Ok(())
}

/// Writes a Merkle proof next to every app image published for the given model, together with
/// the dev-signed and timestamped RootPacket(s) needed to load them.
///
/// All published apps are passed to the tool at once: the proofs of a ring are only valid for
/// the RootPacket built from the whole ring, so rebuilding a single app has to rebuild the set.
pub fn generate_app_proofs(model: Model, emulator: bool) -> Result<()> {
    let dir = helpers::artifacts_dir(model, emulator)?;
    let apps = published_apps(&dir)?;
    ensure!(
        !apps.is_empty(),
        "No app image found in `{}`",
        dir.display()
    );

    let repo_root = helpers::repo_root()?;

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
