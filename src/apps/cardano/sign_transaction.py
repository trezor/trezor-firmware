from trezor import log, ui, wire
from trezor.crypto import base58, bip32, hashlib
from trezor.crypto.curve import ed25519
from trezor.messages.CardanoTxRequest import CardanoTxRequest
from trezor.messages.MessageType import CardanoTxAck
from trezor.ui.text import BR

from .address import _break_address_n_to_lines, derive_address_and_node
from .ui import progress, show_swipable_with_confirmation

from apps.cardano import cbor
from apps.common import seed, storage
from apps.homescreen.homescreen import display_homescreen


async def show_tx(
    ctx,
    outputs: list,
    outcoins: list,
    change_derivation_paths: list,
    change_coins: list,
    fee: float,
    tx_size: float,
) -> bool:
    lines = ("%s ADA" % _micro_ada_to_ada(fee), BR, "Tx size:", "%s bytes" % tx_size)
    if not await show_swipable_with_confirmation(
        ctx, lines, "Confirm fee", ui.ICON_SEND, ui.GREEN
    ):
        return False

    for index, output in enumerate(outputs):
        if not await show_swipable_with_confirmation(
            ctx, output, "Confirm output", ui.ICON_SEND, ui.GREEN
        ):
            return False

        if not await show_swipable_with_confirmation(
            ctx,
            "%s ADA" % _micro_ada_to_ada(outcoins[index]),
            "Confirm amount",
            ui.ICON_SEND,
            ui.GREEN,
        ):
            return False

    for index, change in enumerate(change_derivation_paths):
        if not await show_swipable_with_confirmation(
            ctx,
            _break_address_n_to_lines(change),
            "Confirm change",
            ui.ICON_SEND,
            ui.GREEN,
        ):
            return False

        if not await show_swipable_with_confirmation(
            ctx,
            "%s ADA" % _micro_ada_to_ada(change_coins[index]),
            "Confirm amount",
            ui.ICON_SEND,
            ui.GREEN,
        ):
            return False

    return True


async def request_transaction(ctx, tx_req: CardanoTxRequest, index: int):
    tx_req.tx_index = index
    return await ctx.call(tx_req, CardanoTxAck)


async def cardano_sign_transaction(ctx, msg):
    mnemonic = storage.get_mnemonic()
    root_node = bip32.from_mnemonic_cardano(mnemonic)

    progress.init(msg.transactions_count, "Loading data")

    try:
        # request transactions
        transactions = []
        tx_req = CardanoTxRequest()
        for index in range(msg.transactions_count):
            progress.advance()
            tx_ack = await request_transaction(ctx, tx_req, index)
            transactions.append(tx_ack.transaction)

        # clear progress bar
        display_homescreen()

        # sign the transaction bundle and prepare the result
        transaction = Transaction(msg.inputs, msg.outputs, transactions, root_node)
        tx_body, tx_hash = transaction.serialise_tx()
        tx = CardanoTxRequest(tx_body=tx_body, tx_hash=tx_hash)

    except ValueError as e:
        if __debug__:
            log.exception(__name__, e)
        raise wire.ProcessError("Signing failed")

    # display the transaction in UI
    if not await show_tx(
        ctx,
        transaction.output_addresses,
        transaction.outgoing_coins,
        transaction.change_derivation_paths,
        transaction.change_coins,
        transaction.fee,
        len(tx_body),
    ):
        raise wire.ActionCancelled("Signing cancelled")

    return tx


def _micro_ada_to_ada(amount: float) -> float:
    return amount / 1000000


class Transaction:
    CARDANO_WITNESS_MAGIC_PREFIX = b"\x01\x1a\x2d\x96\x4a\x09\x58\x20"

    def __init__(self, inputs: list, outputs: list, transactions: list, root_node):
        self.inputs = inputs
        self.outputs = outputs
        self.transactions = transactions
        self.root_node = root_node

        # attributes have to be always empty in current Cardano
        self.attributes = {}

    def _process_inputs(self):
        input_coins = []
        input_hashes = []
        output_indexes = []
        types = []
        tx_data = {}

        for raw_transaction in self.transactions:
            tx_hash = hashlib.blake2b(data=bytes(raw_transaction), outlen=32).digest()
            tx_data[tx_hash] = cbor.decode(raw_transaction)

        for input in self.inputs:
            input_hashes.append(input.prev_hash)
            output_indexes.append(input.prev_index)
            types.append(input.type or 0)

        nodes = []
        for input in self.inputs:
            _, node = derive_address_and_node(self.root_node, input.address_n)
            nodes.append(node)

        for index, output_index in enumerate(output_indexes):
            tx_hash = bytes(input_hashes[index])
            if tx_hash in tx_data:
                tx = tx_data[tx_hash]
                outputs = tx[1]
                amount = outputs[output_index][1]
                input_coins.append(amount)
            else:
                raise wire.ProcessError("No tx data sent for input " + str(index))

        self.input_coins = input_coins
        self.nodes = nodes
        self.types = types
        self.input_hashes = input_hashes
        self.output_indexes = output_indexes

    def _process_outputs(self):
        change_addresses = []
        change_derivation_paths = []
        output_addresses = []
        outgoing_coins = []
        change_coins = []

        for output in self.outputs:
            if output.address_n:
                address, _ = derive_address_and_node(self.root_node, output.address_n)
                change_addresses.append(address)
                change_derivation_paths.append(output.address_n)
                change_coins.append(output.amount)
            else:
                if output.address is None:
                    raise wire.ProcessError(
                        "Each output must have address or address_n field!"
                    )

                outgoing_coins.append(output.amount)
                output_addresses.append(output.address)

        self.change_addresses = change_addresses
        self.output_addresses = output_addresses
        self.outgoing_coins = outgoing_coins
        self.change_coins = change_coins
        self.change_derivation_paths = change_derivation_paths

    def _build_witnesses(self, tx_aux_hash: str):
        witnesses = []
        for index, node in enumerate(self.nodes):
            message = self.CARDANO_WITNESS_MAGIC_PREFIX + tx_aux_hash
            signature = ed25519.sign_ext(
                node.private_key(), node.private_key_ext(), message
            )
            extended_public_key = (
                seed.remove_ed25519_prefix(node.public_key()) + node.chain_code()
            )
            witnesses.append(
                [
                    self.types[index],
                    cbor.Tagged(24, cbor.encode([extended_public_key, signature])),
                ]
            )

        return witnesses

    @staticmethod
    def compute_fee(input_coins: list, outgoing_coins: list, change_coins: list):
        input_coins_sum = sum(input_coins)
        outgoing_coins_sum = sum(outgoing_coins)
        change_coins_sum = sum(change_coins)

        return input_coins_sum - outgoing_coins_sum - change_coins_sum

    def serialise_tx(self):

        self._process_inputs()
        self._process_outputs()

        inputs_cbor = []
        for i, output_index in enumerate(self.output_indexes):
            inputs_cbor.append(
                [
                    self.types[i],
                    cbor.Tagged(24, cbor.encode([self.input_hashes[i], output_index])),
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
            self.input_coins, self.outgoing_coins, self.change_coins
        )

        return tx_body, tx_hash
