# flake8: noqa: F403,F405
from common import *  # isort:skip

# CKB ships on T3W1 only (core/SConscript.unix).
_CKB = not utils.BITCOIN_ONLY and utils.INTERNAL_MODEL == "T3W1"

if _CKB:
    from trezor.messages import CKBBlockHeader, CKBCellDep, CKBCellInput, CKBCellOutput
    from trezor.wire import DataError

    from apps.ckb import helpers
    from apps.ckb.sign_tx import (
        _blake2b_hash,
        _build_witness_args,
        _compute_raw_tx_hash,
        _compute_sighash_all,
        _is_dao_type_script,
        _is_dao_withdrawing_cell,
        _occupied_capacity,
        _serialize_cell_dep,
        _serialize_cell_input,
        _serialize_header,
        _serialize_script,
        _validate_sign_group,
    )

    DAO_CODE_HASH = unhexlify(
        "82d76d1b75fe2fd9a27dfbaa65a039221a380d76c926f378d3f81cf3e7e13f2e"
    )
    SECP_CODE_HASH = unhexlify(
        "9bd7e06f3ecf4be0f2fcd2188b23f1b9fcc88e5d4b65a8637b17723bbda3cce8"
    )

    def _cell(capacity=1000, lock_args=b"\x11" * 20, **kwargs):
        return CKBCellOutput(
            capacity=capacity,
            lock_code_hash=SECP_CODE_HASH,
            lock_hash_type=1,
            lock_args=lock_args,
            **kwargs,
        )


@unittest.skipUnless(_CKB, "CKB is T3W1 only")
class TestCkbSerialization(unittest.TestCase):
    """The Molecule serialization and hashing, anchored to real CKB chain data."""

    def test_raw_tx_hash_matches_real_block_tx(self):
        # CKB testnet tx 0x9a8ad792..., 1 input / 1 output / 1 dep_group dep.
        inputs = [
            CKBCellInput(
                previous_output_tx_hash=unhexlify(
                    "7337f83101d63e1c94b485062281e33429c72b5a290649cbdb43395b17d0576b"
                ),
                previous_output_index=0,
            )
        ]
        outputs = [
            _cell(
                capacity=27_135_496_481,
                lock_args=unhexlify("fa9e6338fb52b39ff39a3ca11c0ad793c0efeaf6"),
            )
        ]
        cell_deps = [
            CKBCellDep(
                tx_hash=unhexlify(
                    "f8de3bb47d055cdf460d93a2a6e1b05f7432f9777c8c474abf4eec1d4aee5d37"
                ),
                index=0,
                dep_type=1,
            )
        ]

        tx_hash = _compute_raw_tx_hash(inputs, outputs, [b""], cell_deps)

        self.assertEqual(
            hexlify(tx_hash),
            b"9a8ad7922b5f03a3072fc5cb4aac6194e55a5f2c4ee43483010002b42d3b44dc",
        )

    def test_raw_tx_hash_commits_header_deps_and_type_scripts(self):
        # Pins the ScriptOpt "Some" arm and a non-empty header_deps FixVec, which
        # the real-tx vector above has neither of. Expected values computed by
        # the host oracle in tests/device_tests/ckb/prevtx.py.
        inputs = [
            CKBCellInput(
                previous_output_tx_hash=b"\x33" * 32,
                previous_output_index=1,
                since=42,
            )
        ]
        outputs = [
            _cell(
                capacity=50_000_000_000,
                type_code_hash=DAO_CODE_HASH,
                type_hash_type=1,
                type_args=b"",
                data=bytes(8),
            )
        ]
        header_deps = [b"\x11" * 32, b"\x22" * 32]

        tx_hash = _compute_raw_tx_hash(
            inputs, outputs, [bytes(8)], [], header_deps=header_deps
        )

        self.assertEqual(
            hexlify(tx_hash),
            b"ce9bfe474a1eefdd18c03be7f3ba8cd7a5aa933591ac3222e8e22309ec9ce47b",
        )
        # ...and the header_deps are really committed, not ignored.
        self.assertEqual(
            hexlify(_compute_raw_tx_hash(inputs, outputs, [bytes(8)], [])),
            b"d65e0d8b4bb1c175c93721ae64f68bac27f88fc850d3137b27d49e5ff98a1390",
        )

    def test_sighash_all_matches_real_signed_tx(self):
        # The digest of the same tx as signed on chain; also pins
        # _build_witness_args, which produced the blanked witness.
        tx_hash = unhexlify(
            "9a8ad7922b5f03a3072fc5cb4aac6194e55a5f2c4ee43483010002b42d3b44dc"
        )
        blanked = _build_witness_args(65, None, None)

        sighash = _compute_sighash_all(tx_hash, [blanked], [0], 1)

        self.assertEqual(
            hexlify(sighash),
            b"b8bba12b59dbf39447ae69006c63e67ce7f8d94020cd3ee4110787dc4c83e77a",
        )

    def test_header_hash_matches_real_block(self):
        # Real CKB testnet block 0x14862de.
        header = CKBBlockHeader(
            version=0,
            compact_target=0x1D092A51,
            timestamp=0x19EF54A43FF,
            number=0x14862DE,
            epoch=0x708030D00340F,
            parent_hash=unhexlify(
                "2ce3fc21e61547b9f3cf64607ede99db89b57105f863fc0d54e2551a4b73ae11"
            ),
            transactions_root=unhexlify(
                "459a8d141f32618ab6b0d0009e6c0519dabee211eda82ff0bc6f8bf440bc14a5"
            ),
            proposals_hash=unhexlify(
                "d89c1955e7aede1c654347f5fbc7b01eaaa42de9b8b8f38fd435502ccf40a3ad"
            ),
            extra_hash=unhexlify(
                "2a1c789d4f5b25c7314d9b519d136cdfacf639c066cb15496fd9c0f0050703fb"
            ),
            dao=unhexlify(
                "92e19928da715f5721051281c41d2a00ec383bac641ff50900032e1e81ec5c09"
            ),
            # the RPC nonce dca82cb7e9a6532774df50405ea8f7b4, byte-reversed:
            # the Molecule serialization stores it little-endian
            nonce=unhexlify("b4f7a85e4050df742753a6e9b72ca8dc"),
        )

        block_hash = _blake2b_hash(_serialize_header(header))

        self.assertEqual(
            hexlify(block_hash),
            b"6e94518dac325b38b689e0632cb8f7d39bc5feb1f4761140acb02174ccadb4d0",
        )

    def test_message_digest(self):
        # blake2b("ckb-default-hash", "Nervos Message:" || message), as ckb-cli
        # and Neuron compute it.
        digest = helpers.message_digest(b"This is an example of a signed message.")
        self.assertEqual(
            hexlify(digest),
            b"6f5821c0b5278b9e9f13e01b884da7611eb9475dabacc0f366f9a84a580343f6",
        )

    def test_serialize_script_rejects_malformed_fields(self):
        with self.assertRaises(DataError):
            _serialize_script(b"\x00" * 31, 1, b"")  # short code hash
        with self.assertRaises(DataError):
            _serialize_script(b"\x00" * 32, 3, b"")  # 3 is not a CKB hash_type

    def test_serialize_cell_input_rejects_short_hash(self):
        inp = CKBCellInput(
            previous_output_tx_hash=b"\x00" * 31, previous_output_index=0
        )
        with self.assertRaises(DataError):
            _serialize_cell_input(inp)

    def test_serialize_cell_dep_rejects_malformed_fields(self):
        with self.assertRaises(DataError):
            _serialize_cell_dep(CKBCellDep(tx_hash=b"\x00" * 31, index=0, dep_type=1))
        with self.assertRaises(DataError):
            _serialize_cell_dep(CKBCellDep(tx_hash=b"\x00" * 32, index=0, dep_type=2))

    def test_raw_tx_hash_rejects_short_header_dep(self):
        with self.assertRaises(DataError):
            _compute_raw_tx_hash([], [_cell()], [b""], [], header_deps=[b"\x00" * 31])


@unittest.skipUnless(_CKB, "CKB is T3W1 only")
class TestCkbSignGroup(unittest.TestCase):
    def test_accepts_a_sorted_group(self):
        _validate_sign_group([0, 2, 5], inputs_count=6, witnesses_count=6)

    def test_rejects_bad_groups(self):
        with self.assertRaises(DataError):
            _validate_sign_group([], 1, 1)
        with self.assertRaises(DataError):
            _validate_sign_group([0, 0], 2, 2)  # duplicate
        with self.assertRaises(DataError):
            _validate_sign_group([1, 0], 2, 2)  # unsorted
        with self.assertRaises(DataError):
            _validate_sign_group([0, 5], 2, 2)  # index >= inputs_count
        with self.assertRaises(DataError):
            _validate_sign_group([1], 2, 1)  # signing witness absent


@unittest.skipUnless(_CKB, "CKB is T3W1 only")
class TestCkbDaoCells(unittest.TestCase):
    """The classification that decides which confirmation screen an output gets
    and whether an input earns DAO compensation."""

    def test_dao_type_script_is_exact(self):
        dao = _cell(type_code_hash=DAO_CODE_HASH, type_hash_type=1, type_args=b"")
        self.assertTrue(_is_dao_type_script(dao))

        self.assertFalse(_is_dao_type_script(_cell()))  # no type script
        self.assertFalse(
            # near-miss: DAO code hash but with args
            _is_dao_type_script(
                _cell(type_code_hash=DAO_CODE_HASH, type_hash_type=1, type_args=b"\x01")
            )
        )
        self.assertFalse(
            # wrong hash type
            _is_dao_type_script(
                _cell(type_code_hash=DAO_CODE_HASH, type_hash_type=0, type_args=b"")
            )
        )
        self.assertFalse(
            _is_dao_type_script(
                _cell(type_code_hash=SECP_CODE_HASH, type_hash_type=1, type_args=b"")
            )
        )

    def test_withdrawing_cell_requires_a_deposit_number(self):
        def dao_cell(data):
            return _cell(
                type_code_hash=DAO_CODE_HASH,
                type_hash_type=1,
                type_args=b"",
                data=data,
            )

        # phase-2 withdrawing cell
        self.assertTrue(_is_dao_withdrawing_cell(dao_cell((100).to_bytes(8, "little"))))
        # a fresh deposit: spendable, but earns nothing yet
        self.assertFalse(_is_dao_withdrawing_cell(dao_cell(bytes(8))))
        # wrong data size
        self.assertFalse(_is_dao_withdrawing_cell(dao_cell(b"\x01" * 7)))
        self.assertFalse(_is_dao_withdrawing_cell(_cell()))

    def test_occupied_capacity(self):
        # 8 (capacity) + 33 (lock) + 20 (args) + 33 (type) + 0 (type args) + 8
        # (data) = 102 occupied bytes, i.e. 102 CKB of occupied capacity.
        cell = _cell(
            lock_args=b"\x11" * 20,
            type_code_hash=DAO_CODE_HASH,
            type_hash_type=1,
            type_args=b"",
            data=bytes(8),
        )
        self.assertEqual(_occupied_capacity(cell), 102 * 100_000_000)


if __name__ == "__main__":
    unittest.main()
