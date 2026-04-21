import ustruct
from micropython import const
from typing import TYPE_CHECKING

import trezorcrypto_api
import trezorui_api
from storage import cache_common as cc
from storage.cache import get_sessionless_cache
from trezor import app, io, loop
from trezor.enums import FailureType
from trezor.messages import ExtAppMessage, ExtAppResponse, Failure
from trezor.ui import ProgressLayout
from trezor.ui.layouts.common import interact
from trezor.ui.layouts.progress import progress
from trezor.wire import context
from trezor.wire.errors import DataError

from apps.common import paths
from apps.common.keychain import get_keychain
from apps.ethereum.definitions import Definitions

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
_SERVICE_WIRE_ERROR = const(8)

_SERVICE_PROGRESS_INIT = const(0)
_SERVICE_PROGRESS_REPORT = const(1)
_SERVICE_PROGRESS_STOP = const(2)

_SERIVICE_CRYPTO_GET_XPUB = const(0)
_SERIVICE_CRYPTO_GET_ETH_XPUB_HASH = const(1)
_SERVICE_CRYPTO_SIGN_TYPED_HASH = const(2)
_SERVICE_CRYPTO_GET_ADDRESS_MAC = const(3)
_SERVICE_CRYPTO_VERIFY_NONCE_CACHE = const(4)
_SERVICE_CRYPTO_CHECK_ADDRESS_MAC = const(5)


def fn_id(service: int, message_id: int) -> int:
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
            (main_layout_obj, br_code, br_name) = trezorui_api.process_ipc_message(
                data=bytes(msg.data), request_cb=request_callback
            )

            result = await interact(
                main_layout_obj, br_name, br_code, raise_on_cancel=None
            )
            # Serialize and send the result back
            trezorui_api.send_ui_result(result=result, ipc_cb=ui_resp_cb)

        elif service == _SERVICE_CRYPTO:
            try:
                obj = trezorcrypto_api.deserialize_crypto_message(data=bytes(msg.data))

                if message_id == _SERIVICE_CRYPTO_GET_XPUB:
                    address_n: list[int] = obj
                    try:
                        result = await _get_public_key(address_n)
                    # TODO: catch specific exception
                    except:  # noqa: E722
                        result = False

                elif message_id == _SERIVICE_CRYPTO_GET_ETH_XPUB_HASH:
                    assert len(obj) == 3
                    address_n: list[int] = obj[0]
                    encoded_network: bytes | None = obj[1]
                    encoded_token: bytes | None = obj[2]
                    try:
                        result = await _ethereum_pubkeyhash(
                            address_n, encoded_network, encoded_token
                        )
                    # TODO: catch specific exception
                    except:  # noqa: E722
                        result = False

                elif message_id == _SERVICE_CRYPTO_SIGN_TYPED_HASH:
                    assert len(obj) == 5
                    address_n: list[int] = obj[0]
                    data_hash: bytes = obj[1]
                    encoded_network: bytes | None = obj[2]
                    encoded_token: bytes | None = obj[3]
                    chain_id: int | None = obj[4]
                    try:
                        result = await _sign_typed_hash(
                            address_n,
                            data_hash,
                            encoded_network,
                            encoded_token,
                            chain_id,
                        )
                    # TODO: catch specific exception
                    except:  # noqa: E722
                        result = False

                elif message_id == _SERVICE_CRYPTO_GET_ADDRESS_MAC:
                    assert len(obj) == 3
                    address_n: list[int] = obj[0]
                    address_str: str = obj[1]
                    network: bytes | None = obj[2]
                    try:
                        result = await _get_address_mac(address_n, address_str, network)
                    # TODO: catch specific exception
                    except:  # noqa: E722
                        result = False
                elif message_id == _SERVICE_CRYPTO_VERIFY_NONCE_CACHE:
                    nonce: bytes = obj
                    try:
                        result = await _verify_nonce_cache(bytes(nonce))
                    # TODO: catch specific exception
                    except:  # noqa: E722
                        result = False
                elif message_id == _SERVICE_CRYPTO_CHECK_ADDRESS_MAC:
                    assert len(obj) == 4
                    address_n: list[int] = obj[0]
                    mac: bytes = obj[1]
                    address_str: str = obj[2]
                    network: bytes | None = obj[3]
                    result = await _check_address_mac(
                        address_n, mac, address_str, network
                    )
                else:
                    die(DataError("Unknown crypto operation"))

            # TODO: catch specific exception
            except:  # noqa: E722
                result = False

            # Serialize and send the result back
            try:
                trezorcrypto_api.send_crypto_result(
                    result=result, ipc_cb=crypto_resp_cb
                )
            except Exception:
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
            # task.unload()
            return response

        elif service == _SERVICE_PROGRESS:
            obj = trezorui_api.deserialize_progress_message(data=bytes(msg.data))
            if message_id == _SERVICE_PROGRESS_INIT:
                # Initialize a progress context
                assert isinstance(obj, tuple)
                assert len(obj) == 4
                description: str | None = obj[0]
                title: str | None = obj[1]
                indeterminate: bool = obj[2]
                danger: bool = obj[3]
                progress_obj = progress(
                    description=description,
                    title=title,
                    indeterminate=indeterminate,
                    danger=danger,
                )
            elif message_id == _SERVICE_PROGRESS_REPORT:
                if progress_obj is None:
                    die(DataError("Progress not initialized"))
                # Report progress update
                assert isinstance(obj, tuple)
                assert len(obj) == 2
                description: str | None = obj[0]
                value: int = obj[1]
                progress_obj.report(value, description=description)
            elif message_id == _SERVICE_PROGRESS_STOP:
                if progress_obj is None:
                    die(DataError("Progress not initialized"))
                # Stop the progress context
                progress_obj.stop()
                progress_obj = None
            else:
                die(DataError("Unknown progress message ID"))

            # Serialize and send the result back
            try:
                io.ipc_send(
                    _SYSTASK_ID_EXTAPP,
                    fn_id(_SERVICE_PROGRESS, message_id),
                    b"",
                )
            except Exception:
                die(DataError("Failed to send progress result"))

        elif service == _SERVICE_WIRE_ERROR:
            err_message = (
                msg.data.decode("utf-8", "replace")
                if isinstance(msg.data, (bytes, bytearray))
                else str(msg.data)
            )
            code: FailureType = message_id
            response = Failure(code=code, message=err_message)
            ack = await context.call(response, ExtAppMessage)
            if ack.message_id > 0xFFFF:
                die(DataError("Invalid message ID."))
            io.ipc_send(
                _SYSTASK_ID_EXTAPP,
                fn_id(_SERVICE_WIRE_START, ack.message_id),
                ack.data,
            )

        else:
            die(RuntimeError("Unknown IPC function"))


async def _get_public_key(address_n: list[int]) -> str:
    from apps.common import coininfo, paths
    from apps.common.keychain import ForbiddenKeyPath, get_keychain

    coin = coininfo.by_name("Bitcoin")

    if address_n and address_n[0] == paths.SLIP25_PURPOSE:
        # UnlockPath is required to access SLIP25 paths.
        raise ForbiddenKeyPath()

    keychain = await get_keychain(coin.curve_name, [paths.AlwaysMatchingSchema])

    node = keychain.derive(address_n)
    assert coin.xpub_magic is not None
    node_xpub = node.serialize_public(coin.xpub_magic)
    return node_xpub


async def _ethereum_pubkeyhash(
    address_n: list[int], encoded_network: bytes | None, encoded_token: bytes | None
) -> bytes:
    from apps.ethereum.definitions import Definitions
    from apps.ethereum.keychain import (
        PATTERNS_ADDRESS,
        _schemas_from_network,
        _slip44_from_address_n,
    )

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
        _schemas_from_network,
        _slip44_from_address_n,
    )

    slip44 = _slip44_from_address_n(address_n)
    defs = Definitions.from_encoded(
        encoded_network=encoded_network, encoded_token=None, slip44=slip44
    )
    schemas = _schemas_from_network(PATTERNS_ADDRESS, defs.network)
    keychain = await get_keychain("secp256k1", schemas, [[b"SLIP-0024"]])

    slip44_id = address_n[1]  # it depends on the network (ETH vs ETC...)
    return get_address_mac(address, paths.unharden(slip44_id), address_n, keychain)


async def _check_address_mac(
    address_n: list[int], mac: bytes, address: str, encoded_network: bytes | None
) -> bool:
    from apps.common.address_mac import check_address_mac
    from apps.ethereum.keychain import (
        PATTERNS_ADDRESS,
        _schemas_from_network,
        _slip44_from_address_n,
    )

    slip44 = _slip44_from_address_n(address_n)
    defs = Definitions.from_encoded(
        encoded_network=encoded_network, encoded_token=None, slip44=slip44
    )
    schemas = _schemas_from_network(PATTERNS_ADDRESS, defs.network)
    keychain = await get_keychain("secp256k1", schemas, [[b"SLIP-0024"]])

    slip44_id = address_n[1]  # it depends on the network (ETH vs ETC...)

    try:
        check_address_mac(address, mac, paths.unharden(slip44_id), address_n, keychain)
    except DataError:
        return False
    return True


async def _sign_typed_hash(
    address_n: list[int],
    data_hash: bytes,
    encoded_network: bytes | None,
    encoded_token: bytes | None,
    chain_id: int | None,
) -> bytes:
    from trezor import TR
    from trezor.crypto.curve import secp256k1
    from trezor.ui.layouts.progress import progress

    from apps.ethereum.keychain import (
        PATTERNS_ADDRESS,
        _schemas_from_network,
        _slip44_from_address_n,
    )

    if chain_id is not None:
        defs = Definitions.from_encoded(
            encoded_network, encoded_token, chain_id=chain_id
        )
    else:
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


async def _verify_nonce_cache(nonce: bytes) -> bool:
    from storage.cache_common import APP_COMMON_NONCE

    result = context.cache_get(APP_COMMON_NONCE) == nonce

    if result:
        context.cache_delete(APP_COMMON_NONCE)

    return result
