use std::io::ErrorKind;
use std::net::{SocketAddr, UdpSocket};
use std::time::Duration;

use trezor_thp::{
    Backend, ChannelIO, Error, channel::host::ChannelOpen, channel::vec::ChannelVec,
    credential::CredentialStore,
};

use protobuf::{Enum, Message};

const ACK_TIMEOUT: Duration = Duration::from_secs(1);
const READ_TIMEOUT: Duration = Duration::from_secs(30);
const PACKET_LEN: usize = 64;

const MESSAGE_TYPE_BUTTONREQUEST: u16 = 26;
const MESSAGE_TYPE_BUTTONACK: u16 = 27;

pub struct Client<C> {
    pub channel: ChannelVec<C>,
    socket: UdpSocket,
    emu_addr: SocketAddr,
}

impl<C, B> Client<ChannelOpen<C, B>>
where
    B: Backend,
    C: CredentialStore,
{
    pub fn open(emu_addr: SocketAddr, channel: ChannelOpen<C, B>) -> Self {
        Client {
            channel: ChannelVec::new(channel, PACKET_LEN),
            socket: UdpSocket::bind("127.0.0.1:0").unwrap(),
            emu_addr,
        }
    }
}

impl<C: ChannelIO> Client<C> {
    pub fn map<D>(self, func: impl FnOnce(C) -> D) -> Client<D> {
        Client {
            channel: self.channel.map(func),
            socket: self.socket,
            emu_addr: self.emu_addr,
        }
    }

    fn send_to(&mut self, buf: &[u8]) {
        log::trace!("> {}", hex::encode(&buf));
        self.socket.send_to(buf, self.emu_addr).unwrap();
    }

    fn recv_from(&mut self, timeout: Duration) -> Option<Vec<u8>> {
        self.socket.set_read_timeout(Some(timeout)).unwrap();
        let mut sockbuf = vec![0u8; PACKET_LEN];
        let res = self.socket.recv_from(sockbuf.as_mut_slice());
        match res {
            Ok((reply_len, src_addr)) => {
                assert_eq!(src_addr, self.emu_addr);
                sockbuf.truncate(reply_len);
                log::trace!("< {}", hex::encode(&sockbuf));
                Some(sockbuf)
            }
            Err(e) if matches!(e.kind(), ErrorKind::WouldBlock | ErrorKind::TimedOut) => {
                log::debug!("UDP receive timeout after {:?}.", timeout);
                None
            }
            Err(e) => {
                log::error!("Cannot read from UDP socket: {}.", e);
                panic!();
            }
        }
    }

    fn write_ack(&mut self) -> Vec<u8> {
        self.channel.packet_out().unwrap()
    }

    fn read_ack(&mut self, packet: &[u8]) -> bool {
        self.channel.packet_in(packet).unwrap().got_ack()
    }

    pub fn write(&mut self, sid: u8, message_type: u16, message: &[u8]) {
        self.channel.message_in(sid, message_type, message).unwrap();

        let mut sockbuf = [0u8; PACKET_LEN];
        let mut acked = false;
        while !acked {
            while self.channel.packet_out_ready() {
                let packet = self.channel.packet_out().unwrap();
                self.send_to(&packet);
                sockbuf.fill(0);
            }
            // Only true if channel ID is not known, otherwise we need to wait for an ACK.
            if self.channel.message_in_ready() {
                break;
            }
            while !acked {
                match self.recv_from(ACK_TIMEOUT) {
                    None => {
                        // timeout
                        self.channel.message_retransmit().unwrap();
                        break;
                    }
                    Some(packet) => {
                        acked = self.read_ack(&packet);
                    }
                }
            }
        }
    }

    pub fn read(&mut self) -> (u8, u16, Vec<u8>) {
        let mut result: Option<(u8, u16, Vec<u8>)> = None;
        while result.is_none() {
            let mut message_ready = false;
            while !message_ready {
                let Some(packet) = self.recv_from(READ_TIMEOUT) else {
                    log::error!("Timed out waiting for response for {:?}.", READ_TIMEOUT);
                    panic!();
                };
                message_ready = self.channel.packet_in(&packet).unwrap().got_message();
            }
            result = match self.channel.message_out() {
                Ok(r) => Some(r),
                Err(Error::InvalidDigest | Error::MalformedData) => {
                    log::error!("Received bad message, waiting for retransmission.");
                    continue;
                }
                Err(e) => {
                    log::error!("Cannot read message from channel: {:?}.", e);
                    panic!();
                }
            }
        }
        // Send ACK
        let packet = self.write_ack();
        self.send_to(&packet);
        result.unwrap()
    }

    pub fn call(&mut self, message_type: u16, message: &[u8]) -> (u16, Vec<u8>) {
        let session_id = 0;
        log::debug!("write message_type={} len={}", message_type, message.len());
        self.write(session_id, message_type, message);
        let res = self.read();
        log::debug!("read  message_type={} len={}", res.1, res.2.len());
        assert_eq!(res.0, session_id);
        (res.1, res.2)
    }

    pub fn write_pb(&mut self, sid: u8, message_type: impl Enum, message: impl Message) {
        log::debug!("write {:?}", message_type);
        let message_type: u16 = message_type.value().try_into().unwrap();
        let message = message.write_to_bytes().unwrap();
        self.write(sid, message_type, &message);
    }

    pub fn read_pb<E: Enum, T: Message>(&mut self) -> (u8, E, Option<T>) {
        let (sid, message_type, message) = self.read();
        let message_type = E::from_i32(message_type.try_into().unwrap()).unwrap();
        log::debug!("read  {:?}", message_type);
        let message = T::parse_from_bytes(&message).ok();
        (sid, message_type, message)
    }

    pub fn call_pb<T: Message, E: Enum>(
        &mut self,
        message_type: E,
        message: impl Message,
        expected_reply_type: E,
    ) -> T {
        self.write_pb(0, message_type, message);
        let (mut _sid, mut reply_message_type, mut reply_message) = self.read_pb::<E, T>();
        while reply_message_type.value() == MESSAGE_TYPE_BUTTONREQUEST.into() {
            log::debug!("write ButtonAck");
            self.write(0, MESSAGE_TYPE_BUTTONACK, &[]);
            println!("PLEASE CONFIRM ON YOUR TREZOR");
            (_sid, reply_message_type, reply_message) = self.read_pb::<E, T>();
        }
        assert_eq!(reply_message_type, expected_reply_type);
        reply_message.unwrap()
    }
}
