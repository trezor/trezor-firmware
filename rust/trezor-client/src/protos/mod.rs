include!(concat!(env!("OUT_DIR"), "/protos/mod.rs"));

#[allow(ambiguous_glob_reexports)]
pub use messages::*;
pub use messages_bootloader::*;
pub use messages_common::*;
pub use messages_crypto::*;
pub use messages_debug::*;
pub use messages_management::*;

macro_rules! features {
    ($($feature:literal => $item:ident)+) => {$(
        #[cfg(feature = $feature)]
        #[allow(ambiguous_glob_reexports)]
        pub use $item::*;
    )+};
}

features! {
    "bitcoin" => messages_bitcoin
    "ethereum" => messages_ethereum
    "ethereum" => messages_ethereum_eip712
    "ethereum" => messages_ethereum_definitions
    "binance" => messages_binance
    "cardano" => messages_cardano
    "eos" => messages_eos
    "monero" => messages_monero
    "nem" => messages_nem
    "ripple" => messages_ripple
    "stellar" => messages_stellar
    "tezos" => messages_tezos
    "webauthn" => messages_webauthn
}
