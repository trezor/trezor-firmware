# flake8: noqa: F403,F405
from common import *  # isort:skip

if utils.USE_THP:
    import trezorthp
    from mock import Mock, patch
    from mock_wire_interface import MockHID
    from storage import device
    from trezor import config, loop
    from trezor.wire.thp import crypto, interface_context
    from trezor.wire.thp.interface_context import InterfaceContext, ThpContext

    # Public identities recorded using the original HDNode derivation.
    VECTORS = (
        (bytes(16), "cc6436c3681de6602d80e782e3e0a023e59e7fbd20d77ab8806ed15e80e77843"),
        (
            bytes(range(16)),
            "4288cccef083658378cbf154a86ffd3376325d733304d2850076020be6e23974",
        ),
        (
            b"\xff" * 16,
            "61ab2fc9e91180a1c0cf004fceed95be08a141585a17f36f9ec0e8679578a11e",
        ),
    )

    class TestThpIdentity(unittest.TestCase):
        def setUp(self):
            config.init()
            config.wipe()
            self.assertTrue(config.unlock("", None))

        def tearDown(self):
            loop.clear()

        def test_legacy_public_identity_without_wallet_owner(self):
            for secret, expected in VECTORS:
                public = trezorthp.static_public_key(secret)
                self.assertIsInstance(public, bytes)
                self.assertEqual(public.hex(), expected)
                with patch(device, "get_device_secret", lambda: secret):
                    self.assertEqual(crypto.get_trezor_static_public_key(), public)

        def test_invalid_device_secret(self):
            for length in (0, 1, 15, 17, 32, 64):
                with self.assertRaises(ValueError):
                    trezorthp.static_public_key(bytes(length))
                with self.assertRaises(ValueError):
                    trezorthp.handshake_key_from_device_secret(42, bytes(length))
            self.assertEqual(
                trezorthp.static_public_key(VECTORS[0][0]).hex(), VECTORS[0][1]
            )

        def test_read_loop_survives_key_failure(self):
            iface = MockHID()
            proxy = Mock()
            proxy.init = lambda *_: None
            with patch(interface_context, "trezorthp", proxy):
                with patch(
                    interface_context, "get_encoded_device_properties", lambda _: b""
                ):
                    ctx = InterfaceContext(iface, ThpContext())
            reader = ctx.read_loop()
            calls = []
            native_handshake_key = trezorthp.handshake_key_from_device_secret

            def supply_key(iface_num, secret):
                calls.append((iface_num, secret))
                native_handshake_key(iface_num, secret)

            attempts = [0]

            def get_secret():
                attempts[0] += 1
                if attempts[0] == 1:
                    raise ValueError("injected device-secret failure")
                return VECTORS[0][0]

            proxy.packet_in = lambda *_: trezorthp.KEY_REQUIRED
            proxy.handshake_key_from_device_secret = supply_key
            with patch(device, "get_device_secret", get_secret):
                with patch(interface_context, "trezorthp", proxy):
                    next(reader)
                    iface.mock_read(bytes(64), reader)
                    self.assertEqual(calls, [(42, None)])
                    iface.mock_read(bytes(64), reader)
                    self.assertEqual(calls, [(42, None), (42, VECTORS[0][0])])
            reader.close()


if __name__ == "__main__":
    unittest.main()
