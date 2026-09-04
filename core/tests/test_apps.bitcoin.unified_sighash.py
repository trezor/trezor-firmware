# flake8: noqa: F403,F405
from common import *  # isort:skip

from trezor.messages import PrevOutput, SignTx, TxInput
from trezor.utils import BufferReader
from unified_sighash_vectors import VECTORS

from apps.bitcoin.common import UNIFIED_SCRIPT_TYPE_TAPROOT, SigHashType
from apps.bitcoin.sign_tx.sig_hasher import BitcoinSigHasher
from apps.common.readers import read_compact_size
from apps.common.writers import write_compact_size

# The only unified hash type we sign with, and the only one implemented. The
# other five commit to less of the transaction than the user approved.
_HASH_TYPE = SigHashType.SIGHASH_ALL_UNIFIED

# Bare/P2SH, SegWit v0 and Taproot key path. Tapscript (3) is script type we
# cannot spend.
_SCRIPT_TYPES = (0, 1, 2)

# Every Bitcoin-family coin the opt-in is enabled for.
_COINS = ("Bitcoin", "Testnet", "Regtest", "Signet")


def read_uint32(r):
    return int.from_bytes(r.read(4), "little")


def read_uint64(r):
    return int.from_bytes(r.read(8), "little")


def parse_tx(raw):
    """Deserialize a non-witness transaction into the pieces the sighash needs."""
    r = BufferReader(raw)
    version = read_uint32(r)
    vin = []
    for _ in range(read_compact_size(r)):
        prev_hash = bytes(reversed(r.read(32)))
        prev_index = read_uint32(r)
        r.read(read_compact_size(r))  # scriptSig
        sequence = read_uint32(r)
        vin.append((prev_hash, prev_index, sequence))
    vout = []
    for _ in range(read_compact_size(r)):
        amount = read_uint64(r)
        vout.append((amount, bytes(r.read(read_compact_size(r)))))
    lock_time = read_uint32(r)
    assert r.remaining_count() == 0
    return version, vin, vout, lock_time


def prefixed(script):
    w = bytearray()
    write_compact_size(w, len(script))
    w.extend(script)
    return w


class TestUnifiedSigHash(unittest.TestCase):
    def test_vectors(self):
        run = 0
        skipped_hash_type = 0
        skipped_script_type = 0

        for (
            script_code,
            raw_tx,
            in_idx,
            hash_type,
            script_type,
            spent,
            expected,
        ) in VECTORS:
            if script_type not in _SCRIPT_TYPES:
                skipped_script_type += 1
                continue
            if hash_type != _HASH_TYPE:
                skipped_hash_type += 1
                continue

            version, vin, vout, lock_time = parse_tx(bytes.fromhex(raw_tx))
            self.assertEqual(len(spent), len(vin))

            hasher = BitcoinSigHasher()
            for (prev_hash, prev_index, sequence), (amount, spk) in zip(vin, spent):
                hasher.add_input(
                    TxInput(
                        prev_hash=prev_hash,
                        prev_index=prev_index,
                        sequence=sequence,
                        amount=amount,
                    ),
                    bytes.fromhex(spk),
                )
            for amount, spk in vout:
                hasher.add_output(PrevOutput(amount=amount, script_pubkey=spk), spk)

            if script_type == UNIFIED_SCRIPT_TYPE_TAPROOT:
                self.assertEqual(script_code, "")
                script = None
            else:
                script = prefixed(bytes.fromhex(script_code))

            result = hasher.hash_unified(
                in_idx,
                SignTx(
                    coin_name="Bitcoin",
                    version=version,
                    lock_time=lock_time,
                    inputs_count=len(vin),
                    outputs_count=len(vout),
                ),
                script_type,
                script,
                hash_type,
            )
            self.assertEqual(result.hex(), expected)
            run += 1

        print(
            f"unified sighash vectors: ran {run}, skipped {skipped_hash_type} for"
            f" hash type (only {hex(_HASH_TYPE)} is implemented) and"
            f" {skipped_script_type} for tapscript"
        )
        self.assertEqual(run, 27)
        self.assertEqual(run + skipped_hash_type + skipped_script_type, len(VECTORS))

    def test_no_chain_parameter(self):
        """The message has no chain parameter, so the same transaction must
        produce the same digest on every network the opt-in is enabled for.
        The only thing that could couple them is the scriptCode, which is
        derived with the coin's script_hash."""
        from trezor.enums import InputScriptType

        from apps.bitcoin.scripts import bip143_script_code_prefixed
        from apps.common import coininfo

        txi = TxInput(
            prev_hash=bytes(32),
            prev_index=0,
            amount=1000,
            script_type=InputScriptType.SPENDWITNESS,
        )
        pubkey = bytes.fromhex(
            "03adc58245cf28406af0ef5cc24b8afba7f1be6c72f279b642d85c48798685f862"
        )
        digests = set()
        for name in _COINS:
            coin = coininfo.by_name(name)
            script_code = bip143_script_code_prefixed(txi, [pubkey], 1, coin)

            hasher = BitcoinSigHasher()
            hasher.add_input(txi, b"\x00\x14" + bytes(20))
            hasher.add_output(
                PrevOutput(amount=900, script_pubkey=b"\x51\x02\x00\x00"),
                b"\x51\x02\x00\x00",
            )
            digests.add(
                hasher.hash_unified(
                    0,
                    SignTx(
                        coin_name=name,
                        version=2,
                        lock_time=0,
                        inputs_count=1,
                        outputs_count=1,
                    ),
                    1,
                    script_code,
                    _HASH_TYPE,
                )
            )
        self.assertEqual(len(digests), 1)


if __name__ == "__main__":
    unittest.main()
