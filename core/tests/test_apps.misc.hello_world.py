from common import unittest  # isort:skip

from trezor.messages import HelloWorldRequest

from apps.misc.hello_world import _get_text_from_msg


class TestHelloWorld(unittest.TestCase):
    def test_get_text_from_msg(self):
        msg = HelloWorldRequest(name="Satoshi", amount=2, show_display=False)
        self.assertEqual(_get_text_from_msg(msg), "Hello Satoshi!\nHello Satoshi!\n")


if __name__ == "__main__":
    unittest.main()
