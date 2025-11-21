fn main() {
    prost_build::compile_protos(
        &["../../../common/protob/messages-funnycoin.proto"],
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
}
