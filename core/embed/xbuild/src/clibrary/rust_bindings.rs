use std::path::PathBuf;

use bindgen;
use color_eyre::Result;
use color_eyre::eyre::WrapErr;

use super::CLibrary;
use crate::helpers::{links_name, path_from_env};

impl CLibrary {
    /// Sets the output path for the generated Rust bindings.
    /// If not set, it defaults to `OUT_DIR/links_name.rs`.
    pub fn set_rust_bindings_output(&mut self, output_path: PathBuf) {
        self.builder_output = Some(output_path);
    }

    /// Configures the bindgen builder with the provided function, allowing
    /// users to customize the generation of Rust bindings. The function takes
    /// a `bindgen::Builder` as input and returns a modified builder.
    pub fn add_rust_bindings(
        &mut self,
        func: impl FnOnce(bindgen::Builder) -> Result<bindgen::Builder>,
    ) -> Result<()> {
        let builder = self.builder.take().unwrap_or_default();
        self.builder = Some(func(builder)?);
        Ok(())
    }

    /// Generates rust bininding (a .rs file) from the configured builder and
    /// writes it to the OUT_DIR.
    pub(crate) fn generate_rust_bindings(&mut self, use_cc_includes: bool) -> Result<()> {
        let out_file = path_from_env("OUT_DIR")?.join(links_name()? + ".rs");
        let content = if let Some(builder) = self.builder.take() {
            let mut attrs = self.get_merged_attrs();

            if use_cc_includes {
                attrs
                    .import_cc_compiler_includes()
                    .context("Failed to import C compiler includes")?;
            }

            // bindgen uses clang to parse headers, while GCC compiles the C code.
            // Remove GCC-only flags that make clang fail.
            attrs.remove_flag("-mcmse");
            attrs.remove_flag("-fsingle-precision-constant");

            let out_file = self
                .builder_output
                .clone()
                .unwrap_or(path_from_env("OUT_DIR")?.join(links_name()? + ".rs"));

            let tmp_out_file = out_file.with_extension("rs.tmp");

            let mut content = Vec::<u8>::new();
            builder
                .clang_args(attrs.to_compiler_args())
                // Customize the standard types.
                .use_core()
                .ctypes_prefix("cty")
                .size_t_is_usize(true)
                // Disable the layout tests. They spew out a lot of code-style bindings, and are not
                // too relevant for our use-case.
                .layout_tests(false)
                // Tell cargo to invalidate the built crate whenever any of the
                // included header files change.
                .parse_callbacks(Box::new(bindgen::CargoCallbacks::new()))
                .generate()
                .context("Unable to generate bindings")?
                .write(Box::new(&mut content))
                .context(format!(
                    "Unable to write bindings to {}",
                    tmp_out_file.display()
                ))?;

            content
        } else {
            // just empty file
            Vec::<u8>::new()
        };

        // Bindgen writes the output file even if the content is unchanged,
        // which causes unnecessary recompilations. To avoid this, we
        // compare the generated file with the existing one and only replace
        // it if there are changes.
        maybe_replace(content, &out_file)?;
        Ok(())
    }
}

fn maybe_replace(src_content: Vec<u8>, dst: &std::path::Path) -> Result<()> {
    let should_write = if !dst.exists() {
        true
    } else {
        let dst_content = std::fs::read(dst).context("Failed to read existing bindings file")?;
        src_content != dst_content
    };

    if !should_write {
        // Files are identical, no need to replace
        return Ok(());
    }

    // short path: new content is empty
    if src_content.is_empty() {
        std::fs::write(dst, src_content).context("Failed to write empty bindings file")?;
        return Ok(());
    }

    // normal path: write new content into a temp file first
    let out_temp_file = dst.with_extension("rs.tmp");
    match std::fs::write(&out_temp_file, src_content) {
        Ok(_) => {
            std::fs::rename(&out_temp_file, dst).context("Failed to replace bindings file")?;
            Ok(())
        }
        Err(e) => {
            // try to clean up the temp file, ignore errorrs
            std::fs::remove_file(out_temp_file).ok();
            // bail out via the original error
            Err::<(), std::io::Error>(e.into()).context("Failed to write temp bindings file")
        }
    }
}
