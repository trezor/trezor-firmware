//! Cross-implementation test vector generator for
//! Noise_pqIKpsk1_XWing_AESGCM_SHA256, built on the clatter PQNoise
//! implementation with a custom X-Wing KEM adapter
//! (draft-connolly-cfrg-xwing-kem-10).

use core::convert::Infallible;
use std::cell::RefCell;
use std::collections::VecDeque;

use clatter::crypto::cipher::AesGcm;
use clatter::crypto::hash::Sha256;
use clatter::error::KemResult;
use clatter::handshakepattern::noise_pqik_psk1;
use clatter::traits::{CryptoComponent, Handshaker, Kem, Rng};
use clatter::transportstate::TransportState;
use clatter::{KeyPair, PqHandshakeCore};

use ml_kem::array::Array;
use ml_kem::ml_kem_768::{
    Ciphertext as MlCiphertext, DecapsulationKey as MlDk, EncapsulationKey as MlEk,
};
use ml_kem::{B32, Decapsulate, Key, KeyExport, Seed};
use sha3::digest::{ExtendableOutput, Update, XofReader};
use sha3::{Digest, Sha3_256, Shake256};

const MLKEM_PK: usize = 1184;
const MLKEM_CT: usize = 1088;
const XWING_PK: usize = 1216;
const XWING_CT: usize = 1120;
const XWING_LABEL: [u8; 6] = [b'\\', b'.', b'/', b'/', b'^', b'\\'];

fn shake256_96(input: &[u8]) -> [u8; 96] {
    let mut xof = Shake256::default();
    xof.update(input);
    let mut reader = xof.finalize_xof();
    let mut out = [0u8; 96];
    reader.read(&mut out);
    out
}

fn combiner(ss_m: &[u8], ss_x: &[u8], ct_x: &[u8], pk_x: &[u8]) -> [u8; 32] {
    let mut h = Sha3_256::new();
    Digest::update(&mut h, ss_m);
    Digest::update(&mut h, ss_x);
    Digest::update(&mut h, ct_x);
    Digest::update(&mut h, pk_x);
    Digest::update(&mut h, XWING_LABEL);
    h.finalize().into()
}

fn expand(sk: &[u8; 32]) -> (MlDk, [u8; MLKEM_PK], [u8; 32]) {
    let expanded = shake256_96(sk);
    // FIPS 203 seed convention: d (32) || z (32)
    let seed = Seed::try_from(&expanded[0..64]).unwrap();
    let sk_x: [u8; 32] = expanded[64..96].try_into().unwrap();
    let dk = MlDk::from_seed(seed);
    let pk_m: [u8; MLKEM_PK] = dk.encapsulation_key().to_bytes().as_slice().try_into().unwrap();
    (dk, pk_m, sk_x)
}

fn xwing_pubkey(sk: &[u8; 32]) -> [u8; XWING_PK] {
    let (_, pk_m, sk_x) = expand(sk);
    let pk_x = x25519_dalek::x25519(sk_x, x25519_dalek::X25519_BASEPOINT_BYTES);
    let mut pk = [0u8; XWING_PK];
    pk[..MLKEM_PK].copy_from_slice(&pk_m);
    pk[MLKEM_PK..].copy_from_slice(&pk_x);
    pk
}

fn xwing_encaps_derand(seed: &[u8; 64], pk: &[u8; XWING_PK]) -> ([u8; XWING_CT], [u8; 32]) {
    let m_bytes: [u8; 32] = seed[0..32].try_into().unwrap();
    let m = m_bytes;
    let ek_x: [u8; 32] = seed[32..64].try_into().unwrap();
    let pk_x: [u8; 32] = pk[MLKEM_PK..].try_into().unwrap();

    let key: Key<MlEk> = Array::try_from(&pk[..MLKEM_PK]).unwrap();
    let ek = MlEk::new(&key).unwrap();
    let m: B32 = Array::from(m);
    let (ct_m, ss_m) = ek.encapsulate_deterministic(&m);

    let ct_x = x25519_dalek::x25519(ek_x, x25519_dalek::X25519_BASEPOINT_BYTES);
    let ss_x = x25519_dalek::x25519(ek_x, pk_x);

    let ss = combiner(ss_m.as_slice(), &ss_x, &ct_x, &pk_x);
    let mut ct = [0u8; XWING_CT];
    ct[..MLKEM_CT].copy_from_slice(ct_m.as_slice());
    ct[MLKEM_CT..].copy_from_slice(&ct_x);
    (ct, ss)
}

fn xwing_decaps(sk: &[u8; 32], ct: &[u8; XWING_CT]) -> [u8; 32] {
    let (dk, _, sk_x) = expand(sk);
    let ct_m: MlCiphertext = Array::try_from(&ct[..MLKEM_CT]).unwrap();
    let ct_x: [u8; 32] = ct[MLKEM_CT..].try_into().unwrap();
    let ss_m = dk.decapsulate(&ct_m);
    let ss_x = x25519_dalek::x25519(sk_x, ct_x);
    let pk_x = x25519_dalek::x25519(sk_x, x25519_dalek::X25519_BASEPOINT_BYTES);
    combiner(ss_m.as_slice(), &ss_x, &ct_x, &pk_x)
}

// --- clatter KEM adapter ---

#[derive(Clone)]
struct XWing;

impl CryptoComponent for XWing {
    fn name() -> &'static str {
        "XWing"
    }
}

impl Kem for XWing {
    type SecretKey = [u8; 32];
    type PubKey = [u8; XWING_PK];
    type Ct = [u8; XWING_CT];
    type Ss = [u8; 32];

    fn genkey_rng<R: Rng>(rng: &mut R) -> KemResult<KeyPair<Self::PubKey, Self::SecretKey>> {
        let mut seed = [0u8; 32];
        let _ = rng.try_fill_bytes(&mut seed);
        Ok(KeyPair::new(xwing_pubkey(&seed), seed))
    }

    fn encapsulate<R: Rng>(pk: &[u8], rng: &mut R) -> KemResult<(Self::Ct, Self::Ss)> {
        let mut seed = [0u8; 64];
        let _ = rng.try_fill_bytes(&mut seed);
        Ok(xwing_encaps_derand(&seed, pk.try_into().unwrap()))
    }

    fn decapsulate(ct: &[u8], sk: &[u8]) -> KemResult<Self::Ss> {
        let sk: [u8; 32] = sk.try_into().unwrap();
        let ct: [u8; XWING_CT] = ct.try_into().unwrap();
        Ok(xwing_decaps(&sk, &ct))
    }
}

// --- replay RNG fed from a thread-local queue ---

thread_local! {
    static RNG_QUEUE: RefCell<VecDeque<u8>> = const { RefCell::new(VecDeque::new()) };
}

fn queue_rng(bytes: &[u8]) {
    RNG_QUEUE.with(|q| q.borrow_mut().extend(bytes.iter().copied()));
}

fn assert_rng_empty() {
    RNG_QUEUE.with(|q| assert!(q.borrow().is_empty(), "rng queue not fully consumed"));
}

#[derive(Clone, Default)]
struct ReplayRng;

impl rand_core::TryRng for ReplayRng {
    type Error = Infallible;

    fn try_next_u32(&mut self) -> Result<u32, Infallible> {
        let mut b = [0u8; 4];
        self.try_fill_bytes(&mut b)?;
        Ok(u32::from_le_bytes(b))
    }

    fn try_next_u64(&mut self) -> Result<u64, Infallible> {
        let mut b = [0u8; 8];
        self.try_fill_bytes(&mut b)?;
        Ok(u64::from_le_bytes(b))
    }

    fn try_fill_bytes(&mut self, dst: &mut [u8]) -> Result<(), Infallible> {
        RNG_QUEUE.with(|q| {
            let mut q = q.borrow_mut();
            assert!(q.len() >= dst.len(), "rng queue underrun");
            for d in dst.iter_mut() {
                *d = q.pop_front().unwrap();
            }
        });
        Ok(())
    }
}

impl rand_core::TryCryptoRng for ReplayRng {}

// --- vector generation ---

type Handshake = PqHandshakeCore<XWing, XWing, AesGcm, Sha256, ReplayRng>;

struct Input {
    psk: [u8; 32],
    prologue: Vec<u8>,
    initiator_static: [u8; 32],
    responder_static: [u8; 32],
    ephemeral: [u8; 32],
    initiator_skem_seed: [u8; 64],
    responder_ekem_seed: [u8; 64],
    responder_skem_seed: [u8; 64],
    request_payload: Vec<u8>,
    response_payload: Vec<u8>,
    transport_i2r: Vec<u8>,
    transport_r2i: Vec<u8>,
}

fn pat(fill: u8, len: usize) -> Vec<u8> {
    (0..len).map(|i| fill.wrapping_add(i as u8)).collect()
}

fn arr<const N: usize>(fill: u8) -> [u8; N] {
    let mut a = [0u8; N];
    for (i, b) in a.iter_mut().enumerate() {
        *b = fill.wrapping_add(i as u8);
    }
    a
}

fn selfcheck() {
    // Official test vector from draft-connolly-cfrg-xwing-kem-10, Appendix C
    let sk: [u8; 32] =
        hex::decode("7f9c2ba4e88f827d616045507605853ed73b8093f6efbc88eb1a6eacfa66ef26")
            .unwrap()
            .try_into()
            .unwrap();
    let eseed: [u8; 64] = hex::decode(
        "3cb1eea988004b93103cfb0aeefd2a686e01fa4a58e8a3639ca8a1e3f9ae57e2\
         35b8cc873c23dc62b8d260169afa2f75ab916a58d974918835d25e6a435085b2",
    )
    .unwrap()
    .try_into()
    .unwrap();
    let expected_ss =
        hex::decode("d2df0522128f09dd8e2c92b1e905c793d8f57a54c3da25861f10bf4ca613e384").unwrap();

    let pk = xwing_pubkey(&sk);
    let (ct, ss) = xwing_encaps_derand(&eseed, &pk);
    assert_eq!(ss.as_slice(), expected_ss.as_slice(), "X-Wing encaps self-check failed");
    let ss2 = xwing_decaps(&sk, &ct);
    assert_eq!(ss2.as_slice(), expected_ss.as_slice(), "X-Wing decaps self-check failed");
    eprintln!("X-Wing self-check against draft-10 vector: OK");
}

fn hexdump(name: &str, data: &[u8]) {
    println!("          /* {} */", name);
    if data.is_empty() {
        println!("          \"\",");
        return;
    }
    for chunk in data.chunks(32) {
        println!("          \"{}\"", hex::encode(chunk));
    }
    println!("          ,");
}

fn run_vector(input: &Input) {
    let i_pub = xwing_pubkey(&input.initiator_static);
    let r_pub = xwing_pubkey(&input.responder_static);

    let mut initiator = Handshake::new(
        noise_pqik_psk1(),
        &input.prologue,
        true,
        Some(KeyPair::new(i_pub, input.initiator_static)),
        None,
        Some(r_pub),
        None,
    )
    .unwrap();
    initiator.push_psk(&input.psk);

    let mut responder = Handshake::new(
        noise_pqik_psk1(),
        &input.prologue,
        false,
        Some(KeyPair::new(r_pub, input.responder_static)),
        None,
        None,
        None,
    )
    .unwrap();
    responder.push_psk(&input.psk);

    // Message 1: the initiator consumes the skem encapsulation seed first,
    // then the ephemeral key generation seed
    queue_rng(&input.initiator_skem_seed);
    queue_rng(&input.ephemeral);
    let mut request = vec![0u8; 65535];
    let request_len = initiator.write_message(&input.request_payload, &mut request).unwrap();
    request.truncate(request_len);
    assert_rng_empty();

    let mut payload = vec![0u8; 65535];
    let n = responder.read_message(&request, &mut payload).unwrap();
    assert_eq!(&payload[..n], &input.request_payload[..], "request payload mismatch");

    // Message 2: the responder consumes the ekem seed first, then the skem seed
    queue_rng(&input.responder_ekem_seed);
    queue_rng(&input.responder_skem_seed);
    let mut response = vec![0u8; 65535];
    let response_len = responder.write_message(&input.response_payload, &mut response).unwrap();
    response.truncate(response_len);
    assert_rng_empty();

    let n = initiator.read_message(&response, &mut payload).unwrap();
    assert_eq!(&payload[..n], &input.response_payload[..], "response payload mismatch");

    assert!(initiator.is_finished() && responder.is_finished());

    let mut t_init = TransportState::new(initiator).unwrap();
    let mut t_resp = TransportState::new(responder).unwrap();

    let hash_i = t_init.get_handshake_hash();
    let hash_r = t_resp.get_handshake_hash();
    assert_eq!(hash_i.as_slice(), hash_r.as_slice(), "handshake hash mismatch");
    let handshake_hash = hash_i.as_slice().to_vec();

    let mut ct_i2r = vec![0u8; input.transport_i2r.len() + 16];
    let n = t_init.send(&input.transport_i2r, &mut ct_i2r).unwrap();
    assert_eq!(n, ct_i2r.len());
    let mut pt = vec![0u8; input.transport_i2r.len()];
    let n = t_resp.receive(&ct_i2r, &mut pt).unwrap();
    assert_eq!(&pt[..n], &input.transport_i2r[..]);

    let mut ct_r2i = vec![0u8; input.transport_r2i.len() + 16];
    let n = t_resp.send(&input.transport_r2i, &mut ct_r2i).unwrap();
    assert_eq!(n, ct_r2i.len());
    let mut pt = vec![0u8; input.transport_r2i.len()];
    let n = t_init.receive(&ct_r2i, &mut pt).unwrap();
    assert_eq!(&pt[..n], &input.transport_r2i[..]);

    // Emit a C struct initializer for test_check.c
    println!("      {{");
    hexdump("psk", &input.psk);
    hexdump("prologue", &input.prologue);
    hexdump("initiator_static_private_key", &input.initiator_static);
    hexdump("responder_static_private_key", &input.responder_static);
    hexdump("ephemeral_private_key", &input.ephemeral);
    hexdump("initiator_skem_seed", &input.initiator_skem_seed);
    hexdump("responder_ekem_seed", &input.responder_ekem_seed);
    hexdump("responder_skem_seed", &input.responder_skem_seed);
    hexdump("request_payload", &input.request_payload);
    hexdump("response_payload", &input.response_payload);
    hexdump("transport_i2r", &input.transport_i2r);
    hexdump("transport_r2i", &input.transport_r2i);
    hexdump("expected_request", &request);
    hexdump("expected_response", &response);
    hexdump("expected_handshake_hash", &handshake_hash);
    hexdump("expected_transport_i2r", &ct_i2r);
    hexdump("expected_transport_r2i", &ct_r2i);
    println!("      }},");
}

fn main() {
    selfcheck();

    let vectors = [
        // Empty payloads, empty prologue
        Input {
            psk: arr(0x10),
            prologue: vec![],
            initiator_static: arr(0x20),
            responder_static: arr(0x30),
            ephemeral: arr(0x40),
            initiator_skem_seed: arr(0x50),
            responder_ekem_seed: arr(0x60),
            responder_skem_seed: arr(0x70),
            request_payload: vec![],
            response_payload: vec![],
            transport_i2r: pat(0x80, 5),
            transport_r2i: pat(0x90, 5),
        },
        // Non-empty payloads and prologue
        Input {
            psk: arr(0x11),
            prologue: pat(0xa0, 17),
            initiator_static: arr(0x21),
            responder_static: arr(0x31),
            ephemeral: arr(0x41),
            initiator_skem_seed: arr(0x51),
            responder_ekem_seed: arr(0x61),
            responder_skem_seed: arr(0x71),
            request_payload: pat(0xb0, 13),
            response_payload: pat(0xc0, 42),
            transport_i2r: pat(0xd0, 33),
            transport_r2i: vec![],
        },
    ];

    for v in &vectors {
        run_vector(v);
    }
    eprintln!("all vectors generated OK");
}
