//! With `codec`: parse the firmware's `common/protob/messages*.proto` (pure Rust, no protoc) into
//! a FileDescriptorSet the crate embeds, so messages are encoded by name from the SAME definitions
//! the firmware is built from -- never from a generated copy that can fall behind.

fn main() {
    #[cfg(feature = "codec")]
    codec::build();
}

#[cfg(feature = "codec")]
mod codec {
    use std::{env, fs, path::PathBuf};

    use protobuf::Message;

    pub fn build() {
        let dir =
            PathBuf::from(env::var("CARGO_MANIFEST_DIR").unwrap()).join("../../common/protob");
        println!("cargo:rerun-if-changed={}", dir.display());
        let mut inputs: Vec<PathBuf> = fs::read_dir(&dir)
            .expect("common/protob")
            .filter_map(|e| e.ok().map(|e| e.path()))
            .filter(|p| {
                let name = p.file_name().unwrap().to_string_lossy();
                name.starts_with("messages") && name.ends_with(".proto")
            })
            .collect();
        inputs.sort();
        let parsed = protobuf_parse::Parser::new()
            .pure()
            .include(&dir)
            .inputs(&inputs)
            .parse_and_typecheck()
            .expect("the firmware protos parse");
        let set = protobuf::descriptor::FileDescriptorSet {
            file: parsed.file_descriptors,
            ..Default::default()
        };
        let out = PathBuf::from(env::var("OUT_DIR").unwrap()).join("protob.bin");
        fs::write(out, set.write_to_bytes().unwrap()).unwrap();
    }
}
