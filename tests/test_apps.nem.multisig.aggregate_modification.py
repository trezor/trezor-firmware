from common import *

from apps.nem.helpers import *
from apps.nem.multisig import *
from apps.nem.multisig.serialize import *

from trezor.crypto import hashlib
from trezor.messages.NEMSignTx import NEMSignTx
from trezor.messages.NEMAggregateModification import NEMAggregateModification
from trezor.messages.NEMCosignatoryModification import NEMCosignatoryModification
from trezor.messages.NEMTransactionCommon import NEMTransactionCommon


class TestNemMultisigAggregateModification(unittest.TestCase):

    def test_nem_transaction_aggregate_modification(self):
        # http://bob.nem.ninja:8765/#/aggregate/6a55471b17159e5b6cd579c421e95a4e39d92e3f78b0a55ee337e785a601d3a2
        m = _create_msg(NEM_NETWORK_TESTNET,
                        0,
                        22000000,
                        0,
                        2,
                        0)
        t = serialize_aggregate_modification(m.transaction, m.aggregate_modification, unhexlify("462ee976890916e54fa825d26bdd0235f5eb5b6a143c199ab0ae5ee9328e08ce"))

        serialize_cosignatory_modification(t, 1, unhexlify(
            "994793ba1c789fa9bdea918afc9b06e2d0309beb1081ac5b6952991e4defd324"))
        serialize_cosignatory_modification(t, 1, unhexlify(
            "c54d6e33ed1446eedd7f7a80a588dd01857f723687a09200c1917d5524752f8b"))

        self.assertEqual(hashlib.sha3_256(t, keccak=True).digest(),
                         unhexlify("6a55471b17159e5b6cd579c421e95a4e39d92e3f78b0a55ee337e785a601d3a2"))

        # http://chain.nem.ninja/#/aggregate/cc64ca69bfa95db2ff7ac1e21fe6d27ece189c603200ebc9778d8bb80ca25c3c
        m = _create_msg(NEM_NETWORK_MAINNET,
                        0,
                        40000000,
                        0,
                        5,
                        0)
        t = serialize_aggregate_modification(m.transaction, m.aggregate_modification, unhexlify("f41b99320549741c5cce42d9e4bb836d98c50ed5415d0c3c2912d1bb50e6a0e5"))

        serialize_cosignatory_modification(t, 1, unhexlify(
            "1fbdbdde28daf828245e4533765726f0b7790e0b7146e2ce205df3e86366980b"))
        serialize_cosignatory_modification(t, 1, unhexlify(
            "f94e8702eb1943b23570b1b83be1b81536df35538978820e98bfce8f999e2d37"))
        serialize_cosignatory_modification(t, 1, unhexlify(
            "826cedee421ff66e708858c17815fcd831a4bb68e3d8956299334e9e24380ba8"))
        serialize_cosignatory_modification(t, 1, unhexlify(
            "719862cd7d0f4e875a6a0274c9a1738f38f40ad9944179006a54c34724c1274d"))
        serialize_cosignatory_modification(t, 1, unhexlify(
            "43aa69177018fc3e2bdbeb259c81cddf24be50eef9c5386db51d82386c41475a"))

        self.assertEqual(hashlib.sha3_256(t, keccak=True).digest(),
                         unhexlify("cc64ca69bfa95db2ff7ac1e21fe6d27ece189c603200ebc9778d8bb80ca25c3c"))

    def test_nem_transaction_aggregate_modification_relative_change(self):
        # http://bob.nem.ninja:8765/#/aggregate/1fbdae5ba753e68af270930413ae90f671eb8ab58988116684bac0abd5726584
        m = _create_msg(NEM_NETWORK_TESTNET,
                        6542254,
                        40000000,
                        6545854,
                        4,
                        2)
        t = serialize_aggregate_modification(m.transaction, m.aggregate_modification, unhexlify("6bf7849c1eec6a2002995cc457dc00c4e29bad5c88de63f51e42dfdcd7b2131d"))

        serialize_cosignatory_modification(t, 1, unhexlify(
            "5f53d076c8c3ec3110b98364bc423092c3ec2be2b1b3c40fd8ab68d54fa39295"))
        serialize_cosignatory_modification(t, 1, unhexlify(
            "9eb199c2b4d406f64cb7aa5b2b0815264b56ba8fe44d558a6cb423a31a33c4c2"))
        serialize_cosignatory_modification(t, 1, unhexlify(
            "94b2323dab23a3faba24fa6ddda0ece4fbb06acfedd74e76ad9fae38d006882b"))
        serialize_cosignatory_modification(t, 1, unhexlify(
            "d88c6ee2a2cd3929d0d76b6b14ecb549d21296ab196a2b3a4cb2536bcce32e87"))
        serialize_minimum_cosignatories(t, 2)

        self.assertEqual(hashlib.sha3_256(t, keccak=True).digest(),
                         unhexlify("1fbdae5ba753e68af270930413ae90f671eb8ab58988116684bac0abd5726584"))


def _create_msg(network: int, timestamp: int, fee: int, deadline: int,
                modifications: int, relative_change: int):
    m = NEMSignTx()
    m.transaction = NEMTransactionCommon()
    m.transaction.network = network
    m.transaction.timestamp = timestamp
    m.transaction.fee = fee
    m.transaction.deadline = deadline

    m.aggregate_modification = NEMAggregateModification()
    for i in range(modifications):
        m.aggregate_modification.modifications.append(NEMCosignatoryModification())
    m.aggregate_modification.relative_change = relative_change
    return m


if __name__ == '__main__':
    unittest.main()
