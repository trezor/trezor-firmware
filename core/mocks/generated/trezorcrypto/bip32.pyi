from typing import *


# extmod/modtrezorcrypto/modtrezorcrypto-bip32.h
class HDNode:
    """
    BIP0032 HD node structure.
    """

    def __init__(
        self,
        depth: int,
        fingerprint: int,
        child_num: int,
        chain_code: bytes,
        private_key: bytes = None,
        public_key: bytes = None,
        curve_name: str = None,
    ) -> None:
        """
        """

    def derive(self, index: int, public: bool = False) -> None:
        """
        Derive a BIP0032 child node in place.
        """

    def derive_cardano(self, index: int) -> None:
        """
        Derive a BIP0032 child node in place using Cardano algorithm.
        """

    def derive_path(self, path: Sequence[int]) -> None:
        """
        Go through a list of indexes and iteratively derive a child node in
        place.
        """

    def serialize_public(self, version: int) -> str:
        """
        Serialize the public info from HD node to base58 string.
        """

    def clone(self) -> HDNode:
        """
        Returns a copy of the HD node.
        """

    def depth(self) -> int:
        """
        Returns a depth of the HD node.
        """

    def fingerprint(self) -> int:
        """
        Returns a fingerprint of the HD node (hash of the parent public key).
        """

    def child_num(self) -> int:
        """
        Returns a child index of the HD node.
        """

    def chain_code(self) -> bytes:
        """
        Returns a chain code of the HD node.
        """

    def private_key(self) -> bytes:
        """
        Returns a private key of the HD node.
        """

    def private_key_ext(self) -> bytes:
        """
        Returns a private key extension of the HD node.
        """

    def public_key(self) -> bytes:
        """
        Returns a public key of the HD node.
        """

    def address(self, version: int) -> str:
        """
        Compute a base58-encoded address string from the HD node.
        """

    def nem_address(self, network: int) -> str:
        """
        Compute a NEM address string from the HD node.
        """

    def nem_encrypt(
        self, transfer_public_key: bytes, iv: bytes, salt: bytes, payload: bytes
    ) -> bytes:
        """
        Encrypts payload using the transfer's public key
        """

    def ethereum_pubkeyhash(self) -> bytes:
        """
        Compute an Ethereum pubkeyhash (aka address) from the HD node.
        """

    def __del__(self) -> None:
        """
        Cleans up sensitive memory.
        """


# extmod/modtrezorcrypto/modtrezorcrypto-bip32.h
def from_seed(seed: bytes, curve_name: str) -> HDNode:
    """
    Construct a BIP0032 HD node from a BIP0039 seed value.
    """


# extmod/modtrezorcrypto/modtrezorcrypto-bip32.h
def from_mnemonic_cardano(mnemonic: str, passphrase: str) -> bytes:
    """
    Construct a HD node from a BIP-0039 mnemonic using the Icarus derivation
    scheme, aka v2 derivation scheme.
    """
