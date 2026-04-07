use std::{
    fs,
    path::{Path, PathBuf},
};

fn main() {
    let out_path = std::env::args()
        .nth(1)
        .expect("Usage: ./gen-protobuf <input-output-dir>");
    let in_path = out_path.clone();

    let proto_dir = Path::new(&in_path).canonicalize().unwrap();
    let protos: Vec<PathBuf> = fs::read_dir(&proto_dir)
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

    let out_dir = Path::new(&out_path).canonicalize().unwrap();
    fs::create_dir_all(&out_dir).expect("Failed to create output directory");
    protobuf_codegen::Codegen::new()
        .protoc()
        .includes(&[proto_dir])
        .inputs(protos)
        .out_dir(&out_dir)
        .run_from_script();
}
