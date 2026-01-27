use std::collections::VecDeque;
use std::sync::Once;

use super::vec::ChannelVec;
use super::*;
use crate::credential::{NullCredentialStore, NullCredentialVerifier};

struct RustCrypto;

impl Backend for RustCrypto {
    type DH = trezor_noise_rust_crypto::X25519;
    type Cipher = trezor_noise_rust_crypto::Aes256Gcm;
    type Hash = trezor_noise_rust_crypto::Sha256;

    fn random_bytes(dest: &mut [u8]) {
        getrandom::fill(dest).unwrap();
    }
}

const DEVICE_PROPERTIES: &[u8] = &[]; // FIXME
const PACKET_LEN: usize = 64;
type Packet = Vec<u8>;
type AppMsg = (u8, u16, Vec<u8>);

type HostCh = ChannelVec<host::ChannelOpen<NullCredentialStore, RustCrypto>>;
type DeviceCh = ChannelVec<device::ChannelOpen<NullCredentialVerifier, RustCrypto>>;

static SETUP: Once = Once::new();

fn setup() {
    SETUP.call_once(|| {
        env_logger::init_from_env(env_logger::Env::default().filter_or("RUST_LOG", "info"));
    })
}

fn take_turns<C1, C2>(ch1: &mut ChannelVec<C1>, ch2: &mut ChannelVec<C2>) -> Result<Option<AppMsg>>
where
    C1: ChannelIO,
    C2: ChannelIO,
{
    let mut msg = None;
    let mut wire = VecDeque::<Packet>::new();
    while ch1.packet_out_ready() || ch2.packet_out_ready() {
        while ch1.packet_out_ready() {
            wire.push_back(ch1.packet_out()?);
        }
        for packet in wire.iter() {
            log::trace!("> {}", hex::encode(packet));
            ch2.packet_in(packet)?;
        }
        if ch2.message_out_ready() {
            assert!(msg.is_none());
            msg = Some(ch2.message_out()?);
        }
        wire.clear();
        while ch2.packet_out_ready() {
            wire.push_back(ch2.packet_out()?);
        }
        for packet in wire.iter() {
            log::trace!("< {}", hex::encode(packet));
            ch1.packet_in(packet)?;
        }
        if ch1.message_out_ready() {
            assert!(msg.is_none());
            msg = Some(ch1.message_out()?);
        }
        wire.clear();
    }
    Ok(msg)
}

fn send<C1, C2>(
    ch1: &mut ChannelVec<C1>,
    ch2: &mut ChannelVec<C2>,
    sid: u8,
    mty: u16,
    message: &[u8],
) -> Result<()>
where
    C1: ChannelIO,
    C2: ChannelIO,
{
    ch1.message_in(sid, mty, message)?;
    let msg = take_turns(ch1, ch2)?.expect("a message");
    assert_eq!(msg, (sid, mty, message.into()));
    Ok(())
}

#[test]
fn test_open() -> Result<()> {
    setup();

    let mut h = HostCh::new(
        host::ChannelOpen::new(false, NullCredentialStore)?,
        PACKET_LEN,
    );
    let packet = h.packet_out()?;
    assert!(!h.packet_out_ready());

    let mut d = DeviceCh::new(
        device::ChannelOpen::new(&packet, 2026, DEVICE_PROPERTIES, NullCredentialVerifier)?,
        PACKET_LEN,
    );
    take_turns(&mut h, &mut d)?;
    assert!(h.handshake_done());
    assert!(d.handshake_done());
    let mut h = h.map(|h| h.complete())?;
    let mut d = d.map(|d| d.complete())?;

    send(&mut h, &mut d, 0, 1008, b"ThpPairingRequest placeholder")?;
    send(&mut d, &mut h, 0, 1009, b"ThpPairingResponse placeholder")?;
    send(&mut h, &mut d, 0, 1010, b"ThpSelectMethod with SkipParing")?;
    send(&mut d, &mut h, 0, 1019, b"ThpEndResponse means done")?;
    assert!(h.pairing_done());
    assert!(d.pairing_done());
    let mut h = h.map(|h| h.complete())?;
    let mut d = d.map(|d| d.complete())?;

    send(&mut h, &mut d, 0, 1234, b"Ping")?;
    send(&mut d, &mut h, 0, 5678, b"Pong")?;
    send(&mut h, &mut d, 1, 9999, &[0u8; 999])?;
    send(&mut d, &mut h, 1, 9998, &[9u8; 666])?;
    Ok(())
}
