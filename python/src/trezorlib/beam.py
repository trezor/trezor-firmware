# This file is part of the Trezor project.
#
# Copyright (C) 2012-2019 SatoshiLabs and contributors
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

from typing import List

from . import messages
from .tools import CallException, expect, normalize_nfc, session

REQUIRED_FIELDS_KIDV = ["idx", "type", "sub_idx", "value"]
REQUIRED_FIELDS_TRANSACTION = [
    "inputs",
    "outputs",
    "offset_sk",
    "nonce_slot",
    "kernel_parameters",
]
REQUIRED_FIELDS_KERNEL_PARAMS = [
    "fee",
    "commitment",
    "min_height",
    "max_height",
    "asset_emission",
    "hash_lock",
    "multisig",
]
REQUIRED_FIELDS_ECC_POINT = ["x", "y"]
REQUIRED_FIELDS_MULTISIG = ["nonce", "excess"]


@expect(messages.BeamSignature)
def sign_message(client, message, kid_idx, kid_sub_idx, show_display=True):
    return client.call(
        messages.BeamSignMessage(
            msg=message,
            kid_idx=int(kid_idx),
            kid_sub_idx=int(kid_sub_idx),
            show_display=show_display,
        )
    )


def verify_message(client, nonce_pub_x, nonce_pub_y, sign_k, pk_x, pk_y, message):
    nonce_pub_x = hex_str_to_bytearray(nonce_pub_x, "Nonce X", True)
    nonce_pub_y = int(nonce_pub_y)
    sign_k = hex_str_to_bytearray(sign_k, "K", True)
    pk_x = hex_str_to_bytearray(pk_x, "PK X", True)
    pk_y = int(pk_y)
    message = normalize_nfc(message)

    try:
        signature = messages.BeamSignature(
            nonce_pub=messages.BeamECCPoint(x=nonce_pub_x, y=nonce_pub_y), sign_k=sign_k
        )
        public_key = messages.BeamECCPoint(x=pk_x, y=pk_y)
        resp = client.call(
            messages.BeamVerifyMessage(
                signature=signature, public_key=public_key, message=message
            )
        )
    except CallException as e:
        resp = e
    if isinstance(resp, messages.Success):
        return True
    return False


@expect(messages.BeamECCPoint)
def get_public_key(client, kid_idx, kid_sub_idx, show_display=True):
    return client.call(
        messages.BeamGetPublicKey(
            kid_idx=int(kid_idx),
            kid_sub_idx=int(kid_sub_idx),
            show_display=show_display,
        )
    )


@expect(messages.BeamOwnerKey)
def get_owner_key(client, show_display=True):
    return client.call(messages.BeamGetOwnerKey(show_display=show_display))


@expect(messages.BeamECCPoint)
def generate_key(client, kidv_idx, kidv_type, kidv_sub_idx, kidv_value, is_coin_key):
    kidv = messages.BeamKeyIDV(
        idx=int(kidv_idx),
        type=int(kidv_type),
        sub_idx=int(kidv_sub_idx),
        value=int(kidv_value),
    )
    return client.call(messages.BeamGenerateKey(kidv=kidv, is_coin_key=is_coin_key))


@expect(messages.BeamECCPoint)
def generate_nonce(client, slot):
    return client.call(messages.BeamGenerateNonce(slot=int(slot)))


@expect(messages.BeamECCPoint)
def get_nonce_image(client, slot):
    return client.call(messages.BeamGetNoncePublic(slot=int(slot)))


@expect(messages.BeamRangeproofData)
def generate_rangeproof(
    client, kidv_idx, kidv_type, kidv_sub_idx, kidv_value, is_public
):
    kidv = messages.BeamKeyIDV(
        idx=int(kidv_idx),
        type=int(kidv_type),
        sub_idx=int(kidv_sub_idx),
        value=int(kidv_value),
    )
    return client.call(messages.BeamGenerateRangeproof(kidv=kidv, is_public=is_public))


@session
@expect(messages.BeamSignedTransaction)
def sign_tx(
    client,
    inputs: List[messages.BeamKeyIDV],
    outputs: List[messages.BeamKeyIDV],
    offset_sk,
    nonce_slot,
    kernel_params,
):
    response = client.call(
        messages.BeamSignTransaction(
            inputs=inputs,
            outputs=outputs,
            offset_sk=bytearray(offset_sk, "utf-8"),
            nonce_slot=int(nonce_slot),
            kernel_params=kernel_params,
        )
    )
    return response


def _check_required_fields(data, required_fields, error_message):
    missing_fields = [field for field in required_fields if field not in data.keys()]

    if missing_fields:
        raise ValueError(
            error_message
            + ": The structure is missing some fields: "
            + str(missing_fields)
        )


def check_transaction_data(transaction):
    _check_required_fields(
        transaction,
        REQUIRED_FIELDS_TRANSACTION,
        "The transaction is missing some fields",
    )

    for input in transaction["inputs"]:
        _check_required_fields(input, REQUIRED_FIELDS_KIDV, "Input")
    for output in transaction["outputs"]:
        _check_required_fields(output, REQUIRED_FIELDS_KIDV, "Output")

    _check_required_fields(
        transaction["kernel_parameters"],
        REQUIRED_FIELDS_KERNEL_PARAMS,
        "Kernel parameters",
    )
    _check_required_fields(
        transaction["kernel_parameters"]["multisig"],
        REQUIRED_FIELDS_MULTISIG,
        "Multisig",
    )
    _check_required_fields(
        transaction["kernel_parameters"]["multisig"]["nonce"],
        REQUIRED_FIELDS_ECC_POINT,
        "Multisig",
    )
    _check_required_fields(
        transaction["kernel_parameters"]["multisig"]["excess"],
        REQUIRED_FIELDS_ECC_POINT,
        "Multisig",
    )


def create_kidv(kidv) -> messages.BeamKeyIDV:
    _check_required_fields(kidv, REQUIRED_FIELDS_KIDV, "Input/Output")

    return messages.BeamKeyIDV(
        idx=int(kidv["idx"]),
        type=int(kidv["type"]),
        sub_idx=int(kidv["sub_idx"]),
        value=int(kidv["value"]),
    )


def create_point(point) -> messages.BeamECCPoint:
    _check_required_fields(point, REQUIRED_FIELDS_ECC_POINT, "ECC Point")

    return messages.BeamECCPoint(x=bytearray(point["x"], "utf-8"), y=bool(point["y"]))


def create_kernel_params(params) -> messages.BeamKernelParameters:
    _check_required_fields(params, REQUIRED_FIELDS_KERNEL_PARAMS, "Kernel parameters")

    return messages.BeamKernelParameters(
        fee=int(params["fee"]),
        commitment=create_point(params["commitment"]),
        min_height=int(params["min_height"]),
        max_height=int(params["max_height"]),
        asset_emission=int(params["asset_emission"]),
        hash_lock=bytearray(params["hash_lock"], "utf-8"),
        multisig_nonce=create_point(params["multisig"]["nonce"]),
        multisig_excess=create_point(params["multisig"]["excess"]),
    )


def hex_str_to_bytearray(hex_data, name="", print_info=False):
    if hex_data.startswith("0x"):
        hex_data = hex_data[2:]
        if print_info:
            print("Converted {}: {}".format(name, hex_data))

    return bytearray.fromhex(hex_data)
