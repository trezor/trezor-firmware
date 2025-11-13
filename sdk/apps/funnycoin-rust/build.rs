use std::fs;
use std::path::PathBuf;

fn main() {
    // Generate Rust code from protobuf files (using pure Rust parser, no protoc binary needed)
    protobuf_codegen::Codegen::new()
        .pure()
        .cargo_out_dir("protos")
        .include("../../../common/protob")
        .input("../../../common/protob/messages-funnycoin.proto")
        .run_from_script();

    // Post-process generated files to replace std:: with core::
    let out_dir = PathBuf::from(std::env::var("OUT_DIR").unwrap());
    let protos_dir = out_dir.join("protos");

    if let Ok(entries) = fs::read_dir(&protos_dir) {
        for entry in entries.flatten() {
            let path = entry.path();
            if path.extension().and_then(|s| s.to_str()) == Some("rs") {
                if let Ok(content) = fs::read_to_string(&path) {
                    let modified = content
                        // Replace std types with alloc/core equivalents
                        .replace("::std::vec::Vec", "::alloc::vec::Vec")
                        .replace("::std::string::String", "::alloc::string::String")
                        .replace("::std::option::", "::core::option::")
                        .replace("::std::result::", "::core::result::")
                        .replace("::std::default::", "::core::default::")
                        .replace("::std::clone::", "::core::clone::")
                        .replace("::std::cmp::", "::core::cmp::")
                        .replace("::std::fmt::", "::core::fmt::")
                        .replace("::std::hash::", "::core::hash::")
                        .replace("::std::iter::", "::core::iter::")
                        .replace("::std::marker::", "::core::marker::")
                        .replace("::std::mem::", "::core::mem::")
                        .replace("::std::ops::", "::core::ops::")
                        .replace("::std::ptr::", "::core::ptr::")
                        .replace("::std::slice::", "::core::slice::")
                        .replace("::std::str::", "::core::str::");
                    let _ = fs::write(&path, modified);
                }
            }
        }
    }
}
