use crypto::merkle::merkle_root;
use crypto::{cosi, ed25519, sha256};

use super::error::Error;
use super::{constants, generated};
use crate::io::InputStream;

fn verify_with_keys(
    threshold: u8,
    digest: &[u8],
    sig: &cosi::Signature,
    public_keys: &[ed25519::PublicKey; 3],
) -> Result<(), Error> {
    cosi::verify(threshold, digest, public_keys, sig).map_err(|_| Error::InvalidSignature)
}

fn verify(threshold: u8, digest: &[u8], sig: &cosi::Signature) -> Result<(), Error> {
    #[allow(unused_mut)]
    let mut result = verify_with_keys(threshold, digest, sig, &constants::PUBLIC_KEYS_PRODUCTION);

    #[cfg(feature = "dev_keys")]
    if result.is_err() {
        // allow development keys
        result = verify_with_keys(threshold, digest, sig, &constants::PUBLIC_KEYS_DEVEL);
    }

    result
}

/// Parse and verify a signed definition blob. Returns the protobuf payload.
///
/// Expects the definition format specified in
/// `docs/common/external-definitions.md`.
pub fn parse_and_verify(definition: &[u8], expected_type: u8) -> Result<&[u8], Error> {
    let mut reader = InputStream::new(definition);

    // magic
    if reader.read(constants::MAGIC.len())? != constants::MAGIC {
        return Err(Error::BadMagic);
    }

    // format version
    let version = constants::DefsVersion::try_from_byte(reader.read_byte()?)?;

    // definition type
    if reader.read_byte()? != expected_type {
        return Err(Error::UnexpectedType);
    }

    // data version
    let data_version = reader.read_u32_le()?;
    if data_version < generated::MIN_DATA_VERSION {
        return Err(Error::Outdated);
    }

    // payload
    let payload_len: usize = reader.read_u16_le()?.into();
    let payload = reader.read(payload_len)?;
    let payload_end = reader.tell();

    // Merkle proof
    let proof_len: usize = reader.read_byte()?.into();
    let proof_bytes = reader.read(proof_len * sha256::DIGEST_SIZE)?;
    // SAFETY: sha256::Digest is a plain array of u8, so any bytes are valid.
    let (_prefix, proof, _suffix) = unsafe { proof_bytes.align_to::<sha256::Digest>() };
    if !_prefix.is_empty() || !_suffix.is_empty() {
        return Err(Error::InvalidAlignment);
    }

    // CoSi signature
    let sigmask = reader.read_byte()?;
    let signature = cosi::Signature::new(
        sigmask,
        unwrap!(reader.read(ed25519::SIGNATURE_SIZE)?.try_into()),
    );

    // no trailing data
    if reader.remaining() > 0 {
        return Err(Error::TrailingData);
    }

    // compute Merkle tree root hash using the payload with prefix as leaf data
    // and verify the signature
    let merkle_root = merkle_root(&definition[..payload_end], proof);

    verify(version.threshold(), &merkle_root, &signature)?;

    Ok(payload)
}
