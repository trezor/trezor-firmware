from typing import TYPE_CHECKING

from apps.common.keychain import auto_keychain

if TYPE_CHECKING:
    from trezor.messages import CosmosSignTx, CosmosSignedTx, CosmosAny, CosmosBankMsgSend, CosmosTxBody, CosmosFee
    from typing import Any

    from apps.common.keychain import Keychain

@auto_keychain(__name__)
async def sign_tx(
    msg: CosmosSignTx, keychain: Keychain
) -> CosmosSignedTx:
    from trezor import wire
    from trezor.messages import CosmosSignDoc, CosmosSignedTx, CosmosTxBody, CosmosBankMsgSend, CosmosAuthInfo
    from trezor.protobuf import decode
    from trezor.ui.layouts import confirm_value

    from apps.common import paths

    address_n = msg.address_n

    await paths.validate_path(keychain, address_n)

    sd = decode(msg.sign_doc, CosmosSignDoc, False)

    if sd.chain_id == "":
        raise wire.DataError("Empty chain id")
    
    await confirm_value("chain id", sd.chain_id, "", "confirm")
    
    # XXX: should we display this? not very relevant to user, if the account number has a mismatch with the address, the tx won't pass.
    await confirm_value("account number", str(sd.account_number), "", "confirm")

    auth_info = decode(sd.auth_info_bytes, CosmosAuthInfo, False)

    node = keychain.derive(address_n)
    pk = node.public_key()

    await validate_and_confirm_auth_info(auth_info, pk)

    body = decode(sd.body_bytes, CosmosTxBody, False)

    # TODO: support any message type via requesting protobuf definitions from the outside in a verifiable way (merkle proof or something)
    msg_map = {
        "/cosmos.bank.v1beta1.MsgSend": {
            "desc": CosmosBankMsgSend,
            "validate": validate_bank_msg_send, # XXX: not possible to make it generic, idea is to have it for well known messages, then for extra messages show a warning
            "confirm": confirm_bank_msg_send, # XXX: not possible to make it generic, idea is to have it for well known messages, then for extra messages, show the raw fields, like eth does for eip1559
        },
    }

    # TODO: allow navigation between all screens instead of cancel for some

    for index, tx_msg in enumerate(body.messages):
        # XXX: maybe show a pretty name for well known messages? e.g. "Send coins" instead of "/cosmos.bank.v1beta1.MsgSend"
        await confirm_value("message #"+str(index+1), tx_msg.type_url, "", "confirm")

        if not (tx_msg.type_url in msg_map):
            raise wire.DataError("Message type not supported: " + tx_msg.type_url)
        msg_ctx = msg_map[tx_msg.type_url]

        dmsg = decode(tx_msg.value, msg_ctx["desc"], False)
        msg_ctx["validate"](dmsg, pk)
        await msg_ctx["confirm"](dmsg)

    await confirm_fee(auth_info.fee)

    await confirm_body_infos(body)

    sk = node.private_key()
    signature = crypto_sign_doc(sk, msg.sign_doc)

    return CosmosSignedTx(
        signature=signature,
    )

def crypto_sign_doc(sk: bytes, sign_doc: bytes):
    from trezor.crypto.curve import secp256k1
    from trezor.crypto.hashlib import sha256

    msg_hash = sha256(sign_doc).digest()
    signature = secp256k1.sign(sk, msg_hash)
    return signature[1:] # cosmos signatures do not have this heading byte

async def validate_and_confirm_auth_info(auth_info: bytes, pubkey: bytes):
    from trezor.messages import  CosmosSecp256k1Pubkey
    from trezor.protobuf import decode
    from trezor import wire
    from trezor.ui.layouts import confirm_value

    # TODO: properly support cases where there is multiple signers
    if len(auth_info.signer_infos) != 1:
        raise wire.DataError("Invalid signer infos")
    
    signer_info = auth_info.signer_infos[0]

    if signer_info.mode_info.single.mode != 1: # TODO: use constants for sign mode, protobuf enums crash on import it seems
        raise wire.DataError("Only direct sign mode is supported")

    pk_type = signer_info.public_key.type_url
    if pk_type != "/cosmos.crypto.secp256k1.PubKey":
        raise wire.DataError("Invalid pubkey type: " + pk_type)
    
    signer_pubkey = decode(signer_info.public_key.value, CosmosSecp256k1Pubkey, False)

    if signer_pubkey.key != pubkey:
        raise wire.DataError("Unexpected signer pubkey")
    
    await confirm_value("sequence", str(signer_info.sequence), "", "confirm")

async def confirm_body_infos(body: CosmosTxBody):
    from trezor.ui.layouts import confirm_value

    if body.memo != None and body.memo != "":
        await confirm_value("memo", body.memo, "", "confirm")

    if body.timeout_height != None and body.timeout_height != 0:
        await confirm_value("timeout height", str(body.timeout_height), "", "confirm")

async def confirm_fee(fee: CosmosFee):
    from trezor import wire
    from trezor.ui.layouts import confirm_value

    # TODO: support granter and payer, need to properly support multiple signers for that
    if fee.granter != None and fee.granter != "":
        raise wire.DataError("Fee granter not supported")
    if fee.payer != None and fee.payer != "":
        raise wire.DataError("Fee payer not supported")
    
    # XXX: should we display gas limit? does not seem relevant to the user since it's an abstract value used by the chain internals, but we're blind-signing it in this case.
    # maybe we should display the gas-cost instead?
    await confirm_value("gas limit", str(fee.gas_limit), "", "confirm")

    # TODO: support multiple fee coins, how to do this properly in ui? one screen for each coin, or some kind of list?
    if len(fee.amount) != 1:
        raise wire.DataError("Invalid number of fee coins, expected 1, got " + str(len(fee.amount)))
    amount = fee.amount[0].amount + fee.amount[0].denom
    await confirm_value("max fee", amount, "", "confirm")

def validate_bank_msg_send(msg: CosmosBankMsgSend, pk: bytes):
    from trezor.crypto.bech32 import bech32_decode, bech32_encode, convertbits, Encoding
    from trezor import wire
    from .addr import derive_addr_bz

    # TODO: support list of coins, how to do this properly in ui? one screen for each coin, or some kind of list?
    if len(msg.amount) != 1:
        raise wire.DataError("Invalid number of coins, expected 1, got " + str(len(msg.amount)))

    msg_addr = msg.from_address
    hrp, data, _ = bech32_decode(msg_addr)
    msg_addr_bz = bytes(convertbits(data, 5, 8))

    addr_bz = derive_addr_bz(pk)

    if addr_bz != msg_addr_bz:
        converted_bits = convertbits(addr_bz, 8, 5)
        addr = bech32_encode(hrp, converted_bits, Encoding.BECH32)
        raise wire.DataError("Invalid sender expected " + addr + ", got " + msg.from_address)
    
async def confirm_bank_msg_send(msg: CosmosBankMsgSend):
    from trezor.ui.layouts import confirm_output, confirm_address

    await confirm_address(
        "sending from",
        msg.from_address,
    )

    # TODO: support list of coins, how to do this properly in ui? one screen for each coin, or some kind of list?
    # XXX: should we and how should we show a decimal amount with coin name instead of atomics with minimal denom, eg show "1 ATOM" instead of "1000000uatom"
    amount = msg.amount[0].amount + msg.amount[0].denom
    await confirm_output(
        msg.to_address,
        amount=amount,
    )