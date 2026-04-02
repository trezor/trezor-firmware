pub mod commands;
pub mod compile;
pub mod embed;

use std::path::{Path, PathBuf};

use color_eyre::{Result, eyre::WrapErr};

use crate::attrs::CompileAttrs;
use crate::helpers::{library_metadata, relative_to_manifest};

/// A source file entry with optional per-file compile attributes.
#[derive(Clone)]
pub struct SourceEntry {
    // Path to the source file
    pub path: PathBuf,
    // Optional per-source compile attributes that are merged
    // with the library-level attributes.
    // (Quite rarely used, but can be useful for special cases.)
    pub attrs: Option<CompileAttrs>,
}

/// A C static library built from source files with configurable compile attributes.
pub struct CLibrary {
    // List of source files to compile into the library, along with optional
    // per-source compile attributes that are merged with the
    // library-level attributes.
    sources: Vec<SourceEntry>,

    // List of precompiled object files to link into the library.
    objects: Vec<PathBuf>,

    // Compile attributes that apply to all sources in the library.
    private_attrs: CompileAttrs,

    // Compile attributes that apply to all sources in the library.
    // Public attributes are also visible to downstream crates that use
    // this library, and are automatically imported when using `import_crate`.
    public_attrs: CompileAttrs,

    // List of libraries that this library depends on, which must be linked
    // when using this library. This includes both libraries added directly
    // to this library and libraries imported from other crates.
    libs: Vec<String>,
}

impl CLibrary {
    /// Creates a new `CLibrary` instance with default attributes and no sources or libraries.
    ///
    /// # Returns
    ///
    /// A new `CLibrary`.
    pub(crate) fn new() -> Self {
        Self {
            sources: Vec::new(),
            objects: Vec::new(),
            private_attrs: CompileAttrs::default(),
            public_attrs: CompileAttrs::default(),
            libs: Vec::new(),
        }
    }

    /// Adds a single C or assembly source file to the library.
    ///
    /// # Parameters
    ///
    /// - `src`: Path to the source file, relative to the crate root or absolute.
    pub fn add_source(&mut self, src: impl AsRef<Path>) {
        self.add_source_with_attrs(src, None);
    }

    /// Adds multiple source files to the library.
    ///
    /// # Parameters
    ///
    /// - `sources`: Iterator of paths to source files, each relative to the crate root or absolute.
    pub fn add_sources<I, P>(&mut self, sources: I)
    where
        I: IntoIterator<Item = P>,
        P: AsRef<Path>,
    {
        self.add_sources_with_attrs(sources, None);
    }

    /// Adds multiple source files from a common folder.
    ///
    /// # Parameters
    ///
    /// - `folder`: Path to the folder containing the sources.
    /// - `sources`: Iterator of source file paths, each relative to the folder or absolute.
    pub fn add_sources_from_folder<I, P>(&mut self, folder: impl AsRef<Path>, sources: I)
    where
        I: IntoIterator<Item = P>,
        P: AsRef<Path>,
    {
        self.add_sources_from_folder_with_attrs(folder, sources, None);
    }

    /// Adds a single C or assembly source file with per-source compile attributes.
    ///
    /// This source will be compiled with the library-level attributes merged with the provided attributes.
    ///
    /// # Parameters
    ///
    /// - `src`: Path to the source file, relative to the crate root or absolute.
    /// - `attrs`: Optional compile attributes specific to this source file.
    pub fn add_source_with_attrs(&mut self, src: impl AsRef<Path>, attrs: Option<CompileAttrs>) {
        let src = relative_to_manifest(src);
        self.sources.push(SourceEntry {
            path: src,
            attrs: attrs.clone(),
        });
    }

    /// Adds multiple source files with specific compile attributes.
    ///
    /// All sources will be compiled with the library-level attributes merged with the provided attributes.
    ///
    /// # Parameters
    ///
    /// - `sources`: Iterator of source file paths, each relative to the crate root or absolute.
    /// - `attrs`: Optional compile attributes to apply to all sources.
    pub fn add_sources_with_attrs<I, P>(&mut self, sources: I, attrs: Option<CompileAttrs>)
    where
        I: IntoIterator<Item = P>,
        P: AsRef<Path>,
    {
        for src in sources {
            self.add_source_with_attrs(src, attrs.clone());
        }
    }

    /// Adds multiple source files from a common folder with specific compile attributes.
    ///
    /// All sources will be compiled with the library-level attributes merged with the provided attributes.
    ///
    /// # Parameters
    ///
    /// - `folder`: Path to the folder containing the sources.
    /// - `sources`: Iterator of source file paths, each relative to the folder or absolute.
    /// - `attrs`: Optional compile attributes to apply to all sources.
    pub fn add_sources_from_folder_with_attrs<I, P>(
        &mut self,
        folder: impl AsRef<Path>,
        sources: I,
        attrs: Option<CompileAttrs>,
    ) where
        I: IntoIterator<Item = P>,
        P: AsRef<Path>,
    {
        for src in sources {
            let full_path = folder.as_ref().join(src.as_ref());
            self.add_source_with_attrs(full_path, attrs.clone());
        }
    }

    /// Returns an iterator over the source entries added to the library.
    pub fn get_sources(&self) -> impl IntoIterator<Item = &SourceEntry> {
        self.sources.iter()
    }

    /// Adds a precompiled object file to be linked into the library.
    pub fn add_object(&mut self, obj: impl AsRef<Path>) {
        self.objects.push(obj.as_ref().to_path_buf());
    }

    /// Returns an iterator over the precompiled object files to be
    /// linked into the library.
    pub fn get_objects(&self) -> impl IntoIterator<Item = &PathBuf> {
        self.objects.iter()
    }

    /// Adds an include directory private to the library.
    ///
    /// # Parameters
    ///
    /// - `path`: Path to the include directory, relative to the crate root or absolute.
    pub fn add_private_include(&mut self, path: impl AsRef<Path>) {
        self.private_attrs.add_include(path);
    }

    /// Adds multiple include directories private to the library.
    ///
    /// # Parameters
    ///
    /// - `paths`: Iterator of include directory paths, each relative to the crate root or absolute.
    pub fn add_private_includes<I, P>(&mut self, paths: I)
    where
        I: IntoIterator<Item = P>,
        P: AsRef<Path>,
    {
        for path in paths {
            self.add_private_include(path);
        }
    }

    /// Adds a public include directory.
    ///
    /// Public include directories are visible to downstream crates that use this library.
    ///
    /// # Parameters
    ///
    /// - `path`: Path to the public include directory, relative to the crate root or absolute.
    pub fn add_include(&mut self, path: impl AsRef<Path>) {
        self.public_attrs.add_include(path);
    }

    /// Adds multiple public include directories.
    ///
    /// Public include directories are visible to downstream crates that use this library.
    ///
    /// # Parameters
    ///
    /// - `paths`: Iterator of public include directory paths, each relative to the crate root or absolute.
    pub fn add_includes<I, P>(&mut self, paths: I)
    where
        I: IntoIterator<Item = P>,
        P: AsRef<Path>,
    {
        for path in paths {
            self.add_include(path);
        }
    }

    /// Adds a preprocessor define private to the library.
    ///
    /// # Parameters
    ///
    /// - `name`: The name of the define (do not include `-D` or `=`).
    /// - `value`: Optional value for the define. If `None`, treated as `-DNAME`.
    pub fn add_private_define(&mut self, name: &str, value: Option<&str>) {
        self.private_attrs.add_define(name, value);
    }

    /// Adds multiple preprocessor defines private to the library.
    ///
    /// # Parameters
    ///
    /// - `defines`: Iterator of (name, optional value) tuples. Names must not include `-D` or `=`.
    pub fn add_private_defines<I, N, V>(&mut self, defines: I)
    where
        I: IntoIterator<Item = (N, Option<V>)>,
        N: AsRef<str>,
        V: AsRef<str>,
    {
        for (name, value) in defines {
            self.add_private_define(name.as_ref(), value.as_ref().map(|v| v.as_ref()));
        }
    }

    /// Adds a public preprocessor define.
    ///
    /// Public defines are visible to downstream crates that use this library.
    ///
    /// # Parameters
    ///
    /// - `name`: The name of the define (do not include `-D` or `=`).
    /// - `value`: Optional value for the define. If `None`, treated as `-DNAME`.
    pub fn add_define(&mut self, name: &str, value: Option<&str>) {
        self.public_attrs.add_define(name, value);
    }

    /// Adds multiple public preprocessor defines.
    ///
    /// Public defines are visible to downstream crates that use this library.
    ///
    /// # Parameters
    ///
    /// - `defines`: Iterator of (name, optional value) tuples. Names must not include `-D` or `=`.
    pub fn add_defines<I, N, V>(&mut self, defines: I)
    where
        I: IntoIterator<Item = (N, Option<V>)>,
        N: AsRef<str>,
        V: AsRef<str>,
    {
        for (name, value) in defines {
            self.add_define(name.as_ref(), value.as_ref().map(|v| v.as_ref()));
        }
    }

    /// Adds a compile flag private to the library.
    ///
    /// Private compile flags are not visible to downstream crates. Not for linker flags.
    ///
    /// # Parameters
    ///
    /// - `flag`: The private compile flag to add (e.g., `-O3`).
    pub fn add_private_flag(&mut self, flag: &str) {
        self.private_attrs.add_flag(flag);
    }

    /// Adds multiple compile flags private to the library.
    ///
    /// Private compile flags are not visible to downstream crates. Not for linker flags.
    ///
    /// # Parameters
    ///
    /// - `flags`: Iterator of private compile flags to add.
    pub fn add_private_flags<I, F>(&mut self, flags: I)
    where
        I: IntoIterator<Item = F>,
        F: AsRef<str>,
    {
        for flag in flags {
            self.add_private_flag(flag.as_ref());
        }
    }

    /// Adds a public compile flag.
    ///
    /// Public flags are visible to downstream crates that use this library.
    ///
    /// # Parameters
    ///
    /// - `flag`: The public compile flag to add (e.g., `-O2`).
    pub fn add_flag(&mut self, flag: &str) {
        self.public_attrs.add_flag(flag);
    }

    /// Adds multiple public compile flags.
    ///
    /// Public flags are visible to downstream crates that use this library.
    ///
    /// # Parameters
    ///
    /// - `flags`: Iterator of public compile flags to add.
    pub fn add_flags<I, F>(&mut self, flags: I)
    where
        I: IntoIterator<Item = F>,
        F: AsRef<str>,
    {
        for flag in flags {
            self.add_flag(flag.as_ref());
        }
    }

    /// Returns the merged compile attributes for the library, combining both private and public attributes.
    pub fn get_merged_attrs(&self) -> CompileAttrs {
        self.private_attrs.clone().merge(&self.public_attrs)
    }

    /// Returns the public compile attributes for the library, which are visible to downstream crates that use this library.
    pub fn get_public_attrs(&self) -> &CompileAttrs {
        &self.public_attrs
    }

    /// Imports an external library using `pkg-config`.
    ///
    /// # Parameters
    ///
    /// - `library_name`: The name of the external library to import.
    /// - `make_public`: If `true`, include paths are treated as public (visible to downstream crates); otherwise, they are private.
    ///
    /// # Errors
    ///
    /// Returns an error if the library cannot be found or probed.
    pub fn import_external_lib(&mut self, library_name: &str, make_public: bool) -> Result<()> {
        let extlib = pkg_config::probe_library(library_name)
            .with_context(|| format!("Failed to probe pkg-config library `{library_name}`"))?;

        extlib.include_paths.iter().for_each(|path| {
            if make_public {
                self.add_include(path);
            } else {
                self.add_private_include(path);
            }
        });

        extlib.link_paths.iter().for_each(|path| {
            println!("cargo:rustc-link-search={}", path.display());
        });

        extlib.libs.iter().for_each(|lib| {
            self.add_lib(lib);
        });

        Ok(())
    }

    /// Adds a library to the list of dependencies for this library.
    ///
    /// This function is used internally to track libraries that must be linked when using this library.
    ///
    /// # Parameters
    ///
    /// - `lib`: The name of the library to add.
    fn add_lib(&mut self, lib: &str) {
        if !self.libs.contains(&lib.to_string()) {
            self.libs.push(lib.to_string());
        }
    }

    /// Returns an iterator over the libraries that this library depends on, which must be linked when using this library.
    ///
    /// This includes both libraries added directly to this library and libraries imported from other crates.
    ///
    /// # Returns
    ///
    /// An iterator of library names as string slices.
    pub fn get_libs(&self) -> impl IntoIterator<Item = &str> {
        self.libs.iter().map(|s| s.as_str())
    }

    /// Imports another C library defined in a different crate.
    ///
    /// This function automatically imports the public include paths, defines, flags,
    /// and dependent libraries from the specified crate, making them available to this library.
    ///
    /// # Parameters
    ///
    /// - `crate_name`: The name of the crate whose public C library attributes should be imported.
    ///
    /// If the crate has already been imported, this function does nothing.
    pub fn import_lib(&mut self, lib_name: &str) -> Result<()> {
        let lib_name = lib_name.to_string();

        if self.libs.contains(&lib_name) {
            return Ok(());
        }

        self.add_lib(&lib_name);

        self.public_attrs.import_library_metadata(&lib_name)?;

        let public_libs = library_metadata(&lib_name, "LIBS")?;

        for library_name in public_libs.split(';').filter(|lib| !lib.is_empty()) {
            self.add_lib(library_name);
        }

        Ok(())
    }
}
