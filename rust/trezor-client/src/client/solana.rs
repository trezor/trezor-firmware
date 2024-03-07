use super::{handle_interaction, Trezor};
use crate::{error::Result, protos};

impl Trezor {
    // SOLANA
    pub fn solana_get_address(&mut self, path: Vec<u32>) -> Result<String> {
        let mut req = protos::SolanaGetAddress::new();
        req.address_n = path;
        req.show_display = Some(true);
        let address = handle_interaction(
            self.call(req, Box::new(|_, m: protos::SolanaAddress| Ok(m.address().into())))?,
        )?;
        Ok(address)
    }
}
