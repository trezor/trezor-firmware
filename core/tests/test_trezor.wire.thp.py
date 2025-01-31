# flake8: noqa: F403,F405
from common import *  # isort:skip
from mock_wire_interface import MockHID
from trezor import config, io, protobuf
from trezor.crypto.curve import curve25519
from trezor.enums import ThpMessageType
from trezor.wire.errors import UnexpectedMessage
from trezor.wire.protocol_common import Message

if utils.USE_THP:
    from typing import TYPE_CHECKING

    import thp_common
    from storage import cache_thp
    from storage.cache_common import (
        CHANNEL_HANDSHAKE_HASH,
        CHANNEL_KEY_RECEIVE,
        CHANNEL_KEY_SEND,
        CHANNEL_NONCE_RECEIVE,
        CHANNEL_NONCE_SEND,
    )
    from trezor.crypto import elligator2
    from trezor.enums import ThpPairingMethod
    from trezor.messages import (
        ThpCodeEntryChallenge,
        ThpCodeEntryCpaceHostTag,
        ThpCredentialRequest,
        ThpEndRequest,
        ThpPairingRequest,
    )
    from trezor.wire.thp import (
        ChannelState,
        checksum,
        interface_manager,
        memory_manager,
        thp_main,
    )
    from trezor.wire.thp.crypto import Handshake
    from trezor.wire.thp.pairing_context import PairingContext

    from apps.thp import pairing

    if TYPE_CHECKING:
        from trezor.wire import WireInterface

    def get_dummy_key() -> bytes:
        return b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x10\x01\x02\x03\x04\x05\x06\x07\x08\x09\x20\x01\x02\x03\x04\x05\x06\x07\x08\x09\x30\x31"

    def dummy_encode_iface(iface: WireInterface):
        return thp_common._MOCK_INTERFACE_HID

    def send_channel_allocation_request(
        interface: MockHID, nonce: bytes | None = None
    ) -> bytes:
        if nonce is None or len(nonce) != 8:
            nonce = b"\x00\x11\x22\x33\x44\x55\x66\x77"
        header = b"\x40\xff\xff\x00\x0c"
        chksum = checksum.compute(header + nonce)
        cid_req = header + nonce + chksum
        gen = thp_main.thp_main_loop(interface)
        expected_channel_index = cache_thp._get_next_channel_index()
        gen.send(None)
        interface.mock_read(cid_req, gen)
        gen.send(None)
        model = bytes(utils.INTERNAL_MODEL, "big")
        response_data = (
            b"\x0a\x04" + model + "\x10\x00\x18\x00\x20\x02\x28\x02\x28\x03\x28\x04"
        )
        response_without_crc = (
            b"\x41\xff\xff\x00\x20"
            + nonce
            + cache_thp._CHANNELS[expected_channel_index].channel_id
            + response_data
        )
        chkcsum = checksum.compute(response_without_crc)
        expected_response = response_without_crc + chkcsum + b"\x00" * 27
        return expected_response

    def get_channel_id_from_response(channel_allocation_response: bytes) -> int:
        return int.from_bytes(channel_allocation_response[13:15], "big")

    def get_ack(channel_id: bytes) -> bytes:
        if len(channel_id) != 2:
            raise Exception("Channel id should by two bytes long")
        return (
            b"\x20"
            + channel_id
            + b"\x00\x04"
            + checksum.compute(b"\x20" + channel_id + b"\x00\x04")
            + b"\x00" * 55
        )


@unittest.skipUnless(utils.USE_THP, "only needed for THP")
class TestTrezorHostProtocol(unittest.TestCase):

    def __init__(self):
        if __debug__:
            thp_common.suppres_debug_log()
        interface_manager.encode_iface = dummy_encode_iface
        super().__init__()

    def setUp(self):
        self.interface = MockHID(0xDEADBEEF)
        memory_manager.READ_BUFFER = bytearray(64)
        memory_manager.WRITE_BUFFER = bytearray(256)
        interface_manager.decode_iface = thp_common.dummy_decode_iface

    def test_codec_message(self):
        self.assertEqual(len(self.interface.data), 0)
        gen = thp_main.thp_main_loop(self.interface)
        gen.send(None)

        # There should be a failiure response to received init packet (starts with "?##")
        test_codec_message = b"?## Some data"
        self.interface.mock_read(test_codec_message, gen)
        gen.send(None)
        self.assertEqual(len(self.interface.data), 1)

        expected_response = b"?##\x00\x03\x00\x00\x00\x14\x08\x10"
        self.assertEqual(
            self.interface.data[-1][: len(expected_response)], expected_response
        )

        # There should be no response for continuation packet (starts with "?" only)
        test_codec_message_2 = b"? Cont packet"
        self.interface.mock_read(test_codec_message_2, gen)

        # Check that sending None fails on AssertionError
        with self.assertRaises(AssertionError):
            gen.send(None)
        self.assertEqual(len(self.interface.data), 1)

    def test_message_on_unallocated_channel(self):
        gen = thp_main.thp_main_loop(self.interface)
        query = gen.send(None)
        self.assertObjectEqual(query, self.interface.wait_object(io.POLL_READ))
        message_to_channel_789a = (
            b"\x04\x78\x9a\x00\x0c\x00\x11\x22\x33\x44\x55\x66\x77\x96\x64\x3c\x6c"
        )
        self.interface.mock_read(message_to_channel_789a, gen)
        gen.send(None)
        unallocated_chanel_error_on_channel_789a = "42789a0005027b743563000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
        self.assertEqual(
            utils.get_bytes_as_str(self.interface.data[-1]),
            unallocated_chanel_error_on_channel_789a,
        )

    def tbd_channel_allocation(self):
        self.assertEqual(len(thp_main._CHANNELS), 0)
        for c in cache_thp._CHANNELS:
            self.assertEqual(int.from_bytes(c.state, "big"), ChannelState.UNALLOCATED)

        expected_channel_index = cache_thp._get_next_channel_index()
        expected_response = send_channel_allocation_request(self.interface)
        self.assertEqual(self.interface.data[-1], expected_response)

        cid = cache_thp._CHANNELS[expected_channel_index].channel_id
        self.assertTrue(int.from_bytes(cid, "big") in thp_main._CHANNELS)
        self.assertEqual(len(thp_main._CHANNELS), 1)
        # test channel's default state is TH1:
        cid = get_channel_id_from_response(self.interface.data[-1])
        self.assertEqual(thp_main._CHANNELS[cid].get_channel_state(), ChannelState.TH1)

    def tbd_invalid_encrypted_tag(self):
        gen = thp_main.thp_main_loop(self.interface)
        gen.send(None)
        # prepare 2 new channels
        expected_response_1 = send_channel_allocation_request(self.interface)
        expected_response_2 = send_channel_allocation_request(self.interface)
        self.assertEqual(self.interface.data[-2], expected_response_1)
        self.assertEqual(self.interface.data[-1], expected_response_2)

        # test invalid encryption tag
        config.init()
        config.wipe()
        cid_1 = get_channel_id_from_response(expected_response_1)
        channel = thp_main._CHANNELS[cid_1]
        channel.iface = self.interface
        channel.set_channel_state(ChannelState.ENCRYPTED_TRANSPORT)
        header = b"\x04" + channel.channel_id + b"\x00\x14"

        tag = b"\x00" * 16
        chksum = checksum.compute(header + tag)
        message_with_invalid_tag = header + tag + chksum

        channel.channel_cache.set(CHANNEL_KEY_RECEIVE, get_dummy_key())
        channel.channel_cache.set_int(CHANNEL_NONCE_RECEIVE, 0)

        cid_1_bytes = int.to_bytes(cid_1, 2, "big")
        expected_ack_on_received_message = get_ack(cid_1_bytes)

        self.interface.mock_read(message_with_invalid_tag, gen)
        gen.send(None)

        self.assertEqual(
            self.interface.data[-1],
            expected_ack_on_received_message,
        )
        error_without_crc = b"\x42" + cid_1_bytes + b"\x00\x05\x03"
        chksum_err = checksum.compute(error_without_crc)
        gen.send(None)

        decryption_failed_error = error_without_crc + chksum_err + b"\x00" * 54

        self.assertEqual(
            self.interface.data[-1],
            decryption_failed_error,
        )

    def tbd_test_channel_errors(self):
        gen = thp_main.thp_main_loop(self.interface)
        gen.send(None)
        # prepare 2 new channels
        expected_response_1 = send_channel_allocation_request(self.interface)
        expected_response_2 = send_channel_allocation_request(self.interface)
        self.assertEqual(self.interface.data[-2], expected_response_1)
        self.assertEqual(self.interface.data[-1], expected_response_2)

        # test invalid encryption tag
        config.init()
        config.wipe()
        cid_1 = get_channel_id_from_response(expected_response_1)
        channel = thp_main._CHANNELS[cid_1]
        channel.iface = self.interface
        channel.set_channel_state(ChannelState.ENCRYPTED_TRANSPORT)
        header = b"\x04" + channel.channel_id + b"\x00\x14"

        tag = b"\x00" * 16
        chksum = checksum.compute(header + tag)
        message_with_invalid_tag = header + tag + chksum

        channel.channel_cache.set(CHANNEL_KEY_RECEIVE, get_dummy_key())
        channel.channel_cache.set_int(CHANNEL_NONCE_RECEIVE, 0)

        cid_1_bytes = int.to_bytes(cid_1, 2, "big")
        # expected_ack_on_received_message = get_ack(cid_1_bytes)

        self.interface.mock_read(message_with_invalid_tag, gen)
        # gen.send(None)

        # self.assertEqual(
        #     self.interface.data[-1],
        #     expected_ack_on_received_message,
        # )
        error_without_crc = b"\x42" + cid_1_bytes + b"\x00\x05\x03"
        chksum_err = checksum.compute(error_without_crc)
        # gen.send(None)

        decryption_failed_error = error_without_crc + chksum_err + b"\x00" * 54

        self.assertEqual(
            self.interface.data[-1],
            decryption_failed_error,
        )

        # test invalid tag in handshake phase
        cid_2 = get_channel_id_from_response(expected_response_1)
        # cid_2_bytes = cid_2.to_bytes(2, "big")
        channel = thp_main._CHANNELS[cid_2]
        channel.iface = self.interface

        channel.set_channel_state(ChannelState.TH2)

        message_with_invalid_tag = b"\x0a\x12\x36\x00\x14\x00\x11\x22\x33\x44\x55\x66\x77\x00\x11\x22\x33\x44\x55\x66\x77\x91\x65\x4c\xf9"

        channel.channel_cache.set(CHANNEL_KEY_RECEIVE, get_dummy_key())
        channel.channel_cache.set_int(CHANNEL_NONCE_RECEIVE, 0)

        # gen.send(message_with_invalid_tag)
        # gen.send(None)
        # gen.send(None)
        # for i in self.interface.data:
        #    print(utils.get_bytes_as_str(i))

    def tbd_skip_pairing(self):
        config.init()
        config.wipe()
        channel = next(iter(thp_main._CHANNELS.values()))
        channel.selected_pairing_methods = [
            ThpPairingMethod.SkipPairing,
            ThpPairingMethod.CodeEntry,
            ThpPairingMethod.NFC_Unidirectional,
            ThpPairingMethod.QrCode,
        ]
        pairing_ctx = PairingContext(channel)
        request_message = ThpPairingRequest()
        channel.set_channel_state(ChannelState.TP1)
        gen = pairing.handle_pairing_request(pairing_ctx, request_message)

        with self.assertRaises(StopIteration):
            gen.send(None)
        self.assertEqual(channel.get_channel_state(), ChannelState.ENCRYPTED_TRANSPORT)

        # Teardown: set back initial channel state value
        channel.set_channel_state(ChannelState.TH1)

    def TODO_test_pairing(self):
        config.init()
        config.wipe()
        cid = get_channel_id_from_response(
            send_channel_allocation_request(self.interface)
        )
        channel = thp_main._CHANNELS[cid]
        channel.selected_pairing_methods = [
            ThpPairingMethod.CodeEntry,
            ThpPairingMethod.NFC,
            ThpPairingMethod.QrCode,
        ]
        pairing_ctx = PairingContext(channel)
        request_message = ThpPairingRequest()
        with self.assertRaises(UnexpectedMessage) as e:
            pairing.handle_pairing_request(pairing_ctx, request_message)
        print(e.value.message)
        channel.set_channel_state(ChannelState.TP1)
        gen = pairing.handle_pairing_request(pairing_ctx, request_message)

        channel.channel_cache.set(CHANNEL_KEY_SEND, get_dummy_key())
        channel.channel_cache.set_int(CHANNEL_NONCE_SEND, 0)
        channel.channel_cache.set(CHANNEL_HANDSHAKE_HASH, b"")

        gen.send(None)

        async def _dummy(ctx: PairingContext, expected_types):
            return await ctx.read([1018, 1024])

        # pairing.show_display_data = _dummy

        msg_code_entry = ThpCodeEntryChallenge(challenge=b"\x12\x34")
        buffer: bytearray = bytearray(protobuf.encoded_length(msg_code_entry))
        protobuf.encode(buffer, msg_code_entry)
        code_entry_challenge = Message(ThpMessageType.ThpCodeEntryChallenge, buffer)
        self.interface.mock_read(code_entry_challenge, gen)

        # tag_qrc = b"\x55\xdf\x6c\xba\x0b\xe9\x5e\xd1\x4b\x78\x61\xec\xfa\x07\x9b\x5d\x37\x60\xd8\x79\x9c\xd7\x89\xb4\x22\xc1\x6f\x39\xde\x8f\x3b\xc3"
        # tag_nfc = b"\x8f\xf0\xfa\x37\x0a\x5b\xdb\x29\x32\x21\xd8\x2f\x95\xdd\xb6\xb8\xee\xfd\x28\x6f\x56\x9f\xa9\x0b\x64\x8c\xfc\x62\x46\x5a\xdd\xd0"

        pregenerator_host = b"\xf6\x94\xc3\x6f\xb3\xbd\xfb\xba\x2f\xfd\x0c\xd0\x71\xed\x54\x76\x73\x64\x37\xfa\x25\x85\x12\x8d\xcf\xb5\x6c\x02\xaf\x9d\xe8\xbe"
        generator_host = elligator2.map_to_curve25519(pregenerator_host)
        cpace_host_private_key = b"\x02\x80\x70\x3c\x06\x45\x19\x75\x87\x0c\x82\xe1\x64\x11\xc0\x18\x13\xb2\x29\x04\xb3\xf0\xe4\x1e\x6b\xfd\x77\x63\x11\x73\x07\xa9"
        cpace_host_public_key: bytes = curve25519.multiply(
            cpace_host_private_key, generator_host
        )
        msg = ThpCodeEntryCpaceHost(cpace_host_public_key=cpace_host_public_key)

        # msg = ThpQrCodeTag(tag=tag_qrc)
        # msg = ThpNfcTagHost(tag=tag_nfc)
        buffer: bytearray = bytearray(protobuf.encoded_length(msg))

        protobuf.encode(buffer, msg)
        user_message = Message(ThpMessageType.ThpCodeEntryCpaceHost, buffer)
        self.interface.mock_read(user_message, gen)

        tag_ent = b"\xd0\x15\xd6\x72\x7c\xa6\x9b\x2a\x07\xfa\x30\xee\x03\xf0\x2d\x04\xdc\x96\x06\x77\x0c\xbd\xb4\xaa\x77\xc7\x68\x6f\xae\xa9\xdd\x81"
        msg = ThpCodeEntryTag(tag=tag_ent)

        buffer: bytearray = bytearray(protobuf.encoded_length(msg))

        protobuf.encode(buffer, msg)
        user_message = Message(ThpMessageType.ThpCodeEntryTag, buffer)
        self.interface.mock_read(user_message, gen)

        host_static_pubkey = b"\x00\x11\x22\x33\x44\x55\x66\x77\x00\x11\x22\x33\x44\x55\x66\x77\x00\x11\x22\x33\x44\x55\x66\x77\x00\x11\x22\x33\x44\x55\x66\x77\x00\x11\x22\x33\x44\x55\x66\x77\x00\x11\x22\x33\x44\x55\x66\x77"
        msg = ThpCredentialRequest(host_static_pubkey=host_static_pubkey)
        buffer: bytearray = bytearray(protobuf.encoded_length(msg))
        protobuf.encode(buffer, msg)
        credential_request = Message(ThpMessageType.ThpCredentialRequest, buffer)
        self.interface.mock_read(credential_request, gen)

        msg = ThpEndRequest()

        buffer: bytearray = bytearray(protobuf.encoded_length(msg))
        protobuf.encode(buffer, msg)
        end_request = Message(1012, buffer)
        with self.assertRaises(StopIteration) as e:
            self.interface.mock_read(end_request, gen)
        print("response message:", e.value.value.MESSAGE_NAME)


if __name__ == "__main__":
    unittest.main()
