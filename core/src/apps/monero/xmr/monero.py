from apps.monero.xmr import crypto

if False:
    from apps.monero.xmr.types import Ge25519, Sc25519
    from apps.monero.xmr.credentials import AccountCreds

    Subaddresses = dict[bytes, tuple[int, int]]


class XmrException(Exception):
    pass


class XmrNoSuchAddressException(XmrException):
    pass


def get_subaddress_secret_key(secret_key: Sc25519, major: int = 0, minor: int = 0):
    """
    Builds subaddress secret key from the subaddress index
    Hs(SubAddr || a || index_major || index_minor)
    """
    if major == 0 and minor == 0:
        return secret_key

    return crypto.get_subaddress_secret_key(secret_key, major, minor)


def get_subaddress_spend_public_key(
    view_private: Sc25519, spend_public: Ge25519, major: int, minor: int
) -> Ge25519:
    """
    Generates subaddress spend public key D_{major, minor}
    """
    if major == 0 and minor == 0:
        return spend_public

    m = get_subaddress_secret_key(view_private, major=major, minor=minor)
    M = crypto.scalarmult_base(m)
    D = crypto.point_add(spend_public, M)
    return D


def derive_subaddress_public_key(
    out_key: Ge25519, derivation: Ge25519, output_index: int
) -> Ge25519:
    """
    out_key - H_s(derivation || varint(output_index))G
    """
    crypto.check_ed25519point(out_key)
    scalar = crypto.derivation_to_scalar(derivation, output_index)
    point2 = crypto.scalarmult_base(scalar)
    point4 = crypto.point_sub(out_key, point2)
    return point4


def generate_key_image(public_key: bytes, secret_key: Sc25519) -> Ge25519:
    """
    Key image: secret_key * H_p(pub_key)
    """
    point = crypto.hash_to_point(public_key)
    point2 = crypto.scalarmult(point, secret_key)
    return point2


def is_out_to_account(
    subaddresses: Subaddresses,
    out_key: Ge25519,
    derivation: Ge25519,
    additional_derivation: Ge25519,
    output_index: int,
    creds: AccountCreds | None = None,
    sub_addr_major: int = None,
    sub_addr_minor: int = None,
):
    """
    Checks whether the given transaction is sent to the account.
    Searches subaddresses for the computed subaddress_spendkey.
    Corresponds to is_out_to_acc_precomp() in the Monero codebase.
    If found, returns (major, minor), derivation, otherwise None.
    If (creds, sub_addr_major, sub_addr_minor) are specified,
    subaddress is checked directly (avoids the need to store
    large subaddresses dicts).
    """
    subaddress_spendkey_obj = derive_subaddress_public_key(
        out_key, derivation, output_index
    )

    sub_pub_key = None
    if creds and sub_addr_major is not None and sub_addr_minor is not None:
        sub_pub_key = get_subaddress_spend_public_key(
            creds.view_key_private,
            creds.spend_key_public,
            sub_addr_major,
            sub_addr_minor,
        )

        if crypto.point_eq(subaddress_spendkey_obj, sub_pub_key):
            return (sub_addr_major, sub_addr_minor), derivation

    if subaddresses:
        subaddress_spendkey = crypto.encodepoint(subaddress_spendkey_obj)
        if subaddress_spendkey in subaddresses:
            return subaddresses[subaddress_spendkey], derivation

    if additional_derivation:
        subaddress_spendkey_obj = derive_subaddress_public_key(
            out_key, additional_derivation, output_index
        )

        if sub_pub_key and crypto.point_eq(subaddress_spendkey_obj, sub_pub_key):
            return (sub_addr_major, sub_addr_minor), additional_derivation

        if subaddresses:
            subaddress_spendkey = crypto.encodepoint(subaddress_spendkey_obj)
            if subaddress_spendkey in subaddresses:
                return subaddresses[subaddress_spendkey], additional_derivation

    return None


def generate_tx_spend_and_key_image(
    ack: AccountCreds,
    out_key: Ge25519,
    recv_derivation: Ge25519,
    real_output_index: int,
    received_index: tuple[int, int],
) -> tuple[Sc25519, Ge25519] | None:
    """
    Generates UTXO spending key and key image.
    Corresponds to generate_key_image_helper_precomp() in the Monero codebase.

    :param ack: sender credentials
    :type ack: apps.monero.xmr.credentials.AccountCreds
    :param out_key: real output (from input RCT) destination key
    :param recv_derivation:
    :param real_output_index:
    :param received_index: subaddress index this payment was received to
    :return:
    """
    if not crypto.sc_isnonzero(ack.spend_key_private):
        raise ValueError("Watch-only wallet not supported")

    # derive secret key with subaddress - step 1: original CN derivation
    scalar_step1 = crypto.derive_secret_key(
        recv_derivation, real_output_index, ack.spend_key_private
    )

    # step 2: add Hs(SubAddr || a || index_major || index_minor)
    subaddr_sk = None
    if received_index == (0, 0):
        scalar_step2 = scalar_step1
    else:
        subaddr_sk = get_subaddress_secret_key(
            ack.view_key_private, major=received_index[0], minor=received_index[1]
        )
        scalar_step2 = crypto.sc_add(scalar_step1, subaddr_sk)

    # When not in multisig, we know the full spend secret key, so the output pubkey can be obtained by scalarmultBase
    pub_ver = crypto.scalarmult_base(scalar_step2)

    # <Multisig>, branch deactivated until implemented
    # # When in multisig, we only know the partial spend secret key. But we do know the full spend public key,
    # # so the output pubkey can be obtained by using the standard CN key derivation.
    # pub_ver = crypto.derive_public_key(
    #     recv_derivation, real_output_index, ack.spend_key_public
    # )
    #
    # # Add the contribution from the subaddress part
    # if received_index != (0, 0):
    #     subaddr_pk = crypto.scalarmult_base(subaddr_sk)
    #     pub_ver = crypto.point_add(pub_ver, subaddr_pk)
    # </Multisig>

    if not crypto.point_eq(pub_ver, out_key):
        raise ValueError(
            "key image helper precomp: given output pubkey doesn't match the derived one"
        )

    ki = generate_key_image(crypto.encodepoint(pub_ver), scalar_step2)
    return scalar_step2, ki


def generate_tx_spend_and_key_image_and_derivation(
    creds: AccountCreds,
    subaddresses: Subaddresses,
    out_key: Ge25519,
    tx_public_key: Ge25519,
    additional_tx_public_key: Ge25519,
    real_output_index: int,
    sub_addr_major: int = None,
    sub_addr_minor: int = None,
) -> tuple[Sc25519, Ge25519, Ge25519]:
    """
    Generates UTXO spending key and key image and corresponding derivation.
    Supports subaddresses.
    Corresponds to generate_key_image_helper() in the Monero codebase.

    :param creds:
    :param subaddresses:
    :param out_key: real output (from input RCT) destination key
    :param tx_public_key: R, transaction public key
    :param additional_tx_public_key: Additional Rs, for subaddress destinations
    :param real_output_index: index of the real output in the RCT
    :param sub_addr_major: subaddress major index
    :param sub_addr_minor: subaddress minor index
    :return:
    """
    recv_derivation = crypto.generate_key_derivation(
        tx_public_key, creds.view_key_private
    )

    additional_recv_derivation = (
        crypto.generate_key_derivation(additional_tx_public_key, creds.view_key_private)
        if additional_tx_public_key
        else None
    )

    subaddr_recv_info = is_out_to_account(
        subaddresses,
        out_key,
        recv_derivation,
        additional_recv_derivation,
        real_output_index,
        creds,
        sub_addr_major,
        sub_addr_minor,
    )
    if subaddr_recv_info is None:
        raise XmrNoSuchAddressException("No such addr")

    xi, ki = generate_tx_spend_and_key_image(
        creds, out_key, subaddr_recv_info[1], real_output_index, subaddr_recv_info[0]
    )
    return xi, ki, recv_derivation


def compute_subaddresses(
    creds: AccountCreds,
    account: int,
    indices: list[int],
    subaddresses: Subaddresses | None = None,
) -> Subaddresses:
    """
    Computes subaddress public spend key for receiving transactions.

    :param creds: credentials
    :param account: major index
    :param indices: array of minor indices
    :param subaddresses: subaddress dict. optional.
    :return:
    """
    if subaddresses is None:
        subaddresses = {}

    for idx in indices:
        if account == 0 and idx == 0:
            subaddresses[crypto.encodepoint(creds.spend_key_public)] = (0, 0)
            continue

        pub = get_subaddress_spend_public_key(
            creds.view_key_private, creds.spend_key_public, major=account, minor=idx
        )
        pub = crypto.encodepoint(pub)
        subaddresses[pub] = (account, idx)
    return subaddresses


def generate_keys(recovery_key: Sc25519) -> tuple[Sc25519, Ge25519]:
    pub = crypto.scalarmult_base(recovery_key)
    return recovery_key, pub


def generate_monero_keys(seed: bytes) -> tuple[Sc25519, Ge25519, Sc25519, Ge25519]:
    """
    Generates spend key / view key from the seed in the same manner as Monero code does.

    account.cpp:
    crypto::secret_key account_base::generate(const crypto::secret_key& recovery_key, bool recover, bool two_random).
    """
    spend_sec, spend_pub = generate_keys(crypto.decodeint(seed))
    hash = crypto.cn_fast_hash(crypto.encodeint(spend_sec))
    view_sec, view_pub = generate_keys(crypto.decodeint(hash))
    return spend_sec, spend_pub, view_sec, view_pub


def generate_sub_address_keys(
    view_sec: Sc25519, spend_pub: Ge25519, major: int, minor: int
) -> tuple[Ge25519, Ge25519]:
    if major == 0 and minor == 0:  # special case, Monero-defined
        return spend_pub, crypto.scalarmult_base(view_sec)

    m = get_subaddress_secret_key(view_sec, major=major, minor=minor)
    M = crypto.scalarmult_base(m)
    D = crypto.point_add(spend_pub, M)
    C = crypto.scalarmult(D, view_sec)
    return D, C


def commitment_mask(key: bytes, buff: Sc25519 | None = None) -> Sc25519:
    """
    Generates deterministic commitment mask for Bulletproof2
    """
    data = bytearray(15 + 32)
    data[0:15] = b"commitment_mask"
    data[15:] = key
    if buff:
        return crypto.hash_to_scalar_into(buff, data)
    else:
        return crypto.hash_to_scalar(data)
