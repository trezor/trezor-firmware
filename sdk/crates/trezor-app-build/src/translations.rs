use anyhow::{Context, Result};
use serde::Deserialize;
use serde_json::Value;
use std::collections::BTreeMap;
use std::{env, fs, path::PathBuf};

use crate::helpers::{Language, Model};

#[derive(Debug, Deserialize)]
struct TranslationFile {
    translations: BTreeMap<String, Value>,
}

/// Builds the translation macros for the current language and model layout.
///
/// Reads the translation file for the current language and model layout,
/// resolves the translations, and generates a Rust macro for easy access to the translations.
pub fn build_translations() -> Result<()> {
    let language = Language::from_env();
    let model = Model::from_env();
    let layout = model.layout();
    let json_path = language.file();

    println!("cargo:rerun-if-changed={}", json_path);

    let json = fs::read_to_string(&json_path)
        .with_context(|| format!("Could not read translation file: {}", json_path))?;

    let out = generate_macro(&json, layout)?;

    let out_dir =
        PathBuf::from(env::var("OUT_DIR").context("OUT_DIR environment variable not set")?);
    let out_file = out_dir.join("translations.rs");

    fs::write(&out_file, out).with_context(|| format!("Failed to write {}", out_file.display()))?;

    Ok(())
}

/// Generates the `tr!` macro source from the translation JSON for the given layout.
fn generate_macro(json: &str, layout: &str) -> Result<String> {
    let file: TranslationFile =
        serde_json::from_str(json).context("Failed to parse translation file")?;

    fn resolve_translation<'a>(value: &'a Value, layout: &str) -> Option<&'a str> {
        match value {
            Value::String(s) => Some(s.as_str()),
            Value::Object(map) => map
                .get(layout)
                .or_else(|| map.values().next())
                .and_then(|v| v.as_str()),
            _ => None,
        }
    }

    let mut out = String::new();
    out.push_str("#[macro_export]\n");
    out.push_str("macro_rules! tr {\n");

    for (key, value) in &file.translations {
        if let Some(resolved) = resolve_translation(value, layout) {
            out.push_str(&format!("    ({:?}) => {{ {:?} }};\n", key, resolved));
        }
    }

    out.push_str("    ($key:literal) => {\n");
    out.push_str("        compile_error!(\"unknown translation key\")\n");
    out.push_str("    };\n");
    out.push_str("}\n");

    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn generate(translations: &str, layout: &str) -> String {
        generate_macro(&format!(r#"{{"translations": {translations}}}"#), layout).unwrap()
    }

    fn arms(out: &str) -> Vec<&str> {
        out.lines().filter(|l| l.starts_with("    (\"")).collect()
    }

    #[test]
    fn plain_string_entry() {
        let out = generate(r#"{"buttons__cancel": "Cancel"}"#, "Eckhart");
        assert_eq!(arms(&out), [r#"    ("buttons__cancel") => { "Cancel" };"#]);
    }

    #[test]
    fn layout_object_picks_requested_layout() {
        let json = r#"{"k": {"Delizia": "Short", "Eckhart": "Long"}}"#;
        assert_eq!(
            arms(&generate(json, "Eckhart")),
            [r#"    ("k") => { "Long" };"#]
        );
        assert_eq!(
            arms(&generate(json, "Delizia")),
            [r#"    ("k") => { "Short" };"#]
        );
    }

    #[test]
    fn missing_layout_falls_back_to_first_value() {
        // Documents current behavior: serde_json maps are ordered by key,
        // so the alphabetically first layout wins.
        let json = r#"{"k": {"Delizia": "D", "Bolt": "B"}}"#;
        assert_eq!(
            arms(&generate(json, "Eckhart")),
            [r#"    ("k") => { "B" };"#]
        );
    }

    #[test]
    fn non_string_values_are_skipped() {
        let json = r#"{"a": 1, "b": null, "c": ["x"], "d": {"Eckhart": 2}, "e": "ok"}"#;
        assert_eq!(
            arms(&generate(json, "Eckhart")),
            [r#"    ("e") => { "ok" };"#]
        );
    }

    #[test]
    fn arms_are_sorted_by_key() {
        let json = r#"{"z": "1", "a": "2", "m": "3"}"#;
        let out = generate(json, "Eckhart");
        let keys: Vec<_> = arms(&out)
            .iter()
            .map(|l| l.split('"').nth(1).unwrap())
            .collect();
        assert_eq!(keys, ["a", "m", "z"]);
    }

    #[test]
    fn special_characters_are_escaped() {
        let json = r#"{"k": "Say \"hi\"\nPříliš žluťoučký kůň"}"#;
        assert_eq!(
            arms(&generate(json, "Eckhart")),
            [r#"    ("k") => { "Say \"hi\"\nPříliš žluťoučký kůň" };"#]
        );
    }

    #[test]
    fn macro_skeleton() {
        let out = generate("{}", "Eckhart");
        assert_eq!(
            out,
            "#[macro_export]\n\
             macro_rules! tr {\n\
             \x20   ($key:literal) => {\n\
             \x20       compile_error!(\"unknown translation key\")\n\
             \x20   };\n\
             }\n"
        );
    }

    #[test]
    fn invalid_input_is_an_error() {
        assert!(generate_macro("not json", "Eckhart").is_err());
        assert!(generate_macro(r#"{"header": {}}"#, "Eckhart").is_err());
    }
}
