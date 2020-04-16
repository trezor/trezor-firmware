from micropython import const
from ubinascii import unhexlify

from trezor import log, wire
from trezor.crypto import hashlib
from trezor.crypto.curve import ed25519
from trezor.messages.CardanoSignedTx import CardanoSignedTx
from trezor.messages.CardanoTxAck import CardanoTxAck
from trezor.messages.CardanoTxRequest import CardanoTxRequest

from apps.cardano import CURVE, seed
from apps.cardano.address import derive_address, validate_full_path
from apps.cardano.layout import (
    confirm_certificate,
    confirm_sending,
    confirm_transaction,
)
from apps.common import cbor
from apps.common.paths import validate_path

# the maximum allowed change address.  this should be large enough for normal
# use and still allow to quickly brute-force the correct bip32 path
MAX_CHANGE_ADDRESS_INDEX = const(1000000)
ACCOUNT_PREFIX_DEPTH = const(2)

KNOWN_PROTOCOL_MAGICS = {764824073: "Mainnet", 1097911063: "Testnet"}


# we consider addresses from the external chain as possible change addresses as well
def is_change(output, inputs):
    for input in inputs:
        inp = input.address_n
        if (
            not output[:ACCOUNT_PREFIX_DEPTH] == inp[:ACCOUNT_PREFIX_DEPTH]
            or not output[-2] < 2
            or not output[-1] < MAX_CHANGE_ADDRESS_INDEX
        ):
            return False
    return True


async def show_tx(
    ctx,
    outputs: list,
    outcoins: list,
    fee: int,
    network_name: str,
    raw_inputs: list,
    raw_outputs: list,
    certificates: list,
) -> bool:
    for index, output in enumerate(outputs):
        if raw_outputs[index].address_parameters and is_change(
            raw_outputs[index].address_parameters.address_n, raw_inputs
        ):
            continue

        await confirm_sending(ctx, outcoins[index], output)

    for index, certificate in enumerate(certificates):
        await confirm_certificate(ctx, certificate)

    total_amount = sum(outcoins)
    await confirm_transaction(ctx, total_amount, fee, network_name)


async def request_transaction(ctx, tx_req: CardanoTxRequest, index: int):
    tx_req.tx_index = index
    return await ctx.call(tx_req, CardanoTxAck)


@seed.with_keychains
async def sign_tx(ctx, msg, keychains: seed.Keychains):
    try:
        transaction = Transaction(
            msg.inputs,
            msg.outputs,
            keychains,
            msg.protocol_magic,
            msg.fee,
            msg.ttl,
            msg.certificates,
        )

        for i in msg.inputs:
            await validate_path(ctx, validate_full_path, keychains, i.address_n, CURVE)

        # sign the transaction bundle and prepare the result
        tx_body, tx_hash = transaction.serialise_tx()
        tx = CardanoSignedTx(tx_body=tx_body, tx_hash=tx_hash)

    except ValueError as e:
        if __debug__:
            log.exception(__name__, e)
        raise wire.ProcessError("Signing failed")

    # display the transaction in UI
    await show_tx(
        ctx,
        transaction.output_addresses,
        transaction.outgoing_coins,
        transaction.fee,
        transaction.network_name,
        transaction.inputs,
        transaction.outputs,
        transaction.certificates,
    )

    return tx


class Transaction:
    def __init__(
        self,
        inputs: list,
        outputs: list,
        keychains,
        protocol_magic: int,
        fee,
        ttl,
        certificates: list,
    ):
        self.inputs = inputs
        self.outputs = outputs
        self.keychains = keychains
        self.fee = fee
        self.ttl = ttl
        self.certificates = certificates

        self.network_name = KNOWN_PROTOCOL_MAGICS.get(protocol_magic, "Unknown")
        self.protocol_magic = protocol_magic

    def _process_outputs(self):
        change_addresses = []
        change_derivation_paths = []
        output_addresses = []
        outgoing_coins = []
        change_coins = []

        for output in self.outputs:
            if output.address_parameters:
                address = derive_address(
                    self.keychains,
                    output.address_parameters,
                    self.protocol_magic,
                    human_readable=False,
                )
                change_addresses.append(address)
                change_derivation_paths.append(output.address_parameters.address_n)
                change_coins.append(output.amount)
            else:
                if output.address is None:
                    raise wire.ProcessError(
                        "Each output must have address or address_n field!"
                    )
                # todo: GK - this should be checked only with byron addresses
                # if not is_safe_output_address(output.address):
                #     raise wire.ProcessError("Invalid output address!")

                outgoing_coins.append(output.amount)
                output_addresses.append(output.address)

        self.change_addresses = change_addresses
        self.output_addresses = output_addresses
        self.outgoing_coins = outgoing_coins
        self.change_coins = change_coins
        self.change_derivation_paths = change_derivation_paths

    def _build_witness(self, keychains, protocol_magic, tx_body_hash, address_path):
        node = self.keychains.derive(address_path)
        message = b"\x58\x20" + tx_body_hash

        # todo: GK - sign ext? sign?
        signature = ed25519.sign(node.private_key(), message)
        # signature = ed25519.sign_ext(node.private_key(), node.private_key_ext(), message)

        # todo: GK - extended pub key vs pub key?
        # extended_public_key = (
        #     remove_ed25519_prefix(node.public_key()) + node.chain_code()
        # )

        # return [extended_public_key, signature]
        return [node.public_key(), signature]

    def _build_witnesses(self, tx_aux_hash: str):
        witnesses = []
        for input in self.inputs:
            witness = self._build_witness(
                self.keychains, self.protocol_magic, tx_aux_hash, input.address_n
            )
            witnesses.append(witness)

        for certificate in self.certificates:
            # todo: add other certificates without witnesses + refactor
            if certificate.type == "stake_registration":
                continue

            witness = self._build_witness(
                self.keychains, self.protocol_magic, tx_aux_hash, certificate.path
            )
            witnesses.append(witness)

        return {0: witnesses}

    # todo: move?
    def certificate_type_to_type_id(self, certificate_type):
        if certificate_type == "stake_registration":
            return 0
        if certificate_type == "stake_deregistration":
            return 1
        if certificate_type == "stake_delegation":
            return 2

        raise ValueError("Unsupported certificate type '%s'" % certificate_type)

    def serialise_tx(self):

        self._process_outputs()

        inputs_cbor = []
        for input in self.inputs:
            inputs_cbor.append([input.prev_hash, input.prev_index])

        outputs_cbor = []
        for index, address in enumerate(self.output_addresses):
            outputs_cbor.append([unhexlify(address), self.outgoing_coins[index]])

        for index, address in enumerate(self.change_addresses):
            outputs_cbor.append([address, self.change_coins[index]])

        outputs_cbor = outputs_cbor

        # todo: certificates, withdrawals, metadata
        tx_body = {0: inputs_cbor, 1: outputs_cbor, 2: self.fee, 3: self.ttl}

        if len(self.certificates) > 0:
            certificates_cbor = []
            for index, certificate in enumerate(self.certificates):
                node = self.keychains.derive(certificate.path)
                public_key_hash = hashlib.blake2b(
                    data=node.public_key(), outlen=32
                ).digest()

                # todo: GK - 0 deppends on cert type
                cert_type_id = self.certificate_type_to_type_id(certificate.type)
                certificates_cbor.append([cert_type_id, [0, public_key_hash]])

            tx_body[4] = certificates_cbor

        tx_body_cbor = cbor.encode(tx_body)
        tx_hash = hashlib.blake2b(data=tx_body_cbor, outlen=32).digest()

        witnesses = self._build_witnesses(tx_hash)
        tx_body = cbor.encode([tx_body, witnesses, {}])

        return tx_body, tx_hash
