from common import H_, await_result, unittest  # isort:skip
from ubinascii import hexlify, unhexlify

from trezor.enums import InputScriptType, OutputScriptType
from trezor.messages import (
    TxInput,
    TxOutput,
    HDNodeType,
    MultisigRedeemScriptType,
)

from apps.bitcoin.sign_tx.change_detector import ChangeDetector

# all all all all all all all all all all all all/45/0
xpub1 = HDNodeType(
    depth=2,
    fingerprint=50263508,
    child_num=0,
    chain_code=unhexlify("8eb1f96a45dcb693dbad61f5184871d999127a37f1b0d4dae9964eaf3fb0e15b"),
    public_key=unhexlify("03922315cd2d2d874e4c55add2e0ea41af9c2957f02c0abe0f55285d364a067b61"),
)

# all all all all all all all all all all all all/45/1
xpub2 = HDNodeType(
    depth=2,
    fingerprint=50263508,
    child_num=1,
    chain_code=unhexlify("acad50a7e52e44841d42bec6886df516974f8d366bc471a8515dfc69a6692700"),
    public_key=unhexlify("02e6f3bf3093b45705e3d838490377e0d99eed911ca01990d1e94acd445dee59e8"),
)

# all all all all all all all all all all all all/45/2
xpub3 = HDNodeType(
    depth=2,
    fingerprint=50263508,
    child_num=2,
    chain_code=unhexlify("5204b124a264b0bbf86360e365f0c9a0cb6e3ea57dda97196af015d64ccfa6b1"),
    public_key=unhexlify("021cd5d138ba442c7f8ee9a2b8f4e254dc599a57d42c69b7194074135a0ba82926"),
)


def get_multisig(path: list[int], xpubs: list[HDNodeType]) -> MultisigRedeemScriptType:
    return MultisigRedeemScriptType(
        nodes=xpubs,
        signatures=b"" * len(xpubs),
        address_n=path[-2:],
        m=2,
    )


def get_singlesig_input(path: list[int]) -> TxInput:
    return TxInput(
        address_n=path,
        amount=1_000_000,
        prev_hash=bytes(32),
        prev_index=0,
        script_type=InputScriptType.SPENDADDRESS,
    )


def get_multisig_input(path: list[int], xpubs: list[HDNodeType]) -> TxInput:
    return TxInput(
        address_n=path,
        amount=1_000_000,
        prev_hash=bytes(32),
        prev_index=0,
        script_type=InputScriptType.SPENDMULTISIG,
        multisig=get_multisig(path, xpubs),
    )


def get_internal_multisig_output(path: list[int], xpubs: list[HDNodeType]) -> TxOutput:
    return TxOutput(
        address_n=path,
        amount=1_000_000,
        script_type=OutputScriptType.PAYTOMULTISIG,
        multisig=get_multisig(path, xpubs),
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
        assert self.d.output_is_change(get_internal_singlesig_output([H_(45), 0, 0, 0])) == True
        assert self.d.output_is_change(get_internal_singlesig_output([H_(45), 0, 0, 1])) == True
        assert self.d.output_is_change(get_internal_singlesig_output([H_(45), 0, 1, 0])) == True
        assert self.d.output_is_change(get_internal_singlesig_output([H_(45), 0, 1, 1])) == True

        # Different account index
        assert self.d.output_is_change(get_internal_singlesig_output([H_(45), 1, 0, 0])) == False

        # Multisig instead of singlesig
        assert self.d.output_is_change(get_internal_multisig_output([H_(45), 0, 0, 0], [xpub1])) == False

        # External output
        assert self.d.output_is_change(get_external_singlesig_output()) == False

    def test_multisig_different_xpubs_order(self):
        # Different order of xpubs
        self.d.add_input(get_multisig_input([H_(45), 0, 0, 0], [xpub1, xpub2]))
        self.d.add_input(get_multisig_input([H_(45), 0, 0, 0], [xpub2, xpub1]))

        # Same ouputs as inputs
        assert self.d.output_is_change(get_internal_multisig_output([H_(45), 0, 0, 0], [xpub1, xpub2])) == True
        assert self.d.output_is_change(get_internal_multisig_output([H_(45), 0, 0, 0], [xpub2, xpub1])) == True

        # Singlesig instead of multisig
        assert self.d.output_is_change(get_internal_singlesig_output([H_(45), 0, 0, 0])) == True

        # External output
        assert self.d.output_is_change(get_external_singlesig_output()) == False

    def test_multisig(self):
        # Different change and account index
        self.d.add_input(get_multisig_input([H_(45), 0, 0, 0], [xpub1, xpub2]))
        self.d.add_input(get_multisig_input([H_(45), 0, 0, 1], [xpub1, xpub2]))
        self.d.add_input(get_multisig_input([H_(45), 0, 1, 0], [xpub1, xpub2]))
        self.d.add_input(get_multisig_input([H_(45), 0, 1, 1], [xpub1, xpub2]))

        # Same outputs as inputs
        assert self.d.output_is_change(get_internal_multisig_output([H_(45), 0, 0, 0], [xpub1, xpub2])) == True
        assert self.d.output_is_change(get_internal_multisig_output([H_(45), 0, 0, 1], [xpub1, xpub2])) == True
        assert self.d.output_is_change(get_internal_multisig_output([H_(45), 0, 1, 0], [xpub1, xpub2])) == True
        assert self.d.output_is_change(get_internal_multisig_output([H_(45), 0, 1, 1], [xpub1, xpub2])) == True

        # Singlesig instead of multisig
        assert self.d.output_is_change(get_internal_singlesig_output([H_(45), 0, 0, 0])) == True

        # Different account index
        assert self.d.output_is_change(get_internal_singlesig_output([H_(45), 1, 0, 0])) == False

        # Different order of xpubs
        assert self.d.output_is_change(get_internal_multisig_output([H_(45), 0, 0, 0], [xpub2, xpub1])) == True

        # Different xpubs
        assert self.d.output_is_change(get_internal_multisig_output([H_(45), 0, 0, 0], [xpub1, xpub3])) == False

        # External output
        assert self.d.output_is_change(get_external_singlesig_output()) == False

    def test_singlesig_different_account_indices(self):
        # Different account indices
        self.d.add_input(get_singlesig_input([H_(45), 0, 0, 0]))
        self.d.add_input(get_singlesig_input([H_(45), 1, 0, 0]))

        # Same outputs as inputs
        assert self.d.output_is_change(get_internal_singlesig_output([H_(45), 0, 0, 0])) == False
        assert self.d.output_is_change(get_internal_singlesig_output([H_(45), 1, 0, 0])) == False

        # Multisig instead of singlesig
        assert self.d.output_is_change(get_internal_multisig_output([H_(45), 0, 0, 0], [xpub1])) == False

        # External output
        assert self.d.output_is_change(get_external_singlesig_output()) == False

    def test_multisig_different_xpubs(self):
        # Different xpubs
        self.d.add_input(get_multisig_input([H_(45), 0, 0, 0], [xpub1, xpub2]))
        self.d.add_input(get_multisig_input([H_(45), 0, 0, 0], [xpub1, xpub3]))

        # Same ouputs as inputs
        assert self.d.output_is_change(get_internal_multisig_output([H_(45), 0, 0, 0], [xpub1, xpub2])) == False
        assert self.d.output_is_change(get_internal_multisig_output([H_(45), 0, 0, 0], [xpub1, xpub3])) == False

        # Singlesig instead of multisig
        assert self.d.output_is_change(get_internal_singlesig_output([H_(45), 0, 0, 0])) == True

        # External output
        assert self.d.output_is_change(get_external_singlesig_output()) == False


if __name__ == "__main__":
    unittest.main()
