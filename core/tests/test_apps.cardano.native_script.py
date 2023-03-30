from common import *
from trezor import wire
from trezor.crypto import cardano
from trezor.enums import CardanoNativeScriptType
from trezor.messages import CardanoNativeScript

if not utils.BITCOIN_ONLY:
    from apps.cardano.seed import Keychain
    from apps.cardano.native_script import get_native_script_hash, validate_native_script

VALID_NATIVE_SCRIPTS = [
    # PUB_KEY
    [
        CardanoNativeScript(
            type=CardanoNativeScriptType.PUB_KEY,
            key_hash=unhexlify(
                "c4b9265645fde9536c0795adbcc5291767a0c61fd62448341d7e0386"
            ),
        ),
        b"29fb5fd4aa8cadd6705acc8263cee0fc62edca5ac38db593fec2f9fd",
    ],
    # PUB_KEY with path
    [
        CardanoNativeScript(
            type=CardanoNativeScriptType.PUB_KEY,
            key_path=[1854 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0],
        ),
        b"29fb5fd4aa8cadd6705acc8263cee0fc62edca5ac38db593fec2f9fd",
    ],
    # ALL
    [
        CardanoNativeScript(
            type=CardanoNativeScriptType.ALL,
            scripts=[
                CardanoNativeScript(
                    type=CardanoNativeScriptType.PUB_KEY,
                    key_path=[1854 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0],
                ),
                CardanoNativeScript(
                    type=CardanoNativeScriptType.PUB_KEY,
                    key_hash=unhexlify(
                        "0241f2d196f52a92fbd2183d03b370c30b6960cfdeae364ffabac889"
                    ),
                ),
            ],
        ),
        b"af5c2ce476a6ede1c879f7b1909d6a0b96cb2081391712d4a355cef6",
    ],
    # ALL with 1855 path
    [
        CardanoNativeScript(
            type=CardanoNativeScriptType.ALL,
            scripts=[
                CardanoNativeScript(
                    type=CardanoNativeScriptType.PUB_KEY,
                    key_path=[1855 | HARDENED, 1815 | HARDENED, 0 | HARDENED],
                ),
                CardanoNativeScript(
                    type=CardanoNativeScriptType.PUB_KEY,
                    key_hash=unhexlify(
                        "0241f2d196f52a92fbd2183d03b370c30b6960cfdeae364ffabac889"
                    ),
                ),
            ],
        ),
        b"fbf6672eb655c29b0f148fa1429be57c2174b067a7b3e3942e967fe8",
    ],
    # ALL scripts are empty
    [
        CardanoNativeScript(type=CardanoNativeScriptType.ALL, scripts=[]),
        b"d441227553a0f1a965fee7d60a0f724b368dd1bddbc208730fccebcf"
    ],
    # ANY
    [
        CardanoNativeScript(
            type=CardanoNativeScriptType.ANY,
            scripts=[
                CardanoNativeScript(
                    type=CardanoNativeScriptType.PUB_KEY,
                    key_path=[1854 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0],
                ),
                CardanoNativeScript(
                    type=CardanoNativeScriptType.PUB_KEY,
                    key_hash=unhexlify(
                        "0241f2d196f52a92fbd2183d03b370c30b6960cfdeae364ffabac889"
                    ),
                ),
            ],
        ),
        b"d6428ec36719146b7b5fb3a2d5322ce702d32762b8c7eeeb797a20db",
    ],
    # ANY scripts are empty
    [
        CardanoNativeScript(type=CardanoNativeScriptType.ANY, scripts=[]),
        b"52dc3d43b6d2465e96109ce75ab61abe5e9c1d8a3c9ce6ff8a3af528"
    ],
    # N OF K
    [
        CardanoNativeScript(
            type=CardanoNativeScriptType.N_OF_K,
            required_signatures_count=2,
            scripts=[
                CardanoNativeScript(
                    type=CardanoNativeScriptType.PUB_KEY,
                    key_path=[1854 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0],
                ),
                CardanoNativeScript(
                    type=CardanoNativeScriptType.PUB_KEY,
                    key_hash=unhexlify(
                        "0241f2d196f52a92fbd2183d03b370c30b6960cfdeae364ffabac889"
                    ),
                ),
                CardanoNativeScript(
                    type=CardanoNativeScriptType.PUB_KEY,
                    key_hash=unhexlify(
                        "cecb1d427c4ae436d28cc0f8ae9bb37501a5b77bcc64cd1693e9ae20"
                    ),
                ),
            ],
        ),
        b"2b2b17fd18e18acae4601d4818a1dee00a917ff72e772fa8482e36c9",
    ],
    # N_OF_K scripts are empty
    [
        CardanoNativeScript(type=CardanoNativeScriptType.N_OF_K, required_signatures_count=0, scripts=[]),
        b"3530cc9ae7f2895111a99b7a02184dd7c0cea7424f1632d73951b1d7"
    ],
    # INVALID BEFORE
    [
        CardanoNativeScript(
            type=CardanoNativeScriptType.ALL,
            scripts=[
                CardanoNativeScript(
                    type=CardanoNativeScriptType.PUB_KEY,
                    key_hash=unhexlify(
                        "c4b9265645fde9536c0795adbcc5291767a0c61fd62448341d7e0386"
                    ),
                ),
                CardanoNativeScript(
                    type=CardanoNativeScriptType.INVALID_BEFORE, invalid_before=100
                ),
            ],
        ),
        b"c6262ef9bb2b1291c058d93b46dabf458e2d135f803f60713f84b0b7",
    ],
    # INVALID HEREAFTER
    [
        CardanoNativeScript(
            type=CardanoNativeScriptType.ALL,
            scripts=[
                CardanoNativeScript(
                    type=CardanoNativeScriptType.PUB_KEY,
                    key_hash=unhexlify(
                        "c4b9265645fde9536c0795adbcc5291767a0c61fd62448341d7e0386"
                    ),
                ),
                CardanoNativeScript(
                    type=CardanoNativeScriptType.INVALID_HEREAFTER,
                    invalid_hereafter=200,
                ),
            ],
        ),
        b"b12ac304f89f4cd4d23f59a2b90d2b2697f7540b8f470d6aa05851b5",
    ],
    # NESTED SCRIPT
    [
        CardanoNativeScript(
            type=CardanoNativeScriptType.ALL,
            scripts=[
                CardanoNativeScript(
                    type=CardanoNativeScriptType.PUB_KEY,
                    key_hash=unhexlify(
                        "c4b9265645fde9536c0795adbcc5291767a0c61fd62448341d7e0386"
                    ),
                ),
                CardanoNativeScript(
                    type=CardanoNativeScriptType.PUB_KEY,
                    key_path=[1854 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0],
                ),
                CardanoNativeScript(
                    type=CardanoNativeScriptType.ANY,
                    scripts=[
                        CardanoNativeScript(
                            type=CardanoNativeScriptType.PUB_KEY,
                            key_path=[1854 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0],
                        ),
                        CardanoNativeScript(
                            type=CardanoNativeScriptType.PUB_KEY,
                            key_hash=unhexlify(
                                "0241f2d196f52a92fbd2183d03b370c30b6960cfdeae364ffabac889"
                            ),
                        ),
                    ],
                ),
                CardanoNativeScript(
                    type=CardanoNativeScriptType.N_OF_K,
                    required_signatures_count=2,
                    scripts=[
                        CardanoNativeScript(
                            type=CardanoNativeScriptType.PUB_KEY,
                            key_path=[1854 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0],
                        ),
                        CardanoNativeScript(
                            type=CardanoNativeScriptType.PUB_KEY,
                            key_hash=unhexlify(
                                "0241f2d196f52a92fbd2183d03b370c30b6960cfdeae364ffabac889"
                            ),
                        ),
                        CardanoNativeScript(
                            type=CardanoNativeScriptType.PUB_KEY,
                            key_hash=unhexlify(
                                "cecb1d427c4ae436d28cc0f8ae9bb37501a5b77bcc64cd1693e9ae20"
                            ),
                        ),
                    ],
                ),
                CardanoNativeScript(
                    type=CardanoNativeScriptType.INVALID_BEFORE, invalid_before=100
                ),
                CardanoNativeScript(
                    type=CardanoNativeScriptType.INVALID_HEREAFTER,
                    invalid_hereafter=200,
                ),
            ],
        ),
        b"4a6b4288459bf34668c0b281f922691460caf0c7c09caee3a726c27a",
    ],
]

INVALID_SCRIPTS = [
    # PUB_KEY key_hash has invalid length
    CardanoNativeScript(
        type=CardanoNativeScriptType.PUB_KEY,
        key_hash=unhexlify("3a55d9f68255dfbefa1efd711f82d005fae1be2e145d616c90cf0f"),
    ),
    # PUB_KEY key_path is not multisig or mint
    CardanoNativeScript(
        type=CardanoNativeScriptType.PUB_KEY,
        key_path=[1852 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0, 0],
    ),
    # PUB_KEY mint key_path is too long
    CardanoNativeScript(
        type=CardanoNativeScriptType.PUB_KEY,
        key_path=[1855 | HARDENED, 1815 | HARDENED, 0 | HARDENED, 0],
    ),
    # N_OF_K required_signatures_count is not set
    CardanoNativeScript(
        type=CardanoNativeScriptType.N_OF_K,
        scripts=[
            CardanoNativeScript(
                type=CardanoNativeScriptType.PUB_KEY,
                key_hash=unhexlify(
                    "3a55d9f68255dfbefa1efd711f82d005fae1be2e145d616c90cf0fa9"
                ),
            ),
        ],
    ),
    # N_OF_K N is larger than K
    CardanoNativeScript(
        type=CardanoNativeScriptType.N_OF_K,
        required_signatures_count=2,
        scripts=[
            CardanoNativeScript(
                type=CardanoNativeScriptType.PUB_KEY,
                key_hash=unhexlify(
                    "3a55d9f68255dfbefa1efd711f82d005fae1be2e145d616c90cf0fa9"
                ),
            ),
        ],
    ),
    # INVALID_BEFORE invalid_before is not set
    CardanoNativeScript(type=CardanoNativeScriptType.INVALID_BEFORE),
    # INVALID_HEREAFTER invalid_hereafter is not set
    CardanoNativeScript(type=CardanoNativeScriptType.INVALID_HEREAFTER),
]


@unittest.skipUnless(not utils.BITCOIN_ONLY, "altcoin")
class TestCardanoNativeScript(unittest.TestCase):
    def test_get_native_script_hash(self):
        mnemonic = "all all all all all all all all all all all all"
        passphrase = ""
        secret = cardano.derive_icarus(mnemonic, passphrase, False)
        node = cardano.from_secret(secret)
        keychain = Keychain(node)

        for script, expected_hash in VALID_NATIVE_SCRIPTS:
            actual_hash = get_native_script_hash(keychain, script)
            self.assertEqual(hexlify(actual_hash), expected_hash)

    def test_validate_native_script(self):
        for script, _ in VALID_NATIVE_SCRIPTS:
            validate_native_script(script)

    def test_validate_native_script_invalid(self):
        for script in INVALID_SCRIPTS:
            with self.assertRaises(wire.ProcessError):
                validate_native_script(script)


if __name__ == "__main__":
    unittest.main()
