use std::{collections::BTreeMap, env, fs, path::PathBuf};

use serde::Deserialize;
use serde_json::Value;

#[derive(Debug, Deserialize)]
struct TranslationFile {
    translations: BTreeMap<String, Value>,
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

#[derive(Default)]
enum Model {
    #[default]
    T3T1,
    T3W1,
}

impl Model {
    fn from_env() -> Self {
        if env::var("CARGO_FEATURE_MODEL_T3W1").is_ok() {
            Self::T3W1
        } else if env::var("CARGO_FEATURE_MODEL_T3T1").is_ok() {
            Self::T3T1
        } else {
            Self::default()
        }
    }

    fn layout(&self) -> &'static str {
        match self {
            Self::T3T1 => "Eckhart",
            Self::T3W1 => "Delizia",
        }
    }
}

fn main() {
    build_protobufs();
    build_translations();
    link();
}

fn build_protobufs() {
    let protos = &[
        "protob/common.proto",
        "protob/definitions.proto",
        "protob/ethereum.proto",
        "protob/messages.proto",
    ];

    for proto in protos {
        println!("cargo:rerun-if-changed={}", proto);
    }

    let mut config = prost_build::Config::new();
    config.compile_protos(protos, &["protob/"]).unwrap();
}

fn build_translations() {
    let language = Language::from_env();
    let model = Model::from_env();
    let layout = model.layout();
    let json_path = language.file();

    println!("cargo:rerun-if-changed={}", json_path);

    let json = fs::read_to_string(&json_path)
        .unwrap_or_else(|_| panic!("Could not read translation file: {}", json_path));
    let file: TranslationFile = serde_json::from_str(&json).unwrap();

    fn resolve_translation<'a>(value: &'a Value, layout: &str) -> Option<&'a str> {
        match value {
            Value::String(s) => Some(s.as_str()),
            Value::Object(map) => map
                .get(layout)
                .or_else(|| map.values().next())
                .and_then(|v| v.as_str()),
            _ => None,
        }
    }

    let mut out = String::new();
    out.push_str("#[macro_export]\n");
    out.push_str("macro_rules! tr {\n");

    for (key, value) in &file.translations {
        if let Some(resolved) = resolve_translation(value, layout) {
            out.push_str(&format!("    ({:?}) => {{ {:?} }};\n", key, resolved));
        }
    }

    out.push_str("    ($key:literal) => {\n");
    out.push_str("        compile_error!(\"unknown translation key\")\n");
    out.push_str("    };\n");
    out.push_str("}\n");

    let out_dir = PathBuf::from(env::var("OUT_DIR").unwrap());
    fs::write(out_dir.join("translations.rs"), out).unwrap();
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
