//! Formatting for an app's `translations/*.json` files: recursively sorts
//! object keys and pretty-prints with a trailing newline, matching the
//! style produced by `cargo app-tool fmt`.

use std::{
    collections::BTreeMap,
    fs,
    path::{Path, PathBuf},
};

use anyhow::{Result, bail};
use serde_json::Value;

enum FileStatus {
    Ok,
    StyleError,
    FatalError,
}

/// Formats all JSON translation files in the `translations/` directory of
/// the app at `package_dir`. If `check_only` is `true`, it will only check
/// for formatting issues without modifying files.
pub fn format(package_dir: &Path, check_only: bool) -> Result<()> {
    let dir = package_dir.join("translations");
    let mut errors: Vec<PathBuf> = Vec::new();

    for entry in fs::read_dir(&dir)? {
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

fn process_file(path: &Path, check_only: bool) -> Result<FileStatus> {
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

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn sorts_top_level_keys() {
        let input = json!({"words__send": "Send", "address__confirmed": "Confirmed"});
        let sorted = sort_keys_recursive(input);
        let keys: Vec<&String> = sorted.as_object().unwrap().keys().collect();
        assert_eq!(keys, ["address__confirmed", "words__send"]);
    }

    #[test]
    fn sorts_nested_object_keys() {
        // Per-layout translations are themselves objects (e.g. {"Eckhart":
        // "...", "Delizia": "..."}), and must be sorted too.
        let input = json!({"key": {"Eckhart": "e", "Delizia": "d", "Bolt": "b"}});
        let sorted = sort_keys_recursive(input);
        let inner_keys: Vec<&String> = sorted["key"].as_object().unwrap().keys().collect();
        assert_eq!(inner_keys, ["Bolt", "Delizia", "Eckhart"]);
    }

    #[test]
    fn leaves_arrays_and_scalars_unchanged() {
        let input = json!({"b": [3, 1, 2], "a": "unchanged", "c": null});
        let sorted = sort_keys_recursive(input.clone());
        // Only object *keys* are sorted -- array element order and scalar
        // values are left exactly as they were.
        assert_eq!(sorted["b"], input["b"]);
        assert_eq!(sorted["a"], input["a"]);
        assert_eq!(sorted["c"], input["c"]);
    }

    #[test]
    fn is_idempotent() {
        let input = json!({"z": 1, "a": {"y": 2, "b": 3}});
        let once = sort_keys_recursive(input);
        let twice = sort_keys_recursive(once.clone());
        assert_eq!(once, twice);
    }
}
