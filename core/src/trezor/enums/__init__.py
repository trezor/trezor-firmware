if False:
    from typing import TYPE_CHECKING
else:
    TYPE_CHECKING = False


if TYPE_CHECKING:
    from enum import IntEnum

    class MessageType(IntEnum):
        Initialize = 0
        Ping = 1
        Success = 2
        Failure = 3
        ChangePin = 4
        WipeDevice = 5
        GetEntropy = 9
        Entropy = 10
        LoadDevice = 13
        ResetDevice = 14
        Features = 17
        PinMatrixRequest = 18
        PinMatrixAck = 19
        Cancel = 20
        LockDevice = 24
        ApplySettings = 25
        ButtonRequest = 26
        ButtonAck = 27
        ApplyFlags = 28
        BackupDevice = 34
        EntropyRequest = 35
        EntropyAck = 36
        PassphraseRequest = 41
        PassphraseAck = 42
        RecoveryDevice = 45
        WordRequest = 46
        WordAck = 47
        GetFeatures = 55
        SdProtect = 79
        ChangeWipeCode = 82
        EndSession = 83
        DoPreauthorized = 84
        PreauthorizedRequest = 85
        CancelAuthorization = 86
        RebootToBootloader = 87
        SetU2FCounter = 63
        GetNextU2FCounter = 80
        NextU2FCounter = 81
        Deprecated_PassphraseStateRequest = 77
        Deprecated_PassphraseStateAck = 78
        FirmwareErase = 6
        FirmwareUpload = 7
        FirmwareRequest = 8
        SelfTest = 32
        GetPublicKey = 11
        PublicKey = 12
        SignTx = 15
        TxRequest = 21
        TxAck = 22
        GetAddress = 29
        Address = 30
        SignMessage = 38
        VerifyMessage = 39
        MessageSignature = 40
        GetOwnershipId = 43
        OwnershipId = 44
        GetOwnershipProof = 49
        OwnershipProof = 50
        AuthorizeCoinJoin = 51
        CipherKeyValue = 23
        CipheredKeyValue = 48
        SignIdentity = 53
        SignedIdentity = 54
        GetECDHSessionKey = 61
        ECDHSessionKey = 62
        CosiCommit = 71
        CosiCommitment = 72
        CosiSign = 73
        CosiSignature = 74
        DebugLinkDecision = 100
        DebugLinkGetState = 101
        DebugLinkState = 102
        DebugLinkStop = 103
        DebugLinkLog = 104
        DebugLinkMemoryRead = 110
        DebugLinkMemory = 111
        DebugLinkMemoryWrite = 112
        DebugLinkFlashErase = 113
        DebugLinkLayout = 9001
        DebugLinkReseedRandom = 9002
        DebugLinkRecordScreen = 9003
        DebugLinkEraseSdCard = 9005
        DebugLinkWatchLayout = 9006
        EthereumGetPublicKey = 450
        EthereumPublicKey = 451
        EthereumGetAddress = 56
        EthereumAddress = 57
        EthereumSignTx = 58
        EthereumTxRequest = 59
        EthereumTxAck = 60
        EthereumSignMessage = 64
        EthereumVerifyMessage = 65
        EthereumMessageSignature = 66
        NEMGetAddress = 67
        NEMAddress = 68
        NEMSignTx = 69
        NEMSignedTx = 70
        NEMDecryptMessage = 75
        NEMDecryptedMessage = 76
        LiskGetAddress = 114
        LiskAddress = 115
        LiskSignTx = 116
        LiskSignedTx = 117
        LiskSignMessage = 118
        LiskMessageSignature = 119
        LiskVerifyMessage = 120
        LiskGetPublicKey = 121
        LiskPublicKey = 122
        TezosGetAddress = 150
        TezosAddress = 151
        TezosSignTx = 152
        TezosSignedTx = 153
        TezosGetPublicKey = 154
        TezosPublicKey = 155
        StellarSignTx = 202
        StellarTxOpRequest = 203
        StellarGetAddress = 207
        StellarAddress = 208
        StellarCreateAccountOp = 210
        StellarPaymentOp = 211
        StellarPathPaymentOp = 212
        StellarManageOfferOp = 213
        StellarCreatePassiveOfferOp = 214
        StellarSetOptionsOp = 215
        StellarChangeTrustOp = 216
        StellarAllowTrustOp = 217
        StellarAccountMergeOp = 218
        StellarManageDataOp = 220
        StellarBumpSequenceOp = 221
        StellarSignedTx = 230
        CardanoSignTx = 303
        CardanoGetPublicKey = 305
        CardanoPublicKey = 306
        CardanoGetAddress = 307
        CardanoAddress = 308
        CardanoSignedTx = 310
        CardanoSignedTxChunk = 311
        CardanoSignedTxChunkAck = 312
        RippleGetAddress = 400
        RippleAddress = 401
        RippleSignTx = 402
        RippleSignedTx = 403
        MoneroTransactionInitRequest = 501
        MoneroTransactionInitAck = 502
        MoneroTransactionSetInputRequest = 503
        MoneroTransactionSetInputAck = 504
        MoneroTransactionInputsPermutationRequest = 505
        MoneroTransactionInputsPermutationAck = 506
        MoneroTransactionInputViniRequest = 507
        MoneroTransactionInputViniAck = 508
        MoneroTransactionAllInputsSetRequest = 509
        MoneroTransactionAllInputsSetAck = 510
        MoneroTransactionSetOutputRequest = 511
        MoneroTransactionSetOutputAck = 512
        MoneroTransactionAllOutSetRequest = 513
        MoneroTransactionAllOutSetAck = 514
        MoneroTransactionSignInputRequest = 515
        MoneroTransactionSignInputAck = 516
        MoneroTransactionFinalRequest = 517
        MoneroTransactionFinalAck = 518
        MoneroKeyImageExportInitRequest = 530
        MoneroKeyImageExportInitAck = 531
        MoneroKeyImageSyncStepRequest = 532
        MoneroKeyImageSyncStepAck = 533
        MoneroKeyImageSyncFinalRequest = 534
        MoneroKeyImageSyncFinalAck = 535
        MoneroGetAddress = 540
        MoneroAddress = 541
        MoneroGetWatchKey = 542
        MoneroWatchKey = 543
        DebugMoneroDiagRequest = 546
        DebugMoneroDiagAck = 547
        MoneroGetTxKeyRequest = 550
        MoneroGetTxKeyAck = 551
        MoneroLiveRefreshStartRequest = 552
        MoneroLiveRefreshStartAck = 553
        MoneroLiveRefreshStepRequest = 554
        MoneroLiveRefreshStepAck = 555
        MoneroLiveRefreshFinalRequest = 556
        MoneroLiveRefreshFinalAck = 557
        EosGetPublicKey = 600
        EosPublicKey = 601
        EosSignTx = 602
        EosTxActionRequest = 603
        EosTxActionAck = 604
        EosSignedTx = 605
        BinanceGetAddress = 700
        BinanceAddress = 701
        BinanceGetPublicKey = 702
        BinancePublicKey = 703
        BinanceSignTx = 704
        BinanceTxRequest = 705
        BinanceTransferMsg = 706
        BinanceOrderMsg = 707
        BinanceCancelMsg = 708
        BinanceSignedTx = 709
        WebAuthnListResidentCredentials = 800
        WebAuthnCredentials = 801
        WebAuthnAddResidentCredential = 802
        WebAuthnRemoveResidentCredential = 803

    class BinanceOrderType(IntEnum):
        OT_UNKNOWN = 0
        MARKET = 1
        LIMIT = 2
        OT_RESERVED = 3

    class BinanceOrderSide(IntEnum):
        SIDE_UNKNOWN = 0
        BUY = 1
        SELL = 2

    class BinanceTimeInForce(IntEnum):
        TIF_UNKNOWN = 0
        GTE = 1
        TIF_RESERVED = 2
        IOC = 3

    class FailureType(IntEnum):
        UnexpectedMessage = 1
        ButtonExpected = 2
        DataError = 3
        ActionCancelled = 4
        PinExpected = 5
        PinCancelled = 6
        PinInvalid = 7
        InvalidSignature = 8
        ProcessError = 9
        NotEnoughFunds = 10
        NotInitialized = 11
        PinMismatch = 12
        WipeCodeMismatch = 13
        InvalidSession = 14
        FirmwareError = 99

    class ButtonRequestType(IntEnum):
        Other = 1
        FeeOverThreshold = 2
        ConfirmOutput = 3
        ResetDevice = 4
        ConfirmWord = 5
        WipeDevice = 6
        ProtectCall = 7
        SignTx = 8
        FirmwareCheck = 9
        Address = 10
        PublicKey = 11
        MnemonicWordCount = 12
        MnemonicInput = 13
        _Deprecated_ButtonRequest_PassphraseType = 14
        UnknownDerivationPath = 15
        RecoveryHomepage = 16
        Success = 17
        Warning = 18
        PassphraseEntry = 19
        PinEntry = 20

    class PinMatrixRequestType(IntEnum):
        Current = 1
        NewFirst = 2
        NewSecond = 3
        WipeCodeFirst = 4
        WipeCodeSecond = 5

    class InputScriptType(IntEnum):
        SPENDADDRESS = 0
        SPENDMULTISIG = 1
        EXTERNAL = 2
        SPENDWITNESS = 3
        SPENDP2SHWITNESS = 4

    class OutputScriptType(IntEnum):
        PAYTOADDRESS = 0
        PAYTOSCRIPTHASH = 1
        PAYTOMULTISIG = 2
        PAYTOOPRETURN = 3
        PAYTOWITNESS = 4
        PAYTOP2SHWITNESS = 5

    class DecredStakingSpendType(IntEnum):
        SSGen = 0
        SSRTX = 1

    class AmountUnit(IntEnum):
        BITCOIN = 0
        MILLIBITCOIN = 1
        MICROBITCOIN = 2
        SATOSHI = 3

    class RequestType(IntEnum):
        TXINPUT = 0
        TXOUTPUT = 1
        TXMETA = 2
        TXFINISHED = 3
        TXEXTRADATA = 4
        TXORIGINPUT = 5
        TXORIGOUTPUT = 6

    class CardanoAddressType(IntEnum):
        BASE = 0
        BASE_SCRIPT_KEY = 1
        BASE_KEY_SCRIPT = 2
        BASE_SCRIPT_SCRIPT = 3
        POINTER = 4
        POINTER_SCRIPT = 5
        ENTERPRISE = 6
        ENTERPRISE_SCRIPT = 7
        BYRON = 8
        REWARD = 14
        REWARD_SCRIPT = 15

    class CardanoCertificateType(IntEnum):
        STAKE_REGISTRATION = 0
        STAKE_DEREGISTRATION = 1
        STAKE_DELEGATION = 2
        STAKE_POOL_REGISTRATION = 3

    class CardanoPoolRelayType(IntEnum):
        SINGLE_HOST_IP = 0
        SINGLE_HOST_NAME = 1
        MULTIPLE_HOST_NAME = 2

    class BackupType(IntEnum):
        Bip39 = 0
        Slip39_Basic = 1
        Slip39_Advanced = 2

    class SafetyCheckLevel(IntEnum):
        Strict = 0
        PromptAlways = 1
        PromptTemporarily = 2

    class Capability(IntEnum):
        Bitcoin = 1
        Bitcoin_like = 2
        Binance = 3
        Cardano = 4
        Crypto = 5
        EOS = 6
        Ethereum = 7
        Lisk = 8
        Monero = 9
        NEM = 10
        Ripple = 11
        Stellar = 12
        Tezos = 13
        U2F = 14
        Shamir = 15
        ShamirGroups = 16
        PassphraseEntry = 17

    class SdProtectOperationType(IntEnum):
        DISABLE = 0
        ENABLE = 1
        REFRESH = 2

    class RecoveryDeviceType(IntEnum):
        ScrambledWords = 0
        Matrix = 1

    class WordRequestType(IntEnum):
        Plain = 0
        Matrix9 = 1
        Matrix6 = 2

    class DebugSwipeDirection(IntEnum):
        UP = 0
        DOWN = 1
        LEFT = 2
        RIGHT = 3

    class LiskTransactionType(IntEnum):
        Transfer = 0
        RegisterSecondPassphrase = 1
        RegisterDelegate = 2
        CastVotes = 3
        RegisterMultisignatureAccount = 4
        CreateDapp = 5
        TransferIntoDapp = 6
        TransferOutOfDapp = 7

    class NEMMosaicLevy(IntEnum):
        MosaicLevy_Absolute = 1
        MosaicLevy_Percentile = 2

    class NEMSupplyChangeType(IntEnum):
        SupplyChange_Increase = 1
        SupplyChange_Decrease = 2

    class NEMModificationType(IntEnum):
        CosignatoryModification_Add = 1
        CosignatoryModification_Delete = 2

    class NEMImportanceTransferMode(IntEnum):
        ImportanceTransfer_Activate = 1
        ImportanceTransfer_Deactivate = 2

    class TezosContractType(IntEnum):
        Implicit = 0
        Originated = 1

    class TezosBallotType(IntEnum):
        Yay = 0
        Nay = 1
        Pass = 2
