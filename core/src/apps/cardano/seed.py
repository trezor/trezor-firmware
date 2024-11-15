from typing import TYPE_CHECKING

import storage.device as device
from storage.cache_common import (
    APP_CARDANO_ICARUS_SECRET,
    APP_CARDANO_ICARUS_TREZOR_SECRET,
    APP_COMMON_DERIVE_CARDANO,
)
from trezor import wire
from trezor.crypto import cardano
from trezor.wire import context

from apps.common import mnemonic
from apps.common.seed import get_seed

from .helpers.paths import BYRON_ROOT, MINTING_ROOT, MULTISIG_ROOT, SHELLEY_ROOT

if TYPE_CHECKING:
    from typing import Awaitable, Callable, TypeVar

    from trezor import messages
    from trezor.crypto import bip32
    from trezor.enums import CardanoDerivationType

    from apps.common.keychain import Handler, MsgOut
    from apps.common.paths import Bip32Path

    CardanoMessages = (
        messages.CardanoGetAddress
        | messages.CardanoGetPublicKey
        | messages.CardanoGetNativeScriptHash
        | messages.CardanoSignTxInit
    )
    MsgIn = TypeVar("MsgIn", bound=CardanoMessages)

    HandlerWithKeychain = Callable[[MsgIn, "Keychain"], Awaitable[MsgOut]]


class Keychain:
    """
    Cardano keychain hard-coded to 44 (Byron), 1852 (Shelley), 1854 (multi-sig) and 1855 (token minting)
    seed namespaces.
    """

    def __init__(self, root: bip32.HDNode) -> None:
        self.byron_root = self._derive_path(root, BYRON_ROOT)
        self.shelley_root = self._derive_path(root, SHELLEY_ROOT)
        self.multisig_root = self._derive_path(root, MULTISIG_ROOT)
        self.minting_root = self._derive_path(root, MINTING_ROOT)
        root.__del__()

    @staticmethod
    def _derive_path(root: bip32.HDNode, path: Bip32Path) -> bip32.HDNode:
        """Clone and derive path from the root."""
        node = root.clone()
        node.derive_path(path)
        return node

    def verify_path(self, path: Bip32Path) -> None:
        if not self.is_in_keychain(path):
            raise wire.DataError("Forbidden key path")

    def _get_path_root(self, path: Bip32Path) -> bip32.HDNode:
        if is_byron_path(path):
            return self.byron_root
        elif is_shelley_path(path):
            return self.shelley_root
        elif is_multisig_path(path):
            return self.multisig_root
        elif is_minting_path(path):
            return self.minting_root
        else:
            raise wire.DataError("Forbidden key path")

    def is_in_keychain(self, path: Bip32Path) -> bool:
        return (
            is_byron_path(path)
            or is_shelley_path(path)
            or is_multisig_path(path)
            or is_minting_path(path)
        )

    def derive(self, node_path: Bip32Path) -> bip32.HDNode:
        self.verify_path(node_path)
        path_root = self._get_path_root(node_path)

        # this is true now, so for simplicity we don't branch on path type
        assert (
            len(BYRON_ROOT) == len(SHELLEY_ROOT)
            and len(MULTISIG_ROOT) == len(SHELLEY_ROOT)
            and len(MINTING_ROOT) == len(SHELLEY_ROOT)
        )
        suffix = node_path[len(SHELLEY_ROOT) :]

        # derive child node from the root
        return self._derive_path(path_root, suffix)

    # XXX the root node remains in session cache so we should not delete it
    # def __del__(self) -> None:
    #     self.root.__del__()


def is_byron_path(path: Bip32Path) -> bool:
    return path[: len(BYRON_ROOT)] == BYRON_ROOT


def is_shelley_path(path: Bip32Path) -> bool:
    return path[: len(SHELLEY_ROOT)] == SHELLEY_ROOT


def is_multisig_path(path: Bip32Path) -> bool:
    return path[: len(MULTISIG_ROOT)] == MULTISIG_ROOT


def is_minting_path(path: Bip32Path) -> bool:
    return path[: len(MINTING_ROOT)] == MINTING_ROOT


def derive_and_store_secrets(passphrase: str) -> None:
    assert device.is_initialized()
    assert context.cache_get_bool(APP_COMMON_DERIVE_CARDANO)

    if not mnemonic.is_bip39():
        # nothing to do for SLIP-39, where we can derive the root from the main seed
        return

    icarus_secret = mnemonic.derive_cardano_icarus(passphrase, trezor_derivation=False)

    words = mnemonic.get_secret()
    assert words is not None, "Mnemonic is not set"
    # count ASCII spaces, add 1 to get number of words
    words_count = sum(c == 0x20 for c in words) + 1

    if words_count == 24:
        icarus_trezor_secret = mnemonic.derive_cardano_icarus(
            passphrase, trezor_derivation=True
        )
    else:
        icarus_trezor_secret = icarus_secret

    context.cache_set(APP_CARDANO_ICARUS_SECRET, icarus_secret)
    context.cache_set(APP_CARDANO_ICARUS_TREZOR_SECRET, icarus_trezor_secret)


async def _get_keychain_bip39(derivation_type: CardanoDerivationType) -> Keychain:
    from trezor.enums import CardanoDerivationType

    from apps.common.seed import derive_and_store_roots

    if not device.is_initialized():
        raise wire.NotInitialized("Device is not initialized")

    if derivation_type == CardanoDerivationType.LEDGER:
        seed = await get_seed()
        return Keychain(cardano.from_seed_ledger(seed))

    if not context.cache_get_bool(APP_COMMON_DERIVE_CARDANO):
        raise wire.ProcessError("Cardano derivation is not enabled for this session")

    if derivation_type == CardanoDerivationType.ICARUS:
        cache_entry = APP_CARDANO_ICARUS_SECRET
    else:
        cache_entry = APP_CARDANO_ICARUS_TREZOR_SECRET

    # _get_secret
    secret = context.cache_get(cache_entry)
    if secret is None:
        await derive_and_store_roots()
        secret = context.cache_get(cache_entry)
        assert secret is not None

    root = cardano.from_secret(secret)
    return Keychain(root)


async def _get_keychain(derivation_type: CardanoDerivationType) -> Keychain:
    if mnemonic.is_bip39():
        return await _get_keychain_bip39(derivation_type)
    else:
        # derive the root node via SLIP-0023 https://github.com/satoshilabs/slips/blob/master/slip-0023.md
        seed = await get_seed()
        return Keychain(cardano.from_seed_slip23(seed))


def with_keychain(func: HandlerWithKeychain[MsgIn, MsgOut]) -> Handler[MsgIn, MsgOut]:
    async def wrapper(msg: MsgIn) -> MsgOut:
        keychain = await _get_keychain(msg.derivation_type)
        return await func(msg, keychain)

    return wrapper
