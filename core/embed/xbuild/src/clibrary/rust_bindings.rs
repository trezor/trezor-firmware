use bindgen;
use color_eyre::Result;
use color_eyre::eyre::WrapErr;

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
                .context("Unable to write bindings to a buffer")?;

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

    if should_write {
        std::fs::write(dst, src_content).context("Failed to write empty bindings file")?;
    }
    Ok(())
}
