use super::sha256;

/// Calculate a Merkle root based on a leaf element and a proof of inclusion.
///
/// Expects the Merkle tree format specified in `external-definitions.md`.
pub fn merkle_root(elem: &[u8], proof: &[sha256::Digest]) -> sha256::Digest {
    let mut ctx = sha256::Sha256Ctx::default();

    // hash the leaf element
    let mut sha = sha256::Sha256::new(&mut ctx);
    sha.update(&[0x00]);
    sha.update(elem);
    let mut out = sha.finalize();

    for proof_elem in proof {
        // hash together the current hash and the proof element
        let (min, max) = if &out < proof_elem {
            (&out, proof_elem)
        } else {
            (proof_elem, &out)
        };
        let mut sha = sha256::Sha256::new(&mut ctx);
        sha.update(&[0x01]);
        sha.update(min);
        sha.update(max);
        out = sha.finalize();
    }

    out
}
