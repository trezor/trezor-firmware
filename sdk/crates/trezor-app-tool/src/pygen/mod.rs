//! Generates `trezorlib`-style Python message classes from an app's `.proto`
//! files, for use by its device tests (`tests/generated/messages.py`).
//!
//! The `.proto` files are compiled in-process with `protox`, so no `protoc`
//! binary is needed.

mod model;
mod render;

use crate::{args::GenPyArgs, helpers};
use anyhow::{Context, Result};
use std::{
    fs,
    path::{Path, PathBuf},
};

/// Directory (relative to the app package) holding the `.proto` sources.
const PROTOB_DIR: &str = "protob";
/// Output file (relative to the app package).
const OUT_FILE: &str = "tests/generated/messages.py";

/// `app-tool gen-py`: generates the Python definitions for the selected apps.
pub fn generate_packages(args: GenPyArgs) -> Result<()> {
    for package in helpers::selected_packages(&args.package)? {
        generate(helpers::package_dir(&package)?)?;
    }
    Ok(())
}

/// Generates `tests/generated/messages.py` for the app at `package_dir`
/// from the `.proto` files in its `protob/` directory; an app without any is
/// skipped.
pub fn generate(package_dir: &Path) -> Result<()> {
    let proto_dir = package_dir.join(PROTOB_DIR);
    let proto_files = collect_proto_files(&proto_dir)?;
    if proto_files.is_empty() {
        println!(
            "app-tool: No .proto files in {}, skipping",
            proto_dir.display()
        );
        return Ok(());
    }

    let descriptors = protox::compile(&proto_files, [&proto_dir]).with_context(|| {
        format!(
            "Failed to compile protobuf files in {}",
            proto_dir.display()
        )
    })?;
    let defs = model::Definitions::from_descriptors(&descriptors)?;
    let python = render::render(&defs);

    let out_file = package_dir.join(OUT_FILE);
    let out_dir = out_file.parent().expect("OUT_FILE has a parent");
    fs::create_dir_all(out_dir)
        .with_context(|| format!("Failed to create {}", out_dir.display()))?;
    let init = out_dir.join("__init__.py");
    if !init.exists() {
        fs::write(&init, "").with_context(|| format!("Failed to write {}", init.display()))?;
    }
    fs::write(&out_file, python)
        .with_context(|| format!("Failed to write {}", out_file.display()))?;

    println!("app-tool: Generated {}", out_file.display());
    Ok(())
}

/// Returns the `.proto` file names in `proto_dir` (none if it does not
/// exist), sorted for deterministic output. Names are relative to
/// `proto_dir`, which is the include root.
fn collect_proto_files(proto_dir: &Path) -> Result<Vec<PathBuf>> {
    let mut files = Vec::new();
    if !proto_dir.exists() {
        return Ok(files);
    }
    for entry in fs::read_dir(proto_dir)
        .with_context(|| format!("Failed to read {}", proto_dir.display()))?
    {
        let path = entry?.path();
        if path.extension().is_some_and(|ext| ext == "proto") {
            files.push(PathBuf::from(path.file_name().expect("file has a name")));
        }
    }
    files.sort();
    Ok(files)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn generate_skips_apps_without_protos() {
        let root = std::env::temp_dir().join(format!("app-tool-pygen-{}", std::process::id()));
        let _ = fs::remove_dir_all(&root);
        // no `protob/`
        fs::create_dir_all(&root).unwrap();
        generate(&root).unwrap();
        // empty `protob/`
        fs::create_dir_all(root.join(PROTOB_DIR)).unwrap();
        generate(&root).unwrap();
        assert!(!root.join(OUT_FILE).exists());
        let _ = fs::remove_dir_all(&root);
    }
}
