use super::Trezor;
use crate::{error::Result, protos};

impl Trezor {
    // SOLANA
    pub fn solana_get_address(&mut self, path: Vec<u32>) -> Result<String> {
        let mut req = protos::SolanaGetAddress::new();
        req.address_n = path;
        req.show_display = Some(true);
        let m: protos::SolanaAddress = self.call(req)?;
        Ok(m.address().into())
    }
}
