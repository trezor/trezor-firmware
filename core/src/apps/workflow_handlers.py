from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.wire import Handler, Msg


workflow_handlers: dict[int, Handler] = {}


def register(wire_type: int, handler: Handler[Msg]) -> None:
    """Register `handler` to get scheduled after `wire_type` message is received."""
    workflow_handlers[wire_type] = handler


def _find_message_handler_module(msg_type: int) -> str:
    """Statically find the appropriate workflow handler.

    For now, new messages must be registered by hand in the if-elif manner below.
    The reason for this is memory fragmentation optimization:
    - using a dict would mean that the whole thing stays in RAM, whereas an if-elif
      sequence is run from flash
    - collecting everything as strings instead of importing directly means that we don't
      need to load any of the modules into memory until we actually need them
    """
    from trezor import utils
    from trezor.enums import MessageType

    # debug
    if __debug__ and msg_type == MessageType.LoadDevice:
        return "apps.debug.load_device"

    # benchmark
    if __debug__ and msg_type == MessageType.BenchmarkListNames:
        return "apps.benchmark.list_names"
    if __debug__ and msg_type == MessageType.BenchmarkRun:
        return "apps.benchmark.run"

    # management
    if msg_type == MessageType.ResetDevice:
        return "apps.management.reset_device"
    if msg_type == MessageType.BackupDevice:
        return "apps.management.backup_device"
    if msg_type == MessageType.WipeDevice:
        return "apps.management.wipe_device"
    if msg_type == MessageType.RecoveryDevice:
        return "apps.management.recovery_device"
    if msg_type == MessageType.ApplySettings:
        return "apps.management.apply_settings"
    if msg_type == MessageType.ChangeLanguage:
        return "apps.management.change_language"
    if msg_type == MessageType.ApplyFlags:
        return "apps.management.apply_flags"
    if msg_type == MessageType.ChangePin:
        return "apps.management.change_pin"
    if msg_type == MessageType.ChangeWipeCode:
        return "apps.management.change_wipe_code"
    if msg_type == MessageType.GetNonce:
        return "apps.management.get_nonce"
    if utils.USE_SERIAL_NUMBER and msg_type == MessageType.GetSerialNumber:
        return "apps.management.get_serial_number"
    if msg_type == MessageType.RebootToBootloader:
        return "apps.management.reboot_to_bootloader"

    if msg_type == MessageType.ShowDeviceTutorial:
        return "apps.management.show_tutorial"

    if utils.USE_BACKLIGHT and msg_type == MessageType.SetBrightness:
        return "apps.management.set_brightness"

    if utils.USE_SD_CARD and msg_type == MessageType.SdProtect:
        return "apps.management.sd_protect"

    if utils.USE_OPTIGA and msg_type == MessageType.AuthenticateDevice:
        return "apps.management.authenticate_device"

    if utils.USE_BLE:
        if msg_type == MessageType.BleUnpair:
            return "apps.management.ble.unpair"

    # bitcoin
    if msg_type == MessageType.AuthorizeCoinJoin:
        return "apps.bitcoin.authorize_coinjoin"
    if msg_type == MessageType.GetPublicKey:
        return "apps.bitcoin.get_public_key"
    if msg_type == MessageType.GetAddress:
        return "apps.bitcoin.get_address"
    if msg_type == MessageType.GetOwnershipId:
        return "apps.bitcoin.get_ownership_id"
    if msg_type == MessageType.GetOwnershipProof:
        return "apps.bitcoin.get_ownership_proof"
    if msg_type == MessageType.SignTx:
        return "apps.bitcoin.sign_tx"
    if msg_type == MessageType.SignMessage:
        return "apps.bitcoin.sign_message"
    if msg_type == MessageType.VerifyMessage:
        return "apps.bitcoin.verify_message"

    # extapp
    if msg_type == MessageType.ExtAppLoad:
        return "apps.extapp.load"
    if msg_type == MessageType.ExtAppRun:
        return "apps.extapp.run"

    # misc
    if msg_type == MessageType.GetEntropy:
        return "apps.misc.get_entropy"
    if msg_type == MessageType.SignIdentity:
        return "apps.misc.sign_identity"
    if msg_type == MessageType.GetECDHSessionKey:
        return "apps.misc.get_ecdh_session_key"
    if msg_type == MessageType.CipherKeyValue:
        return "apps.misc.cipher_key_value"
    if msg_type == MessageType.GetFirmwareHash:
        return "apps.misc.get_firmware_hash"

    # evolu
    if msg_type == MessageType.EvoluGetNode:
        return "apps.evolu.get_node"
    if msg_type == MessageType.EvoluSignRegistrationRequest:
        return "apps.evolu.sign_registration_request"
    if msg_type == MessageType.EvoluGetDelegatedIdentityKey:
        return "apps.evolu.get_delegated_identity_key"
    if msg_type == MessageType.PaymentNotification:
        return "apps.misc.payment_notification"

    if not utils.BITCOIN_ONLY:
        # When promoting the Nostr app to production-level
        # and removing the "if" guard don't forget to also remove
        # the corresponding guards (PYOPT == '0') in Sconscript.*
        if __debug__:
            # nostr
            if msg_type == MessageType.NostrGetPubkey:
                return "apps.nostr.get_pubkey"
            if msg_type == MessageType.NostrSignEvent:
                return "apps.nostr.sign_event"

        if msg_type == MessageType.SetU2FCounter:
            return "apps.management.set_u2f_counter"
        if msg_type == MessageType.GetNextU2FCounter:
            return "apps.management.get_next_u2f_counter"

        # webauthn
        if msg_type == MessageType.WebAuthnListResidentCredentials:
            return "apps.webauthn.list_resident_credentials"
        if msg_type == MessageType.WebAuthnAddResidentCredential:
            return "apps.webauthn.add_resident_credential"
        if msg_type == MessageType.WebAuthnRemoveResidentCredential:
            return "apps.webauthn.remove_resident_credential"

        # ethereum
        if msg_type == MessageType.EthereumGetAddress:
            return "apps.ethereum.get_address"
        if msg_type == MessageType.EthereumGetPublicKey:
            return "apps.ethereum.get_public_key"
        if msg_type == MessageType.EthereumSignTx:
            return "apps.ethereum.sign_tx"
        if msg_type == MessageType.EthereumSignTxEIP1559:
            return "apps.ethereum.sign_tx_eip1559"
        if msg_type == MessageType.EthereumSignMessage:
            return "apps.ethereum.sign_message"
        if msg_type == MessageType.EthereumVerifyMessage:
            return "apps.ethereum.verify_message"
        if msg_type == MessageType.EthereumSignTypedData:
            return "apps.ethereum.sign_typed_data"

        # monero
        if msg_type == MessageType.MoneroGetAddress:
            return "apps.monero.get_address"
        if msg_type == MessageType.MoneroGetWatchKey:
            return "apps.monero.get_watch_only"
        if msg_type == MessageType.MoneroTransactionInitRequest:
            return "apps.monero.sign_tx"
        if msg_type == MessageType.MoneroKeyImageExportInitRequest:
            return "apps.monero.key_image_sync"
        if msg_type == MessageType.MoneroGetTxKeyRequest:
            return "apps.monero.get_tx_keys"
        if msg_type == MessageType.MoneroLiveRefreshStartRequest:
            return "apps.monero.live_refresh"
        if __debug__ and msg_type == MessageType.DebugMoneroDiagRequest:
            return "apps.monero.diag"

        # nem
        if msg_type == MessageType.NEMGetAddress:
            return "apps.nem.get_address"
        if msg_type == MessageType.NEMSignTx:
            return "apps.nem.sign_tx"

        # stellar
        if msg_type == MessageType.StellarGetAddress:
            return "apps.stellar.get_address"
        if msg_type == MessageType.StellarSignTx:
            return "apps.stellar.sign_tx"

        # ripple
        if msg_type == MessageType.RippleGetAddress:
            return "apps.ripple.get_address"
        if msg_type == MessageType.RippleSignTx:
            return "apps.ripple.sign_tx"

        # cardano
        if msg_type == MessageType.CardanoGetAddress:
            return "apps.cardano.get_address"
        if msg_type == MessageType.CardanoGetPublicKey:
            return "apps.cardano.get_public_key"
        if msg_type == MessageType.CardanoSignTxInit:
            return "apps.cardano.sign_tx"
        if msg_type == MessageType.CardanoGetNativeScriptHash:
            return "apps.cardano.get_native_script_hash"
        if msg_type == MessageType.CardanoSignMessageInit:
            return "apps.cardano.sign_message"

        # tezos
        if msg_type == MessageType.TezosGetAddress:
            return "apps.tezos.get_address"
        if msg_type == MessageType.TezosSignTx:
            return "apps.tezos.sign_tx"
        if msg_type == MessageType.TezosGetPublicKey:
            return "apps.tezos.get_public_key"

        # eos
        if msg_type == MessageType.EosGetPublicKey:
            return "apps.eos.get_public_key"
        if msg_type == MessageType.EosSignTx:
            return "apps.eos.sign_tx"

        # solana
        if msg_type == MessageType.SolanaGetPublicKey:
            return "apps.solana.get_public_key"
        if msg_type == MessageType.SolanaGetAddress:
            return "apps.solana.get_address"
        if msg_type == MessageType.SolanaSignTx:
            return "apps.solana.sign_tx"

        # tron
        if msg_type == MessageType.TronGetAddress:
            return "apps.tron.get_address"

    raise ValueError


def find_registered_handler(msg_type: int) -> Handler | None:
    if msg_type in workflow_handlers:
        # Message has a handler available, return it directly.
        return workflow_handlers[msg_type]

    try:
        modname = _find_message_handler_module(msg_type)
        handler_name = modname[modname.rfind(".") + 1 :]
        module = __import__(modname, None, None, (handler_name,), 0)
        return getattr(module, handler_name)
    except ValueError:
        return None
