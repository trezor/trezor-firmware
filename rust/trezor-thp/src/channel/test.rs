use std::collections::{HashSet, VecDeque};
use std::sync::Once;

use super::buffered::{Buffered, ChannelExt};
use super::*;
use crate::{
    Device, Host,
    credential::{CREDENTIAL_PRIVKEY_LEN, CredentialVerifier, NullCredentialStore},
};

use test_case::{test_case, test_matrix};

struct RustCrypto;

impl Backend for RustCrypto {
    type DH = trezor_noise_rust_crypto::X25519;
    type Cipher = trezor_noise_rust_crypto::Aes256Gcm;
    type Hash = trezor_noise_rust_crypto::Sha256;

    fn random_bytes(dest: &mut [u8]) {
        getrandom::fill(dest).unwrap();
    }
}

type Packet = Vec<u8>;
type AppMsg = (u8, u16, Vec<u8>);

#[derive(Debug, PartialEq, Eq, Clone, Copy)]
enum Direction {
    HostToDevice,
    DeviceToHost,
}

use Direction::*;

type TakeTurnsResult = Option<(Direction, AppMsg)>;

const DEFAULT_PACKET_LEN: usize = 64;
static SETUP: Once = Once::new();

fn setup() {
    SETUP.call_once(|| {
        env_logger::init_from_env(env_logger::Env::default().filter_or("RUST_LOG", "info"));
    })
}

/// Uses all-zero privkey, verification always fails.
#[derive(Clone)]
pub struct TestCredentialVerifier;

impl CredentialVerifier for TestCredentialVerifier {
    fn verify(&self, _remote_static_pubkey: &[u8], _credential: &[u8]) -> PairingState {
        PairingState::Unpaired
    }

    fn static_privkey(&self) -> &[u8; CREDENTIAL_PRIVKEY_LEN] {
        // Do not do this in production code.
        static KEY: [u8; CREDENTIAL_PRIVKEY_LEN] = [0u8; CREDENTIAL_PRIVKEY_LEN];
        &KEY
    }

    fn device_properties(&self) -> &[u8] {
        // internal_model: Some("T2W1"), model_variant: Some(0), protocol_version_major: Some(2),
        // protocol_version_minor: Some(0), pairing_methods: [CodeEntry, SkipPairing]
        b"\x0a\x04\x54\x32\x57\x31\x10\x00\x18\x02\x20\x00\x28\x02\x28\x01"
    }
}

fn take_turns_mutate<C1, C2, F>(
    host: &mut Buffered<C1>,
    device: &mut Buffered<C2>,
    mut func: F,
) -> Result<TakeTurnsResult>
where
    C1: ChannelIO,
    C2: ChannelIO,
    F: FnMut(Direction, &mut VecDeque<Packet>),
{
    let mut msg = TakeTurnsResult::None;
    let mut wire = VecDeque::<Packet>::new();
    while host.packet_out_ready() || device.packet_out_ready() {
        while host.packet_out_ready() {
            wire.push_back(host.packet_out()?);
        }
        if !wire.is_empty() {
            func(HostToDevice, &mut wire);
        }
        for packet in wire.iter() {
            log::trace!("> {}", hex::encode(packet));
            device.packet_in(packet).check_failed()?;
        }
        if device.message_out_ready() {
            assert!(msg.is_none());
            msg = Some((HostToDevice, device.message_out()?));
        }
        wire.clear();
        while device.packet_out_ready() {
            wire.push_back(device.packet_out()?);
        }
        if !wire.is_empty() {
            func(DeviceToHost, &mut wire);
        }
        for packet in wire.iter() {
            log::trace!("< {}", hex::encode(packet));
            host.packet_in(packet).check_failed()?;
        }
        if host.message_out_ready() {
            assert!(msg.is_none());
            msg = Some((DeviceToHost, host.message_out()?));
        }
        wire.clear();
    }
    Ok(msg)
}

fn take_turns<C1, C2>(host: &mut Buffered<C1>, device: &mut Buffered<C2>) -> Result<TakeTurnsResult>
where
    C1: ChannelIO,
    C2: ChannelIO,
{
    take_turns_mutate(host, device, |_, _| {})
}

impl Direction {
    fn send_nocheck<C1, C2>(
        self,
        host: &mut Buffered<C1>,
        device: &mut Buffered<C2>,
        sid: u8,
        mty: u16,
        message: &[u8],
    ) -> Result<TakeTurnsResult>
    where
        C1: ChannelIO,
        C2: ChannelIO,
    {
        if self == HostToDevice {
            host.message_in(sid, mty, message)?;
        } else {
            device.message_in(sid, mty, message)?;
        }
        take_turns(host, device)
    }

    fn send<C1, C2>(
        self,
        host: &mut Buffered<C1>,
        device: &mut Buffered<C2>,
        sid: u8,
        mty: u16,
        message: &[u8],
    ) -> Result<()>
    where
        C1: ChannelIO,
        C2: ChannelIO,
    {
        let msg = self.send_nocheck(host, device, sid, mty, message)?;
        assert_eq!(msg, Some((self, (sid, mty, message.into()))));
        Ok(())
    }

    fn send_noresult<C1: ChannelIO, C2: ChannelIO>(
        self,
        host: &mut Buffered<C1>,
        device: &mut Buffered<C2>,
        message: &[u8],
    ) -> Result<()> {
        let msg = self.send_nocheck(host, device, 10, 100, message)?;
        assert_eq!(msg, None);
        Ok(())
    }
}

#[test]
fn test_open() -> Result<()> {
    setup();

    let mut hm = host::Mux::<_, RustCrypto>::new(NullCredentialStore).into_buffered();
    hm.set_packet_len(DEFAULT_PACKET_LEN);
    let mut dm = device::Mux::<_, RustCrypto>::new(TestCredentialVerifier).into_buffered();
    dm.set_packet_len(DEFAULT_PACKET_LEN);
    // channel allocation
    hm.request_channel(false);
    take_turns(&mut hm, &mut dm)?;
    let mut d = dm.channel_alloc()?.into_buffered();
    take_turns(&mut hm, &mut d)?;
    let mut h = hm.channel_alloc()?.into_buffered();

    // handshake
    assert!(!h.handshake_done());
    assert!(!d.handshake_done());
    take_turns(&mut h, &mut d)?;
    assert!(h.handshake_done());
    assert!(d.handshake_done());
    let mut h = h.map(|h| h.complete())?;
    let mut d = d.map(|d| d.complete())?;

    // pairing
    HostToDevice.send(&mut h, &mut d, 0, 1008, b"ThpPairingRequest placeholder")?;
    DeviceToHost.send(&mut h, &mut d, 0, 1009, b"ThpPairingResponse placeholder")?;
    HostToDevice.send(&mut h, &mut d, 0, 1010, b"ThpSelectMethod with SkipParing")?;
    assert!(!h.pairing_done());
    assert!(!d.pairing_done());
    DeviceToHost.send(&mut h, &mut d, 0, 1019, b"ThpEndResponse means done")?;
    assert!(h.pairing_done());
    assert!(d.pairing_done());
    let mut h = h.map(|h| h.complete())?;
    let mut d = d.map(|d| d.complete())?;

    // application messaging
    HostToDevice.send(&mut h, &mut d, 0, 1234, b"Ping")?;
    DeviceToHost.send(&mut h, &mut d, 0, 5678, b"Pong")?;
    HostToDevice.send(&mut h, &mut d, 1, 9999, &[0u8; 999])?;
    DeviceToHost.send(&mut h, &mut d, 1, 9998, &[9u8; 666])?;
    Ok(())
}

fn open_channel(
    packet_len: usize,
) -> Result<(
    Buffered<Channel<Host, RustCrypto>>,
    Buffered<Channel<Device, RustCrypto>>,
)> {
    let mut hm = host::Mux::<_, RustCrypto>::new(NullCredentialStore).into_buffered();
    hm.set_packet_len(packet_len);
    let mut dm = device::Mux::<_, RustCrypto>::new(TestCredentialVerifier).into_buffered();
    dm.set_packet_len(packet_len);
    hm.request_channel(false);
    take_turns(&mut hm, &mut dm)?;
    let mut d = dm.channel_alloc()?.into_buffered();
    take_turns(&mut d, &mut hm)?;
    let mut h = hm.channel_alloc()?.into_buffered();
    take_turns(&mut h, &mut d)?;
    let mut h = h.map(|h| h.complete())?;
    let mut d = d.map(|d| d.complete())?;
    HostToDevice.send(&mut h, &mut d, 0, 1010, b"doesn't really matter")?;
    DeviceToHost.send(&mut h, &mut d, 0, 1019, b"only ThpEndResponse does")?;
    let h = h.map(|h| h.complete())?;
    let d = d.map(|d| d.complete())?;

    Ok((h, d))
}

#[test_case(10, 0; "empty messages")]
#[test_case(30, 1; "short messages")]
#[test_case(20, 2000; "medium messages")]
#[test_case(5, 59976; "huge messages")]
#[test_case(1000, 100; "lots of messages")]
fn test_messages(count: usize, length: usize) -> Result<()> {
    setup();
    let (mut h, mut d) = open_channel(DEFAULT_PACKET_LEN)?;
    let payload = vec![42u8; length];
    for _i in 0..count {
        HostToDevice.send(&mut h, &mut d, 10, 100, &payload)?;
        DeviceToHost.send(&mut h, &mut d, 10, 100, &payload)?;
    }
    Ok(())
}

#[test_case(17; "tiny")]
#[test_case(256; "medium")]
#[test_case(1500; "large")]
fn test_packet_length(packet_len: usize) -> Result<()> {
    setup();
    let (mut h, mut d) = open_channel(packet_len)?;
    let payload = vec![69u8; 3200];
    for _i in 0..10 {
        HostToDevice.send(&mut h, &mut d, 10, 100, &payload)?;
        DeviceToHost.send(&mut h, &mut d, 10, 100, &payload)?;
    }
    Ok(())
}

#[test]
fn test_one_device_multiple_hosts() -> Result<()> {
    const NHOSTS: usize = 4;
    setup();
    let mut dm = device::Mux::<_, RustCrypto>::new(TestCredentialVerifier).into_buffered();
    dm.set_packet_len(DEFAULT_PACKET_LEN);

    let mut device_chans = Vec::<Buffered<Channel<Device, RustCrypto>>>::new();
    let mut host_chans = Vec::<Buffered<Channel<Host, RustCrypto>>>::new();

    // open channels
    for _i in 0..NHOSTS {
        let mut hm = host::Mux::<_, RustCrypto>::new(NullCredentialStore).into_buffered();
        hm.set_packet_len(DEFAULT_PACKET_LEN);
        hm.request_channel(false);
        take_turns(&mut hm, &mut dm)?;
        let mut d = dm.channel_alloc()?.into_buffered();
        take_turns(&mut d, &mut hm)?;
        let mut h = hm.channel_alloc()?.into_buffered();
        take_turns(&mut h, &mut d)?;
        let mut h = h.map(|h| h.complete())?;
        let mut d = d.map(|d| d.complete())?;
        HostToDevice.send(&mut h, &mut d, 0, 1010, b"pls pair")?;
        DeviceToHost.send(&mut h, &mut d, 0, 1019, b"ok")?;
        let h = h.map(|h| h.complete())?;
        let d = d.map(|d| d.complete())?;
        device_chans.push(d);
        host_chans.push(h);
    }

    // check that channel ids are distinct
    let device_ids: HashSet<u16> = device_chans.iter().map(|c| c.channel_id()).collect();
    assert_eq!(device_ids.len(), NHOSTS);
    let host_ids: HashSet<u16> = host_chans.iter().map(|c| c.channel_id()).collect();
    assert_eq!(host_ids.len(), NHOSTS);

    // normal operation
    let payload = vec![67u8; 160];
    for i in 0..NHOSTS {
        HostToDevice.send(&mut host_chans[i], &mut device_chans[i], 10, 100, &payload)?;
        DeviceToHost.send(&mut host_chans[i], &mut device_chans[i], 10, 100, &payload)?;
    }

    // channel mismatch, packets should be ignored
    for i in 0..NHOSTS {
        HostToDevice.send_noresult(
            &mut host_chans[i],
            &mut device_chans[(i + 1) % NHOSTS],
            &payload,
        )?;
        DeviceToHost.send_noresult(
            &mut host_chans[(i + 1) % NHOSTS],
            &mut device_chans[i],
            &payload,
        )?;
    }

    Ok(())
}

fn lose_nth(dir: Direction, i: usize) -> impl FnMut(Direction, &mut VecDeque<Packet>) {
    let mut index = Some(i);
    return move |cur_dir: Direction, wire: &mut VecDeque<Packet>| {
        if dir != cur_dir {
            return;
        }
        if let Some(i) = index {
            if i < wire.len() {
                let packet = wire.remove(i).unwrap();
                log::trace!("drop {}", hex::encode(packet));
                index = None;
            } else {
                index = Some(i.checked_sub(wire.len()).unwrap());
            }
        }
    };
}

#[test]
fn test_packet_loss_alloc() -> Result<()> {
    setup();

    let mut hm = host::Mux::<_, RustCrypto>::new(NullCredentialStore).into_buffered();
    hm.set_packet_len(DEFAULT_PACKET_LEN);
    let mut dm = device::Mux::<_, RustCrypto>::new(TestCredentialVerifier).into_buffered();
    dm.set_packet_len(DEFAULT_PACKET_LEN);

    // channel allocation request lost
    hm.request_channel(false);
    take_turns_mutate(&mut hm, &mut dm, lose_nth(HostToDevice, 0))?;
    assert!(!dm.channel_alloc_ready());

    // channel allocation response lost
    hm.request_channel(false);
    take_turns(&mut hm, &mut dm)?;
    let mut d = dm.channel_alloc()?.into_buffered();
    take_turns_mutate(&mut hm, &mut d, lose_nth(DeviceToHost, 0))?;
    assert!(!hm.channel_alloc_ready());

    // successful allocation
    hm.request_channel(false);
    take_turns(&mut hm, &mut dm)?;
    let mut d = dm.channel_alloc()?.into_buffered();
    take_turns(&mut hm, &mut d)?;
    let mut _h = hm.channel_alloc()?.into_buffered();
    Ok(())
}

#[test_case(HostToDevice, 0; "handshake_init_request")]
//#[test_case(HostToDevice, 1; "handshake_init_response_ack")]
#[test_case(HostToDevice, 2; "handshake_completion_request")]
#[test_case(HostToDevice, 3; "handshake_completion_request_cont")]
//#[test_case(HostToDevice, 4, "handshake_completion_response_ack")]
//#[test_case(DeviceToHost, 0, "handshake_init_request_ack")]
#[test_case(DeviceToHost, 1; "handshake_init_response")]
#[test_case(DeviceToHost, 2; "handshake_init_response_cont")]
//#[test_case(DeviceToHost, 3; "handshake_completion_request_ack")]
#[test_case(DeviceToHost, 4; "handshake_completion_response")]
fn test_packet_loss_handshake(dir: Direction, lost_index: usize) -> Result<()> {
    setup();

    let mut hm = host::Mux::<_, RustCrypto>::new(NullCredentialStore).into_buffered();
    hm.set_packet_len(DEFAULT_PACKET_LEN);
    let mut dm = device::Mux::<_, RustCrypto>::new(TestCredentialVerifier).into_buffered();
    dm.set_packet_len(DEFAULT_PACKET_LEN);
    // channel allocation
    hm.request_channel(false);
    take_turns(&mut hm, &mut dm)?;
    let mut d = dm.channel_alloc()?.into_buffered();
    take_turns(&mut hm, &mut d)?;
    let mut h = hm.channel_alloc()?.into_buffered();

    // handshake
    take_turns_mutate(&mut h, &mut d, lose_nth(dir, lost_index))?;
    if dir == DeviceToHost {
        assert!(!h.handshake_done());
        d.message_retransmit()?;
    } else {
        assert!(!d.handshake_done());
        h.message_retransmit()?;
    }
    take_turns(&mut h, &mut d)?;
    let mut h = h.map(|h| h.complete())?;
    let mut d = d.map(|d| d.complete())?;

    // pairing
    HostToDevice.send(&mut h, &mut d, 0, 1010, b"ThpSelectMethod with SkipParing")?;
    DeviceToHost.send(&mut h, &mut d, 0, 1019, b"ThpEndResponse means done")?;
    let mut h = h.map(|h| h.complete())?;
    let mut d = d.map(|d| d.complete())?;

    // application messaging
    HostToDevice.send(&mut h, &mut d, 0, 1234, b"Ping")?;
    DeviceToHost.send(&mut h, &mut d, 0, 5678, b"Pong")?;
    Ok(())
}

fn damage_nth(
    dir: Direction,
    packet_index: usize,
    byte_index: usize,
) -> impl FnMut(Direction, &mut VecDeque<Packet>) {
    let mut index = Some(packet_index);
    return move |cur_dir: Direction, wire: &mut VecDeque<Packet>| {
        if dir != cur_dir {
            return;
        }
        if let Some(pi) = index {
            if pi < wire.len() {
                let packet = &mut wire[pi];
                // only way to damage continuations which are 1XXXXXXX (X = any)
                packet[byte_index] ^= 0b1000_0000;
                log::trace!("damaged {}", hex::encode(packet));
                index = None;
            } else {
                index = Some(pi.checked_sub(wire.len()).unwrap());
            }
        }
    };
}

#[test_case(0; "cb")]
#[test_case(1; "cid")]
#[test_case(3; "len")]
#[test_case(5; "data")]
fn test_packet_damage_alloc(byte_index: usize) -> Result<()> {
    setup();

    let mut hm = host::Mux::<_, RustCrypto>::new(NullCredentialStore).into_buffered();
    hm.set_packet_len(DEFAULT_PACKET_LEN);
    let mut dm = device::Mux::<_, RustCrypto>::new(TestCredentialVerifier).into_buffered();
    dm.set_packet_len(DEFAULT_PACKET_LEN);

    // channel allocation request lost
    hm.request_channel(false);
    take_turns_mutate(&mut hm, &mut dm, damage_nth(HostToDevice, 0, byte_index))?;
    assert!(!dm.channel_alloc_ready());

    // channel allocation response lost
    hm.request_channel(false);
    take_turns(&mut hm, &mut dm)?;
    let mut d = dm.channel_alloc()?.into_buffered();
    take_turns_mutate(&mut hm, &mut d, damage_nth(DeviceToHost, 0, byte_index))?;
    assert!(!hm.channel_alloc_ready());

    // successful allocation
    hm.request_channel(false);
    take_turns(&mut hm, &mut dm)?;
    let mut d = dm.channel_alloc()?.into_buffered();
    take_turns(&mut hm, &mut d)?;
    let mut _h = hm.channel_alloc()?.into_buffered();
    Ok(())
}

#[test_matrix(
    [HostToDevice, DeviceToHost],
    [0, 1, 2, 3, 4],
    [0, 1, 3, 6]
)]
fn test_packet_damage_handshake(
    dir: Direction,
    packet_index: usize,
    byte_index: usize,
) -> Result<()> {
    setup();

    // Don't test ACKs for now.
    let skip = [
        (HostToDevice, 1),
        (HostToDevice, 4),
        (DeviceToHost, 0),
        (DeviceToHost, 3),
    ];
    if skip.contains(&(dir, packet_index)) {
        log::warn!("Skipping test case");
        return Ok(());
    }

    let mut hm = host::Mux::<_, RustCrypto>::new(NullCredentialStore).into_buffered();
    hm.set_packet_len(DEFAULT_PACKET_LEN);
    let mut dm = device::Mux::<_, RustCrypto>::new(TestCredentialVerifier).into_buffered();
    dm.set_packet_len(DEFAULT_PACKET_LEN);
    // channel allocation
    hm.request_channel(false);
    take_turns(&mut hm, &mut dm)?;
    let mut d = dm.channel_alloc()?.into_buffered();
    take_turns(&mut hm, &mut d)?;
    let mut h = hm.channel_alloc()?.into_buffered();

    // handshake
    take_turns_mutate(&mut h, &mut d, damage_nth(dir, packet_index, byte_index))?;
    if dir == DeviceToHost {
        assert!(!h.handshake_done());
        d.message_retransmit()?;
    } else {
        assert!(!d.handshake_done());
        h.message_retransmit()?;
    }
    take_turns(&mut h, &mut d)?;
    let mut h = h.map(|h| h.complete())?;
    let mut d = d.map(|d| d.complete())?;

    // pairing
    HostToDevice.send(&mut h, &mut d, 0, 1010, b"ThpSelectMethod with SkipParing")?;
    DeviceToHost.send(&mut h, &mut d, 0, 1019, b"ThpEndResponse means done")?;
    let mut h = h.map(|h| h.complete())?;
    let mut d = d.map(|d| d.complete())?;

    // application messaging
    HostToDevice.send(&mut h, &mut d, 0, 1234, b"Ping")?;
    DeviceToHost.send(&mut h, &mut d, 0, 5678, b"Pong")?;
    Ok(())
}

// TODO invalid channel id
// TODO good CRC but invalid tag
// TODO codec_v1
