use anyhow::{Context, Result, bail};
use serde::Deserialize;
use serde_json::Value;
use std::collections::BTreeMap;
use std::{env, fs, path::PathBuf};

use crate::helpers::Language;

#[derive(Debug, Deserialize)]
struct TranslationFile {
    translations: BTreeMap<String, Value>,
}

/// Builds the translation macros for the current language.
///
/// Reads the translation file for the current language and generates a Rust
/// macro for easy access to the translations.
pub fn build_translations() -> Result<()> {
    let language = Language::from_env();
    let json_path = language.file();

    println!("cargo:rerun-if-changed={}", json_path);

    let json = fs::read_to_string(&json_path)
        .with_context(|| format!("Could not read translation file: {}", json_path))?;

    let out = generate_macro(&json)?;

    let out_dir =
        PathBuf::from(env::var("OUT_DIR").context("OUT_DIR environment variable not set")?);
    let out_file = out_dir.join("translations.rs");

    fs::write(&out_file, out).with_context(|| format!("Failed to write {}", out_file.display()))?;

    Ok(())
}

/// Generates the `tr!` macro source from the translation JSON.
///
/// Every translation must be a plain string; one text serves all devices,
/// there are no layout-specific variants.
fn generate_macro(json: &str) -> Result<String> {
    let file: TranslationFile =
        serde_json::from_str(json).context("Failed to parse translation file")?;

    let mut out = String::new();
    out.push_str("#[macro_export]\n");
    out.push_str("macro_rules! tr {\n");

    for (key, value) in &file.translations {
        let Value::String(text) = value else {
            bail!("Translation `{key}` must be a string, not {value}");
        };
        out.push_str(&format!("    ({:?}) => {{ {:?} }};\n", key, text));
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

    fn generate(translations: &str) -> Result<String> {
        generate_macro(&format!(r#"{{"translations": {translations}}}"#))
    }

    fn arms(out: &str) -> Vec<&str> {
        out.lines().filter(|l| l.starts_with("    (\"")).collect()
    }

    #[test]
    fn plain_string_entry() {
        let out = generate(r#"{"buttons__cancel": "Cancel"}"#).unwrap();
        assert_eq!(arms(&out), [r#"    ("buttons__cancel") => { "Cancel" };"#]);
    }

    #[test]
    fn non_string_values_are_an_error() {
        // e.g. a layout-specific object, which is not supported
        for value in [
            r#"{"Delizia": "Short", "Eckhart": "Long"}"#,
            "1",
            "null",
            r#"["x"]"#,
        ] {
            let error = generate(&format!(r#"{{"k": {value}, "e": "ok"}}"#)).unwrap_err();
            assert!(error.to_string().contains("`k` must be a string"));
        }
    }

    #[test]
    fn arms_are_sorted_by_key() {
        let json = r#"{"z": "1", "a": "2", "m": "3"}"#;
        let out = generate(json).unwrap();
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
            arms(&generate(json).unwrap()),
            [r#"    ("k") => { "Say \"hi\"\nPříliš žluťoučký kůň" };"#]
        );
    }

    #[test]
    fn macro_skeleton() {
        let out = generate("{}").unwrap();
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
        assert!(generate_macro("not json").is_err());
        assert!(generate_macro(r#"{"header": {}}"#).is_err());
    }
}
