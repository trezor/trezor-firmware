from common import *
from trezor import log, loop, utils

if not utils.BITCOIN_ONLY:
    from apps.monero.xmr.serialize.int_serialize import (
        dump_uint,
        dump_uvarint,
        load_uint,
        load_uvarint,
    )
    from apps.monero.xmr.serialize.readwriter import MemoryReaderWriter
    from apps.monero.xmr.serialize_messages.base import ECPoint
    from apps.monero.xmr.serialize_messages.tx_prefix import (
        TxinToKey,
    )


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestMoneroSerializer(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestMoneroSerializer, self).__init__(*args, **kwargs)

    def test_varint(self):
        """
        Var int
        :return:
        """
        # fmt: off
        test_nums = [0, 1, 12, 44, 32, 63, 64, 127, 128, 255, 256, 1023, 1024, 8191, 8192,
                     2**16, 2**16 - 1, 2**32, 2**32 - 1, 2**64, 2**64 - 1, 2**72 - 1, 2**112]
        # fmt: on

        for test_num in test_nums:
            writer = MemoryReaderWriter()

            dump_uvarint(writer, test_num)
            test_deser = load_uvarint(MemoryReaderWriter(writer.get_buffer()))

            self.assertEqual(test_num, test_deser)

    def test_ecpoint(self):
        """
        Ec point
        :return:
        """
        ec_data = bytearray(range(32))
        writer = MemoryReaderWriter()

        ECPoint.dump(writer, ec_data)
        self.assertTrue(len(writer.get_buffer()), ECPoint.SIZE)

        test_deser = ECPoint.load(MemoryReaderWriter(writer.get_buffer()))
        self.assertEqual(ec_data, test_deser)

    def test_txin_to_key(self):
        """
        TxinToKey
        :return:
        """
        msg = TxinToKey(
            amount=123, key_offsets=[1, 2, 3, 2 ** 76], k_image=bytearray(range(32))
        )

        writer = MemoryReaderWriter()
        TxinToKey.dump(writer, msg)
        test_deser = TxinToKey.load(MemoryReaderWriter(writer.get_buffer()))

        self.assertEqual(msg.amount, test_deser.amount)
        self.assertEqual(msg, test_deser)


if __name__ == "__main__":
    unittest.main()
