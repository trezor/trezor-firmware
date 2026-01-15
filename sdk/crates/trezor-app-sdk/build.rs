fn main() {
    let level = std::env::var("LOG_LEVEL").unwrap_or("info".to_string());
    match level.as_str() {
        "error" | "warn" | "info" | "debug" | "trace" | "off" => (),
        _ => panic!("Invalid log level: {}", level),
    }
    println!("cargo:rustc-cfg=log_level=\"{}\"", level);
    println!("cargo:rustc-check-cfg=cfg(log_level, values(\"off\", \"error\", \"warn\", \"info\", \"debug\", \"trace\"))");
    println!("cargo:rerun-if-env-changed=LOG_LEVEL");
}
