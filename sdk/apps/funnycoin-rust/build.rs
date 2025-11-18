fn main() {
    prost_build::compile_protos(
        &["../../../common/protob/messages-funnycoin.proto"],
        &["../../../common/protob/"],
    )
    .unwrap();

    // On macOS, link to System framework to get memcpy, memset, etc.
    // Check the TARGET OS, not the host OS
    let target_os = std::env::var("CARGO_CFG_TARGET_OS").unwrap_or_default();

    if target_os == "macos" {
        println!("cargo:rustc-link-lib=System");
    }
}
