use std::process;

use anyhow::Result;

use crate::args::AppsArgs;
use crate::helpers;

pub fn run(args: AppsArgs) -> Result<()> {
    let sdk_dir = helpers::workspace_dir()?.join("../../sdk");
    let manifest = sdk_dir.join("crates/trezor-app-tool/Cargo.toml");
    let cmd = std::process::Command::new("cargo")
        .current_dir(sdk_dir.join("apps"))
        .args(["run", "-q", "--manifest-path"])
        .arg(manifest)
        .arg("--")
        .args(&args.args)
        .status()?;

    if !cmd.success() {
        process::exit(cmd.code().unwrap_or(1));
    }

    Ok(())
}
