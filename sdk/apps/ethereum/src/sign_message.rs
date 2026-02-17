extern crate alloc;

use alloc::{string::String, vec};

use trezor_app_sdk::{Result, ui};

use crate::proto::ethereum::{EthereumMessageSignature, EthereumSignMessage};

/// Ethereum uses Bitcoin xpub format
pub fn sign_message(_msg: EthereumSignMessage) -> Result<EthereumMessageSignature> {
    // await paths.validate_path(keychain, msg.address_n)

    // node = keychain.derive(msg.address_n)
    // address = address_from_bytes(node.ethereum_pubkeyhash(), defs.network)
    // path = paths.address_n_to_str(msg.address_n)

    // await confirm_signverify(
    //     decode_message(msg.message), address, account="ETH", path=path, verify=False
    // )
    ui::confirm_value("Signing address", "address")?;

    // signature = secp256k1.sign(
    //     node.private_key(),
    //     message_digest(msg.message),
    //     False,
    //     secp256k1.CANONICAL_SIG_ETHEREUM,
    // )

    // TODO implement actual signing logic
    Ok(EthereumMessageSignature {
        signature: vec![0u8; 65],
        address: String::from("address"),
    })
}
