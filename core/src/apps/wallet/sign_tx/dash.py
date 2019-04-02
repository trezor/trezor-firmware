from ustruct import unpack
from ubinascii import unhexlify
from trezor import ui
from trezor.messages import ButtonRequestType
from trezor.ui.text import Text
from trezor.utils import obj_eq
from trezor.wire import ProcessError
from trezor.crypto.base58 import encode_check
from trezor.crypto.curve import secp256k1
from trezor.crypto.hashlib import ripemd160, sha256
from apps.common.signverify import message_digest
from trezor.messages.TxRequest import TxRequest
from trezor.messages.TxRequestDetailsType import TxRequestDetailsType
from apps.common import coininfo, coins

from apps.common.confirm import (
    require_confirm,
    require_hold_to_confirm,
    confirm,
)
from apps.wallet.sign_tx import (
    helpers,
    addresses
)


VAR_INT_MAX_SIZE = 8
_DASH_COIN = 100000000
_BLS_SIGNATURE_SIZE = 96


def _dip2_tx_type(tx):
    return tx.version >> 16


def _is_testnet(tx):
    return "test" in tx.coin_name.lower()


def _varint_size(data: bytes):
    size = 1
    nit = unpack("<B", data[0:1])[0]
    if nit == 253:
        size += 2
    elif nit == 254:
        size += 4
    elif nit == 255:
        size += 8
    return size


def _unpack_varint(data: bytes):
    nit = unpack("<B", data[0:1])[0]
    if nit == 253:
        nit = unpack("<H", data[1:3])[0]
    elif nit == 254:
        nit = unpack("<I", data[1:5])[0]
    elif nit == 255:
        nit = unpack("<Q", data[1:9])[0]
    return nit


def _to_hex(data: bytes) -> str:
    return "".join('{:02x}'.format(x) for x in data)


def _inet_ntoa(data: bytes) -> str:
    # this is IPv4 mapped IPv6 address,  can get only 4 last bytes
    return ".".join('{}'.format(data[i]) for i in [12, 13, 14, 15])


def _is_p2pkh_script(data: bytes) -> bool:
    if not len(data) == 25:
        return False
    if not data[0] == 0x76:
        return False
    if not data[1] == 0xa9:
        return False
    if not data[2] == 0x14:
        return False
    if not data[-1] == 0xac:
        return False
    if not data[-2] == 0x88:
        return False
    return True


def _is_p2sh_script(data: bytes) -> bool:
    if not len(data) == 23:
        return False
    if not data[0] == 0xa9:
        return False
    if not data[1] == 0x14:
        return False
    if not data[-1] == 0x88:
        return False
    return True


def _address_from_script(data: bytes, coin: coininfo.CoinInfo) -> str:
    if _is_p2pkh_script(data):
        return addresses.address_pkh_from_keyid(data[3:23], coin)
    if _is_p2sh_script(data):
        return addresses.address_p2sh(data[2:22], coin)
    raise ProcessError("Unsupported payout script type")


async def _addr_from_txout(tx_id: str, tx_out: int, coin: coininfo.CoinInfo) -> str:
    tx_req = TxRequest()
    tx_req.details = TxRequestDetailsType()
    txo = await helpers.request_tx_output(tx_req, tx_out, unhexlify(tx_id))
    return _address_from_script(txo.script_pubkey, coin)


async def _verify_collateral_out(tx_id: str, tx_out: int) -> bool:
    tx_req = TxRequest()
    tx_req.details = TxRequestDetailsType()
    txo = await helpers.request_tx_output(tx_req, tx_out, unhexlify(tx_id))
    return txo.amount == 1000 * _DASH_COIN


# masternode registration revoke reason for user confirmation
def _revoke_reason(idx: int) -> str:
    if idx == 0:
        return "Not Specified"
    elif idx == 1:
        return "Termination of Service"
    elif idx == 2:
        return "Compromised Keys"
    elif idx == 3:
        return "Change of Keys (Not compromised)"
    # no error here, this reason is used only for information
    return "Unknown revoke reason ({})".format(idx)


class UIConfirmTxDetail:
    def __init__(self, title: str, data:str):
        self.title = title
        self.data = data

    __eq__ = obj_eq


# This class is used to parse specific transaction details
class SpecialTx:
    def __init__(self, data: bytes, dip2_type, testnet: bool, coin: coininfo, inputs_hash: bytes):
        self.coin = coin
        self.payload = data
        self.position = 0
        # check payload size
        varint_size = _varint_size(data)
        payload_size = _unpack_varint(data[self.position:self.position + varint_size])
        if len(data) != varint_size + payload_size:
            raise ProcessError("Invalid Dash DIP2 extra payload size")
        self.position += varint_size
        self.payload_content_start = self.position
        self.type = dip2_type
        self.testnet = testnet
        self.inputs_hash = inputs_hash
        self.confirmations = []

    def tx_name(self):
        if self.type == 1:
            return 'Provider Registration Transaction'
        elif self.type == 2:
            return 'Provider Update Service Transaction'
        elif self.type == 3:
            return 'Provider Update Registrar Transaction'
        elif self.type == 4:
            return 'Provider Update Revocation Transaction'
        elif self.type == 5:
            return 'Coinbase Transaction'
        elif self.type == 6:
            return 'Quorum Commitment'
        elif self.type == 8:
            return 'Register Subscription Transaction'
        elif self.type == 9:
            return 'Topup BU Credit Subscription Transaction'
        elif self.type == 10:
            return 'Reset BU Key Subscription Transaction'
        elif self.type == 11:
            return 'Close BU Account Subscription Transaction'
        raise ProcessError("Unknown Dash DIP2 transaction type")

    async def parse(self):
        if self.type == 1:
            await self._parse_pro_reg_tx(self.payload, self.position)
        elif self.type == 2:
            await self._parse_pro_up_serv_tx(self.payload, self.position)
        elif self.type == 3:
            await self._parse_pro_up_reg_tx(self.payload, self.position)
        elif self.type == 4:
            await self._parse_pro_up_rev_tx(self.payload, self.position)
        elif self.type == 5:
            self._parse_cb_tx(self.payload, self.position)
        elif self.type == 6:
            self._parse_qm_tx(self.payload, self.position)
        elif self.type == 8:
            self._parse_bu_reg_tx(self.payload, self.position)
        elif self.type == 9:
            self._parse_bu_credit_tx(self.payload, self.position)
        elif self.type == 10:
            self._parse_bu_reset_tx(self.payload, self.position)
        elif self.type == 11:
            self._parse_bu_close_tx(self.payload, self.position)
        else:
            raise ProcessError("Unknown Dash DIP2 transaction type")

    async def _parse_pro_reg_tx(self, data, position):
        version = unpack("<H", data[position:position + 2])[0]
        if not version == 1:
            raise ProcessError("Unknown Dash Provider Register format version")
        position += 2
        mntype = unpack("<H", data[position:position + 2])[0]
        position += 2
        mode = unpack("<H", data[position:position + 2])[0]
        position += 2
        self.confirmations.extend([("Masternode type",
                                    "Type: {}, mode: {}".format(mntype, mode))])
        collateral_id = _to_hex(reversed(data[position:position + 32]))
        position += 32
        collateral_out = unpack('<I', data[position:position + 4])[0]
        position += 4
        empty_collateral = all(c == "0" for c in collateral_id)
        if empty_collateral:
            self.confirmations.extend([("External collateral", "Empty")])
        else:
            tx_req = TxRequest()
            tx_req.details = TxRequestDetailsType()
            collateral_txo = await helpers.request_tx_output(tx_req, collateral_out, unhexlify(collateral_id))
            if collateral_txo.amount != 1000 * _DASH_COIN:
                raise ProcessError("Invalid external collateral")
            self.confirmations.extend([("External collateral",
                                        "{}:{}".format(collateral_id, collateral_out))])
        ip = _inet_ntoa(data[position:position+16])
        position += 16
        port = unpack(">H", data[position:position+2])[0]
        position += 2
        self.confirmations.extend([("Address and port",
                                    "{}:{}".format(ip, port))])
        owner_address = addresses.address_pkh_from_keyid(data[position:position + 20], self.coin)
        position += 20
        self.confirmations.extend([("Owner address", owner_address)])
        self.confirmations.extend([("Operator Public Key",
                                    _to_hex(data[position:position + 48]))])
        position += 48
        voting_address = addresses.address_pkh_from_keyid(data[position:position + 20], self.coin)
        position += 20
        self.confirmations.extend([("Voting address", voting_address)])
        operator_reward = unpack("<H", data[position:position+2])[0]
        if operator_reward > 10000:
            raise ProcessError("Invalid operator reward in ProRegTx")
        position += 2
        self.confirmations.extend([("Operator reward",
                                    "{:.2f}%".format(operator_reward / 100.0))])
        varint_size = _varint_size(data[position:position + 8])
        payout_script_size = _unpack_varint(data[position:position + varint_size])
        position += varint_size
        payout_address = _address_from_script(data[position:position + payout_script_size], self.coin)
        position += payout_script_size
        self.confirmations.extend([("Payout address", payout_address)])
        if data[position:position + 32] != self.inputs_hash:
            raise ProcessError("Invalid inputs hash in DIP2 transaction")
        position += 32
        payload_content_end = position
        varint_size = _varint_size(data[position:position + 8])
        payload_sig_size = _unpack_varint(data[position:position + varint_size])
        position += varint_size
        if position + payload_sig_size != len(data):
            raise ProcessError("Invalid payload signature size")
        if empty_collateral and payload_sig_size > 0:
            raise ProcessError("Empty collateral and not empty payload signature")
        if not empty_collateral and payload_sig_size == 0:
            raise ProcessError("No payload signature for external collateral")
        if payload_sig_size > 0:
            payload_sig = data[position:position + payload_sig_size]
            res = payout_address + "|" + str(operator_reward) + "|" + \
                  owner_address + "|" + voting_address + "|"
            data_hash = bytes(reversed(sha256(sha256(data[self.payload_content_start:payload_content_end]).digest()).digest()))
            res += _to_hex(data_hash)
            digest = message_digest(self.coin, res)
            key_from_sig = secp256k1.verify_recover(payload_sig, digest)
            if not key_from_sig:
                raise ProcessError("Invalid payload signature")
            address_from_sig = addresses.address_pkh(key_from_sig, self.coin)
            address_from_txout = _address_from_script(collateral_txo.script_pubkey, self.coin)
            if address_from_sig != address_from_txout:
                raise ProcessError("Invalid payload signature")

    async def _parse_pro_up_serv_tx(self, data, position):
        version = unpack("<H", data[position:position + 2])[0]
        if not version == 1:
            raise ProcessError("Unknown Dash Provider Update Service format version")
        position += 2
        initial_proregtx_id = bytes(reversed(data[position:position + 32]))
        position += 32
        tx_req = TxRequest()
        tx_req.details = TxRequestDetailsType()
        proregtx = await helpers.request_tx_meta(tx_req, initial_proregtx_id)
        if proregtx.version != ((1 << 16) | 3):
            raise ProcessError("Invalid ProRegTx")
        self.confirmations.extend([("Initial ProRegTx", _to_hex(initial_proregtx_id))])
        ip = _inet_ntoa(data[position:position+16])
        position += 16
        port = unpack(">H", data[position:position+2])[0]
        position += 2
        self.confirmations.extend([("Address and port",
                                    "{}:{}".format(ip, port))])
        varint_size = _varint_size(data[position:position + 8])
        payout_script_size = _unpack_varint(data[position:position + varint_size])
        position += varint_size
        if payout_script_size == 0:
            payout_address = "Empty"
        else:
            payout_address = _address_from_script(data[position:position + payout_script_size], self.coin)
        position += payout_script_size
        self.confirmations.extend([("Payout address", payout_address)])
        if data[position:position + 32] != self.inputs_hash:
            raise ProcessError("Invalid inputs hash in DIP2 transaction")
        position += 32
        if position + _BLS_SIGNATURE_SIZE != len(data):
            raise ProcessError("Invalid payload BLS signature size")

    async def _parse_pro_up_reg_tx(self, data, position):
        version = unpack("<H", data[position:position + 2])[0]
        if not version == 1:
            raise ProcessError("Unknown Dash Provider Update Registrar format version")
        position += 2
        initial_proregtx_id = bytes(reversed(data[position:position + 32]))
        position += 32
        tx_req = TxRequest()
        tx_req.details = TxRequestDetailsType()
        proregtx = await helpers.request_tx_meta(tx_req, initial_proregtx_id)
        if proregtx.version != ((1 << 16) | 3):
            raise ProcessError("Invalid ProRegTx")
        self.confirmations.extend([("Initial ProRegTx", _to_hex(initial_proregtx_id))])
        mode = unpack("<H", data[position:position + 2])[0]
        position += 2
        self.confirmations.extend([("Masternode mode",
                                    "Mode: {}".format(mode))])
        self.confirmations.extend([("Operator Public Key",
                                    _to_hex(data[position:position + 48]))])
        position += 48
        voting_address = addresses.address_pkh_from_keyid(data[position:position + 20], self.coin)
        position += 20
        self.confirmations.extend([("Voting address", voting_address)])
        varint_size = _varint_size(data[position:position + 8])
        payout_script_size = _unpack_varint(data[position:position + varint_size])
        position += varint_size
        if payout_script_size == 0:
            payout_address = "Empty"
        else:
            payout_address = _address_from_script(data[position:position + payout_script_size], self.coin)
        position += payout_script_size
        self.confirmations.extend([("Payout address", payout_address)])
        if data[position:position + 32] != self.inputs_hash:
            raise ProcessError("Invalid inputs hash in DIP2 transaction")
        position += 32
        payload_content_end = position
        varint_size = _varint_size(data[position:position + 8])
        payload_sig_size = _unpack_varint(data[position:position + varint_size])
        position += varint_size
        if position + payload_sig_size != len(data):
            raise ProcessError("Invalid payload signature size")
        if payload_sig_size == 0:
            raise ProcessError("Invalid payload signature size")
        payload_sig = data[position:position + payload_sig_size]
        data_hash = sha256(sha256(data[self.payload_content_start:payload_content_end]).digest()).digest()
        key_from_sig = secp256k1.verify_recover(payload_sig, data_hash)
        if not key_from_sig:
            raise ProcessError("Invalid payload signature")
        keyid_from_sig = self.coin.script_hash(key_from_sig)
        tx_req = TxRequest()
        tx_req.details = TxRequestDetailsType()
        ofs = 0
        proregtx_payload = bytes()
        while ofs < proregtx.extra_data_len:
            size = min(1024, proregtx.extra_data_len - ofs)
            chunk = await helpers.request_tx_extra_data(tx_req, ofs, size, initial_proregtx_id)
            proregtx_payload += chunk
            ofs += len(chunk)
        ownerkeyid_position = _varint_size(proregtx_payload) + 60
        owner_keyid = proregtx_payload[ownerkeyid_position:ownerkeyid_position + 20]
        if keyid_from_sig != owner_keyid:
            raise ProcessError("Payload signature doesn't match Owner key")

    async def _parse_pro_up_rev_tx(self, data, position):
        version = unpack("<H", data[position:position + 2])[0]
        if not version == 1:
            raise ProcessError("Unknown Dash Provider Update Registrar format version")
        position += 2
        initial_proregtx_id = bytes(reversed(data[position:position + 32]))
        position += 32
        tx_req = TxRequest()
        tx_req.details = TxRequestDetailsType()
        proregtx = await helpers.request_tx_meta(tx_req, initial_proregtx_id)
        if proregtx.version != ((1 << 16) | 3):
            raise ProcessError("Invalid ProRegTx")
        self.confirmations.extend([("Initial ProRegTx", _to_hex(initial_proregtx_id))])
        reason = unpack("<H", data[position:position + 2])[0]
        position += 2
        self.confirmations.extend([("Revoke reason", _revoke_reason(reason))])
        if data[position:position + 32] != self.inputs_hash:
            raise ProcessError("Invalid inputs hash in DIP2 transaction")
        position += 32
        if position + _BLS_SIGNATURE_SIZE != len(data):
            raise ProcessError("Invalid payload BLS signature size")

    def _parse_cb_tx(self, data, position):
        raise ProcessError("Unsupported Dash DIP3 transaction type")

    def _parse_qm_tx(self, data, position):
        raise ProcessError("Unsupported Dash DIP3 transaction type")

    def _parse_bu_reg_tx(self, data, position):
        raise ProcessError("Unsupported Dash DIP3 transaction type")

    def _parse_bu_credit_tx(self, data, position):
        raise ProcessError("Unsupported Dash DIP3 transaction type")

    def _parse_bu_reset_tx(self, data, position):
        raise ProcessError("Unsupported Dash DIP3 transaction type")

    def _parse_bu_close_tx(self, data, position):
        raise ProcessError("Unsupported Dash DIP3 transaction type")


async def confirm_tx_detail(ctx, title, data):
    text = Text(title, ui.ICON_SEND, icon_color=ui.GREEN)
    text.bold(data)
    return await require_confirm(ctx, text, ButtonRequestType.SignTx)


# Used to check if this transaction requires special processing
def is_dip2_tx(tx):
    if not tx.coin_name.lower().startswith("dash"):
        return False
    version = tx.version
    dip2_type = version >> 16
    version &= 0xffff
    return (version is 3) and (dip2_type > 0)


async def request_dip2_extra_payload(tx_req):
    # if it is Dash Special Tx it has at least 8 (max varint size) bytes
    # extra data, so we can request it
    size = VAR_INT_MAX_SIZE
    ofs = 0
    data = await helpers.request_tx_extra_data(tx_req, ofs, size)
    # calc full extra data size
    extra_len = _varint_size(data) + _unpack_varint(data)
    # request remaining extra data
    ofs = VAR_INT_MAX_SIZE
    data_to_confirm = bytearray(data)
    while ofs < extra_len:
        size = min(1024, extra_len - ofs)
        data = await helpers.request_tx_extra_data(tx_req, ofs, size)
        data_to_confirm.extend(data)
        ofs += len(data)
    return data_to_confirm


# Used to explicitly verify or to confirm by user all specific transaction details
async def confirm_dip2_tx_payload(data, tx, inputs_hash):
    dip2_type = _dip2_tx_type(tx)
    testnet = _is_testnet(tx)
    tx = SpecialTx(data, dip2_type, testnet, coins.by_name(tx.coin_name), inputs_hash)
    await tx.parse()
    yield UIConfirmTxDetail("Confirm this is", tx.tx_name())
    for c in tx.confirmations:
        yield UIConfirmTxDetail(c[0], c[1])
