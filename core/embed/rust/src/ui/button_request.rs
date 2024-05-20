use crate::strutil::TString;
use num_traits::FromPrimitive;

// ButtonRequestType from messages-common.proto
// Eventually this should be generated
#[derive(Clone, Copy, FromPrimitive)]
#[repr(u16)]
pub enum ButtonRequestCode {
    Other = 1,
    FeeOverThreshold = 2,
    ConfirmOutput = 3,
    ResetDevice = 4,
    ConfirmWord = 5,
    WipeDevice = 6,
    ProtectCall = 7,
    SignTx = 8,
    FirmwareCheck = 9,
    Address = 10,
    PublicKey = 11,
    MnemonicWordCount = 12,
    MnemonicInput = 13,
    UnknownDerivationPath = 15,
    RecoveryHomepage = 16,
    Success = 17,
    Warning = 18,
    PassphraseEntry = 19,
    PinEntry = 20,
}

impl ButtonRequestCode {
    pub fn num(&self) -> u16 {
        *self as u16
    }

    pub fn with_type(self, br_type: &'static str) -> ButtonRequest {
        ButtonRequest::new(self, br_type.into())
    }

    pub fn from(i: u16) -> Self {
        unwrap!(Self::from_u16(i))
    }
}

const MAX_TYPE_LEN: usize = 32;

#[derive(Clone)]
pub struct ButtonRequest {
    pub code: ButtonRequestCode,
    pub br_type: TString<'static>,
}

impl ButtonRequest {
    pub fn new(code: ButtonRequestCode, br_type: TString<'static>) -> Self {
        ButtonRequest { code, br_type }
    }

    pub fn from_tstring(code: u16, br_type: TString<'static>) -> Self {
        ButtonRequest::new(ButtonRequestCode::from(code), br_type)
    }
}
