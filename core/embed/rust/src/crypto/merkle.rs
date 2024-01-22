use super::sha256;

/// Calculate a Merkle root based on a leaf element and a proof of inclusion.
///
/// Expects the Merkle tree format specified in `ethereum-definitions.md`.
pub fn merkle_root(elem: &[u8], proof: &[sha256::Digest]) -> sha256::Digest {
    let mut out = sha256::Digest::default();

    // hash the leaf element
    sha256::init_ctx!(ctx);
    ctx.update(&[0x00]);
    ctx.update(elem);
    ctx.finalize_into(&mut out);

    for proof_elem in proof {
        // hash together the current hash and the proof element
        let (min, max) = if &out < proof_elem {
            (&out, proof_elem)
        } else {
            (proof_elem, &out)
        };
        sha256::init_ctx!(ctx);
        ctx.update(&[0x01]);
        ctx.update(min);
        ctx.update(max);
        ctx.finalize_into(&mut out);
    }

    out
}
