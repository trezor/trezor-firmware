from apps.monero.xmr import crypto, monero
from apps.monero.xmr.serialize.int_serialize import dump_uvarint_b


def compute_hash(rr):
    kck = crypto.get_keccak()
    kck.update(rr.out_key)
    kck.update(rr.tx_pub_key)
    if rr.additional_tx_pub_keys:
        for x in rr.additional_tx_pub_keys:
            kck.update(x)
    kck.update(dump_uvarint_b(rr.internal_output_index))
    return kck.digest()


def export_key_image(creds, subaddresses, td):
    out_key = crypto.decodepoint(td.out_key)
    tx_pub_key = crypto.decodepoint(td.tx_pub_key)
    additional_tx_pub_keys = [crypto.decodepoint(x) for x in td.additional_tx_pub_keys]
    ki, sig = _export_key_image(
        creds,
        subaddresses,
        out_key,
        tx_pub_key,
        additional_tx_pub_keys,
        td.internal_output_index,
    )
    return ki, sig


def _export_key_image(
    creds, subaddresses, pkey, tx_pub_key, additional_tx_pub_keys, out_idx, test=True
):
    """
    Generates key image for the TXO + signature for the key image
    """
    r = monero.generate_tx_spend_and_key_image_and_derivation(
        creds, subaddresses, pkey, tx_pub_key, additional_tx_pub_keys, out_idx
    )
    xi, ki, recv_derivation = r[:3]

    phash = crypto.encodepoint(ki)
    sig = generate_ring_signature(phash, ki, [pkey], xi, 0, test)

    return ki, sig


def generate_ring_signature(prefix_hash, image, pubs, sec, sec_idx, test=False):
    """
    Generates ring signature with key image.
    void crypto_ops::generate_ring_signature()
    """
    from trezor.utils import memcpy

    if test:
        t = crypto.scalarmult_base(sec)
        if not crypto.point_eq(t, pubs[sec_idx]):
            raise ValueError("Invalid sec key")

        k_i = monero.generate_key_image(crypto.encodepoint(pubs[sec_idx]), sec)
        if not crypto.point_eq(k_i, image):
            raise ValueError("Key image invalid")
        for k in pubs:
            crypto.check_ed25519point(k)

    buff_off = len(prefix_hash)
    buff = bytearray(buff_off + 2 * 32 * len(pubs))
    memcpy(buff, 0, prefix_hash, 0, buff_off)
    mvbuff = memoryview(buff)

    sum = crypto.sc_0()
    k = crypto.sc_0()
    sig = []

    for i in range(len(pubs)):
        sig.append([crypto.sc_0(), crypto.sc_0()])  # c, r

    for i in range(len(pubs)):
        if i == sec_idx:
            k = crypto.random_scalar()
            tmp3 = crypto.scalarmult_base(k)
            crypto.encodepoint_into(mvbuff[buff_off : buff_off + 32], tmp3)
            buff_off += 32

            tmp3 = crypto.hash_to_point(crypto.encodepoint(pubs[i]))
            tmp2 = crypto.scalarmult(tmp3, k)
            crypto.encodepoint_into(mvbuff[buff_off : buff_off + 32], tmp2)
            buff_off += 32

        else:
            sig[i] = [crypto.random_scalar(), crypto.random_scalar()]
            tmp3 = pubs[i]
            tmp2 = crypto.ge25519_double_scalarmult_base_vartime(
                sig[i][0], tmp3, sig[i][1]
            )
            crypto.encodepoint_into(mvbuff[buff_off : buff_off + 32], tmp2)
            buff_off += 32

            tmp3 = crypto.hash_to_point(crypto.encodepoint(tmp3))
            tmp2 = crypto.ge25519_double_scalarmult_vartime2(
                sig[i][1], tmp3, sig[i][0], image
            )
            crypto.encodepoint_into(mvbuff[buff_off : buff_off + 32], tmp2)
            buff_off += 32

            sum = crypto.sc_add(sum, sig[i][0])

    h = crypto.hash_to_scalar(buff)
    sig[sec_idx][0] = crypto.sc_sub(h, sum)
    sig[sec_idx][1] = crypto.sc_mulsub(sig[sec_idx][0], sec, k)
    return sig
