use std::{env, path::PathBuf, process::Command};

fn main() {
    println!("cargo:rustc-env=BUILD_DIR={}", build_dir());
    generate_crypto_bindings();
    #[cfg(feature = "test")]
    link_core_objects();
}

fn build_dir() -> String {
    let build_dir_str = env::var("BUILD_DIR").unwrap_or(String::from("../../../../build/unix"));
    PathBuf::from(build_dir_str)
        .canonicalize()
        .unwrap()
        .to_str()
        .unwrap()
        .to_string()
}

fn prepare_bindings() -> bindgen::Builder {
    let mut bindings = bindgen::Builder::default();

    let build_dir_include = format!("-I{}", build_dir());

    let mut clang_args: Vec<String> = Vec::new();
    clang_args.push(build_dir_include);
    clang_args.push("-Iinc".to_string());

    // Pass in correct include paths and defines.
    if env::var("CARGO_CFG_TARGET_OS").unwrap() == "none" {
        clang_args.push("-nostdinc".to_string());
        clang_args.push("-fshort-enums".to_string()); // Make sure enums use the same size as in C

        // Append gcc-arm-none-eabi's include paths.
        let cc_output = Command::new("arm-none-eabi-gcc")
            .arg("-E")
            .arg("-Wp,-v")
            .arg("-")
            .output()
            .expect("arm-none-eabi-gcc failed to execute");
        if !cc_output.status.success() {
            panic!("arm-none-eabi-gcc failed");
        }
        let include_paths =
            String::from_utf8(cc_output.stderr).expect("arm-none-eabi-gcc returned invalid output");
        let include_args = include_paths
            .lines()
            .skip_while(|s| !s.contains("search starts here:"))
            .take_while(|s| !s.contains("End of search list."))
            .filter(|s| s.starts_with(' '))
            .map(|s| format!("-I{}", s.trim()));

        bindings = bindings.clang_args(include_args);
    } else {
        clang_args.push("-fno-short-enums".to_string());
    }

    bindings = bindings.clang_args(&clang_args);

    bindings
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
}

fn generate_crypto_bindings() {
    let out_path = env::var("OUT_DIR").unwrap();

    // Tell cargo to invalidate the built crate whenever the header changes.
    println!("cargo:rerun-if-changed=crypto.h");

    let bindings = prepare_bindings()
        .header("crypto.h")
        // aesgcm
        .allowlist_type("gcm_ctx")
        .no_copy("gcm_ctx")
        .allowlist_function("gcm_init_and_key")
        .allowlist_function("gcm_init_message")
        .allowlist_function("gcm_encrypt")
        .allowlist_function("gcm_decrypt")
        .allowlist_function("gcm_auth_header")
        .allowlist_function("gcm_compute_tag")
        // curve25519
        .allowlist_function("curve25519_scalarmult")
        .allowlist_function("curve25519_scalarmult_basepoint")
        // ed25519
        .allowlist_type("ed25519_signature")
        .allowlist_type("ed25519_public_key")
        .allowlist_function("ed25519_cosi_combine_publickeys")
        .allowlist_function("ed25519_sign_open")
        // elligator2
        .allowlist_function("map_to_curve_elligator2_curve25519")
        // hmac
        .allowlist_type("HMAC_SHA256_CTX")
        .no_copy("HMAC_SHA256_CTX")
        .allowlist_function("hmac_sha256_Init")
        .allowlist_function("hmac_sha256_Update")
        .allowlist_function("hmac_sha256_Final")
        // sha256
        .allowlist_var("SHA256_DIGEST_LENGTH")
        .allowlist_type("SHA256_CTX")
        .no_copy("SHA256_CTX")
        .allowlist_function("sha256_Init")
        .allowlist_function("sha256_Update")
        .allowlist_function("sha256_Final")
        // sha512
        .allowlist_var("SHA512_DIGEST_LENGTH")
        .allowlist_type("SHA512_CTX")
        .no_copy("SHA512_CTX")
        .allowlist_function("sha512_Init")
        .allowlist_function("sha512_Update")
        .allowlist_function("sha512_Final");

    // Write the bindings to a file in the OUR_DIR.
    bindings
        .clang_arg("-fgnuc-version=0") // avoid weirdness with ed25519.h CONST definition
        .generate()
        .expect("Unable to generate bindings")
        .write_to_file(PathBuf::from(out_path).join("crypto.rs"))
        .unwrap();
}

#[cfg(feature = "test")]
fn link_core_objects() {
    use std::ffi::OsStr;

    let crate_path = env::var("CARGO_MANIFEST_DIR").unwrap();
    let build_path = format!("{}/../../../../build/unix", crate_path);
    let path = PathBuf::from(build_path.clone());

    // List of object filenames to ignore in the `embed` directory
    let embed_blocklist = [OsStr::new("main_main.o")];

    // Collect all objects that the `core` library uses, and link it in. We have to
    // make sure to avoid the object with the `_main` symbol, so we don't get any
    // duplicates.
    let mut cc = cc::Build::new();
    for obj in glob::glob(&format!("{}/embed/**/*.o", build_path)).unwrap() {
        let obj = obj.unwrap();
        if embed_blocklist.contains(&obj.file_name().unwrap()) {
            // Ignore.
        } else {
            cc.object(obj);
        }
    }

    for obj in glob::glob(&format!("{}/vendor/**/*.o", build_path)).unwrap() {
        let obj = obj.unwrap();
        cc.object(obj);
    }

    // Add frozen modules, if present.
    for obj in glob::glob(&format!("{}/*.o", build_path)).unwrap() {
        cc.object(obj.unwrap());
    }

    // Compile all the objects into a static library and link it in automatically.
    cc.compile("core_lib");
}
