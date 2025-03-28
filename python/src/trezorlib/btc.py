# This file is part of the Trezor project.
#
# Copyright (C) 2012-2022 SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

from __future__ import annotations

import warnings
from copy import copy
from decimal import Decimal
from typing import TYPE_CHECKING, Any, AnyStr, List, Optional, Sequence, Tuple

# TypedDict is not available in typing for python < 3.8
from typing_extensions import Protocol, TypedDict

from . import exceptions, messages
from .anti_exfil import AntiExfilSignature, commit_entropy, generate_entropy, verify
from .tools import _return_success, prepare_message_bytes, session

if TYPE_CHECKING:
    from .client import TrezorClient
    from .tools import Address

    class ScriptSig(TypedDict):
        asm: str
        hex: str

    class ScriptPubKey(TypedDict):
        asm: str
        hex: str
        type: str
        reqSigs: int
        addresses: List[str]

    class Vin(TypedDict):
        txid: str
        vout: int
        sequence: int
        coinbase: str
        scriptSig: "ScriptSig"
        txinwitness: List[str]

    class Vout(TypedDict):
        value: float
        int: int
        scriptPubKey: "ScriptPubKey"

    class Transaction(TypedDict):
        txid: str
        hash: str
        version: int
        size: int
        vsize: int
        weight: int
        locktime: int
        vin: List[Vin]
        vout: List[Vout]

    class TxCacheType(Protocol):
        def __getitem__(self, __key: bytes) -> messages.TransactionType: ...

        def __contains__(self, __key: bytes) -> bool: ...


def from_json(json_dict: "Transaction") -> messages.TransactionType:
    def make_input(vin: "Vin") -> messages.TxInputType:
        if "coinbase" in vin:
            return messages.TxInputType(
                prev_hash=b"\0" * 32,
                prev_index=0xFFFFFFFF,  # signed int -1
                script_sig=bytes.fromhex(vin["coinbase"]),
                sequence=vin["sequence"],
            )

        else:
            return messages.TxInputType(
                prev_hash=bytes.fromhex(vin["txid"]),
                prev_index=vin["vout"],
                script_sig=bytes.fromhex(vin["scriptSig"]["hex"]),
                sequence=vin["sequence"],
            )

    def make_bin_output(vout: "Vout") -> messages.TxOutputBinType:
        return messages.TxOutputBinType(
            amount=int(Decimal(vout["value"]) * (10**8)),
            script_pubkey=bytes.fromhex(vout["scriptPubKey"]["hex"]),
        )

    return messages.TransactionType(
        version=json_dict["version"],
        lock_time=json_dict.get("locktime", 0),
        inputs=[make_input(vin) for vin in json_dict["vin"]],
        bin_outputs=[make_bin_output(vout) for vout in json_dict["vout"]],
    )


def get_public_node(
    client: "TrezorClient",
    n: "Address",
    ecdsa_curve_name: Optional[str] = None,
    show_display: bool = False,
    coin_name: Optional[str] = None,
    script_type: messages.InputScriptType = messages.InputScriptType.SPENDADDRESS,
    ignore_xpub_magic: bool = False,
    unlock_path: Optional[List[int]] = None,
    unlock_path_mac: Optional[bytes] = None,
) -> messages.PublicKey:
    if unlock_path:
        client.call(
            messages.UnlockPath(address_n=unlock_path, mac=unlock_path_mac),
            expect=messages.UnlockedPathRequest,
        )

    return client.call(
        messages.GetPublicKey(
            address_n=n,
            ecdsa_curve_name=ecdsa_curve_name,
            show_display=show_display,
            coin_name=coin_name,
            script_type=script_type,
            ignore_xpub_magic=ignore_xpub_magic,
        ),
        expect=messages.PublicKey,
    )


def get_address(*args: Any, **kwargs: Any) -> str:
    return get_authenticated_address(*args, **kwargs).address


def get_authenticated_address(
    client: "TrezorClient",
    coin_name: str,
    n: "Address",
    show_display: bool = False,
    multisig: Optional[messages.MultisigRedeemScriptType] = None,
    script_type: messages.InputScriptType = messages.InputScriptType.SPENDADDRESS,
    ignore_xpub_magic: bool = False,
    unlock_path: Optional[List[int]] = None,
    unlock_path_mac: Optional[bytes] = None,
    chunkify: bool = False,
) -> messages.Address:
    if unlock_path:
        client.call(
            messages.UnlockPath(address_n=unlock_path, mac=unlock_path_mac),
            expect=messages.UnlockedPathRequest,
        )

    return client.call(
        messages.GetAddress(
            address_n=n,
            coin_name=coin_name,
            show_display=show_display,
            multisig=multisig,
            script_type=script_type,
            ignore_xpub_magic=ignore_xpub_magic,
            chunkify=chunkify,
        ),
        expect=messages.Address,
    )


def get_ownership_id(
    client: "TrezorClient",
    coin_name: str,
    n: "Address",
    multisig: Optional[messages.MultisigRedeemScriptType] = None,
    script_type: messages.InputScriptType = messages.InputScriptType.SPENDADDRESS,
) -> bytes:
    return client.call(
        messages.GetOwnershipId(
            address_n=n,
            coin_name=coin_name,
            multisig=multisig,
            script_type=script_type,
        ),
        expect=messages.OwnershipId,
    ).ownership_id


def get_ownership_proof_common(
    client: "TrezorClient",
    coin_name: str,
    n: "Address",
    multisig: Optional[messages.MultisigRedeemScriptType],
    script_type: messages.InputScriptType,
    user_confirmation: bool,
    ownership_ids: Optional[List[bytes]],
    commitment_data: Optional[bytes],
    preauthorized: bool,
    use_anti_exfil: bool,
    entropy: Optional[bytes],
) -> Tuple[Optional[bytes], AntiExfilSignature]:
    if preauthorized:
        client.call(messages.DoPreauthorized(), expect=messages.PreauthorizedRequest)

    if not use_anti_exfil:
        res = client.call(
            messages.GetOwnershipProof(
                address_n=n,
                coin_name=coin_name,
                script_type=script_type,
                multisig=multisig,
                user_confirmation=user_confirmation,
                ownership_ids=ownership_ids,
                commitment_data=commitment_data,
            ),
            expect=messages.OwnershipProof,
        )
        assert res.ownership_proof != b""

        return res.ownership_proof, AntiExfilSignature(res.signature, None, None)
    else:
        if not entropy:
            entropy = generate_entropy()

        res = client.call(
            messages.GetOwnershipProof(
                address_n=n,
                coin_name=coin_name,
                script_type=script_type,
                multisig=multisig,
                user_confirmation=user_confirmation,
                ownership_ids=ownership_ids,
                commitment_data=commitment_data,
                entropy_commitment=commit_entropy(entropy),
            ),
            expect=messages.OwnershipProofNonceCommitment,
        )

        assert res.nonce_commitment is not None
        nonce_commitment = res.nonce_commitment

        res = client.call(
            messages.OwnershipProofEntropy(entropy=entropy),
            expect=messages.OwnershipProof,
        )

        # This function verifies that the signature includes the host's entropy and that its s value is less than half of the curve's order. However, it does not verify the signature itself, as trezorlib doesn't have the digest. The verification of the signature is the caller's responsibility.
        if not verify(
            None,
            res.signature,
            None,
            entropy,
            nonce_commitment,
        ):
            # This is a violation of the anti-exfil protocol.
            raise ValueError("Invalid signature")

        if res.ownership_proof != b"":
            # If host uses the anti-exfil protocol, it should not rely on device to serialize the ownwership proof correctly.
            raise ValueError("Ownership proof is not expected")
        return None, AntiExfilSignature(res.signature, entropy, nonce_commitment)


def get_ownership_proof(
    client: "TrezorClient",
    coin_name: str,
    n: "Address",
    multisig: Optional[messages.MultisigRedeemScriptType] = None,
    script_type: messages.InputScriptType = messages.InputScriptType.SPENDADDRESS,
    user_confirmation: bool = False,
    ownership_ids: Optional[List[bytes]] = None,
    commitment_data: Optional[bytes] = None,
    preauthorized: bool = False,
) -> Tuple[bytes, bytes]:
    ownership_proof, anti_exfil_signature = get_ownership_proof_common(
        client,
        coin_name,
        n,
        multisig,
        script_type,
        user_confirmation,
        ownership_ids,
        commitment_data,
        preauthorized,
        False,
        None,
    )
    assert ownership_proof is not None
    assert anti_exfil_signature.signature is not None
    return ownership_proof, anti_exfil_signature.signature


def get_ownership_proof_new(
    client: "TrezorClient",
    coin_name: str,
    n: "Address",
    multisig: Optional[messages.MultisigRedeemScriptType] = None,
    script_type: messages.InputScriptType = messages.InputScriptType.SPENDADDRESS,
    user_confirmation: bool = False,
    ownership_ids: Optional[List[bytes]] = None,
    commitment_data: Optional[bytes] = None,
    preauthorized: bool = False,
    use_anti_exfil: bool = True,
    entropy: Optional[bytes] = None,
) -> AntiExfilSignature:
    """
    If `use_anti_exfil` is set to `True`, the anti-exfilitration protocol will be
    used. The purpose of this protocol is to prevent the device from leaking
    its secrets through the signatures. In this case, `AntiExfilSignature` objects
    will have non-emtpy fields `entropy` and `nonce_commitment`. It's the caller
    responsibility to verify the signature and the nonce commitment. The caller
    can optionally provide a list of entropies to be used in the protocol. Ideally,
    the caller should provide the same list of entropies if the signing is repeated
    due to a error to prevent the device to perform nonce-grinding attacks.
    """
    ownership_proof, anti_exfil_signature = get_ownership_proof_common(
        client,
        coin_name,
        n,
        multisig,
        script_type,
        user_confirmation,
        ownership_ids,
        commitment_data,
        preauthorized,
        use_anti_exfil,
        entropy,
    )
    return anti_exfil_signature


def sign_message(
    client: "TrezorClient",
    coin_name: str,
    n: "Address",
    message: AnyStr,
    script_type: messages.InputScriptType = messages.InputScriptType.SPENDADDRESS,
    no_script_type: bool = False,
    chunkify: bool = False,
) -> messages.MessageSignature:
    return client.call(
        messages.SignMessage(
            coin_name=coin_name,
            address_n=n,
            message=prepare_message_bytes(message),
            script_type=script_type,
            no_script_type=no_script_type,
            chunkify=chunkify,
        ),
        expect=messages.MessageSignature,
    )


def verify_message(
    client: "TrezorClient",
    coin_name: str,
    address: str,
    signature: bytes,
    message: AnyStr,
    chunkify: bool = False,
) -> bool:
    try:
        client.call(
            messages.VerifyMessage(
                address=address,
                signature=signature,
                message=prepare_message_bytes(message),
                coin_name=coin_name,
                chunkify=chunkify,
            ),
            expect=messages.Success,
        )
        return True
    except exceptions.TrezorFailure:
        return False


@session
def sign_tx_common(
    client: "TrezorClient",
    coin_name: str,
    inputs: Sequence[messages.TxInputType],
    outputs: Sequence[messages.TxOutputType],
    details: Optional[messages.SignTx],
    prev_txes: Optional["TxCacheType"],
    payment_reqs: Sequence[messages.TxAckPaymentRequest],
    preauthorized: bool,
    unlock_path: Optional[List[int]],
    unlock_path_mac: Optional[bytes],
    use_anti_exfil: bool,
    entropy_list: Optional[List[bytes]],
    **kwargs: Any,
) -> Tuple[Sequence[Optional[AntiExfilSignature]], bytes]:
    if prev_txes is None:
        prev_txes = {}

    if details is not None:
        warnings.warn(
            "'details' argument is deprecated, use kwargs instead",
            DeprecationWarning,
            stacklevel=2,
        )
        signtx = details
        signtx.coin_name = coin_name
        signtx.inputs_count = len(inputs)
        signtx.outputs_count = len(outputs)

    else:
        signtx = messages.SignTx(
            coin_name=coin_name,
            inputs_count=len(inputs),
            outputs_count=len(outputs),
        )
        for name, value in kwargs.items():
            if hasattr(signtx, name):
                setattr(signtx, name, value)

    if unlock_path:
        client.call(
            messages.UnlockPath(address_n=unlock_path, mac=unlock_path_mac),
            expect=messages.UnlockedPathRequest,
        )
    elif preauthorized:
        client.call(messages.DoPreauthorized(), expect=messages.PreauthorizedRequest)

    res = client.call(signtx, expect=messages.TxRequest)

    # Prepare structure for signatures
    signatures: List[Optional[bytes]] = [None] * len(inputs)
    serialized_tx = b""

    def copy_tx_meta(tx: messages.TransactionType) -> messages.TransactionType:
        tx_copy = copy(tx)
        # clear fields
        tx_copy.inputs_cnt = len(tx.inputs)
        tx_copy.inputs = []
        tx_copy.outputs_cnt = len(tx.bin_outputs or tx.outputs)
        tx_copy.outputs = []
        tx_copy.bin_outputs = []
        tx_copy.extra_data_len = len(tx.extra_data or b"")
        tx_copy.extra_data = None
        return tx_copy

    this_tx = messages.TransactionType(
        inputs=inputs,
        outputs=outputs,
        inputs_cnt=len(inputs),
        outputs_cnt=len(outputs),
        # pick either kw-provided or default value from the SignTx request
        version=signtx.version,
    )

    R = messages.RequestType

    nonce_commitment_list: List[Optional[bytes]] = [None for _ in inputs]
    if use_anti_exfil and entropy_list is None:
        entropy_list = [generate_entropy() for _ in inputs]

    while True:
        # If there's some part of signed transaction, let's add it
        if res.serialized:
            if res.serialized.serialized_tx:
                if use_anti_exfil:
                    # If host uses the anti-exfil protocol, it should not rely on device to serialize the transaction correctly.
                    raise ValueError("Serialization is not expected")
                serialized_tx += res.serialized.serialized_tx

            if res.serialized.signature_index is not None:
                idx = res.serialized.signature_index
                sig = res.serialized.signature
                assert sig is not None
                if signatures[idx] is not None:
                    raise ValueError(f"Signature for index {idx} already filled")
                signatures[idx] = sig
                if use_anti_exfil:
                    assert entropy_list is not None
                    nonce_commitment = nonce_commitment_list[idx]
                    if nonce_commitment is None:
                        # Device provides a signature without commiting to the nonce before. This is a violation of the anti-exfil protocol.
                        raise ValueError(
                            f"Nonce commitment for index {idx} not provided"
                        )
                    # This function verifies that the signature includes the host's entropy and that its s value is less than half of the curve's order. However, it does not verify the signature itself, as trezorlib doesn't have the digest. The verification of the signature is the caller's responsibility.
                    if not verify(
                        None,
                        sig,
                        None,
                        entropy_list[idx],
                        nonce_commitment,
                    ):
                        # This is a violation of the anti-exfil protocol.
                        raise ValueError(f"Invalid signature for index {idx}")

        if res.request_type == R.TXFINISHED:
            break

        assert res.details is not None, "device did not provide details"

        # Device asked for one more information, let's process it.
        if res.details.tx_hash is not None:
            if res.details.tx_hash not in prev_txes:
                raise ValueError(
                    f"Previous transaction {res.details.tx_hash.hex()} not available"
                )
            current_tx = prev_txes[res.details.tx_hash]
        else:
            current_tx = this_tx

        if res.request_type == R.TXPAYMENTREQ:
            assert res.details.request_index is not None
            msg = payment_reqs[res.details.request_index]
            res = client.call(msg, expect=messages.TxRequest)
        else:
            msg = messages.TransactionType()
            if res.request_type == R.TXMETA:
                msg = copy_tx_meta(current_tx)
            elif res.request_type in (R.TXINPUT, R.TXORIGINPUT):
                assert res.details.request_index is not None
                idx = res.details.request_index
                msg.inputs = [current_tx.inputs[idx]]
                if use_anti_exfil:
                    assert entropy_list is not None
                    msg.inputs[0].entropy_commitment = commit_entropy(entropy_list[idx])
            elif use_anti_exfil and res.request_type == R.TXENTROPY:
                assert res.details.request_index is not None
                idx = res.details.request_index
                nonce_commitment = res.details.nonce_commitment
                nonce_commitment_list[idx] = nonce_commitment
                if nonce_commitment is None:
                    # Device requests an entropy without commiting to the nonce before. This is a violation of the anti-exfil protocol.
                    raise ValueError(f"Nonce commitment for index {idx} not provided")
                assert entropy_list is not None
                msg.entropy = messages.TxEntropyType(entropy=entropy_list[idx])
            elif res.request_type == R.TXOUTPUT:
                assert res.details.request_index is not None
                if res.details.tx_hash:
                    msg.bin_outputs = [
                        current_tx.bin_outputs[res.details.request_index]
                    ]
                else:
                    msg.outputs = [current_tx.outputs[res.details.request_index]]
            elif res.request_type == R.TXORIGOUTPUT:
                assert res.details.request_index is not None
                msg.outputs = [current_tx.outputs[res.details.request_index]]
            elif res.request_type == R.TXEXTRADATA:
                assert res.details.extra_data_offset is not None
                assert res.details.extra_data_len is not None
                assert current_tx.extra_data is not None
                o, l = res.details.extra_data_offset, res.details.extra_data_len
                msg.extra_data = current_tx.extra_data[o : o + l]
            else:
                raise exceptions.TrezorException(
                    f"Unknown request type - {res.request_type}."
                )

            res = client.call(messages.TxAck(tx=msg), expect=messages.TxRequest)

    for i, sig in zip(inputs, signatures):
        if i.script_type != messages.InputScriptType.EXTERNAL and sig is None:
            raise exceptions.TrezorException("Some signatures are missing!")

    if use_anti_exfil:
        assert entropy_list is not None
        return [
            (
                AntiExfilSignature(
                    signature=sig, entropy=entropy, nonce_commitment=nonce_commitment
                )
                if sig is not None
                else None
            )
            for sig, entropy, nonce_commitment in zip(
                signatures, entropy_list, nonce_commitment_list
            )
        ], serialized_tx
    else:
        return [
            (
                AntiExfilSignature(signature=sig, entropy=None, nonce_commitment=None)
                if sig is not None
                else None
            )
            for sig in signatures
        ], serialized_tx


@session
def sign_tx(
    client: "TrezorClient",
    coin_name: str,
    inputs: Sequence[messages.TxInputType],
    outputs: Sequence[messages.TxOutputType],
    details: Optional[messages.SignTx] = None,
    prev_txes: Optional["TxCacheType"] = None,
    payment_reqs: Sequence[messages.TxAckPaymentRequest] = (),
    preauthorized: bool = False,
    unlock_path: Optional[List[int]] = None,
    unlock_path_mac: Optional[bytes] = None,
    **kwargs: Any,
) -> Tuple[Sequence[Optional[bytes]], bytes]:
    """Sign a Bitcoin-like transaction.

    Returns a list of signatures (one for each provided input) and the
    network-serialized transaction.

    In addition to the required arguments, it is possible to specify additional
    transaction properties (version, lock time, expiry...). Each additional argument
    must correspond to a field in the `SignTx` data type. Note that some fields
    (`inputs_count`, `outputs_count`, `coin_name`) will be inferred from the arguments
    and cannot be overriden by kwargs.
    """
    anti_exfil_signatures, serialization = sign_tx_common(
        client,
        coin_name,
        inputs,
        outputs,
        details,
        prev_txes,
        payment_reqs,
        preauthorized,
        unlock_path,
        unlock_path_mac,
        False,
        None,
        **kwargs,
    )
    return [
        s.signature if s is not None else None for s in anti_exfil_signatures
    ], serialization


@session
def sign_tx_new(
    client: "TrezorClient",
    coin_name: str,
    inputs: Sequence[messages.TxInputType],
    outputs: Sequence[messages.TxOutputType],
    details: Optional[messages.SignTx] = None,
    prev_txes: Optional["TxCacheType"] = None,
    payment_reqs: Sequence[messages.TxAckPaymentRequest] = (),
    preauthorized: bool = False,
    unlock_path: Optional[List[int]] = None,
    unlock_path_mac: Optional[bytes] = None,
    use_anti_exfil: bool = True,
    entropy_list: Optional[List[bytes]] = None,
    **kwargs: Any,
) -> Sequence[Optional[AntiExfilSignature]]:
    """Sign a Bitcoin-like transaction.

    Returns a list of `AntiExfilSignature` objects (one for each provided input).

    If `use_anti_exfil` is set to `True`, the anti-exfilitration protocol will be
    used. The purpose of this protocol is to prevent the device from leaking
    its secrets through the signatures. In this case, `AntiExfilSignature` objects
    will have non-emtpy fields `entropy` and `nonce_commitment`. It's the caller
    responsibility to verify the signature and the nonce commitment. The caller
    can optionally provide a list of entropies to be used in the protocol. Ideally,
    the caller should provide the same list of entropies if the signing is repeated
    due to a error to prevent the device to perform nonce-grinding attacks.

    In addition to the required arguments, it is possible to specify additional
    transaction properties (version, lock time, expiry...). Each additional argument
    must correspond to a field in the `SignTx` data type. Note that some fields
    (`inputs_count`, `outputs_count`, `coin_name`) will be inferred from the arguments
    and cannot be overriden by kwargs.
    """
    anti_exfil_signatures, serialization = sign_tx_common(
        client,
        coin_name,
        inputs,
        outputs,
        details,
        prev_txes,
        payment_reqs,
        preauthorized,
        unlock_path,
        unlock_path_mac,
        use_anti_exfil,
        entropy_list,
        serialize=False,
        **kwargs,
    )
    return anti_exfil_signatures


def authorize_coinjoin(
    client: "TrezorClient",
    coordinator: str,
    max_rounds: int,
    max_coordinator_fee_rate: int,
    max_fee_per_kvbyte: int,
    n: "Address",
    coin_name: str,
    script_type: messages.InputScriptType = messages.InputScriptType.SPENDADDRESS,
) -> str | None:
    resp = client.call(
        messages.AuthorizeCoinJoin(
            coordinator=coordinator,
            max_rounds=max_rounds,
            max_coordinator_fee_rate=max_coordinator_fee_rate,
            max_fee_per_kvbyte=max_fee_per_kvbyte,
            address_n=n,
            coin_name=coin_name,
            script_type=script_type,
        ),
        expect=messages.Success,
    )
    return _return_success(resp)
