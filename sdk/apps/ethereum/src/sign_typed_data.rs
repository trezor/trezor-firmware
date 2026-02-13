extern crate alloc;

use alloc::vec::Vec;
use alloc::{string::String, vec};

use trezor_app_sdk::{
    ui, {Error, Result},
};

use crate::common::{Bip32Path, require_confirm_address};
use crate::proto::ethereum::EthereumTypedDataSignature;
use crate::proto::ethereum_eip712::EthereumSignTypedData;

/// Ethereum uses Bitcoin xpub format
pub fn sign_typed_data(msg: EthereumSignTypedData) -> Result<EthereumTypedDataSignature> {
    let dp = Bip32Path::from_slice(&msg.address_n);

    // msg.primary_type
    // msg.metamask_v4_compat
    // msg.definitions
    // msg.show_message_hash

    // #[prost(uint32, repeated, packed = "false", tag = "1")]
    // pub address_n: ::prost::alloc::vec::Vec<u32>,
    // /// name of the root message struct
    // #[prost(string, required, tag = "2")]
    // pub primary_type: ::prost::alloc::string::String,
    // /// use MetaMask v4 (see <https://github.com/MetaMask/eth-sig-util/issues/106>)
    // #[prost(bool, optional, tag = "3", default = "true")]
    // pub metamask_v4_compat: ::core::option::Option<bool>,
    // /// network and/or token definitions
    // #[prost(message, optional, tag = "4")]
    // pub definitions: ::core::option::Option<super::ethereum::EthereumDefinitions>,
    // /// hash of the typed data to be signed (if set, user will be asked to confirm before signing)
    // #[prost(bytes = "vec", optional, tag = "5")]
    // pub show_message_hash: ::core::option::Option<::prost::alloc::vec::Vec<u8>>,

    // await paths.validate_path(keychain, msg.address_n)

    // node = keychain.derive(msg.address_n)
    // address_bytes: bytes = node.ethereum_pubkeyhash()

    let hash = vec![0u8; 32]; // TODO: generate actual hash of the typed data

    // # Display address so user can validate it
    require_confirm_address(&hash, None, None, None, None, None)?;

    // data_hash = await _generate_typed_data_hash(
    //     msg.primary_type, msg.metamask_v4_compat, msg.show_message_hash
    // )

    // progress_obj = progress(title=TR.progress__signing_transaction)
    // progress_obj.report(600)
    // signature = secp256k1.sign(
    //     node.private_key(), data_hash, False, secp256k1.CANONICAL_SIG_ETHEREUM
    // )
    // progress_obj.stop()

    // return EthereumTypedDataSignature(
    //     address=address_from_bytes(address_bytes, defs.network),
    //     signature=signature[1:] + signature[0:1],
    // )

    let sig = EthereumTypedDataSignature::default();

    // TODO implement actual signing logic
    Ok(sig)
}
