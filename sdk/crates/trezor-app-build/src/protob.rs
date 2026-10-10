use anyhow::{Context, Result};
use std::{fs, path::PathBuf};

const PROTOB_DIR: &str = "protob";

/// Builds the protobuf files for the project.
///
/// This function collects all `.proto` files in the `protob` directory and compiles them using `prost_build`.
pub fn build_protobufs() -> Result<()> {
    let files = collect_protobuf_files()?;

    println!("cargo:rerun-if-changed={}", PROTOB_DIR);

    let mut config = prost_build::Config::new();
    config
        .compile_protos(&files, &[PROTOB_DIR])
        .context("Failed to compile protobuf files")?;

    Ok(())
}

fn collect_protobuf_files() -> Result<Vec<PathBuf>> {
    let mut files = fs::read_dir(PROTOB_DIR)
        .context(format!("Failed to read {} directory", PROTOB_DIR))?
        .try_fold(Vec::new(), |mut files, entry| {
            let path = entry.context("Failed to read directory entry")?.path();
            if path.extension().and_then(|s| s.to_str()) == Some("proto") {
                files.push(path);
            }
            anyhow::Ok(files)
        })?;

    // Sort for reproducible builds
    files.sort();
    Ok(files)
}
