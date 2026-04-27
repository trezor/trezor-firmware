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

// internal_model: Some("T2W1"), model_variant: Some(0), protocol_version_major: Some(2),
// protocol_version_minor: Some(0), pairing_methods: [CodeEntry, SkipPairing]
const DEVICE_PROPERTIES: &[u8] =
    b"\x0a\x04\x54\x32\x57\x31\x10\x00\x18\x02\x20\x00\x28\x02\x28\x01";

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
                buffer_size: None,
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

fn take_turns_until_fn<C1, C2, Fu, Fw, T>(
    until_func: &mut Fu,
    host: &mut Buffered<C1>,
    device: &mut Buffered<C2>,
    wire_func: &mut Fw,
) -> Result<Option<T>>
where
    C1: ChannelIO,
    C2: ChannelIO,
    Fu: FnMut(Direction, &mut Buffered<C1>, &mut Buffered<C2>, PacketInResult) -> Option<T>,
    Fw: FnMut(Direction, &mut VecDeque<Packet>),
{
    while host.packet_out_ready() || device.packet_out_ready() {
        let pir = HostToDevice.transfer_fn(host, device, wire_func)?;
        let res = until_func(HostToDevice, host, device, pir);
        if res.is_some() {
            return Ok(res);
        }
        let pir = DeviceToHost.transfer_fn(host, device, wire_func)?;
        let res = until_func(DeviceToHost, host, device, pir);
        if res.is_some() {
            return Ok(res);
        }
    }
    Ok(None)
}

fn until_stuck(
    _dir: Direction,
    _h: &mut Buffered<impl ChannelIO>,
    _d: &mut Buffered<impl ChannelIO>,
    _pir: PacketInResult,
) -> Option<()> {
    None
}

fn wire_flush_acks(_dir: Direction, wire: &mut VecDeque<Packet>) {
    for packet in wire.iter() {
        Header::<Host>::parse(packet)
            .map(|(hdr, _)| assert!(hdr.is_ack()))
            .unwrap();
    }
}

fn take_turns_fn<C1, C2, F>(
    host: &mut Buffered<C1>,
    device: &mut Buffered<C2>,
    wire_func: &mut F,
) -> Result<TakeTurnsResult>
where
    C1: ChannelIO,
    C2: ChannelIO,
    F: FnMut(Direction, &mut VecDeque<Packet>),
{
    let mut message_ready = |dir, host: &mut Buffered<C1>, device: &mut Buffered<C2>, _pir| {
        if dir == HostToDevice && device.message_out_ready() {
            return Some((HostToDevice, device.message_out().unwrap()));
        } else if dir == DeviceToHost && host.message_out_ready() {
            return Some((DeviceToHost, host.message_out().unwrap()));
        }
        None
    };
    let res = take_turns_until_fn(&mut message_ready, host, device, wire_func);
    take_turns_until_fn(&mut until_stuck, host, device, &mut wire_flush_acks)?;
    res
}

fn take_turns<C1, C2>(host: &mut Buffered<C1>, device: &mut Buffered<C2>) -> Result<TakeTurnsResult>
where
    C1: ChannelIO,
    C2: ChannelIO,
{
    take_turns_fn(host, device, &mut |_, _| ())
}

impl Direction {
    fn reverse_if(&self, cond: bool) -> Self {
        if !cond {
            return *self;
        }
        match self {
            HostToDevice => DeviceToHost,
            DeviceToHost => HostToDevice,
        }
    }
    fn reverse(&self) -> Self {
        self.reverse_if(true)
    }

    fn transfer_fn<C1, C2>(
        self,
        host: &mut Buffered<C1>,
        device: &mut Buffered<C2>,
        func: &mut impl FnMut(Direction, &mut VecDeque<Packet>),
    ) -> Result<PacketInResult>
    where
        C1: ChannelIO,
        C2: ChannelIO,
    {
        let mut wire = VecDeque::<Packet>::new();
        let mut pir = PacketInResult::Ignored {
            error: Error::NotReady,
        };
        if self == HostToDevice {
            while host.packet_out_ready() {
                wire.push_back(host.packet_out()?);
            }
        } else {
            while device.packet_out_ready() {
                wire.push_back(device.packet_out()?);
            }
        }
        func(self, &mut wire);
        for packet in wire.iter() {
            // Only the last PacketInResult is returned, check that the others are "boring".
            assert!(matches!(
                pir,
                PacketInResult::Ignored { .. }
                    | PacketInResult::Accepted {
                        message_ready: false,
                        pong: false,
                        ..
                    }
            ));
            if self == HostToDevice {
                log::trace!("> {}", hex::encode(packet));
                pir = device.packet_in(packet).check_failed()?;
            } else {
                log::trace!("< {}", hex::encode(packet));
                pir = host.packet_in(packet).check_failed()?;
            }
        }
        Ok(pir)
    }

    fn transfer(
        self,
        host: &mut Buffered<impl ChannelIO>,
        device: &mut Buffered<impl ChannelIO>,
    ) -> Result<PacketInResult> {
        self.transfer_fn(host, device, &mut |_, _| ())
    }

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
        if self == HostToDevice {
            assert_eq!(msg, Some((HostToDevice, (sid, mty, message.into()))));
        } else {
            assert_eq!(msg, Some((DeviceToHost, (sid, mty, message.into()))));
        }
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

    fn call<C1: ChannelIO, C2: ChannelIO>(
        self,
        host: &mut Buffered<C1>,
        device: &mut Buffered<C2>,
        msgs: &[&[u8]],
    ) -> Result<()> {
        let mut i: usize = 0;
        let mut func = |dir, host: &mut Buffered<C1>, device: &mut Buffered<C2>, _pir| {
            if dir == HostToDevice && device.message_out_ready() {
                let (_, _, msg) = device.message_out().unwrap();
                assert_eq!(msg, msgs[i]);
                i += 1;
                if i < msgs.len() {
                    device.message_in(5, 10, msgs[i]).unwrap();
                }
            } else if dir == DeviceToHost && host.message_out_ready() {
                let (_, _, msg) = host.message_out().unwrap();
                assert_eq!(msg, msgs[i]);
                i += 1;
                if i < msgs.len() {
                    host.message_in(5, 11, msgs[i]).unwrap();
                }
            }
            None::<()>
        };
        if self == HostToDevice {
            host.message_in(5, 10, msgs[0])?;
        } else {
            device.message_in(5, 11, msgs[0])?;
        }
        take_turns_until_fn(&mut func, host, device, &mut |_, _| ())?;
        assert_eq!(i, msgs.len());
        Ok(())
    }
}

#[test]
fn test_open() -> Result<()> {
    setup();

    let (mut h, mut d) = alloc_channel()?;

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

fn check_number_of_packets(mut counts: Vec<usize>) -> impl FnMut(Direction, &mut VecDeque<Packet>) {
    let mut turn: usize = 0;
    counts.reverse();
    return move |_: Direction, wire: &mut VecDeque<Packet>| {
        turn += 1;
        let count = counts.pop().unwrap_or(0);
        assert!(
            wire.len() == count,
            "Turn {}: expected {} packets, got {:?}.",
            turn,
            count,
            wire.iter().map(hex::encode).collect::<Vec<_>>(),
        );
    };
}

fn check_just_one(dir: Direction, wire: &mut VecDeque<Packet>) {
    check_number_of_packets(vec![1])(dir, wire)
}

#[test]
fn test_open_piggybacking() -> Result<()> {
    setup();

    let (mut h, mut d) = alloc_channel()?;
    h.set_device_protocol_version(2, 1); // Enable piggybacking.

    // handshake
    assert!(!h.handshake_done());
    assert!(!d.handshake_done());
    take_turns_fn(
        &mut h,
        &mut d,
        &mut check_number_of_packets(vec![1, 2, 2, 1, 1]),
    )?;
    assert!(h.handshake_done());
    assert!(d.handshake_done());
    let mut h = h.map(|h| h.complete())?;
    let mut d = d.map(|d| d.unwrap().complete())?;

    // first message, no ACK
    h.message_in(0, 1010, b"ThpSelectMethod with SkipParing")?;
    let pir = HostToDevice.transfer_fn(&mut h, &mut d, &mut check_just_one)?;
    assert!(!pir.got_ack() && pir.got_message());
    d.message_out()?;

    // piggybacked ACK
    d.message_in(0, 1019, b"ThpEndResponse means done")?;
    let pir = DeviceToHost.transfer_fn(&mut h, &mut d, &mut check_just_one)?;
    assert!(pir.got_ack() && pir.got_message());
    h.message_out()?;

    // packet goes out before message - standalone ACK
    let pir = HostToDevice.transfer_fn(&mut h, &mut d, &mut check_just_one)?;
    assert!(pir.got_ack() && !pir.got_message());
    h.message_in(0, 1234, b"Ping")?;
    let pir = HostToDevice.transfer_fn(&mut h, &mut d, &mut check_just_one)?;
    assert!(!pir.got_ack() && pir.got_message());
    d.message_out()?;

    // packet goes out before message - standalone ACK
    let pir = DeviceToHost.transfer_fn(&mut h, &mut d, &mut check_just_one)?;
    assert!(pir.got_ack() && !pir.got_message());
    d.message_in(0, 5678, b"Pong")?;
    let pir = DeviceToHost.transfer_fn(&mut h, &mut d, &mut check_just_one)?;
    assert!(!pir.got_ack() && pir.got_message());
    h.message_out()?;

    // piggybacked ACK
    h.message_in(1, 9999, &[0u8; 999])?;
    let pir = HostToDevice.transfer(&mut h, &mut d)?;
    assert!(pir.got_ack() && pir.got_message());
    d.message_out()?;

    // piggybacked ACK
    d.message_in(1, 9998, &[9u8; 666])?;
    let pir = DeviceToHost.transfer(&mut h, &mut d)?;
    assert!(pir.got_ack() && pir.got_message());
    h.message_out()?;

    // no further message, just ACK
    let pir = HostToDevice.transfer_fn(&mut h, &mut d, &mut check_just_one)?;
    assert!(pir.got_ack() && !pir.got_message());
    Ok(())
}

#[test_case(false; "v20")]
#[test_case(true; "v21")]
fn test_device_locked(ack_piggybacking: bool) -> Result<()> {
    setup();

    let (mut hm, mut dm, cids) = create_mux();
    // channel allocation
    hm.request_channel(false);
    take_turns(&mut hm, &mut dm)?;
    let mut d = dm
        .channel_alloc(cids.get(), TestCredentialVerifier)?
        .into_buffered();
    take_turns(&mut hm, &mut d)?;
    let mut h = hm.channel_alloc(NullCredentialStore)?.into_buffered();
    if ack_piggybacking {
        h.set_device_protocol_version(2, 1);
    }

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
    assert!(d.handshake_failed());
    Ok(())
}

fn create_mux() -> (
    Buffered<host::Mux<RustCrypto>>,
    Buffered<device::Mux<RustCrypto>>,
    device::ChannelIdAllocator,
) {
    let mut hm = host::Mux::<RustCrypto>::new().into_buffered();
    hm.set_packet_len(DEFAULT_PACKET_LEN);
    let mut dm = device::Mux::<RustCrypto>::new(DEVICE_PROPERTIES)
        .unwrap()
        .into_buffered();
    dm.set_packet_len(DEFAULT_PACKET_LEN);
    let cids = device::ChannelIdAllocator::new_random::<RustCrypto>();
    (hm, dm, cids)
}

fn alloc_channel() -> Result<(
    Buffered<host::ChannelOpen<NullCredentialStore, RustCrypto>>,
    Buffered<WithKey<TestCredentialVerifier, RustCrypto>>,
)> {
    let (mut hm, mut dm, cids) = create_mux();
    hm.request_channel(false);
    take_turns(&mut hm, &mut dm)?;
    let mut d = dm
        .channel_alloc(cids.get(), TestCredentialVerifier)?
        .with_key(DEVICE_KEY)
        .into_buffered();
    take_turns(&mut hm, &mut d)?;
    let h = hm.channel_alloc(NullCredentialStore)?.into_buffered();
    Ok((h, d))
}

fn open_channel(
    packet_len: usize,
    enable_piggybacking: bool,
) -> Result<(
    Buffered<host::Channel<RustCrypto>>,
    Buffered<device::Channel<RustCrypto>>,
)> {
    let (mut hm, mut dm, cids) = create_mux();
    hm.set_packet_len(packet_len);
    dm.set_packet_len(packet_len);
    hm.request_channel(false);
    take_turns(&mut hm, &mut dm)?;
    let mut d = dm
        .channel_alloc(cids.get(), TestCredentialVerifier)?
        .with_key(DEVICE_KEY)
        .into_buffered();
    take_turns(&mut d, &mut hm)?;
    let mut h = hm.channel_alloc(NullCredentialStore)?.into_buffered();
    if enable_piggybacking {
        h.set_device_protocol_version(2, 1);
    }
    take_turns(&mut h, &mut d)?;
    let h = h.map(|h| h.complete())?;
    let d = d.map(|d| d.unwrap().complete())?;

    Ok((h, d))
}

#[test_case(10, 0, false; "empty messages")]
#[test_case(30, 1, false; "short messages")]
#[test_case(20, 2000, false; "medium messages")]
#[test_case(5, 59976, false; "huge messages")]
#[test_case(1000, 100, false; "lots of messages")]
#[test_case(10, 0, true; "empty messages v21")]
#[test_case(30, 1, true; "short messages v21")]
#[test_case(5, 59976, true; "huge messages v21")]
fn test_messages(count: usize, length: usize, ack_piggybacking: bool) -> Result<()> {
    setup();
    let (mut h, mut d) = open_channel(DEFAULT_PACKET_LEN, ack_piggybacking)?;
    let payload = vec![42u8; length];
    for _i in 0..count {
        HostToDevice.call(&mut h, &mut d, &[&payload, &payload])?;
    }
    Ok(())
}

#[test_case(17, false; "tiny")]
#[test_case(256, false; "medium")]
#[test_case(1500, false; "large")]
#[test_case(17, true; "tiny_v21")]
#[test_case(256, true; "medium_v21")]
fn test_packet_length(packet_len: usize, ack_piggybacking: bool) -> Result<()> {
    setup();
    let (mut h, mut d) = open_channel(packet_len, ack_piggybacking)?;
    let payload = vec![69u8; 3200];
    for _i in 0..10 {
        HostToDevice.call(&mut h, &mut d, &[&payload, &payload])?;
    }
    Ok(())
}

#[test]
fn test_one_device_multiple_hosts() -> Result<()> {
    const NHOSTS: usize = 4;
    setup();
    let mut dm = device::Mux::<RustCrypto>::new(DEVICE_PROPERTIES)?.into_buffered();
    dm.set_packet_len(DEFAULT_PACKET_LEN);
    let cids = device::ChannelIdAllocator::new_from(42);

    let mut device_chans = Vec::<Buffered<Channel<Device, RustCrypto>>>::new();
    let mut host_chans = Vec::<Buffered<Channel<Host, RustCrypto>>>::new();

    // open channels
    for i in 0..NHOSTS {
        let mut hm = host::Mux::<RustCrypto>::new().into_buffered();
        hm.set_packet_len(DEFAULT_PACKET_LEN);
        hm.request_channel(false);
        take_turns(&mut hm, &mut dm)?;
        let mut d = dm
            .channel_alloc(cids.get(), TestCredentialVerifier)?
            .with_key(DEVICE_KEY)
            .into_buffered();
        take_turns(&mut d, &mut hm)?;
        let mut h = hm.channel_alloc(NullCredentialStore)?.into_buffered();
        h.set_device_protocol_version(2, (i as u8) % 2); // odd => piggybacking
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
        HostToDevice.call(
            &mut host_chans[i],
            &mut device_chans[i],
            &[&payload, &payload],
        )?;
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

    let (mut hm, mut dm, cids) = create_mux();
    // channel allocation request lost
    hm.request_channel(false);
    take_turns_fn(&mut hm, &mut dm, &mut lose_nth(HostToDevice, 0))?;
    assert!(!dm.channel_alloc_ready());

    // channel allocation response lost
    hm.request_channel(false);
    take_turns(&mut hm, &mut dm)?;
    let mut d = dm
        .channel_alloc(cids.get(), TestCredentialVerifier)?
        .into_buffered();
    take_turns_fn(&mut hm, &mut d, &mut lose_nth(DeviceToHost, 0))?;
    assert!(!hm.channel_alloc_ready());

    // successful allocation
    hm.request_channel(false);
    take_turns(&mut hm, &mut dm)?;
    let mut d = dm
        .channel_alloc(cids.get(), TestCredentialVerifier)?
        .into_buffered();
    take_turns(&mut hm, &mut d)?;
    let mut _h = hm.channel_alloc(NullCredentialStore)?.into_buffered();
    Ok(())
}

fn handshake_timeout(
    h: &mut Buffered<host::ChannelOpen<NullCredentialStore, RustCrypto>>,
    d: &mut Buffered<WithKey<TestCredentialVerifier, RustCrypto>>,
    who_retransmits: Direction,
    max_timeouts: usize,
) -> Result<()> {
    let mut dir = who_retransmits;
    for _ in 0..max_timeouts {
        if dir == DeviceToHost {
            assert!(d.sending_retry().is_some());
            d.message_retransmit()?;
        } else {
            assert!(h.sending_retry().is_some());
            h.message_retransmit()?;
        }
        take_turns_until_fn(&mut until_stuck, h, d, &mut |_, _| ())?;
        if h.handshake_done() && d.handshake_done() {
            return Ok(());
        }
        dir = dir.reverse();
    }
    panic!("Handshake did not finish within {} timeouts.", max_timeouts);
}

// When an ACK is lost, depending on the timing, either peer can retransmit first.
// Both cases are tested via the `who_retransmits` parameter, except the last ACK
// awhere device does not want to send anything.
#[test_case(HostToDevice, 0, HostToDevice; "handshake_init_request")]
#[test_case(HostToDevice, 1, DeviceToHost; "handshake_init_response_ack1")]
#[test_case(HostToDevice, 1, HostToDevice; "handshake_init_response_ack2")]
#[test_case(HostToDevice, 2, HostToDevice; "handshake_completion_request")]
#[test_case(HostToDevice, 3, HostToDevice; "handshake_completion_request_cont")]
#[test_case(HostToDevice, 4, DeviceToHost; "handshake_completion_response_ack1")] // last ACK
#[test_case(DeviceToHost, 0, HostToDevice; "handshake_init_request_ack1")]
#[test_case(DeviceToHost, 0, DeviceToHost; "handshake_init_request_ack2")]
#[test_case(DeviceToHost, 1, DeviceToHost; "handshake_init_response")]
#[test_case(DeviceToHost, 2, DeviceToHost; "handshake_init_response_cont")]
#[test_case(DeviceToHost, 3, HostToDevice; "handshake_completion_request_ack1")]
#[test_case(DeviceToHost, 3, DeviceToHost; "handshake_completion_request_ack2")]
#[test_case(DeviceToHost, 4, DeviceToHost; "handshake_completion_response")]
fn test_packet_loss_handshake_v20(
    dir: Direction,
    lost_index: usize,
    who_retransmits: Direction,
) -> Result<()> {
    setup();
    let (mut h, mut d) = alloc_channel()?;

    // handshake
    take_turns_until_fn(
        &mut until_stuck,
        &mut h,
        &mut d,
        &mut lose_nth(dir, lost_index),
    )?;
    handshake_timeout(&mut h, &mut d, who_retransmits, 3)?;
    let mut h = h.map(|h| h.complete())?;
    let mut d = d.map(|d| d.unwrap().complete())?;

    // application messaging
    HostToDevice.call(&mut h, &mut d, &[b"Ping", b"Pong"])?;

    Ok(())
}

#[test_case(HostToDevice, 0; "handshake_init_request")]
#[test_case(DeviceToHost, 0; "handshake_init_response")]
#[test_case(DeviceToHost, 1; "handshake_init_response_cont")]
#[test_case(HostToDevice, 1; "handshake_completion_request")]
#[test_case(HostToDevice, 2; "handshake_completion_request_cont")]
#[test_case(DeviceToHost, 2; "handshake_completion_response")]
#[test_case(HostToDevice, 3; "handshake_completion_response_ack")] // standalone last ACK
fn test_packet_loss_handshake_v21(dir: Direction, lost_index: usize) -> Result<()> {
    setup();
    let (mut h, mut d) = alloc_channel()?;
    h.set_device_protocol_version(2, 1);

    // handshake
    take_turns_until_fn(
        &mut until_stuck,
        &mut h,
        &mut d,
        &mut lose_nth(dir, lost_index),
    )?;
    // When packet is lost in the middle of an exchange, either side can possibly
    // retransmit first. This test assumes the sender does, except for the last ACK.
    let who_retransmits = dir.reverse_if(dir == HostToDevice && lost_index == 3);
    handshake_timeout(&mut h, &mut d, who_retransmits, 2)?;
    let mut h = h.map(|h| h.complete())?;
    let mut d = d.map(|d| d.unwrap().complete())?;

    // application messaging
    HostToDevice.call(&mut h, &mut d, &[b"Ping", b"Pong"])
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

    let (mut hm, mut dm, cids) = create_mux();
    // channel allocation request lost
    hm.request_channel(false);
    take_turns_fn(
        &mut hm,
        &mut dm,
        &mut damage_nth(HostToDevice, 0, byte_index),
    )?;
    assert!(!dm.channel_alloc_ready());

    // channel allocation response lost
    hm.request_channel(false);
    take_turns(&mut hm, &mut dm)?;
    let mut d = dm
        .channel_alloc(cids.get(), TestCredentialVerifier)?
        .into_buffered();
    take_turns_fn(
        &mut hm,
        &mut d,
        &mut damage_nth(DeviceToHost, 0, byte_index),
    )?;
    assert!(!hm.channel_alloc_ready());

    // successful allocation
    hm.request_channel(false);
    take_turns(&mut hm, &mut dm)?;
    let mut d = dm
        .channel_alloc(cids.get(), TestCredentialVerifier)?
        .into_buffered();
    take_turns(&mut hm, &mut d)?;
    let _h = hm.channel_alloc(NullCredentialStore)?.into_buffered();
    Ok(())
}

#[test_matrix(
    [HostToDevice, DeviceToHost],
    [0, 1, 2, 3, 4],
    [0, 1, 3, 6]
)]
fn test_packet_damage_handshake_v20(
    dir: Direction,
    packet_index: usize,
    byte_index: usize,
) -> Result<()> {
    setup();

    let (mut h, mut d) = alloc_channel()?;
    let acks = [
        (HostToDevice, 1),
        (HostToDevice, 4),
        (DeviceToHost, 0),
        (DeviceToHost, 3),
    ];
    let who_retransmits = dir.reverse_if(acks.contains(&(dir, packet_index)));

    // handshake
    take_turns_fn(
        &mut h,
        &mut d,
        &mut damage_nth(dir, packet_index, byte_index),
    )?;
    handshake_timeout(&mut h, &mut d, who_retransmits, 2)?;
    let mut h = h.map(|h| h.complete())?;
    let mut d = d.map(|d| d.unwrap().complete())?;

    // pairing, appdata
    HostToDevice.call(
        &mut h,
        &mut d,
        &[
            b"ThpSelectMethod with SkipParing",
            b"ThpEndResponse means done",
            b"Ping",
            b"Pong",
        ],
    )
}

#[test_matrix(
    [HostToDevice, DeviceToHost],
    [0, 1, 2],
    [0, 1, 3, 6]
)]
fn test_packet_damage_handshake_v21(
    dir: Direction,
    packet_index: usize,
    byte_index: usize,
) -> Result<()> {
    setup();
    let (mut h, mut d) = alloc_channel()?;
    h.set_device_protocol_version(2, 1);

    take_turns_fn(
        &mut h,
        &mut d,
        &mut damage_nth(dir, packet_index, byte_index),
    )?;
    handshake_timeout(&mut h, &mut d, dir, 1)?;
    let mut h = h.map(|h| h.complete())?;
    let mut d = d.map(|d| d.unwrap().complete())?;

    HostToDevice.call(&mut h, &mut d, &[b"Ping", b"Pong"])
}

#[test_case(false; "v20")]
#[test_case(true; "v21")]
fn test_packet_damage_application(ack_piggybacking: bool) -> Result<()> {
    setup();

    let (mut h, mut d) = open_channel(DEFAULT_PACKET_LEN, ack_piggybacking)?;
    h.message_in(0, 0, b"the quick brown fox jumps over the lazy dog")?;
    let res = take_turns_fn(&mut h, &mut d, &mut damage_nth(HostToDevice, 0, 16))?;
    assert_eq!(res, None);
    h.message_retransmit()?;
    let res = take_turns(&mut h, &mut d)?;
    assert!(matches!(res, Some((HostToDevice, _))));

    d.message_in(0, 0, b"the quick lazy dog crawls under the brown fox")?;
    let res = take_turns_fn(&mut h, &mut d, &mut damage_nth(DeviceToHost, 0, 50))?;
    assert_eq!(res, None);
    d.message_retransmit()?;
    let res = take_turns(&mut h, &mut d)?;
    assert!(matches!(res, Some((DeviceToHost, _))));

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
            pong: false,
            buffer_size: None,
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
    let (mut h, mut d) = open_channel(DEFAULT_PACKET_LEN, false)?;
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
            pong: false,
            buffer_size: None,
        }
    ));
    let pong_packet = dm.packet_out()?;
    let pir = hm.packet_in(&pong_packet);
    assert!(matches!(
        pir,
        PacketInResult::Accepted {
            ack_received: false,
            message_ready: false,
            pong: true,
            buffer_size: None,
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
    let (mut h, mut d) = open_channel(DEFAULT_PACKET_LEN, false)?;
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
    assert_eq!(
        pir,
        PacketInResult::Route {
            channel_id: 66,
            buffer_size: 16.try_into().ok(),
        }
    );
    let pir = hm.packet_in(&make_packet(66));
    assert_eq!(
        pir,
        PacketInResult::Route {
            channel_id: 66,
            buffer_size: 16.try_into().ok(),
        }
    );

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
    let (mut h, mut d) = open_channel(DEFAULT_PACKET_LEN, false)?;
    for channel_id in INVALID.iter().chain(&[BROADCAST_CHANNEL_ID]) {
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

#[test_case(false; "v20")]
#[test_case(true; "v21")]
fn test_invalid_tag(ack_piggybacking: bool) -> Result<()> {
    setup();

    let (mut h, mut d) = open_channel(DEFAULT_PACKET_LEN, ack_piggybacking)?;
    h.message_in(0, 404, b"hello world hello world hello")
        .unwrap();
    take_turns_until_fn(
        &mut until_stuck,
        &mut h,
        &mut d,
        &mut damage_nth_fix_crc(HostToDevice, 0, 10),
    )?;
    assert!(d.message_out_ready());
    assert_eq!(d.message_out(), Err(Error::CryptoError));

    let (mut h, mut d) = open_channel(DEFAULT_PACKET_LEN, ack_piggybacking)?;
    d.message_in(0, 403, b"hello world hello world hello")
        .unwrap();
    take_turns_until_fn(
        &mut until_stuck,
        &mut h,
        &mut d,
        &mut damage_nth_fix_crc(DeviceToHost, 0, 20),
    )?;
    assert!(h.message_out_ready());
    assert_eq!(h.message_out(), Err(Error::CryptoError));

    Ok(())
}

#[test]
fn test_channel_id_wraparound() -> Result<()> {
    setup();

    fn alloc_test(
        hm: &mut Buffered<host::Mux<RustCrypto>>,
        dm: &mut Buffered<device::Mux<RustCrypto>>,
        cids: &device::ChannelIdAllocator,
        expected_id: u16,
    ) -> Result<()> {
        hm.request_channel(false);
        take_turns(hm, dm)?;
        let mut d = dm
            .channel_alloc(cids.get(), TestCredentialVerifier)?
            .into_buffered();
        take_turns(hm, &mut d)?;
        let h = hm.channel_alloc(NullCredentialStore)?.into_buffered();
        assert_eq!(h.channel_id(), expected_id);
        Ok(())
    }

    let (mut hm, mut dm, _) = create_mux();
    let cids = device::ChannelIdAllocator::new_from(MAX_CHANNEL_ID - 1);
    alloc_test(&mut hm, &mut dm, &cids, MAX_CHANNEL_ID - 1)?;
    alloc_test(&mut hm, &mut dm, &cids, MAX_CHANNEL_ID)?;
    alloc_test(&mut hm, &mut dm, &cids, MIN_CHANNEL_ID)?;
    alloc_test(&mut hm, &mut dm, &cids, MIN_CHANNEL_ID + 1)?;

    Ok(())
}
