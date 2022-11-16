//! Test are placed here to be executed by `make test_rust`.

use blake2b_simd::*;

const EMPTY_HASH: [u8; 64] = [
    120, 106, 2, 247, 66, 1, 89, 3, 198, 198, 253, 133, 37, 82, 210, 114, 145, 47, 71, 64, 225, 88,
    71, 97, 138, 134, 226, 23, 247, 31, 84, 25, 210, 94, 16, 49, 175, 238, 88, 83, 19, 137, 100,
    68, 147, 78, 176, 75, 144, 58, 104, 91, 20, 72, 183, 85, 213, 111, 112, 26, 254, 155, 226, 206,
];
const ABC_HASH: [u8; 64] = [
    186, 128, 165, 63, 152, 28, 77, 13, 106, 39, 151, 182, 159, 18, 246, 233, 76, 33, 47, 20, 104,
    90, 196, 183, 75, 18, 187, 111, 219, 255, 162, 209, 125, 135, 197, 57, 42, 171, 121, 45, 194,
    82, 213, 222, 69, 51, 204, 149, 24, 211, 138, 168, 219, 241, 146, 90, 185, 35, 134, 237, 212,
    0, 153, 35,
];
const ONE_BLOCK_HASH: [u8; 64] = [
    134, 89, 57, 225, 32, 230, 128, 84, 56, 71, 136, 65, 175, 183, 57, 174, 66, 80, 207, 55, 38,
    83, 7, 138, 6, 92, 220, 255, 252, 164, 202, 247, 152, 230, 212, 98, 182, 93, 101, 143, 193,
    101, 120, 38, 64, 237, 237, 112, 150, 52, 73, 174, 21, 0, 251, 15, 36, 152, 29, 119, 39, 226,
    44, 65,
];
const THOUSAND_HASH: [u8; 64] = [
    30, 228, 229, 30, 202, 181, 33, 10, 81, 143, 38, 21, 14, 136, 38, 39, 236, 131, 153, 103, 241,
    157, 118, 62, 21, 8, 177, 44, 254, 254, 209, 72, 88, 246, 161, 201, 209, 249, 105, 188, 34, 77,
    201, 68, 15, 90, 105, 85, 39, 126, 117, 91, 156, 81, 63, 155, 164, 66, 28, 94, 80, 200, 215,
    135,
];

#[test]
fn test_update_state() {
    let io = &[
        (&b""[..], EMPTY_HASH),
        (&b"abc"[..], ABC_HASH),
        (&[0; 128], ONE_BLOCK_HASH),
        (&[0; 1000], THOUSAND_HASH),
    ];
    // Test each input all at once.
    for &(input, output) in io {
        let hash = blake2b(input);
        assert_eq!(hash.as_bytes(), &output, "hash mismatch");
    }
    // Now in two chunks. This is especially important for the ONE_BLOCK case,
    // because it would be a mistake for update() to call compress, even though
    // the buffer is full.
    for &(input, output) in io {
        let mut state = State::new();
        let split = input.len() / 2;
        state.update(&input[..split]);
        state.update(&input[split..]);
        let hash = state.finalize();
        assert_eq!(hash.as_bytes(), &output, "hash mismatch");
    }
    // Now one byte at a time.
    for &(input, output) in io {
        let mut state = State::new();
        for &b in input {
            state.update(&[b]);
        }
        let hash = state.finalize();
        assert_eq!(hash.as_bytes(), &output, "hash mismatch");
    }
}
