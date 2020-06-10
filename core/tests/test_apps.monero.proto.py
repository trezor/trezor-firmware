from common import *

if not utils.BITCOIN_ONLY:
    from trezor.crypto import chacha20poly1305
    from apps.monero.signing import offloading_keys
    from apps.monero.signing import step_09_sign_input
    from apps.monero.signing.state import State
    import ubinascii


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestMoneroProto(unittest.TestCase):
    def test_sign_keys(self):
        mst = ubinascii.unhexlify(b"ca3bbe08a178a4508c3992a47ba775799e7626a365ed136e803fe5f2df2ce01c")
        self.assertEqual(offloading_keys.key_signature(mst, 0, True)[:12], ubinascii.unhexlify(b'bb665d97ac7c77995578e352'))
        self.assertEqual(offloading_keys.key_signature(mst, 0, False), ubinascii.unhexlify(b'87bb70af81bb7325f73e8b962167579454d126ff8ee51472922d7c103fc60f5f'))
        self.assertEqual(offloading_keys.key_signature(mst, 3, True)[:12], ubinascii.unhexlify(b'b2ef8e4e4eec72ce3096622a'))
        self.assertEqual(offloading_keys.key_signature(mst, 3, False), ubinascii.unhexlify(b'e4331602a83a68c892a83693a1b961564048d9349111b85b8b4b52a1adcf36da'))

    def test_sig_seal(self):
        mst = ubinascii.unhexlify(b"ca3bbe08a178a4508c3992a47ba775799e7626a365ed136e803fe5f2df2ce01c")
        st = State(None)
        st.last_step = st.STEP_SIGN
        st.opening_key = mst
        st.current_input_index = 3

        mg_buff = [
            '0b',
            '02fe9ee789007254215b41351109f186620624a3c1ad2ba89628194528672adf04f900ebf9ad3b0cc1ac9ae1f03167f74d6e04175df5001c91d09d29dbefd6bc0b',
            '021d46f6db8a349caca48a4dfee155b9dee927d0f25cdf5bcd724358c611b47906de6cedad47fd26070927f3954bcaf7a0e126699bf961ca4e8124abefe8aaeb05',
            '02ae933994effe2b348b09bfab783bf9adb58b09659d8f5bd058cca252d763b600541807dcb0ea9fe253e59f23ce36cc811d627acae5e2abdc00b7ed155f3e6b0f',
            '0203dd7138c7378444fe3c1b1572a351f88505aeab2d9f8ed4a8f67d66e76983072d8ae6e496b3953a8603543c2dc64749ee15fe3575e4505b502bfe696f06690e',
            '0287b572b6c096bc11a8c10fe1fc4ba2085633f8e1bdd2e39df8f46c9bf733ca068261d8006f22ee2bfaf4366e26d42b00befdddd9058a5c87a0f39c757f121909',
            '021e2ea38aa07601e07a3d7623a97e68d3251525304d2a748548c7b46d07c20b0c78506b19cae49d569d0a8c4979c74f7d8d19f7e595d307ddf00faf3d8f621c0d',
            '0214f758c8fb4a521a1e3d25b9fb535974f6aab1c1dda5988e986dda7e17140909a7b7bdb3d5e17a2ebd5deb3530d10c6f5d6966f525c1cbca408059949ff65304',
            '02f707c4a37066a692986ddfdd2ca71f68c6f45a956d45eaf6e8e7a2e5272ac3033eb26ca2b55bf86e90ab8ddcdbad88a82ded88deb552614190440169afcee004',
            '02edb8a5b8cc02a2e03b95ea068084ae2496f21d4dfd0842c63836137e37047b06d5a0160994396c98630d8b47878e9c18fea4fb824588c143e05c4b18bfea2301',
            '02aa59c2ef76ac97c261279a1c6ed3724d66a437fe8df0b85e8858703947a2b10f04e49912a0626c09849c3b4a3ea46166cd909b9fd561257730c91cbccf4abe07',
            '02c64a98c59c4a3d7c583de65404c5a54b350a25011dfca70cd84e3f6e570428026236028fce31bfd8d9fc5401867ab5349eb0859c65df05b380899a7bdfee9003',
            '03da465e27f7feec31353cb668f0e8965391f983b06c0684b35b00af38533603',
        ]

        mg_buff = [ubinascii.unhexlify(x) for x in mg_buff]
        mg_buff_b = list(mg_buff)
        mg_res = step_09_sign_input._protect_signature(st, mg_buff)

        iv = offloading_keys.key_signature(mst, st.current_input_index, True)[:12]
        key = offloading_keys.key_signature(mst, st.current_input_index, False)
        cipher = chacha20poly1305(key, iv)
        ciphertext = cipher.encrypt(b"".join(mg_buff_b))
        ciphertext += cipher.finish()
        self.assertEqual(b"".join(mg_res), ciphertext)

        cipher = chacha20poly1305(key, iv)
        ciphertext = b"".join(mg_res)
        exp_tag, ciphertext = ciphertext[-16:], ciphertext[:-16]
        plaintext = cipher.decrypt(ciphertext)
        tag = cipher.finish()
        self.assertEqual(tag, exp_tag)
        self.assertEqual(plaintext, b"".join(mg_buff_b))


if __name__ == "__main__":
    unittest.main()
