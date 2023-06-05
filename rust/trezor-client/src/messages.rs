//! This module implements the `message_type` getter for all protobuf message types.

use crate::protos::{MessageType::*, *};

/// Extends the protobuf Message trait to also have a static getter for the message
/// type code.
pub trait TrezorMessage: protobuf::Message + std::fmt::Debug {
    const MESSAGE_TYPE: MessageType;

    #[inline]
    #[deprecated(note = "Use `MESSAGE_TYPE` instead")]
    fn message_type() -> MessageType {
        Self::MESSAGE_TYPE
    }
}

/// This macro provides the TrezorMessage trait for a protobuf message.
macro_rules! trezor_message_impl {
	($($struct:ident => $mtype:expr),+ $(,)?) => {$(
		impl TrezorMessage for $struct {
			const MESSAGE_TYPE: MessageType = $mtype;
		}
	)+};
}

trezor_message_impl! {
    Initialize => MessageType_Initialize,
    Ping => MessageType_Ping,
    Success => MessageType_Success,
    Failure => MessageType_Failure,
    ChangePin => MessageType_ChangePin,
    WipeDevice => MessageType_WipeDevice,
    GetEntropy => MessageType_GetEntropy,
    Entropy => MessageType_Entropy,
    LoadDevice => MessageType_LoadDevice,
    ResetDevice => MessageType_ResetDevice,
    SetBusy => MessageType_SetBusy,
    Features => MessageType_Features,
    PinMatrixRequest => MessageType_PinMatrixRequest,
    PinMatrixAck => MessageType_PinMatrixAck,
    Cancel => MessageType_Cancel,
    LockDevice => MessageType_LockDevice,
    ApplySettings => MessageType_ApplySettings,
    ButtonRequest => MessageType_ButtonRequest,
    ButtonAck => MessageType_ButtonAck,
    ApplyFlags => MessageType_ApplyFlags,
    GetNonce => MessageType_GetNonce,
    Nonce => MessageType_Nonce,
    BackupDevice => MessageType_BackupDevice,
    EntropyRequest => MessageType_EntropyRequest,
    EntropyAck => MessageType_EntropyAck,
    PassphraseRequest => MessageType_PassphraseRequest,
    PassphraseAck => MessageType_PassphraseAck,
    RecoveryDevice => MessageType_RecoveryDevice,
    WordRequest => MessageType_WordRequest,
    WordAck => MessageType_WordAck,
    GetFeatures => MessageType_GetFeatures,
    SdProtect => MessageType_SdProtect,
    ChangeWipeCode => MessageType_ChangeWipeCode,
    EndSession => MessageType_EndSession,
    DoPreauthorized => MessageType_DoPreauthorized,
    PreauthorizedRequest => MessageType_PreauthorizedRequest,
    CancelAuthorization => MessageType_CancelAuthorization,
    RebootToBootloader => MessageType_RebootToBootloader,
    GetFirmwareHash => MessageType_GetFirmwareHash,
    FirmwareHash => MessageType_FirmwareHash,
    UnlockPath => MessageType_UnlockPath,
    UnlockedPathRequest => MessageType_UnlockedPathRequest,
    SetU2FCounter => MessageType_SetU2FCounter,
    GetNextU2FCounter => MessageType_GetNextU2FCounter,
    NextU2FCounter => MessageType_NextU2FCounter,
    Deprecated_PassphraseStateRequest => MessageType_Deprecated_PassphraseStateRequest,
    Deprecated_PassphraseStateAck => MessageType_Deprecated_PassphraseStateAck,
    FirmwareErase => MessageType_FirmwareErase,
    FirmwareUpload => MessageType_FirmwareUpload,
    FirmwareRequest => MessageType_FirmwareRequest,
    SelfTest => MessageType_SelfTest,
    CipherKeyValue => MessageType_CipherKeyValue,
    CipheredKeyValue => MessageType_CipheredKeyValue,
    SignIdentity => MessageType_SignIdentity,
    SignedIdentity => MessageType_SignedIdentity,
    GetECDHSessionKey => MessageType_GetECDHSessionKey,
    ECDHSessionKey => MessageType_ECDHSessionKey,
    CosiCommit => MessageType_CosiCommit,
    CosiCommitment => MessageType_CosiCommitment,
    CosiSign => MessageType_CosiSign,
    CosiSignature => MessageType_CosiSignature,
    DebugLinkDecision => MessageType_DebugLinkDecision,
    DebugLinkGetState => MessageType_DebugLinkGetState,
    DebugLinkState => MessageType_DebugLinkState,
    DebugLinkStop => MessageType_DebugLinkStop,
    DebugLinkLog => MessageType_DebugLinkLog,
    DebugLinkMemoryRead => MessageType_DebugLinkMemoryRead,
    DebugLinkMemory => MessageType_DebugLinkMemory,
    DebugLinkMemoryWrite => MessageType_DebugLinkMemoryWrite,
    DebugLinkFlashErase => MessageType_DebugLinkFlashErase,
    DebugLinkLayout => MessageType_DebugLinkLayout,
    DebugLinkReseedRandom => MessageType_DebugLinkReseedRandom,
    DebugLinkRecordScreen => MessageType_DebugLinkRecordScreen,
    DebugLinkEraseSdCard => MessageType_DebugLinkEraseSdCard,
    DebugLinkWatchLayout => MessageType_DebugLinkWatchLayout,
    DebugLinkResetDebugEvents => MessageType_DebugLinkResetDebugEvents,
}

#[cfg(feature = "binance")]
trezor_message_impl! {
    BinanceGetAddress => MessageType_BinanceGetAddress,
    BinanceAddress => MessageType_BinanceAddress,
    BinanceGetPublicKey => MessageType_BinanceGetPublicKey,
    BinancePublicKey => MessageType_BinancePublicKey,
    BinanceSignTx => MessageType_BinanceSignTx,
    BinanceTxRequest => MessageType_BinanceTxRequest,
    BinanceTransferMsg => MessageType_BinanceTransferMsg,
    BinanceOrderMsg => MessageType_BinanceOrderMsg,
    BinanceCancelMsg => MessageType_BinanceCancelMsg,
    BinanceSignedTx => MessageType_BinanceSignedTx,
}

#[cfg(feature = "bitcoin")]
trezor_message_impl! {
    GetPublicKey => MessageType_GetPublicKey,
    PublicKey => MessageType_PublicKey,
    SignTx => MessageType_SignTx,
    TxRequest => MessageType_TxRequest,
    TxAck => MessageType_TxAck,
    GetAddress => MessageType_GetAddress,
    Address => MessageType_Address,
    TxAckPaymentRequest => MessageType_TxAckPaymentRequest,
    SignMessage => MessageType_SignMessage,
    VerifyMessage => MessageType_VerifyMessage,
    MessageSignature => MessageType_MessageSignature,
    GetOwnershipId => MessageType_GetOwnershipId,
    OwnershipId => MessageType_OwnershipId,
    GetOwnershipProof => MessageType_GetOwnershipProof,
    OwnershipProof => MessageType_OwnershipProof,
    AuthorizeCoinJoin => MessageType_AuthorizeCoinJoin,
}

#[cfg(feature = "cardano")]
trezor_message_impl! {
    CardanoGetPublicKey => MessageType_CardanoGetPublicKey,
    CardanoPublicKey => MessageType_CardanoPublicKey,
    CardanoGetAddress => MessageType_CardanoGetAddress,
    CardanoAddress => MessageType_CardanoAddress,
    CardanoTxItemAck => MessageType_CardanoTxItemAck,
    CardanoTxAuxiliaryDataSupplement => MessageType_CardanoTxAuxiliaryDataSupplement,
    CardanoTxWitnessRequest => MessageType_CardanoTxWitnessRequest,
    CardanoTxWitnessResponse => MessageType_CardanoTxWitnessResponse,
    CardanoTxHostAck => MessageType_CardanoTxHostAck,
    CardanoTxBodyHash => MessageType_CardanoTxBodyHash,
    CardanoSignTxFinished => MessageType_CardanoSignTxFinished,
    CardanoSignTxInit => MessageType_CardanoSignTxInit,
    CardanoTxInput => MessageType_CardanoTxInput,
    CardanoTxOutput => MessageType_CardanoTxOutput,
    CardanoAssetGroup => MessageType_CardanoAssetGroup,
    CardanoToken => MessageType_CardanoToken,
    CardanoTxCertificate => MessageType_CardanoTxCertificate,
    CardanoTxWithdrawal => MessageType_CardanoTxWithdrawal,
    CardanoTxAuxiliaryData => MessageType_CardanoTxAuxiliaryData,
    CardanoPoolOwner => MessageType_CardanoPoolOwner,
    CardanoPoolRelayParameters => MessageType_CardanoPoolRelayParameters,
    CardanoGetNativeScriptHash => MessageType_CardanoGetNativeScriptHash,
    CardanoNativeScriptHash => MessageType_CardanoNativeScriptHash,
    CardanoTxMint => MessageType_CardanoTxMint,
    CardanoTxCollateralInput => MessageType_CardanoTxCollateralInput,
    CardanoTxRequiredSigner => MessageType_CardanoTxRequiredSigner,
    CardanoTxInlineDatumChunk => MessageType_CardanoTxInlineDatumChunk,
    CardanoTxReferenceScriptChunk => MessageType_CardanoTxReferenceScriptChunk,
    CardanoTxReferenceInput => MessageType_CardanoTxReferenceInput,
}

#[cfg(feature = "eos")]
trezor_message_impl! {
    EosGetPublicKey => MessageType_EosGetPublicKey,
    EosPublicKey => MessageType_EosPublicKey,
    EosSignTx => MessageType_EosSignTx,
    EosTxActionRequest => MessageType_EosTxActionRequest,
    EosTxActionAck => MessageType_EosTxActionAck,
    EosSignedTx => MessageType_EosSignedTx,
}

#[cfg(feature = "ethereum")]
trezor_message_impl! {
    EthereumGetPublicKey => MessageType_EthereumGetPublicKey,
    EthereumPublicKey => MessageType_EthereumPublicKey,
    EthereumGetAddress => MessageType_EthereumGetAddress,
    EthereumAddress => MessageType_EthereumAddress,
    EthereumSignTx => MessageType_EthereumSignTx,
    EthereumSignTxEIP1559 => MessageType_EthereumSignTxEIP1559,
    EthereumTxRequest => MessageType_EthereumTxRequest,
    EthereumTxAck => MessageType_EthereumTxAck,
    EthereumSignMessage => MessageType_EthereumSignMessage,
    EthereumVerifyMessage => MessageType_EthereumVerifyMessage,
    EthereumMessageSignature => MessageType_EthereumMessageSignature,
    EthereumSignTypedData => MessageType_EthereumSignTypedData,
    EthereumTypedDataStructRequest => MessageType_EthereumTypedDataStructRequest,
    EthereumTypedDataStructAck => MessageType_EthereumTypedDataStructAck,
    EthereumTypedDataValueRequest => MessageType_EthereumTypedDataValueRequest,
    EthereumTypedDataValueAck => MessageType_EthereumTypedDataValueAck,
    EthereumTypedDataSignature => MessageType_EthereumTypedDataSignature,
    EthereumSignTypedHash => MessageType_EthereumSignTypedHash,
}

#[cfg(feature = "monero")]
trezor_message_impl! {
    MoneroTransactionInitRequest => MessageType_MoneroTransactionInitRequest,
    MoneroTransactionInitAck => MessageType_MoneroTransactionInitAck,
    MoneroTransactionSetInputRequest => MessageType_MoneroTransactionSetInputRequest,
    MoneroTransactionSetInputAck => MessageType_MoneroTransactionSetInputAck,
    MoneroTransactionInputViniRequest => MessageType_MoneroTransactionInputViniRequest,
    MoneroTransactionInputViniAck => MessageType_MoneroTransactionInputViniAck,
    MoneroTransactionAllInputsSetRequest => MessageType_MoneroTransactionAllInputsSetRequest,
    MoneroTransactionAllInputsSetAck => MessageType_MoneroTransactionAllInputsSetAck,
    MoneroTransactionSetOutputRequest => MessageType_MoneroTransactionSetOutputRequest,
    MoneroTransactionSetOutputAck => MessageType_MoneroTransactionSetOutputAck,
    MoneroTransactionAllOutSetRequest => MessageType_MoneroTransactionAllOutSetRequest,
    MoneroTransactionAllOutSetAck => MessageType_MoneroTransactionAllOutSetAck,
    MoneroTransactionSignInputRequest => MessageType_MoneroTransactionSignInputRequest,
    MoneroTransactionSignInputAck => MessageType_MoneroTransactionSignInputAck,
    MoneroTransactionFinalRequest => MessageType_MoneroTransactionFinalRequest,
    MoneroTransactionFinalAck => MessageType_MoneroTransactionFinalAck,
    MoneroKeyImageExportInitRequest => MessageType_MoneroKeyImageExportInitRequest,
    MoneroKeyImageExportInitAck => MessageType_MoneroKeyImageExportInitAck,
    MoneroKeyImageSyncStepRequest => MessageType_MoneroKeyImageSyncStepRequest,
    MoneroKeyImageSyncStepAck => MessageType_MoneroKeyImageSyncStepAck,
    MoneroKeyImageSyncFinalRequest => MessageType_MoneroKeyImageSyncFinalRequest,
    MoneroKeyImageSyncFinalAck => MessageType_MoneroKeyImageSyncFinalAck,
    MoneroGetAddress => MessageType_MoneroGetAddress,
    MoneroAddress => MessageType_MoneroAddress,
    MoneroGetWatchKey => MessageType_MoneroGetWatchKey,
    MoneroWatchKey => MessageType_MoneroWatchKey,
    DebugMoneroDiagRequest => MessageType_DebugMoneroDiagRequest,
    DebugMoneroDiagAck => MessageType_DebugMoneroDiagAck,
    MoneroGetTxKeyRequest => MessageType_MoneroGetTxKeyRequest,
    MoneroGetTxKeyAck => MessageType_MoneroGetTxKeyAck,
    MoneroLiveRefreshStartRequest => MessageType_MoneroLiveRefreshStartRequest,
    MoneroLiveRefreshStartAck => MessageType_MoneroLiveRefreshStartAck,
    MoneroLiveRefreshStepRequest => MessageType_MoneroLiveRefreshStepRequest,
    MoneroLiveRefreshStepAck => MessageType_MoneroLiveRefreshStepAck,
    MoneroLiveRefreshFinalRequest => MessageType_MoneroLiveRefreshFinalRequest,
    MoneroLiveRefreshFinalAck => MessageType_MoneroLiveRefreshFinalAck,
}

#[cfg(feature = "nem")]
trezor_message_impl! {
    NEMGetAddress => MessageType_NEMGetAddress,
    NEMAddress => MessageType_NEMAddress,
    NEMSignTx => MessageType_NEMSignTx,
    NEMSignedTx => MessageType_NEMSignedTx,
    NEMDecryptMessage => MessageType_NEMDecryptMessage,
    NEMDecryptedMessage => MessageType_NEMDecryptedMessage,
}

#[cfg(feature = "ripple")]
trezor_message_impl! {
    RippleGetAddress => MessageType_RippleGetAddress,
    RippleAddress => MessageType_RippleAddress,
    RippleSignTx => MessageType_RippleSignTx,
    RippleSignedTx => MessageType_RippleSignedTx,
}

#[cfg(feature = "stellar")]
trezor_message_impl! {
    StellarSignTx => MessageType_StellarSignTx,
    StellarTxOpRequest => MessageType_StellarTxOpRequest,
    StellarGetAddress => MessageType_StellarGetAddress,
    StellarAddress => MessageType_StellarAddress,
    StellarCreateAccountOp => MessageType_StellarCreateAccountOp,
    StellarPaymentOp => MessageType_StellarPaymentOp,
    StellarPathPaymentStrictReceiveOp => MessageType_StellarPathPaymentStrictReceiveOp,
    StellarManageSellOfferOp => MessageType_StellarManageSellOfferOp,
    StellarCreatePassiveSellOfferOp => MessageType_StellarCreatePassiveSellOfferOp,
    StellarSetOptionsOp => MessageType_StellarSetOptionsOp,
    StellarChangeTrustOp => MessageType_StellarChangeTrustOp,
    StellarAllowTrustOp => MessageType_StellarAllowTrustOp,
    StellarAccountMergeOp => MessageType_StellarAccountMergeOp,
    StellarManageDataOp => MessageType_StellarManageDataOp,
    StellarBumpSequenceOp => MessageType_StellarBumpSequenceOp,
    StellarManageBuyOfferOp => MessageType_StellarManageBuyOfferOp,
    StellarPathPaymentStrictSendOp => MessageType_StellarPathPaymentStrictSendOp,
    StellarSignedTx => MessageType_StellarSignedTx,
}

#[cfg(feature = "tezos")]
trezor_message_impl! {
    TezosGetAddress => MessageType_TezosGetAddress,
    TezosAddress => MessageType_TezosAddress,
    TezosSignTx => MessageType_TezosSignTx,
    TezosSignedTx => MessageType_TezosSignedTx,
    TezosGetPublicKey => MessageType_TezosGetPublicKey,
    TezosPublicKey => MessageType_TezosPublicKey,
}

#[cfg(feature = "webauthn")]
trezor_message_impl! {
    WebAuthnListResidentCredentials => MessageType_WebAuthnListResidentCredentials,
    WebAuthnCredentials => MessageType_WebAuthnCredentials,
    WebAuthnAddResidentCredential => MessageType_WebAuthnAddResidentCredential,
    WebAuthnRemoveResidentCredential => MessageType_WebAuthnRemoveResidentCredential,
}
