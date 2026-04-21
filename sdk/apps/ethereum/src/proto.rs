// Include generated protobuf code

pub mod common {
    include!(concat!(env!("OUT_DIR"), "/hw.trezor.common.rs"));
}

pub mod definitions {
    include!(concat!(env!("OUT_DIR"), "/hw.trezor.definitions.rs"));
}
pub mod ethereum {
    include!(concat!(env!("OUT_DIR"), "/hw.trezor.ethereum.rs"));
}

pub mod messages {
    include!(concat!(env!("OUT_DIR"), "/hw.trezor.messages.rs"));
}
