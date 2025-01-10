//! Bindings for Trezor protobufs.

// Note: we do not use the generated `mod.rs` because we want to feature-gate some modules manually.
// This significantly improves compile times.
// See https://github.com/joshieDo/rust-trezor-api/pull/9 for more details.
#[allow(ambiguous_glob_reexports, unreachable_pub)]
mod generated {
    macro_rules! modules {
        ($($($feature:literal =>)? $module:ident)+) => {$(
            $(#[cfg(feature = $feature)])?
            mod $module;
            $(#[cfg(feature = $feature)])?
            pub use self::$module::*;
        )+};
    }

    modules! {
        messages
        messages_bootloader
        messages_ble
        messages_common
        messages_crypto
        messages_debug
        messages_definitions
        messages_management
        messages_benchmark
        options

        "bitcoin" => messages_bitcoin
        "ethereum" => messages_ethereum
        "ethereum" => messages_ethereum_eip712
        "binance" => messages_binance
        "cardano" => messages_cardano
        "eos" => messages_eos
        "monero" => messages_monero
        "nem" => messages_nem
        "nostr" => messages_nostr
        "ripple" => messages_ripple
        "solana" => messages_solana
        "stellar" => messages_stellar
        "tezos" => messages_tezos
        "webauthn" => messages_webauthn
    }
}

pub use generated::*;
