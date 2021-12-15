macro_rules! include_res {
    ($filename:expr) => {
        include_bytes!(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../../src/trezor/res/",
            $filename,
        ))
    };
}
