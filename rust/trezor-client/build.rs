use std::{fs, path::PathBuf};

fn main() {
    let proto_path = "protob";
    let protos: Vec<PathBuf> = fs::read_dir(proto_path)
        .unwrap()
        .filter_map(|entry| {
            let entry = entry.unwrap();
            let path = entry.path();
            if path.is_file() && path.extension().map_or(false, |ext| ext == "proto") {
                Some(path)
            } else {
                None
            }
        })
        .collect();
    let out_path = std::env::var("OUT_DIR").unwrap();
    let out_dir = PathBuf::from(out_path).join("protos");
    fs::create_dir_all(&out_dir).expect("Failed to create output directory");
    protobuf_codegen::Codegen::new()
        .protoc()
        .includes(&[proto_path])
        .inputs(protos)
        .out_dir(out_dir)
        .run_from_script();
}
