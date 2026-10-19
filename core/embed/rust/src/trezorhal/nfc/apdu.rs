//! Implements subset of ISO/IEC 7816-4 Application Protocol Data Unit format.

use core::ops::{Deref, DerefMut};

use heapless::Vec;
use num_traits::FromPrimitive;
use sys::ulog;

use super::NfcError;

pub const APPLET_TREZOR_N1W1: &[u8] = &[0xa0, 0x00, 0x00, 0x09, 0x59, 0x00, 0x01];

pub(super) type Apdu = super::ffi::nfc_apdu_message_t;

// Values corresponding to CLA INS.
#[repr(u16)]
#[derive(Copy, Clone, FromPrimitive, ufmt::derive::uDebug)]
pub enum Instruction {
    Select = 0x00a4,

    GetOsVersion = 0x2001,
    GetUid = 0x2002,
    MeasureCpuFrequency = 0x2003,
    HardenMemory = 0x2004,
    IntegrityCheck = 0x2005,

    Handshake = 0x8001,
    PinUnlocked = 0x8003,
    Authenticate = 0x8004,
    SetPin = 0x8005,
    Wipe = 0x8006,
    ReadPinCounter = 0x8007,
    ReadSuccessLog = 0x8008,
    ReadFailureLogs = 0x8009,
    ReadSeedMetadata = 0x800a,
    WriteSeedMetadata = 0x800b,
    ReadSeed = 0x800c,
    WriteSeed = 0x800d,
}

impl From<Instruction> for u16 {
    fn from(ins: Instruction) -> Self {
        ins.code()
    }
}

impl TryFrom<u16> for Instruction {
    type Error = NfcError;

    fn try_from(code: u16) -> Result<Self, NfcError> {
        Instruction::from_u16(code).ok_or(NfcError::InvalidData)
    }
}

struct InsProps {
    needs_handshake: bool,
    needs_auth: bool,
    max_response: u16,
}

const fn props(needs_handshake: bool, needs_auth: bool, max_response: u16) -> InsProps {
    InsProps {
        needs_handshake,
        needs_auth,
        max_response,
    }
}

impl Instruction {
    const fn props(&self) -> InsProps {
        let small = 255; // FIXME tag
        let large = RApdu::MAX_DATA_LEN as u16; // FIXME tag
        match self {
            Instruction::Select => props(false, false, 0),
            Instruction::GetOsVersion => props(false, false, small),
            Instruction::GetUid => props(false, false, small),
            Instruction::MeasureCpuFrequency => props(false, false, small),
            Instruction::HardenMemory => props(false, false, 0),
            Instruction::IntegrityCheck => props(false, false, small),

            Instruction::Handshake => props(false, false, large),
            Instruction::PinUnlocked => props(false, false, 0), //?
            Instruction::Authenticate => props(true, false, 0),
            Instruction::SetPin => props(true, true, 0),
            Instruction::Wipe => props(true, false, 0),
            Instruction::ReadPinCounter => props(false, false, small),
            Instruction::ReadSuccessLog => props(false, false, small),
            Instruction::ReadFailureLogs => props(false, false, large),
            Instruction::ReadSeedMetadata => props(true, true, large),
            Instruction::WriteSeedMetadata => props(true, true, large),
            Instruction::ReadSeed => props(true, true, large),
            Instruction::WriteSeed => props(true, true, large),
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

    pub const fn code(&self) -> u16 {
        *self as u16
    }
}

#[repr(u16)]
#[derive(Copy, Clone, FromPrimitive, ufmt::derive::uDebug)]
pub enum StatusWord {
    /// Command executed.
    Success = 0x9000,

    /// SELECT with data of the wrong length.
    WrongLength = 0x6700,
    /// Firmware update: command not allowed in the current state, or a
    /// signature, hash or integrity check failed.
    ConditionsNotSatisfied = 0x6985,
    /// SELECT could not resolve the AID or file identifier.
    FileNotFound = 0x6a82,
    /// Firmware update and flashloader activation: P1 or P2 not 0x00.
    IncorrectP1P2 = 0x6a86,
    /// Firmware update: command data of wrong length or content.
    WrongParameters = 0x6b00,
    /// Unassigned instruction within the firmware update group (0x17-0x1F).
    UnknownINS = 0x6d00,

    SystemInternal = 0xf001,
    SystemStorageInit = 0xf002,
    CommandInvalid = 0xf101,
    CommandInvalidFormat = 0xf102,
    CommandInvalidParamters = 0xf103,
    CommandInternalError = 0xf104,
    ApiHandshakeRequired = 0xf301,
    ApiPermissionDenied = 0xf302,
    ApiPskNotAvailable = 0xf303,
    ApiInvalidDataFormat = 0xf304,
    ApiInvalidPinFormat = 0xf305,
}

impl From<StatusWord> for u16 {
    fn from(val: StatusWord) -> Self {
        val as u16
    }
}

impl TryFrom<u16> for StatusWord {
    type Error = u16;

    fn try_from(num: u16) -> Result<Self, u16> {
        StatusWord::from_u16(num).ok_or(num)
    }
}

impl Apdu {
    pub const MAX_LEN: usize = super::ffi::NFC_MAX_APDU_LEN as usize;

    pub const fn len(&self) -> usize {
        self.data_len as usize
    }

    pub fn as_slice(&self) -> &[u8] {
        &self.data[..self.len()]
    }

    pub const fn as_ptr(&self) -> *const Self {
        self as *const _
    }

    pub const fn as_mut_ptr(&mut self) -> *mut Self {
        self as *mut _
    }

    pub const fn zero() -> Self {
        Self {
            data: [0u8; Apdu::MAX_LEN],
            data_len: 0,
        }
    }

    pub fn write_with<F>(&mut self, mut func: F) -> Result<(), NfcError>
    where
        F: FnMut(&mut [u8]) -> Result<usize, NfcError>,
    {
        let dest = &mut self.data;
        dest.fill(0);
        let size = func(dest)?;
        if size > dest.len() {
            return Err(NfcError::InvalidData);
        }
        self.data_len = size as u16;
        Ok(())
    }
}

pub struct CApdu(Apdu);

impl CApdu {
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
    ) -> Result<Self, NfcError> {
        let mut apdu = [0u8; Apdu::MAX_LEN];
        let mut apdu_len = 0usize;

        let data_len: u16 = data.len().try_into().map_err(|_| NfcError::InvalidData)?;
        let (encoded_data_len, encoded_expected_len) = Self::encode_lengths(data_len, expected);

        let items: [&[u8]; _] = [
            &[cla, ins, p1, p2],
            encoded_data_len.as_slice(),
            data,
            encoded_expected_len.as_slice(),
        ];
        if items.iter().map(|x| x.len()).sum::<usize>() > Apdu::MAX_LEN {
            return Err(NfcError::InvalidData);
        }
        for elem in items {
            let new_len = apdu_len + elem.len();
            apdu[apdu_len..new_len].copy_from_slice(elem);
            apdu_len = new_len;
        }
        Ok(Self(Apdu {
            data: apdu,
            data_len: apdu_len as u16,
        }))
    }

    pub fn compose(inst: Instruction, data: &[u8]) -> Result<Self, NfcError> {
        // TODO return NfcError
        let [cla, ins] = u16::from(inst).to_be_bytes();
        Self::command(cla, ins, 0, 0, data, inst.max_expected_response())
    }

    pub fn with_param(mut self, p1: u8, p2: u8) -> Self {
        self.0.data[2] = p1;
        self.0.data[3] = p2;
        self
    }

    pub fn ins(&self) -> Result<Instruction, u16> {
        let bytes = self.as_slice().first_chunk::<2>().ok_or(0u16)?;
        let code = u16::from_be_bytes(*bytes);
        Instruction::try_from(code).map_err(|_| code)
    }
}

impl AsRef<[u8]> for CApdu {
    fn as_ref(&self) -> &[u8] {
        self.as_slice()
    }
}

impl Deref for CApdu {
    type Target = Apdu;

    fn deref(&self) -> &Apdu {
        &self.0
    }
}

impl DerefMut for CApdu {
    fn deref_mut(&mut self) -> &mut Apdu {
        &mut self.0
    }
}

impl<'b, 'a: 'b> From<&'a CApdu> for &'b Apdu {
    fn from(val: &'a CApdu) -> &'b Apdu {
        &val.0
    }
}

pub struct RApdu(Apdu);

impl RApdu {
    pub const MAX_DATA_LEN: usize = Apdu::MAX_LEN - 2;

    pub const fn zero() -> Self {
        Self(Apdu::zero())
    }

    pub fn sw(&self) -> Result<u16, NfcError> {
        let len = self.len();
        assert!(len <= Apdu::MAX_LEN);
        let (_, sw) = &self.0.data[..len]
            .split_last_chunk::<2>()
            .ok_or(NfcError::InvalidData)?;
        Ok(u16::from_be_bytes(**sw))
    }

    pub fn response(&self) -> Result<(&[u8], u16), NfcError> {
        let len = self.len();
        assert!(len <= Apdu::MAX_LEN);
        let (data, swbytes) = self
            .as_slice()
            .split_last_chunk::<2>()
            .ok_or(NfcError::InvalidData)?;
        let code = u16::from_be_bytes(*swbytes);
        Ok((data, code))
    }

    pub fn response_ok(&self) -> Result<&[u8], NfcError> {
        let len = self.len();
        assert!(len <= Apdu::MAX_LEN);
        let (data, sw) = &self.0.data[..len]
            .split_last_chunk::<2>()
            .ok_or(NfcError::InvalidData)?;
        let code = u16::from_be_bytes(**sw);
        match StatusWord::try_from(code) {
            Ok(StatusWord::Success) => Ok(data),
            _ => Err(NfcError::CommandFailed(code)),
        }
    }

    pub fn response_nodata(&self) -> Result<(), NfcError> {
        let data = self.response_ok()?;
        if !data.is_empty() {
            ulog::error!("Expected no data, got {} bytes.", data.len());
            return Err(NfcError::InvalidData);
        }
        Ok(())
    }
}

impl AsRef<[u8]> for RApdu {
    fn as_ref(&self) -> &[u8] {
        self.as_slice()
    }
}

impl Deref for RApdu {
    type Target = Apdu;

    fn deref(&self) -> &Apdu {
        &self.0
    }
}

impl DerefMut for RApdu {
    fn deref_mut(&mut self) -> &mut Apdu {
        &mut self.0
    }
}
