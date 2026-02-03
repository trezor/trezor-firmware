use crate::proto::ethereum::{EthereumGetPublicKey, EthereumPublicKey};
use alloc::string::ToString;
use trezor_app_sdk::{Result, crypto, log, ui};

pub fn get_public_key(msg: EthereumGetPublicKey) -> Result<EthereumPublicKey> {
    let long_string: &str = "Hello, 世界! 🌍🌎🌏 Привет мир! مرحبا بالعالم 日本語テスト αβγδε ñoño café naïve 北京 Zürich™ €100 ½ ¼ ¾ → ← ↑ ↓ ♠♣♥♦ ✓✗ ∑∏∫∂ ≤≥≠≈ 🎉🔥💡🚀 ⚡️☀️🌙⭐️";
    log::info!("string chars: {}, string bytes: {}", long_string.chars().count(), long_string.len());

    ui::confirm_long_value("title", long_string)?;

    // TODO: Implement Ethereum public key retrieval"
    let mut public_key = EthereumPublicKey::default();

    let xpub = crypto::get_xpub(&msg.address_n)?;
    public_key.xpub = xpub.as_str().to_string();

    // TODO: hexlify(resp.node.public_key).decode()
    if matches!(msg.show_display, Some(true)) {
        ui::show_public_key(&public_key.xpub)?;
    }

    Ok(public_key)
}
