from micropython import const

from trezor import log, wire
from trezor.crypto import base58, hashlib
from trezor.crypto.curve import ed25519
from trezor.messages.CardanoSignedTx import CardanoSignedTx
from trezor.messages.CardanoTxRequest import CardanoTxRequest
from trezor.messages.MessageType import CardanoTxAck

from apps.cardano import CURVE, cbor, seed
from apps.cardano.address import (
    derive_address_and_node,
    is_safe_output_address,
    validate_full_path,
)
from apps.cardano.layout import confirm_sending, confirm_transaction, progress
from apps.common.paths import validate_path
from apps.common.seed import remove_ed25519_prefix
from apps.homescreen.homescreen import display_homescreen

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
) -> bool:
    for index, output in enumerate(outputs):
        if is_change(raw_outputs[index].address_n, raw_inputs):
            continue

        if not await confirm_sending(ctx, outcoins[index], output):
            return False

    total_amount = sum(outcoins)
    if not await confirm_transaction(ctx, total_amount, fee, network_name):
        return False

    return True


async def request_transaction(ctx, tx_req: CardanoTxRequest, index: int):
    tx_req.tx_index = index
    return await ctx.call(tx_req, CardanoTxAck)


async def sign_tx(ctx, msg):
    keychain = await seed.get_keychain(ctx)

    progress.init(msg.transactions_count, "Loading data")

    try:
        attested = len(msg.inputs)*[False]
        input_coins_sum = 0
        # request transactions
        tx_req = CardanoTxRequest()

        for index in range(msg.transactions_count):
            progress.advance()
            tx_ack = await request_transaction(ctx, tx_req, index)
            tx_hash = hashlib.blake2b(data=bytes(tx_ack.transaction), outlen=32).digest()
            tx_decoded = cbor.decode(tx_ack.transaction)
            for i, input in enumerate(msg.inputs):
                if not attested[i] and bytes(input.prev_hash) == tx_hash:
                   attested[i] = True
                   outputs = tx_decoded[1]
                   amount = outputs[input.prev_index][1]
                   input_coins_sum += amount

        if not all(attested):
            raise wire.ProcessError("No tx data sent for input " + str(attested.index(False)))

        transaction = Transaction(
            msg.inputs, msg.outputs, keychain, msg.protocol_magic, input_coins_sum
        )

        # clear progress bar
        display_homescreen()

        for i in msg.inputs:
            await validate_path(ctx, validate_full_path, keychain, i.address_n, CURVE)

        # sign the transaction bundle and prepare the result
        tx_body, tx_hash = transaction.serialise_tx()
        tx = CardanoSignedTx(tx_body=tx_body, tx_hash=tx_hash)

    except ValueError as e:
        if __debug__:
            log.exception(__name__, e)
        raise wire.ProcessError("Signing failed")

    # display the transaction in UI
    if not await show_tx(
        ctx,
        transaction.output_addresses,
        transaction.outgoing_coins,
        transaction.fee,
        transaction.network_name,
        transaction.inputs,
        transaction.outputs,
    ):
        raise wire.ActionCancelled("Signing cancelled")

    return tx


class Transaction:
    def __init__(
        self,
        inputs: list,
        outputs: list,
        keychain,
        protocol_magic: int,
        input_coins_sum: int,
    ):
        self.inputs = inputs
        self.outputs = outputs
        self.keychain = keychain
        # attributes have to be always empty in current Cardano
        self.attributes = {}

        self.network_name = KNOWN_PROTOCOL_MAGICS.get(protocol_magic, "Unknown")
        self.protocol_magic = protocol_magic
        self.input_coins_sum = input_coins_sum

    def _process_outputs(self):
        change_addresses = []
        change_derivation_paths = []
        output_addresses = []
        outgoing_coins = []
        change_coins = []

        for output in self.outputs:
            if output.address_n:
                address, _ = derive_address_and_node(self.keychain, output.address_n)
                change_addresses.append(address)
                change_derivation_paths.append(output.address_n)
                change_coins.append(output.amount)
            else:
                if output.address is None:
                    raise wire.ProcessError(
                        "Each output must have address or address_n field!"
                    )
                if not is_safe_output_address(output.address):
                    raise wire.ProcessError("Invalid output address!")

                outgoing_coins.append(output.amount)
                output_addresses.append(output.address)

        self.change_addresses = change_addresses
        self.output_addresses = output_addresses
        self.outgoing_coins = outgoing_coins
        self.change_coins = change_coins
        self.change_derivation_paths = change_derivation_paths

    def _build_witnesses(self, tx_aux_hash: str):
        witnesses = []
        for input in self.inputs:
            _, node = derive_address_and_node(self.keychain, input.address_n)
            message = (
                b"\x01" + cbor.encode(self.protocol_magic) + b"\x58\x20" + tx_aux_hash
            )
            signature = ed25519.sign_ext(
                node.private_key(), node.private_key_ext(), message
            )
            extended_public_key = (
                remove_ed25519_prefix(node.public_key()) + node.chain_code()
            )
            witnesses.append(
                [
                    (input.type or 0),
                    cbor.Tagged(24, cbor.encode([extended_public_key, signature])),
                ]
            )

        return witnesses

    @staticmethod
    def compute_fee(input_coins_sum: int, outgoing_coins: list, change_coins: list):
        outgoing_coins_sum = sum(outgoing_coins)
        change_coins_sum = sum(change_coins)

        return input_coins_sum - outgoing_coins_sum - change_coins_sum

    def serialise_tx(self):

        self._process_outputs()

        inputs_cbor = []
        for input in self.inputs:
            inputs_cbor.append(
                [
                    (input.type or 0),
                    cbor.Tagged(24, cbor.encode([input.prev_hash, input.prev_index])),
                ]
            )

        inputs_cbor = cbor.IndefiniteLengthArray(inputs_cbor)

        outputs_cbor = []
        for index, address in enumerate(self.output_addresses):
            outputs_cbor.append(
                [cbor.Raw(base58.decode(address)), self.outgoing_coins[index]]
            )

        for index, address in enumerate(self.change_addresses):
            outputs_cbor.append(
                [cbor.Raw(base58.decode(address)), self.change_coins[index]]
            )

        outputs_cbor = cbor.IndefiniteLengthArray(outputs_cbor)

        tx_aux_cbor = [inputs_cbor, outputs_cbor, self.attributes]
        tx_hash = hashlib.blake2b(data=cbor.encode(tx_aux_cbor), outlen=32).digest()

        witnesses = self._build_witnesses(tx_hash)
        tx_body = cbor.encode([tx_aux_cbor, witnesses])

        self.fee = self.compute_fee(
            self.input_coins_sum, self.outgoing_coins, self.change_coins
        )

        return tx_body, tx_hash
