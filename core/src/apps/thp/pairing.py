from typing import TYPE_CHECKING
from ubinascii import hexlify

from trezor import protobuf
from trezor.crypto import random
from trezor.crypto.hashlib import sha256
from trezor.enums import ThpMessageType, ThpPairingMethod
from trezor.messages import (
    Cancel,
    ThpCodeEntryChallenge,
    ThpCodeEntryCommitment,
    ThpCodeEntryCpaceHostTag,
    ThpCodeEntryCpaceTrezor,
    ThpCodeEntrySecret,
    ThpCredentialMetadata,
    ThpCredentialRequest,
    ThpCredentialResponse,
    ThpEndRequest,
    ThpEndResponse,
    ThpNfcTagHost,
    ThpNfcTagTrezor,
    ThpPairingPreparationsFinished,
    ThpPairingRequest,
    ThpQrCodeSecret,
    ThpQrCodeTag,
    ThpSelectMethod,
)
from trezor.wire import message_handler
from trezor.wire.context import UnexpectedMessageException
from trezor.wire.errors import SilentError, UnexpectedMessage
from trezor.wire.thp import ChannelState, ThpError, crypto, get_enabled_pairing_methods
from trezor.wire.thp.pairing_context import PairingContext

from .credential_manager import is_credential_autoconnect, issue_credential

if __debug__:
    from trezor import log

if TYPE_CHECKING:
    from typing import Any, Callable, Concatenate, ParamSpec, Tuple

    P = ParamSpec("P")
    FuncWithContext = Callable[Concatenate[PairingContext, P], Any]

#
# Helpers - decorators


def check_state_and_log(
    *allowed_states: ChannelState,
) -> Callable[[FuncWithContext], FuncWithContext]:
    def decorator(f: FuncWithContext) -> FuncWithContext:
        def inner(context: PairingContext, *args: P.args, **kwargs: P.kwargs) -> object:
            _check_state(context, *allowed_states)
            if __debug__:
                try:
                    log.debug(__name__, "started %s", f.__name__)
                except AttributeError:
                    log.debug(
                        __name__,
                        "started a function that cannot be named, because it raises AttributeError, eg. closure",
                    )
            return f(context, *args, **kwargs)

        return inner

    return decorator


def check_method_is_allowed_and_selected(
    pairing_method: ThpPairingMethod,
) -> Callable[[FuncWithContext], FuncWithContext]:
    def decorator(f: FuncWithContext) -> FuncWithContext:
        def inner(context: PairingContext, *args: P.args, **kwargs: P.kwargs) -> object:
            _check_method_is_allowed(context, pairing_method)
            _check_method_is_selected(context, pairing_method)
            return f(context, *args, **kwargs)

        return inner

    return decorator


#
# Pairing handlers


@check_state_and_log(ChannelState.TP0)
async def handle_pairing_request(
    ctx: PairingContext, message: protobuf.MessageType
) -> ThpEndResponse:

    if not ThpPairingRequest.is_type_of(message):
        raise UnexpectedMessage("Unexpected message")

    ctx.host_name = message.host_name or ""

    await ctx.show_pairing_dialogue()
    assert ThpSelectMethod.MESSAGE_WIRE_TYPE is not None
    select_method_msg = await ctx.read(
        [
            ThpSelectMethod.MESSAGE_WIRE_TYPE,
        ]
    )

    assert ThpSelectMethod.is_type_of(select_method_msg)
    assert select_method_msg.selected_pairing_method is not None

    ctx.set_selected_method(select_method_msg.selected_pairing_method)

    if ctx.selected_method == ThpPairingMethod.SkipPairing:
        return await _end_pairing(ctx)

    while True:
        await _prepare_pairing(ctx)

        ctx.channel_ctx.set_channel_state(ChannelState.TP3)
        try:
            # Should raise UnexpectedMessageException
            await ctx.show_pairing_method_screen()
        except UnexpectedMessageException as e:
            raw_response = e.msg
            name = message_handler.get_msg_name(raw_response.type)
            if name is None:
                req_type = protobuf.type_for_wire(raw_response.type)
            else:
                req_type = protobuf.type_for_name(name)
            response = message_handler.wrap_protobuf_load(raw_response.data, req_type)

        if Cancel.is_type_of(response):
            ctx.channel_ctx.clear()
            raise SilentError("Action was cancelled by the Host")

        if ThpSelectMethod.is_type_of(response):
            assert response.selected_pairing_method is not None
            ctx.set_selected_method(response.selected_pairing_method)
            ctx.channel_ctx.set_channel_state(ChannelState.TP1)
        else:
            break

    response: protobuf.MessageType = await _handle_different_pairing_methods(
        ctx, response
    )
    return await handle_credential_phase(
        ctx,
        message=response,
        show_connection_dialog=False,
    )


@check_state_and_log(ChannelState.TC1)
async def handle_credential_phase(
    ctx: PairingContext,
    message: protobuf.MessageType,
    show_connection_dialog: bool = True,
) -> ThpEndResponse:
    autoconnect: bool = False
    credential = ctx.channel_ctx.credential

    if credential is not None:
        autoconnect = is_credential_autoconnect(credential)
        if not autoconnect:
            autoconnect = ctx.channel_ctx.is_channel_to_replace()
        if credential.cred_metadata is not None:
            ctx.host_name = credential.cred_metadata.host_name
        if ctx.host_name is None:
            raise Exception("Credential does not have a hostname")

    if show_connection_dialog and not autoconnect:
        await ctx.show_connection_dialogue()

    while ThpCredentialRequest.is_type_of(message):
        message = await _handle_credential_request(ctx, message)

    return await _handle_end_request(ctx, message)


async def _prepare_pairing(ctx: PairingContext) -> None:
    ctx.channel_ctx.set_channel_state(ChannelState.TP1)

    if ctx.selected_method == ThpPairingMethod.CodeEntry:
        await _handle_code_entry_is_selected(ctx)
    elif ctx.selected_method == ThpPairingMethod.NFC:
        await _handle_nfc_is_selected(ctx)
    elif ctx.selected_method == ThpPairingMethod.QrCode:
        await _handle_qr_code_is_selected(ctx)
    else:
        raise Exception()  # TODO unknown pairing method


@check_state_and_log(ChannelState.TP1)
async def _handle_code_entry_is_selected(ctx: PairingContext) -> None:
    if ctx.code_entry_secret is None:
        await _handle_code_entry_is_selected_first_time(ctx)
    else:
        await ctx.write_force(ThpPairingPreparationsFinished())


async def _handle_code_entry_is_selected_first_time(ctx: PairingContext) -> None:
    from trezor.wire.thp.cpace import Cpace

    ctx.code_entry_secret = random.bytes(16)
    commitment = sha256(ctx.code_entry_secret).digest()

    challenge_message = await ctx.call(
        ThpCodeEntryCommitment(commitment=commitment), ThpCodeEntryChallenge
    )
    ctx.channel_ctx.set_channel_state(ChannelState.TP2)

    if not ThpCodeEntryChallenge.is_type_of(challenge_message):
        raise UnexpectedMessage("Unexpected message")

    if challenge_message.challenge is None:
        raise Exception("Invalid message")
    sha_ctx = sha256(ThpPairingMethod.CodeEntry.to_bytes(1, "big"))
    sha_ctx.update(ctx.channel_ctx.get_handshake_hash())
    sha_ctx.update(ctx.code_entry_secret)
    sha_ctx.update(challenge_message.challenge)
    code_code_entry_hash = sha_ctx.digest()
    ctx.code_code_entry = int.from_bytes(code_code_entry_hash, "big") % 1000000
    ctx.cpace = Cpace(
        ctx.channel_ctx.get_handshake_hash(),
    )
    assert ctx.code_code_entry is not None
    ctx.cpace.generate_keys(ctx.code_code_entry.to_bytes(6, "big"))
    await ctx.write_force(
        ThpCodeEntryCpaceTrezor(cpace_trezor_public_key=ctx.cpace.trezor_public_key)
    )


@check_state_and_log(ChannelState.TP1)
async def _handle_nfc_is_selected(ctx: PairingContext) -> None:
    ctx.nfc_secret = random.bytes(16)
    await ctx.write_force(ThpPairingPreparationsFinished())


@check_state_and_log(ChannelState.TP1)
async def _handle_qr_code_is_selected(ctx: PairingContext) -> None:
    ctx.qr_code_secret = random.bytes(16)

    sha_ctx = sha256(ThpPairingMethod.QrCode.to_bytes(1, "big"))
    sha_ctx.update(ctx.channel_ctx.get_handshake_hash())
    sha_ctx.update(ctx.qr_code_secret)

    ctx.code_qr_code = sha_ctx.digest()[:16]
    await ctx.write_force(ThpPairingPreparationsFinished())


@check_state_and_log(ChannelState.TP3)
async def _handle_different_pairing_methods(
    ctx: PairingContext, response: protobuf.MessageType
) -> protobuf.MessageType:
    if ThpCodeEntryCpaceHostTag.is_type_of(response):
        return await _handle_code_entry_cpace(ctx, response)
    if ThpQrCodeTag.is_type_of(response):
        return await _handle_qr_code_tag(ctx, response)
    if ThpNfcTagHost.is_type_of(response):
        return await _handle_nfc_tag(ctx, response)
    raise UnexpectedMessage("Unexpected message" + str(response))


@check_state_and_log(ChannelState.TP3)
@check_method_is_allowed_and_selected(ThpPairingMethod.CodeEntry)
async def _handle_code_entry_cpace(
    ctx: PairingContext, message: protobuf.MessageType
) -> protobuf.MessageType:

    if TYPE_CHECKING:
        assert ThpCodeEntryCpaceHostTag.is_type_of(message)
    if message.cpace_host_public_key is None:
        raise ThpError(
            "Message ThpCodeEntryCpaceHostTag is missing cpace_host_public_key"
        )
    if message.tag is None:
        raise ThpError("Message ThpCodeEntryCpaceHostTag is missing tag")

    ctx.cpace.compute_shared_secret(message.cpace_host_public_key)
    expected_tag = sha256(ctx.cpace.shared_secret).digest()
    if expected_tag != message.tag:
        print(
            "expected code entry tag:", hexlify(expected_tag).decode()
        )  # TODO remove after testing
        print(
            "expected code entry shared secret:",
            hexlify(ctx.cpace.shared_secret).decode(),
        )  # TODO remove after testing
        raise ThpError("Unexpected Code Entry Tag")

    return await _handle_secret_reveal(
        ctx,
        msg=ThpCodeEntrySecret(secret=ctx.code_entry_secret),
    )


@check_state_and_log(ChannelState.TP3)
@check_method_is_allowed_and_selected(ThpPairingMethod.QrCode)
async def _handle_qr_code_tag(
    ctx: PairingContext, message: protobuf.MessageType
) -> protobuf.MessageType:
    if TYPE_CHECKING:
        assert isinstance(message, ThpQrCodeTag)
    assert ctx.code_qr_code is not None
    sha_ctx = sha256(ctx.channel_ctx.get_handshake_hash())
    sha_ctx.update(ctx.code_qr_code)
    expected_tag = sha_ctx.digest()
    if expected_tag != message.tag:
        print(
            "expected qr code tag:", hexlify(expected_tag).decode()
        )  # TODO remove after testing
        print(
            "expected handshake hash:",
            hexlify(ctx.channel_ctx.get_handshake_hash()).decode(),
        )  # TODO remove after testing
        print(
            "expected code qr code:",
            hexlify(ctx.code_qr_code).decode(),
        )  # TODO remove after testing
        print(
            "expected secret:", hexlify(ctx.qr_code_secret or b"").decode()
        )  # TODO remove after testing
        raise ThpError("Unexpected QR Code Tag")

    return await _handle_secret_reveal(
        ctx,
        msg=ThpQrCodeSecret(secret=ctx.qr_code_secret),
    )


@check_state_and_log(ChannelState.TP3)
@check_method_is_allowed_and_selected(ThpPairingMethod.NFC)
async def _handle_nfc_tag(
    ctx: PairingContext, message: protobuf.MessageType
) -> protobuf.MessageType:
    if TYPE_CHECKING:
        assert isinstance(message, ThpNfcTagHost)

    assert ctx.nfc_secret is not None
    assert ctx.handshake_hash_host is not None
    assert ctx.nfc_secret_host is not None
    assert len(ctx.nfc_secret_host) == 16

    sha_ctx = sha256(ThpPairingMethod.NFC.to_bytes(1, "big"))
    sha_ctx.update(ctx.channel_ctx.get_handshake_hash())
    sha_ctx.update(ctx.nfc_secret)
    expected_tag = sha_ctx.digest()
    if expected_tag != message.tag:
        print(
            "expected nfc tag:", hexlify(expected_tag).decode()
        )  # TODO remove after testing
        raise ThpError("Unexpected NFC Unidirectional Tag")

    if ctx.handshake_hash_host[:16] != ctx.channel_ctx.get_handshake_hash()[:16]:
        raise ThpError("Handshake hash mismatch")

    sha_ctx = sha256(ThpPairingMethod.NFC.to_bytes(1, "big"))
    sha_ctx.update(ctx.channel_ctx.get_handshake_hash())
    sha_ctx.update(ctx.nfc_secret_host)
    trezor_tag = sha_ctx.digest()
    return await _handle_secret_reveal(
        ctx,
        msg=ThpNfcTagTrezor(tag=trezor_tag),
    )


@check_state_and_log(ChannelState.TP3, ChannelState.TP4)
async def _handle_secret_reveal(
    ctx: PairingContext,
    msg: protobuf.MessageType,
) -> protobuf.MessageType:
    ctx.channel_ctx.set_channel_state(ChannelState.TC1)
    return await ctx.call_any(
        msg,
        ThpMessageType.ThpCredentialRequest,
        ThpMessageType.ThpEndRequest,
    )


@check_state_and_log(ChannelState.TC1)
async def _handle_credential_request(
    ctx: PairingContext, message: protobuf.MessageType
) -> protobuf.MessageType:

    if not ThpCredentialRequest.is_type_of(message):
        raise UnexpectedMessage("Unexpected message")
    if message.host_static_pubkey is None:
        raise Exception("Invalid message")  # TODO change failure type

    autoconnect: bool = False
    if message.autoconnect is not None:
        autoconnect = message.autoconnect

    trezor_static_pubkey = crypto.get_trezor_static_pubkey()
    credential_metadata = ThpCredentialMetadata(
        host_name=ctx.host_name,
        autoconnect=autoconnect,
    )
    credential = issue_credential(message.host_static_pubkey, credential_metadata)

    return await ctx.call_any(
        ThpCredentialResponse(
            trezor_static_pubkey=trezor_static_pubkey, credential=credential
        ),
        ThpMessageType.ThpCredentialRequest,
        ThpMessageType.ThpEndRequest,
    )


@check_state_and_log(ChannelState.TC1)
async def _handle_end_request(
    ctx: PairingContext, message: protobuf.MessageType
) -> ThpEndResponse:
    if not ThpEndRequest.is_type_of(message):
        raise UnexpectedMessage("Unexpected message")
    return await _end_pairing(ctx)


async def _end_pairing(ctx: PairingContext) -> ThpEndResponse:
    ctx.channel_ctx.replace_old_channels_with_the_same_host_pubkey()
    ctx.channel_ctx.set_channel_state(ChannelState.ENCRYPTED_TRANSPORT)
    return ThpEndResponse()


#
# Helpers - checkers


def _check_state(ctx: PairingContext, *allowed_states: ChannelState) -> None:
    if ctx.channel_ctx.get_channel_state() not in allowed_states:
        raise UnexpectedMessage("Unexpected message")


def _check_method_is_allowed(ctx: PairingContext, method: ThpPairingMethod) -> None:
    if method not in get_enabled_pairing_methods(ctx.iface):
        raise ThpError("Unexpected pairing method")


def _check_method_is_selected(ctx: PairingContext, method: ThpPairingMethod) -> None:
    if method is not ctx.selected_method:
        raise ThpError("Not selected pairing method")


#
# Helpers - getters


def _get_accepted_messages(ctx: PairingContext) -> Tuple[int, ...]:
    r = _get_possible_pairing_methods(ctx)
    mtype = Cancel.MESSAGE_WIRE_TYPE
    r += (mtype,) if mtype is not None else ()
    mtype = ThpSelectMethod.MESSAGE_WIRE_TYPE
    r += (mtype,) if mtype is not None else ()

    return r


def _get_possible_pairing_methods(ctx: PairingContext) -> Tuple[int, ...]:
    r = tuple(
        [
            _get_message_type_for_method(ctx.selected_method),
        ]
    )
    return r


def _get_message_type_for_method(method: int) -> int:
    if method is ThpPairingMethod.CodeEntry:
        return ThpMessageType.ThpCodeEntryCpaceHostTag
    if method is ThpPairingMethod.NFC:
        return ThpMessageType.ThpNfcTagHost
    if method is ThpPairingMethod.QrCode:
        return ThpMessageType.ThpQrCodeTag
    raise ValueError("Unexpected pairing method - no message type available")
