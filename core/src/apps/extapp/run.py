from micropython import const
from typing import TYPE_CHECKING

import trezorcrypto_api
import trezorui_api
import ustruct  # pyright: ignore[reportMissingImports]
from storage import cache_common as cc
from storage.cache import get_sessionless_cache
from trezor import app, io, loop, ui, workflow
from trezor.messages import ExtAppMessage, ExtAppResponse, Failure
from trezor.ui import ProgressLayout
from trezor.ui.layouts.progress import progress
from trezor.wire import context
from trezor.wire.errors import DataError

from apps.common import paths
from apps.common.keychain import Keychain, get_keychain
from apps.ethereum.definitions import Definitions

if __debug__:
    from trezor import log

if TYPE_CHECKING:
    from trezorio import IpcMessage
    from typing import Any, NoReturn

    from trezor.enums import ButtonRequestType

_SERVICE_WIRE_START = const(0)
_SERVICE_WIRE_CONTINUE = const(1)
_SERVICE_WIRE_END = const(2)
_SERVICE_WIRE_ERROR = const(3)
_SERVICE_UI = const(4)
_SERVICE_PROGRESS = const(5)
_SERVICE_CRYPTO = const(6)

# A UI message id packs an operation and a screen handle, so that a layout can
# outlive the answer it gave. The old UI API never opens a screen and always
# sends `_UI_OP_ONE_SHOT` with handle 0, so it is unaffected.
_UI_HANDLE_BITS = const(12)
_UI_HANDLE_MASK = const((1 << 12) - 1)

_UI_OP_ONE_SHOT = const(0)  # build, show, forget
_UI_OP_OPEN = const(1)  # build, show, keep under the handle
_UI_OP_REOPEN = const(2)  # show what is already held, without rebuilding
_UI_OP_CLOSE = const(3)  # drop what is held, show nothing

# An app nests only a few screens at a time; anything beyond this is a leak.
_UI_MAX_SCREENS = const(8)

_SERVICE_PROGRESS_INIT = const(0)
_SERVICE_PROGRESS_REPORT = const(1)
_SERVICE_PROGRESS_STOP = const(2)

_SERVICE_CRYPTO_GET_XPUB = const(0)
_SERVICE_CRYPTO_GET_PUBLIC_KEY = const(1)
_SERVICE_CRYPTO_SIGN_DIGEST = const(2)
_SERVICE_CRYPTO_SIGN_TYPED_HASH = const(3)
_SERVICE_CRYPTO_GET_ADDRESS_MAC = const(4)
_SERVICE_CRYPTO_CHECK_ADDRESS_MAC = const(5)
_SERVICE_CRYPTO_VERIFY_NONCE_CACHE = const(6)


def fn_id(service: int, message_id: int) -> int:
    return (service << 16) | (message_id & 0xFFFF)


def from_fn_id(fn_id: int) -> tuple[int, int]:
    return ((fn_id >> 16) & 0xFFFF, fn_id & 0xFFFF)


def from_ui_message_id(message_id: int) -> tuple[int, int]:
    """Split a UI message id into the operation and the screen handle."""
    return (message_id >> _UI_HANDLE_BITS, message_id & _UI_HANDLE_MASK)


async def _show_new_layout(
    layout_obj: Any, br_code: ButtonRequestType, br_name: str | None
) -> tuple[ui.Layout, Any]:
    """Show a freshly built layout, and wait for the answer.

    Returns the layout as well, so that a caller which means to show it again
    can keep it instead of paying for a second one.
    """
    # The body of `interact()`, unrolled because the layout itself is needed
    # and `interact()` only hands back the result.
    workflow.close_others()
    layout = ui.Layout(layout_obj)
    layout.start()
    if br_name is not None:
        layout.put_button_request((br_code, br_name))
    return layout, await layout.get_result()


async def _run_layout(layout: ui.Layout) -> Any:
    """Show a layout that is already built, and wait for the user to answer.

    The layout keeps whatever state it had — which page it was on, how far it
    was scrolled — because it is started again rather than constructed again.
    """
    # Same courtesy `interact()` does: nobody else should be drawing.
    workflow.close_others()
    # The user has seen this screen before, so it should return rather than
    # arrive.
    layout.should_resume = True
    layout.start()
    return await layout.get_result()


def _extract_slip44_id(patterns: list[str]) -> int:
    """Extract the app's SLIP-44 coin type from its allowed path patterns.

    Every pattern is expected to hard-code the same coin type as its second
    path component (e.g. `m/44'/60'/...`), so the value is derived from the
    patterns themselves instead of being passed in separately.
    """
    if not patterns:
        raise DataError("Expected at least one allowed path")

    slip44_id: int | None = None
    for pattern in patterns:
        component = pattern.split("/")[2]
        if component[-1] == "'":
            component = component[:-1]
        try:
            coin_type = int(component)
        except ValueError:
            raise DataError(f"Invalid coin type in path pattern: {pattern}")

        if slip44_id is None:
            slip44_id = coin_type
        elif slip44_id != coin_type:
            raise DataError("Expected the same coin type in every allowed path")

    assert slip44_id is not None
    return slip44_id


async def run(request: ExtAppMessage) -> ExtAppResponse:
    if request.message_id > 0xFFFF:
        raise DataError("Invalid message ID.")

    instance_ids = get_sessionless_cache().get(cc.APP_EXTAPP_IDS)
    if instance_ids is None:
        raise DataError(f"Invalid instance ID: {request.instance_id}")
    image_handle, instance_id = ustruct.unpack("<II", instance_ids)
    if instance_id != request.instance_id:
        raise DataError(f"Invalid instance ID: {request.instance_id}")

    image = app.image_by_handle(image_handle)

    curves: list[str] = list(image.allowed_curves())
    if len(curves) != 1:
        raise DataError("Expected exactly one allowed curve")
    curve = curves[0]

    patterns: list[str] = list(image.allowed_paths())
    slip44_id: int = _extract_slip44_id(patterns)

    if __debug__:
        log.debug(
            __name__,
            f"Allowed curves: {curves}, slip44_id: {slip44_id}, patterns: {patterns}",
        )
    schemas = []
    for pattern in patterns:
        schemas.append(paths.PathSchema.parse(pattern, slip44_id))
    schemas: list[paths.PathSchema] = [s.copy() for s in schemas]

    if not image.is_running():
        if __debug__:
            log.error(__name__, f"Task not running: {request.instance_id}")
        raise DataError(f"Task not running: {request.instance_id}")

    def die(exception: Exception) -> NoReturn:
        if __debug__:
            log.error(__name__, f"Task died due to exception: {exception}")
        image.stop()  # TODO or image.delete ???
        raise exception

    task_id = image.task_id()

    try:
        if __debug__:
            log.debug(__name__, f"Sending wire start IPC message: {request.message_id}")
        io.ipc_send(
            task_id,
            fn_id(_SERVICE_WIRE_START, request.message_id),
            request.data,
        )
    except Exception as e:
        if __debug__:
            log.error(__name__, "Failed to send IPC message")
        die(DataError(f"Failed to send IPC message: {e}"))

    progress_obj: ProgressLayout | None = None
    # Layouts the app asked to keep, so that showing one again does not build a
    # second copy of it. Emptied when the task ends, with the task's memory.
    screens: dict[int, ui.Layout] = {}

    def crypto_resp_cb(data: bytes) -> None:
        log.debug(__name__, "Sending crypto result")
        io.ipc_send(task_id, fn_id(_SERVICE_CRYPTO, 0), data)

    def ui_resp_cb(data: bytes) -> None:
        io.ipc_send(task_id, fn_id(_SERVICE_UI, 0), data)

    while True:
        if not image.is_running():
            raise DataError(f"Task stopped: {request.instance_id}")
        try:
            msg: IpcMessage = await loop.wait(
                io.IPC2_EVENT | io.POLL_READ, timeout_ms=1000
            )
        except loop.Timeout:
            die(DataError("Timeout waiting for message"))

        service, message_id = from_fn_id(msg.fn)

        if service == _SERVICE_UI:
            op, handle = from_ui_message_id(message_id)

            if op == _UI_OP_CLOSE:
                # Nothing is shown; the app is only saying it is done with the
                # screen. Answering keeps the app's blocking call symmetric.
                screens.pop(handle, None)
                result = trezorui_api.CANCELLED
            elif op == _UI_OP_REOPEN and handle in screens:
                result = await _run_layout(screens[handle])
            else:
                # Either a fresh screen, or a reopen of one we no longer hold —
                # in which case the app sent the payload again precisely so it
                # can be rebuilt rather than fail.
                try:
                    layout_obj, br_code, br_name = trezorui_api.process_ipc_message(
                        data=bytes(msg.data)
                    )
                except Exception as e:
                    # The request cannot be drawn. Answering would leave the app
                    # waiting on a screen that never existed, so the app stops.
                    die(DataError(f"Cannot show the app's screen: {e}"))
                layout, result = await _show_new_layout(layout_obj, br_code, br_name)
                if op != _UI_OP_ONE_SHOT:
                    if handle not in screens and len(screens) >= _UI_MAX_SCREENS:
                        die(DataError("Too many open screens"))
                    screens[handle] = layout

            log.debug(__name__, f"UI interaction result: {result}")
            # Serialize and send the result back
            try:
                trezorui_api.send_ui_result(result=result, ipc_cb=ui_resp_cb)
            except Exception as e:
                die(DataError(f"Cannot send the screen's result: {e}"))

        elif service == _SERVICE_CRYPTO:
            try:
                if __debug__:
                    log.debug(__name__, "Processing crypto message")
                obj = trezorcrypto_api.deserialize_crypto_message(data=bytes(msg.data))

                if message_id == _SERVICE_CRYPTO_GET_XPUB:
                    assert len(obj) == 2
                    address_n: list[int] = obj[0]
                    xpub_magic: int = obj[1]
                    try:
                        if __debug__:
                            log.debug(
                                __name__,
                                f"Getting xpub for path: {address_n}, xpub_magic: {xpub_magic}",
                            )
                        keychain = await get_keychain(
                            curve, [paths.AlwaysMatchingSchema]
                        )
                        result = await _get_xpub(address_n, keychain, xpub_magic)
                    except Exception:
                        if __debug__:
                            log.error(__name__, "Failed to get xpub")
                        result = False

                elif message_id == _SERVICE_CRYPTO_GET_PUBLIC_KEY:
                    assert len(obj) == 2
                    address_n: list[int] = obj[0]
                    compressed: bool = obj[1]
                    try:
                        if __debug__:
                            log.debug(
                                __name__,
                                "Deriving keychain",
                            )
                        keychain = await get_keychain(
                            curve, [paths.AlwaysMatchingSchema]
                        )
                        if __debug__:
                            log.debug(
                                __name__,
                                f"Getting public key bytes for path: {address_n} compressed={compressed}",
                            )
                        result = [
                            0,
                            await _get_public_key(
                                address_n, compressed, keychain, curve
                            ),
                        ]
                        if __debug__:
                            log.debug(
                                __name__,
                                f"Result: {len(result[1])} bytes",
                            )
                    except Exception as e:
                        if __debug__:
                            log.error(
                                __name__,
                                f"Failed to get public key bytes due to exception: {e}",
                            )
                        result = False

                elif message_id == _SERVICE_CRYPTO_SIGN_DIGEST:
                    assert len(obj) == 3
                    address_n: list[int] = obj[0]
                    digest: bytes = obj[1]
                    compressed: bool = obj[2]
                    try:
                        if __debug__:
                            log.debug(__name__, f"Signing digest for path: {address_n}")
                        keychain = await get_keychain(curve, schemas, [[b"SLIP-0024"]])
                        result = await _sign_digest(
                            address_n, digest, compressed, keychain, curve
                        )

                    except Exception:
                        log.error(__name__, "Failed to sign digest")
                        result = False

                elif message_id == _SERVICE_CRYPTO_SIGN_TYPED_HASH:
                    assert len(obj) == 6
                    address_n: list[int] = obj[0]
                    data_hash: bytes = obj[1]
                    encoded_network: bytes | None = obj[2]
                    encoded_token: bytes | None = obj[3]
                    chain_id: int | None = obj[4]
                    show_progress: bool = obj[5]
                    try:
                        if __debug__:
                            log.debug(
                                __name__, f"Signing typed hash for path: {address_n}"
                            )
                        keychain = None
                        if (
                            encoded_network is None
                            and encoded_token is None
                            and chain_id is None
                        ):
                            keychain = await get_keychain(curve, schemas)
                        result = await _sign_typed_hash(
                            address_n,
                            data_hash,
                            keychain,
                            encoded_network,
                            encoded_token,
                            chain_id,
                            show_progress,
                        )

                    except Exception:
                        log.error(__name__, "Failed to sign typed hash")
                        result = False

                elif message_id == _SERVICE_CRYPTO_GET_ADDRESS_MAC:
                    assert len(obj) == 2
                    address_n: list[int] = obj[0]
                    address_str: str = obj[1]
                    try:
                        if __debug__:
                            log.debug(
                                __name__, f"Getting address MAC for path: {address_n}"
                            )
                        keychain = await get_keychain(curve, schemas, [[b"SLIP-0024"]])
                        await paths.validate_path(keychain, address_n)
                        from apps.common.address_mac import get_address_mac

                        result = get_address_mac(
                            address_str, paths.unharden(slip44_id), address_n, keychain
                        )
                    except Exception:
                        log.error(__name__, "Failed to get address MAC")
                        result = False
                elif message_id == _SERVICE_CRYPTO_CHECK_ADDRESS_MAC:
                    assert len(obj) == 3
                    address_n: list[int] = obj[0]
                    mac: bytes = obj[1]
                    address_str: str = obj[2]
                    try:
                        if __debug__:
                            log.debug(
                                __name__, f"Checking address MAC for path: {address_n}"
                            )
                        keychain = await get_keychain(curve, schemas, [[b"SLIP-0024"]])
                        await paths.validate_path(keychain, address_n)
                        from apps.common.address_mac import check_address_mac

                        check_address_mac(
                            address_str,
                            mac,
                            paths.unharden(slip44_id),
                            address_n,
                            keychain,
                        )
                        result = True
                    except Exception:
                        log.error(__name__, "Failed to check address MAC")
                        result = False
                elif message_id == _SERVICE_CRYPTO_VERIFY_NONCE_CACHE:
                    nonce: bytes = obj
                    try:
                        if __debug__:
                            log.debug(
                                __name__, f"Verifying nonce cache for nonce: {nonce}"
                            )
                        result = await _verify_nonce_cache(bytes(nonce))
                    except Exception:
                        log.error(__name__, "Failed to verify nonce cache")
                        result = False

                else:
                    log.error(__name__, f"Unknown crypto operation: {message_id}")
                    die(DataError("Unknown crypto operation"))

            except Exception:
                log.error(__name__, "Failed to process crypto message")
                result = False

            # Serialize and send the result back
            try:
                if __debug__:
                    log.debug(__name__, "Serializing crypto result")
                trezorcrypto_api.send_crypto_result(
                    result=result, ipc_cb=crypto_resp_cb
                )
            except Exception:
                if __debug__:
                    log.error(__name__, "Failed to serialize or send crypto result")
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
                task_id,
                fn_id(_SERVICE_WIRE_CONTINUE, ack.message_id),
                ack.data,
            )

        elif service == _SERVICE_WIRE_END:
            if __debug__:
                log.debug(__name__, f"Forwarding wire end message: {message_id}")
            # usb final message
            response = ExtAppResponse(
                message_id=message_id, data=msg.data, finished=True
            )
            if __debug__:
                log.info(__name__, "Ending extapp run function")
            return response

        elif service == _SERVICE_PROGRESS:
            if __debug__:
                log.debug(__name__, f"Processing progress message: {message_id}")
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
                    task_id,
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
            if __debug__:
                log.debug(__name__, f"Received wire error message: {err_message}")
            response = Failure(
                code=message_id,  # pyright: ignore [reportArgumentType]
                message=err_message,
            )
            ack = await context.call(response, ExtAppMessage)
            if ack.message_id > 0xFFFF:
                die(DataError("Invalid message ID."))
            io.ipc_send(
                task_id,
                fn_id(_SERVICE_WIRE_START, ack.message_id),
                ack.data,
            )

        else:
            if __debug__:
                log.error(
                    __name__,
                    f"Unknown IPC function: service={service}, message_id={message_id}",
                )
            die(RuntimeError("Unknown IPC function"))


async def _get_xpub(address_n: list[int], keychain: Keychain, xpub_magic: int) -> str:
    from apps.common import paths
    from apps.common.keychain import ForbiddenKeyPath

    if address_n and address_n[0] == paths.SLIP25_PURPOSE:
        # UnlockPath is required to access SLIP25 paths.
        log.error(__name__, "Forbidden key path: SLIP25 purpose detected")
        raise ForbiddenKeyPath()

    node = keychain.derive(address_n)
    node_xpub = node.serialize_public(xpub_magic)
    return node_xpub


async def _get_public_key(
    address_n: list[int], compressed: bool, keychain: Keychain, curve_name: str
) -> bytes:
    from apps.common import paths
    from apps.common.keychain import ForbiddenKeyPath

    if address_n and address_n[0] == paths.SLIP25_PURPOSE:
        # UnlockPath is required to access SLIP25 paths.
        log.error(__name__, "Forbidden key path: SLIP25 purpose detected")
        raise ForbiddenKeyPath()

    log.debug(__name__, f"Deriving keychain for path: {address_n}")
    node = keychain.derive(address_n)

    if curve_name == "secp256k1":
        from trezor.crypto.curve import secp256k1

        log.debug(
            __name__,
            f"Getting secp256k1 public key bytes for path: {address_n} compressed={compressed}",
        )
        return secp256k1.publickey(node.private_key(), compressed)
    elif curve_name == "nist256p1":
        from trezor.crypto.curve import nist256p1

        return nist256p1.publickey(node.private_key(), compressed)
    elif curve_name == "ed25519":
        from trezor.crypto.curve import ed25519

        return ed25519.publickey(node.private_key())
    elif curve_name == "curve25519":
        from trezor.crypto.curve import curve25519

        return curve25519.publickey(node.private_key())
    elif curve_name == "bip340":
        from trezor.crypto.curve import bip340

        return bip340.publickey(node.private_key())
    else:
        raise DataError(f"Unsupported curve: {curve_name}")


async def _sign_digest(
    address_n: list[int],
    digest: bytes,
    compressed: bool,
    keychain: Keychain,
    curve_name: str,
) -> bytes:

    await paths.validate_path(keychain, address_n)
    node = keychain.derive(address_n)

    if curve_name == "secp256k1":
        from trezor.crypto.curve import secp256k1

        return secp256k1.sign(node.private_key(), digest, compressed)
    elif curve_name == "nist256p1":
        from trezor.crypto.curve import nist256p1

        return nist256p1.sign(node.private_key(), digest, compressed)
    elif curve_name == "ed25519":
        from trezor.crypto.curve import ed25519

        return ed25519.sign(node.private_key(), digest)
    elif curve_name == "bip340":
        from trezor.crypto.curve import bip340

        return bip340.sign(node.private_key(), digest)
    else:
        raise DataError(f"Unsupported curve: {curve_name} for signing digest")


async def _sign_typed_hash(
    address_n: list[int],
    data_hash: bytes,
    keychain: Keychain | None,
    encoded_network: bytes | None,
    encoded_token: bytes | None,
    chain_id: int | None,
    show_progress: bool,
) -> bytes:
    from trezor import TR
    from trezor.crypto.curve import secp256k1
    from trezor.ui.layouts.progress import progress

    if keychain is None:
        from apps.ethereum.keychain import (
            PATTERNS_ADDRESS,
            _schemas_from_network,
            _slip44_from_address_n,
        )

        if chain_id is not None:
            if __debug__:
                log.debug(
                    __name__,
                    f"Getting definitions from encoded network and token for chain_id: {chain_id}",
                )
            defs = Definitions.from_encoded(
                encoded_network, encoded_token, chain_id=chain_id
            )
        else:
            slip44 = _slip44_from_address_n(address_n)
            defs = Definitions.from_encoded(
                encoded_network, encoded_token, slip44=slip44
            )
        schemas = _schemas_from_network(PATTERNS_ADDRESS, defs.network)
        keychain = await get_keychain("secp256k1", schemas, [[b"SLIP-0024"]])

    await paths.validate_path(keychain, address_n)

    node = keychain.derive(address_n)
    if show_progress:
        progress_obj = progress(title=TR.progress__signing_transaction)
        progress_obj.report(600)
    signature = secp256k1.sign(
        node.private_key(),
        data_hash,
        False,
        secp256k1.CANONICAL_SIG_ETHEREUM,
    )
    if show_progress:
        progress_obj.stop()
    return signature


async def _verify_nonce_cache(nonce: bytes) -> bool:
    from storage.cache_common import APP_COMMON_NONCE

    result = context.cache_get(APP_COMMON_NONCE) == nonce

    if result:
        context.cache_delete(APP_COMMON_NONCE)

    return result
