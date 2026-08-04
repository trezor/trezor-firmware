//! Generates `trezorlib`-style Python message classes from an app's `.proto`
//! files, for use by its device tests (`tests/generated/messages.py`).
//!
//! The `.proto` files are compiled in-process with `protox`, so no `protoc`
//! binary is needed.

mod model;
mod render;

use crate::{args::GenPyArgs, helpers};
use anyhow::{Context, Result, ensure};
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
/// from the `.proto` files in its `protob/` directory.
pub fn generate(package_dir: &Path) -> Result<()> {
    let proto_dir = package_dir.join(PROTOB_DIR);
    let proto_files = collect_proto_files(&proto_dir)?;

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

/// Returns the `.proto` file names in `proto_dir`, sorted for deterministic
/// output. Names are relative to `proto_dir`, which is the include root.
fn collect_proto_files(proto_dir: &Path) -> Result<Vec<PathBuf>> {
    let mut files = Vec::new();
    for entry in fs::read_dir(proto_dir)
        .with_context(|| format!("Failed to read {}", proto_dir.display()))?
    {
        let path = entry?.path();
        if path.extension().is_some_and(|ext| ext == "proto") {
            files.push(PathBuf::from(path.file_name().expect("file has a name")));
        }
    }
    ensure!(
        !files.is_empty(),
        "no .proto files found in {}",
        proto_dir.display()
    );
    files.sort();
    Ok(files)
}
