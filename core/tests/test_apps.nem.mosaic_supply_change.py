from common import *

from trezor.crypto import hashlib

if not utils.BITCOIN_ONLY:
    from apps.nem.helpers import *
    from apps.nem.mosaic import *
    from apps.nem.mosaic.serialize import *
    from trezor.messages import NEMSignTx
    from trezor.messages import NEMMosaicSupplyChange


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestNemMosaicSupplyChange(unittest.TestCase):

    def test_nem_transaction_create_mosaic_supply_change(self):

        # http://bigalice2.nem.ninja:7890/transaction/get?hash=33a50fdd4a54913643a580b2af08b9a5b51b7cee922bde380e84c573a7969c50
        m = _create_msg(NEM_NETWORK_TESTNET,
                        14071648,
                        108000000,
                        14075248,
                        "gimre.games.pong",
                        "paddles",
                        1,
                        1234)
        t = serialize_mosaic_supply_change(m.transaction, m.supply_change, unhexlify("994793ba1c789fa9bdea918afc9b06e2d0309beb1081ac5b6952991e4defd324"))

        self.assertEqual(hashlib.sha3_256(t, keccak=True).digest(),
                         unhexlify('33a50fdd4a54913643a580b2af08b9a5b51b7cee922bde380e84c573a7969c50'))

        # http://bigalice2.nem.ninja:7890/transaction/get?hash=1ce8e8894d077a66ff22294b000825d090a60742ec407efd80eb8b19657704f2
        m = _create_msg(NEM_NETWORK_TESTNET,
                        14126909,
                        108000000,
                        14130509,
                        "jabo38_ltd.fuzzy_kittens_cafe",
                        "coupons",
                        2,
                        1)
        t = serialize_mosaic_supply_change(m.transaction, m.supply_change, unhexlify("84afa1bbc993b7f5536344914dde86141e61f8cbecaf8c9cefc07391f3287cf5"))

        self.assertEqual(hashlib.sha3_256(t, keccak=True).digest(),
                         unhexlify('1ce8e8894d077a66ff22294b000825d090a60742ec407efd80eb8b19657704f2'))

        # http://bigalice3.nem.ninja:7890/transaction/get?hash=694e493e9576d2bcf60d85747e302ac2e1cc27783187947180d4275a713ff1ff
        m = _create_msg(NEM_NETWORK_MAINNET,
                        53377685,
                        20000000,
                        53464085,
                        "abvapp",
                        "abv",
                        1,
                        9000000)
        t = serialize_mosaic_supply_change(m.transaction, m.supply_change, unhexlify("b7ccc27b21ba6cf5c699a8dc86ba6ba98950442597ff9fa30e0abe0f5f4dd05d"))

        self.assertEqual(hashlib.sha3_256(t, keccak=True).digest(),
                         unhexlify('694e493e9576d2bcf60d85747e302ac2e1cc27783187947180d4275a713ff1ff'))

        # http://bigalice3.nem.ninja:7890/transaction/get?hash=09836334e123970e068d5b411e4d1df54a3ead10acf1ad5935a2cdd9f9680185
        m = _create_msg(NEM_NETWORK_MAINNET,
                        55176304,
                        20000000,
                        55262704,
                        "sushi",
                        "wasabi",
                        2,
                        20)
        t = serialize_mosaic_supply_change(m.transaction, m.supply_change, unhexlify("75f001a8641e2ce5c4386883dda561399ed346177411b492a677b73899502f13"))

        self.assertEqual(hashlib.sha3_256(t, keccak=True).digest(),
                         unhexlify('09836334e123970e068d5b411e4d1df54a3ead10acf1ad5935a2cdd9f9680185'))


def _create_msg(network: int, timestamp: int, fee: int, deadline: int,
                namespace: str, mosaic: str, mod_type: int, delta: int):
    transaction = NEMTransactionCommon(
        network=network,
        timestamp=timestamp,
        fee=fee,
        deadline=deadline,
    )

    supply_change = NEMMosaicSupplyChange(
        namespace=namespace,
        mosaic=mosaic,
        type=mod_type,
        delta=delta,
    )

    return NEMSignTx(
        transaction=transaction,
        supply_change=supply_change,
    )


if __name__ == '__main__':
    unittest.main()
