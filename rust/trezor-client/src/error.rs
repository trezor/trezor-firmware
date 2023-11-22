//! # Error Handling

use crate::{client::InteractionType, protos, transport::error::Error as TransportError};

/// Trezor result type. Aliased to [`std::result::Result`] with the error type
/// set to [`Error`].
pub type Result<T, E = Error> = std::result::Result<T, E>;

/// Trezor error.
#[derive(Debug, thiserror::Error)]
pub enum Error {
    /// Less than one device was plugged in.
    #[error("Trezor device not found")]
    NoDeviceFound,
    /// More than one device was plugged in.
    #[error("multiple Trezor devices found")]
    DeviceNotUnique,
    /// Transport error connecting to device.
    #[error("transport connect: {0}")]
    TransportConnect(#[source] TransportError),
    /// Transport error while beginning a session.
    #[error("transport beginning session: {0}")]
    TransportBeginSession(#[source] TransportError),
    /// Transport error while ending a session.
    #[error("transport ending session: {0}")]
    TransportEndSession(#[source] TransportError),
    /// Transport error while sending a message.
    #[error("transport sending message: {0}")]
    TransportSendMessage(#[source] TransportError),
    /// Transport error while receiving a message.
    #[error("transport receiving message: {0}")]
    TransportReceiveMessage(#[source] TransportError),
    /// Received an unexpected message type from the device.
    #[error("received unexpected message type: {0:?}")]
    UnexpectedMessageType(protos::MessageType), //TODO(stevenroose) type alias
    /// Error reading or writing protobuf messages.
    #[error(transparent)]
    Protobuf(#[from] protobuf::Error),
    /// A failure message was returned by the device.
    #[error("failure received: code={:?} message=\"{}\"", .0.code(), .0.message())]
    FailureResponse(protos::Failure),
    /// An unexpected interaction request was returned by the device.
    #[error("unexpected interaction request: {0:?}")]
    UnexpectedInteractionRequest(InteractionType),
    /// The given Bitcoin network is not supported.
    #[error("given network is not supported")]
    UnsupportedNetwork,
    /// Provided entropy is not 32 bytes.
    #[error("provided entropy is not 32 bytes")]
    InvalidEntropy,
    /// The device erenced a non-existing input or output index.
    #[error("device referenced non-existing input or output index: {0}")]
    TxRequestInvalidIndex(usize),

    /// User provided invalid PSBT.
    #[error("PSBT missing input tx: {0}")]
    InvalidPsbt(String),

    // bitcoin
    /// Error in Base58 decoding
    #[cfg(feature = "bitcoin")]
    #[error(transparent)]
    Base58(#[from] bitcoin::base58::Error),
    /// The device erenced an unknown TXID.
    #[cfg(feature = "bitcoin")]
    #[error("device referenced unknown TXID: {0}")]
    TxRequestUnknownTxid(bitcoin::hashes::sha256d::Hash),
    /// The PSBT is missing the full tx for given input.
    #[cfg(feature = "bitcoin")]
    #[error("PSBT missing input tx: {0}")]
    PsbtMissingInputTx(bitcoin::hashes::sha256d::Hash),
    /// Device produced invalid TxRequest message.
    #[cfg(feature = "bitcoin")]
    #[error("malformed TxRequest: {0:?}")]
    MalformedTxRequest(protos::TxRequest),
    /// Error encoding/decoding a Bitcoin data structure.
    #[cfg(feature = "bitcoin")]
    #[error(transparent)]
    BitcoinEncode(#[from] bitcoin::consensus::encode::Error),
    /// Elliptic curve crypto error.
    #[cfg(feature = "bitcoin")]
    #[error(transparent)]
    Secp256k1(#[from] bitcoin::secp256k1::Error),
    /// Bip32 error.
    #[cfg(feature = "bitcoin")]
    #[error(transparent)]
    Bip32(#[from] bitcoin::bip32::Error),
    /// Address error.
    #[cfg(feature = "bitcoin")]
    #[error(transparent)]
    Address(#[from] bitcoin::address::ParseError),
}
