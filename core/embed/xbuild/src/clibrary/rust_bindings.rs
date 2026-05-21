use bindgen;
use color_eyre::{Result, eyre::WrapErr};

use super::CLibrary;

use crate::helpers::{links_name, path_from_env};

impl CLibrary {
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
        if let Some(builder) = self.builder.take() {
            let mut attrs = self.get_merged_attrs();

            if use_cc_includes {
                attrs
                    .import_cc_compiler_includes()
                    .expect("Failed to import C compiler includes");
            }

            // bindgen uses clang to parse headers, while GCC compiles the C code.
            // Remove GCC-only flags that make clang fail.
            attrs.remove_flag("-mcmse");
            attrs.remove_flag("-fsingle-precision-constant");

            let out_file = path_from_env("OUT_DIR")?.join(links_name()? + ".rs");
            let tmp_out_file = out_file.with_extension("rs.tmp");

            builder
                .clang_args(attrs.to_compiler_args())
                // Customize the standard types.
                .use_core()
                .ctypes_prefix("cty")
                .size_t_is_usize(true)
                // Disable the layout tests. They spew out a lot of code-style bindings, and are not too
                // relevant for our use-case.
                .layout_tests(false)
                // Tell cargo to invalidate the built crate whenever any of the
                // included header files change.
                .parse_callbacks(Box::new(bindgen::CargoCallbacks::new()))
                .generate()
                .context("Unable to generate bindings")?
                .write_to_file(&tmp_out_file)
                .context(format!(
                    "Unable to write bindings to {}",
                    tmp_out_file.display()
                ))?;

            // Bindgen writes the output file even if the content is unchanged,
            // which causes unnecessary recompilations. To avoid this, we
            // compare the generated file with the existing one and only replace
            // it if there are changes.
            replace_if_different(&tmp_out_file, &out_file)?;
        }
        Ok(())
    }
}

fn replace_if_different(src: &std::path::Path, dst: &std::path::Path) -> Result<()> {
    if dst.exists() {
        let src_content = std::fs::read(src).context("Failed to read temporary bindings file")?;
        let dst_content = std::fs::read(dst).context("Failed to read existing bindings file")?;

        if src_content == dst_content {
            // Files are identical, no need to replace
            // Clean up the temporary file
            std::fs::remove_file(src).context("Failed to remove temporary bindings file")?;
            return Ok(());
        }
    }

    std::fs::rename(src, dst).context("Failed to replace bindings file")?;
    Ok(())
}
