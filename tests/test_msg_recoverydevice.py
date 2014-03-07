import unittest
import common

from trezorlib import messages_pb2 as proto

class TestDeviceRecovery(common.TrezorTest):
    def test_pin_passphrase(self):
        mnemonic = self.mnemonic12.split(' ')
        ret = self.client.call_raw(proto.RecoveryDevice(word_count=12,
                                   passphrase_protection=True,
                                   pin_protection=True,
                                   label='label',
                                   language='english',
                                   enforce_wordlist=True))


        self.assertIsInstance(ret, proto.ButtonRequest)
        self.client.debug.press_yes()
        ret = self.client.call_raw(proto.ButtonAck())

        self.assertIsInstance(ret, proto.PinMatrixRequest)

        # Enter PIN for first time
        pin_encoded = self.client.debug.encode_pin(self.pin6)
        ret = self.client.call_raw(proto.PinMatrixAck(pin=pin_encoded))
        self.assertIsInstance(ret, proto.PinMatrixRequest)

        # Enter PIN for second time
        pin_encoded = self.client.debug.encode_pin(self.pin6)
        ret = self.client.call_raw(proto.PinMatrixAck(pin=pin_encoded))

        fakes = 0
        for _ in range(int(12 * 1.5)):
            self.assertIsInstance(ret, proto.WordRequest)
            (word, pos) = self.client.debug.read_recovery_word()

            if pos != 0:
                ret = self.client.call_raw(proto.WordAck(word=mnemonic[pos - 1]))
                mnemonic[pos - 1] = None
            else:
                ret = self.client.call_raw(proto.WordAck(word=word))
                fakes += 1

            print mnemonic

        # Workflow succesfully ended
        self.assertIsInstance(ret, proto.Success)

        # 6 expected fake words and all words of mnemonic are used
        self.assertEqual(fakes, 6)
        self.assertEqual(mnemonic, [None] * 12)

        # Mnemonic is the same
        self.client.init_device()
        self.assertEqual(self.client.debug.read_mnemonic(), self.mnemonic12)

        self.assertTrue(self.client.features.pin_protection)
        self.assertTrue(self.client.features.passphrase_protection)
        
        # Do passphrase-protected action, PassphraseRequest should be raised
        resp = self.client.call_raw(proto.Ping(passphrase_protection=True))
        self.assertIsInstance(resp, proto.PassphraseRequest)

        # Do PIN-protected action, PinRequest should be raised
        resp = self.client.call_raw(proto.Ping(pin_protection=True))
        self.assertIsInstance(resp, proto.PinMatrixRequest)

    def test_nopin_nopassphrase(self):
        mnemonic = self.mnemonic12.split(' ')
        ret = self.client.call_raw(proto.RecoveryDevice(word_count=12,
                                   passphrase_protection=False,
                                   pin_protection=False,
                                   label='label',
                                   language='english',
                                   enforce_wordlist=True))


        self.assertIsInstance(ret, proto.ButtonRequest)
        self.client.debug.press_yes()
        ret = self.client.call_raw(proto.ButtonAck())

        fakes = 0
        for _ in range(int(12 * 1.5)):
            self.assertIsInstance(ret, proto.WordRequest)
            (word, pos) = self.client.debug.read_recovery_word()

            if pos != 0:
                ret = self.client.call_raw(proto.WordAck(word=mnemonic[pos - 1]))
                mnemonic[pos - 1] = None
            else:
                ret = self.client.call_raw(proto.WordAck(word=word))
                fakes += 1

            print mnemonic

        # Workflow succesfully ended
        self.assertIsInstance(ret, proto.Success)

        # 6 expected fake words and all words of mnemonic are used
        self.assertEqual(fakes, 6)
        self.assertEqual(mnemonic, [None] * 12)

        # Mnemonic is the same
        self.client.init_device()
        self.assertEqual(self.client.debug.read_mnemonic(), self.mnemonic12)

        self.assertFalse(self.client.features.pin_protection)
        self.assertFalse(self.client.features.passphrase_protection)

        # Do passphrase-protected action, PassphraseRequest should NOT be raised
        resp = self.client.call_raw(proto.Ping(passphrase_protection=True))
        self.assertIsInstance(resp, proto.Success)

        # Do PIN-protected action, PinRequest should NOT be raised
        resp = self.client.call_raw(proto.Ping(pin_protection=True))
        self.assertIsInstance(resp, proto.Success)
    
    def test_word_fail(self):
        ret = self.client.call_raw(proto.RecoveryDevice(word_count=12,
                                   passphrase_protection=False,
                                   pin_protection=False,
                                   label='label',
                                   language='english',
                                   enforce_wordlist=True))

        self.assertIsInstance(ret, proto.ButtonRequest)
        self.client.debug.press_yes()
        ret = self.client.call_raw(proto.ButtonAck())

        for _ in range(int(12 * 1.5)):
            self.assertIsInstance(ret, proto.WordRequest)
            (word, pos) = self.client.debug.read_recovery_word()

            if pos != 0:
                ret = self.client.call_raw(proto.WordAck('kwyjibo'))
                self.assertIsInstance(ret, proto.Failure)
            else:
                ret = self.client.call_raw(proto.WordAck(word=word))

    def test_pin_fail(self):
        ret = self.client.call_raw(proto.RecoveryDevice(word_count=12,
                                   passphrase_protection=True,
                                   pin_protection=True,
                                   label='label',
                                   language='english',
                                   enforce_wordlist=True))


        self.assertIsInstance(ret, proto.ButtonRequest)
        self.client.debug.press_yes()
        ret = self.client.call_raw(proto.ButtonAck())

        self.assertIsInstance(ret, proto.PinMatrixRequest)

        # Enter PIN for first time
        pin_encoded = self.client.debug.encode_pin(self.pin4)
        ret = self.client.call_raw(proto.PinMatrixAck(pin=pin_encoded))
        self.assertIsInstance(ret, proto.PinMatrixRequest)

        # Enter PIN for second time, but different one
        pin_encoded = self.client.debug.encode_pin(self.pin6)
        ret = self.client.call_raw(proto.PinMatrixAck(pin=pin_encoded))

        # Failure should be raised
        self.assertIsInstance(ret, proto.Failure)

    def test_already_initialized(self):
        self.setup_mnemonic_nopin_nopassphrase()
        self.assertRaises(Exception, self.client.recovery_device, 12, False, False, 'label', 'english')

if __name__ == '__main__':
    unittest.main()
