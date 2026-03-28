use std::collections::{HashSet, VecDeque};
use std::ops::{Deref, DerefMut};
use std::sync::Once;

use super::super::crc32;
use super::buffered::{Buffered, ChannelExt};
use super::*;
use crate::{
    Device, Host,
    credential::{CredentialVerifier, NullCredentialStore},
    header::{BROADCAST_CHANNEL_ID, MAX_CHANNEL_ID, MIN_CHANNEL_ID},
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
const DEVICE_KEY: &[u8; PRIVKEY_LEN] = &[0u8; PRIVKEY_LEN];

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

    fn device_properties(&self) -> &[u8] {
        // internal_model: Some("T2W1"), model_variant: Some(0), protocol_version_major: Some(2),
        // protocol_version_minor: Some(0), pairing_methods: [CodeEntry, SkipPairing]
        b"\x0a\x04\x54\x32\x57\x31\x10\x00\x18\x02\x20\x00\x28\x02\x28\x01"
    }
}

pub struct WithKey<C: CredentialVerifier, B: Backend> {
    channel: super::device::ChannelOpen<C, B>,
    static_key: [u8; PRIVKEY_LEN],
}

impl<C: CredentialVerifier, B: Backend> WithKey<C, B> {
    fn unwrap(self) -> super::device::ChannelOpen<C, B> {
        self.channel
    }
}

impl<C: CredentialVerifier, B: Backend> ChannelIO for WithKey<C, B> {
    fn packet_in(&mut self, packet_buffer: &[u8], receive_buffer: &mut [u8]) -> PacketInResult {
        let pir = self.channel.packet_in(packet_buffer, receive_buffer);
        if matches!(pir, PacketInResult::HandshakeKeyRequired { .. }) {
            self.channel.set_static_key(&self.static_key).unwrap();
            return PacketInResult::Accepted {
                ack_received: false,
                message_ready: false,
                pong: false,
            };
        }
        pir
    }

    fn packet_in_ready(&self) -> bool {
        self.channel.packet_in_ready()
    }

    fn packet_out(&mut self, packet_buffer: &mut [u8], send_buffer: &[u8]) -> Result<()> {
        self.channel.packet_out(packet_buffer, send_buffer)
    }

    fn packet_out_ready(&self) -> bool {
        self.channel.packet_out_ready()
    }

    fn message_in(&mut self, plaintext_len: usize, send_buffer: &mut [u8]) -> Result<()> {
        self.channel.message_in(plaintext_len, send_buffer)
    }

    fn message_in_ready(&self) -> bool {
        self.channel.message_in_ready()
    }

    fn message_out<'a>(&mut self, receive_buffer: &'a mut [u8]) -> Result<(u8, u16, &'a [u8])> {
        self.channel.message_out(receive_buffer)
    }

    fn message_out_ready(&self) -> bool {
        self.channel.message_out_ready()
    }

    fn message_retransmit(&mut self) -> Result<()> {
        self.channel.message_retransmit()
    }
}

impl<C: CredentialVerifier, B: Backend> Deref for WithKey<C, B> {
    type Target = super::device::ChannelOpen<C, B>;

    fn deref(&self) -> &Self::Target {
        &self.channel
    }
}

impl<C: CredentialVerifier, B: Backend> DerefMut for WithKey<C, B> {
    fn deref_mut(&mut self) -> &mut Self::Target {
        &mut self.channel
    }
}

pub trait WithKeyExt<C: CredentialVerifier, B: Backend>: Sized {
    fn with_key(self, key: &[u8; PRIVKEY_LEN]) -> WithKey<C, B>;
}

impl<C: CredentialVerifier, B: Backend> WithKeyExt<C, B> for super::device::ChannelOpen<C, B> {
    fn with_key(self, key: &[u8; PRIVKEY_LEN]) -> WithKey<C, B> {
        WithKey {
            channel: self,
            static_key: *key,
        }
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

    let (mut hm, mut dm, mut cids) = create_mux();
    // channel allocation
    hm.request_channel(false);
    take_turns(&mut hm, &mut dm)?;
    let mut d = dm
        .channel_alloc(cids.get())?
        .with_key(DEVICE_KEY)
        .into_buffered();
    take_turns(&mut hm, &mut d)?;
    let mut h = hm.channel_alloc()?.into_buffered();

    // handshake
    assert!(!h.handshake_done());
    assert!(!d.handshake_done());
    take_turns(&mut h, &mut d)?;
    assert!(h.handshake_done());
    assert!(d.handshake_done());
    let mut h = h.map(|h| h.complete())?;
    let mut d = d.map(|d| d.unwrap().complete())?;

    // pairing
    HostToDevice.send(&mut h, &mut d, 0, 1008, b"ThpPairingRequest placeholder")?;
    DeviceToHost.send(&mut h, &mut d, 0, 1009, b"ThpPairingResponse placeholder")?;
    HostToDevice.send(&mut h, &mut d, 0, 1010, b"ThpSelectMethod with SkipParing")?;
    DeviceToHost.send(&mut h, &mut d, 0, 1019, b"ThpEndResponse means done")?;

    // application messaging
    HostToDevice.send(&mut h, &mut d, 0, 1234, b"Ping")?;
    DeviceToHost.send(&mut h, &mut d, 0, 5678, b"Pong")?;
    HostToDevice.send(&mut h, &mut d, 1, 9999, &[0u8; 999])?;
    DeviceToHost.send(&mut h, &mut d, 1, 9998, &[9u8; 666])?;
    Ok(())
}

#[test]
fn test_device_locked() -> Result<()> {
    setup();

    let (mut hm, mut dm, mut cids) = create_mux();
    // channel allocation
    hm.request_channel(false);
    take_turns(&mut hm, &mut dm)?;
    let mut d = dm.channel_alloc(cids.get())?.into_buffered();
    take_turns(&mut hm, &mut d)?;
    let mut h = hm.channel_alloc()?.into_buffered();

    // handshake
    assert!(!h.handshake_done());
    assert!(!d.handshake_done());
    take_turns(&mut h, &mut d)?;
    assert!(d.static_key_required());
    assert!(!d.handshake_failed());

    // static key not available
    d.send_device_locked()?;
    take_turns(&mut h, &mut d)?;
    assert!(h.handshake_failed());
    // TODO: either the host needs to ACK the error, or host transitions to ack after sending it
    // assert!(d.handshake_failed());
    Ok(())
}

fn create_mux() -> (
    Buffered<host::Mux<NullCredentialStore, RustCrypto>>,
    Buffered<device::Mux<TestCredentialVerifier, RustCrypto>>,
    device::ChannelIdAllocator,
) {
    let mut hm = host::Mux::<_, RustCrypto>::new(NullCredentialStore).into_buffered();
    hm.set_packet_len(DEFAULT_PACKET_LEN);
    let mut dm = device::Mux::<_, RustCrypto>::new(TestCredentialVerifier).into_buffered();
    dm.set_packet_len(DEFAULT_PACKET_LEN);
    let cids = device::ChannelIdAllocator::new_random::<RustCrypto>();
    (hm, dm, cids)
}

fn open_channel(
    packet_len: usize,
) -> Result<(
    Buffered<Channel<Host, RustCrypto>>,
    Buffered<Channel<Device, RustCrypto>>,
)> {
    let (mut hm, mut dm, mut cids) = create_mux();
    hm.set_packet_len(packet_len);
    dm.set_packet_len(packet_len);
    hm.request_channel(false);
    take_turns(&mut hm, &mut dm)?;
    let mut d = dm
        .channel_alloc(cids.get())?
        .with_key(DEVICE_KEY)
        .into_buffered();
    take_turns(&mut d, &mut hm)?;
    let mut h = hm.channel_alloc()?.into_buffered();
    take_turns(&mut h, &mut d)?;
    let h = h.map(|h| h.complete())?;
    let d = d.map(|d| d.unwrap().complete())?;

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
    let mut cids = device::ChannelIdAllocator::new_from(42).unwrap();

    let mut device_chans = Vec::<Buffered<Channel<Device, RustCrypto>>>::new();
    let mut host_chans = Vec::<Buffered<Channel<Host, RustCrypto>>>::new();

    // open channels
    for _i in 0..NHOSTS {
        let mut hm = host::Mux::<_, RustCrypto>::new(NullCredentialStore).into_buffered();
        hm.set_packet_len(DEFAULT_PACKET_LEN);
        hm.request_channel(false);
        take_turns(&mut hm, &mut dm)?;
        let mut d = dm
            .channel_alloc(cids.get())?
            .with_key(DEVICE_KEY)
            .into_buffered();
        take_turns(&mut d, &mut hm)?;
        let mut h = hm.channel_alloc()?.into_buffered();
        take_turns(&mut h, &mut d)?;
        let h = h.map(|h| h.complete())?;
        let d = d.map(|d| d.unwrap().complete())?;
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

    let (mut hm, mut dm, mut cids) = create_mux();
    // channel allocation request lost
    hm.request_channel(false);
    take_turns_mutate(&mut hm, &mut dm, lose_nth(HostToDevice, 0))?;
    assert!(!dm.channel_alloc_ready());

    // channel allocation response lost
    hm.request_channel(false);
    take_turns(&mut hm, &mut dm)?;
    let mut d = dm.channel_alloc(cids.get())?.into_buffered();
    take_turns_mutate(&mut hm, &mut d, lose_nth(DeviceToHost, 0))?;
    assert!(!hm.channel_alloc_ready());

    // successful allocation
    hm.request_channel(false);
    take_turns(&mut hm, &mut dm)?;
    let mut d = dm.channel_alloc(cids.get())?.into_buffered();
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

    let (mut hm, mut dm, mut cids) = create_mux();
    // channel allocation
    hm.request_channel(false);
    take_turns(&mut hm, &mut dm)?;
    let mut d = dm
        .channel_alloc(cids.get())?
        .with_key(DEVICE_KEY)
        .into_buffered();
    take_turns(&mut hm, &mut d)?;
    let mut h = hm.channel_alloc()?.into_buffered();

    // handshake
    take_turns_mutate(&mut h, &mut d, lose_nth(dir, lost_index))?;
    if dir == DeviceToHost {
        assert!(!h.handshake_done());
        assert_eq!(h.sending_retry(), None);
        assert_eq!(d.sending_retry(), Some(0));
        d.message_retransmit()?;
        assert_eq!(d.sending_retry(), Some(1));
    } else {
        assert!(!d.handshake_done());
        assert_eq!(d.sending_retry(), None);
        assert_eq!(h.sending_retry(), Some(0));
        h.message_retransmit()?;
        assert_eq!(h.sending_retry(), Some(1));
    }
    take_turns(&mut h, &mut d)?;
    let mut h = h.map(|h| h.complete())?;
    let mut d = d.map(|d| d.unwrap().complete())?;

    // pairing
    HostToDevice.send(&mut h, &mut d, 0, 1010, b"ThpSelectMethod with SkipParing")?;
    DeviceToHost.send(&mut h, &mut d, 0, 1019, b"ThpEndResponse means done")?;

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

    let (mut hm, mut dm, mut cids) = create_mux();
    // channel allocation request lost
    hm.request_channel(false);
    take_turns_mutate(&mut hm, &mut dm, damage_nth(HostToDevice, 0, byte_index))?;
    assert!(!dm.channel_alloc_ready());

    // channel allocation response lost
    hm.request_channel(false);
    take_turns(&mut hm, &mut dm)?;
    let mut d = dm.channel_alloc(cids.get())?.into_buffered();
    take_turns_mutate(&mut hm, &mut d, damage_nth(DeviceToHost, 0, byte_index))?;
    assert!(!hm.channel_alloc_ready());

    // successful allocation
    hm.request_channel(false);
    take_turns(&mut hm, &mut dm)?;
    let mut d = dm.channel_alloc(cids.get())?.into_buffered();
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

    let (mut hm, mut dm, mut cids) = create_mux();
    // channel allocation
    hm.request_channel(false);
    take_turns(&mut hm, &mut dm)?;
    let mut d = dm
        .channel_alloc(cids.get())?
        .with_key(DEVICE_KEY)
        .into_buffered();
    take_turns(&mut hm, &mut d)?;
    let mut h = hm.channel_alloc()?.into_buffered();

    // handshake
    take_turns_mutate(&mut h, &mut d, damage_nth(dir, packet_index, byte_index))?;
    if dir == DeviceToHost {
        assert!(!h.handshake_done());
        assert_eq!(h.sending_retry(), None);
        assert_eq!(d.sending_retry(), Some(0));
        d.message_retransmit()?;
        assert_eq!(d.sending_retry(), Some(1));
    } else {
        assert!(!d.handshake_done());
        assert_eq!(d.sending_retry(), None);
        assert_eq!(h.sending_retry(), Some(0));
        h.message_retransmit()?;
        assert_eq!(h.sending_retry(), Some(1));
    }
    take_turns(&mut h, &mut d)?;
    let mut h = h.map(|h| h.complete())?;
    let mut d = d.map(|d| d.unwrap().complete())?;

    // pairing
    HostToDevice.send(&mut h, &mut d, 0, 1010, b"ThpSelectMethod with SkipParing")?;
    DeviceToHost.send(&mut h, &mut d, 0, 1019, b"ThpEndResponse means done")?;

    // application messaging
    HostToDevice.send(&mut h, &mut d, 0, 1234, b"Ping")?;
    DeviceToHost.send(&mut h, &mut d, 0, 5678, b"Pong")?;
    Ok(())
}

#[test]
fn test_packet_damage_application() -> Result<()> {
    setup();

    let (mut h, mut d) = open_channel(DEFAULT_PACKET_LEN)?;
    h.message_in(0, 0, b"the quick brown fox jumps over the lazy dog")?;
    let res = take_turns_mutate(&mut h, &mut d, damage_nth(HostToDevice, 0, 16));
    assert_eq!(res, Err(Error::InvalidChecksum));
    h.message_retransmit().unwrap();
    take_turns(&mut h, &mut d)?;

    d.message_in(0, 0, b"the quick lazy dog crawls under the brown fox")?;
    let res = take_turns_mutate(&mut h, &mut d, damage_nth(DeviceToHost, 0, 50));
    assert_eq!(res, Err(Error::InvalidChecksum));
    d.message_retransmit().unwrap();
    take_turns(&mut h, &mut d)?;

    Ok(())
}

#[test]
fn test_codec_v1() -> Result<()> {
    setup();

    fn assert_ignored<C: ChannelIO>(channel: &mut Buffered<C>, packet: &[u8]) {
        let pir = channel.packet_in(&packet);
        assert!(matches!(pir, PacketInResult::Ignored { .. }));
        assert!(!channel.packet_out_ready());
    }

    let v1_init = "3f23230001000000080a0470696e671001000000000000000000000000000000\
                   0000000000000000000000000000000000000000000000000000000000000000";
    let v1_cont = "3f61616161616161616161616161616161616161616141414141414141414141\
                   4141414141414141414141414141414141414141414141414141414141414141";
    let v1_init = hex::decode(v1_init).unwrap();
    let v1_cont = hex::decode(v1_cont).unwrap();

    // broadcast handling
    let (mut hm, mut dm, _cids) = create_mux();
    // device::Mux shoud respond
    let pir = dm.packet_in(&v1_init);
    assert!(matches!(
        pir,
        PacketInResult::Accepted {
            ack_received: false,
            message_ready: false,
            pong: false
        }
    ));
    let response = dm.packet_out().unwrap();
    assert!(response.starts_with(b"?##"));
    assert!(!dm.packet_out_ready());
    // in other cases the packet should be ignored
    assert_ignored(&mut dm, &v1_cont);
    assert_ignored(&mut hm, &v1_init);
    assert_ignored(&mut hm, &v1_cont);

    // non-broadcast handling
    let (mut h, mut d) = open_channel(DEFAULT_PACKET_LEN)?;
    assert_ne!(h.channel_id, 0x2323);
    assert_ne!(d.channel_id, 0x2323);
    assert_ignored(&mut d, &v1_init);
    assert_ignored(&mut d, &v1_cont);
    assert_ignored(&mut h, &v1_init);
    assert_ignored(&mut h, &v1_cont);

    // non-broadcast handling, channel_id == "##"
    h.channel_id = 0x2323;
    d.channel_id = 0x2323;
    assert_ignored(&mut d, &v1_init);
    assert_ignored(&mut d, &v1_cont);
    assert_ignored(&mut h, &v1_init);
    assert_ignored(&mut h, &v1_cont);

    Ok(())
}

#[test]
fn test_ping() -> Result<()> {
    setup();

    let (mut hm, mut dm, _cids) = create_mux();
    // host->device ping
    hm.ping();
    let ping_packet = hm.packet_out()?;
    let pir = dm.packet_in(&ping_packet);
    assert!(matches!(
        pir,
        PacketInResult::Accepted {
            ack_received: false,
            message_ready: false,
            pong: false
        }
    ));
    let pong_packet = dm.packet_out()?;
    let pir = hm.packet_in(&pong_packet);
    assert!(matches!(
        pir,
        PacketInResult::Accepted {
            ack_received: false,
            message_ready: false,
            pong: true
        }
    ));
    assert!(pir.got_pong());
    // duplicates are ignored
    let pir = hm.packet_in(&pong_packet);
    assert!(matches!(pir, PacketInResult::Ignored { .. }));
    assert!(!pir.got_pong());

    // device->host ping is not implemented
    let pir = hm.packet_in(&ping_packet);
    assert!(matches!(pir, PacketInResult::Ignored { .. }));

    // non-broadcast channels ignore ping
    let (mut h, mut d) = open_channel(DEFAULT_PACKET_LEN)?;
    let pir = h.packet_in(&ping_packet);
    assert!(matches!(pir, PacketInResult::Ignored { .. }));
    let pir = d.packet_in(&ping_packet);
    assert!(matches!(pir, PacketInResult::Ignored { .. }));

    Ok(())
}

#[test]
fn test_invalid_channel_id() -> Result<()> {
    setup();

    const INVALID: &[u16] = &[
        MIN_CHANNEL_ID - 1,
        MAX_CHANNEL_ID + 1,
        BROADCAST_CHANNEL_ID - 1,
    ];

    fn make_packet(channel_id: u16) -> Vec<u8> {
        let mut res = Vec::new();
        res.push(0x04);
        res.push((channel_id >> 8) as u8);
        res.push((channel_id & 0xff) as u8);
        res.extend_from_slice(&[0x00, 0x10]);
        res.resize(DEFAULT_PACKET_LEN, 0x00);
        res
    }

    let (mut hm, mut dm, _cids) = create_mux();
    // muxes return Route(cid) for valid non-broadcast channel
    let pir = dm.packet_in(&make_packet(66));
    assert_eq!(pir, PacketInResult::Route { channel_id: 66 });
    let pir = hm.packet_in(&make_packet(66));
    assert_eq!(pir, PacketInResult::Route { channel_id: 66 });

    // muxes return error for invalid channel ids
    for channel_id in INVALID {
        assert_eq!(
            dm.packet_in(&make_packet(*channel_id)),
            PacketInResult::Ignored {
                error: Error::MalformedData
            }
        );
        assert_eq!(
            hm.packet_in(&make_packet(*channel_id)),
            PacketInResult::Ignored {
                error: Error::MalformedData
            }
        );
    }

    // normal channels return error for invalid ids
    let (mut h, mut d) = open_channel(DEFAULT_PACKET_LEN)?;
    for channel_id in INVALID {
        assert_eq!(
            d.packet_in(&make_packet(*channel_id)),
            PacketInResult::Ignored {
                error: Error::MalformedData
            }
        );
        assert_eq!(
            h.packet_in(&make_packet(*channel_id)),
            PacketInResult::Ignored {
                error: Error::MalformedData
            }
        );
    }

    Ok(())
}

// NOTE: does not work with CRC across packet boundary.
fn recompute_crc(wire: &mut VecDeque<Packet>) {
    let payload_len: usize = u16::from_be_bytes([wire[0][3], wire[0][4]]).into();
    let mut crc_start = 5 + payload_len - crc32::CHECKSUM_LEN;
    let mut buf = Vec::new();
    for p in wire.iter() {
        buf.extend_from_slice(p);
    }
    buf.truncate(crc_start);
    let checksum = crc32::digest(&buf);
    for i in 0..wire.len() {
        if crc_start > wire[i].len() {
            crc_start -= wire[i].len()
        } else {
            wire[i][crc_start..crc_start + crc32::CHECKSUM_LEN].copy_from_slice(&checksum);
            break;
        }
    }
}

fn damage_nth_fix_crc(
    dir: Direction,
    packet_index: usize,
    byte_index: usize,
) -> impl FnMut(Direction, &mut VecDeque<Packet>) {
    let mut index = Some(packet_index);
    return move |cur_dir: Direction, wire: &mut VecDeque<Packet>| {
        if dir != cur_dir {
            return;
        }
        let Some(pi) = index else {
            return;
        };
        if pi < wire.len() {
            // only way to damage continuations which are 1XXXXXXX (X = any)
            wire[pi][byte_index] ^= 0b1000_0000;
            recompute_crc(wire);
            log::trace!("damaged+crc {}", hex::encode(&wire[pi]));
            index = None;
        } else {
            index = Some(pi.checked_sub(wire.len()).unwrap());
        }
    };
}

#[test]
fn test_invalid_tag() -> Result<()> {
    setup();

    let (mut h, mut d) = open_channel(DEFAULT_PACKET_LEN)?;
    h.message_in(0, 404, b"hello world hello world hello")
        .unwrap();
    let res = take_turns_mutate(&mut h, &mut d, damage_nth_fix_crc(HostToDevice, 0, 10));
    assert_eq!(res, Err(Error::CryptoError));

    let (mut h, mut d) = open_channel(DEFAULT_PACKET_LEN)?;
    d.message_in(0, 403, b"hello world hello world hello")
        .unwrap();
    let res = take_turns_mutate(&mut h, &mut d, damage_nth_fix_crc(DeviceToHost, 0, 20));
    assert_eq!(res, Err(Error::CryptoError));

    Ok(())
}

#[test]
fn test_channel_id_wraparound() -> Result<()> {
    setup();

    fn alloc_test(
        hm: &mut Buffered<host::Mux<NullCredentialStore, RustCrypto>>,
        dm: &mut Buffered<device::Mux<TestCredentialVerifier, RustCrypto>>,
        cids: &mut device::ChannelIdAllocator,
        expected_id: u16,
    ) -> Result<()> {
        hm.request_channel(false);
        take_turns(hm, dm)?;
        let mut d = dm.channel_alloc(cids.get())?.into_buffered();
        take_turns(hm, &mut d)?;
        let h = hm.channel_alloc()?.into_buffered();
        assert_eq!(h.channel_id(), expected_id);
        Ok(())
    }

    let (mut hm, mut dm, _) = create_mux();
    let mut cids = device::ChannelIdAllocator::new_from(MAX_CHANNEL_ID - 1).unwrap();
    alloc_test(&mut hm, &mut dm, &mut cids, MAX_CHANNEL_ID - 1)?;
    alloc_test(&mut hm, &mut dm, &mut cids, MAX_CHANNEL_ID)?;
    alloc_test(&mut hm, &mut dm, &mut cids, MIN_CHANNEL_ID)?;
    alloc_test(&mut hm, &mut dm, &mut cids, MIN_CHANNEL_ID + 1)?;

    Ok(())
}
