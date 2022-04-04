from typing import TYPE_CHECKING

from apps.monero.xmr import crypto, crypto_helpers, monero
from apps.monero.xmr.serialize.int_serialize import dump_uvarint_b

if TYPE_CHECKING:
    from apps.monero.xmr.credentials import AccountCreds
    from trezor.messages import MoneroTransferDetails

    Subaddresses = dict[bytes, tuple[int, int]]
    Sig = list[list[crypto.Scalar]]


def compute_hash(rr: MoneroTransferDetails) -> bytes:
    kck = crypto_helpers.get_keccak()
    kck.update(rr.out_key)
    kck.update(rr.tx_pub_key)
    if rr.additional_tx_pub_keys:
        for x in rr.additional_tx_pub_keys:
            kck.update(x)
    kck.update(dump_uvarint_b(rr.internal_output_index))
    return kck.digest()


def export_key_image(
    creds: AccountCreds, subaddresses: Subaddresses, td: MoneroTransferDetails
) -> tuple[crypto.Point, Sig]:
    out_key = crypto_helpers.decodepoint(td.out_key)
    tx_pub_key = crypto_helpers.decodepoint(td.tx_pub_key)

    additional_tx_pub_key = None
    if len(td.additional_tx_pub_keys) == 1:  # compression
        additional_tx_pub_key = crypto_helpers.decodepoint(td.additional_tx_pub_keys[0])
    elif td.additional_tx_pub_keys:
        if td.internal_output_index >= len(td.additional_tx_pub_keys):
            raise ValueError("Wrong number of additional derivations")
        additional_tx_pub_key = crypto_helpers.decodepoint(
            td.additional_tx_pub_keys[td.internal_output_index]
        )

    ki, sig = _export_key_image(
        creds,
        subaddresses,
        out_key,
        tx_pub_key,
        additional_tx_pub_key,
        td.internal_output_index,
        True,
        td.sub_addr_major,
        td.sub_addr_minor,
    )
    return ki, sig


def _export_key_image(
    creds: AccountCreds,
    subaddresses: Subaddresses,
    pkey: crypto.Point,
    tx_pub_key: crypto.Point,
    additional_tx_pub_key: crypto.Point | None,
    out_idx: int,
    test: bool = True,
    sub_addr_major: int | None = None,
    sub_addr_minor: int | None = None,
) -> tuple[crypto.Point, Sig]:
    """
    Generates key image for the TXO + signature for the key image
    """
    r = monero.generate_tx_spend_and_key_image_and_derivation(
        creds,
        subaddresses,
        pkey,
        tx_pub_key,
        additional_tx_pub_key,
        out_idx,
        sub_addr_major,
        sub_addr_minor,
    )
    xi, ki, _ = r[:3]

    phash = crypto_helpers.encodepoint(ki)
    sig = generate_ring_signature(phash, ki, [pkey], xi, 0, test)

    return ki, sig


def generate_ring_signature(
    prefix_hash: bytes,
    image: crypto.Point,
    pubs: list[crypto.Point],
    sec: crypto.Scalar,
    sec_idx: int,
    test: bool = False,
) -> Sig:
    """
    Generates ring signature with key image.
    void crypto_ops::generate_ring_signature()
    """
    from trezor.utils import memcpy

    if test:
        t = crypto.scalarmult_base_into(None, sec)
        if not crypto.point_eq(t, pubs[sec_idx]):
            raise ValueError("Invalid sec key")

        k_i = monero.generate_key_image(crypto_helpers.encodepoint(pubs[sec_idx]), sec)
        if not crypto.point_eq(k_i, image):
            raise ValueError("Key image invalid")
        for k in pubs:
            crypto.ge25519_check(k)

    buff_off = len(prefix_hash)
    buff = bytearray(buff_off + 2 * 32 * len(pubs))
    memcpy(buff, 0, prefix_hash, 0, buff_off)
    mvbuff = memoryview(buff)

    sum = crypto.Scalar(0)
    k = crypto.Scalar(0)
    sig = []

    for _ in range(len(pubs)):
        sig.append([crypto.Scalar(0), crypto.Scalar(0)])  # c, r

    for i in range(len(pubs)):
        if i == sec_idx:
            k = crypto.random_scalar()
            tmp3 = crypto.scalarmult_base_into(None, k)
            crypto.encodepoint_into(mvbuff[buff_off : buff_off + 32], tmp3)
            buff_off += 32

            tmp3 = crypto.hash_to_point_into(None, crypto_helpers.encodepoint(pubs[i]))
            tmp2 = crypto.scalarmult_into(None, tmp3, k)
            crypto.encodepoint_into(mvbuff[buff_off : buff_off + 32], tmp2)
            buff_off += 32

        else:
            sig[i] = [crypto.random_scalar(), crypto.random_scalar()]
            tmp3 = pubs[i]
            tmp2 = crypto.ge25519_double_scalarmult_vartime_into(
                None, tmp3, sig[i][0], sig[i][1]
            )
            crypto.encodepoint_into(mvbuff[buff_off : buff_off + 32], tmp2)
            buff_off += 32

            tmp3 = crypto.hash_to_point_into(None, crypto_helpers.encodepoint(tmp3))
            tmp2 = crypto.add_keys3_into(None, sig[i][1], tmp3, sig[i][0], image)
            crypto.encodepoint_into(mvbuff[buff_off : buff_off + 32], tmp2)
            buff_off += 32

            crypto.sc_add_into(sum, sum, sig[i][0])

    h = crypto.hash_to_scalar_into(None, buff)
    sig[sec_idx][0] = crypto.sc_sub_into(None, h, sum)
    sig[sec_idx][1] = crypto.sc_mulsub_into(None, sig[sec_idx][0], sec, k)
    return sig
