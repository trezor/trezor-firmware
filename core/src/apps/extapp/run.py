import ustruct
from micropython import const
from typing import TYPE_CHECKING

import trezorcrypto_api
import trezorui_api
from storage import cache_common as cc
from storage.cache import get_sessionless_cache
from trezor import app, io, loop
from trezor.messages import ExtAppMessage, ExtAppResponse
from trezor.ui import ProgressLayout
from trezor.ui.layouts.progress import progress
from trezor.ui.layouts.common import with_info, interact
from trezor.wire import context
from trezor.wire.errors import DataError
from apps.common import paths
from apps.common.keychain import get_keychain
from apps.ethereum.definitions import Definitions
from trezor.enums import ButtonRequestType
from trezor.wire import ActionCancelled

if TYPE_CHECKING:
    from trezorio import IpcMessage
    from typing import NoReturn

_SYSTASK_ID_EXTAPP = const(2)

_SERVICE_LIFECYCLE = const(0)
_SERVICE_UI = const(1)
_SERVICE_WIRE_START = const(2)
_SERVICE_WIRE_CONTINUE = const(3)
_SERVICE_WIRE_END = const(4)
_SERVICE_CRYPTO = const(5)
_SERVICE_UTIL = const(6)
_SERVICE_PROGRESS = const(7)

_SERVICE_PROGRESS_INIT = const(0)
_SERVICE_PROGRESS_REPORT = const(1)
_SERVICE_PROGRESS_STOP = const(2)

_SERIVICE_CRYPTO_GET_XPUB = const(0)
_SERIVICE_CRYPTO_GET_ETH_XPUB_HASH = const(1)
_SERVICE_CRYPTO_SIGN_TYPED_HASH = const(2)
_SERVICE_CRYPTO_GET_ADDRESS_MAC = const(3)


def fn_id(service: int, message_id: int) -> int:
    print("service:", service, "message_id:", message_id)
    print("fn_id:", (service << 16) | (message_id & 0xFFFF))
    return (service << 16) | (message_id & 0xFFFF)


def from_fn_id(fn_id: int) -> tuple[int, int]:
    return ((fn_id >> 16) & 0xFFFF, fn_id & 0xFFFF)


async def run(request: ExtAppMessage) -> ExtAppResponse:
    if request.message_id > 0xFFFF:
        raise DataError("Invalid message ID.")

    instance_ids = get_sessionless_cache().get(cc.APP_EXTAPP_IDS)
    if instance_ids is None:
        raise DataError(f"Invalid instance ID: {request.instance_id}")
    task_id, instance_id = ustruct.unpack("<BI", instance_ids)
    if instance_id != request.instance_id:
        raise DataError(f"Invalid instance ID: {request.instance_id}")

    task = app.AppTask(task_id)
    if not task.is_running():
        raise DataError(f"Task not running: {request.instance_id}")

    def die(exception: Exception) -> NoReturn:
        task.unload()
        raise exception

    try:
        io.ipc_send(
            _SYSTASK_ID_EXTAPP,
            fn_id(_SERVICE_WIRE_START, request.message_id),
            request.data,
        )
    except Exception as e:
        die(DataError(f"Failed to send IPC message: {e}"))

    progress_obj: ProgressLayout | None = None

    def request_callback(data: bytes, id: int = 0) -> None:
        io.ipc_send(_SYSTASK_ID_EXTAPP, fn_id(_SERVICE_UTIL, id), data)

    def crypto_resp_cb(data: bytes) -> None:
        io.ipc_send(_SYSTASK_ID_EXTAPP, fn_id(_SERVICE_CRYPTO, 0), data)

    def ui_resp_cb(data: bytes) -> None:
        io.ipc_send(_SYSTASK_ID_EXTAPP, fn_id(_SERVICE_UI, 0), data)

    while True:
        if not task.is_running():
            raise DataError(f"Task stopped: {request.instance_id}")
        try:
            msg: IpcMessage = await loop.wait(
                io.IPC2_EVENT | io.POLL_READ, timeout_ms=1000
            )
        except loop.Timeout:
            die(DataError("Timeout waiting for message"))

        service, message_id = from_fn_id(msg.fn)

        if service == _SERVICE_UI:
            (main_layout_obj, info_layout_obj, (br_code, br_name)) = (
                trezorui_api.process_ipc_message(
                    data=bytes(msg.data), request_cb=request_callback
                )
            )
            br_code_value: ButtonRequestType = (
                br_code if br_code is not None else ButtonRequestType.Other
            )

            if info_layout_obj is not None:
                assert (
                    br_name is not None
                ), "br_name must be provided if info_layout_obj is provided"

                try:
                    result = await with_info(
                        main_layout_obj, info_layout_obj, br_name, br_code_value
                    )
                except ActionCancelled:
                    result = trezorui_api.CANCELLED
            else:
                result = await interact(
                    main_layout_obj, br_name, br_code_value, raise_on_cancel=None
                )
            # Serialize and send the result back
            trezorui_api.send_ui_result(result=result, ipc_cb=ui_resp_cb)

        elif service == _SERVICE_CRYPTO:
            print("Received crypto message with ID:", message_id)
            try:
                obj = trezorcrypto_api.deserialize_crypto_message(data=bytes(msg.data))

                if message_id == _SERIVICE_CRYPTO_GET_XPUB:
                    print("Handling get xpub request")
                    address_n: list[int] = obj
                    try:
                        result = await _get_public_key(address_n)
                    except:
                        print("Failed to derive public key")
                        result = False

                elif message_id == _SERIVICE_CRYPTO_GET_ETH_XPUB_HASH:
                    print("Handling get Ethereum pubkey hash request")
                    assert len(obj) == 3
                    address_n: list[int] = obj[0]
                    encoded_network: bytes | None = obj[1]
                    encoded_token: bytes | None = obj[2]
                    try:
                        result = await _ethereum_pubkeyhash(
                            address_n, encoded_network, encoded_token
                        )
                    except:
                        print("Failed to derive Ethereum pubkey hash")
                        result = False

                elif message_id == _SERVICE_CRYPTO_SIGN_TYPED_HASH:
                    print("Handling sign typed hash request")
                    assert len(obj) == 4
                    address_n: list[int] = obj[0]
                    data_hash: bytes = obj[1]
                    encoded_network: bytes | None = obj[2]
                    encoded_token: bytes | None = obj[3]
                    try:
                        result = await _sign_typed_hash(
                            address_n, data_hash, encoded_network, encoded_token
                        )
                    except:
                        print("Failed to sign typed hash")
                        result = False

                elif message_id == _SERVICE_CRYPTO_GET_ADDRESS_MAC:
                    print("Handling get address MAC request")
                    assert len(obj) == 3
                    address_n: list[int] = obj[0]
                    address_str: str = obj[1]
                    network: bytes | None = obj[2]
                    try:
                        result = await _get_address_mac(address_n, address_str, network)
                    except:
                        print("Failed to get address MAC")
                        result = False

                else:
                    print("Unknown crypto message ID:", message_id)
                    die(DataError("Unknown crypto operation"))

            except:
                print("Invalid crypto message format")
                result = False

            # Serialize and send the result back
            try:
                result = trezorcrypto_api.send_crypto_result(
                    result=result, ipc_cb=crypto_resp_cb
                )
            except:
                print("Failed to send crypto result")
                die(DataError("Failed to serialize or send crypto result"))

        elif service == _SERVICE_WIRE_CONTINUE:
            # usb request/ack
            response = ExtAppResponse(
                message_id=message_id, data=msg.data, finished=False
            )
            ack = await context.call(response, ExtAppMessage)
            if ack.message_id > 0xFFFF:
                die(DataError("Invalid message ID."))
            io.ipc_send(
                _SYSTASK_ID_EXTAPP,
                fn_id(_SERVICE_WIRE_CONTINUE, ack.message_id),
                ack.data,
            )

        elif service == _SERVICE_WIRE_END:
            # usb final message
            response = ExtAppResponse(
                message_id=message_id, data=msg.data, finished=True
            )
            task.unload()
            return response

        elif service == _SERVICE_PROGRESS:
            obj = trezorui_api.deserialize_progress_message(data=bytes(msg.data))
            if message_id == _SERVICE_PROGRESS_INIT:
                # Initialize a progress context
                assert isinstance(obj, tuple)
                assert len(obj) == 4
                description: str = obj[0]
                title: str | None = obj[1]
                indeterminate: bool = obj[2]
                danger: bool = obj[3]
                progress_obj = progress(
                    description=description,
                    title=title,
                    indeterminate=indeterminate,
                    danger=danger,
                )
                io.ipc_send(
                    _SYSTASK_ID_EXTAPP,
                    fn_id(_SERVICE_PROGRESS_INIT, message_id),
                    b"",
                )
            elif message_id == _SERVICE_PROGRESS_REPORT:
                if progress_obj is None:
                    die(DataError("Progress not initialized"))
                # Report progress update
                assert isinstance(obj, tuple)
                assert len(obj) == 2
                description: str = obj[0]
                value: int = obj[1]
                progress_obj.report(value, description=description)
                io.ipc_send(
                    _SYSTASK_ID_EXTAPP,
                    fn_id(_SERVICE_PROGRESS_REPORT, message_id),
                    b"",
                )
            elif message_id == _SERVICE_PROGRESS_STOP:
                if progress_obj is None:
                    die(DataError("Progress not initialized"))
                # Stop the progress context
                progress_obj.stop()
                io.ipc_send(
                    _SYSTASK_ID_EXTAPP,
                    fn_id(_SERVICE_PROGRESS_STOP, message_id),
                    b"",
                )
                progress_obj = None
            else:
                die(DataError("Unknown progress message ID"))

        else:
            die(RuntimeError("Unknown IPC function"))


async def _get_public_key(address_n: list[int]) -> str:
    from apps.common import coininfo, paths
    from apps.common.keychain import ForbiddenKeyPath, get_keychain

    # from trezor.messages import HDNodeType
    # from trezor.enums import InputScriptType

    coin = coininfo.by_name("Bitcoin")
    # script_type = InputScriptType.SPENDADDRESS

    if address_n and address_n[0] == paths.SLIP25_PURPOSE:
        # UnlockPath is required to access SLIP25 paths.
        raise ForbiddenKeyPath()

    keychain = await get_keychain(coin.curve_name, [paths.AlwaysMatchingSchema])

    node = keychain.derive(address_n)
    assert coin.xpub_magic is not None
    node_xpub = node.serialize_public(coin.xpub_magic)
    # pubkey = node.public_key()
    # node_type = HDNodeType(
    #     depth=node.depth(),
    #     child_num=node.child_num(),
    #     fingerprint=node.fingerprint(),
    #     chain_code=node.chain_code(),
    #     public_key=pubkey,
    # )
    return node_xpub


async def _ethereum_pubkeyhash(
    address_n: list[int], encoded_network: bytes | None, encoded_token: bytes | None
) -> bytes:
    from apps.ethereum.keychain import (
        PATTERNS_ADDRESS,
        _slip44_from_address_n,
        _schemas_from_network,
    )
    from apps.ethereum.definitions import Definitions

    slip44 = _slip44_from_address_n(address_n)
    defs = Definitions.from_encoded(encoded_network, encoded_token, slip44=slip44)
    schemas = _schemas_from_network(PATTERNS_ADDRESS, defs.network)
    keychain = await get_keychain("secp256k1", schemas, [[b"SLIP-0024"]])

    node = keychain.derive(address_n)
    address_bytes: bytes = node.ethereum_pubkeyhash()
    return address_bytes


async def _get_address_mac(
    address_n: list[int], address: str, encoded_network: bytes | None
) -> bytes:
    from apps.common.address_mac import get_address_mac
    from apps.ethereum.keychain import (
        PATTERNS_ADDRESS,
        _slip44_from_address_n,
        _schemas_from_network,
    )

    slip44 = _slip44_from_address_n(address_n)
    defs = Definitions.from_encoded(
        encoded_network=encoded_network, encoded_token=None, slip44=slip44
    )
    schemas = _schemas_from_network(PATTERNS_ADDRESS, defs.network)
    keychain = await get_keychain("secp256k1", schemas, [[b"SLIP-0024"]])

    slip44_id = address_n[1]  # it depends on the network (ETH vs ETC...)
    return get_address_mac(address, paths.unharden(slip44_id), address_n, keychain)


async def _sign_typed_hash(
    address_n: list[int],
    data_hash: bytes,
    encoded_network: bytes | None,
    encoded_token: bytes | None,
) -> bytes:
    from trezor import TR
    from trezor.crypto.curve import secp256k1
    from trezor.ui.layouts.progress import progress
    from apps.ethereum.keychain import (
        PATTERNS_ADDRESS,
        _slip44_from_address_n,
        _schemas_from_network,
    )

    slip44 = _slip44_from_address_n(address_n)
    defs = Definitions.from_encoded(encoded_network, encoded_token, slip44=slip44)
    schemas = _schemas_from_network(PATTERNS_ADDRESS, defs.network)
    keychain = await get_keychain("secp256k1", schemas, [[b"SLIP-0024"]])

    node = keychain.derive(address_n)

    progress_obj = progress(title=TR.progress__signing_transaction)
    progress_obj.report(600)
    signature = secp256k1.sign(
        node.private_key(),
        data_hash,
        False,
        secp256k1.CANONICAL_SIG_ETHEREUM,
    )
    progress_obj.stop()
    return signature
