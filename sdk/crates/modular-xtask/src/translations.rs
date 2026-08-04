use std::{collections::BTreeMap, fs};

use anyhow::{Result, bail, ensure};
use serde_json::Value;

use crate::{args::ProjectArgs, helpers};

enum FileStatus {
    Ok,
    StyleError,
    FatalError,
}

pub fn run(args: &ProjectArgs, check_only: bool) -> Result<()> {
    let mut project_dir = helpers::root_dir()?;
    if helpers::is_workspace()? {
        ensure!(
            !args.project.is_empty(),
            "Project name must be specified when running py-style in a workspace"
        );
        project_dir = project_dir.join(&args.project);
    }
    let translation_dir = project_dir.join("translations");

    let mut errors: Vec<std::path::PathBuf> = Vec::new();

    for entry in fs::read_dir(&translation_dir)? {
        let entry = entry?;
        let path = entry.path();

        if path.extension().and_then(|e| e.to_str()) != Some("json") {
            continue;
        }

        let status = process_file(&path, check_only)?;
        if !matches!(status, FileStatus::Ok) {
            errors.push(path);
        }
    }

    if !errors.is_empty() {
        bail!("\n[FAIL] Some files are invalid or not properly formatted.");
    }

    Ok(())
}

fn process_file(path: &std::path::Path, check_only: bool) -> Result<FileStatus> {
    let original_text = fs::read_to_string(path)?;

    let value: Value = match serde_json::from_str(&original_text) {
        Ok(v) => v,
        Err(e) => {
            println!("[INVALID] {}: {}", path.display(), e);
            return Ok(FileStatus::FatalError);
        }
    };

    let sorted = sort_keys_recursive(value);
    let formatted = serde_json::to_string_pretty(&sorted)? + "\n";

    if original_text == formatted {
        return Ok(FileStatus::Ok);
    }

    if check_only {
        println!("[UNFORMATTED] {}", path.display());
        Ok(FileStatus::StyleError)
    } else {
        println!("[FORMATTING] {}", path.display());
        fs::write(path, formatted.as_bytes())?;
        Ok(FileStatus::Ok)
    }
}

fn sort_keys_recursive(value: Value) -> Value {
    match value {
        Value::Object(map) => {
            let sorted: BTreeMap<String, Value> = map
                .into_iter()
                .map(|(k, v)| (k, sort_keys_recursive(v)))
                .collect();
            Value::Object(sorted.into_iter().collect())
        }
        Value::Array(arr) => Value::Array(arr.into_iter().map(sort_keys_recursive).collect()),
        other => other,
    }
}
