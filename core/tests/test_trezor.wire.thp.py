from common import *

from apps.thp import pairing
from storage.cache_common import (
    CHANNEL_HANDSHAKE_HASH,
    CHANNEL_KEY_RECEIVE,
    CHANNEL_KEY_SEND,
    CHANNEL_NONCE_RECEIVE,
    CHANNEL_NONCE_SEND,
)
from trezor.enums import ThpPairingMethod, MessageType
from trezor.wire.errors import UnexpectedMessage
from trezor.wire.protocol_common import Message
from trezor.wire.thp.crypto import Handshake
from trezor.wire.thp.pairing_context import PairingContext
from trezor.messages import (
    ThpCodeEntryChallenge,
    ThpCodeEntryCpaceHost,
    ThpCodeEntryTag,
    ThpCredentialRequest,
    ThpEndRequest,
    ThpStartPairingRequest,
)
from trezor import io, config, log, protobuf
from trezor.loop import wait
from trezor.wire import thp_v3
from trezor.wire.thp import interface_manager
from storage import cache_thp
from trezor.wire.thp import ChannelState
from trezor.crypto import elligator2
from trezor.crypto.curve import curve25519


# Disable log.debug for the test
log.debug = lambda name, msg, *args: None
class MockHID:
    def __init__(self, num):
        self.num = num
        self.data = []

    def iface_num(self):
        return self.num

    def write(self, msg):
        self.data.append(bytearray(msg))
        return len(msg)

    def wait_object(self, mode):
        return wait(mode | self.num)


def dummy_decode_iface(cached_iface: bytes):
    return MockHID(0xDEADBEEF)


def getBytes(a):
    return hexlify(a).decode("utf-8")


def get_dummy_key() -> bytes:
    return b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x10\x01\x02\x03\x04\x05\x06\x07\x08\x09\x20\x01\x02\x03\x04\x05\x06\x07\x08\x09\x30\x31"


class TestTrezorHostProtocol(unittest.TestCase):
    def setUp(self):
        self.interface = MockHID(0xDEADBEEF)
        buffer = bytearray(64)
        thp_v3.set_buffer(buffer)
        interface_manager.decode_iface = dummy_decode_iface

    def test_simple(self):
        self.assertTrue(True)

    def test_channel_allocation(self):
        cid_req = (
            b"\x40\xff\xff\x00\x0c\x00\x11\x22\x33\x44\x55\x66\x77\x96\x64\x3c\x6c"
        )
        expected_response = "41ffff0020001122334455667712340a04543254311000180020032802280328048ed892b3000000000000000000000000000000000000000000000000000000"
        test_counter = cache_thp.cid_counter + 1
        self.assertEqual(len(thp_v3._CHANNELS), 0)
        self.assertFalse(test_counter in thp_v3._CHANNELS)
        gen = thp_v3.thp_main_loop(self.interface, is_debug_session=True)
        query = gen.send(None)
        self.assertObjectEqual(query, self.interface.wait_object(io.POLL_READ))
        gen.send(cid_req)
        gen.send(None)
        self.assertEqual(
            getBytes(self.interface.data[-1]),
            expected_response,
        )
        self.assertTrue(test_counter in thp_v3._CHANNELS)
        self.assertEqual(len(thp_v3._CHANNELS), 1)
        gen.send(cid_req)
        gen.send(None)
        gen.send(cid_req)
        gen.send(None)

    def test_channel_default_state_is_TH1(self):
        self.assertEqual(thp_v3._CHANNELS[4660].get_channel_state(), ChannelState.TH1)

    def test_channel_errors(self):
        gen = thp_v3.thp_main_loop(self.interface, is_debug_session=True)
        query = gen.send(None)
        self.assertObjectEqual(query, self.interface.wait_object(io.POLL_READ))
        message_to_channel_789a = (
            b"\x04\x78\x9a\x00\x0c\x00\x11\x22\x33\x44\x55\x66\x77\x96\x64\x3c\x6c"
        )
        gen.send(message_to_channel_789a)
        gen.send(None)
        unallocated_chanel_error_on_channel_789a = "42789a0005027b743563000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
        self.assertEqual(
            getBytes(self.interface.data[-1]),
            unallocated_chanel_error_on_channel_789a,
        )
        config.init()
        config.wipe()
        channel = thp_v3._CHANNELS[4661]
        channel.iface = self.interface
        channel.set_channel_state(ChannelState.ENCRYPTED_TRANSPORT)
        message_with_invalid_tag = b"\x04\x12\x35\x00\x14\x00\x11\x22\x33\x44\x55\x66\x77\x00\x11\x22\x33\x44\x55\x66\x77\xe1\xfc\xc6\xe0"

        channel.channel_cache.set(CHANNEL_KEY_RECEIVE, get_dummy_key())
        channel.channel_cache.set_int(CHANNEL_NONCE_RECEIVE, 0)
        channel.channel_cache.set(CHANNEL_HANDSHAKE_HASH, b"")

        gen.send(message_with_invalid_tag)
        gen.send(None)
        ack_on_received_message = "2012350004d83ea46f00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
        self.assertEqual(
            getBytes(self.interface.data[-1]),
            ack_on_received_message,
        )
        gen.send(None)
        decryption_failed_error_on_channel_1235 = "421235000503caf9634a000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
        self.assertEqual(
            getBytes(self.interface.data[-1]),
            decryption_failed_error_on_channel_1235,
        )

        channel = thp_v3._CHANNELS[4662]
        channel.iface = self.interface

        channel.set_channel_state(ChannelState.TH2)

        message_with_invalid_tag = b"\x0a\x12\x36\x00\x14\x00\x11\x22\x33\x44\x55\x66\x77\x00\x11\x22\x33\x44\x55\x66\x77\x91\x65\x4c\xf9"

        channel.channel_cache.set(CHANNEL_KEY_RECEIVE, get_dummy_key())
        channel.channel_cache.set_int(CHANNEL_NONCE_RECEIVE, 0)
        channel.channel_cache.set(CHANNEL_HANDSHAKE_HASH, b"")

        # gen.send(message_with_invalid_tag)
        # gen.send(None)
        # gen.send(None)
        for i in self.interface.data:
            print(hexlify(i))

    def test_skip_pairing(self):
        config.init()
        config.wipe()
        channel = thp_v3._CHANNELS[4660]
        channel.selected_pairing_methods = [
            ThpPairingMethod.NoMethod,
            ThpPairingMethod.CodeEntry,
            ThpPairingMethod.NFC_Unidirectional,
            ThpPairingMethod.QrCode,
        ]
        pairing_ctx = PairingContext(channel)
        request_message = ThpStartPairingRequest()
        channel.set_channel_state(ChannelState.TP1)
        gen = pairing.handle_pairing_request(pairing_ctx, request_message)

        with self.assertRaises(StopIteration):
            gen.send(None)
        self.assertEqual(channel.get_channel_state(), ChannelState.ENCRYPTED_TRANSPORT)

        # Teardown: set back initial channel state value
        channel.set_channel_state(ChannelState.TH1)

    def test_pairing(self):
        config.init()
        config.wipe()
        channel = thp_v3._CHANNELS[4660]
        channel.selected_pairing_methods = [
            ThpPairingMethod.CodeEntry,
            ThpPairingMethod.NFC_Unidirectional,
            ThpPairingMethod.QrCode,
        ]
        pairing_ctx = PairingContext(channel)
        request_message = ThpStartPairingRequest()
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

        pairing.show_display_data = _dummy

        msg_code_entry = ThpCodeEntryChallenge(challenge=b"\x12\x34")
        buffer: bytearray = bytearray(protobuf.encoded_length(msg_code_entry))
        protobuf.encode(buffer, msg_code_entry)
        code_entry_challenge = Message(MessageType.ThpCodeEntryChallenge, buffer)
        gen.send(code_entry_challenge)

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
        # msg = ThpNfcUnidirectionalTag(tag=tag_nfc)
        buffer: bytearray = bytearray(protobuf.encoded_length(msg))

        protobuf.encode(buffer, msg)
        user_message = Message(MessageType.ThpCodeEntryCpaceHost, buffer)
        gen.send(user_message)

        tag_ent = b"\xf5\x20\xee\xae\xb8\xa9\x65\x3e\x77\x89\x8f\x81\x8d\x03\x4d\xaa\x93\x79\xc3\xe4\x89\x3c\xb8\x31\x42\xdc\x01\x57\x2d\x5d\x11\xb5"

        msg = ThpCodeEntryTag(tag=tag_ent)

        buffer: bytearray = bytearray(protobuf.encoded_length(msg))

        protobuf.encode(buffer, msg)
        user_message = Message(MessageType.ThpCodeEntryTag, buffer)
        gen.send(user_message)

        host_static_pubkey = b"\x00\x11\x22\x33\x44\x55\x66\x77\x00\x11\x22\x33\x44\x55\x66\x77\x00\x11\x22\x33\x44\x55\x66\x77\x00\x11\x22\x33\x44\x55\x66\x77\x00\x11\x22\x33\x44\x55\x66\x77\x00\x11\x22\x33\x44\x55\x66\x77"
        msg = ThpCredentialRequest(host_static_pubkey=host_static_pubkey)
        buffer: bytearray = bytearray(protobuf.encoded_length(msg))
        protobuf.encode(buffer, msg)
        credential_request = Message(MessageType.ThpCredentialRequest, buffer)
        gen.send(credential_request)

        msg = ThpEndRequest()

        buffer: bytearray = bytearray(protobuf.encoded_length(msg))
        protobuf.encode(buffer, msg)
        end_request = Message(1012, buffer)
        with self.assertRaises(StopIteration) as e:
            gen.send(end_request)
        print("response message:", e.value.value.MESSAGE_NAME)


if __name__ == "__main__":
    unittest.main()
