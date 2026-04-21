use std::{collections::BTreeMap, env, fs, path::PathBuf};

use serde::Deserialize;

#[derive(Debug, Deserialize)]
struct TranslationFile {
    translations: BTreeMap<String, String>,
}

fn main() {
    build_protobufs();
    build_translations();

    let target_os = std::env::var("CARGO_CFG_TARGET_OS").unwrap_or_default();

    let is_test = std::env::var("CARGO_FEATURE_TEST").is_ok();

    if !is_test {
        if target_os == "macos" {
            // On macOS, link to System framework to get memcpy, memset, etc.
            println!("cargo:rustc-link-lib=System");
        } else if target_os == "linux" {
            // On Linux, link to C library to get __libc_start_main, memcpy, etc.
            println!("cargo:rustc-link-lib=c");
            println!("cargo:rustc-link-arg=-shared");
        }
    }

    let level = std::env::var("LOG_LEVEL").unwrap_or("info".to_string());
    match level.as_str() {
        "error" | "warn" | "info" | "debug" | "trace" | "off" => (),
        _ => panic!("Invalid log level: {}", level),
    }
    println!("cargo:rustc-cfg=log_level=\"{}\"", level);
    println!(
        "cargo:rustc-check-cfg=cfg(log_level, values(\"off\", \"error\", \"warn\", \"info\", \"debug\", \"trace\"))"
    );
    println!("cargo:rerun-if-env-changed=LOG_LEVEL");
}

fn build_protobufs() {
    let mut config = prost_build::Config::new();
    config
        .compile_protos(
            &[
                "protob/common.proto",
                "protob/definitions.proto",
                "protob/ethereum.proto",
                "protob/messages.proto",
            ],
            &["protob/"],
        )
        .unwrap();
}

fn build_translations() {
    println!("cargo:rerun-if-changed=core/translations/en.json");

    let json = fs::read_to_string("translations/en.json").unwrap();
    let file: TranslationFile = serde_json::from_str(&json).unwrap();

    let mut out = String::new();
    out.push_str("#[macro_export]\n");
    out.push_str("macro_rules! tr {\n");

    for (key, value) in file.translations {
        out.push_str(&format!("    ({:?}) => {{ {:?} }};\n", key, value));
    }

    out.push_str("    ($key:literal) => {\n");
    out.push_str("        compile_error!(\"unknown translation key\")\n");
    out.push_str("    };\n");
    out.push_str("}\n");

    let out_dir = PathBuf::from(env::var("OUT_DIR").unwrap());
    fs::write(out_dir.join("translations.rs"), out).unwrap();
}
