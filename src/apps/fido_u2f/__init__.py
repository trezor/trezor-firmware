import uctypes
import ustruct

from trezor import log
from trezor import loop
from trezor import msg
from trezor import utils
from trezor.crypto import der
from trezor.crypto import hashlib
from trezor.crypto import hmac
from trezor.crypto import random
from trezor.crypto.curve import nist256p1

_HID_RPT_SIZE = const(64)
_CID_BROADCAST = const(0xffffffff)  # broadcast channel id

# types of frame
_TYPE_MASK = const(0x80)  # frame type mask
_TYPE_INIT = const(0x80)  # initial frame identifier
_TYPE_CONT = const(0x00)  # continuation frame identifier

# types of cmd
_CMD_PING = const(0x81)   # echo data through local processor only
_CMD_MSG = const(0x83)    # send U2F message frame
_CMD_LOCK = const(0x84)   # send lock channel command
_CMD_INIT = const(0x86)   # channel initialization
_CMD_WINK = const(0x88)   # send device identification wink
_CMD_ERROR = const(0xbf)  # error response

# types for the msg cmd
_MSG_REGISTER = const(0x01)      # registration command
_MSG_AUTHENTICATE = const(0x02)  # authenticate/sign command
_MSG_VERSION = const(0x03)       # read version string command

# hid error codes
_ERR_NONE = const(0x00)  # no error
_ERR_INVALID_CMD = const(0x01)  # invalid command
_ERR_INVALID_PAR = const(0x02)  # invalid parameter
_ERR_INVALID_LEN = const(0x03)  # invalid message length
_ERR_INVALID_SEQ = const(0x04)  # invalid message sequencing
_ERR_MSG_TIMEOUT = const(0x05)  # message has timed out
_ERR_CHANNEL_BUSY = const(0x06)  # channel busy
_ERR_LOCK_REQUIRED = const(0x0a)  # command requires channel lock
_ERR_INVALID_CID = const(0x0b)  # command not allowed on this cid
_ERR_OTHER = const(0x7f)  # other unspecified error

# command status responses
_SW_NO_ERROR = const(0x9000)
_SW_WRONG_LENGTH = const(0x6700)
_SW_DATA_INVALID = const(0x6984)
_SW_CONDITIONS_NOT_SATISFIED = const(0x6985)
_SW_WRONG_DATA = const(0x6a80)
_SW_INS_NOT_SUPPORTED = const(0x6d00)
_SW_CLA_NOT_SUPPORTED = const(0x6e00)

# init response
_CAPFLAG_WINK = const(0x01)     # device supports _CMD_WINK
_U2FHID_IF_VERSION = const(2)   # interface version

# register response
_U2F_KEY_PATH = const(0x80553246)
_U2F_REGISTER_ID = const(0x05)  # version 2 registration identifier
_U2F_ATT_PRIV_KEY = b"q&\xac+\xf6D\xdca\x86\xad\x83\xef\x1f\xcd\xf1*W\xb5\xcf\xa2\x00\x0b\x8a\xd0'\xe9V\xe8T\xc5\n\x8b"
_U2F_ATT_CERT = b"0\x82\x01\x180\x81\xc0\x02\t\x00\xb1\xd9\x8fBdr\xd3,0\n\x06\x08*\x86H\xce=\x04\x03\x020\x151\x130\x11\x06\x03U\x04\x03\x0c\nTrezor U2F0\x1e\x17\r160429133153Z\x17\r260427133153Z0\x151\x130\x11\x06\x03U\x04\x03\x0c\nTrezor U2F0Y0\x13\x06\x07*\x86H\xce=\x02\x01\x06\x08*\x86H\xce=\x03\x01\x07\x03B\x00\x04\xd9\x18\xbd\xfa\x8aT\xac\x92\xe9\r\xa9\x1f\xcaz\xa2dT\xc0\xd1s61M\xde\x83\xa5K\x86\xb5\xdfN\xf0Re\x9a\x1do\xfc\xb7F\x7f\x1a\xcd\xdb\x8a3\x08\x0b^\xed\x91\x89\x13\xf4C\xa5&\x1b\xc7{h`o\xc10\n\x06\x08*\x86H\xce=\x04\x03\x02\x03G\x000D\x02 $\x1e\x81\xff\xd2\xe5\xe6\x156\x94\xc3U.\x8f\xeb\xd7\x1e\x895\x92\x1c\xb4\x83ACq\x1cv\xea\xee\xf3\x95\x02 _\x80\xeb\x10\xf2\\\xcc9\x8b<\xa8\xa9\xad\xa4\x02\x7f\x93\x13 w\xb7\xab\xcewFZ'\xf5=3\xa1\x1d"

# common raw message format (ISO7816-4:2005 mapping)
_APDU_CLA = const(0)  # uint8_t cla;        // Class - reserved
_APDU_INS = const(1)  # uint8_t ins;        // U2F instruction
_APDU_P1 = const(2)   # uint8_t p1;         // U2F parameter 1
_APDU_P2 = const(3)   # uint8_t p2;         // U2F parameter 2
_APDU_LC1 = const(4)  # uint8_t lc1;        // Length field, set to zero
_APDU_LC2 = const(5)  # uint8_t lc2;        // Length field, MSB
_APDU_LC3 = const(6)  # uint8_t lc3;        // Length field, LSB
_APDU_DATA = const(7) # uint8_t data[1];    // Data field


def frame_init() -> dict:
    # uint32_t cid;	    // Channel identifier
    # uint8_t cmd;	    // Command - b7 set
    # uint8_t bcnth;    // Message byte count - high part
    # uint8_t bcntl;    // Message byte count - low part
    # uint8_t data[HID_RPT_SIZE - 7];   // Data payload
    return {
        'cid':   0 | uctypes.UINT32,
        'cmd':   4 | uctypes.UINT8,
        'bcnt':  5 | uctypes.UINT16,
        'data': (7 | uctypes.ARRAY, (_HID_RPT_SIZE - 7) | uctypes.UINT8),
    }


def frame_cont() -> dict:
    # uint32_t cid;		// Channel identifier
    # uint8_t seq;		// Sequence number - b7 cleared
    # uint8_t data[HID_RPT_SIZE - 5];   // Data payload
    return {
        'cid':   0 | uctypes.UINT32,
        'seq':   4 | uctypes.UINT8,
        'data': (5 | uctypes.ARRAY, (_HID_RPT_SIZE - 5) | uctypes.UINT8),
    }


def resp_cmd_init() -> dict:
    # uint8_t nonce[8];         // Client application nonce
    # uint32_t cid;             // Channel identifier
    # uint8_t versionInterface; // Interface version
    # uint8_t versionMajor;	    // Major version number
    # uint8_t versionMinor;     // Minor version number
    # uint8_t versionBuild;     // Build version number
    # uint8_t capFlags;         // Capabilities flags
    return {
        'nonce':            (0 | uctypes.ARRAY, 8 | uctypes.UINT8),
        'cid':               8 | uctypes.UINT32,
        'versionInterface': 12 | uctypes.UINT8,
        'versionMajor':     13 | uctypes.UINT8,
        'versionMinor':     14 | uctypes.UINT8,
        'versionBuild':     15 | uctypes.UINT8,
        'capFlags':         16 | uctypes.UINT8,
    }


def resp_cmd_register() -> dict:
    # uint8_t registerId;       // Registration identifier (U2F_REGISTER_ID)
    # uint8_t pubKey[65];       // Generated public key
    # uint8_t keyHandleLen;     // Length of key handle
    # uint8_t keyHandle[128];   // Key handle
    # uint8_t cert[1024];       // Attestation certificate
    # uint8_t sig[72];          // Registration signature
    # uint16_t status;
    return {
        'registerId':       0 | uctypes.UINT8,
        'pubKey':          (1 | uctypes.ARRAY, 65 | uctypes.UINT8),
        'keyHandleLen':    66 | uctypes.UINT8,
        'keyHandle':      (67 | uctypes.ARRAY, 128 | uctypes.UINT8),
        'cert':          (195 | uctypes.ARRAY, 1024 | uctypes.UINT8),
        'sig':          (1219 | uctypes.ARRAY, 72 | uctypes.UINT8),
        'status':        1291 | uctypes.UINT16,
    }


def overlay_struct(buf, desc):
    desc_size = uctypes.sizeof(desc, uctypes.BIG_ENDIAN)
    if desc_size > len(buf):
        raise ValueError('desc is too big (%d > %d)' % (desc_size, len(buf)))
    return uctypes.struct(uctypes.addressof(buf), desc, uctypes.BIG_ENDIAN)


def make_struct(desc):
    desc_size = uctypes.sizeof(desc, uctypes.BIG_ENDIAN)
    buf = bytearray(desc_size)
    return buf, uctypes.struct(uctypes.addressof(buf), desc, uctypes.BIG_ENDIAN)


class Cmd:

    def __init__(self, cid: int, cmd: int, data: bytes):
        self.cid = cid
        self.cmd = cmd
        self.data = data

    def to_msg(self):
        cla = self.data[_APDU_CLA]
        ins = self.data[_APDU_INS]
        data = self.data[_APDU_DATA:]
        return Msg(self.cid, cla, ins, data)


class Msg:

    def __init__(self, cid: int, cla: int, ins: int, data: bytes):
        self.cid = cid
        self.cla = cla
        self.ins = ins
        self.data = data


def read_cmd(iface: int) -> Cmd:
    desc_init = frame_init()
    desc_cont = frame_cont()

    buf, = yield loop.select(iface)
    log.debug(__name__, 'read init %s', buf)

    ifrm = overlay_struct(buf, desc_init)
    cid = ifrm.cid
    bcnt = ifrm.bcnt
    data = ifrm.data
    datalen = len(data)
    seq = 0

    if datalen < bcnt:
        databuf = bytearray(bcnt)
        utils.memcpy(databuf, 0, data, 0, bcnt)
        data = databuf
    else:
        data = data[:bcnt]

    while datalen < bcnt:
        buf, = yield loop.select(iface)
        log.debug(__name__, 'read cont %s', buf)

        cfrm = overlay_struct(buf, desc_cont)

        if cfrm.seq == _CMD_INIT:
            ifrm = overlay_struct(buf, desc_init)
            data = ifrm.data[:ifrm.bcnt]
            break

        if cfrm.cid != cid:
            send_cmd(cmd_error(cfrm.cid, _ERR_CHANNEL_BUSY), iface)
            continue

        if cfrm.seq != seq:
            send_cmd(cmd_error(cfrm.cid, _ERR_INVALID_SEQ), iface)
            raise Exception(_ERR_INVALID_SEQ)

        datalen += utils.memcpy(data, datalen, cfrm.data, 0, bcnt - datalen)
        seq += 1

    return Cmd(cid, ifrm.cmd, data)


def send_cmd(cmd: Cmd, iface: int):
    init_desc = frame_init()
    cont_desc = frame_cont()
    offset = 0
    seq = 0
    datalen = len(cmd.data)

    buf, frm = make_struct(init_desc)
    frm.cid = cmd.cid
    frm.cmd = cmd.cmd
    frm.bcnt = datalen

    offset += utils.memcpy(frm.data, 0, cmd.data, offset, datalen)
    msg.send(iface, buf)
    log.debug(__name__, 'send init %s', buf)

    if offset < datalen:
        frm = overlay_struct(buf, cont_desc)

    while offset < datalen:
        frm.seq = seq
        offset += utils.memcpy(frm.data, 0, cmd.data, offset, datalen)
        msg.send(iface, buf)
        log.debug(__name__, 'send cont %s', buf)
        seq += 1


def boot():
    iface = 0x00
    loop.schedule_task(handle_reports(iface))


def handle_reports(iface: int):
    while True:
        try:
            req = yield from read_cmd(iface)
            resp = yield from dispatch_cmd(req)
            send_cmd(resp, iface)
        except Exception as e:
            log.exception(__name__, e)


async def dispatch_cmd(req: Cmd) -> Cmd:
    if req.cmd == _CMD_MSG:
        m = req.to_msg()

        if m.cla != 0:
            return msg_error(req, _SW_CLA_NOT_SUPPORTED)

        if m.ins == _MSG_REGISTER:
            log.debug(__name__, '_MSG_REGISTER')
            return await msg_register(m)
        elif m.ins == _MSG_AUTHENTICATE:
            log.debug(__name__, '_MSG_AUTHENTICATE')
            return await msg_authenticate(m)
        elif m.ins == _MSG_VERSION:
            log.debug(__name__, '_MSG_VERSION')
            return msg_version(m)
        else:
            log.warning(__name__, '_SW_INS_NOT_SUPPORTED: %d', m.ins)
            return msg_error(req, _SW_INS_NOT_SUPPORTED)

    elif req.cmd == _CMD_INIT:
        log.debug(__name__, '_CMD_INIT')
        return cmd_init(req)
    elif req.cmd == _CMD_PING:
        log.debug(__name__, '_CMD_PING')
        return req
    elif req.cmd == _CMD_WINK:
        log.debug(__name__, '_CMD_WINK')
        return req
    else:
        log.warning(__name__, '_ERR_INVALID_CMD: %d', req.cmd)
        return cmd_error(req.cid, _ERR_INVALID_CMD)


def cmd_init(req: Cmd) -> Cmd:
    if req.cid == 0:
        return cmd_error(req.cid, _ERR_INVALID_CID)
    elif req.cid == _CID_BROADCAST:
        resp_cid = random.uniform(0xfffffffe) + 1  # uint32_t except 0 and 0xffffffff
    else:
        resp_cid = req.cid

    buf, resp = make_struct(resp_cmd_init())
    utils.memcpy(resp.nonce, 0, req.data, 0, len(req.data))
    resp.cid = resp_cid
    resp.versionInterface = _U2FHID_IF_VERSION
    resp.versionMajor = 2
    resp.versionMinor = 0
    resp.versionBuild = 0
    resp.capFlags = _CAPFLAG_WINK

    return Cmd(req.cid, req.cmd, buf)


async def msg_register(req: Msg) -> Cmd:
    from apps.common import storage

    if not storage.is_initialized():
        return msg_error(req, _SW_CONDITIONS_NOT_SATISFIED)

    chal = req.data[:32]
    app_id = req.data[32:]
    buf = msg_register_sign(chal, app_id)

    return Cmd(req.cid, _CMD_MSG, buf)


def msg_register_sign(challenge: bytes, app_id: bytes) -> bytes:

    from apps.common import seed

    # derivation path is m/U2F'/r'/r'/r'/r'/r'/r'/r'/r'
    key_path = [0x80000000 | random.uniform(0xf0000000) for _ in range(0, 8)]
    node_path = [_U2F_KEY_PATH] + key_path

    # prepare signing key from random path, compute decompressed public key
    node = seed.get_root_without_passphrase('nist256p1')
    node.derive_path(node_path)
    pubkey = nist256p1.publickey(node.private_key(), False)

    # first half of keyhandle is key_path
    keybuf = ustruct.pack('>8L', *key_path)

    # second half of keyhandle is a hmac of app_id and key_path
    keybase = hmac.Hmac(node.private_key(), app_id, hashlib.sha256)
    keybase.update(keybuf)
    keybase = keybase.digest()

    # hash the request data together with keyhandle and pubkey
    dig = hashlib.sha256()
    dig.update(b'\x00')    # uint8_t reserved;
    dig.update(app_id)     # uint8_t appId[U2F_APPID_SIZE];
    dig.update(challenge)  # uint8_t chal[U2F_CHAL_SIZE];
    dig.update(keybuf)     # uint8_t keyHandle[KEY_HANDLE_LEN];
    dig.update(keybase)
    dig.update(pubkey)     # uint8_t pubKey[U2F_PUBKEY_LEN];
    dig = dig.digest()

    # sign the digest and convert to der
    sig = nist256p1.sign(node.private_key(), dig, False)
    sig = der.encode_seq((sig[1:33], sig[33:]))

    # pack to a response
    buf, resp = make_struct(resp_cmd_register())
    resp.registerId = _U2F_REGISTER_ID
    resp.status = _SW_NO_ERROR
    resp.keyHandleLen = len(keybuf) + len(keybase)
    utils.memcpy(resp.cert, 0, _U2F_ATT_CERT, 0, len(_U2F_ATT_CERT))
    utils.memcpy(resp.pubKey, 0, pubkey, 0, len(pubkey))
    utils.memcpy(resp.keyHandle, 0, keybuf, 0, len(keybuf))
    utils.memcpy(resp.keyHandle, len(keybuf), keybase, 0, len(keybase))
    utils.memcpy(resp.sig, 0, sig, 0, len(sig))

    return buf


async def msg_authenticate(req: Msg) -> Cmd:
    pass


def msg_version(req: Msg) -> Cmd:
    return Cmd(req.cid, _CMD_MSG, b'U2F_V2\x90\x00')  # includes _SW_NO_ERROR


def msg_error(req: Msg, code: int) -> Cmd:
    return Cmd(req.cid, _CMD_MSG, ustruct.pack('>H', code))


def cmd_error(cid: int, code: int) -> Cmd:
    return Cmd(cid, _CMD_ERROR, ustruct.pack('>B', code))
