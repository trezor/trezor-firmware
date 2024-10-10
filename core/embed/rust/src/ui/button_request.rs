use crate::strutil::TString;
use num_traits::FromPrimitive;

// ButtonRequestType from messages-common.proto
// Eventually this should be generated
#[derive(Clone, Copy, FromPrimitive, PartialEq, Eq)]
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

    pub fn with_name(self, name: &'static str) -> ButtonRequest {
        ButtonRequest::new(self, name.into())
    }

    pub fn from(i: u16) -> Self {
        unwrap!(Self::from_u16(i))
    }
}

#[derive(Copy, Clone, PartialEq, Eq)]
pub struct ButtonRequest {
    pub code: ButtonRequestCode,
    pub name: TString<'static>,
}

impl ButtonRequest {
    pub fn new(code: ButtonRequestCode, name: TString<'static>) -> Self {
        ButtonRequest { code, name }
    }

    pub fn from_num(code: u16, name: TString<'static>) -> Self {
        ButtonRequest::new(ButtonRequestCode::from(code), name)
    }
}
