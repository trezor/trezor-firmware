from apps.wallet.sign_tx.writers import *


# TX Scripts
# ===

# -------------------------- First gen --------------------------

# =============== P2PK ===============
# obsolete


# =============== P2PKH ===============

def input_script_p2pkh_or_p2sh(pubkey: bytes, signature: bytes) -> bytearray:
    w = bytearray_with_cap(5 + len(signature) + 1 + 5 + len(pubkey))
    append_signature_and_pubkey(w, pubkey, signature)
    return w


def output_script_p2pkh(pubkeyhash: bytes) -> bytearray:
    s = bytearray(25)
    s[0] = 0x76  # OP_DUP
    s[1] = 0xA9  # OP_HASH_160
    s[2] = 0x14  # pushing 20 bytes
    s[3:23] = pubkeyhash
    s[23] = 0x88  # OP_EQUALVERIFY
    s[24] = 0xAC  # OP_CHECKSIG
    return s


# =============== P2SH ===============
# see https://github.com/bitcoin/bips/blob/master/bip-0016.mediawiki

# input script (scriptSig) is the same as input_script_p2pkh_or_p2sh

# output script (scriptPubKey) is A9 14 <scripthash> 87
def output_script_p2sh(scripthash: bytes) -> bytearray:
    s = bytearray(23)
    s[0] = 0xA9  # OP_HASH_160
    s[1] = 0x14  # pushing 20 bytes
    s[2:22] = scripthash
    s[22] = 0x87  # OP_EQUAL
    return s


# -------------------------- SegWit --------------------------

# =============== Native P2WPKH ===============
# see https://github.com/bitcoin/bips/blob/master/bip-0141.mediawiki#p2wpkh
# P2WPKH (Pay-to-Witness-Public-Key-Hash) is the segwit native P2PKH
# not backwards compatible

# input script is completely replaced by the witness and therefore empty
def input_script_native_p2wpkh_or_p2wsh() -> bytearray:
    return bytearray(0)


# output script consists of 00 14 <20-byte-key-hash>
def output_script_native_p2wpkh_or_p2wsh(pubkeyhash: bytes) -> bytearray:
    w = bytearray_with_cap(3 + len(pubkeyhash))
    w.append(0x00)  # witness version byte
    w.append(len(pubkeyhash))  # pub key hash length is 20 (P2WPKH) or 32 (P2WSH) bytes
    write_bytes(w, pubkeyhash)  # pub key hash
    return w


# =============== Native P2WPKH nested in P2SH ===============
# P2WPKH is nested in P2SH to be backwards compatible
# see https://github.com/bitcoin/bips/blob/master/bip-0141.mediawiki#witness-program

# input script (scriptSig) is 16 00 14 <pubkeyhash>
# signature is moved to the witness
def input_script_p2wpkh_in_p2sh(pubkeyhash: bytes) -> bytearray:
    w = bytearray_with_cap(3 + len(pubkeyhash))
    w.append(0x16)  # 0x16 - length of the redeemScript
    w.append(0x00)  # witness version byte
    w.append(0x14)  # P2WPKH witness program (pub key hash length)
    write_bytes(w, pubkeyhash)  # pub key hash
    return w

# output script (scriptPubKey) is A9 14 <scripthash> 87
# which is same as the output_script_p2sh


# =============== Native P2WSH ===============
# see https://github.com/bitcoin/bips/blob/master/bip-0141.mediawiki#p2wsh
# P2WSH (Pay-to-Witness-Script-Hash) is segwit native P2SH
# not backwards compatible

# input script is completely replaced by the witness and therefore empty
# same as input_script_native_p2wpkh_or_p2wsh

# output script consists of 00 20 <32-byte-key-hash>
# same as output_script_native_p2wpkh_or_p2wsh (only different length)


# -------------------------- Others --------------------------

# === OP_RETURN script

def output_script_paytoopreturn(data: bytes) -> bytearray:
    w = bytearray_with_cap(1 + 5 + len(data))
    w.append(0x6A)  # OP_RETURN
    write_op_push(w, len(data))
    w.extend(data)
    return w


# === helpers

def append_signature_and_pubkey(w: bytearray, pubkey: bytes, signature: bytes) -> bytearray:
    write_op_push(w, len(signature) + 1)
    write_bytes(w, signature)
    w.append(0x01)  # SIGHASH_ALL
    write_op_push(w, len(pubkey))
    write_bytes(w, pubkey)
    return w
