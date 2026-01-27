use crate::{
    ChannelIO,
    channel::{APP_HEADER_LEN, PacketInResult},
    error::Result,
};

use std::ops::Deref;
use std::vec::Vec;

const INITIAL_BUFFER_LEN: usize = 1024;

pub struct ChannelVec<C> {
    channel: C,
    packet_len: usize,
    send_buffer: Vec<u8>,
    receive_buffer: Vec<u8>,
}

impl<C: ChannelIO> ChannelVec<C> {
    pub fn new(channel: C, packet_len: usize) -> Self {
        Self {
            channel,
            packet_len,
            send_buffer: Vec::new(),
            receive_buffer: vec![0u8; INITIAL_BUFFER_LEN],
        }
    }

    pub fn packet_in(&mut self, packet_buffer: &[u8]) -> Result<PacketInResult> {
        let res = self
            .channel
            .packet_in(packet_buffer, self.receive_buffer.as_mut_slice());
        if let Ok(pir) = &res {
            if let Some(new_size) = pir.enlarge_receive_buffer {
                self.receive_buffer.resize(new_size.into(), 0u8);
            }
        }
        res
    }

    pub fn packet_out(&mut self) -> Result<Vec<u8>> {
        let mut channel_buffer = vec![0u8; self.packet_len];
        self.channel
            .packet_out(channel_buffer.as_mut_slice(), &self.send_buffer)?;
        Ok(channel_buffer)
    }

    pub fn message_in(&mut self, session_id: u8, message_type: u16, message: &[u8]) -> Result<()> {
        let mut send_buffer = vec![0; message.len() + C::BUFFER_OVERHEAD];
        let res = self.channel.message_in_from(
            session_id,
            message_type,
            message,
            send_buffer.as_mut_slice(),
        );
        if res.is_ok() {
            self.send_buffer = send_buffer;
        }
        res
    }

    pub fn message_out<'a>(&mut self) -> Result<(u8, u16, Vec<u8>)> {
        let (session_id, message_type, message) = self
            .channel
            .message_out(self.receive_buffer.as_mut_slice())?;
        let len = message.len();
        self.receive_buffer
            .copy_within(APP_HEADER_LEN..APP_HEADER_LEN + len, 0);
        self.receive_buffer.truncate(len);
        let res = core::mem::replace(&mut self.receive_buffer, vec![0u8; INITIAL_BUFFER_LEN]);
        Ok((session_id, message_type, res))
    }

    pub fn message_retransmit(&mut self) -> Result<()> {
        self.channel.message_retransmit()
    }

    pub fn inner(&self) -> &C {
        &self.channel
    }

    pub fn map<D>(self, func: impl FnOnce(C) -> D) -> ChannelVec<D> {
        ChannelVec {
            channel: func(self.channel),
            packet_len: self.packet_len,
            send_buffer: self.send_buffer,
            receive_buffer: self.receive_buffer,
        }
    }
}

impl<C: ChannelIO> Deref for ChannelVec<C> {
    type Target = C;

    fn deref(&self) -> &Self::Target {
        self.inner()
    }
}
