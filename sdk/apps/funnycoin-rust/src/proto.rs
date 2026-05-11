// Include generated protobuf code

pub mod common {
    include!(concat!(env!("OUT_DIR"), "/hw.trezor.common.rs"));
}

pub mod funnycoin {
    include!(concat!(env!("OUT_DIR"), "/hw.trezor.funnycoin.rs"));
}

pub mod messages {
    include!(concat!(env!("OUT_DIR"), "/hw.trezor.messages.rs"));
}
