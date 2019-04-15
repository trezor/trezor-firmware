import utest
from common import *
from trezor import log, loop, utils

from apps.monero.xmr.serialize.int_serialize import (
    dump_uint,
    dump_uvarint,
    load_uint,
    load_uvarint,
)
from apps.monero.xmr.serialize.readwriter import MemoryReaderWriter
from apps.monero.xmr.serialize_messages.base import ECPoint
from apps.monero.xmr.serialize_messages.tx_prefix import (
    TxinGen,
    TxinToKey,
    TxInV,
    TxOut,
    TxoutToKey,
)


class XmrTstData(object):
    """Simple tests data generator"""

    def __init__(self, *args, **kwargs):
        super(XmrTstData, self).__init__()
        self.ec_offset = 0

    def reset(self):
        self.ec_offset = 0

    def generate_ec_key(self, use_offset=True):
        """
        Returns test EC key, 32 element byte array
        :param use_offset:
        :return:
        """
        offset = 0
        if use_offset:
            offset = self.ec_offset
            self.ec_offset += 1

        return bytearray(range(offset, offset + 32))

    def gen_transaction_prefix(self):
        """
        Returns test transaction prefix
        :return:
        """
        vin = [
            TxinToKey(
                amount=123, key_offsets=[1, 2, 3, 2 ** 76], k_image=bytearray(range(32))
            ),
            TxinToKey(
                amount=456, key_offsets=[9, 8, 7, 6], k_image=bytearray(range(32, 64))
            ),
            TxinGen(height=99),
        ]

        vout = [
            TxOut(amount=11, target=TxoutToKey(key=bytearray(range(32)))),
            TxOut(amount=34, target=TxoutToKey(key=bytearray(range(64, 96)))),
        ]

        msg = TransactionPrefix(
            version=2, unlock_time=10, vin=vin, vout=vout, extra=list(range(31))
        )
        return msg


class TestMoneroSerializer(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestMoneroSerializer, self).__init__(*args, **kwargs)
        self.tdata = XmrTstData()

    def setUp(self):
        self.tdata.reset()

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

    def test_simple_msg(self):
        """
        TxinGen
        :return:
        """
        msg = TxinGen(height=42)

        writer = MemoryReaderWriter()
        TxinGen.dump(writer, msg)
        test_deser = TxinGen.load(MemoryReaderWriter(writer.get_buffer()))

        self.assertEqual(msg.height, test_deser.height)

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

    def test_txin_variant(self):
        """
        TxInV
        :return:
        """
        msg1 = TxinToKey(
            amount=123, key_offsets=[1, 2, 3, 2 ** 76], k_image=bytearray(range(32))
        )

        writer = MemoryReaderWriter()
        TxInV.dump(writer, msg1)
        test_deser = TxInV.load(MemoryReaderWriter(writer.get_buffer()))

        self.assertEqual(test_deser.__class__, TxinToKey)
        self.assertEqual(msg1, test_deser)


if __name__ == "__main__":
    unittest.main()
