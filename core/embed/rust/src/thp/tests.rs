use crate::micropython::{func::Func, macros::obj_fn_2, obj::Obj, testutil::mpy_init};

use std::{
    assert_matches,
    collections::{HashMap, VecDeque},
    iter::repeat_n,
};

use spin::MutexGuard;

use trezor_thp::{
    channel::{
        buffered::{Buffered, ChannelExt},
        host, ChannelIO, PacketInResult, PairingState, Phase, APP_HEADER_LEN, PRIVKEY_LEN, TAG_LEN,
    },
    credential::{CredentialStore, FoundCredential, NullCredentialStore},
    error::TransportError,
};

use super::{Auxiliary, Error, ThpContext, TrezorCrypto, TrezorInResult, THP_AUX, THP_CONTEXT};

type HostChannel = host::Channel<TrezorCrypto>;
type HostChannelOpen<C> = host::ChannelOpen<C, TrezorCrypto>;

const DUMMY_PRIVKEY: [u8; PRIVKEY_LEN] = [0; _];
const IFACE_USB: u8 = 0x58;
const IFACE_BLE: u8 = 0x13;

// Model of the environment that the module interacts with.
struct TestContext {
    // Unique THP_CONTEXT reference.
    thp: MutexGuard<'static, ThpContext>,

    // Queue of packets in transit between Trezor and Host. Two directions per interface.
    wire_h2t: HashMap<u8, VecDeque<Vec<u8>>>,
    wire_t2h: HashMap<u8, VecDeque<Vec<u8>>>,

    // Micropython code maintains send and receive buffers bound to channel+interface.
    send_buffer: HashMap<(u8, u16), Vec<u8>>,
    receive_buffer: HashMap<(u8, u16), Vec<u8>>,

    // Micropython credential verification callback.
    credential_fn: Obj,
}

impl TestContext {
    fn new(thp: MutexGuard<'static, ThpContext>) -> Self {
        TestContext {
            thp,
            wire_h2t: HashMap::new(),
            wire_t2h: HashMap::new(),
            send_buffer: HashMap::new(),
            receive_buffer: HashMap::new(),
            credential_fn: Obj::const_none(),
        }
    }

    fn wire_h2t(&mut self, iface_num: u8) -> &mut VecDeque<Vec<u8>> {
        self.wire_h2t
            .entry(iface_num)
            .or_insert_with(|| VecDeque::new())
    }

    fn wire_t2h(&mut self, iface_num: u8) -> &mut VecDeque<Vec<u8>> {
        self.wire_t2h
            .entry(iface_num)
            .or_insert_with(|| VecDeque::new())
    }
}

impl Drop for TestContext {
    fn drop(&mut self) {
        for (iface_num, wire) in self.wire_h2t.iter() {
            if !wire.is_empty() {
                log::error!(
                    "wire_h2t[{:02x}] must end up empty, has {} packets:",
                    iface_num,
                    wire.len()
                );
            }
            for packet in wire {
                log::error!("{}", hex::encode(&packet));
            }
        }
        for (iface_num, wire) in self.wire_t2h.iter() {
            if !wire.is_empty() {
                log::error!(
                    "wire_t2h[{:02x}] must end up empty, has {} packets:",
                    iface_num,
                    wire.len()
                );
            }
            for packet in wire {
                log::error!("{}", hex::encode(&packet));
            }
        }
    }
}

#[derive(Debug)]
enum ExchangeResult {
    Trezor(TrezorInResult),
    Host(PacketInResult),
}
use ExchangeResult::*;

impl ExchangeResult {
    fn assert_host_error(&self, te: TransportError) {
        match self {
            Host(PacketInResult::TransportError { error }) if *error == te => {}
            r => panic!("Unexpected ExchangeResult: {:?}", r),
        }
    }
}

impl TestContext {
    // Send packets back and forth between Host and Trezor until there's nothing
    // left to send, or something interesting happens.
    fn exchange_packets<C: ChannelIO>(
        &mut self,
        iface_num: u8,
        host: &mut Buffered<C>,
    ) -> Result<ExchangeResult, Error> {
        let mut idle = false;

        while !idle {
            idle = true;
            // host to trezor
            while host.packet_out_ready() {
                self.wire_h2t(iface_num).push_back(host.packet_out()?);
                idle = false;
            }
            while !self.wire_h2t(iface_num).is_empty() {
                let packet = self.wire_h2t(iface_num).pop_front().unwrap();
                log::debug!("[{:02x}] > {}", iface_num, hex::encode(&packet));
                let mut res = self.thp.packet_in(iface_num, &packet, self.credential_fn)?;
                if let TrezorInResult::Route {
                    channel_id,
                    buffer_size,
                } = res
                {
                    if let Some(buffer_size) = buffer_size {
                        self.receive_buffer.insert(
                            (iface_num, channel_id),
                            Vec::from_iter(repeat_n(0, buffer_size.get().into())),
                        );
                    }
                    let mut receive_buffer = self
                        .receive_buffer
                        .get_mut(&(iface_num, channel_id))
                        .unwrap();
                    res = self.thp.packet_in_channel(
                        iface_num,
                        channel_id,
                        &packet,
                        &mut receive_buffer,
                    )?;
                }
                if !matches!(res, TrezorInResult::None) {
                    log::debug!("trezor[{:02x}]: {:?}", iface_num, res);
                    return Ok(ExchangeResult::Trezor(res));
                }
            }
            // trezor to host
            let mut packet_buffer = Vec::from_iter(repeat_n(0, host.packet_len()));
            while self.thp.packet_out(iface_num, &mut packet_buffer)? {
                self.wire_t2h(iface_num).push_back(packet_buffer.clone());
                idle = false;
            }
            // FIXME: maybe just send host.channel_id() if iface_num matches?
            let iface_channels = self
                .send_buffer
                .keys()
                .filter_map(|&(ifn, cid)| (ifn == iface_num).then_some(cid))
                .collect::<Vec<u16>>();
            for channel_id in iface_channels {
                while self.thp.packet_out_channel(
                    iface_num,
                    channel_id,
                    self.send_buffer.get_mut(&(iface_num, channel_id)).unwrap(),
                    &mut packet_buffer,
                )? {
                    self.wire_t2h(iface_num).push_back(packet_buffer.clone());
                    idle = false;
                }
            }
            while !self.wire_t2h(iface_num).is_empty() {
                let packet = self.wire_t2h(iface_num).pop_front().unwrap();
                log::debug!("[{:02x}] < {}", iface_num, hex::encode(&packet));
                let res = host.packet_in(&packet).check_failed()?;
                if !matches!(
                    res,
                    PacketInResult::Ignored { .. } | PacketInResult::Accepted { .. }
                ) {
                    log::debug!("host[{:02x}]: {:?}", iface_num, res);
                    return Ok(ExchangeResult::Host(res));
                }
            }
        }

        Ok(ExchangeResult::Trezor(TrezorInResult::None))
    }

    // Allocate new channel on given interface.
    fn allocate_channel<C: CredentialStore>(
        &mut self,
        iface_num: u8,
        cred_store: C,
    ) -> Result<Buffered<HostChannelOpen<C>>, Error> {
        let mut host = host::Mux::<TrezorCrypto>::new().into_buffered();
        host.request_channel(false);
        self.exchange_packets(iface_num, &mut host)?;
        assert!(host.channel_alloc_ready());
        let mut host = host.channel_alloc(cred_store)?.into_buffered();
        // enable ACK piggybacking
        host.set_device_protocol_version(2, 1);
        Ok(host)
    }

    // Perform handshake on allocated channel.
    fn perform_handshake<C: CredentialStore>(
        &mut self,
        iface_num: u8,
        mut host: Buffered<HostChannelOpen<C>>,
    ) -> Result<Buffered<HostChannel>, Error> {
        let res = self.exchange_packets(iface_num, &mut host)?;
        assert_matches!(res, Trezor(TrezorInResult::KeyRequired { .. }));
        self.thp.handshake_static_key(iface_num, &DUMMY_PRIVKEY)?;
        self.exchange_packets(iface_num, &mut host)?;
        assert!(host.handshake_done());
        let host = host.map(|h| h.complete())?;
        assert!(!host.is_encrypted_transport());
        assert_matches!(
            self.trezor_phase(iface_num, host.channel_id()),
            Phase::PairingCredential { .. }
        );
        Ok(host)
    }

    // Transition from pairing/credential phase to encrypted transport.
    fn end_pairing(
        &mut self,
        iface_num: u8,
        host: &mut Buffered<HostChannel>,
    ) -> Result<Option<u16>, Error> {
        let channel_id = host.channel_id();
        assert!(!host.is_encrypted_transport());
        assert_matches!(
            self.trezor_phase(iface_num, channel_id),
            Phase::PairingCredential { .. }
        );
        host.end_pairing();
        let replaced_channel = self.thp.channel_paired(iface_num, channel_id)?;
        assert!(host.is_encrypted_transport());
        assert_matches!(
            self.trezor_phase(iface_num, channel_id),
            Phase::EncryptedTransport
        );
        Ok(replaced_channel)
    }

    // Send application message from Host to Trezor. Does not send ACK.
    fn send_h2t(
        &mut self,
        iface_num: u8,
        host: &mut Buffered<HostChannel>,
        message: &[u8],
    ) -> Result<(), Error> {
        let channel_id = host.channel_id();
        host.message_in(0, 1234, message)?;
        let res = self.exchange_packets(iface_num, host)?;
        assert_matches!(
            res,
            Trezor(TrezorInResult::MessageReady | TrezorInResult::MessageReadyAck)
        );
        let mut receive_buffer = self
            .receive_buffer
            .get_mut(&(iface_num, channel_id))
            .unwrap();
        let (sid, mty, len) = self
            .thp
            .message_out(iface_num, channel_id, &mut receive_buffer)?;
        let msg = &receive_buffer[APP_HEADER_LEN..][..len];
        assert_eq!(sid, 0);
        assert_eq!(mty, 1234);
        assert_eq!(msg, message);
        Ok(())
    }

    // Send application message from Trezor to Host. Does not send ACK.
    fn send_t2h(
        &mut self,
        iface_num: u8,
        host: &mut Buffered<HostChannel>,
        message: &[u8],
    ) -> Result<(), Error> {
        let channel_id = host.channel_id();
        let mut msg = Vec::new();
        msg.push(0u8);
        msg.extend_from_slice(&[0xc0, 0xfe]);
        msg.extend_from_slice(message);
        let plaintext_len = msg.len();
        msg.extend_from_slice(&[0; TAG_LEN]);
        self.send_buffer.insert((iface_num, channel_id), msg);
        let mut send_buffer = self.send_buffer.get_mut(&(iface_num, channel_id)).unwrap();
        self.thp
            .message_in(iface_num, channel_id, plaintext_len, &mut send_buffer)?;
        self.exchange_packets(iface_num, host)?;
        assert!(host.message_out_ready());
        let (sid, mty, msg_host) = host.message_out()?;
        assert_eq!(sid, 0);
        assert_eq!(mty, 0xc0fe);
        assert_eq!(msg_host, message);
        Ok(())
    }

    // Send a sequence of requests-responses from Host to Trezor and back.
    // After last response, a standalone ACK packet is sent to Trezor.
    fn call(
        &mut self,
        iface_num: u8,
        host: &mut Buffered<HostChannel>,
        request_response: &[(&[u8], &[u8])],
    ) -> Result<(), Error> {
        for (request, response) in request_response {
            self.send_h2t(iface_num, host, request)?;
            self.send_t2h(iface_num, host, response)?;
        }
        // end of piggybacking, host needs to send standalone ACK
        let res = self.exchange_packets(iface_num, host)?;
        assert_matches!(res, Trezor(TrezorInResult::Ack));
        Ok(())
    }

    // Assert there are no packets pending.
    fn assert_silence<C: ChannelIO>(&mut self, host: &Buffered<C>) {
        assert!(!host.packet_out_ready());
        let mut packet_buffer = Vec::from_iter(repeat_n(0, host.packet_len()));
        for iface_num in self.thp.ifaces.keys().map(|x| *x).collect::<Vec<u8>>() {
            assert!(!self.thp.packet_out(iface_num, &mut packet_buffer).unwrap());
        }
        for &(iface_num, channel_id) in self.send_buffer.keys() {
            assert!(!self
                .thp
                .packet_out_channel(
                    iface_num,
                    channel_id,
                    self.send_buffer.get(&(iface_num, channel_id)).unwrap(),
                    &mut packet_buffer
                )
                .unwrap());
        }
    }

    fn trezor_phase(&self, iface_num: u8, channel_id: u16) -> Phase {
        self.thp.channel_info(iface_num, channel_id).unwrap().1
    }

    // Assert particular pairing state on both sides of an interface.
    fn assert_pairing_state(
        &mut self,
        iface_num: u8,
        host: &Buffered<HostChannel>,
        ps: PairingState,
    ) {
        match self.trezor_phase(iface_num, host.channel_id()) {
            Phase::PairingCredential {
                handshake_pairing_state,
            } if handshake_pairing_state == ps => {}
            tp => panic!("Unexpected trezor pairing state: {:?}", tp),
        }
        match host.phase() {
            Phase::PairingCredential {
                handshake_pairing_state,
            } if handshake_pairing_state == ps => {}
            hp => panic!("Unexpected host pairing state: {:?}", hp),
        }
    }
}

// Every test must start by calling this function and not discarding the
// MutexGuard until the end.
// - By default `cargo test` uses multiple threads but we only have one
//   THP_CONTEXT.
// - If we somehow get rid of THP_AUX we can stop with this circus and just make
//   a new ThpContext instance.
fn setup(ifaces: &[u8]) -> TestContext {
    unsafe { mpy_init() };

    let mut thp = THP_CONTEXT.lock();
    *thp = ThpContext::new();
    let mut aux = THP_AUX.lock();
    *aux = Auxiliary::new();
    // should be fine to leave CHANNEL_ID_COUNTER as is
    for &iface_num in ifaces {
        thp.add_interface(iface_num, b"FakeDeviceProperties")
            .unwrap();
    }
    TestContext::new(thp)
}

#[test]
fn test_open() -> Result<(), Error> {
    let mut test = setup(&[IFACE_USB, IFACE_BLE]);

    // channel allocation
    let host = test.allocate_channel(IFACE_USB, NullCredentialStore)?;
    assert_eq!(host.device_properties(), b"FakeDeviceProperties");

    // handshake
    let mut host = test.perform_handshake(IFACE_USB, host)?;
    test.assert_pairing_state(IFACE_USB, &host, PairingState::Unpaired);

    // pairing
    test.call(
        IFACE_USB,
        &mut host,
        &[(b"DummySkipPairing", b"DummyThpEndResponse")],
    )?;

    // pairing done
    test.end_pairing(IFACE_USB, &mut host)?;

    // application messages
    test.call(
        IFACE_USB,
        &mut host,
        &[(b"Ping", b"Pong"), (&[123; 130], &[45; 140])],
    )?;

    Ok(())
}

#[test]
fn test_isolation_handshake_1() -> Result<(), Error> {
    let mut test = setup(&[IFACE_USB, IFACE_BLE]);
    // allocate channel on USB interface
    let mut host = test.allocate_channel(IFACE_USB, NullCredentialStore)?;
    // host initiates handshake on BLE, is ignored
    test.exchange_packets(IFACE_BLE, &mut host)?
        .assert_host_error(TransportError::UnallocatedChannel);
    assert!(host.handshake_failed());
    test.assert_silence(&host);
    Ok(())
}

#[test]
fn test_isolation_handshake_2() -> Result<(), Error> {
    let mut test = setup(&[IFACE_BLE, IFACE_USB]);
    // allocate channel on USB interface
    let mut host = test.allocate_channel(IFACE_USB, NullCredentialStore)?;
    // start handshake on USB
    let res = test.exchange_packets(IFACE_USB, &mut host)?;
    assert_matches!(res, Trezor(TrezorInResult::KeyRequired { .. }));
    test.thp.handshake_static_key(IFACE_USB, &DUMMY_PRIVKEY)?;
    let mut packet_buffer = Vec::from_iter(repeat_n(0, host.packet_len()));
    while test.thp.packet_out(IFACE_USB, &mut packet_buffer)? {
        log::debug!("[{:02x}] < {}", IFACE_USB, hex::encode(&packet_buffer));
        host.packet_in(&packet_buffer).check_failed()?;
    }
    // host sends completion request over BLE, is ignored
    test.exchange_packets(IFACE_BLE, &mut host)?
        .assert_host_error(TransportError::UnallocatedChannel);
    assert!(host.handshake_failed());
    test.assert_silence(&host);
    Ok(())
}

#[test]
fn test_isolation_appdata_1() -> Result<(), Error> {
    let mut test = setup(&[IFACE_USB, IFACE_BLE]);
    // allocate channel on BLE interface
    let host = test.allocate_channel(IFACE_BLE, NullCredentialStore)?;
    let mut host = test.perform_handshake(IFACE_BLE, host)?;
    // message on USB interface should be ignored
    host.message_in(0, 1234, b"DummySkipPairing")?;
    test.exchange_packets(IFACE_USB, &mut host)?
        .assert_host_error(TransportError::UnallocatedChannel);
    assert!(host.is_failed());
    test.assert_silence(&host);
    Ok(())
}

#[test]
fn test_isolation_appdata_2() -> Result<(), Error> {
    let mut test = setup(&[IFACE_USB, IFACE_BLE]);
    // allocate channel on BLE interface
    let host = test.allocate_channel(IFACE_BLE, NullCredentialStore)?;
    let mut host = test.perform_handshake(IFACE_BLE, host)?;
    // send first message over BLE
    test.call(
        IFACE_BLE,
        &mut host,
        &[(b"DummySkipPairing", b"DummyThpEndResponse")],
    )?;
    // pairing done
    test.end_pairing(IFACE_BLE, &mut host)?;
    // sending second message over USB should fail
    host.message_in(0, 6667, b"Ping")?;
    test.exchange_packets(IFACE_USB, &mut host)?
        .assert_host_error(TransportError::UnallocatedChannel);
    assert!(host.is_failed());
    test.assert_silence(&host);
    Ok(())
}

// Dummy store that returns the same credential and privkey made of repeating
// byte regardless of the inputs.
struct SingleCredentialStore(u8);

impl CredentialStore for SingleCredentialStore {
    fn lookup<'a>(
        &self,
        _ephemeral: &[u8],
        _masked_static: &[u8],
        dest: &'a mut [u8],
    ) -> Option<FoundCredential<'a>> {
        const CRED: &[u8] = b"hello";
        let (local_static_privkey, auth_credential) =
            dest.split_first_chunk_mut::<PRIVKEY_LEN>().unwrap();
        local_static_privkey.copy_from_slice(&[self.0; PRIVKEY_LEN]);
        let auth_credential = &mut auth_credential[..CRED.len()];
        auth_credential.copy_from_slice(CRED);
        Some(FoundCredential {
            local_static_privkey,
            auth_credential,
        })
    }
}

// Had weird issues trying to convert Obj arguments to slices - just accept
// everything. Possibly related to HEAP and https://doc.rust-lang.org/edition-guide/rust-2024/static-mut-references.html
extern "C" fn py_accept_everything(_host_static_pubkey: Obj, _credential: Obj) -> Obj {
    Obj::small_int(u16::from(u8::from(PairingState::Paired)))
}
static ACCEPT_EVERYTHING_FN: Func = obj_fn_2!(py_accept_everything);

#[test]
fn test_channel_replacement() -> Result<(), Error> {
    let mut test = setup(&[IFACE_USB, IFACE_BLE]);
    test.credential_fn = ACCEPT_EVERYTHING_FN.as_obj();

    // open channel with privkey AA...
    let host = test.allocate_channel(IFACE_USB, SingleCredentialStore(0xaa))?;
    let mut host = test.perform_handshake(IFACE_USB, host)?;
    test.assert_pairing_state(IFACE_USB, &host, PairingState::Paired);
    let replaced = test.end_pairing(IFACE_USB, &mut host)?;
    assert_eq!(replaced, None);
    let channel_id_1 = host.channel_id();

    // open channel with privkey BB... - no replacement
    let host = test.allocate_channel(IFACE_USB, SingleCredentialStore(0xbb))?;
    let mut host = test.perform_handshake(IFACE_USB, host)?;
    test.assert_pairing_state(IFACE_USB, &host, PairingState::Paired);
    let replaced = test.end_pairing(IFACE_USB, &mut host)?;
    assert_eq!(replaced, None);

    // open channel with privkey AA... - replaces first channel
    let host = test.allocate_channel(IFACE_USB, SingleCredentialStore(0xaa))?;
    let mut host = test.perform_handshake(IFACE_USB, host)?;
    test.assert_pairing_state(IFACE_USB, &host, PairingState::PairedAutoconnect);
    let replaced = test.end_pairing(IFACE_USB, &mut host)?;
    assert_eq!(replaced, Some(channel_id_1));
    assert_eq!(&test.thp.channel_get_closed(IFACE_USB), &[channel_id_1]);

    // open channel with privkey BB... on the other interface - no replacement
    let host = test.allocate_channel(IFACE_BLE, SingleCredentialStore(0xbb))?;
    let mut host = test.perform_handshake(IFACE_BLE, host)?;
    test.assert_pairing_state(IFACE_BLE, &host, PairingState::Paired);
    let replaced = test.end_pairing(IFACE_BLE, &mut host)?;
    assert_eq!(replaced, None);

    Ok(())
}
