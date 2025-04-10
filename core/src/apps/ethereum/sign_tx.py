from typing import TYPE_CHECKING

from trezor.crypto import rlp
from trezor.messages import EthereumTxRequest
from trezor.utils import BufferReader
from trezor.wire import DataError

from apps.ethereum import sc_constants as constants

from .helpers import address_from_bytes, bytes_from_address
from .keychain import with_keychain_from_chain_id

if TYPE_CHECKING:
    from typing import Iterable

    from trezor.messages import (
        EthereumNetworkInfo,
        EthereumSignTx,
        EthereumTokenInfo,
        EthereumTxAck,
    )

    from apps.common.keychain import Keychain
    from apps.common.payment_request import PaymentRequestVerifier

    from .definitions import Definitions
    from .keychain import MsgInSignTx


# Maximum chain_id which returns the full signature_v (which must fit into an uint32).
# chain_ids larger than this will only return one bit and the caller must recalculate
# the full value: v = 2 * chain_id + 35 + v_bit
MAX_CHAIN_ID = (0xFFFF_FFFF - 36) // 2


@with_keychain_from_chain_id
async def sign_tx(
    msg: EthereumSignTx,
    keychain: Keychain,
    defs: Definitions,
) -> EthereumTxRequest:
    from trezor import TR
    from trezor.crypto.hashlib import sha3_256
    from trezor.ui.layouts import show_continue_in_app
    from trezor.ui.layouts.progress import progress
    from trezor.utils import HashWriter

    from apps.common import paths

    from .helpers import format_ethereum_amount, get_fee_items_regular

    data_total = msg.data_length  # local_cache_attribute

    # check
    if msg.tx_type not in [1, 6, None]:
        raise DataError("tx_type out of bounds")
    if len(msg.gas_price) + len(msg.gas_limit) > 30:
        raise DataError("Fee overflow")
    check_common_fields(msg)

    # have the user confirm signing
    await paths.validate_path(keychain, msg.address_n)
    address_bytes = bytes_from_address(msg.to)
    gas_price = int.from_bytes(msg.gas_price, "big")
    gas_limit = int.from_bytes(msg.gas_limit, "big")
    maximum_fee = format_ethereum_amount(gas_price * gas_limit, None, defs.network)
    fee_items = get_fee_items_regular(
        gas_price,
        gas_limit,
        defs.network,
    )

    payment_req_verifier = None
    if msg.payment_req:
        from apps.common.payment_request import PaymentRequestVerifier

        slip44_id = paths.unharden(msg.address_n[1])
        payment_req_verifier = PaymentRequestVerifier(
            msg.payment_req, slip44_id, keychain
        )

    await confirm_tx_data(
        msg,
        defs,
        address_bytes,
        maximum_fee,
        fee_items,
        data_total,
        payment_req_verifier,
    )

    progress_obj = progress(title=TR.progress__signing_transaction)
    progress_obj.report(30)

    # sign
    data = bytearray()
    data += msg.data_initial_chunk
    data_left = data_total - len(msg.data_initial_chunk)

    total_length = _get_total_length(msg, data_total)

    sha = HashWriter(sha3_256(keccak=True))
    rlp.write_header(sha, total_length, rlp.LIST_HEADER_BYTE)

    if msg.tx_type is not None:
        rlp.write(sha, msg.tx_type)

    for field in (msg.nonce, msg.gas_price, msg.gas_limit, address_bytes, msg.value):
        rlp.write(sha, field)

    if data_left == 0:
        rlp.write(sha, data)
    else:
        rlp.write_header(sha, data_total, rlp.STRING_HEADER_BYTE, data)
        sha.extend(data)

    progress_obj.report(60)

    while data_left > 0:
        resp = await send_request_chunk(data_left)
        data_left -= len(resp.data_chunk)
        sha.extend(resp.data_chunk)

    # eip 155 replay protection
    rlp.write(sha, msg.chain_id)
    rlp.write(sha, 0)
    rlp.write(sha, 0)

    digest = sha.get_digest()
    result = _sign_digest(msg, keychain, digest)

    progress_obj.stop()

    show_continue_in_app(TR.send__transaction_signed)
    return result


async def confirm_tx_data(
    msg: MsgInSignTx,
    defs: Definitions,
    address_bytes: bytes,
    maximum_fee: str,
    fee_items: Iterable[tuple[str, str]],
    data_total_len: int,
    payment_req_verifier: PaymentRequestVerifier | None,
) -> None:
    # function distinguishes between staking / smart contracts / regular transactions
    from .layout import (
        require_confirm_approve,
        require_confirm_other_data,
        require_confirm_tx,
    )

    if await handle_staking(msg, defs.network, address_bytes, maximum_fee, fee_items):
        return

    # Handle ERC-20 known functions
    token, token_address, func_sig, recipient, value = await _handle_erc20(
        msg, defs, address_bytes
    )

    if func_sig == constants.SC_FUNC_SIG_APPROVE:
        assert token
        assert token_address

        if payment_req_verifier is not None:
            raise DataError("Payment Requests not supported for the APPROVE call")

        await require_confirm_approve(
            recipient,
            value,
            msg.address_n,
            maximum_fee,
            fee_items,
            msg.chain_id,
            defs.network,
            token,
            token_address,
            chunkify=bool(msg.chunkify),
        )
    else:
        assert func_sig == constants.SC_FUNC_SIG_TRANSFER or func_sig is None
        assert value is not None

        recipient_str = (
            address_from_bytes(recipient, defs.network) if recipient else None
        )
        if payment_req_verifier is not None:
            # If a payment_req_verifier is provided, then msg.payment_req must have been set.
            assert msg.payment_req is not None
            payment_req_verifier.add_output(value, recipient_str or "")
            payment_req_verifier.verify()
            recipient_str = msg.payment_req.recipient_name

        is_contract_interaction = token is None and data_total_len > 0

        if is_contract_interaction:
            await require_confirm_other_data(msg.data_initial_chunk, data_total_len)

        await require_confirm_tx(
            recipient_str,
            value,
            msg.address_n,
            maximum_fee,
            fee_items,
            defs.network,
            token,
            is_contract_interaction=is_contract_interaction,
            chunkify=bool(msg.chunkify),
        )


async def handle_staking(
    msg: MsgInSignTx,
    network: EthereumNetworkInfo,
    address_bytes: bytes,
    maximum_fee: str,
    fee_items: Iterable[tuple[str, str]],
) -> bool:

    data_reader = BufferReader(msg.data_initial_chunk)
    if data_reader.remaining_count() < constants.SC_FUNC_SIG_BYTES:
        return False

    func_sig = data_reader.read_memoryview(constants.SC_FUNC_SIG_BYTES)
    if address_bytes in constants.ADDRESSES_POOL:
        if func_sig == constants.SC_FUNC_SIG_STAKE:
            await _handle_staking_tx_stake(
                data_reader, msg, network, address_bytes, maximum_fee, fee_items
            )
            return True
        if func_sig == constants.SC_FUNC_SIG_UNSTAKE:
            await _handle_staking_tx_unstake(
                data_reader, msg, network, address_bytes, maximum_fee, fee_items
            )
            return True

    if address_bytes in constants.ADDRESSES_ACCOUNTING:
        if func_sig == constants.SC_FUNC_SIG_CLAIM:
            await _handle_staking_tx_claim(
                data_reader,
                msg,
                address_bytes,
                maximum_fee,
                fee_items,
                network,
                bool(msg.chunkify),
            )
            return True

    # data not corresponding to staking transaction
    return False


async def _handle_erc20(
    msg: MsgInSignTx,
    definitions: Definitions,
    address_bytes: bytes,
) -> tuple[EthereumTokenInfo | None, bytes | None, bytes | None, bytes, int | None]:
    from trezor import TR
    from trezor.ui.layouts import ethereum_address_title

    from . import tokens
    from .layout import require_confirm_address, require_confirm_unknown_token

    # local_cache_attribute
    data_initial_chunk = msg.data_initial_chunk
    SC_FUNC_SIG_BYTES = constants.SC_FUNC_SIG_BYTES
    SC_ARGUMENT_BYTES = constants.SC_ARGUMENT_BYTES
    SC_ARGUMENT_ADDRESS_BYTES = constants.SC_ARGUMENT_ADDRESS_BYTES
    SC_FUNC_SIG_APPROVE = constants.SC_FUNC_SIG_APPROVE
    SC_FUNC_SIG_TRANSFER = constants.SC_FUNC_SIG_TRANSFER
    REVOKE_AMOUNT = constants.SC_FUNC_APPROVE_REVOKE_AMOUNT

    token = None
    token_address = None
    func_sig = None
    recipient = address_bytes
    value = int.from_bytes(msg.value, "big")
    if (
        len(msg.to) in (40, 42)
        and len(msg.value) == 0
        and msg.data_length == 68
        and len(data_initial_chunk) == 68
    ):
        data_reader = BufferReader(data_initial_chunk)
        if data_reader.remaining_count() < SC_FUNC_SIG_BYTES:
            return token, token_address, func_sig, recipient, value

        func_sig = data_reader.read_memoryview(SC_FUNC_SIG_BYTES)
        if func_sig in (SC_FUNC_SIG_TRANSFER, SC_FUNC_SIG_APPROVE):
            # The two functions happen to have the exact same parameters, so we treat them together.
            # This will need to be made into a more generic solution eventually.

            # arg0: address, Address, 20 bytes (left padded with zeroes)
            # arg1: value, uint256, 32 bytes
            if data_reader.remaining_count() < SC_ARGUMENT_BYTES * 2:
                return token, token_address, None, recipient, value
            arg0 = data_reader.read_memoryview(SC_ARGUMENT_BYTES)
            assert all(
                byte == 0
                for byte in arg0[: SC_ARGUMENT_BYTES - SC_ARGUMENT_ADDRESS_BYTES]
            )
            recipient = bytes(arg0[SC_ARGUMENT_BYTES - SC_ARGUMENT_ADDRESS_BYTES :])
            arg1 = data_reader.read_memoryview(SC_ARGUMENT_BYTES)
            if func_sig == SC_FUNC_SIG_APPROVE and all(byte == 255 for byte in arg1):
                # "Unlimited" approval (all bits set) is a special case
                # which we encode as value=None internally.
                value = None
            else:
                value = int.from_bytes(arg1, "big")

        token = definitions.get_token(address_bytes)
        token_address = address_bytes

        if token is tokens.UNKNOWN_TOKEN:
            if func_sig == SC_FUNC_SIG_APPROVE:
                if value == REVOKE_AMOUNT:
                    title = TR.ethereum__approve_intro_title_revoke
                else:
                    title = TR.ethereum__approve_intro_title
            else:
                title = ethereum_address_title()
            await require_confirm_unknown_token(title)
            if func_sig != SC_FUNC_SIG_APPROVE:
                # For unknown tokens we also show the token address immediately after the warning
                # except in the case of the "approve" flow which shows the token address later on!
                await require_confirm_address(
                    address_bytes,
                    ethereum_address_title(),
                    TR.ethereum__token_contract,
                    TR.buttons__continue,
                    "unknown_token",
                    TR.ethereum__unknown_contract_address,
                )

    return token, token_address, func_sig, recipient, value


def _get_total_length(msg: EthereumSignTx, data_total: int) -> int:
    length = 0
    if msg.tx_type is not None:
        length += rlp.length(msg.tx_type)

    fields: tuple[rlp.RLPItem, ...] = (
        msg.nonce,
        msg.gas_price,
        msg.gas_limit,
        bytes_from_address(msg.to),
        msg.value,
        msg.chain_id,
        0,
        0,
    )

    for field in fields:
        length += rlp.length(field)

    length += rlp.header_length(data_total, msg.data_initial_chunk)
    length += data_total

    return length


async def send_request_chunk(data_left: int) -> EthereumTxAck:
    from trezor.messages import EthereumTxAck
    from trezor.wire.context import call

    # TODO: layoutProgress ?
    req = EthereumTxRequest()
    req.data_length = min(data_left, 1024)
    return await call(req, EthereumTxAck)


def _sign_digest(
    msg: EthereumSignTx, keychain: Keychain, digest: bytes
) -> EthereumTxRequest:
    from trezor.crypto.curve import secp256k1

    node = keychain.derive(msg.address_n)
    signature = secp256k1.sign(
        node.private_key(), digest, False, secp256k1.CANONICAL_SIG_ETHEREUM
    )

    req = EthereumTxRequest()
    req.signature_v = signature[0]
    if msg.chain_id > MAX_CHAIN_ID:
        req.signature_v -= 27
    else:
        req.signature_v += 2 * msg.chain_id + 8

    req.signature_r = signature[1:33]
    req.signature_s = signature[33:]

    return req


def check_common_fields(msg: MsgInSignTx) -> None:
    data_length = msg.data_length  # local_cache_attribute

    if data_length > 0:
        if not msg.data_initial_chunk:
            raise DataError("Data length provided, but no initial chunk")
        # Our encoding only supports transactions up to 2^24 bytes. To
        # prevent exceeding the limit we use a stricter limit on data length.
        if data_length > 16_000_000:
            raise DataError("Data length exceeds limit")
        if len(msg.data_initial_chunk) > data_length:
            raise DataError("Invalid size of initial chunk")

    if len(msg.to) not in (0, 40, 42):
        raise DataError("Invalid recipient address")

    if not msg.to and data_length == 0:
        # sending transaction to address 0 (contract creation) without a data field
        raise DataError("Contract creation without data")

    if msg.chain_id == 0:
        raise DataError("Chain ID out of bounds")


async def _handle_staking_tx_stake(
    data_reader: BufferReader,
    msg: MsgInSignTx,
    network: EthereumNetworkInfo,
    address_bytes: bytes,
    maximum_fee: str,
    fee_items: Iterable[tuple[str, str]],
) -> None:
    from .layout import require_confirm_stake

    # stake args:
    # - arg0: uint64, source (should be 1)
    try:
        source = int.from_bytes(
            data_reader.read_memoryview(constants.SC_ARGUMENT_BYTES), "big"
        )
        if source != 1:
            raise ValueError  # wrong value of 1st argument ('source' should be 1)
        if data_reader.remaining_count() != 0:
            raise ValueError  # wrong number of arguments for stake (should be 1)
    except (ValueError, EOFError):
        raise DataError("Invalid staking transaction call")

    await require_confirm_stake(
        address_bytes,
        int.from_bytes(msg.value, "big"),
        msg.address_n,
        maximum_fee,
        fee_items,
        network,
        bool(msg.chunkify),
    )


async def _handle_staking_tx_unstake(
    data_reader: BufferReader,
    msg: MsgInSignTx,
    network: EthereumNetworkInfo,
    address_bytes: bytes,
    maximum_fee: str,
    fee_items: Iterable[tuple[str, str]],
) -> None:
    from .layout import require_confirm_unstake

    # unstake args:
    # - arg0: uint256, value
    # - arg1:  uint16, isAllowedInterchange (bool)
    # - arg2: uint64, source, should be 1
    try:
        value = int.from_bytes(
            data_reader.read_memoryview(constants.SC_ARGUMENT_BYTES), "big"
        )
        _ = data_reader.read_memoryview(constants.SC_ARGUMENT_BYTES)  # skip arg1
        source = int.from_bytes(
            data_reader.read_memoryview(constants.SC_ARGUMENT_BYTES), "big"
        )
        if source != 1:
            raise ValueError  # wrong value of 3rd argument ('source' should be 1)
        if data_reader.remaining_count() != 0:
            raise ValueError  # wrong number of arguments for unstake (should be 3)
    except (ValueError, EOFError):
        raise DataError("Invalid staking transaction call")

    await require_confirm_unstake(
        address_bytes,
        value,
        msg.address_n,
        maximum_fee,
        fee_items,
        network,
        bool(msg.chunkify),
    )


async def _handle_staking_tx_claim(
    data_reader: BufferReader,
    msg: MsgInSignTx,
    staking_addr: bytes,
    maximum_fee: str,
    fee_items: Iterable[tuple[str, str]],
    network: EthereumNetworkInfo,
    chunkify: bool,
) -> None:
    from .layout import require_confirm_claim

    # claim has no args
    if data_reader.remaining_count() != 0:
        raise DataError("Invalid staking transaction call")

    await require_confirm_claim(
        staking_addr, msg.address_n, maximum_fee, fee_items, network, chunkify
    )
