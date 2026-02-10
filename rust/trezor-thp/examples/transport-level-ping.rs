use std::env;
use std::io::ErrorKind;
use std::net::{SocketAddr, UdpSocket};
use std::str::FromStr;
use std::time::Duration;

use trezor_thp::{
    Backend, channel::buffered::ChannelExt, channel::host::Mux, credential::NullCredentialStore,
};

struct RustCrypto;

impl Backend for RustCrypto {
    type DH = trezor_noise_rust_crypto::X25519;
    type Cipher = trezor_noise_rust_crypto::Aes256Gcm;
    type Hash = trezor_noise_rust_crypto::Sha256;

    fn random_bytes(dest: &mut [u8]) {
        getrandom::fill(dest).unwrap();
    }
}

const REPEAT: u8 = 1;
const PACKET_LEN: usize = 64;
const READ_TIMEOUT: Duration = Duration::from_secs(2);

pub fn main() -> std::io::Result<()> {
    let port_str = env::args().nth(1).unwrap_or("21324".to_string());
    let port = u16::from_str(&port_str).expect("UDP port number");
    let emu_addr = SocketAddr::from(([127, 0, 0, 1], port));
    let socket = UdpSocket::bind("127.0.0.1:0")?;

    let mut recvbuf = [0u8; PACKET_LEN];
    let mut mux = Mux::<_, RustCrypto>::new(NullCredentialStore).into_buffered();
    mux.set_packet_len(PACKET_LEN);

    for _i in 0..REPEAT {
        mux.ping();
        let packet = mux.packet_out().unwrap();
        socket.send_to(&packet, &emu_addr)?;
        socket.set_read_timeout(Some(READ_TIMEOUT))?;
        match socket.recv_from(&mut recvbuf) {
            Ok(_) => {}
            Err(e) if matches!(e.kind(), ErrorKind::WouldBlock | ErrorKind::TimedOut) => {
                println!("Ping timeout");
                return Ok(());
            }
            Err(e) => {
                return Err(e);
            }
        };
        let res = mux.packet_in(&recvbuf);
        if res.got_pong() {
            println!("Pong OK");
        } else {
            println!("Invalid reply {}", hex::encode(recvbuf));
            break;
        }
    }

    Ok(())
}
