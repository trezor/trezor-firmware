	// in messages
	{ 'n', 'i', MessageType_MessageType_Initialize,            Initialize_fields,            (void (*)(void *)) fsm_msgInitialize },
	{ 'n', 'i', MessageType_MessageType_Ping,                  Ping_fields,                  (void (*)(void *)) fsm_msgPing },
	{ 'n', 'i', MessageType_MessageType_ChangePin,             ChangePin_fields,             (void (*)(void *)) fsm_msgChangePin },
	{ 'n', 'i', MessageType_MessageType_WipeDevice,            WipeDevice_fields,            (void (*)(void *)) fsm_msgWipeDevice },
// 	{ 'n', 'i', MessageType_MessageType_FirmwareErase,         FirmwareErase_fields,         (void (*)(void *)) fsm_msgFirmwareErase }, // BOOTLOADER
// 	{ 'n', 'i', MessageType_MessageType_FirmwareUpload,        FirmwareUpload_fields,        (void (*)(void *)) fsm_msgFirmwareUpload }, // BOOTLOADER
	{ 'n', 'i', MessageType_MessageType_GetEntropy,            GetEntropy_fields,            (void (*)(void *)) fsm_msgGetEntropy },
	{ 'n', 'i', MessageType_MessageType_GetPublicKey,          GetPublicKey_fields,          (void (*)(void *)) fsm_msgGetPublicKey },
	{ 'n', 'i', MessageType_MessageType_LoadDevice,            LoadDevice_fields,            (void (*)(void *)) fsm_msgLoadDevice },
	{ 'n', 'i', MessageType_MessageType_ResetDevice,           ResetDevice_fields,           (void (*)(void *)) fsm_msgResetDevice },
	{ 'n', 'i', MessageType_MessageType_SignTx,                SignTx_fields,                (void (*)(void *)) fsm_msgSignTx },
// 	{ 'n', 'i', MessageType_MessageType_SimpleSignTx,          SimpleSignTx_fields,          (void (*)(void *)) fsm_msgSimpleSignTx }, // DEPRECATED
// 	{ 'n', 'i', MessageType_MessageType_PinMatrixAck,          PinMatrixAck_fields,          (void (*)(void *)) fsm_msgPinMatrixAck },
	{ 'n', 'i', MessageType_MessageType_Cancel,                Cancel_fields,                (void (*)(void *)) fsm_msgCancel },
	{ 'n', 'i', MessageType_MessageType_TxAck,                 TxAck_fields,                 (void (*)(void *)) fsm_msgTxAck },
	{ 'n', 'i', MessageType_MessageType_CipherKeyValue,        CipherKeyValue_fields,        (void (*)(void *)) fsm_msgCipherKeyValue },
	{ 'n', 'i', MessageType_MessageType_ClearSession,          ClearSession_fields,          (void (*)(void *)) fsm_msgClearSession },
	{ 'n', 'i', MessageType_MessageType_ApplySettings,         ApplySettings_fields,         (void (*)(void *)) fsm_msgApplySettings },
// 	{ 'n', 'i', MessageType_MessageType_ButtonAck,             ButtonAck_fields,             (void (*)(void *)) fsm_msgButtonAck },
	{ 'n', 'i', MessageType_MessageType_GetAddress,            GetAddress_fields,            (void (*)(void *)) fsm_msgGetAddress },
	{ 'n', 'i', MessageType_MessageType_EntropyAck,            EntropyAck_fields,            (void (*)(void *)) fsm_msgEntropyAck },
	{ 'n', 'i', MessageType_MessageType_SignMessage,           SignMessage_fields,           (void (*)(void *)) fsm_msgSignMessage },
	{ 'n', 'i', MessageType_MessageType_VerifyMessage,         VerifyMessage_fields,         (void (*)(void *)) fsm_msgVerifyMessage },
// 	{ 'n', 'i', MessageType_MessageType_PassphraseAck,         PassphraseAck_fields,         (void (*)(void *)) fsm_msgPassphraseAck },
	{ 'n', 'i', MessageType_MessageType_EstimateTxSize,        EstimateTxSize_fields,        (void (*)(void *)) fsm_msgEstimateTxSize },
	{ 'n', 'i', MessageType_MessageType_RecoveryDevice,        RecoveryDevice_fields,        (void (*)(void *)) fsm_msgRecoveryDevice },
	{ 'n', 'i', MessageType_MessageType_WordAck,               WordAck_fields,               (void (*)(void *)) fsm_msgWordAck },
// 	{ 'n', 'i', MessageType_MessageType_EncryptMessage,        EncryptMessage_fields,        (void (*)(void *)) fsm_msgEncryptMessage }, // DEPRECATED
// 	{ 'n', 'i', MessageType_MessageType_DecryptMessage,        DecryptMessage_fields,        (void (*)(void *)) fsm_msgDecryptMessage }, // DEPRECATED
	{ 'n', 'i', MessageType_MessageType_SignIdentity,          SignIdentity_fields,          (void (*)(void *)) fsm_msgSignIdentity },
	{ 'n', 'i', MessageType_MessageType_GetFeatures,           GetFeatures_fields,           (void (*)(void *)) fsm_msgGetFeatures },
	{ 'n', 'i', MessageType_MessageType_EthereumGetAddress,    EthereumGetAddress_fields,    (void (*)(void *)) fsm_msgEthereumGetAddress },
	{ 'n', 'i', MessageType_MessageType_EthereumSignTx,        EthereumSignTx_fields,        (void (*)(void *)) fsm_msgEthereumSignTx },
	{ 'n', 'i', MessageType_MessageType_EthereumTxAck,         EthereumTxAck_fields,         (void (*)(void *)) fsm_msgEthereumTxAck },
	{ 'n', 'i', MessageType_MessageType_GetECDHSessionKey,     GetECDHSessionKey_fields,     (void (*)(void *)) fsm_msgGetECDHSessionKey },
	{ 'n', 'i', MessageType_MessageType_SetU2FCounter,         SetU2FCounter_fields,         (void (*)(void *)) fsm_msgSetU2FCounter },
	// out messages
	{ 'n', 'o', MessageType_MessageType_Success,               Success_fields,               0 },
	{ 'n', 'o', MessageType_MessageType_Failure,               Failure_fields,               0 },
// 	{ 'n', 'o', MessageType_MessageType_FirmwareRequest,       FirmwareRequest_fields,       0 }, // BOOTLOADER
	{ 'n', 'o', MessageType_MessageType_Entropy,               Entropy_fields,               0 },
	{ 'n', 'o', MessageType_MessageType_PublicKey,             PublicKey_fields,             0 },
	{ 'n', 'o', MessageType_MessageType_Features,              Features_fields,              0 },
	{ 'n', 'o', MessageType_MessageType_PinMatrixRequest,      PinMatrixRequest_fields,      0 },
	{ 'n', 'o', MessageType_MessageType_TxRequest,             TxRequest_fields,             0 },
	{ 'n', 'o', MessageType_MessageType_ButtonRequest,         ButtonRequest_fields,         0 },
	{ 'n', 'o', MessageType_MessageType_Address,               Address_fields,               0 },
	{ 'n', 'o', MessageType_MessageType_EntropyRequest,        EntropyRequest_fields,        0 },
	{ 'n', 'o', MessageType_MessageType_MessageSignature,      MessageSignature_fields,      0 },
	{ 'n', 'o', MessageType_MessageType_PassphraseRequest,     PassphraseRequest_fields,     0 },
	{ 'n', 'o', MessageType_MessageType_TxSize,                TxSize_fields,                0 },
	{ 'n', 'o', MessageType_MessageType_WordRequest,           WordRequest_fields,           0 },
	{ 'n', 'o', MessageType_MessageType_CipheredKeyValue,      CipheredKeyValue_fields,      0 },
// 	{ 'n', 'o', MessageType_MessageType_EncryptedMessage,      EncryptedMessage_fields,      0 }, // DEPRECATED
// 	{ 'n', 'o', MessageType_MessageType_DecryptedMessage,      DecryptedMessage_fields,      0 }, // DEPRECATED
	{ 'n', 'o', MessageType_MessageType_SignedIdentity,        SignedIdentity_fields,        0 },
	{ 'n', 'o', MessageType_MessageType_EthereumAddress,       EthereumAddress_fields,       0 },
	{ 'n', 'o', MessageType_MessageType_EthereumTxRequest,     EthereumTxRequest_fields,     0 },
	{ 'n', 'o', MessageType_MessageType_ECDHSessionKey,        ECDHSessionKey_fields,        0 },
#if DEBUG_LINK
	// debug in messages
// 	{ 'd', 'i', MessageType_MessageType_DebugLinkDecision,     DebugLinkDecision_fields,     (void (*)(void *)) fsm_msgDebugLinkDecision },
	{ 'd', 'i', MessageType_MessageType_DebugLinkGetState,     DebugLinkGetState_fields,     (void (*)(void *)) fsm_msgDebugLinkGetState },
	{ 'd', 'i', MessageType_MessageType_DebugLinkStop,         DebugLinkStop_fields,         (void (*)(void *)) fsm_msgDebugLinkStop },
	{ 'd', 'i', MessageType_MessageType_DebugLinkMemoryRead,   DebugLinkMemoryRead_fields,   (void (*)(void *)) fsm_msgDebugLinkMemoryRead },
	{ 'd', 'i', MessageType_MessageType_DebugLinkMemoryWrite,  DebugLinkMemoryWrite_fields,  (void (*)(void *)) fsm_msgDebugLinkMemoryWrite },
	{ 'd', 'i', MessageType_MessageType_DebugLinkFlashErase,   DebugLinkFlashErase_fields,   (void (*)(void *)) fsm_msgDebugLinkFlashErase },
	// debug out messages
	{ 'd', 'o', MessageType_MessageType_DebugLinkState,        DebugLinkState_fields,        0 },
	{ 'd', 'o', MessageType_MessageType_DebugLinkLog,          DebugLinkLog_fields,          0 },
	{ 'd', 'o', MessageType_MessageType_DebugLinkMemory,       DebugLinkMemory_fields,       0 },
#endif
