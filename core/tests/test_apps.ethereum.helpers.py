# flake8: noqa: F403,F405
from common import *  # isort:skip

from mock import patch

from trezor import TR

if not utils.BITCOIN_ONLY:
    from ethereum_common import make_eth_network

    from apps.ethereum.helpers import address_from_bytes, get_data_confirmer
    import trezor.ui.layouts as layouts_module


class TestTranslationStringsMock(unittest.TestCase):
    """Tests for the newly added translation string mock values."""

    def test_subtitle_input_data_bytes_value(self):
        self.assertEqual(TR.ethereum__subtitle_input_data_bytes, "{0} / {1} bytes")

    def test_subtitle_input_data_bytes_format(self):
        result = TR.ethereum__subtitle_input_data_bytes.format(27, 100)
        self.assertEqual(result, "27 / 100 bytes")

    def test_subtitle_input_data_bytes_format_zero(self):
        result = TR.ethereum__subtitle_input_data_bytes.format(0, 50)
        self.assertEqual(result, "0 / 50 bytes")

    def test_subtitle_input_data_bytes_format_equal(self):
        # When confirmed == total (last chunk)
        result = TR.ethereum__subtitle_input_data_bytes.format(63, 63)
        self.assertEqual(result, "63 / 63 bytes")

    def test_title_input_data_bytes_value(self):
        self.assertEqual(TR.ethereum__title_input_data_bytes, "Input data:\n{0} / {1} bytes")

    def test_title_input_data_bytes_format(self):
        result = TR.ethereum__title_input_data_bytes.format(27, 100)
        self.assertEqual(result, "Input data:\n27 / 100 bytes")

    def test_title_input_data_bytes_format_zero(self):
        result = TR.ethereum__title_input_data_bytes.format(0, 200)
        self.assertEqual(result, "Input data:\n0 / 200 bytes")

    def test_title_input_data_bytes_format_last_chunk(self):
        result = TR.ethereum__title_input_data_bytes.format(81, 81)
        self.assertEqual(result, "Input data:\n81 / 81 bytes")


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestGetDataConfirmerNoBlobPrefixTitle(unittest.TestCase):
    """Tests that get_data_confirmer calls confirm_blob_prefix without a title kwarg."""

    def test_confirm_blob_prefix_called_without_title(self):
        # Verify that after first chunk (which uses confirm_blob_intro),
        # subsequent calls use confirm_blob_prefix WITHOUT title kwarg.
        calls = []

        async def mock_confirm_blob_intro(**kwargs):
            # Return False = don't skip, proceed to prefix display
            return False

        async def mock_confirm_blob_prefix(**kwargs):
            calls.append(kwargs)
            # Return None = confirm all (skip rest)
            return None

        total_len = 100
        chunk = memoryview(bytes(50))

        # helpers.py does a lazy `from trezor.ui.layouts import confirm_blob_prefix`
        # inside get_data_confirmer, so patch must be active BEFORE calling it.
        with patch(layouts_module, "confirm_blob_intro", mock_confirm_blob_intro):
            with patch(layouts_module, "confirm_blob_prefix", mock_confirm_blob_prefix):
                confirm_fn = get_data_confirmer(total_len)
                await_result(confirm_fn(chunk))

        self.assertGreater(len(calls), 0)
        for call_kwargs in calls:
            self.assertNotIn("title", call_kwargs)

    def test_confirm_blob_prefix_receives_correct_kwargs(self):
        # Verify confirm_blob_prefix is called with expected keyword arguments
        calls = []

        async def mock_confirm_blob_intro(**kwargs):
            return False

        async def mock_confirm_blob_prefix(**kwargs):
            calls.append(kwargs)
            return None  # confirm all

        total_len = 100
        chunk = memoryview(bytes(50))

        with patch(layouts_module, "confirm_blob_intro", mock_confirm_blob_intro):
            with patch(layouts_module, "confirm_blob_prefix", mock_confirm_blob_prefix):
                confirm_fn = get_data_confirmer(total_len)
                await_result(confirm_fn(chunk))

        self.assertGreater(len(calls), 0)
        first_call = calls[0]
        self.assertIn("data", first_call)
        self.assertIn("total_len", first_call)
        self.assertIn("confirmed_len", first_call)
        self.assertIn("br_name", first_call)
        self.assertEqual(first_call["total_len"], total_len)

    def test_first_chunk_calls_confirm_blob_intro(self):
        # Verify that the first chunk triggers confirm_blob_intro, not confirm_blob_prefix
        intro_calls = []
        prefix_calls = []

        async def mock_confirm_blob_intro(**kwargs):
            intro_calls.append(kwargs)
            return True  # skip = use progress bar

        async def mock_confirm_blob_prefix(**kwargs):
            prefix_calls.append(kwargs)
            return None

        total_len = 100
        chunk = memoryview(bytes(50))

        with patch(layouts_module, "confirm_blob_intro", mock_confirm_blob_intro):
            with patch(layouts_module, "confirm_blob_prefix", mock_confirm_blob_prefix):
                confirm_fn = get_data_confirmer(total_len)
                # When intro returns True (skip), progress bar is used
                # So confirm_blob_prefix should NOT be called on first chunk
                try:
                    await_result(confirm_fn(chunk))
                except Exception:
                    pass  # progress bar call may fail in test env

        self.assertEqual(len(intro_calls), 1)
        self.assertEqual(len(prefix_calls), 0)


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestEthereumGetAddress(unittest.TestCase):
    def test_address_from_bytes_eip55(self):
        # https://github.com/ethereum/EIPs/blob/master/EIPS/eip-55.md
        eip55 = [
            "0x52908400098527886E0F7030069857D2E4169EE7",
            "0x8617E340B3D01FA5F11F306F4090FD50E238070D",
            "0xde709f2102306220921060314715629080e2fb77",
            "0x27b1fdb04752bbc536007a920d24acb045561c26",
            "0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed",
            "0xfB6916095ca1df60bB79Ce92cE3Ea74c37c5d359",
            "0xdbF03B407c01E7cD3CBea99509d93f8DDDC8C6FB",
            "0xD1220A0cf47c7B9Be7A2E6BA89F429762e7b9aDb",
        ]
        for s in eip55:
            b = unhexlify(s[2:])
            h = address_from_bytes(b)
            self.assertEqual(h, s)

    def test_address_from_bytes_rskip60(self):
        # https://github.com/rsksmart/RSKIPs/blob/master/IPs/RSKIP60.md
        rskip60_chain_30 = [
            "0x5aaEB6053f3e94c9b9a09f33669435E7ef1bEAeD",
            "0xFb6916095cA1Df60bb79ce92cE3EA74c37c5d359",
            "0xDBF03B407c01E7CD3cBea99509D93F8Dddc8C6FB",
            "0xD1220A0Cf47c7B9BE7a2e6ba89F429762E7B9adB",
        ]
        rskip60_chain_31 = [
            "0x5aAeb6053F3e94c9b9A09F33669435E7EF1BEaEd",
            "0xFb6916095CA1dF60bb79CE92ce3Ea74C37c5D359",
            "0xdbF03B407C01E7cd3cbEa99509D93f8dDDc8C6fB",
            "0xd1220a0CF47c7B9Be7A2E6Ba89f429762E7b9adB",
        ]

        n = make_eth_network(chain_id=30)
        for s in rskip60_chain_30:
            b = unhexlify(s[2:])
            h = address_from_bytes(b, n)
            self.assertEqual(h, s)

        n = make_eth_network(chain_id=31)
        for s in rskip60_chain_31:
            b = unhexlify(s[2:])
            h = address_from_bytes(b, n)
            self.assertEqual(h, s)


if __name__ == "__main__":
    unittest.main()
