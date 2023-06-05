use crate::{
    error::{Error, Result},
    messages::TrezorMessage,
    protos, Trezor,
};
use std::fmt;

// Some types with raw protos that we use in the public interface so they have to be exported.
pub use protos::{
    button_request::ButtonRequestType, pin_matrix_request::PinMatrixRequestType, Features,
};

#[cfg(feature = "bitcoin")]
pub use protos::InputScriptType;

/// The different options for the number of words in a seed phrase.
pub enum WordCount {
    W12 = 12,
    W18 = 18,
    W24 = 24,
}

/// The different types of user interactions the Trezor device can request.
#[derive(PartialEq, Eq, Clone, Debug)]
pub enum InteractionType {
    Button,
    PinMatrix,
    Passphrase,
    PassphraseState,
}

//TODO(stevenroose) should this be FnOnce and put in an FnBox?
/// Function to be passed to the `Trezor.call` method to process the Trezor response message into a
/// general-purpose type.
pub type ResultHandler<'a, T, R> = dyn Fn(&'a mut Trezor, R) -> Result<T>;

/// A button request message sent by the device.
pub struct ButtonRequest<'a, T, R: TrezorMessage> {
    pub message: protos::ButtonRequest,
    pub client: &'a mut Trezor,
    pub result_handler: Box<ResultHandler<'a, T, R>>,
}

impl<'a, T, R: TrezorMessage> fmt::Debug for ButtonRequest<'a, T, R> {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        fmt::Debug::fmt(&self.message, f)
    }
}

impl<'a, T, R: TrezorMessage> ButtonRequest<'a, T, R> {
    /// The type of button request.
    pub fn request_type(&self) -> ButtonRequestType {
        self.message.code()
    }

    /// Ack the request and get the next message from the device.
    pub fn ack(self) -> Result<TrezorResponse<'a, T, R>> {
        let req = protos::ButtonAck::new();
        self.client.call(req, self.result_handler)
    }
}

/// A PIN matrix request message sent by the device.
pub struct PinMatrixRequest<'a, T, R: TrezorMessage> {
    pub message: protos::PinMatrixRequest,
    pub client: &'a mut Trezor,
    pub result_handler: Box<ResultHandler<'a, T, R>>,
}

impl<'a, T, R: TrezorMessage> fmt::Debug for PinMatrixRequest<'a, T, R> {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        fmt::Debug::fmt(&self.message, f)
    }
}

impl<'a, T, R: TrezorMessage> PinMatrixRequest<'a, T, R> {
    /// The type of PIN matrix request.
    pub fn request_type(&self) -> PinMatrixRequestType {
        self.message.type_()
    }

    /// Ack the request with a PIN and get the next message from the device.
    pub fn ack_pin(self, pin: String) -> Result<TrezorResponse<'a, T, R>> {
        let mut req = protos::PinMatrixAck::new();
        req.set_pin(pin);
        self.client.call(req, self.result_handler)
    }
}

/// A passphrase request message sent by the device.
pub struct PassphraseRequest<'a, T, R: TrezorMessage> {
    pub message: protos::PassphraseRequest,
    pub client: &'a mut Trezor,
    pub result_handler: Box<ResultHandler<'a, T, R>>,
}

impl<'a, T, R: TrezorMessage> fmt::Debug for PassphraseRequest<'a, T, R> {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        fmt::Debug::fmt(&self.message, f)
    }
}

impl<'a, T, R: TrezorMessage> PassphraseRequest<'a, T, R> {
    /// Check whether the use is supposed to enter the passphrase on the device or not.
    pub fn on_device(&self) -> bool {
        self.message._on_device()
    }

    /// Ack the request with a passphrase and get the next message from the device.
    pub fn ack_passphrase(self, passphrase: String) -> Result<TrezorResponse<'a, T, R>> {
        let mut req = protos::PassphraseAck::new();
        req.set_passphrase(passphrase);
        self.client.call(req, self.result_handler)
    }

    /// Ack the request without a passphrase to let the user enter it on the device
    /// and get the next message from the device.
    pub fn ack(self, on_device: bool) -> Result<TrezorResponse<'a, T, R>> {
        let mut req = protos::PassphraseAck::new();
        if on_device {
            req.set_on_device(on_device);
        }
        self.client.call(req, self.result_handler)
    }
}

/// A response from a Trezor device.  On every message exchange, instead of the expected/desired
/// response, the Trezor can ask for some user interaction, or can send a failure.
#[derive(Debug)]
pub enum TrezorResponse<'a, T, R: TrezorMessage> {
    Ok(T),
    Failure(protos::Failure),
    ButtonRequest(ButtonRequest<'a, T, R>),
    PinMatrixRequest(PinMatrixRequest<'a, T, R>),
    PassphraseRequest(PassphraseRequest<'a, T, R>),
    //TODO(stevenroose) This should be taken out of this enum and intrinsically attached to the
    // PassphraseRequest variant.  However, it's currently impossible to do this.  It might be
    // possible to do with FnBox (currently nightly) or when Box<FnOnce> becomes possible.
}

impl<'a, T, R: TrezorMessage> fmt::Display for TrezorResponse<'a, T, R> {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            // TODO(stevenroose) should we make T: Debug?
            TrezorResponse::Ok(ref _m) => f.write_str("Ok"),
            TrezorResponse::Failure(ref m) => write!(f, "Failure: {:?}", m),
            TrezorResponse::ButtonRequest(ref r) => write!(f, "ButtonRequest: {:?}", r),
            TrezorResponse::PinMatrixRequest(ref r) => write!(f, "PinMatrixRequest: {:?}", r),
            TrezorResponse::PassphraseRequest(ref r) => write!(f, "PassphraseRequest: {:?}", r),
        }
    }
}

impl<'a, T, R: TrezorMessage> TrezorResponse<'a, T, R> {
    /// Get the actual `Ok` response value or an error if not `Ok`.
    pub fn ok(self) -> Result<T> {
        match self {
            TrezorResponse::Ok(m) => Ok(m),
            TrezorResponse::Failure(m) => Err(Error::FailureResponse(m)),
            TrezorResponse::ButtonRequest(_) => {
                Err(Error::UnexpectedInteractionRequest(InteractionType::Button))
            }
            TrezorResponse::PinMatrixRequest(_) => {
                Err(Error::UnexpectedInteractionRequest(InteractionType::PinMatrix))
            }
            TrezorResponse::PassphraseRequest(_) => {
                Err(Error::UnexpectedInteractionRequest(InteractionType::Passphrase))
            }
        }
    }

    /// Get the button request object or an error if not `ButtonRequest`.
    pub fn button_request(self) -> Result<ButtonRequest<'a, T, R>> {
        match self {
            TrezorResponse::ButtonRequest(r) => Ok(r),
            TrezorResponse::Ok(_) => Err(Error::UnexpectedMessageType(R::MESSAGE_TYPE)),
            TrezorResponse::Failure(m) => Err(Error::FailureResponse(m)),
            TrezorResponse::PinMatrixRequest(_) => {
                Err(Error::UnexpectedInteractionRequest(InteractionType::PinMatrix))
            }
            TrezorResponse::PassphraseRequest(_) => {
                Err(Error::UnexpectedInteractionRequest(InteractionType::Passphrase))
            }
        }
    }

    /// Get the PIN matrix request object or an error if not `PinMatrixRequest`.
    pub fn pin_matrix_request(self) -> Result<PinMatrixRequest<'a, T, R>> {
        match self {
            TrezorResponse::PinMatrixRequest(r) => Ok(r),
            TrezorResponse::Ok(_) => Err(Error::UnexpectedMessageType(R::MESSAGE_TYPE)),
            TrezorResponse::Failure(m) => Err(Error::FailureResponse(m)),
            TrezorResponse::ButtonRequest(_) => {
                Err(Error::UnexpectedInteractionRequest(InteractionType::Button))
            }
            TrezorResponse::PassphraseRequest(_) => {
                Err(Error::UnexpectedInteractionRequest(InteractionType::Passphrase))
            }
        }
    }

    /// Get the passphrase request object or an error if not `PassphraseRequest`.
    pub fn passphrase_request(self) -> Result<PassphraseRequest<'a, T, R>> {
        match self {
            TrezorResponse::PassphraseRequest(r) => Ok(r),
            TrezorResponse::Ok(_) => Err(Error::UnexpectedMessageType(R::MESSAGE_TYPE)),
            TrezorResponse::Failure(m) => Err(Error::FailureResponse(m)),
            TrezorResponse::ButtonRequest(_) => {
                Err(Error::UnexpectedInteractionRequest(InteractionType::Button))
            }
            TrezorResponse::PinMatrixRequest(_) => {
                Err(Error::UnexpectedInteractionRequest(InteractionType::PinMatrix))
            }
        }
    }
}

pub fn handle_interaction<T, R: TrezorMessage>(resp: TrezorResponse<'_, T, R>) -> Result<T> {
    match resp {
        TrezorResponse::Ok(res) => Ok(res),
        TrezorResponse::Failure(_) => resp.ok(), // assering ok() returns the failure error
        TrezorResponse::ButtonRequest(req) => handle_interaction(req.ack()?),
        TrezorResponse::PinMatrixRequest(_) => Err(Error::UnsupportedNetwork),
        TrezorResponse::PassphraseRequest(req) => handle_interaction({
            let on_device = req.on_device();
            req.ack(!on_device)?
        }),
    }
}

/// When resetting the device, it will ask for entropy to aid key generation.
pub struct EntropyRequest<'a> {
    pub client: &'a mut Trezor,
}

impl<'a> EntropyRequest<'a> {
    /// Provide exactly 32 bytes or entropy.
    pub fn ack_entropy(self, entropy: Vec<u8>) -> Result<TrezorResponse<'a, (), protos::Success>> {
        if entropy.len() != 32 {
            return Err(Error::InvalidEntropy)
        }

        let mut req = protos::EntropyAck::new();
        req.set_entropy(entropy);
        self.client.call(req, Box::new(|_, _| Ok(())))
    }
}
