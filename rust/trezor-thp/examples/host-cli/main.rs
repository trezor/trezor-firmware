mod client;
mod pb;

use std::{env, net::SocketAddr, str::FromStr};

use protobuf::Message;

use trezor_thp::{
    Backend, Channel, Host,
    channel::host::{ChannelOpen, ChannelPairing},
    credential::{CredentialStore, NullCredentialStore},
};

use client::Client;
use pb::{
    messages::MessageType::*, messages_common::*, messages_management::*,
    messages_thp::ThpMessageType::*, messages_thp::*,
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

fn do_handshake<C>(client: &mut Client<ChannelOpen<C, RustCrypto>>)
where
    C: CredentialStore,
{
    // Handshake should finish within 3 request-response cycles.
    // Device properties and channel id are available after the first one.
    client.call(0, &[]);
    let device_properties =
        ThpDeviceProperties::parse_from_bytes(client.channel.device_properties()).unwrap();
    log::debug!("Device properties: {:?}.", device_properties);
    client.call(0, &[]);
    client.call(0, &[]);
}

fn do_pairing(client: &mut Client<ChannelPairing<RustCrypto>>) {
    let device_properties =
        ThpDeviceProperties::parse_from_bytes(client.channel.device_properties()).unwrap();

    let mut pairing_methods = Vec::new();
    for p in &device_properties.pairing_methods {
        if let Ok(method) = p.enum_value() {
            pairing_methods.push(method);
        }
    }

    if pairing_methods.contains(&ThpPairingMethod::SkipPairing) {
        do_pairing_skip(client)
    } else {
        log::error!("Device does not support SkipPairing.");
        panic!();
    }
}

fn do_pairing_skip(client: &mut Client<ChannelPairing<RustCrypto>>) {
    let mut pairing_request = ThpPairingRequest::new();
    pairing_request.set_host_name("localhost".into());
    pairing_request.set_app_name("trezor-thp/examples".into());

    client.call_pb::<ThpPairingRequestApproved, _>(
        ThpMessageType_ThpPairingRequest,
        pairing_request,
        ThpMessageType_ThpPairingRequestApproved,
    );

    let mut select_method = ThpSelectMethod::new();
    select_method.set_selected_pairing_method(ThpPairingMethod::SkipPairing);
    client.call_pb::<ThpEndResponse, _>(
        ThpMessageType_ThpSelectMethod,
        select_method,
        ThpMessageType_ThpEndResponse,
    );
}

fn do_ping(client: &mut Client<Channel<Host, RustCrypto>>) {
    let mut ping = Ping::new();
    ping.set_message("trezor-thp/examples".into());
    ping.set_button_protection(true);
    let success = client.call_pb::<Success, _>(MessageType_Ping, ping, MessageType_Success);
    println!("{}({})", Success::NAME, success);
}

fn get_address() -> SocketAddr {
    let port_str = env::args().nth(1).unwrap_or("21324".to_string());
    let port = u16::from_str(&port_str).expect("UDP port number");
    SocketAddr::from(([127, 0, 0, 1], port))
}

pub fn main() -> std::io::Result<()> {
    env_logger::init_from_env(env_logger::Env::default().filter_or("RUST_LOG", "info"));

    let cred_lookup = NullCredentialStore;
    let channel = ChannelOpen::<_, RustCrypto>::new(false, cred_lookup).unwrap();
    let mut client = Client::open(get_address(), channel);

    do_handshake(&mut client);
    assert!(client.channel.handshake_done());
    let mut client = client.map(|c| c.complete().unwrap());

    do_pairing(&mut client);
    assert!(client.channel.pairing_done());
    let mut client = client.map(|c| c.complete().unwrap());

    do_ping(&mut client);
    Ok(())
}
