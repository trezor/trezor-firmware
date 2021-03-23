from common import *

from trezor.crypto import hashlib

if not utils.BITCOIN_ONLY:
    from trezor.messages import NEMSignTx
    from trezor.messages import NEMMosaicCreation
    from trezor.messages import NEMMosaicDefinition
    from apps.nem.helpers import *
    from apps.nem.mosaic import *
    from apps.nem.mosaic.serialize import *


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestNemMosaicCreation(unittest.TestCase):

    def test_nem_transaction_mosaic_creation(self):

        #  http://bob.nem.ninja:8765/#/mosaic/68364353c29105e6d361ad1a42abbccbf419cfc7adb8b74c8f35d8f8bdaca3fa/0
        m = _create_msg(NEM_NETWORK_TESTNET,
                        14070896,
                        108000000,
                        14074496,
                        'gimre.games.pong',
                        'paddles',
                        'Paddles for the bong game.\n',
                        0,
                        10000,
                        True,
                        True,
                        0,
                        0,
                        '',
                        '',
                        '',
                        'TBMOSAICOD4F54EE5CDMR23CCBGOAM2XSJBR5OLC',
                        50000000000)

        t = serialize_mosaic_creation(m.transaction, m.mosaic_creation, unhexlify('994793ba1c789fa9bdea918afc9b06e2d0309beb1081ac5b6952991e4defd324'))

        self.assertEqual(t, unhexlify('014000000100009870b4d60020000000994793ba1c789fa9bdea918afc9b06e2d0309beb1081ac5b6952991e4defd32400f36f060000000080c2d600de00000020000000994793ba1c789fa9bdea918afc9b06e2d0309beb1081ac5b6952991e4defd3241f0000001000000067696d72652e67616d65732e706f6e6707000000706164646c65731b000000506164646c657320666f722074686520626f6e672067616d652e0a04000000150000000c00000064697669736962696c69747901000000301a0000000d000000696e697469616c537570706c79050000003130303030190000000d000000737570706c794d757461626c650400000074727565180000000c0000007472616e7366657261626c650400000074727565000000002800000054424d4f534149434f443446353445453543444d523233434342474f414d3258534a4252354f4c4300743ba40b000000'))
        self.assertEqual(hashlib.sha3_256(t, keccak=True).digest(), unhexlify('68364353c29105e6d361ad1a42abbccbf419cfc7adb8b74c8f35d8f8bdaca3fa'))

    def test_nem_transaction_mosaic_creation_with_levy(self):
        # http://bob.nem.ninja:8765/#/mosaic/b2f4a98113ff1f3a8f1e9d7197aa982545297fe0aa3fa6094af8031569953a55/0
        m = _create_msg(NEM_NETWORK_TESTNET,
                        21497248,
                        108000000,
                        21500848,
                        "alice.misc",
                        "bar",
                        "Special offer: get one bar extra by bying one foo!",
                        0,
                        1000,
                        False,
                        True,
                        1,
                        1,
                        "TALICE2GMA34CXHD7XLJQ536NM5UNKQHTORNNT2J",
                        "nem",
                        "xem",
                        "TBMOSAICOD4F54EE5CDMR23CCBGOAM2XSJBR5OLC",
                        50000000000)

        t = serialize_mosaic_creation(m.transaction, m.mosaic_creation, unhexlify("244fa194e2509ac0d2fbc18779c2618d8c2ebb61c16a3bcbebcf448c661ba8dc"),)

        self.assertEqual(hashlib.sha3_256(t, keccak=True).digest(), unhexlify('b2f4a98113ff1f3a8f1e9d7197aa982545297fe0aa3fa6094af8031569953a55'))

        # http://chain.nem.ninja/#/mosaic/e8dc14821dbea4831d9051f86158ef348001447968fc22c01644fdaf2bda75c6/0
        m = _create_msg(NEM_NETWORK_MAINNET,
                        69251020,
                        20000000,
                        69337420,
                        "dim",
                        "coin",
                        "DIM COIN",
                        6,
                        9000000000,
                        False,
                        True,
                        2,
                        10,
                        "NCGGLVO2G3CUACVI5GNX2KRBJSQCN4RDL2ZWJ4DP",
                        "dim",
                        "coin",
                        "NBMOSAICOD4F54EE5CDMR23CCBGOAM2XSIUX6TRS",
                        500000000)

        t = serialize_mosaic_creation(m.transaction, m.mosaic_creation, unhexlify("a1df5306355766bd2f9a64efdc089eb294be265987b3359093ae474c051d7d5a"))
        self.assertEqual(t, unhexlify('0140000001000068ccaf200420000000a1df5306355766bd2f9a64efdc089eb294be265987b3359093ae474c051d7d5a002d3101000000004c0122040c01000020000000a1df5306355766bd2f9a64efdc089eb294be265987b3359093ae474c051d7d5a0f0000000300000064696d04000000636f696e0800000044494d20434f494e04000000150000000c00000064697669736962696c69747901000000361f0000000d000000696e697469616c537570706c790a000000393030303030303030301a0000000d000000737570706c794d757461626c650500000066616c7365180000000c0000007472616e7366657261626c6504000000747275654b00000002000000280000004e4347474c564f32473343554143564935474e58324b52424a5351434e3452444c325a574a3444500f0000000300000064696d04000000636f696e0a00000000000000280000004e424d4f534149434f443446353445453543444d523233434342474f414d325853495558365452530065cd1d00000000'))
        self.assertEqual(hashlib.sha3_256(t, keccak=True).digest(), unhexlify('e8dc14821dbea4831d9051f86158ef348001447968fc22c01644fdaf2bda75c6'))

    def test_nem_transaction_mosaic_creation_with_description(self):
        # http://chain.nem.ninja/#/mosaic/269c6fda657aba3053a0e5b138c075808cc20e244e1182d9b730798b60a1f77b/0
        m = _create_msg(NEM_NETWORK_MAINNET,
                        26729938,
                        108000000,
                        26733538,
                        "jabo38",
                        "red_token",
                        "This token is to celebrate the release of Namespaces and Mosaics "
                        "on the NEM system. This token was the fist ever mosaic created "
                        "other than nem.xem. There are only 10,000 Red Tokens that will "
                        "ever be created. It has no levy and can be traded freely among "
                        "third parties.",
                        2,
                        10000,
                        False,
                        True,
                        0,
                        0,
                        "",
                        "",
                        "",
                        "NBMOSAICOD4F54EE5CDMR23CCBGOAM2XSIUX6TRS",
                        50000000000)
        t = serialize_mosaic_creation(m.transaction, m.mosaic_creation, unhexlify("58956ac77951622dc5f1c938affbf017c458e30e6b21ddb5783d38b302531f23"))

        self.assertEqual(t, unhexlify('0140000001000068d2dd97012000000058956ac77951622dc5f1c938affbf017c458e30e6b21ddb5783d38b302531f2300f36f0600000000e2eb9701c80100002000000058956ac77951622dc5f1c938affbf017c458e30e6b21ddb5783d38b302531f2317000000060000006a61626f3338090000007265645f746f6b656e0c0100005468697320746f6b656e20697320746f2063656c656272617465207468652072656c65617365206f66204e616d6573706163657320616e64204d6f7361696373206f6e20746865204e454d2073797374656d2e205468697320746f6b656e207761732074686520666973742065766572206d6f736169632063726561746564206f74686572207468616e206e656d2e78656d2e20546865726520617265206f6e6c792031302c3030302052656420546f6b656e7320746861742077696c6c206576657220626520637265617465642e20497420686173206e6f206c65767920616e642063616e2062652074726164656420667265656c7920616d6f6e6720746869726420706172746965732e04000000150000000c00000064697669736962696c69747901000000321a0000000d000000696e697469616c537570706c790500000031303030301a0000000d000000737570706c794d757461626c650500000066616c7365180000000c0000007472616e7366657261626c65040000007472756500000000280000004e424d4f534149434f443446353445453543444d523233434342474f414d3258534955583654525300743ba40b000000'))
        self.assertEqual(hashlib.sha3_256(t, keccak=True).digest(), unhexlify('269c6fda657aba3053a0e5b138c075808cc20e244e1182d9b730798b60a1f77b'))


def _create_msg(network: int, timestamp: int, fee: int, deadline: int,
                namespace: str, mosaic: str, description: str,
                divisibility: int, supply: int, mutable_supply: bool, transferable: bool,
                levy_type: int, levy_fee: int, levy_address: str, levy_namespace: str,
                levy_mosaic: str, creation_sink: str, creation_fee: int):
    m = NEMSignTx()
    m.transaction = NEMTransactionCommon()
    m.transaction.network = network
    m.transaction.timestamp = timestamp
    m.transaction.fee = fee
    m.transaction.deadline = deadline

    m.mosaic_creation = NEMMosaicCreation()
    m.mosaic_creation.sink = creation_sink
    m.mosaic_creation.fee = creation_fee

    m.mosaic_creation.definition = NEMMosaicDefinition()
    m.mosaic_creation.definition.namespace = namespace
    m.mosaic_creation.definition.mosaic = mosaic
    m.mosaic_creation.definition.description = description
    m.mosaic_creation.definition.divisibility = divisibility
    m.mosaic_creation.definition.supply = supply
    m.mosaic_creation.definition.mutable_supply = mutable_supply
    m.mosaic_creation.definition.transferable = transferable
    m.mosaic_creation.definition.levy = levy_type
    m.mosaic_creation.definition.fee = levy_fee
    m.mosaic_creation.definition.levy_address = levy_address
    m.mosaic_creation.definition.levy_namespace = levy_namespace
    m.mosaic_creation.definition.levy_mosaic = levy_mosaic
    return m


if __name__ == '__main__':
    unittest.main()
