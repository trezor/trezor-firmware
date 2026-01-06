// Include generated protobuf code
pub mod common {
    include!(concat!(env!("OUT_DIR"), "/hw.trezor.messages.common.rs"));
}
pub mod ethereum {
    include!(concat!(env!("OUT_DIR"), "/hw.trezor.messages.ethereum.rs"));
}
pub mod ethereum_eip712 {
    include!(concat!(
        env!("OUT_DIR"),
        "/hw.trezor.messages.ethereum_eip712.rs"
    ));
}
