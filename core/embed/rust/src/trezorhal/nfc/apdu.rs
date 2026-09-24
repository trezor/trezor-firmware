use heapless::Vec;
use num_traits::FromPrimitive;

use super::NfcError;

pub const APPLET_TREZOR_KEEP: &[u8] = &[0xa0, 0x00, 0x00, 0x09, 0x59, 0x00, 0x01];

pub type Apdu = super::ffi::nfc_apdu_message_t;

// Values corresponding to CLA INS.
#[repr(u16)]
#[derive(Copy, Clone)]
pub enum Instruction {
    Select = 0x00a4,
    Handshake = 0x8001,
    Authenticate = 0x8003,
    SetPin = 0x8004,
    Wipe = 0x8005,
    ReadPinCounter = 0x8008,
    ReadSuccessLog = 0x8009,
    ReadFailureLogs = 0x800a,
    ReadSeedMetadata = 0x800b,
    WriteSeedMetadata = 0x800c,
    ReadSeed = 0x800d,
    WriteSeed = 0x800e,
    ActivateFlashloader = 0xc2a0,
}

#[repr(u16)]
#[derive(Copy, Clone, FromPrimitive)]
pub enum StatusWord {
    /// Command executed.
    Success = 0x9000,
    /// Malformed Lc/Le, or a length the command does not accept.
    WrongLength = 0x6700,
    /// Class not supported.
    UnknownCLA = 0x6e00,
    /// Instruction not supported.
    UnknownINS = 0x6d00,
    /// SELECT could not resolve the AID or file identifier.
    FileNotFound = 0x6a82,
    /// Parameter out of range, e.g. a READ BINARY offset beyond the end of the
    /// file.
    IncorrectP1P2 = 0x6a86,
    /// Command data rejected by the card.
    DataInvalid = 0x6984,
    /// A valid command in an unsupported mode, e.g. an unsupported SELECT mode.
    FunctionNotSupported = 0x6a81,
}
// 0x07d0 - handshake required?
// 0x01f8 - seed metadata already exist??
// 0x0005 - seed doesn't exist?

impl From<Instruction> for u16 {
    fn from(val: Instruction) -> Self {
        val as u16
    }
}

struct InsProps {
    needs_handshake: bool,
    needs_auth: bool,
    encrypted_data: bool,
    max_response: u16,
}

const fn props(
    needs_handshake: bool,
    needs_auth: bool,
    encrypted_data: bool,
    max_response: u16,
) -> InsProps {
    InsProps {
        needs_handshake,
        needs_auth,
        encrypted_data,
        max_response,
    }
}

impl Instruction {
    const fn props(&self) -> InsProps {
        let small = 255;
        let large = Apdu::MAX_RESPONSE_DATA_LEN as u16;
        match self {
            Instruction::Select => props(false, false, false, 0),
            Instruction::Handshake => props(false, false, false, large),
            Instruction::Authenticate => props(true, false, true, 0),
            Instruction::SetPin => props(true, true, true, 0),
            Instruction::Wipe => props(false, false, false, 0),
            Instruction::ReadPinCounter => props(false, false, false, small),
            Instruction::ReadSuccessLog => props(false, false, false, small),
            Instruction::ReadFailureLogs => props(false, false, false, large),
            Instruction::ReadSeedMetadata => props(false, false, false, large),
            Instruction::WriteSeedMetadata => props(true, true, false /* ? */, 0),
            Instruction::ReadSeed => props(true, true, true, large),
            Instruction::WriteSeed => props(true, true, true, 0),
            Instruction::ActivateFlashloader => props(false, false, false, 0),
        }
    }

    pub const fn max_expected_response(&self) -> u16 {
        self.props().max_response
    }

    pub const fn needs_handshake(&self) -> bool {
        self.props().needs_handshake
    }

    pub const fn needs_auth(&self) -> bool {
        self.props().needs_auth
    }

    pub const fn encrypted_data(&self) -> bool {
        self.props().encrypted_data
    }
}

impl From<StatusWord> for u16 {
    fn from(val: StatusWord) -> Self {
        val as u16
    }
}

impl Apdu {
    pub const MAX_LEN: usize = super::ffi::NFC_MAX_APDU_LEN as usize;
    pub const MAX_RESPONSE_DATA_LEN: usize = Self::MAX_LEN - 2;

    pub const fn zero() -> Self {
        Self {
            data: [0u8; Self::MAX_LEN],
            data_len: 0,
        }
    }

    pub fn len(&self) -> usize {
        self.data_len.into()
    }

    pub fn as_slice(&self) -> &[u8] {
        &self.data[..self.len()]
    }

    fn encode_lengths(data_len: u16, expected_len: u16) -> (Vec<u8, 3>, Vec<u8, 3>) {
        let mut bytes_data = Vec::new();
        let mut bytes_expected = Vec::new();
        let both_short = data_len <= 255 && expected_len <= 256;

        if data_len > 0 {
            if both_short {
                bytes_data.push(data_len as u8).unwrap()
            } else {
                bytes_data.push(0).unwrap();
                bytes_data
                    .extend_from_slice(&data_len.to_be_bytes())
                    .unwrap();
            }
        }

        match expected_len {
            0 => {}
            256 if both_short => {
                bytes_expected.push(0).unwrap();
            }
            _ if both_short => {
                bytes_expected.push(expected_len as u8).unwrap();
            }
            _ => {
                if bytes_data.is_empty() {
                    bytes_expected.push(0).unwrap();
                }
                bytes_expected
                    .extend_from_slice(&expected_len.to_be_bytes())
                    .unwrap();
            }
        }

        (bytes_data, bytes_expected)
    }

    pub fn command(
        cla: u8,
        ins: u8,
        p1: u8,
        p2: u8,
        data: &[u8],
        expected: u16,
    ) -> Result<Self, ()> {
        let mut apdu = [0u8; Self::MAX_LEN];
        let mut apdu_len = 0usize;

        let data_len: u16 = data.len().try_into().map_err(|_| ())?;
        let (encoded_data_len, encoded_expected_len) = Self::encode_lengths(data_len, expected);

        let items: [&[u8]; _] = [
            &[cla, ins, p1, p2],
            encoded_data_len.as_slice(),
            data,
            encoded_expected_len.as_slice(),
        ];
        if items.iter().map(|x| x.len()).sum::<usize>() > Self::MAX_LEN {
            return Err(());
        }
        for elem in items {
            let new_len = apdu_len + elem.len();
            apdu[apdu_len..new_len].copy_from_slice(elem);
            apdu_len = new_len;
        }
        Ok(Self {
            data: apdu,
            data_len: apdu_len as u16,
        })
    }

    pub fn compose(inst: Instruction, p1: u8, p2: u8, data: &[u8]) -> Result<Self, ()> {
        let [cla, ins] = u16::from(inst).to_be_bytes();
        Self::command(cla, ins, p1, p2, data, inst.max_expected_response())
    }

    pub fn response(&self) -> Result<&[u8], NfcError> {
        let len = self.data_len.into();
        assert!(len <= Self::MAX_LEN);
        let (data, sw) = &self.data[..len]
            .split_last_chunk::<2>()
            .ok_or(NfcError::InvalidData)?;
        let code = u16::from_be_bytes(**sw);
        match StatusWord::from_u16(code) {
            Some(StatusWord::Success) => Ok(data),
            Some(sw) => {
                log::error!("Command failed: {:04x}", u16::from(sw));
                Err(NfcError::CommandFailed(sw))
            }
            None => {
                log::error!("Command failed: unknown status: {:04x}", code);
                Err(NfcError::CommandFailedUnknown(code))
            }
        }
    }

    pub fn response_nodata(&self) -> Result<(), NfcError> {
        let data = self.response()?;
        if !data.is_empty() {
            log::error!("Expected no data, got {} bytes.", data.len());
            return Err(NfcError::InvalidData);
        }
        Ok(())
    }
}

impl AsRef<[u8]> for Apdu {
    fn as_ref(&self) -> &[u8] {
        self.as_slice()
    }
}
