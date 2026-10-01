use crate::{
    helpers::{address_from_public_key, sha256},
    layout::{
        confirm_auth_final, confirm_authorized_invocation, require_confirm_auth_on_behalf_of,
        require_confirm_auth_signing_address,
    },
    proto::stellar::{
        SignSorobanAuthorization, SorobanAuthorizationSignature,
        sign_soroban_authorization::SorobanAuthorizationEnvelopeType,
    },
    sign_tx::sign_digest,
    writers::{
        write_hash_id_preimage_header, write_int64, write_sc_address,
        write_soroban_authorized_invocation, write_uint32,
    },
};
use trezor_app_sdk::{
    Error, Result, ResultExt,
    crypto::{self, HasherExt as _, HashingAlgorithm},
};

pub fn sign_soroban_authorization(
    msg: SignSorobanAuthorization,
) -> Result<SorobanAuthorizationSignature> {
    // Only the address-bound preimage variant introduced in Protocol 27 is supported
    if SorobanAuthorizationEnvelopeType::try_from(msg.envelope_type).ok()
        != Some(SorobanAuthorizationEnvelopeType::EnvelopeTypeSorobanAuthorizationWithAddress)
    {
        return Err(Error::DataError(
            "Stellar: unsupported authorization envelope type",
        ));
    }
    let auth = msg
        .soroban_authorization_with_address
        .as_ref()
        .ok_or(Error::DataError(
            "Stellar: missing soroban_authorization_with_address",
        ))?;

    let pubkey = crypto::get_public_key(&msg.address_n, false).c()?;
    let signing_address = address_from_public_key(&pubkey);

    // Serialize the ENVELOPE_TYPE_SOROBAN_AUTHORIZATION_WITH_ADDRESS preimage
    // (Protocol 27, CAP-46-11/CAP-71). It binds the signature to the
    // authorizing address.
    let network_id = sha256(msg.network_passphrase.as_bytes());

    let mut w = crypto::get_hasher(HashingAlgorithm::Sha256);
    write_hash_id_preimage_header(&mut w, msg.envelope_type as u32, &network_id);
    write_int64(&mut w, auth.nonce);
    write_uint32(&mut w, auth.signature_expiration_ledger);
    write_sc_address(&mut w, &auth.address).c()?;
    write_soroban_authorized_invocation(&mut w, &auth.invocation).c()?;

    require_confirm_auth_signing_address(&signing_address, &msg.address_n).c()?;

    if auth.address != signing_address {
        // The credentials belong to another party, e.g. a contract account of
        // which the device account is a signer.
        require_confirm_auth_on_behalf_of(&auth.address).c()?;
    }

    confirm_authorized_invocation(&auth.invocation, &network_id, &auth.address).c()?;
    confirm_auth_final(auth.signature_expiration_ledger, &msg.network_passphrase).c()?;

    let payload: [u8; 32] = w
        .finalize()
        .as_slice()
        .try_into()
        .map_err(|_| Error::DataError("Stellar: invalid digest"))?;
    let signature = sign_digest(&msg.address_n, &payload).c()?;

    Ok(SorobanAuthorizationSignature {
        public_key: pubkey,
        signature: signature.to_vec(),
    })
}
