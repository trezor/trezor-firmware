use super::sha256;

/// Calculate a Merkle root based on a leaf element and a proof of inclusion.
///
/// Expects the Merkle tree format specified in `external-definitions.md`.
pub fn merkle_root(elem: &[u8], proof: &[sha256::Digest]) -> sha256::Digest {
    // hash the leaf element
    let mut ctx = sha256::Sha256Ctx::default();
    let mut out = {
        let mut sha = sha256::Sha256::new(&mut ctx);
        sha.update(&[0x00]);
        sha.update(elem);
        sha.finalize()
    };

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

#[cfg(test)]
mod test {
    use super::*;

    fn hash(prefix: u8, parts: &[&[u8]]) -> sha256::Digest {
        let mut data = vec![prefix];
        parts.iter().for_each(|p| data.extend_from_slice(p));
        sha256::Sha256::digest(&data)
    }

    fn node(a: &sha256::Digest, b: &sha256::Digest) -> sha256::Digest {
        let (min, max) = if a < b { (a, b) } else { (b, a) };
        hash(0x01, &[min, max])
    }

    #[test]
    fn test_empty_proof() {
        assert_eq!(merkle_root(b"leaf", &[]), hash(0x00, &[b"leaf"]));
    }

    #[test]
    fn test_one_level_both_orders() {
        let leaf = hash(0x00, &[b"leaf"]);
        // a sibling smaller and larger than the leaf
        let smaller = [0x00; 32];
        let larger = [0xff; 32];
        assert_eq!(merkle_root(b"leaf", &[smaller]), node(&smaller, &leaf));
        assert_eq!(merkle_root(b"leaf", &[larger]), node(&leaf, &larger));
    }

    #[test]
    fn test_two_levels() {
        let leaf = hash(0x00, &[b"leaf"]);
        let (p1, p2) = ([0x11; 32], [0x22; 32]);
        let expected = node(&node(&leaf, &p1), &p2);
        assert_eq!(merkle_root(b"leaf", &[p1, p2]), expected);
    }
}
