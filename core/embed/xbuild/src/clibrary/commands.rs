use color_eyre::{Result, eyre::WrapErr};

use super::CLibrary;

use crate::helpers::{derive_output_path, join_paths_lexically, links_name, path_from_env};

/// Path to the partial compile_commands.json fragment within OUT_DIR.
const COMPILE_COMMANDS_FILE: &str = "compile_commands.json";

impl CLibrary {
    /// Generates a partial `compile_commands.json` fragment for this library.
    ///
    /// Each entry follows the clang compilation database format with
    /// `directory`, `file`, and `arguments` fields. The fragment is written
    /// to `OUT_DIR/compile_commands.json` and its path is exported via
    /// Cargo metadata so the top-level crate can merge all fragments.
    pub fn generate_compile_commands(&self) -> Result<()> {
        let out_dir = path_from_env("OUT_DIR")?;
        let base_dir = path_from_env("CARGO_MANIFEST_DIR")?;
        let attrs = self.get_merged_attrs();
        let tool = attrs.get_configured_compiler();

        let entries: Vec<serde_json::Value> = self
            .get_sources()
            .into_iter()
            .filter(|entry| {
                matches!(
                    entry.path.extension().and_then(|e| e.to_str()),
                    Some("c" | "cpp" | "cc" | "S" | "s")
                )
            })
            .map(|entry| {
                let input = join_paths_lexically(&base_dir, &entry.path);
                let output = derive_output_path(&base_dir, &entry.path, &out_dir, "o");

                // Reconstruct the full compiler command line
                let mut arguments: Vec<String> = vec![tool.path().to_string_lossy().into()];
                // Add tool-level flags configured by the `cc` crate
                arguments.extend(tool.args().iter().map(|a| a.to_string_lossy().into()));
                // Add per-source overrides if any
                if let Some(per_source) = &entry.attrs {
                    arguments.extend(per_source.to_compiler_args());
                }
                arguments.extend([
                    "-c".into(),
                    "-o".into(),
                    output.to_string_lossy().into(),
                    input.to_string_lossy().into(),
                ]);

                serde_json::json!({
                    "directory": base_dir.to_string_lossy(),
                    "file": input.to_string_lossy(),
                    "arguments": arguments,
                })
            })
            .collect();

        let output_path = out_dir.join(COMPILE_COMMANDS_FILE);
        std::fs::write(&output_path, serde_json::to_string_pretty(&entries)?)
            .with_context(|| format!("Failed to write {}", output_path.display()))?;

        // Export path to partial compile_commands.json
        println!(
            "cargo::metadata=public_c_compile_commands={}",
            output_path.display()
        );

        Ok(())
    }

    /// Merges partial `compile_commands.json` fragments from all dependency
    /// libraries and the current crate into a single file in the target
    /// directory.
    pub fn merge_compile_commands(&self) -> Result<()> {
        use crate::helpers::library_metadata;

        let mut all_entries: Vec<serde_json::Value> = Vec::new();

        // Collect fragments from dependency libraries
        for dep_lib in self.get_libs() {
            if let Ok(path) = library_metadata(dep_lib, "COMPILE_COMMANDS") {
                if let Ok(content) = std::fs::read_to_string(&path) {
                    if let Ok(entries) = serde_json::from_str::<Vec<serde_json::Value>>(&content) {
                        all_entries.extend(entries);
                    }
                }
            }
        }

        // Add this crate's own fragment
        let out_dir = path_from_env("OUT_DIR")?;
        let own_path = out_dir.join("compile_commands.json");
        if own_path.exists() {
            let content = std::fs::read_to_string(&own_path)?;
            let entries: Vec<serde_json::Value> = serde_json::from_str(&content)?;
            all_entries.extend(entries);
        }

        // Write merged compile_commands.json next to the final binary
        let name = links_name()?;
        let target_path = out_dir.join(format!("../../../{name}.cc.json"));
        std::fs::write(&target_path, serde_json::to_string_pretty(&all_entries)?)?;

        Ok(())
    }
}
