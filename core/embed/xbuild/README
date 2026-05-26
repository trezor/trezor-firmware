## xbuild

`xbuild` is a Cargo build-script helper library for compiling and linking C code in the Trezor firmware Rust build.

It wraps the `cc` crate with a small API that fits this codebase: configure a C library, compile it, optionally link a final binary, and share compile settings between crates.

## Usage

Build scripts use one of two entry points:

```rust
// Library crates — compile a static .a archive:
xbuild::build(|lib| {
    lib.add_sources_in_dir(&src, ["driver.c"]);
    lib.add_include(&src.join("include"));
    Ok(())
})?;

// Project (top-level) crates — compile and link a binary:
xbuild::build_and_link("firmware", |lib| {
    lib.import_lib("io")?;
    lib.add_sources_in_dir(&src, ["main.c"]);
    Ok(())
})?;
```

`build()` is for crates that produce a C static library.
`build_and_link()` is for top-level crates that also link a final binary.

Both entry points handle the Trezor-specific build conventions for compiler setup, linking, metadata export, and editor tooling.

## What It Provides

- A single `CLibrary` builder for configuring sources, include paths, defines, flags, and extra objects
- Support for sharing public C build settings across Cargo crates
- Incremental rebuild tracking for source, header, and command-line changes
- Parallel C compilation
- Binary embedding helpers
- Optional Rust bindings generation with `bindgen`
- Generation of compile-command data for editor tooling

## Structure

```
xbuild/src/
├── lib.rs          — public API and re-exports
├── trezor.rs       — Trezor-specific build entry points and linking
├── attrs.rs        — compile flags, defines, and include-path handling
├── helpers.rs      — shared path, environment, and Cargo metadata helpers
├── dep_tracking.rs — incremental rebuild tracking for generated outputs
├── input_files.rs  — source file collection helpers
├── parallel.rs     — parallel worker execution utilities
└── clibrary/
    ├── mod.rs           — `CLibrary` configuration API
    ├── compile.rs       — C compilation and archive creation
    ├── embed.rs         — binary embedding helpers
    ├── cc_generator.rs  — compile-command database generation
    └── rust_bindings.rs — optional bindgen integration
```

The central type is `CLibrary`, which represents one C library being assembled by a build script. It owns the library's source files, extra object files, compile settings, dependent libraries, and optional bindgen configuration, and acts as the main configuration object passed through `build()` and `build_and_link()`.

## Main Concepts

Unless noted otherwise, paths passed to `xbuild` are interpreted relative to the current crate root. Absolute paths are also supported.

- Add source files with `add_source()`, `add_sources()`, or `add_sources_in_dir()`.
- Add include paths with `add_include()` and `add_includes()`.
- Add preprocessor defines with `add_define()` and `add_defines()`.
- Import another xbuild-based C library crate with `import_lib()`.
- Import a system library discovered through `pkg-config` with `import_external_lib()`.
- Configure Rust bindings generation with `add_rust_bindings()`.

```rust
lib.import_lib("sys");
lib.import_external_lib("libjpeg", false)?;
lib.add_include("src/include");
lib.add_define("USE_DMA", Some("1"));
lib.add_sources_in_dir("src", ["main.c", "util.c"]);

lib.add_rust_bindings(|builder|
    Ok(builder
        .header("inc/my_driver.h")
        .allowlist_function("my_driver_func")
    ))?;
```

## Rust Analyzer Support

Rust Analyzer runs `build.rs` scripts to collect information for code analysis.

This is especially relevant for crates that generate Rust bindings from C headers. To produce useful bindings, the build script still needs to know the C build configuration, and some headers may need to be prepared ahead of time.

To avoid doing expensive work in that mode, Rust Analyzer can be configured to pass the `IS_RUST_ANALYZER` environment variable. `xbuild` exposes this through `xbuild::is_rust_analyzer()`.

When `IS_RUST_ANALYZER` is set, `xbuild` automatically skips C compilation and avoids processing embedded binaries. This significantly speeds up `build.rs` execution.

Crates such as micropython may use `xbuild::is_rust_analyzer()` to skip expensive file generation that is not needed for analysis.

```rust
if !xbuild::is_rust_analyzer() {
    // build .py files using mpy-cross
}
```

## Importing and Exporting Metadata

`xbuild` uses Cargo build-script metadata to share public C build settings between crates.

When a crate is built with `build()` or `build_and_link()`, its public include paths, defines, flags, and dependent library names are exported automatically. A downstream crate can then call `import_lib()` to import that metadata and apply the same public C settings to its own build.

Under the hood, this flows through Cargo's `DEP_<NAME>_PUBLIC_C_*` environment variables, so build scripts can be composed without manually repeating include paths or compiler definitions in every crate.

This mechanism requires the crate to define a `links` entry in `Cargo.toml`. Without `links`, Cargo does not expose the `DEP_<NAME>_PUBLIC_C_*` variables and the metadata passing does not work.

For example:

```toml
[package]
name = "sys"
version = "0.0.0"
edition = "2024"
links = "sys"
```

In practice, the crate must also produce a library artifact that downstream crates can link against. In this repository that is typically ensured by compiling at least one C source file, sometimes a dummy one.

