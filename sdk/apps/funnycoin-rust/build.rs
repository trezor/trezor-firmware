use std::{collections::BTreeMap, env, fs, path::PathBuf};

use serde::Deserialize;

#[derive(Debug, Deserialize)]
struct TranslationFile {
    translations: BTreeMap<String, String>,
}

#[derive(Default)]
enum Language {
    #[default]
    English,
    Czech,
}

impl Language {
    fn from_env() -> Self {
        if env::var("CARGO_FEATURE_LANG_CS").is_ok() {
            Self::Czech
        } else if env::var("CARGO_FEATURE_LANG_EN").is_ok() {
            Self::English
        } else {
            Self::default()
        }
    }

    fn file(&self) -> String {
        let name = match self {
            Self::English => "en",
            Self::Czech => "cs",
        };
        format!("translations/{}.json", name)
    }
}

fn main() {
    build_protobufs();
    build_translations();
    link();
}

fn build_protobufs() {
    let mut config = prost_build::Config::new();
    config
        .compile_protos(
            &[
                "protob/common.proto",
                "protob/funnycoin.proto",
                "protob/messages.proto",
            ],
            &["protob/"],
        )
        .expect("Failed to compile protobufs");
}
fn build_translations() {
    let lang_json = Language::from_env().file();
    println!("cargo:rerun-if-changed={}", &lang_json);

    let lang_json_str = fs::read_to_string(&lang_json).expect("Failed to read translation file");
    let file: TranslationFile =
        serde_json::from_str(&lang_json_str).expect("Failed to parse translation file");

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

    let out_dir = PathBuf::from(env::var("OUT_DIR").expect("OUT_DIR environment variable not set"));
    fs::write(out_dir.join("translations.rs"), out).expect("Failed to write translations.rs");
}

fn is_linux() -> bool {
    env::var("CARGO_CFG_UNIX").is_ok()
        || env::var("CARGO_CFG_TARGET_OS")
            .map(|os| os == "linux")
            .unwrap_or(false)
}

fn is_macos() -> bool {
    env::var("CARGO_CFG_TARGET_OS")
        .map(|os| os == "macos")
        .unwrap_or(false)
}

fn is_unit_test() -> bool {
    env::var("CARGO_FEATURE_TEST").is_ok()
}

fn link() {
    if !is_unit_test() {
        if is_macos() {
            // On macOS, link to System framework to get memcpy, memset, etc.
            println!("cargo:rustc-link-lib=System");
            println!("cargo:rustc-link-arg=-Wl,-export_dynamic");
        } else if is_linux() {
            // On Linux, link to C library to get __libc_start_main, memcpy, etc.
            println!("cargo:rustc-link-lib=c");
            println!("cargo:rustc-link-arg=-shared");
        }
    }
}
