use std::path::{Path, PathBuf};

use color_eyre::{
    Result,
    eyre::{WrapErr, ensure},
};

use crate::helpers::{join_paths_lexically, library_metadata, relative_to_manifest};

/// Attributes for configuring C compilation.
///
/// This struct holds compiler flags, defines, and include paths for use when compiling C code.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct CompileAttrs {
    /// Compiler flags (e.g. `-O3`, `-fno-exceptions`, etc.)
    pub flags: Vec<String>,
    /// Defines, as (name, optional value) pairs. For example,
    /// `("FOO", Some("1"))` represents `-DFOO=1`, while
    /// `("BAR", None)` represents `-DBAR`.
    pub defines: Vec<(String, Option<String>)>,
    /// Include paths to be added with `-I` when compiling C code.
    pub includes: Vec<PathBuf>,
}

impl CompileAttrs {
    /// Creates a new `CompileAttrs` with default values.
    pub fn new() -> Self {
        Self::default()
    }

    /// Appends a compiler flag and returns the modified `CompileAttrs` for chaining.
    ///
    /// # Parameters
    /// - `flag`: The compiler flag to add (e.g., `-O2`).
    ///
    /// # Returns
    ///
    /// The modified `CompileAttrs` with the new flag added.
    pub fn with_flag(mut self, flag: &str) -> Self {
        self.add_flag(flag);
        self
    }

    /// Appends an include path and returns the modified `CompileAttrs` for chaining.
    ///
    /// # Parameters
    /// - `path`: The include path to add.
    ///
    /// # Returns
    ///
    /// The modified `CompileAttrs` with the new include path added.
    pub fn with_include(mut self, path: impl AsRef<Path>) -> Self {
        self.add_include(path);
        self
    }

    /// Adds a compiler flag.
    ///
    /// # Parameters
    /// - `flag`: The compiler flag to add (e.g., `-O2`).
    pub fn add_flag(&mut self, flag: &str) {
        self.flags.push(flag.to_string());
    }

    /// Removes a compiler flag.
    ///
    /// # Parameters
    /// - `flag`: The compiler flag to remove (e.g., `-O2`).
    pub fn remove_flag(&mut self, flag: &str) {
        self.flags.retain(|f| f != flag);
    }

    /// Adds a preprocessor define, with an optional value, if not already present.
    ///
    /// # Parameters
    /// - `name`: The name of the define (e.g., `FOO`).
    /// - `value`: The value of the define, or `None` for a value-less define.
    pub fn add_define(&mut self, name: &str, value: Option<&str>) {
        let pair = (name.to_string(), value.map(|v| v.to_string()));
        if !self.defines.contains(&pair) {
            self.defines.push(pair);
        }
    }

    /// Adds an include path, making it relative to the Cargo manifest if possible, if not already present.
    ///
    /// # Parameters
    /// - `path`: The include path to add.
    pub fn add_include(&mut self, path: impl AsRef<Path>) {
        let path = relative_to_manifest(path);
        if !self.includes.contains(&path) {
            self.includes.push(path);
        }
    }

    /// Merges another `CompileAttrs` into this one, combining their flags, defines, and includes.
    ///
    /// Duplicate flags are allowed, but defines and includes are deduplicated.
    ///
    /// # Parameters
    /// - `other`: The `CompileAttrs` to merge from.
    ///
    /// # Returns
    ///
    /// A new `CompileAttrs` containing the merged attributes.
    pub fn merge(mut self, other: &CompileAttrs) -> Self {
        for flag in &other.flags {
            // Duplicate flags are allowed
            // (the order of flags may matter)
            self.flags.push(flag.clone());
        }

        for define in &other.defines {
            if !self.defines.contains(define) {
                self.defines.push(define.clone());
            }
        }

        for include in &other.includes {
            if !self.includes.contains(include) {
                self.includes.push(include.clone());
            }
        }
        self
    }

    /// Configures and returns a `cc::Tool` based on the current compile attributes.
    ///
    /// This can be used to compile C code with the same settings.
    ///
    /// # Returns
    ///
    /// A configured `cc::Tool` instance.
    pub fn get_configured_compiler(&self) -> cc::Tool {
        let mut build = cc::Build::new();
        build.warnings(false);

        for flag in &self.flags {
            build.flag(flag);
        }

        for dir in &self.includes {
            build.include(dir);
        }

        for def in &self.defines {
            build.define(&def.0, def.1.as_deref());
        }

        build.get_compiler()
    }

    /// Exports the compile attributes as Cargo metadata for use in dependent crates.
    ///
    /// This function prints metadata for includes, defines, and flags to stdout for Cargo to consume.
    ///
    /// # Errors
    ///
    /// Returns an error if the manifest directory is not set or if path conversion fails.
    pub fn export_as_metadata(&self) -> Result<()> {
        let manifest_dir = std::env::var("CARGO_MANIFEST_DIR")
            .context("CARGO_MANIFEST_DIR is required but not set")?;

        let includes = self
            .includes
            .iter()
            .map(|dir| {
                if dir.is_absolute() {
                    dir.to_string_lossy().to_string()
                } else {
                    join_paths_lexically(&manifest_dir, dir)
                        .to_string_lossy()
                        .to_string()
                }
            })
            .collect::<Vec<_>>()
            .join(";");
        println!("cargo::metadata=public_c_includes={}", includes);

        let defines = self
            .defines
            .iter()
            .map(|(name, value)| {
                if let Some(val) = value {
                    format!("{}={}", name, val)
                } else {
                    name.clone()
                }
            })
            .collect::<Vec<_>>()
            .join(";");
        println!("cargo::metadata=public_c_defines={}", defines);

        let flags = self.flags.join(";");
        println!("cargo::metadata=public_c_flags={}", flags);

        Ok(())
    }

    /// Imports the specified crate's public C compiler attributes from Cargo metadata.
    ///
    /// # Parameters
    /// - `library`: The name of the library whose metadata to import.
    pub fn import_library_metadata(&mut self, lib_name: &str) -> Result<()> {
        let includes = library_metadata(lib_name, "INCLUDES")?;

        for dir in includes.split(';').filter(|path| !path.is_empty()) {
            self.add_include(dir);
        }

        let defines = library_metadata(lib_name, "DEFINES")?;

        for def in defines.split(';').filter(|def| !def.is_empty()) {
            let parts: Vec<&str> = def.splitn(2, '=').collect();
            let name = parts[0];
            let value = if parts.len() > 1 {
                Some(parts[1])
            } else {
                None
            };
            self.add_define(name, value);
        }

        let flags = library_metadata(lib_name, "FLAGS")?;

        for flag in flags.split(';').filter(|flag| !flag.is_empty()) {
            self.add_flag(flag);
        }

        Ok(())
    }

    /// Imports include paths from the system C compiler.
    ///
    /// # Errors
    ///
    /// Returns an error if the compiler cannot be executed or its output cannot be parsed.
    pub fn import_cc_compiler_includes(&mut self) -> Result<()> {
        let compiler = cc::Build::new().get_compiler();
        let cc_output = compiler
            .to_command()
            .arg("-E")
            .arg("-Wp,-v")
            .arg("-")
            .output()
            .with_context(|| format!("Failed to execute C compiler {:?}", compiler))?;

        ensure!(
            cc_output.status.success(),
            "C compiler failed while probing include paths with status {}",
            cc_output.status
        );

        let compiler_output = String::from_utf8(cc_output.stderr)
            .with_context(|| format!("C compiler {:?} returned invalid UTF-8", compiler))?;

        compiler_output
            .lines()
            .skip_while(|s| !s.contains("search starts here:"))
            .take_while(|s| !s.contains("End of search list."))
            .filter(|s| s.starts_with(' '))
            .for_each(|s| self.add_include(s.trim()));

        Ok(())
    }

    /// Returns a list of arguments that represent the compile attributes, suitable for passing to a C compiler.
    ///
    /// # Returns
    ///
    /// A vector of strings representing compiler arguments.
    pub fn to_compiler_args(&self) -> Vec<String> {
        let mut args = Vec::new();

        for flag in &self.flags {
            args.push(flag.clone());
        }

        for dir in &self.includes {
            args.push(format!("-I{}", dir.to_string_lossy()));
        }

        for (name, value) in &self.defines {
            match value {
                Some(value) => {
                    args.push(format!("-D{}={}", name, value));
                }
                None => {
                    args.push(format!("-D{}", name));
                }
            }
        }

        args
    }
}
