use std::env;
use std::net::{SocketAddr, UdpSocket};
use std::str::FromStr;

use trezor_thp::{
    alternating_bit::SyncBits,
    fragment::{Fragmenter, Reassembler},
    header::Header,
};

const IS_HOST: bool = true;
const REPEAT: u8 = 1;
const PACKET_LEN: usize = 64;

pub fn main() -> std::io::Result<()> {
    let port_str = env::args().nth(1).unwrap_or("21324".to_string());
    let port = u16::from_str(&port_str).expect("UDP port number");
    let emu_addr = SocketAddr::from(([127, 0, 0, 1], port));
    let socket = UdpSocket::bind("127.0.0.1:0")?;

    let mut sockbuf = [0u8; PACKET_LEN];
    let mut reply_data = [0u8; PACKET_LEN];

    for i in 0..REPEAT {
        let nonce = [i; 8]; // not a good nonce
        let sb = SyncBits::new(); // no ABP for ping
        Fragmenter::single(Header::new_ping(), sb, &nonce, &mut sockbuf, IS_HOST).unwrap();
        socket.send_to(&sockbuf, &emu_addr)?;

        let (reply_len, _src_addr) = socket.recv_from(&mut sockbuf).unwrap();
        assert!(reply_len > 0);
        let (header, payload) =
            Reassembler::single(&sockbuf[..reply_len], &mut reply_data, IS_HOST).unwrap();

        if header.is_pong() && payload == &nonce {
            println!("Pong OK");
        } else {
            println!("Invalid reply {}", hex::encode(sockbuf));
            break;
        }
    }

    Ok(())
}
