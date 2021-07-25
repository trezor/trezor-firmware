from trezor import utils
from trezor.enums import MessageType

if False:
    from trezor.wire import Handler
    from trezorio import WireInterface


workflow_handlers: dict[int, Handler] = {}


def register(wire_type: int, handler: Handler) -> None:
    """Register `handler` to get scheduled after `wire_type` message is received."""
    workflow_handlers[wire_type] = handler


def find_message_handler_module(msg_type: int) -> str:
    """Statically find the appropriate workflow handler.

    For now, new messages must be registered by hand in the if-elif manner below.
    The reason for this is memory fragmentation optimization:
    - using a dict would mean that the whole thing stays in RAM, whereas an if-elif
      sequence is run from flash
    - collecting everything as strings instead of importing directly means that we don't
      need to load any of the modules into memory until we actually need them
    """
    if False:
        raise RuntimeError

    # debug
    elif __debug__ and msg_type == MessageType.LoadDevice:
        return "apps.debug.load_device"

    # management
    elif msg_type == MessageType.ResetDevice:
        return "apps.management.reset_device"
    elif msg_type == MessageType.BackupDevice:
        return "apps.management.backup_device"
    elif msg_type == MessageType.WipeDevice:
        return "apps.management.wipe_device"
    elif msg_type == MessageType.RecoveryDevice:
        return "apps.management.recovery_device"
    elif msg_type == MessageType.ApplySettings:
        return "apps.management.apply_settings"
    elif msg_type == MessageType.ApplyFlags:
        return "apps.management.apply_flags"
    elif msg_type == MessageType.ChangePin:
        return "apps.management.change_pin"
    elif msg_type == MessageType.SdProtect:
        return "apps.management.sd_protect"
    elif msg_type == MessageType.ChangeWipeCode:
        return "apps.management.change_wipe_code"

    # bitcoin
    elif msg_type == MessageType.AuthorizeCoinJoin:
        return "apps.bitcoin.authorize_coinjoin"
    elif msg_type == MessageType.GetPublicKey:
        return "apps.bitcoin.get_public_key"
    elif msg_type == MessageType.GetAddress:
        return "apps.bitcoin.get_address"
    elif msg_type == MessageType.GetOwnershipId:
        return "apps.bitcoin.get_ownership_id"
    elif msg_type == MessageType.GetOwnershipProof:
        return "apps.bitcoin.get_ownership_proof"
    elif msg_type == MessageType.SignTx:
        return "apps.bitcoin.sign_tx"
    elif msg_type == MessageType.SignMessage:
        return "apps.bitcoin.sign_message"
    elif msg_type == MessageType.VerifyMessage:
        return "apps.bitcoin.verify_message"

    # misc
    elif msg_type == MessageType.GetEntropy:
        return "apps.misc.get_entropy"
    elif msg_type == MessageType.SignIdentity:
        return "apps.misc.sign_identity"
    elif msg_type == MessageType.GetECDHSessionKey:
        return "apps.misc.get_ecdh_session_key"
    elif msg_type == MessageType.CipherKeyValue:
        return "apps.misc.cipher_key_value"

    elif not utils.BITCOIN_ONLY:
        if False:
            raise RuntimeError

        elif msg_type == MessageType.SetU2FCounter:
            return "apps.management.set_u2f_counter"
        elif msg_type == MessageType.GetNextU2FCounter:
            return "apps.management.get_next_u2f_counter"

        # webauthn
        elif msg_type == MessageType.WebAuthnListResidentCredentials:
            return "apps.webauthn.list_resident_credentials"
        elif msg_type == MessageType.WebAuthnAddResidentCredential:
            return "apps.webauthn.add_resident_credential"
        elif msg_type == MessageType.WebAuthnRemoveResidentCredential:
            return "apps.webauthn.remove_resident_credential"

        # ethereum
        elif msg_type == MessageType.EthereumGetAddress:
            return "apps.ethereum.get_address"
        elif msg_type == MessageType.EthereumGetPublicKey:
            return "apps.ethereum.get_public_key"
        elif msg_type == MessageType.EthereumSignTx:
            return "apps.ethereum.sign_tx"
        elif msg_type == MessageType.EthereumSignMessage:
            return "apps.ethereum.sign_message"
        elif msg_type == MessageType.EthereumVerifyMessage:
            return "apps.ethereum.verify_message"

        # lisk
        elif msg_type == MessageType.LiskGetPublicKey:
            return "apps.lisk.get_public_key"
        elif msg_type == MessageType.LiskGetAddress:
            return "apps.lisk.get_address"
        elif msg_type == MessageType.LiskSignTx:
            return "apps.lisk.sign_tx"
        elif msg_type == MessageType.LiskSignMessage:
            return "apps.lisk.sign_message"
        elif msg_type == MessageType.LiskVerifyMessage:
            return "apps.lisk.verify_message"

        # monero
        elif msg_type == MessageType.MoneroGetAddress:
            return "apps.monero.get_address"
        elif msg_type == MessageType.MoneroGetWatchKey:
            return "apps.monero.get_watch_only"
        elif msg_type == MessageType.MoneroTransactionInitRequest:
            return "apps.monero.sign_tx"
        elif msg_type == MessageType.MoneroKeyImageExportInitRequest:
            return "apps.monero.key_image_sync"
        elif msg_type == MessageType.MoneroGetTxKeyRequest:
            return "apps.monero.get_tx_keys"
        elif msg_type == MessageType.MoneroLiveRefreshStartRequest:
            return "apps.monero.live_refresh"
        if __debug__ and msg_type == MessageType.DebugMoneroDiagRequest:
            return "apps.monero.diag"

        # nem
        elif msg_type == MessageType.NEMGetAddress:
            return "apps.nem.get_address"
        elif msg_type == MessageType.NEMSignTx:
            return "apps.nem.sign_tx"

        # stellar
        elif msg_type == MessageType.StellarGetAddress:
            return "apps.stellar.get_address"
        elif msg_type == MessageType.StellarSignTx:
            return "apps.stellar.sign_tx"

        # ripple
        elif msg_type == MessageType.RippleGetAddress:
            return "apps.ripple.get_address"
        elif msg_type == MessageType.RippleSignTx:
            return "apps.ripple.sign_tx"

        # cardano
        elif msg_type == MessageType.CardanoGetAddress:
            return "apps.cardano.get_address"
        elif msg_type == MessageType.CardanoGetPublicKey:
            return "apps.cardano.get_public_key"
        elif msg_type == MessageType.CardanoSignTx:
            return "apps.cardano.sign_tx"

        # tezos
        elif msg_type == MessageType.TezosGetAddress:
            return "apps.tezos.get_address"
        elif msg_type == MessageType.TezosSignTx:
            return "apps.tezos.sign_tx"
        elif msg_type == MessageType.TezosGetPublicKey:
            return "apps.tezos.get_public_key"

        # eos
        elif msg_type == MessageType.EosGetPublicKey:
            return "apps.eos.get_public_key"
        elif msg_type == MessageType.EosSignTx:
            return "apps.eos.sign_tx"

        # binance
        elif msg_type == MessageType.BinanceGetAddress:
            return "apps.binance.get_address"
        elif msg_type == MessageType.BinanceGetPublicKey:
            return "apps.binance.get_public_key"
        elif msg_type == MessageType.BinanceSignTx:
            return "apps.binance.sign_tx"

    raise ValueError


def find_registered_handler(iface: WireInterface, msg_type: int) -> Handler | None:
    if msg_type in workflow_handlers:
        # Message has a handler available, return it directly.
        return workflow_handlers[msg_type]

    try:
        modname = find_message_handler_module(msg_type)
        handler_name = modname[modname.rfind(".") + 1 :]
        module = __import__(modname, None, None, (handler_name,), 0)
        return getattr(module, handler_name)  # type: ignore
    except ValueError:
        return None
