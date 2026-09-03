use crypto::merkle::merkle_root;
use crypto::{cosi, ed25519, sha256};

use super::{constants, generated};
use crate::error::Error;
use crate::io::InputStream;

const INVALID_DEFINITION: Error = Error::ExternalDataError(c"Invalid definition");
const INVALID_SIGNATURE: Error = Error::ExternalDataError(c"Invalid definition signature");

fn read<'a>(reader: &mut InputStream<'a>, len: usize) -> Result<&'a [u8], Error> {
    reader.read(len).map_err(|_| INVALID_DEFINITION)
}

fn read_byte(reader: &mut InputStream<'_>) -> Result<u8, Error> {
    reader.read_byte().map_err(|_| INVALID_DEFINITION)
}

fn verify_with_keys(
    threshold: u8,
    digest: &[u8],
    sig: &cosi::Signature,
    public_keys: &[ed25519::PublicKey; 3],
) -> Result<(), Error> {
    cosi::verify(threshold, digest, public_keys, sig).map_err(|_| INVALID_SIGNATURE)
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
    if read(&mut reader, constants::MAGIC.len())? != constants::MAGIC {
        return Err(INVALID_DEFINITION);
    }

    // format version
    let version =
        constants::DefsVersion::from_byte(read_byte(&mut reader)?).ok_or(INVALID_DEFINITION)?;

    // definition type
    if read_byte(&mut reader)? != expected_type {
        return Err(Error::ExternalDataError(c"Definition type mismatch"));
    }

    // data version
    let data_version = reader.read_u32_le().map_err(|_| INVALID_DEFINITION)?;
    if data_version < generated::MIN_DATA_VERSION {
        return Err(Error::ExternalDataError(c"Definition is outdated"));
    }

    // payload
    let payload_len: usize = reader.read_u16_le().map_err(|_| INVALID_DEFINITION)?.into();
    let payload = read(&mut reader, payload_len)?;
    let payload_end = reader.tell();

    // Merkle proof
    let proof_len: usize = read_byte(&mut reader)?.into();
    let proof_bytes = read(&mut reader, proof_len * sha256::DIGEST_SIZE)?;
    // SAFETY: sha256::Digest is a plain array of u8, so any bytes are valid.
    let (_prefix, proof, _suffix) = unsafe { proof_bytes.align_to::<sha256::Digest>() };
    if !_prefix.is_empty() || !_suffix.is_empty() {
        return Err(INVALID_DEFINITION);
    }

    // CoSi signature
    let sigmask = read_byte(&mut reader)?;
    let signature = cosi::Signature::new(
        sigmask,
        unwrap!(read(&mut reader, ed25519::SIGNATURE_SIZE)?.try_into()),
    );

    // no trailing data
    if reader.remaining() > 0 {
        return Err(INVALID_DEFINITION);
    }

    // compute Merkle tree root hash using the payload with prefix as leaf data
    // and verify the signature
    let merkle_root = merkle_root(&definition[..payload_end], proof);

    verify(version.threshold(), &merkle_root, &signature)?;

    Ok(payload)
}
