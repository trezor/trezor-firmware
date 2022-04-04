from typing import TYPE_CHECKING

from apps.monero.xmr import crypto, crypto_helpers

if TYPE_CHECKING:
    from apps.monero.xmr.credentials import AccountCreds

    Subaddresses = dict[bytes, tuple[int, int]]


class XmrException(Exception):
    pass


class XmrNoSuchAddressException(XmrException):
    pass


def get_subaddress_secret_key(
    secret_key: crypto.Scalar, major: int = 0, minor: int = 0
) -> crypto.Scalar:
    """
    Builds subaddress secret key from the subaddress index
    Hs(SubAddr || a || index_major || index_minor)
    """
    if major == 0 and minor == 0:
        return secret_key

    return crypto_helpers.get_subaddress_secret_key(secret_key, major, minor)


def get_subaddress_spend_public_key(
    view_private: crypto.Scalar, spend_public: crypto.Point, major: int, minor: int
) -> crypto.Point:
    """
    Generates subaddress spend public key D_{major, minor}
    """
    if major == 0 and minor == 0:
        return spend_public

    m = get_subaddress_secret_key(view_private, major=major, minor=minor)
    M = crypto.scalarmult_base_into(None, m)
    D = crypto.point_add_into(None, spend_public, M)
    return D


def derive_subaddress_public_key(
    out_key: crypto.Point, derivation: crypto.Point, output_index: int
) -> crypto.Point:
    """
    out_key - H_s(derivation || varint(output_index))G
    """
    crypto.ge25519_check(out_key)
    scalar = crypto_helpers.derivation_to_scalar(derivation, output_index)
    point2 = crypto.scalarmult_base_into(None, scalar)
    point4 = crypto.point_sub_into(None, out_key, point2)
    return point4


def generate_key_image(public_key: bytes, secret_key: crypto.Scalar) -> crypto.Point:
    """
    Key image: secret_key * H_p(pub_key)
    """
    point = crypto.hash_to_point_into(None, public_key)
    point2 = crypto.scalarmult_into(None, point, secret_key)
    return point2


def is_out_to_account(
    subaddresses: Subaddresses,
    out_key: crypto.Point,
    derivation: crypto.Point,
    additional_derivation: crypto.Point | None,
    output_index: int,
    creds: AccountCreds | None,
    sub_addr_major: int | None,
    sub_addr_minor: int | None,
) -> tuple[tuple[int, int], crypto.Point] | None:
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
        subaddress_spendkey = crypto_helpers.encodepoint(subaddress_spendkey_obj)
        if subaddress_spendkey in subaddresses:
            return subaddresses[subaddress_spendkey], derivation

    if additional_derivation:
        subaddress_spendkey_obj = derive_subaddress_public_key(
            out_key, additional_derivation, output_index
        )

        if sub_pub_key and crypto.point_eq(subaddress_spendkey_obj, sub_pub_key):
            # sub_pub_key is only set if sub_addr_{major, minor} are set
            assert sub_addr_major is not None and sub_addr_minor is not None
            return (sub_addr_major, sub_addr_minor), additional_derivation

        if subaddresses:
            subaddress_spendkey = crypto_helpers.encodepoint(subaddress_spendkey_obj)
            if subaddress_spendkey in subaddresses:
                return subaddresses[subaddress_spendkey], additional_derivation

    return None


def generate_tx_spend_and_key_image(
    ack: AccountCreds,
    out_key: crypto.Point,
    recv_derivation: crypto.Point,
    real_output_index: int,
    received_index: tuple[int, int],
) -> tuple[crypto.Scalar, crypto.Point]:
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
    if crypto.sc_iszero(ack.spend_key_private):
        raise ValueError("Watch-only wallet not supported")

    # derive secret key with subaddress - step 1: original CN derivation
    scalar_step1 = crypto_helpers.derive_secret_key(
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
        scalar_step2 = crypto.sc_add_into(None, scalar_step1, subaddr_sk)

    # When not in multisig, we know the full spend secret key, so the output pubkey can be obtained by scalarmultBase
    pub_ver = crypto.scalarmult_base_into(None, scalar_step2)

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

    ki = generate_key_image(crypto_helpers.encodepoint(pub_ver), scalar_step2)
    return scalar_step2, ki


def generate_tx_spend_and_key_image_and_derivation(
    creds: AccountCreds,
    subaddresses: Subaddresses,
    out_key: crypto.Point,
    tx_public_key: crypto.Point,
    additional_tx_public_key: crypto.Point | None,
    real_output_index: int | None,
    sub_addr_major: int | None,
    sub_addr_minor: int | None,
) -> tuple[crypto.Scalar, crypto.Point, crypto.Point]:
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
    recv_derivation = crypto_helpers.generate_key_derivation(
        tx_public_key, creds.view_key_private
    )

    additional_recv_derivation = (
        crypto_helpers.generate_key_derivation(
            additional_tx_public_key, creds.view_key_private
        )
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
            subaddresses[crypto_helpers.encodepoint(creds.spend_key_public)] = (0, 0)
            continue

        pub = get_subaddress_spend_public_key(
            creds.view_key_private, creds.spend_key_public, major=account, minor=idx
        )
        pub = crypto_helpers.encodepoint(pub)
        subaddresses[pub] = (account, idx)
    return subaddresses


def generate_keys(recovery_key: crypto.Scalar) -> tuple[crypto.Scalar, crypto.Point]:
    pub = crypto.scalarmult_base_into(None, recovery_key)
    return recovery_key, pub


def generate_monero_keys(
    seed: bytes,
) -> tuple[crypto.Scalar, crypto.Point, crypto.Scalar, crypto.Point]:
    """
    Generates spend key / view key from the seed in the same manner as Monero code does.

    account.cpp:
    crypto::secret_key account_base::generate(const crypto::secret_key& recovery_key, bool recover, bool two_random).
    """
    spend_sec, spend_pub = generate_keys(crypto_helpers.decodeint(seed))
    hash = crypto.fast_hash_into(None, crypto_helpers.encodeint(spend_sec))
    view_sec, view_pub = generate_keys(crypto_helpers.decodeint(hash))
    return spend_sec, spend_pub, view_sec, view_pub


def generate_sub_address_keys(
    view_sec: crypto.Scalar, spend_pub: crypto.Point, major: int, minor: int
) -> tuple[crypto.Point, crypto.Point]:
    if major == 0 and minor == 0:  # special case, Monero-defined
        return spend_pub, crypto.scalarmult_base_into(None, view_sec)

    m = get_subaddress_secret_key(view_sec, major=major, minor=minor)
    M = crypto.scalarmult_base_into(None, m)
    D = crypto.point_add_into(None, spend_pub, M)
    C = crypto.scalarmult_into(None, D, view_sec)
    return D, C


def commitment_mask(key: bytes, buff: crypto.Scalar | None = None) -> crypto.Scalar:
    """
    Generates deterministic commitment mask for Bulletproof2
    """
    data = bytearray(15 + 32)
    data[0:15] = b"commitment_mask"
    data[15:] = key
    return crypto.hash_to_scalar_into(buff, data)
