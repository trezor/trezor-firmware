use anyhow::{Context, Result, ensure};
use std::process;

use crate::helpers;

pub fn update_templates() -> Result<()> {
    println!("Updating templates...");

    let tools_dir = helpers::workspace_dir()?.join("../tools");
    let script = tools_dir.join("build_templates");

    let status = process::Command::new(script)
        .current_dir(tools_dir)
        .status()
        .context("Failed to spawn build-templates script")?;

    ensure!(
        status.success(),
        "build-templates script failed with status: {}",
        status
    );

    Ok(())
}

pub fn update_translations() -> Result<()> {
    println!("Updating translations...");

    let translations_dir = helpers::workspace_dir()?.join("../translations");

    let script = translations_dir.join("order.py");
    let status = process::Command::new("python3")
        .arg(script)
        .status()
        .context("Failed to spawn order.py script")?;

    ensure!(
        status.success(),
        "order.py script failed with status: {}",
        status
    );

    let script = translations_dir.join("cli.py");
    let status = process::Command::new("python3")
        .arg(script)
        .arg("gen")
        .status()
        .context("Failed to spawn cli.py script")?;

    ensure!(
        status.success(),
        "cli.py script failed with status: {}",
        status
    );

    Ok(())
}
