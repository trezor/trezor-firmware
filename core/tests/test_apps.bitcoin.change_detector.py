# flake8: noqa: F403,F405
from common import *  # isort:skip

from trezor.enums import InputScriptType, MultisigPubkeysOrder, OutputScriptType
from trezor.enums.MultisigPubkeysOrder import LEXICOGRAPHIC, PRESERVED
from trezor.messages import (
    HDNodeType,
    MiniscriptDerivation,
    MiniscriptRedeemPolicyType,
    MultisigRedeemScriptType,
    TxInput,
    TxOutput,
)
from trezor.wire import DataError, ProcessError

from apps.bitcoin.sign_tx.change_detector import ChangeDetector

# all all all all all all all all all all all all/45/0
xpub1 = HDNodeType(
    depth=2,
    fingerprint=50263508,
    child_num=0,
    chain_code=bytes.fromhex(
        "8eb1f96a45dcb693dbad61f5184871d999127a37f1b0d4dae9964eaf3fb0e15b"
    ),
    public_key=bytes.fromhex(
        "03922315cd2d2d874e4c55add2e0ea41af9c2957f02c0abe0f55285d364a067b61"
    ),
)

# all all all all all all all all all all all all/45/1
xpub2 = HDNodeType(
    depth=2,
    fingerprint=50263508,
    child_num=1,
    chain_code=bytes.fromhex(
        "acad50a7e52e44841d42bec6886df516974f8d366bc471a8515dfc69a6692700"
    ),
    public_key=bytes.fromhex(
        "02e6f3bf3093b45705e3d838490377e0d99eed911ca01990d1e94acd445dee59e8"
    ),
)

# all all all all all all all all all all all all/45/2
xpub3 = HDNodeType(
    depth=2,
    fingerprint=50263508,
    child_num=2,
    chain_code=bytes.fromhex(
        "5204b124a264b0bbf86360e365f0c9a0cb6e3ea57dda97196af015d64ccfa6b1"
    ),
    public_key=bytes.fromhex(
        "021cd5d138ba442c7f8ee9a2b8f4e254dc599a57d42c69b7194074135a0ba82926"
    ),
)


def get_multisig(
    path: list[int], xpubs: list[HDNodeType], pubkeys_order: MultisigPubkeysOrder
) -> MultisigRedeemScriptType:
    return MultisigRedeemScriptType(
        nodes=xpubs,
        signatures=b"" * len(xpubs),
        address_n=path[-2:],
        m=2,
        pubkeys_order=pubkeys_order,
    )


def get_singlesig_input(path: list[int]) -> TxInput:
    return TxInput(
        address_n=path,
        amount=1_000_000,
        prev_hash=bytes(32),
        prev_index=0,
        script_type=InputScriptType.SPENDADDRESS,
    )


def get_multisig_input(
    path: list[int], xpubs: list[HDNodeType], pubkeys_order: MultisigPubkeysOrder
) -> TxInput:
    return TxInput(
        address_n=path,
        amount=1_000_000,
        prev_hash=bytes(32),
        prev_index=0,
        script_type=InputScriptType.SPENDMULTISIG,
        multisig=get_multisig(path, xpubs, pubkeys_order),
    )


def get_internal_multisig_output(
    path: list[int], xpubs: list[HDNodeType], pubkeys_order: MultisigPubkeysOrder
) -> TxOutput:
    return TxOutput(
        address_n=path,
        amount=1_000_000,
        script_type=OutputScriptType.PAYTOMULTISIG,
        multisig=get_multisig(path, xpubs, pubkeys_order),
    )


def get_internal_singlesig_output(path: list[int]) -> TxOutput:
    return TxOutput(
        address_n=path,
        amount=1_000_000,
        script_type=OutputScriptType.PAYTOADDRESS,
    )


def get_external_singlesig_output():
    return TxOutput(
        address="1JAd7XCBzGudGpJQSDSfpmJhiygtLQWaGL",
        amount=1_000_000,
        script_type=OutputScriptType.PAYTOADDRESS,
    )


# BIP-48 account used by the Miniscript tests
MINISCRIPT_ACCOUNT = [H_(48), H_(1), H_(0), H_(2)]


class FakeRegisteredPolicy:
    def __init__(self, digest: bytes, name: str) -> None:
        self.digest = digest
        self.name = name


# Policies #0 and #2 are the same, policy #1 is different.
MINISCRIPT_POLICIES = [
    FakeRegisteredPolicy(b"\x01" * 32, "Liana"),
    FakeRegisteredPolicy(b"\x02" * 32, "Other"),
    FakeRegisteredPolicy(b"\x01" * 32, "Liana"),
]


def get_miniscript_redeem(
    policy_index: int, internal: bool, index: int
) -> MiniscriptRedeemPolicyType:
    return MiniscriptRedeemPolicyType(
        policy_index=policy_index,
        derivation=MiniscriptDerivation(internal=internal, index=index),
    )


def get_miniscript_input(
    policy_index: int, child: int, internal: bool, index: int
) -> TxInput:
    return TxInput(
        address_n=MINISCRIPT_ACCOUNT + [child, index],
        amount=1_000_000,
        prev_hash=bytes(32),
        prev_index=0,
        script_type=InputScriptType.SPENDWITNESS,
        miniscript=get_miniscript_redeem(policy_index, internal, index),
    )


def get_miniscript_output(
    policy_index: int,
    internal: bool,
    index: int,
    script_type: OutputScriptType = OutputScriptType.PAYTOWITNESS,
    amount: int = 1_000_000,
) -> TxOutput:
    return TxOutput(
        amount=amount,
        script_type=script_type,
        miniscript=get_miniscript_redeem(policy_index, internal, index),
    )


def get_singlesig_witness_input(path: list[int]) -> TxInput:
    return TxInput(
        address_n=path,
        amount=1_000_000,
        prev_hash=bytes(32),
        prev_index=0,
        script_type=InputScriptType.SPENDWITNESS,
    )


def get_internal_singlesig_witness_output(path: list[int]) -> TxOutput:
    return TxOutput(
        address_n=path,
        amount=1_000_000,
        script_type=OutputScriptType.PAYTOWITNESS,
    )


class TestChangeDetector(unittest.TestCase):
    def setUp(self):
        self.d = ChangeDetector()

    def test_singlesig(self):
        # Different change and account indices
        self.d.add_input(get_singlesig_input([H_(45), 0, 0, 0]))
        self.d.add_input(get_singlesig_input([H_(45), 0, 0, 1]))
        self.d.add_input(get_singlesig_input([H_(45), 0, 1, 0]))
        self.d.add_input(get_singlesig_input([H_(45), 0, 1, 1]))

        # Same outputs as inputs
        assert (
            self.d.output_is_change(get_internal_singlesig_output([H_(45), 0, 0, 0]))
            is True
        )
        assert (
            self.d.output_is_change(get_internal_singlesig_output([H_(45), 0, 0, 1]))
            is True
        )
        assert (
            self.d.output_is_change(get_internal_singlesig_output([H_(45), 0, 1, 0]))
            is True
        )
        assert (
            self.d.output_is_change(get_internal_singlesig_output([H_(45), 0, 1, 1]))
            is True
        )

        # Different account index
        assert (
            self.d.output_is_change(get_internal_singlesig_output([H_(45), 1, 0, 0]))
            is False
        )

        # Multisig instead of singlesig
        assert (
            self.d.output_is_change(
                get_internal_multisig_output([H_(45), 0, 0, 0], [xpub1], PRESERVED)
            )
            is False
        )
        assert (
            self.d.output_is_change(
                get_internal_multisig_output([H_(45), 0, 0, 0], [xpub1], LEXICOGRAPHIC)
            )
            is False
        )

        # External output
        assert self.d.output_is_change(get_external_singlesig_output()) is False

    def test_singlesig_different_account_indices(self):
        # Different account indices
        self.d.add_input(get_singlesig_input([H_(45), 0, 0, 0]))
        self.d.add_input(get_singlesig_input([H_(45), 1, 0, 0]))

        # Same outputs as inputs
        assert (
            self.d.output_is_change(get_internal_singlesig_output([H_(45), 0, 0, 0]))
            is False
        )
        assert (
            self.d.output_is_change(get_internal_singlesig_output([H_(45), 1, 0, 0]))
            is False
        )

        # Multisig instead of singlesig
        assert (
            self.d.output_is_change(
                get_internal_multisig_output([H_(45), 1, 0, 0], [xpub1], PRESERVED)
            )
            is False
        )
        assert (
            self.d.output_is_change(
                get_internal_multisig_output([H_(45), 1, 0, 0], [xpub1], LEXICOGRAPHIC)
            )
            is False
        )

        # External output
        assert self.d.output_is_change(get_external_singlesig_output()) is False

    def test_unsorted_multisig(self):
        # Different change and account index
        self.d.add_input(
            get_multisig_input([H_(45), 0, 0, 0], [xpub1, xpub2], PRESERVED)
        )
        self.d.add_input(
            get_multisig_input([H_(45), 0, 0, 1], [xpub1, xpub2], PRESERVED)
        )
        self.d.add_input(
            get_multisig_input([H_(45), 0, 1, 0], [xpub1, xpub2], PRESERVED)
        )
        self.d.add_input(
            get_multisig_input([H_(45), 0, 1, 1], [xpub1, xpub2], PRESERVED)
        )

        # Same outputs as inputs
        assert (
            self.d.output_is_change(
                get_internal_multisig_output(
                    [H_(45), 0, 0, 0], [xpub1, xpub2], PRESERVED
                )
            )
            is True
        )
        assert (
            self.d.output_is_change(
                get_internal_multisig_output(
                    [H_(45), 0, 0, 1], [xpub1, xpub2], PRESERVED
                )
            )
            is True
        )
        assert (
            self.d.output_is_change(
                get_internal_multisig_output(
                    [H_(45), 0, 1, 0], [xpub1, xpub2], PRESERVED
                )
            )
            is True
        )
        assert (
            self.d.output_is_change(
                get_internal_multisig_output(
                    [H_(45), 0, 1, 1], [xpub1, xpub2], PRESERVED
                )
            )
            is True
        )

        # Singlesig instead of multisig
        assert (
            self.d.output_is_change(get_internal_singlesig_output([H_(45), 0, 0, 0]))
            is False
        )

        # Different account index
        assert (
            self.d.output_is_change(get_internal_singlesig_output([H_(45), 1, 0, 0]))
            is False
        )

        # Different order of xpubs
        assert (
            self.d.output_is_change(
                get_internal_multisig_output(
                    [H_(45), 0, 0, 0], [xpub2, xpub1], PRESERVED
                )
            )
            is False
        )

        # Sorted instead of unsorted
        assert (
            self.d.output_is_change(
                get_internal_multisig_output(
                    [H_(45), 0, 0, 0], [xpub1, xpub2], LEXICOGRAPHIC
                )
            )
            is False
        )

        # Different xpubs
        assert (
            self.d.output_is_change(
                get_internal_multisig_output(
                    [H_(45), 0, 0, 0], [xpub1, xpub3], PRESERVED
                )
            )
            is False
        )

        # External output
        assert self.d.output_is_change(get_external_singlesig_output()) is False

    def test_sorted_multisig(self):
        # Different change and account index
        self.d.add_input(
            get_multisig_input([H_(45), 0, 0, 0], [xpub1, xpub2], LEXICOGRAPHIC)
        )
        self.d.add_input(
            get_multisig_input([H_(45), 0, 0, 1], [xpub1, xpub2], LEXICOGRAPHIC)
        )
        self.d.add_input(
            get_multisig_input([H_(45), 0, 1, 0], [xpub1, xpub2], LEXICOGRAPHIC)
        )
        self.d.add_input(
            get_multisig_input([H_(45), 0, 1, 1], [xpub1, xpub2], LEXICOGRAPHIC)
        )

        # Same outputs as inputs
        assert (
            self.d.output_is_change(
                get_internal_multisig_output(
                    [H_(45), 0, 0, 0], [xpub1, xpub2], LEXICOGRAPHIC
                )
            )
            is True
        )
        assert (
            self.d.output_is_change(
                get_internal_multisig_output(
                    [H_(45), 0, 0, 1], [xpub1, xpub2], LEXICOGRAPHIC
                )
            )
            is True
        )
        assert (
            self.d.output_is_change(
                get_internal_multisig_output(
                    [H_(45), 0, 1, 0], [xpub1, xpub2], LEXICOGRAPHIC
                )
            )
            is True
        )
        assert (
            self.d.output_is_change(
                get_internal_multisig_output(
                    [H_(45), 0, 1, 1], [xpub1, xpub2], LEXICOGRAPHIC
                )
            )
            is True
        )

        # Singlesig instead of multisig
        assert (
            self.d.output_is_change(get_internal_singlesig_output([H_(45), 0, 0, 0]))
            is False
        )

        # Different account index
        assert (
            self.d.output_is_change(get_internal_singlesig_output([H_(45), 1, 0, 0]))
            is False
        )

        # Different order of xpubs
        assert (
            self.d.output_is_change(
                get_internal_multisig_output(
                    [H_(45), 0, 0, 0], [xpub2, xpub1], LEXICOGRAPHIC
                )
            )
            is True
        )

        # Unsorted instead of sorted
        assert (
            self.d.output_is_change(
                get_internal_multisig_output(
                    [H_(45), 0, 0, 0], [xpub1, xpub2], PRESERVED
                )
            )
            is False
        )

        # Different xpubs
        assert (
            self.d.output_is_change(
                get_internal_multisig_output(
                    [H_(45), 0, 0, 0], [xpub1, xpub3], LEXICOGRAPHIC
                )
            )
            is False
        )

        # External output
        assert self.d.output_is_change(get_external_singlesig_output()) is False

    def test_unsorted_multisig_different_xpubs_order(self):
        # Different order of xpubs
        self.d.add_input(
            get_multisig_input([H_(45), 0, 0, 0], [xpub1, xpub2], PRESERVED)
        )
        self.d.add_input(
            get_multisig_input([H_(45), 0, 0, 0], [xpub2, xpub1], PRESERVED)
        )

        # Same ouputs as inputs
        assert (
            self.d.output_is_change(
                get_internal_multisig_output(
                    [H_(45), 0, 0, 0], [xpub1, xpub2], PRESERVED
                )
            )
            is False
        )
        assert (
            self.d.output_is_change(
                get_internal_multisig_output(
                    [H_(45), 0, 0, 0], [xpub2, xpub1], PRESERVED
                )
            )
            is False
        )

        # Sorted instead of unsorted
        assert (
            self.d.output_is_change(
                get_internal_multisig_output(
                    [H_(45), 0, 0, 0], [xpub1, xpub2], LEXICOGRAPHIC
                )
            )
            is False
        )
        assert (
            self.d.output_is_change(
                get_internal_multisig_output(
                    [H_(45), 0, 0, 0], [xpub2, xpub1], LEXICOGRAPHIC
                )
            )
            is False
        )

        # Singlesig instead of multisig
        assert (
            self.d.output_is_change(get_internal_singlesig_output([H_(45), 0, 0, 0]))
            is False
        )

        # External output
        assert self.d.output_is_change(get_external_singlesig_output()) is False

    def test_sorted_multisig_different_xpubs_order(self):
        # Different order of xpubs
        self.d.add_input(
            get_multisig_input([H_(45), 0, 0, 0], [xpub1, xpub2], LEXICOGRAPHIC)
        )
        self.d.add_input(
            get_multisig_input([H_(45), 0, 0, 0], [xpub2, xpub1], LEXICOGRAPHIC)
        )

        # Same ouputs as inputs
        assert (
            self.d.output_is_change(
                get_internal_multisig_output(
                    [H_(45), 0, 0, 0], [xpub1, xpub2], LEXICOGRAPHIC
                )
            )
            is True
        )
        assert (
            self.d.output_is_change(
                get_internal_multisig_output(
                    [H_(45), 0, 0, 0], [xpub2, xpub1], LEXICOGRAPHIC
                )
            )
            is True
        )

        # Sorted instead of unsorted
        assert (
            self.d.output_is_change(
                get_internal_multisig_output(
                    [H_(45), 0, 0, 0], [xpub1, xpub2], PRESERVED
                )
            )
            is False
        )
        assert (
            self.d.output_is_change(
                get_internal_multisig_output(
                    [H_(45), 0, 0, 0], [xpub2, xpub1], PRESERVED
                )
            )
            is False
        )

        # Singlesig instead of multisig
        assert (
            self.d.output_is_change(get_internal_singlesig_output([H_(45), 0, 0, 0]))
            is False
        )

        # External output
        assert self.d.output_is_change(get_external_singlesig_output()) is False

    def test_unsorted_multisig_different_xpubs(self):
        # Different xpubs
        self.d.add_input(
            get_multisig_input([H_(45), 0, 0, 0], [xpub1, xpub2], PRESERVED)
        )
        self.d.add_input(
            get_multisig_input([H_(45), 0, 0, 0], [xpub1, xpub3], PRESERVED)
        )

        # Same ouputs as inputs
        assert (
            self.d.output_is_change(
                get_internal_multisig_output(
                    [H_(45), 0, 0, 0], [xpub1, xpub2], PRESERVED
                )
            )
            is False
        )
        assert (
            self.d.output_is_change(
                get_internal_multisig_output(
                    [H_(45), 0, 0, 0], [xpub1, xpub3], PRESERVED
                )
            )
            is False
        )

        # Sorted instead of unsorted
        assert (
            self.d.output_is_change(
                get_internal_multisig_output(
                    [H_(45), 0, 0, 0], [xpub1, xpub2], LEXICOGRAPHIC
                )
            )
            is False
        )
        assert (
            self.d.output_is_change(
                get_internal_multisig_output(
                    [H_(45), 0, 0, 0], [xpub1, xpub3], LEXICOGRAPHIC
                )
            )
            is False
        )

        # Singlesig instead of multisig
        assert (
            self.d.output_is_change(get_internal_singlesig_output([H_(45), 0, 0, 0]))
            is False
        )

        # External output
        assert self.d.output_is_change(get_external_singlesig_output()) is False

    def test_sorted_multisig_different_xpubs(self):
        # Different xpubs
        self.d.add_input(
            get_multisig_input([H_(45), 0, 0, 0], [xpub1, xpub2], LEXICOGRAPHIC)
        )
        self.d.add_input(
            get_multisig_input([H_(45), 0, 0, 0], [xpub1, xpub3], LEXICOGRAPHIC)
        )

        # Same ouputs as inputs
        assert (
            self.d.output_is_change(
                get_internal_multisig_output(
                    [H_(45), 0, 0, 0], [xpub1, xpub2], LEXICOGRAPHIC
                )
            )
            is False
        )
        assert (
            self.d.output_is_change(
                get_internal_multisig_output(
                    [H_(45), 0, 0, 0], [xpub1, xpub3], LEXICOGRAPHIC
                )
            )
            is False
        )

        # Sorted instead of unsorted
        assert (
            self.d.output_is_change(
                get_internal_multisig_output(
                    [H_(45), 0, 0, 0], [xpub1, xpub2], PRESERVED
                )
            )
            is False
        )
        assert (
            self.d.output_is_change(
                get_internal_multisig_output(
                    [H_(45), 0, 0, 0], [xpub1, xpub3], PRESERVED
                )
            )
            is False
        )

        # Singlesig instead of multisig
        assert (
            self.d.output_is_change(get_internal_singlesig_output([H_(45), 0, 0, 0]))
            is False
        )

        # External output
        assert self.d.output_is_change(get_external_singlesig_output()) is False

    def test_mixed_sorted_and_unsorted_multisig_1(self):
        self.d.add_input(get_multisig_input([H_(45), 0, 0, 0], [xpub1], PRESERVED))
        self.d.add_input(get_multisig_input([H_(45), 0, 0, 0], [xpub1], LEXICOGRAPHIC))

        # Same ouputs as inputs
        assert (
            self.d.output_is_change(
                get_internal_multisig_output([H_(45), 0, 0, 0], [xpub1], PRESERVED)
            )
            is False
        )
        assert (
            self.d.output_is_change(
                get_internal_multisig_output([H_(45), 0, 0, 0], [xpub1], LEXICOGRAPHIC)
            )
            is False
        )

        # Singlesig instead of multisig
        assert (
            self.d.output_is_change(get_internal_singlesig_output([H_(45), 0, 0, 0]))
            is False
        )

        # External output
        assert self.d.output_is_change(get_external_singlesig_output()) is False


@unittest.skipUnless(utils.USE_MINISCRIPT, "miniscript")
class TestMiniscriptChangeDetector(unittest.TestCase):
    def setUp(self):
        self.d = ChangeDetector(MINISCRIPT_POLICIES)

    def test_miniscript(self):
        # Different key expressions (primary & recovery) and derivations
        self.d.add_input(get_miniscript_input(0, 0, False, 1))
        self.d.add_input(get_miniscript_input(0, 1, True, 2))
        self.d.add_input(get_miniscript_input(0, 2, False, 3))

        # Same policy, both external and internal derivations
        assert self.d.output_is_change(get_miniscript_output(0, True, 5)) is True
        assert self.d.output_is_change(get_miniscript_output(0, False, 5)) is True
        assert (
            self.d.output_is_change(get_miniscript_output(0, True, 1_000_000)) is True
        )

        # Same policy, using another index in SignTx.policies
        assert self.d.output_is_change(get_miniscript_output(2, True, 5)) is True

        # Different policy
        assert self.d.output_is_change(get_miniscript_output(1, True, 5)) is False

        # Derivation index too large
        assert (
            self.d.output_is_change(get_miniscript_output(0, True, 1_000_001)) is False
        )

        # Zero amount
        assert (
            self.d.output_is_change(get_miniscript_output(0, True, 5, amount=0))
            is False
        )

        # Different script type
        assert (
            self.d.output_is_change(
                get_miniscript_output(0, True, 5, OutputScriptType.PAYTOP2SHWITNESS)
            )
            is False
        )

        # Singlesig output using the same account
        assert (
            self.d.output_is_change(
                get_internal_singlesig_witness_output(MINISCRIPT_ACCOUNT + [1, 5])
            )
            is False
        )

        # Multisig output using the same account
        assert (
            self.d.output_is_change(
                get_internal_multisig_output(
                    MINISCRIPT_ACCOUNT + [1, 5], [xpub1], PRESERVED
                )
            )
            is False
        )

        # External output
        assert self.d.output_is_change(get_external_singlesig_output()) is False

    def test_miniscript_different_policies(self):
        self.d.add_input(get_miniscript_input(0, 0, False, 1))
        self.d.add_input(get_miniscript_input(1, 0, False, 1))

        assert self.d.output_is_change(get_miniscript_output(0, True, 5)) is False
        assert self.d.output_is_change(get_miniscript_output(1, True, 5)) is False

    def test_miniscript_same_policy_different_index(self):
        self.d.add_input(get_miniscript_input(0, 0, False, 1))
        self.d.add_input(get_miniscript_input(2, 0, False, 2))

        assert self.d.output_is_change(get_miniscript_output(0, True, 5)) is True
        assert self.d.output_is_change(get_miniscript_output(2, True, 5)) is True

    def test_miniscript_and_singlesig_inputs(self):
        self.d.add_input(get_miniscript_input(0, 0, False, 1))
        self.d.add_input(get_singlesig_witness_input(MINISCRIPT_ACCOUNT + [0, 2]))

        assert self.d.output_is_change(get_miniscript_output(0, True, 5)) is False
        assert (
            self.d.output_is_change(
                get_internal_singlesig_witness_output(MINISCRIPT_ACCOUNT + [1, 5])
            )
            is False
        )

    def test_singlesig_inputs(self):
        self.d.add_input(get_singlesig_witness_input(MINISCRIPT_ACCOUNT + [0, 1]))
        self.d.add_input(get_singlesig_witness_input(MINISCRIPT_ACCOUNT + [0, 2]))

        # Miniscript output is not a change-output
        assert self.d.output_is_change(get_miniscript_output(0, True, 5)) is False

        # Singlesig output is still a change-output
        assert (
            self.d.output_is_change(
                get_internal_singlesig_witness_output(MINISCRIPT_ACCOUNT + [1, 5])
            )
            is True
        )

    def test_check_input(self):
        self.d.add_input(get_miniscript_input(0, 0, False, 1))
        assert self.d.output_is_change(get_miniscript_output(0, True, 5)) is True

        # Same policy
        self.d.check_input(get_miniscript_input(0, 0, False, 1))
        self.d.check_input(get_miniscript_input(2, 0, False, 1))

        # Different policy
        with self.assertRaises(ProcessError):
            self.d.check_input(get_miniscript_input(1, 0, False, 1))

        # Singlesig instead of Miniscript
        with self.assertRaises(ProcessError):
            self.d.check_input(get_singlesig_witness_input(MINISCRIPT_ACCOUNT + [0, 1]))

    def test_account_name(self):
        # No inputs
        assert self.d.account_name() is None

        self.d.add_input(get_miniscript_input(0, 0, False, 1))
        assert self.d.account_name() == "Liana"

        # Same policy, using another index in SignTx.policies
        self.d.add_input(get_miniscript_input(2, 1, True, 2))
        assert self.d.account_name() == "Liana"

    def test_account_name_different_policies(self):
        self.d.add_input(get_miniscript_input(0, 0, False, 1))
        self.d.add_input(get_miniscript_input(1, 0, False, 1))
        assert self.d.account_name() is None

    def test_account_name_singlesig(self):
        self.d.add_input(get_singlesig_witness_input(MINISCRIPT_ACCOUNT + [0, 1]))
        assert self.d.account_name() is None

    def test_account_name_mixed_inputs(self):
        self.d.add_input(get_miniscript_input(0, 0, False, 1))
        self.d.add_input(get_singlesig_witness_input(MINISCRIPT_ACCOUNT + [0, 2]))
        assert self.d.account_name() is None

    def test_invalid_policy_index(self):
        with self.assertRaises(DataError):
            self.d.add_input(get_miniscript_input(3, 0, False, 1))


if __name__ == "__main__":
    unittest.main()
