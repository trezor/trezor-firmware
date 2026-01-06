fn main() {
    let mut config = prost_build::Config::new();
    config.compile_protos(
        &[
            "../../../common/protob/messages-common.proto",
            "../../../common/protob/messages-ethereum.proto",
            "../../../common/protob/messages-ethereum-eip712.proto",
        ],
        &["../../../common/protob/"],
    )
    .unwrap();

    let target_os = std::env::var("CARGO_CFG_TARGET_OS").unwrap_or_default();
    if target_os == "macos" {
        // On macOS, link to System framework to get memcpy, memset, etc.
        println!("cargo:rustc-link-lib=System");
    } else if target_os == "linux" {
        // On Linux, link to C library to get __libc_start_main, memcpy, etc.
        println!("cargo:rustc-link-lib=c");
        println!("cargo:rustc-link-arg=-shared");
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
