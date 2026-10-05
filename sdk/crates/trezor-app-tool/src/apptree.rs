//! Steps that run after a successful `cargo build`: publishing the built
//! ELF/bin as artifacts (see [`crate::helpers::artifacts_dir`]) and
//! generating the Merkle proofs and RootPacket needed to load them.

use crate::{artifacts, helpers};
use anyhow::{Context, Ok, Result, ensure};
use std::{path::Path, process::Command};

/// Python tool building the app Merkle proofs and the RootPacket(s), relative to the repo root.
const APPTREE_TOOL: &str = "core/tools/trezor_core_tools/apptree_tool.py";

/// Generates application tree (Merkle proofs and RootPacket) for all
/// application in artifacts directory.
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

    let artifacts_serialized_dir = helpers::artifacts_serialized_dir()?;

    let mut cmd = Command::new("uv");
    cmd.arg("run")
        .arg(repo_root.join(APPTREE_TOOL))
        .arg("post-build")
        .args(&apps)
        .arg("--out-dir")
        .arg(artifacts_serialized_dir)
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
