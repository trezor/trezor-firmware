//! Implements subset of ISO/IEC 7816-4 Application Protocol Data Unit format.

use core::ops::{Deref, DerefMut};

use heapless::Vec;
use num_traits::FromPrimitive;
use sys::ulog;
use zeroize::{zeroize_flat_type, Zeroize};

use super::{NfcError, TAG_SIZE};

/// Variable-length buffer used by the NFC driver.
pub(super) type Apdu = super::ffi::nfc_apdu_message_t;

impl Apdu {
    pub const MAX_LEN: usize = super::ffi::NFC_MAX_APDU_LEN as usize;

    pub const fn len(&self) -> usize {
        self.data_len as usize
    }

    pub const fn is_empty(&self) -> bool {
        self.len() == 0
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

    pub fn write_with<F>(&mut self, mut func: F) -> Result<(), NfcError>
    where
        F: FnMut(&mut [u8]) -> Result<usize, NfcError>,
    {
        self.zeroize();
        let size = func(&mut self.data)?;
        if size > self.data.len() {
            return Err(NfcError::UnexpectedInput);
        }
        self.data_len = size as u16;
        Ok(())
    }
}

impl Default for Apdu {
    fn default() -> Self {
        Self {
            data: [0u8; Apdu::MAX_LEN],
            data_len: 0,
        }
    }
}

impl Zeroize for Apdu {
    fn zeroize(&mut self) {
        // SAFETY:
        // - plain C type
        // - valid when all zeroes
        unsafe { zeroize_flat_type(self.as_mut_ptr()) };
    }
}

/// Command-APDU interface for building [`Apdu`]s sent to the tag.
/// Consists of:
/// * header: class, instruction, param1, param2 (1B each)
/// * data length (0-3B)
/// * command data (variable)
/// * maximum response length (0-3B)
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

/// Response-APDU interface for parsing [`Apdu`]s received from the tag.
/// Consists of:
/// * response data (variable)
/// * status code (2B)
#[derive(Default)]
pub struct RApdu(Apdu);

impl RApdu {
    pub const MAX_DATA_LEN: usize = Apdu::MAX_LEN - 2;

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
        let (data, code) = self.response()?;
        match StatusWord::try_from(code) {
            Ok(StatusWord::Success) => Ok(data),
            _ => Err(NfcError::CommandFailed(code)),
        }
    }

    pub fn response_ok_nodata(&self) -> Result<(), NfcError> {
        let data = self.response_ok()?;
        if !data.is_empty() {
            ulog::error!("Expected no data, got {} B.", data.len());
            return Err(NfcError::InvalidData);
        }
        Ok(())
    }

    pub fn sw(&self) -> Result<u16, NfcError> {
        let (_, code) = self.response()?;
        Ok(code)
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

/// Values corresponding to CLA INS that are used by firmware.
#[repr(u16)]
#[derive(Copy, Clone, FromPrimitive, PartialEq, ufmt::derive::uDebug)]
#[cfg_attr(test, derive(Debug))]
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
        let tag_size = TAG_SIZE as u16;
        let small = 255 - tag_size;
        let large_no_tag = RApdu::MAX_DATA_LEN as u16;
        let large = large_no_tag - tag_size;
        match self {
            Instruction::Select => props(false, false, 0),
            Instruction::GetOsVersion => props(false, false, small),
            Instruction::GetUid => props(false, false, small),
            Instruction::MeasureCpuFrequency => props(false, false, small),
            Instruction::HardenMemory => props(false, false, 0),
            Instruction::IntegrityCheck => props(false, false, small),

            Instruction::Handshake => props(false, false, large_no_tag),
            Instruction::PinUnlocked => props(false, false, 0),
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

    pub fn can_log_command(&self) -> bool {
        const DENY: &[Instruction] = &[
            Instruction::Authenticate,
            Instruction::SetPin,
            Instruction::WriteSeed,
        ];
        !DENY.contains(self)
    }

    pub fn can_log_response(&self) -> bool {
        const DENY: &[Instruction] = &[Instruction::ReadSeed];
        !DENY.contains(self)
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

/// Known R-APDU status codes.
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

    /// A system command could not read or evaluate a hardware resource.
    SystemInternal = 0xf001,
    /// The secure storage could not be initialised. Checked before every
    /// command; the command is not executed.
    SystemStorageInit = 0xf002,
    /// Unknown CLA/INS combination, or, in a secure session, an APDU that fails
    /// to decrypt.
    CommandInvalid = 0xf101,
    /// The APDU cannot be parsed: shorter than 4 bytes, or Lc/Le inconsistent
    /// with its length.
    CommandInvalidFormat = 0xf102,
    /// P1/P2 combination not supported by the command.
    CommandInvalidParamters = 0xf103,
    /// Unexpected failure of the card OS while executing the command.
    CommandInternalError = 0xf104,
    /// The command needs a completed HANDSHAKE in this activation.
    ApiHandshakeRequired = 0xf301,
    /// Wrong PIN, session not authenticated, or (PinUnlocked) a PIN is set.
    ApiPermissionDenied = 0xf302,
    /// HANDSHAKE without a valid PSK exchange in this activation.
    ApiPskNotAvailable = 0xf303,
    /// The command data has the wrong length.
    ApiInvalidDataFormat = 0xf304,
    /// The PIN field violates the PIN encoding.
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

#[cfg(test)]
mod tests {
    use super::*;

    // not a known CLA INS
    const HEADER: [u8; 4] = [0x12, 0x34, 0x56, 0x78];
    const DATA: [u8; Apdu::MAX_LEN] = [0xab; Apdu::MAX_LEN];

    fn command(data_len: usize, expected: u16) -> Result<CApdu, NfcError> {
        let [cla, ins, p1, p2] = HEADER;
        CApdu::command(cla, ins, p1, p2, &DATA[..data_len], expected)
    }

    fn rapdu(bytes: &[u8]) -> RApdu {
        let mut apdu = RApdu::default();
        apdu.write_with(|dest| {
            dest[..bytes.len()].copy_from_slice(bytes);
            Ok(bytes.len())
        })
        .unwrap();
        apdu
    }

    #[test]
    fn test_command_lengths() {
        // ISO 7816-4 cases around the short/extended boundaries:
        // (data length, Le, encoded Lc, encoded Le)
        let cases: &[(usize, u16, &[u8], &[u8])] = &[
            // case 1
            (0, 0, &[], &[]),
            // case 2, short Le of 256 is encoded as 0
            (0, 1, &[], &[0x01]),
            (0, 256, &[], &[0x00]),
            (0, 257, &[], &[0x00, 0x01, 0x01]),
            (0, 0xffff, &[], &[0x00, 0xff, 0xff]),
            // case 3
            (1, 0, &[0x01], &[]),
            (255, 0, &[0xff], &[]),
            (256, 0, &[0x00, 0x01, 0x00], &[]),
            // case 4, Lc and Le are either both short or both extended, and
            // the extended Le has no leading 0 after an extended Lc
            (255, 256, &[0xff], &[0x00]),
            (255, 257, &[0x00, 0x00, 0xff], &[0x01, 0x01]),
            (256, 1, &[0x00, 0x01, 0x00], &[0x00, 0x01]),
            (256, 256, &[0x00, 0x01, 0x00], &[0x01, 0x00]),
        ];
        for &(data_len, expected, lc, le) in cases {
            let apdu = command(data_len, expected).unwrap();
            assert_eq!(
                apdu.as_slice(),
                [&HEADER, lc, &DATA[..data_len], le].concat(),
                "data_len={data_len} Le={expected}"
            );
        }
    }

    #[test]
    fn test_command_max_len() {
        // header and extended Lc
        let max_data_len = Apdu::MAX_LEN - 4 - 3;
        assert_eq!(command(max_data_len, 0).unwrap().len(), Apdu::MAX_LEN);
        assert!(matches!(
            command(max_data_len + 1, 0),
            Err(NfcError::InvalidData)
        ));
        // extended Le after extended Lc
        assert_eq!(command(max_data_len - 2, 1).unwrap().len(), Apdu::MAX_LEN);
        assert!(matches!(
            command(max_data_len - 1, 1),
            Err(NfcError::InvalidData)
        ));
    }

    #[test]
    fn test_compose() {
        // WRITE SEED as in the card API, followed by Le
        let apdu = CApdu::compose(Instruction::WriteSeed, &DATA[..256]).unwrap();
        let (header, rest) = apdu.as_slice().split_at(7);
        assert_eq!(header, [0x80, 0x0d, 0x00, 0x00, 0x00, 0x01, 0x00]);
        assert_eq!(rest[..256], DATA[..256]);
        assert_eq!(
            rest[256..],
            Instruction::WriteSeed.max_expected_response().to_be_bytes()
        );
        assert!(matches!(apdu.ins(), Ok(Instruction::WriteSeed)));

        let aid = [0xa0, 0x00, 0x00, 0x09, 0x59, 0x00, 0x01];
        let apdu = CApdu::compose(Instruction::Select, &aid)
            .unwrap()
            .with_param(0x04, 0x00);
        let header: &[u8] = &[0x00, 0xa4, 0x04, 0x00, 0x07];
        assert_eq!(apdu.as_slice(), [header, &aid].concat());

        assert_eq!(command(0, 0).unwrap().ins().err(), Some(0x1234));
    }

    #[test]
    fn test_response() {
        // too short for the status word
        assert!(matches!(rapdu(&[]).response(), Err(NfcError::InvalidData)));
        assert!(matches!(
            rapdu(&[0x90]).response(),
            Err(NfcError::InvalidData)
        ));

        let apdu = rapdu(&[0x90, 0x00]);
        assert_eq!(apdu.response().unwrap(), (&[][..], 0x9000));

        let mut full = DATA;
        full[RApdu::MAX_DATA_LEN..].copy_from_slice(&[0x90, 0x00]);
        let apdu = rapdu(&full);
        let (data, sw) = apdu.response().unwrap();
        assert_eq!(data, &DATA[..RApdu::MAX_DATA_LEN]);
        assert_eq!(sw, 0x9000);
    }

    #[test]
    fn test_response_ok() {
        let apdu = rapdu(&[0x01, 0x02, 0x90, 0x00]);
        assert_eq!(apdu.response_ok().unwrap(), [0x01, 0x02]);
        assert!(matches!(
            apdu.response_ok_nodata(),
            Err(NfcError::InvalidData)
        ));
        rapdu(&[0x90, 0x00]).response_ok_nodata().unwrap();

        // no data with an error status, either known or not
        for sw in [StatusWord::CommandInternalError.into(), 0x6f00u16] {
            let [sw1, sw2] = sw.to_be_bytes();
            let apdu = rapdu(&[0x01, sw1, sw2]);
            assert!(matches!(
                apdu.response_ok(),
                Err(NfcError::CommandFailed(code)) if code == sw
            ));
            assert!(matches!(
                apdu.response_ok_nodata(),
                Err(NfcError::CommandFailed(code)) if code == sw
            ));
        }
    }

    #[test]
    fn test_write_with() {
        fn fill(dest: &mut [u8]) -> Result<usize, NfcError> {
            dest.fill(0xab);
            Ok(dest.len())
        }

        let mut apdu = Apdu::default();
        apdu.write_with(fill).unwrap();
        assert_eq!(apdu.as_slice(), DATA);

        // nothing of the previous content is left
        apdu.write_with(|_| Ok(0)).unwrap();
        assert!(apdu.is_empty());
        assert_eq!(apdu.data, [0; Apdu::MAX_LEN]);

        // a failed write leaves the buffer empty
        apdu.write_with(fill).unwrap();
        assert!(matches!(
            apdu.write_with(|dest| Ok(dest.len() + 1)),
            Err(NfcError::UnexpectedInput)
        ));
        assert!(apdu.is_empty());

        apdu.write_with(fill).unwrap();
        assert!(matches!(
            apdu.write_with(|_| Err(NfcError::CryptoError)),
            Err(NfcError::CryptoError)
        ));
        assert!(apdu.is_empty());
    }
}
