//! Steps that run after a successful `cargo build`: publishing the built
//! ELF/bin as artifacts (see [`crate::helpers::artifacts_dir`]) and
//! generating the Merkle proofs and RootPacket needed to load them.

use crate::{artifacts, helpers};
use anyhow::{Context, Ok, Result, ensure};
use std::{path::Path, process::Command};

/// Python tool building the app Merkle proofs and the RootPacket(s), relative to the repo root.
const APPTREE_TOOL: &str = "core/tools/trezor_core_tools/extapp_tool.py";

/// Writes a Merkle proof next to every app image published for the given model, together with
/// the dev-signed and timestamped RootPacket(s) needed to load them.
///
/// All published apps are passed to the tool at once: the proofs of a ring are only valid for
/// the RootPacket built from the whole ring, so rebuilding a single app has to rebuild the set.
///
/// TODO: temporary, only works for the in-tree sdk/apps workspace of a
/// trezor-firmware checkout -- it hardcodes that workspace's fixed depth
/// below the repo root to locate extapp_tool.py. A standalone app repo
/// (modular-xtask consumed as a path dependency from elsewhere) has no
/// trezor-firmware checkout at a known position relative to it, so proof/
/// RootPacket generation is skipped there (with a warning) instead of
/// attempted incorrectly. This whole shell-out to extapp_tool.py is
/// itself expected to be replaced by trezorctl functionality eventually.
pub fn generate() -> Result<()> {
    let apps = artifacts::artifact_with_ext("bin")?;
    ensure!(!apps.is_empty(), "No generated app images found");

    // Hardcoded: the sdk/apps workspace root is always two levels below the
    // trezor-firmware repo root (<repo>/sdk/apps).
    let repo_root = helpers::root_dir()?
        .parent()
        .and_then(Path::parent)
        .context("Failed to resolve repo root from the sdk/apps workspace root")?
        .to_path_buf();

    let mut cmd = Command::new("uv");
    cmd.arg("run")
        .arg(repo_root.join(APPTREE_TOOL))
        .arg("build-dev-bundle")
        .args(&apps)
        .current_dir(&repo_root);

    println!("app-tool: Building app proofs and dev-signed RootPacket");
    println!("\x1b[1;90m{}\x1b[0m", helpers::command_args_to_string(&cmd));

    let status = cmd.status().context("Failed to spawn `extapp_tool.py`")?;
    ensure!(
        status.success(),
        "`extapp_tool.py build-dev-bundle` failed with status: {status}"
    );

    Ok(())
}
