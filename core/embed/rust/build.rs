use std::{env, path::PathBuf};

fn main() {
    generate_qstr_bindings();
}

/// Generates Rust module that exports QSTR constants used in firmware.
fn generate_qstr_bindings() {
    let out_path = env::var("OUT_DIR").unwrap();

    let qstr_path = match env::var("QSTR_GENERATED") {
        Ok(path) => path,
        Err(_) => {
            eprintln!("QSTR_GENERATED is missing, run build through `scons`");
            return;
        }
    };

    // Tell cargo to invalidate the built crate whenever the header changes.
    println!("cargo:rerun-if-changed=qstr.h");
    // ... and whenever the generated QSTRs change.
    println!("cargo:rerun-if-changed={}", qstr_path);

    bindgen::Builder::default()
        .header("qstr.h")
        // Use `core` and `cty` instead of `std` for primitive types.
        .use_core()
        .ctypes_prefix("cty")
        // Build the Qstr enum as a newtype so we can define method on it.
        .default_enum_style(bindgen::EnumVariation::NewType { is_bitfield: false })
        // Pass the path to the QSTR definitions through a define.
        .clang_arg(format!("-DQSTR_GENERATED_PATH=\"{}\"", qstr_path))
        // Tell cargo to invalidate the built crate whenever any of the
        // included header files changed.
        .parse_callbacks(Box::new(bindgen::CargoCallbacks))
        .generate()
        .expect("Unable to generate Rust QSTR bindings")
        .write_to_file(PathBuf::from(out_path).join("qstr.rs"))
        .unwrap();
}
