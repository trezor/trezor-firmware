//! The card side of the emulated NFC driver.

use rtl::error::Error as RtlError;

use super::apdu::Apdu;
use super::{ffi, NfcError};

/// Place a card with `uid` in the field, or remove the card if `uid` is
/// `None`. Removing the card fails the exchange in progress.
pub fn set_connected(uid: Option<&[u8]>) -> Result<(), NfcError> {
    let (ptr, len) = uid.map_or((core::ptr::null(), 0), |uid| (uid.as_ptr(), uid.len()));
    // SAFETY: ffi, the UID is copied before the call returns
    unsafe { ffi::nfc_emu_set_connected(ptr, len) }.ok()?;
    Ok(())
}

/// Take the frame waiting to be sent to the card, and whether it is the
/// reader's PSK share. Fails with `TagDisconnected` if the card is not in the
/// field.
pub fn get_command() -> Result<Option<(Apdu, bool)>, NfcError> {
    let mut cmd: *mut Apdu = core::ptr::null_mut();
    let mut is_psk = false;
    // SAFETY: ffi
    unsafe { ffi::nfc_emu_get_command(&mut cmd, &mut is_psk) }.ok()?;
    // SAFETY: the frame lives in the driver state, which is not modified until
    // `nfc_emu_set_response()`. It is copied out right away.
    let frame = unsafe { cmd.as_ref() }.map(|apdu| {
        let copy = Apdu {
            data: apdu.data,
            data_len: apdu.data_len,
        };
        (copy, is_psk)
    });
    Ok(frame)
}

/// Complete the exchange with the card's response, or fail it with the given
/// error. Fails with `TagDisconnected` if the card is not in the field.
pub fn set_response(response: Result<&[u8], RtlError>) -> Result<(), NfcError> {
    let res = match response {
        // SAFETY: ffi, the response is copied before the call returns
        Ok(data) => unsafe { ffi::nfc_emu_set_response(0, data.as_ptr(), data.len()) },
        // SAFETY: ffi
        Err(e) => unsafe {
            let status = e as u32;
            assert!(status != 0);
            ffi::nfc_emu_set_response(status, core::ptr::null(), 0)
        },
    };
    res.ok()?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use crypto::curve25519::{Point, Scalar};
    use crypto::noise_xxpsk3::responder::{NoiseXXpsk3Responder, NoiseXXpsk3ResponderCtx};
    use Instruction::*;

    use super::super::*;
    use super::*;

    const UID: &[u8] = &[0x01; 7];
    // both already clamped
    const CARD_PRIVATE_KEY: [u8; DHLEN] = [0x40; DHLEN];
    const READER_PRIVATE_KEY: [u8; DHLEN] = [0x48; DHLEN];
    const CERTIFICATE: &[u8] = b"certificate";
    const WELCOME_MESSAGE: &[u8] = b"K1N1\0";

    fn public_key(private_key: &[u8; DHLEN]) -> [u8; DHLEN] {
        Point::from_secret(&Scalar::from_bytes(*private_key)).to_bytes()
    }

    /// Command data of a C-APDU, assuming there is some.
    fn command_data(apdu: &[u8]) -> &[u8] {
        match &apdu[4..] {
            [0, hi, lo, rest @ ..] => &rest[..usize::from(u16::from_be_bytes([*hi, *lo]))],
            [lc, rest @ ..] => &rest[..usize::from(*lc)],
            [] => &[],
        }
    }

    /// The card side of `setup()`, see `tests/k1n1.py` for the full card.
    struct Card {
        pin: &'static str,
        /// Instructions of the frames received, `None` for the PSK share.
        received: Vec<Option<Instruction>>,
        psk: Option<[u8; NOISE_PSK_LEN]>,
        noise: NoiseXXpsk3Responder<Box<NoiseXXpsk3ResponderCtx>>,
        secure: bool,
    }

    impl Card {
        fn new(pin: &'static str) -> Self {
            Self {
                pin,
                received: Vec::new(),
                psk: None,
                noise: NoiseXXpsk3Responder::new(Box::default()).unwrap(),
                secure: false,
            }
        }

        /// The PIN field is the digits padded with 0xff (card API, section
        /// 7.1).
        fn pin_matches(&self, field: &[u8]) -> bool {
            let (digits, padding) = field.split_at(self.pin.len());
            field.len() == MAX_PIN_LEN
                && digits == self.pin.as_bytes()
                && padding.iter().all(|&b| b == 0xff)
        }

        fn encrypt(&mut self, plaintext: &[u8]) -> Vec<u8> {
            let mut buf = [0u8; Apdu::MAX_LEN];
            let len = self.noise.send_message(plaintext, &mut buf).unwrap();
            buf[..len].to_vec()
        }

        fn process(&mut self, frame: &[u8], is_psk: bool) -> Vec<u8> {
            if is_psk {
                self.received.push(None);
                let mut card_share = [0u8; NOISE_PSK_SHARE_LEN];
                random::bytes(&mut card_share);
                // the reader's share comes first
                self.psk = Some([frame, &card_share].concat().try_into().unwrap());
                return card_share.to_vec();
            }
            // the response to HANDSHAKE completing the handshake is not
            // encrypted again
            let secure = self.secure;
            let mut buf = [0u8; Apdu::MAX_LEN];
            let apdu = if secure {
                let len = self.noise.receive_message(frame, &mut buf).unwrap();
                &buf[..len]
            } else {
                frame
            };
            let (data, sw) = self.execute(apdu);
            let mut response = if secure { self.encrypt(&data) } else { data };
            response.extend_from_slice(&u16::from(sw).to_be_bytes());
            response
        }

        fn execute(&mut self, apdu: &[u8]) -> (Vec<u8>, StatusWord) {
            let ins = Instruction::try_from(u16::from_be_bytes([apdu[0], apdu[1]])).ok();
            self.received.push(ins);
            let mut buf = [0u8; Apdu::MAX_LEN];
            match (ins, apdu[2]) {
                (Some(Select), _) => (Vec::new(), StatusWord::Success),
                (Some(Handshake), 0x00) => {
                    let request = command_data(apdu);
                    self.noise.handle_request1(request, &mut buf).unwrap();
                    let card_public_key = public_key(&CARD_PRIVATE_KEY);
                    let len = self
                        .noise
                        .create_response1(
                            &CARD_PRIVATE_KEY,
                            &card_public_key,
                            CERTIFICATE,
                            &mut buf,
                        )
                        .unwrap();
                    (buf[..len].to_vec(), StatusWord::Success)
                }
                (Some(Handshake), 0x01) => {
                    let mut reader_key = [0u8; DHLEN];
                    let psk = self.psk.unwrap();
                    let request = command_data(apdu);
                    self.noise
                        .handle_request2(&psk, request, &mut reader_key, &mut buf)
                        .unwrap();
                    assert_eq!(reader_key, public_key(&READER_PRIVATE_KEY));
                    self.secure = true;
                    (self.encrypt(WELCOME_MESSAGE), StatusWord::Success)
                }
                (Some(PinUnlocked), _) if self.pin.is_empty() => (Vec::new(), StatusWord::Success),
                (Some(Authenticate), _) if self.pin_matches(command_data(apdu)) => {
                    (Vec::new(), StatusWord::Success)
                }
                (Some(PinUnlocked | Authenticate), _) => {
                    (Vec::new(), StatusWord::ApiPermissionDenied)
                }
                (Some(GetUid), _) => (UID.to_vec(), StatusWord::Success),
                _ => (Vec::new(), StatusWord::CommandInvalid),
            }
        }
    }

    /// Place the card in the field and connect to it.
    fn connect() -> TapContext<Box<NoiseXXpsk3Ctx>> {
        // forget the state left by the previous test
        stop_discovery().unwrap();
        set_connected(Some(UID)).unwrap();
        start_discovery().unwrap();
        TapContext::get(Box::default()).unwrap()
    }

    /// Let `card` answer the frame sent by the reader.
    fn answer(card: &mut Card) {
        let (frame, is_psk) = get_command().unwrap().expect("a frame was sent");
        let response = card.process(frame.as_slice(), is_psk);
        set_response(Ok(&response)).unwrap();
    }

    /// Answer the frame sent by the reader with `response`.
    fn answer_with(response: &[u8]) {
        get_command().unwrap().expect("a frame was sent");
        set_response(Ok(response)).unwrap();
    }

    /// One step of `setup()` with the reader's static key.
    fn setup_step(
        ctx: &mut TapContext<Box<NoiseXXpsk3Ctx>>,
        pin: Option<&str>,
        verify_fn: &mut dyn FnMut(&[u8; DHLEN], &[u8]) -> bool,
    ) -> Result<bool, NfcError> {
        let public = public_key(&READER_PRIVATE_KEY);
        let keys = NoiseKeyPair {
            private: &READER_PRIVATE_KEY,
            public: &public,
        };
        ctx.setup(Some(keys), pin, verify_fn)
    }

    /// Run `setup()` with `card` answering, until it finishes or fails.
    fn setup(
        ctx: &mut TapContext<Box<NoiseXXpsk3Ctx>>,
        card: &mut Card,
        pin: Option<&str>,
    ) -> Result<(), NfcError> {
        while !setup_step(ctx, pin, &mut |_, _| true)? {
            answer(card);
        }
        Ok(())
    }

    const HANDSHAKE: [Option<Instruction>; 4] =
        [Some(Select), None, Some(Handshake), Some(Handshake)];

    #[test]
    fn test_setup() {
        // (card PIN, PIN given by the reader, commands after the handshake)
        let cases: &[(&str, Option<&str>, &[Instruction])] = &[
            ("", None, &[]),
            ("", Some(""), &[PinUnlocked, Authenticate]),
            ("1234", Some("1234"), &[Authenticate]),
        ];
        for &(card_pin, pin, after_handshake) in cases {
            let mut ctx = connect();
            let mut card = Card::new(card_pin);
            let mut verified = None;
            while !setup_step(&mut ctx, pin, &mut |key, cert| {
                verified = Some((*key, cert.to_vec()));
                true
            })
            .unwrap()
            {
                answer(&mut card);
            }
            assert_eq!(
                verified,
                Some((public_key(&CARD_PRIVATE_KEY), CERTIFICATE.to_vec()))
            );
            let expected: Vec<_> = HANDSHAKE
                .into_iter()
                .chain(after_handshake.iter().copied().map(Some))
                .collect();
            assert_eq!(card.received, expected, "PIN {pin:?}");

            // the secure channel works both ways
            ctx.command(&CApdu::compose(GetUid, &[]).unwrap()).unwrap();
            answer(&mut card);
            assert_eq!(ctx.response().unwrap(), Some(UID));
        }
    }

    #[test]
    fn test_setup_wrong_pin() {
        let denied = u16::from(StatusWord::ApiPermissionDenied);
        // (PIN given by the reader, the last command sent)
        let cases = [(Some(""), PinUnlocked), (Some("4321"), Authenticate)];
        for (pin, last) in cases {
            let mut ctx = connect();
            let mut card = Card::new("1234");
            assert!(matches!(
                setup(&mut ctx, &mut card, pin),
                Err(NfcError::CommandFailed(code)) if code == denied
            ));
            // no PIN attempt is used when the reader expects an unset PIN
            assert_eq!(card.received.last(), Some(&Some(last)));
            assert!(matches!(
                setup(&mut ctx, &mut card, pin),
                Err(NfcError::UnexpectedInput)
            ));
        }
    }

    #[test]
    fn test_setup_rejected_certificate() {
        let mut ctx = connect();
        let mut card = Card::new("");
        let res = loop {
            match setup_step(&mut ctx, None, &mut |_, _| false) {
                Ok(false) => answer(&mut card),
                res => break res,
            }
        };
        assert!(matches!(res, Err(NfcError::InvalidCertificate)));
        // the handshake is not finished
        assert_eq!(card.received, HANDSHAKE[..3]);
        assert!(get_command().unwrap().is_none());
    }

    #[test]
    fn test_setup_card_errors() {
        let mut ctx = connect();
        assert!(!setup_step(&mut ctx, None, &mut |_, _| true).unwrap());
        answer_with(&[0x6a, 0x82]);
        assert!(matches!(
            setup_step(&mut ctx, None, &mut |_, _| true),
            Err(NfcError::CommandFailed(0x6a82))
        ));

        // the card share is too short
        let mut ctx = connect();
        assert!(!setup_step(&mut ctx, None, &mut |_, _| true).unwrap());
        answer_with(&[0x90, 0x00]);
        assert!(!setup_step(&mut ctx, None, &mut |_, _| true).unwrap());
        answer_with(&[0x69, 0xf0]);
        assert!(matches!(
            setup_step(&mut ctx, None, &mut |_, _| true),
            Err(NfcError::InvalidData)
        ));
    }

    #[test]
    fn test_setup_card_removed() {
        for removed_after in 0..HANDSHAKE.len() {
            let mut ctx = connect();
            let mut card = Card::new("");
            for _ in 0..removed_after {
                assert!(!setup_step(&mut ctx, None, &mut |_, _| true).unwrap());
                answer(&mut card);
            }
            assert!(!setup_step(&mut ctx, None, &mut |_, _| true).unwrap());
            set_connected(None).unwrap();
            assert!(matches!(
                setup_step(&mut ctx, None, &mut |_, _| true),
                Err(NfcError::TagDisconnected)
            ));
        }
    }

    #[test]
    fn test_command_not_sent() {
        let mut ctx = connect();
        let mut card = Card::new("");
        setup(&mut ctx, &mut card, None).unwrap();

        // the message is encrypted, but never reaches the card
        set_connected(None).unwrap();
        assert!(ctx.command(&CApdu::compose(GetUid, &[]).unwrap()).is_err());
        // the nonces of the reader and the card no longer match
        set_connected(Some(UID)).unwrap();
        assert!(matches!(
            ctx.command(&CApdu::compose(GetUid, &[]).unwrap()),
            Err(NfcError::UnexpectedInput)
        ));
    }
}
