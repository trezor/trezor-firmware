fn main() {
    tracing_subscriber::fmt().with_max_level(tracing::Level::TRACE).init();

    // init with debugging
    let mut trezor = trezor_client::unique(false).unwrap();
    trezor.init_device(None).unwrap();

    let signature = trezor
        .ethereum_sign_tx(
            // default ETH path
            vec![44 + (1 << 31), 60 + (1 << 31), 0 + (1 << 31), 0, 0],
            vec![],
            vec![],
            vec![],
            "".to_string(),
            vec![],
            // 10kB of empty data
            vec![0; 10 * 1024],
            Some(1u64),
        )
        .unwrap();
    println!("Signature: {:?}", signature);
}
