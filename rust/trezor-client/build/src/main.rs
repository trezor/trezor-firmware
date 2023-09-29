use std::{
    fs,
    path::{Path, PathBuf},
};

fn main() {
    let proto_path = concat!(env!("CARGO_MANIFEST_DIR"), "/../../../common/protob");
    let proto_dir = Path::new(proto_path).canonicalize().unwrap();
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

    let out_path = std::env::args().skip(1).next().expect("No output directory given");
    let out_dir = PathBuf::from(out_path);
    fs::create_dir_all(&out_dir).expect("Failed to create output directory");
    protobuf_codegen::Codegen::new()
        .protoc()
        .includes(&[proto_dir])
        .inputs(protos)
        .out_dir(&out_dir)
        .run_from_script();

    // Remove mod.rs because we want to feature-gate some modules manually
    fs::remove_file(out_dir.join("mod.rs")).expect("Failed to remove mod.rs");
}
