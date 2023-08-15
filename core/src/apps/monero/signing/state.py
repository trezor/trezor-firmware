from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import MoneroTransactionDestinationEntry

    from apps.monero.xmr.credentials import AccountCreds
    from apps.monero.xmr.crypto import Point, Scalar

    Subaddresses = dict[bytes, tuple[int, int]]


class State:

    STEP_INIT = 0
    STEP_INP = 100
    STEP_VINI = 300
    STEP_ALL_IN = 350
    STEP_OUT = 400
    STEP_ALL_OUT = 500
    STEP_SIGN = 600

    def __init__(self) -> None:
        from apps.monero.xmr import crypto
        from apps.monero.xmr.keccak_hasher import KeccakXmrArchive
        from apps.monero.xmr.mlsag_hasher import PreMlsagHasher

        # Account credentials
        # type: AccountCreds
        # - view private/public key
        # - spend private/public key
        # - and its corresponding address
        self.creds: AccountCreds | None = None

        # HMAC/encryption keys used to protect offloaded data
        self.key_hmac: bytes | None = None
        self.key_enc: bytes | None = None

        """
        Transaction keys
        - also denoted as r/R
        - tx_priv is a random number
        - tx_pub is equal to `r*G` or `r*D` for subaddresses
        - for subaddresses the `r` is commonly denoted as `s`, however it is still just a random number
        - the keys are used to derive the one time address and its keys (P = H(A*r)*G + B)
        """
        self.tx_priv: Scalar | None = None
        self.tx_pub: Point | None = None

        """
        In some cases when subaddresses are used we need more tx_keys
        (explained in step 1).
        """
        self.need_additional_txkeys = False

        # Connected client version
        self.client_version = 0
        self.hard_fork = 12

        self.input_count: int | None = 0
        self.output_count = 0
        self.progress_total = 0
        self.progress_cur = 0

        self.output_change: "MoneroTransactionDestinationEntry" | None = None
        self.fee: int | None = 0
        self.tx_type = 0

        # wallet sub-address major index
        self.account_idx: int | None = 0

        # contains additional tx keys if need_additional_tx_keys is True
        self.additional_tx_private_keys: list[Scalar] = []
        self.additional_tx_public_keys: list[bytes] | None = []

        # currently processed input/output index
        self.current_input_index = -1
        self.current_output_index: int | None = -1
        self.is_processing_offloaded = False

        # for pseudo_out recomputation from new mask
        self.input_last_amount: int | None = 0

        self.summary_inputs_money: int | None = 0
        self.summary_outs_money: int | None = 0

        # output commitments
        self.output_pk_commitments: list[bytes] | None = []

        self.output_amounts: list[int] | None = []
        # output *range proof* masks. HP10+ makes them deterministic.
        self.output_masks: list[Scalar] | None = []

        # the range proofs are calculated in batches, this denotes the grouping
        self.rsig_grouping: list[int] | None = []
        # is range proof computing offloaded or not
        self.rsig_offload: bool | None = False

        # sum of all inputs' pseudo out masks
        self.sumpouts_alphas: Scalar = crypto.Scalar(0)
        # sum of all output' pseudo out masks
        self.sumout: Scalar = crypto.Scalar(0)

        self.subaddresses: Subaddresses | None = {}

        # TX_EXTRA_NONCE extra field for tx.extra, due to sort_tx_extra()
        self.extra_nonce: bytes | None = None

        # Last key image seen. Used for input permutation correctness check
        self.last_ki: bytes | None = None

        # Encryption key to release to host after protocol ends without error
        self.opening_key: bytes | None = None

        # Step transition automaton
        self.last_step: int | None = self.STEP_INIT

        """
        Tx prefix hasher/hash. We use the hasher to incrementally hash and then
        store the final hash in tx_prefix_hash.
        See Monero-Trezor documentation section 3.3 for more details.
        """
        self.tx_prefix_hasher: KeccakXmrArchive | None = KeccakXmrArchive()
        self.tx_prefix_hash: bytes | None = None

        """
        Full message hasher/hash that is to be signed using MLSAG.
        Contains tx_prefix_hash.
        See Monero-Trezor documentation section 3.3 for more details.
        """
        self.full_message_hasher: PreMlsagHasher | None = PreMlsagHasher()
        self.full_message: bytes | None = None

    def mem_trace(self, x=None, collect: bool = False) -> None:
        import gc

        from trezor import log

        if __debug__:
            log.debug(
                __name__,
                "Log trace: %s, ... F: %s A: %s",
                x,
                gc.mem_free(),
                gc.mem_alloc(),
            )
        if collect:
            gc.collect()

    def change_address(self):
        return self.output_change.addr if self.output_change else None
