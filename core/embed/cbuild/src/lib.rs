use std::env;
use std::fs;
use std::path::{Component, PathBuf};

#[derive(Default)]
pub struct CLibrary {
    sources: Vec<String>,
    flags: Vec<String>,
    public_flags: Vec<String>,
    defines: Vec<(String, Option<String>)>,
    public_defines: Vec<(String, Option<String>)>,
    includes: Vec<String>,
    public_includes: Vec<String>,
    public_libs: Vec<String>,
}

fn emit_deps(content: &str) {
    for line in content.lines() {
        // Clean up the .d format (target: dependency1 dependency2 ...)
        let parts = line.split(':').next_back().unwrap_or("");
        for path in parts.split_whitespace() {
            if path != "\\" {
                println!("cargo:rerun-if-changed={}", path);
            }
        }
    }
}

fn has_feature(feature: &str) -> bool {
    let env_name = format!("CARGO_FEATURE_{}", feature_to_env_name(feature));
    env::var_os(env_name).is_some()
}

fn feature_to_env_name(feature: &str) -> String {
    feature
        .chars()
        .map(|ch| {
            if ch.is_ascii_alphanumeric() {
                ch.to_ascii_uppercase()
            } else {
                '_'
            }
        })
        .collect()
}

pub fn emit_linker_args(module_type: &str) {
    if has_feature("mcu_emulator") {
        println!(
            "cargo:rustc-link-search=/nix/store/rmz7imacazbbf4dqgsb9wwbkh0nx1jkh-SDL2-2.26.4/lib"
        );
        println!(
            "cargo:rustc-link-search=/nix/store/frhqd181g2g6l468g1gzx055dw0y560n-SDL2_image-2.6.3/lib"
        );
        println!("cargo:rustc-link-lib=SDL2");
        println!("cargo:rustc-link-lib=SDL2_image");

        println!("cargo:rustc-link-arg=-Wl,-Bdynamic");
        println!("cargo:rustc-link-lib=c");
        println!("cargo:rustc-link-lib=gcc");
        println!("cargo:rustc-link-lib=m");
        println!("cargo:rustc-link-lib=dl");
        println!("cargo:rustc-link-lib=pthread");
    } else {
        let script = {
            let suffix = if has_feature("secmon_layout") {
                "_secmon"
            } else {
                ""
            };

            if has_feature("model_t3w1") {
                format!("models/T3W1/memory{suffix}.ld")
            } else if has_feature("model_t3t1") {
                format!("models/T3T1/memory{suffix}.ld")
            } else if has_feature("model_t3b1") {
                format!("models/T3B1/memory{suffix}.ld")
            } else if has_feature("model_t2b1") {
                format!("models/T2B1/memory{suffix}.ld")
            } else if has_feature("model_t2t1") {
                format!("models/T2T1/memory{suffix}.ld")
            } else {
                unimplemented!();
            }
        };

        println!("cargo:rustc-link-arg=-T{script}");

        let script = if has_feature("mcu_stm32u5g") {
            format!("sys/linker/stm32u5g/{module_type}.ld")
        } else if has_feature("mcu_stm32u58") {
            format!("sys/linker/stm32u58/{module_type}.ld")
        } else if has_feature("mcu_stm32f4") {
            format!("sys/linker/stm32f4/{module_type}.ld")
        } else {
            unimplemented!();
        };

        println!("cargo:rustc-link-arg=-T{script}");

        let map_file =
            PathBuf::from(env::var("OUT_DIR").unwrap()).join(format!("{module_type}.map"));
        println!("cargo:rustc-link-arg=-Wl,-Map={}", map_file.display());
        println!("cargo:rustc-link-arg=-Wl,--gc-sections");

        println!("cargo:rustc-link-lib=c_nano");
        println!("cargo:rustc-link-lib=m");
        println!("cargo:rustc-link-lib=gcc");
    }
}

impl CLibrary {
    pub fn new() -> Self {
        Self::default()
    }

    /// Adds a single source file to the library.
    ///
    /// The path should be relative to the crate root or absolute.
    pub fn add_source(&mut self, src: &str) {
        self.sources.push(src.to_string());
    }

    /// Adds multiple source files to the library.
    ///
    /// The paths should be relative to the crate root or absolute.
    pub fn add_sources(&mut self, sources: &[&str]) {
        for src in sources {
            self.add_source(src);
        }
    }

    pub fn add_sources_from_folder(&mut self, prefix: &str, sources: &[&str]) {
        for src in sources {
            let full_path = format!("{}/{}", prefix, src);
            self.add_source(&full_path);
        }
    }

    /// Adds include directory to the library.
    ///
    /// The path should be relative to the crate root or absolute.
    pub fn add_include(&mut self, inc: &str) {
        if !self.includes.contains(&inc.to_string()) {
            self.includes.push(inc.to_string());
        }
    }

    /// Adds multiple include directories to the library.
    ///
    /// The paths should be relative to the crate root or absolute.
    pub fn add_includes(&mut self, inc: &[&str]) {
        for dir in inc {
            self.add_include(dir);
        }
    }

    /// Adds a preprocessor define to the library.
    ///
    /// `value` is optional and can be used for defines like `-DNAME=value`.
    /// If `value` is `None`, it will be treated as `-DNAME`.
    pub fn add_define(&mut self, name: &str, value: Option<&str>) {
        self.defines
            .push((name.to_string(), value.map(|v| v.to_string())));
    }

    /// Adds multiple preprocessor defines to the library.
    ///
    pub fn add_defines(&mut self, defines: &[(&str, Option<&str>)]) {
        for (name, value) in defines {
            self.add_define(name, *value);
        }
    }

    pub fn add_public_include(&mut self, inc: &str) {
        if !self.public_includes.contains(&inc.to_string()) {
            self.public_includes.push(inc.to_string());
        }
    }

    pub fn add_public_includes(&mut self, inc: &[&str]) {
        for dir in inc {
            self.add_public_include(dir);
        }
    }

    pub fn add_public_define(&mut self, name: &str, value: Option<&str>) {
        self.public_defines
            .push((name.to_string(), value.map(|v| v.to_string())));
    }

    pub fn add_public_defines(&mut self, defines: &[(&str, Option<&str>)]) {
        for (name, value) in defines {
            self.add_public_define(name, *value);
        }
    }

    pub fn add_flag(&mut self, flag: &str) {
        if !self.flags.contains(&flag.to_string()) {
            self.flags.push(flag.to_string());
        }
    }

    pub fn add_flags(&mut self, flags: &[&str]) {
        for flag in flags {
            self.add_flag(flag);
        }
    }

    pub fn add_public_flag(&mut self, flag: &str) {
        if !self.public_flags.contains(&flag.to_string()) {
            self.public_flags.push(flag.to_string());
        }
    }

    pub fn add_public_flags(&mut self, flags: &[&str]) {
        for flag in flags {
            self.add_public_flag(flag);
        }
    }

    pub fn add_public_lib(&mut self, lib: &str) {
        if !self.public_libs.contains(&lib.to_string()) {
            self.public_libs.push(lib.to_string());
        }
    }

    /// Use another C library defined in a different crate.
    ///
    /// This will automatically import the public include paths, defines,
    /// and flags from that crate.
    pub fn use_lib(&mut self, crate_name: &str) {
        self.add_public_lib(crate_name);

        let get_c_public = |crate_name: &str, kind: &str| -> String {
            std::env::var(format!(
                "DEP_{}_PUBLIC_C_{}",
                crate_name.to_uppercase(),
                kind
            ))
            .unwrap_or_default()
        };

        let public_inc = get_c_public(crate_name, "INCLUDES");

        for dir in public_inc.split(';').filter(|path| !path.is_empty()) {
            self.add_public_include(dir);
        }

        let public_defines = get_c_public(crate_name, "DEFINES");

        for def in public_defines.split(';').filter(|def| !def.is_empty()) {
            let parts: Vec<&str> = def.splitn(2, '=').collect();
            let name = parts[0];
            let value = if parts.len() > 1 {
                Some(parts[1])
            } else {
                None
            };
            self.add_public_define(name, value);
        }

        let public_flags = get_c_public(crate_name, "FLAGS");

        for flag in public_flags.split(';').filter(|flag| !flag.is_empty()) {
            self.add_public_flag(flag);
        }

        let public_libs = get_c_public(crate_name, "LIBS");

        for lib in public_libs.split(';').filter(|lib| !lib.is_empty()) {
            self.add_public_lib(lib);
        }
    }

    pub fn build(self: &CLibrary) {
        let out_dir = PathBuf::from(env::var("OUT_DIR").unwrap());
        let manifest_dir = PathBuf::from(env::var("CARGO_MANIFEST_DIR").unwrap());
        let mut build = cc::Build::new();

        for flag in &self.flags {
            build.flag(flag);
        }

        for flag in &self.public_flags {
            build.flag(flag);
        }

        for dir in &self.public_includes {
            build.include(dir);
        }

        for dir in &self.includes {
            build.include(dir);
        }

        for def in &self.public_defines {
            build.define(&def.0, def.1.as_deref());
        }

        for def in &self.defines {
            build.define(&def.0, def.1.as_deref());
        }

        let mut objects = Vec::new();

        for src in &self.sources {
            let src_path = PathBuf::from(src);
            let resolved_src_path = if src_path.is_absolute() {
                src_path.clone()
            } else {
                manifest_dir.join(&src_path)
            };

            let relative_src_path = match resolved_src_path.strip_prefix(&manifest_dir) {
                Ok(path) => path.to_path_buf(),
                Err(_) => {
                    let mut path = PathBuf::from("__external");
                    for component in resolved_src_path.components() {
                        if let Component::Normal(part) = component {
                            path.push(part);
                        }
                    }
                    path
                }
            };

            let obj_path = out_dir.join(relative_src_path).with_extension("o");
            let dep_path = obj_path.with_extension("d");

            if let Some(parent) = obj_path.parent() {
                fs::create_dir_all(parent).expect("Failed to create output directory");
            }

            // Compile individual file to object without making a library yet
            let mut cmd = build.get_compiler().to_command();
            cmd.arg("-c")
                .arg("-MMD")
                .arg("-MF")
                .arg(&dep_path)
                .arg("-o")
                .arg(&obj_path)
                .arg(&resolved_src_path);

            // Run the command (only if needed - cc crate handles some of this logic,
            // but for manual control we check timestamps or just run it)
            let status = cmd.status().expect("Compiler failed");
            if !status.success() {
                panic!("Failed to compile {:?}", resolved_src_path);
            }

            // Parse the .d file for Cargo tracking
            if let Ok(content) = fs::read_to_string(&dep_path) {
                emit_deps(&content);
            }

            objects.push(obj_path);
        }

        // Batch all objects into ONE static library
        let mut final_build = cc::Build::new();
        for obj in objects {
            final_build.object(obj);
        }

        let lib_name =
            env::var("CARGO_MANIFEST_LINKS").unwrap_or_else(|_| "native_part".to_string());
        final_build.compile(&lib_name);

        self.public_libs.iter().for_each(|lib| {
            println!("cargo:rustc-link-lib=static={}", lib);
        });

        let mut exported_public_libs = self.public_libs.clone();
        if !exported_public_libs.contains(&lib_name) {
            exported_public_libs.push(lib_name.clone());
        }
        println!(
            "cargo::metadata=public_c_libs={}",
            exported_public_libs.join(";")
        );

        // Export public include paths
        let manifest_dir = std::env::var("CARGO_MANIFEST_DIR").unwrap();
        let public_includes = self
            .public_includes
            .iter()
            .map(|dir| {
                if dir.starts_with('/') {
                    dir.clone()
                } else {
                    format!("{}/{}", manifest_dir, dir)
                }
            })
            .collect::<Vec<_>>()
            .join(";");
        println!("cargo::metadata=public_c_includes={}", public_includes);

        // Export public defines
        let public_defines = self
            .public_defines
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
        println!("cargo::metadata=public_c_defines={}", public_defines);

        // Export public c_flags
        let public_flags = self.public_flags.join(";");
        println!("cargo::metadata=public_c_flags={}", public_flags);

        // Export compiler default include paths (for bindgen)
        //TODO!@# maybe do not export in emulator build

        let compiler = cc::Build::new().get_compiler();
        let compile_result = compiler
            .to_command()
            .arg("-E")
            .arg("-Wp,-v")
            .arg("-")
            .output()
            .expect("compiler failed to execute");
        if !compile_result.status.success() {
            panic!("compiler failed");
        }

        let compiler_output =
            String::from_utf8(compile_result.stderr).expect("compiler returned invalid output");

        let compiler_includes = compiler_output
            .lines()
            .skip_while(|s| !s.contains("search starts here:"))
            .take_while(|s| !s.contains("End of search list."))
            .filter(|s| s.starts_with(' '))
            .map(|s| s.trim().to_string())
            .collect::<Vec<_>>()
            .join(";");

        println!("cargo::metadata=c_compiler_includes={}", compiler_includes);
    }
}
