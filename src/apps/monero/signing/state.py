import gc
from micropython import const

from trezor import log

from apps.monero.xmr import crypto


class TprefixStub:
    __slots__ = ("version", "unlock_time", "vin", "vout", "extra")

    def __init__(self, **kwargs):
        for kw in kwargs:
            setattr(self, kw, kwargs[kw])


class State:

    STEP_INP = const(100)
    STEP_PERM = const(200)
    STEP_VINI = const(300)
    STEP_ALL_IN = const(350)
    STEP_OUT = const(400)
    STEP_ALL_OUT = const(500)
    STEP_SIGN = const(600)

    def __init__(self, ctx):
        from apps.monero.xmr.keccak_hasher import KeccakXmrArchive
        from apps.monero.xmr.mlsag_hasher import PreMlsagHasher

        self.ctx = ctx

        """
        Account credentials
        type: AccountCreds
        - view private/public key
        - spend private/public key
        - and its corresponding address
        """
        self.creds = None

        # HMAC/encryption keys used to protect offloaded data
        self.key_hmac = None
        self.key_enc = None

        """
        Transaction keys
        - also denoted as r/R
        - tx_priv is a random number
        - tx_pub is equal to `r*G` or `r*D` for subaddresses
        - for subaddresses the `r` is commonly denoted as `s`, however it is still just a random number
        - the keys are used to derive the one time address and its keys (P = H(A*r)*G + B)
        """
        self.tx_priv = None
        self.tx_pub = None

        """
        In some cases when subaddresses are used we need more tx_keys
        (explained in step 1).
        """
        self.need_additional_txkeys = False

        # Ring Confidential Transaction type
        # allowed values: RctType.{Full, Simple}
        self.rct_type = None
        # Range Signature type (also called range proof)
        # allowed values: RsigType.{Borromean, Bulletproof}
        self.rsig_type = None

        self.input_count = 0
        self.output_count = 0
        self.output_change = None
        self.fee = 0

        # wallet sub-address major index
        self.account_idx = 0

        # contains additional tx keys if need_additional_tx_keys is True
        self.additional_tx_private_keys = []
        self.additional_tx_public_keys = []

        # currently processed input/output index
        self.current_input_index = -1
        self.current_output_index = -1

        self.summary_inputs_money = 0
        self.summary_outs_money = 0

        # output commitments
        self.output_pk_commitments = []
        # masks used in the output commitment
        self.output_sk_masks = []

        self.output_amounts = []
        # output *range proof* masks
        self.output_masks = []

        # the range proofs are calculated in batches, this denotes the grouping
        self.rsig_grouping = []
        # is range proof computing offloaded or not
        self.rsig_offload = False

        # sum of all inputs' pseudo out masks
        self.sumpouts_alphas = crypto.sc_0()
        # sum of all output' pseudo out masks
        self.sumout = crypto.sc_0()

        self.subaddresses = {}

        # simple stub containing items hashed into tx prefix
        self.tx = TprefixStub(vin=[], vout=[], extra=b"")

        # contains an array where each item denotes the input's position
        # (inputs are sorted by key images)
        self.source_permutation = []

        """
        Tx prefix hasher/hash. We use the hasher to incrementally hash and then
        store the final hash in tx_prefix_hash.
        See Monero-Trezor documentation section 3.3 for more details.
        """
        self.tx_prefix_hasher = KeccakXmrArchive()
        self.tx_prefix_hash = None

        """
        Full message hasher/hash that is to be signed using MLSAG.
        Contains tx_prefix_hash.
        See Monero-Trezor documentation section 3.3 for more details.
        """
        self.full_message_hasher = PreMlsagHasher()
        self.full_message = None

    def mem_trace(self, x=None, collect=False):
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
