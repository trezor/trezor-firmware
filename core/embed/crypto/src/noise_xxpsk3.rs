use core::ops::DerefMut;

use rtl::{CSlice, CSliceMut};

use super::ffi;
use super::secret::{HazardGuard, SecretContext, SecretContextLock, ZeroableMemory};

pub const DHLEN: usize = ffi::NOISE_XXPSK3_DHLEN as usize;
pub const TAG_SIZE: usize = ffi::NOISE_XXPSK3_TAG_SIZE as usize;
pub const MAX_MESSAGE_SIZE: usize = ffi::NOISE_XXPSK3_MAX_MESSAGE_SIZE as usize;

pub type NoiseXXpsk3Ctx = SecretContext<ffi::noise_xxpsk3_initiator_t>;

// SAFETY: noise_xxpsk3_initiator_t represents a valid state when zeroed
unsafe impl ZeroableMemory for ffi::noise_xxpsk3_initiator_t {}

fn send_message(
    transport_state: &mut ffi::noise_xxpsk3_transport_state_t,
    payload: &[u8],
    ciphertext: &mut [u8],
) -> Result<usize, ()> {
    let payload = CSlice::from(payload);
    let ciphertext = CSliceMut::from(ciphertext);
    let mut ciphertext_size = 0usize;
    // SAFETY: ffi
    let res = unsafe {
        ffi::noise_xxpsk3_send_message(
            transport_state,
            payload.ptr(),
            payload.len(),
            ciphertext.ptr(),
            ciphertext.len(),
            &mut ciphertext_size as *mut _,
        )
    };
    if res {
        assert!(ciphertext_size >= payload.len() && ciphertext_size <= ciphertext.len());
        Ok(ciphertext_size)
    } else {
        Err(())
    }
}

fn receive_message(
    transport_state: &mut ffi::noise_xxpsk3_transport_state_t,
    ciphertext: &[u8],
    payload: &mut [u8],
) -> Result<usize, ()> {
    let ciphertext = CSlice::from(ciphertext);
    let payload = CSliceMut::from(payload);
    let mut payload_size = 0usize;
    // SAFETY: ffi
    let res = unsafe {
        ffi::noise_xxpsk3_receive_message(
            transport_state,
            ciphertext.ptr(),
            ciphertext.len(),
            payload.ptr(),
            payload.len(),
            &mut payload_size as *mut _,
        )
    };
    if res {
        assert!(payload_size <= ciphertext.len() && payload_size <= payload.len());
        Ok(payload_size)
    } else {
        Err(())
    }
}

impl HazardGuard<'_, ffi::noise_xxpsk3_initiator_t> {
    fn init(&mut self) -> Result<(), ()> {
        // SAFETY: ffi
        let res = unsafe { ffi::noise_xxpsk3_initiator_init(self.hazard_mut()) };
        if res { Ok(()) } else { Err(()) }
    }

    fn create_request1(&mut self, payload: &[u8], request: &mut [u8]) -> Result<usize, ()> {
        let payload = CSlice::from(payload);
        let request = CSliceMut::from(request);
        let mut request_size = 0usize;
        // SAFETY: ffi
        let res = unsafe {
            ffi::noise_xxpsk3_initiator_create_request1(
                self.hazard_mut(),
                payload.ptr(),
                payload.len(),
                request.ptr(),
                request.len(),
                &mut request_size as *mut _,
            )
        };
        if res {
            assert!(request_size > 0 && request_size <= request.len());
            Ok(request_size)
        } else {
            Err(())
        }
    }

    fn handle_response1(
        &mut self,
        response: &[u8],
        remote_static_public_key: &mut [u8; DHLEN],
        payload: &mut [u8],
    ) -> Result<usize, ()> {
        let response = CSlice::from(response);
        let payload = CSliceMut::from(payload);
        let mut payload_size = 0usize;
        // SAFETY: ffi
        let res = unsafe {
            ffi::noise_xxpsk3_initiator_handle_response1(
                self.hazard_mut(),
                response.ptr(),
                response.len(),
                remote_static_public_key.as_mut_ptr(),
                payload.ptr(),
                payload.len(),
                &mut payload_size as *mut _,
            )
        };
        if res {
            assert!(payload_size <= payload.len());
            Ok(payload_size)
        } else {
            Err(())
        }
    }

    fn create_request2(
        &mut self,
        static_private_key: &[u8; DHLEN],
        static_public_key: &[u8; DHLEN],
        psk: &[u8; DHLEN],
        payload: &[u8],
        request: &mut [u8],
    ) -> Result<usize, ()> {
        let payload = CSlice::from(payload);
        let request = CSliceMut::from(request);
        let mut request_size = 0usize;
        // SAFETY: ffi
        let res = unsafe {
            ffi::noise_xxpsk3_initiator_create_request2(
                self.hazard_mut(),
                static_private_key.as_ptr(),
                static_public_key.as_ptr(),
                psk.as_ptr(),
                payload.ptr(),
                payload.len(),
                request.ptr(),
                request.len(),
                &mut request_size as *mut _,
            )
        };
        if res {
            assert!(request_size > 0 && request_size <= request.len());
            Ok(request_size)
        } else {
            Err(())
        }
    }

    fn send_message(&mut self, payload: &[u8], ciphertext: &mut [u8]) -> Result<usize, ()> {
        send_message(&mut self.hazard_mut().transport_state, payload, ciphertext)
    }

    fn receive_message(&mut self, ciphertext: &[u8], payload: &mut [u8]) -> Result<usize, ()> {
        receive_message(&mut self.hazard_mut().transport_state, ciphertext, payload)
    }
}

pub struct NoiseXXpsk3<D: DerefMut<Target = NoiseXXpsk3Ctx>>(SecretContextLock<D>);

impl<D: DerefMut<Target = NoiseXXpsk3Ctx>> NoiseXXpsk3<D> {
    pub fn new(ctx: D) -> Result<Self, ()> {
        let mut locked_ctx = SecretContextLock::new(ctx);
        locked_ctx.guarded().init()?;
        Ok(Self(locked_ctx))
    }

    pub fn create_request1(&mut self, payload: &[u8], request: &mut [u8]) -> Result<usize, ()> {
        self.0.guarded().create_request1(payload, request)
    }

    pub fn handle_response1(
        &mut self,
        response: &[u8],
        remote_static_public_key: &mut [u8; DHLEN],
        payload: &mut [u8],
    ) -> Result<usize, ()> {
        self.0
            .guarded()
            .handle_response1(response, remote_static_public_key, payload)
    }

    pub fn create_request2(
        &mut self,
        static_private_key: &[u8; DHLEN],
        static_public_key: &[u8; DHLEN],
        psk: &[u8; DHLEN],
        payload: &[u8],
        request: &mut [u8],
    ) -> Result<usize, ()> {
        self.0.guarded().create_request2(
            static_private_key,
            static_public_key,
            psk,
            payload,
            request,
        )
    }

    pub fn send_message(&mut self, payload: &[u8], ciphertext: &mut [u8]) -> Result<usize, ()> {
        self.0.guarded().send_message(payload, ciphertext)
    }

    pub fn receive_message(&mut self, ciphertext: &[u8], payload: &mut [u8]) -> Result<usize, ()> {
        self.0.guarded().receive_message(ciphertext, payload)
    }
}

/// Responder side of the handshake, the counterpart of [`NoiseXXpsk3`]. Only
/// for testing the initiator, the firmware never acts as the responder.
#[cfg(feature = "noise_xxpsk3_responder")]
pub mod responder {
    use super::*;

    pub type NoiseXXpsk3ResponderCtx = SecretContext<ffi::noise_xxpsk3_responder_t>;

    // SAFETY: noise_xxpsk3_responder_t represents a valid state when zeroed
    unsafe impl ZeroableMemory for ffi::noise_xxpsk3_responder_t {}

    impl HazardGuard<'_, ffi::noise_xxpsk3_responder_t> {
        fn init(&mut self) -> Result<(), ()> {
            // SAFETY: ffi
            let res = unsafe { ffi::noise_xxpsk3_responder_init(self.hazard_mut()) };
            if res { Ok(()) } else { Err(()) }
        }

        fn handle_request1(&mut self, request: &[u8], payload: &mut [u8]) -> Result<usize, ()> {
            let request = CSlice::from(request);
            let payload = CSliceMut::from(payload);
            let mut payload_size = 0usize;
            // SAFETY: ffi
            let res = unsafe {
                ffi::noise_xxpsk3_responder_handle_request1(
                    self.hazard_mut(),
                    request.ptr(),
                    request.len(),
                    payload.ptr(),
                    payload.len(),
                    &mut payload_size as *mut _,
                )
            };
            if res {
                assert!(payload_size <= payload.len());
                Ok(payload_size)
            } else {
                Err(())
            }
        }

        fn create_response1(
            &mut self,
            static_private_key: &[u8; DHLEN],
            static_public_key: &[u8; DHLEN],
            payload: &[u8],
            response: &mut [u8],
        ) -> Result<usize, ()> {
            let payload = CSlice::from(payload);
            let response = CSliceMut::from(response);
            let mut response_size = 0usize;
            // SAFETY: ffi
            let res = unsafe {
                ffi::noise_xxpsk3_responder_create_response1(
                    self.hazard_mut(),
                    static_private_key.as_ptr(),
                    static_public_key.as_ptr(),
                    payload.ptr(),
                    payload.len(),
                    response.ptr(),
                    response.len(),
                    &mut response_size as *mut _,
                )
            };
            if res {
                assert!(response_size > 0 && response_size <= response.len());
                Ok(response_size)
            } else {
                Err(())
            }
        }

        fn handle_request2(
            &mut self,
            psk: &[u8; DHLEN],
            request: &[u8],
            remote_static_public_key: &mut [u8; DHLEN],
            payload: &mut [u8],
        ) -> Result<usize, ()> {
            let request = CSlice::from(request);
            let payload = CSliceMut::from(payload);
            let mut payload_size = 0usize;
            // SAFETY: ffi
            let res = unsafe {
                ffi::noise_xxpsk3_responder_handle_request2(
                    self.hazard_mut(),
                    psk.as_ptr(),
                    request.ptr(),
                    request.len(),
                    remote_static_public_key.as_mut_ptr(),
                    payload.ptr(),
                    payload.len(),
                    &mut payload_size as *mut _,
                )
            };
            if res {
                assert!(payload_size <= payload.len());
                Ok(payload_size)
            } else {
                Err(())
            }
        }

        fn send_message(&mut self, payload: &[u8], ciphertext: &mut [u8]) -> Result<usize, ()> {
            send_message(&mut self.hazard_mut().transport_state, payload, ciphertext)
        }

        fn receive_message(&mut self, ciphertext: &[u8], payload: &mut [u8]) -> Result<usize, ()> {
            receive_message(&mut self.hazard_mut().transport_state, ciphertext, payload)
        }
    }

    pub struct NoiseXXpsk3Responder<D: DerefMut<Target = NoiseXXpsk3ResponderCtx>>(
        SecretContextLock<D>,
    );

    impl<D: DerefMut<Target = NoiseXXpsk3ResponderCtx>> NoiseXXpsk3Responder<D> {
        pub fn new(ctx: D) -> Result<Self, ()> {
            let mut locked_ctx = SecretContextLock::new(ctx);
            locked_ctx.guarded().init()?;
            Ok(Self(locked_ctx))
        }

        pub fn handle_request1(&mut self, request: &[u8], payload: &mut [u8]) -> Result<usize, ()> {
            self.0.guarded().handle_request1(request, payload)
        }

        pub fn create_response1(
            &mut self,
            static_private_key: &[u8; DHLEN],
            static_public_key: &[u8; DHLEN],
            payload: &[u8],
            response: &mut [u8],
        ) -> Result<usize, ()> {
            self.0.guarded().create_response1(
                static_private_key,
                static_public_key,
                payload,
                response,
            )
        }

        pub fn handle_request2(
            &mut self,
            psk: &[u8; DHLEN],
            request: &[u8],
            remote_static_public_key: &mut [u8; DHLEN],
            payload: &mut [u8],
        ) -> Result<usize, ()> {
            self.0
                .guarded()
                .handle_request2(psk, request, remote_static_public_key, payload)
        }

        pub fn send_message(&mut self, payload: &[u8], ciphertext: &mut [u8]) -> Result<usize, ()> {
            self.0.guarded().send_message(payload, ciphertext)
        }

        pub fn receive_message(
            &mut self,
            ciphertext: &[u8],
            payload: &mut [u8],
        ) -> Result<usize, ()> {
            self.0.guarded().receive_message(ciphertext, payload)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::responder::{NoiseXXpsk3Responder, NoiseXXpsk3ResponderCtx};
    use super::*;
    use crate::curve25519::{Point, Scalar};

    type Initiator = NoiseXXpsk3<Box<NoiseXXpsk3Ctx>>;
    type Responder = NoiseXXpsk3Responder<Box<NoiseXXpsk3ResponderCtx>>;

    // both already clamped
    const INITIATOR_PRIVATE_KEY: [u8; DHLEN] = [0x48; DHLEN];
    const RESPONDER_PRIVATE_KEY: [u8; DHLEN] = [0x40; DHLEN];
    const PSK: [u8; DHLEN] = [0x50; DHLEN];

    fn public_key(private_key: &[u8; DHLEN]) -> [u8; DHLEN] {
        Point::from_secret(&Scalar::from_bytes(*private_key)).to_bytes()
    }

    /// Run the handshake with the responder using `responder_psk`, checking
    /// the payloads and the static keys received.
    fn handshake(responder_psk: &[u8; DHLEN]) -> Result<(Initiator, Responder), ()> {
        let initiator_public_key = public_key(&INITIATOR_PRIVATE_KEY);
        let responder_public_key = public_key(&RESPONDER_PRIVATE_KEY);
        let mut initiator = NoiseXXpsk3::new(Box::default())?;
        let mut responder = NoiseXXpsk3Responder::new(Box::default())?;
        let mut message = [0u8; 256];
        let mut payload = [0u8; 256];
        let mut remote_key = [0u8; DHLEN];

        let len = initiator.create_request1(b"request1", &mut message)?;
        let len = responder.handle_request1(&message[..len], &mut payload)?;
        assert_eq!(&payload[..len], b"request1");

        let len = responder.create_response1(
            &RESPONDER_PRIVATE_KEY,
            &responder_public_key,
            b"response1",
            &mut message,
        )?;
        let len = initiator.handle_response1(&message[..len], &mut remote_key, &mut payload)?;
        assert_eq!(&payload[..len], b"response1");
        assert_eq!(remote_key, responder_public_key);

        let len = initiator.create_request2(
            &INITIATOR_PRIVATE_KEY,
            &initiator_public_key,
            &PSK,
            b"request2",
            &mut message,
        )?;
        let len = responder.handle_request2(
            responder_psk,
            &message[..len],
            &mut remote_key,
            &mut payload,
        )?;
        assert_eq!(&payload[..len], b"request2");
        assert_eq!(remote_key, initiator_public_key);

        Ok((initiator, responder))
    }

    /// Encrypt `message` from the initiator to the responder.
    fn encrypt(initiator: &mut Initiator, message: &[u8]) -> Vec<u8> {
        let mut ciphertext = vec![0u8; message.len() + TAG_SIZE];
        let len = initiator.send_message(message, &mut ciphertext).unwrap();
        assert_eq!(len, ciphertext.len());
        ciphertext
    }

    /// Decrypt `ciphertext` received by the responder.
    fn decrypt(responder: &mut Responder, ciphertext: &[u8]) -> Result<Vec<u8>, ()> {
        let mut payload = vec![0u8; ciphertext.len()];
        let len = responder.receive_message(ciphertext, &mut payload)?;
        payload.truncate(len);
        Ok(payload)
    }

    #[test]
    fn test_handshake() {
        let (mut initiator, mut responder) = handshake(&PSK).unwrap();
        let mut ciphertext = [0u8; 256];
        let mut payload = [0u8; 256];
        for message in [&b"ping"[..], b"", b"pong"] {
            let len = initiator.send_message(message, &mut ciphertext).unwrap();
            assert_eq!(len, message.len() + TAG_SIZE);
            let len = responder
                .receive_message(&ciphertext[..len], &mut payload)
                .unwrap();
            assert_eq!(&payload[..len], message);

            let len = responder.send_message(message, &mut ciphertext).unwrap();
            let len = initiator
                .receive_message(&ciphertext[..len], &mut payload)
                .unwrap();
            assert_eq!(&payload[..len], message);
        }
    }

    #[test]
    fn test_handshake_psk_mismatch() {
        assert!(handshake(&[0x51; DHLEN]).is_err());
    }

    #[test]
    fn test_handshake_order() {
        let initiator_public_key = public_key(&INITIATOR_PRIVATE_KEY);
        let responder_public_key = public_key(&RESPONDER_PRIVATE_KEY);
        let mut message = [0u8; 256];

        let mut initiator: Initiator = NoiseXXpsk3::new(Box::default()).unwrap();
        // no transport before the handshake
        assert!(initiator.send_message(b"ping", &mut message).is_err());
        assert!(
            initiator
                .create_request2(
                    &INITIATOR_PRIVATE_KEY,
                    &initiator_public_key,
                    &PSK,
                    &[],
                    &mut message
                )
                .is_err()
        );
        // the failure ended the handshake
        assert!(initiator.create_request1(&[], &mut message).is_err());

        let mut responder: Responder = NoiseXXpsk3Responder::new(Box::default()).unwrap();
        assert!(
            responder
                .create_response1(
                    &RESPONDER_PRIVATE_KEY,
                    &responder_public_key,
                    &[],
                    &mut message
                )
                .is_err()
        );
    }

    #[test]
    fn test_transport() {
        let (mut initiator, mut responder) = handshake(&PSK).unwrap();
        let first = encrypt(&mut initiator, b"first");
        let second = encrypt(&mut initiator, b"second");
        assert_ne!(&first[..5], b"first");

        // a message out of order is rejected, without affecting the ones that
        // follow
        assert!(decrypt(&mut responder, &second).is_err());
        assert_eq!(decrypt(&mut responder, &first).unwrap(), b"first");
        // a replayed message is rejected
        assert!(decrypt(&mut responder, &first).is_err());

        // tampering with the ciphertext or the tag is detected, no
        // unauthenticated plaintext is returned
        for i in [0, second.len() - 1] {
            let mut tampered = second.clone();
            tampered[i] ^= 0x01;
            let mut payload = [0u8; 64];
            assert!(responder.receive_message(&tampered, &mut payload).is_err());
            assert_ne!(&payload[..6], b"second");
        }
        assert_eq!(decrypt(&mut responder, &second).unwrap(), b"second");
    }

    #[test]
    fn test_limits() {
        const MAX_PLAINTEXT_SIZE: usize = MAX_MESSAGE_SIZE - TAG_SIZE;
        let payload = vec![0u8; MAX_PLAINTEXT_SIZE + 1];
        let mut message = vec![0u8; MAX_MESSAGE_SIZE + 1];
        let mut received = vec![0u8; MAX_MESSAGE_SIZE + 1];

        // request1 = ephemeral key + payload + tag
        let max_request1_payload = &payload[..MAX_MESSAGE_SIZE - DHLEN - TAG_SIZE];
        let mut initiator: Initiator = NoiseXXpsk3::new(Box::default()).unwrap();
        let len = initiator
            .create_request1(max_request1_payload, &mut message)
            .unwrap();
        assert_eq!(len, MAX_MESSAGE_SIZE);
        let mut initiator: Initiator = NoiseXXpsk3::new(Box::default()).unwrap();
        let request1_payload = &payload[..max_request1_payload.len() + 1];
        assert!(
            initiator
                .create_request1(request1_payload, &mut message)
                .is_err()
        );

        let (mut initiator, mut responder) = handshake(&PSK).unwrap();
        assert!(initiator.send_message(&payload, &mut message).is_err());
        let len = initiator
            .send_message(&payload[..MAX_PLAINTEXT_SIZE], &mut message)
            .unwrap();
        assert_eq!(len, MAX_MESSAGE_SIZE);
        // the sentinel shows the message was rejected for its size, before
        // decryption failed and wiped the buffer
        received[0] = 0xa5;
        assert!(responder.receive_message(&message, &mut received).is_err());
        assert_eq!(received[0], 0xa5);
        let len = responder
            .receive_message(&message[..len], &mut received)
            .unwrap();
        assert_eq!(len, MAX_PLAINTEXT_SIZE);

        // the buffers are too short
        let ping = b"ping";
        let ciphertext_buffer = &mut message[..ping.len() + TAG_SIZE];
        assert!(
            initiator
                .send_message(ping, &mut ciphertext_buffer[1..])
                .is_err()
        );
        let len = initiator.send_message(ping, ciphertext_buffer).unwrap();
        let ciphertext = &message[..len];
        assert!(
            responder
                .receive_message(ciphertext, &mut received[..ping.len() - 1])
                .is_err()
        );
        assert!(
            responder
                .receive_message(&ciphertext[..TAG_SIZE - 1], &mut received)
                .is_err()
        );
        // the rejected calls did not use up a nonce
        let len = responder
            .receive_message(ciphertext, &mut received[..ping.len()])
            .unwrap();
        assert_eq!(&received[..len], ping);
    }
}
