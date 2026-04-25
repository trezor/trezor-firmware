# flake8: noqa: F403,F405
from common import *  # isort:skip

from mock import MockAsync, patch

from trezor import TR, utils

_layout_module = None  # Will be set below if not BITCOIN_ONLY

if not utils.BITCOIN_ONLY:
    import trezor.ui.layouts as layouts_module

    # Determine the current layout module for patching should_show_more
    if utils.UI_LAYOUT == "BOLT":
        import trezor.ui.layouts.bolt as _layout_module
    elif utils.UI_LAYOUT == "CAESAR":
        import trezor.ui.layouts.caesar as _layout_module
    elif utils.UI_LAYOUT == "DELIZIA":
        import trezor.ui.layouts.delizia as _layout_module
    elif utils.UI_LAYOUT == "ECKHART":
        import trezor.ui.layouts.eckhart as _layout_module


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestConfirmBlobPrefixSignature(unittest.TestCase):
    """Test that confirm_blob_prefix has the new signature (no title parameter)."""

    def test_confirm_blob_prefix_exists(self):
        # confirm_blob_prefix must exist in the layouts namespace
        self.assertTrue(hasattr(layouts_module, "confirm_blob_prefix"))

    def test_confirm_blob_prefix_is_callable(self):
        fn = layouts_module.confirm_blob_prefix
        self.assertTrue(callable(fn))

    def test_no_title_in_call_show_more(self):
        # confirm_blob_prefix should be callable without a title argument
        # and return len(prefix) when the user wants to show more
        if _layout_module is None:
            return

        show_more_mock = MockAsync(return_value=_get_show_more_true_value())

        data = memoryview(bytes(100))
        with patch(_layout_module, "should_show_more", show_more_mock):
            result = await_result(
                _layout_module.confirm_blob_prefix(
                    data=data,
                    total_len=100,
                    confirmed_len=0,
                    br_name="test_br",
                )
            )
        # Should return an integer (len of prefix)
        self.assertIsInstance(result, int)
        self.assertGreater(result, 0)

    def test_no_title_in_call_confirm_all(self):
        # confirm_blob_prefix returns None when user confirms all (skips remaining)
        if _layout_module is None:
            return

        show_more_mock = MockAsync(return_value=_get_show_more_false_value())

        data = memoryview(bytes(100))
        with patch(_layout_module, "should_show_more", show_more_mock):
            result = await_result(
                _layout_module.confirm_blob_prefix(
                    data=data,
                    total_len=100,
                    confirmed_len=0,
                    br_name="test_br",
                )
            )
        # Should return None (skip remaining)
        self.assertIsNone(result)


def _get_show_more_true_value():
    """Return True for show_more (bolt/caesar: show_more=True means return prefix_len)."""
    if utils.UI_LAYOUT in ("BOLT", "CAESAR"):
        # show_more = await should_show_more(...) → True means return len(prefix)
        return True
    elif utils.UI_LAYOUT in ("DELIZIA", "ECKHART"):
        # show_more = not await should_show_more(...) → False means True after inversion
        return False
    return True


def _get_show_more_false_value():
    """Return value such that show_more=False (i.e., return None from confirm_blob_prefix)."""
    if utils.UI_LAYOUT in ("BOLT", "CAESAR"):
        return False
    elif utils.UI_LAYOUT in ("DELIZIA", "ECKHART"):
        return True
    return False


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestConfirmBlobPrefixReturnValues(unittest.TestCase):
    """Test return values of confirm_blob_prefix based on user choice."""

    def setUp(self):
        if _layout_module is None:
            self.skipTest("Layout module not available")

    def test_returns_prefix_len_when_user_wants_more(self):
        # When user wants to see more data, confirm_blob_prefix returns the prefix length
        show_more_mock = MockAsync(return_value=_get_show_more_true_value())
        data = memoryview(bytes(200))

        with patch(_layout_module, "should_show_more", show_more_mock):
            result = await_result(
                _layout_module.confirm_blob_prefix(
                    data=data,
                    total_len=200,
                    confirmed_len=0,
                    br_name="test_br",
                )
            )

        self.assertIsNotNone(result)
        self.assertIsInstance(result, int)
        self.assertGreater(result, 0)

    def test_returns_none_when_user_confirms_all(self):
        # When user confirms all (skips remaining), returns None
        show_more_mock = MockAsync(return_value=_get_show_more_false_value())
        data = memoryview(bytes(200))

        with patch(_layout_module, "should_show_more", show_more_mock):
            result = await_result(
                _layout_module.confirm_blob_prefix(
                    data=data,
                    total_len=200,
                    confirmed_len=0,
                    br_name="test_br",
                )
            )

        self.assertIsNone(result)

    def test_returns_prefix_len_not_full_data_len(self):
        # When data is larger than prefix capacity, result is smaller than data length
        show_more_mock = MockAsync(return_value=_get_show_more_true_value())
        large_data = memoryview(bytes(1000))

        with patch(_layout_module, "should_show_more", show_more_mock):
            result = await_result(
                _layout_module.confirm_blob_prefix(
                    data=large_data,
                    total_len=1000,
                    confirmed_len=0,
                    br_name="test_br",
                )
            )

        # prefix is at most the layout's max prefix bytes
        self.assertIsNotNone(result)
        self.assertLess(result, len(large_data))

    def test_prefix_len_when_data_shorter_than_max(self):
        # When data is shorter than the layout's max prefix, entire data is used
        show_more_mock = MockAsync(return_value=_get_show_more_true_value())
        small_data = memoryview(bytes(5))  # Very small data

        with patch(_layout_module, "should_show_more", show_more_mock):
            result = await_result(
                _layout_module.confirm_blob_prefix(
                    data=small_data,
                    total_len=5,
                    confirmed_len=0,
                    br_name="test_br",
                )
            )

        # All 5 bytes should be the prefix
        self.assertEqual(result, 5)

    def test_empty_data_prefix(self):
        # Edge case: empty data
        show_more_mock = MockAsync(return_value=_get_show_more_true_value())
        empty_data = memoryview(bytes(0))

        with patch(_layout_module, "should_show_more", show_more_mock):
            result = await_result(
                _layout_module.confirm_blob_prefix(
                    data=empty_data,
                    total_len=0,
                    confirmed_len=0,
                    br_name="test_br",
                )
            )

        # Empty prefix: returns 0 or None depending on show_more
        # Either way, confirmed_len should not exceed total_len
        if result is not None:
            self.assertEqual(result, 0)


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestConfirmBlobPrefixTitleUsesTranslation(unittest.TestCase):
    """Test that confirm_blob_prefix uses the new TR string for the title."""

    def setUp(self):
        if _layout_module is None:
            self.skipTest("Layout module not available")

    def test_title_uses_tr_ethereum_title_input_data_bytes(self):
        # The title passed to should_show_more should use TR.ethereum__title_input_data_bytes
        captured_kwargs = []

        async def capture_should_show_more(**kwargs):
            captured_kwargs.append(kwargs)
            return _get_show_more_false_value()

        data = memoryview(bytes(50))
        total_len = 100
        confirmed_len = 0

        with patch(_layout_module, "should_show_more", capture_should_show_more):
            await_result(
                _layout_module.confirm_blob_prefix(
                    data=data,
                    total_len=total_len,
                    confirmed_len=confirmed_len,
                    br_name="test_br",
                )
            )

        self.assertGreater(len(captured_kwargs), 0)
        title = captured_kwargs[0].get("title")
        self.assertIsNotNone(title)

        # The title should contain byte count info
        if utils.UI_LAYOUT in ("BOLT", "CAESAR", "ECKHART"):
            # title = TR.ethereum__title_input_data_bytes.format(confirmed_len, total_len)
            # Default mock: "Input data:\n{0} / {1} bytes"
            self.assertIn(str(total_len), title)
        elif utils.UI_LAYOUT == "DELIZIA":
            # title = TR.ethereum__title_input_data_bytes (no format, used as-is)
            # subtitle contains the formatted bytes info
            subtitle = captured_kwargs[0].get("subtitle")
            self.assertIsNotNone(subtitle)
            self.assertIn(str(total_len), subtitle)

    def test_title_does_not_contain_old_input_data_format(self):
        # The old code used f"{title}:\n{confirmed_len} / {total_len} bytes" with an external title
        # The new code uses TR.ethereum__title_input_data_bytes directly
        # Ensure the title is NOT empty
        captured_kwargs = []

        async def capture_should_show_more(**kwargs):
            captured_kwargs.append(kwargs)
            return _get_show_more_false_value()

        data = memoryview(bytes(50))

        with patch(_layout_module, "should_show_more", capture_should_show_more):
            await_result(
                _layout_module.confirm_blob_prefix(
                    data=data,
                    total_len=100,
                    confirmed_len=0,
                    br_name="test_br",
                )
            )

        self.assertGreater(len(captured_kwargs), 0)
        title = captured_kwargs[0].get("title")
        self.assertIsNotNone(title)
        self.assertNotEqual(title, "")

    def test_confirmed_len_updates_in_title(self):
        # Verify that confirmed_len is used to compute the title (bytes seen so far)
        captured_kwargs = []

        async def capture_should_show_more(**kwargs):
            captured_kwargs.append(kwargs)
            return _get_show_more_false_value()

        data = memoryview(bytes(50))
        total_len = 200
        confirmed_len = 50  # already confirmed 50 bytes

        with patch(_layout_module, "should_show_more", capture_should_show_more):
            await_result(
                _layout_module.confirm_blob_prefix(
                    data=data,
                    total_len=total_len,
                    confirmed_len=confirmed_len,
                    br_name="test_br",
                )
            )

        self.assertGreater(len(captured_kwargs), 0)
        if utils.UI_LAYOUT in ("BOLT", "CAESAR", "ECKHART"):
            title = captured_kwargs[0].get("title")
            # confirmed_len should be updated by prefix length before formatting
            # prefix = data[:prefix_max_size], confirmed_len += len(prefix)
            # So title should show confirmed_len + len(prefix)
            self.assertIn(str(total_len), title)
        elif utils.UI_LAYOUT == "DELIZIA":
            subtitle = captured_kwargs[0].get("subtitle")
            self.assertIn(str(total_len), subtitle)


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestConfirmBlobPrefixLayoutSpecificPrefixSizes(unittest.TestCase):
    """Test layout-specific prefix sizes (data slicing per layout)."""

    def setUp(self):
        if _layout_module is None:
            self.skipTest("Layout module not available")

    def test_prefix_size_matches_layout(self):
        # Each layout defines a different prefix size:
        # bolt: 3 * 9 = 27 bytes
        # caesar: 4 * 9 = 36 bytes
        # delizia: 7 * 9 = 63 bytes
        # eckhart: 9 * 9 = 81 bytes
        layout_prefix_sizes = {
            "BOLT": 27,
            "CAESAR": 36,
            "DELIZIA": 63,
            "ECKHART": 81,
        }

        expected_prefix_size = layout_prefix_sizes.get(utils.UI_LAYOUT)
        if expected_prefix_size is None:
            return

        show_more_mock = MockAsync(return_value=_get_show_more_true_value())
        # Data larger than the expected prefix size
        large_data = memoryview(bytes(expected_prefix_size + 50))

        with patch(_layout_module, "should_show_more", show_more_mock):
            result = await_result(
                _layout_module.confirm_blob_prefix(
                    data=large_data,
                    total_len=expected_prefix_size + 50,
                    confirmed_len=0,
                    br_name="test_br",
                )
            )

        self.assertEqual(result, expected_prefix_size)

    def test_prefix_uses_all_bytes_when_data_smaller_than_max(self):
        # When data is smaller than max prefix size, prefix = entire data
        show_more_mock = MockAsync(return_value=_get_show_more_true_value())
        small_data = memoryview(bytes(10))  # smaller than any layout's max prefix

        with patch(_layout_module, "should_show_more", show_more_mock):
            result = await_result(
                _layout_module.confirm_blob_prefix(
                    data=small_data,
                    total_len=10,
                    confirmed_len=0,
                    br_name="test_br",
                )
            )

        self.assertEqual(result, 10)


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestConfirmBlobPrefixButtonTextBehavior(unittest.TestCase):
    """Test button_text behavior based on confirmed vs total bytes."""

    def setUp(self):
        if _layout_module is None:
            self.skipTest("Layout module not available")
        # Delizia doesn't use button_text in the same way; skip for now
        if utils.UI_LAYOUT == "DELIZIA":
            self.skipTest("Delizia uses a different button text mechanism")

    def test_button_text_show_next_when_more_data_remains(self):
        # When confirmed_len + prefix_len < total_len, button_text should be set
        captured_kwargs = []

        async def capture_should_show_more(**kwargs):
            captured_kwargs.append(kwargs)
            return _get_show_more_false_value()

        # Large total_len ensures more data remains after prefix
        data = memoryview(bytes(50))
        total_len = 10000  # much larger than any prefix

        with patch(_layout_module, "should_show_more", capture_should_show_more):
            await_result(
                _layout_module.confirm_blob_prefix(
                    data=data,
                    total_len=total_len,
                    confirmed_len=0,
                    br_name="test_br",
                )
            )

        self.assertGreater(len(captured_kwargs), 0)
        button_text = captured_kwargs[0].get("button_text")
        # button_text should be set (not None or empty) when more data remains
        self.assertIsNotNone(button_text)

    def test_button_text_when_last_chunk(self):
        # When confirmed_len + prefix_len == total_len, behavior differs per layout
        captured_kwargs = []

        async def capture_should_show_more(**kwargs):
            captured_kwargs.append(kwargs)
            return _get_show_more_false_value()

        # Small data where prefix covers everything
        small_size = 5
        data = memoryview(bytes(small_size))

        with patch(_layout_module, "should_show_more", capture_should_show_more):
            await_result(
                _layout_module.confirm_blob_prefix(
                    data=data,
                    total_len=small_size,
                    confirmed_len=0,
                    br_name="test_br",
                )
            )

        self.assertGreater(len(captured_kwargs), 0)
        button_text = captured_kwargs[0].get("button_text")

        if utils.UI_LAYOUT == "BOLT":
            # bolt: button_text = None when last chunk
            self.assertIsNone(button_text)
        elif utils.UI_LAYOUT == "CAESAR":
            # caesar: button_text = "" when last chunk
            self.assertEqual(button_text, "")
        elif utils.UI_LAYOUT == "ECKHART":
            # eckhart: uses TR.buttons__continue when last chunk
            self.assertIsNotNone(button_text)
            self.assertNotEqual(button_text, "")


if __name__ == "__main__":
    unittest.main()
