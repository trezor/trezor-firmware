import uctypes
import ustruct
import utime
from micropython import const

from trezor import config, io, log, loop, res, ui, utils, workflow
from trezor.crypto import aes, der, hashlib, hmac, random
from trezor.crypto.curve import nist256p1
from trezor.ui.confirm import CONFIRMED, Confirm
from trezor.ui.swipe import SWIPE_HORIZONTAL, SWIPE_LEFT, SWIPE_RIGHT, Swipe
from trezor.ui.text import Text

from apps.common import HARDENED, cbor, storage
from apps.webauthn.credential import Credential

if False:
    from typing import List, Optional

_HID_RPT_SIZE = const(64)
_CID_BROADCAST = const(0xFFFFFFFF)  # broadcast channel id

# types of frame
_TYPE_MASK = const(0x80)  # frame type mask
_TYPE_INIT = const(0x80)  # initial frame identifier
_TYPE_CONT = const(0x00)  # continuation frame identifier

# types of cmd
_CMD_PING = const(0x81)  # echo data through local processor only
_CMD_MSG = const(0x83)  # send U2F message frame
_CMD_LOCK = const(0x84)  # send lock channel command
_CMD_INIT = const(0x86)  # channel initialization
_CMD_WINK = const(0x88)  # send device identification wink
_CMD_CBOR = const(0x90)  # send encapsulated CTAP CBOR encoded message
_CMD_CANCEL = const(0x91)  # cancel any outstanding requests on this CID
_CMD_KEEPALIVE = const(0xBB)  # processing a message
_CMD_ERROR = const(0xBF)  # error response

# types for the msg cmd
_MSG_REGISTER = const(0x01)  # registration command
_MSG_AUTHENTICATE = const(0x02)  # authenticate/sign command
_MSG_VERSION = const(0x03)  # read version string command

# types for the cbor cmd
_CBOR_MAKE_CREDENTIAL = const(0x01)  # generate new credential command
_CBOR_GET_ASSERTION = const(0x02)  # authenticate command
_CBOR_GET_INFO = const(0x04)  # report AAGUID and device capabilities
_CBOR_CLIENT_PIN = const(0x06)  # PIN and pinToken management
_CBOR_RESET = const(0x07)  # factory reset, invalidating all generated credentials
_CBOR_GET_NEXT_ASSERTION = const(0x08)  # obtain the next per-credential signature

# CBOR MakeCredential command parameter keys
_MAKECRED_CMD_CLIENT_DATA_HASH = const(0x01)  # bytes, required
_MAKECRED_CMD_RP = const(0x02)  # map, required
_MAKECRED_CMD_USER = const(0x03)  # map, required
_MAKECRED_CMD_PUB_KEY_CRED_PARAMS = const(0x04)  # array of maps, required
_MAKECRED_CMD_EXCLUDE_LIST = const(0x05)  # array of maps, optional
_MAKECRED_CMD_EXTENSIONS = const(0x06)  # map, optional
_MAKECRED_CMD_OPTIONS = const(0x07)  # map, optional
_MAKECRED_CMD_PIN_AUTH = const(0x08)  # bytes, optional

# CBOR MakeCredential response member keys
_MAKECRED_RESP_FMT = const(0x01)  # str, required
_MAKECRED_RESP_AUTH_DATA = const(0x02)  # bytes, required
_MAKECRED_RESP_ATT_STMT = const(0x03)  # map, required

# CBOR GetAssertion command parameter keys
_GETASSERT_CMD_RP_ID = const(0x01)  # str, required
_GETASSERT_CMD_CLIENT_DATA_HASH = const(0x02)  # bytes, required
_GETASSERT_CMD_ALLOW_LIST = const(0x03)  # array of maps, optional
_GETASSERT_CMD_EXTENSIONS = const(0x04)  # map, optional
_GETASSERT_CMD_OPTIONS = const(0x05)  # map, optional
_GETASSERT_CMD_PIN_AUTH = const(0x06)  # bytes, optional

# CBOR GetAssertion response member keys
_GETASSERT_RESP_CREDENTIAL = const(0x01)  # map, optional
_GETASSERT_RESP_AUTH_DATA = const(0x02)  # bytes, required
_GETASSERT_RESP_SIGNATURE = const(0x03)  # bytes, required
_GETASSERT_RESP_USER = const(0x04)  # map, optional
_GETASSERT_RESP_PUB_KEY_CREDENTIAL_USER_ENTITY = const(0x04)  # map, optional
_GETASSERT_RESP_NUM_OF_CREDENTIALS = const(0x05)  # int, optional

# CBOR GetInfo response member keys
_GETINFO_RESP_VERSIONS = const(0x01)  # array of str, required
_GETINFO_RESP_EXTENSIONS = const(0x02)  # array of str, optional
_GETINFO_RESP_AAGUID = const(0x03)  # bytes(16), required
_GETINFO_RESP_OPTIONS = const(0x04)  # map, optional

# CBOR ClientPin command parameter keys
_CLIENTPIN_CMD_PIN_PROTOCOL = const(0x01)  # unsigned int, required
_CLIENTPIN_CMD_SUBCOMMAND = const(0x02)  # unsigned int, required
_CLIENTPIN_SUBCMD_GET_KEY_AGREEMENT = const(0x02)

# CBOR ClientPin response member keys
_CLIENTPIN_RESP_KEY_AGREEMENT = const(0x01)  # COSE_Key, optional

# status codes for the keepalive cmd
_KEEPALIVE_STATUS_PROCESSING = const(0x01)  # still processing the current request
_KEEPALIVE_STATUS_UP_NEEDED = const(0x02)  # waiting for user presence

# time intervals and timeouts
_KEEPALIVE_INTERVAL_MS = const(80)  # interval between keepalive commands
_U2F_CONFIRM_TIMEOUT_MS = const(10 * 1000)
_FIDO2_CONFIRM_TIMEOUT_MS = const(60 * 1000)

# CBOR object signing and encryption algorithms and keys
_COSE_ALG_KEY = const(3)
_COSE_ALG_ES256 = const(-7)  # ECDSA P-256 with SHA-256
_COSE_KEY_TYPE_KEY = const(1)
_COSE_KEY_TYPE_EC2 = const(2)  # elliptic curve keys with x- and y-coordinate pair
_COSE_CURVE_KEY = const(-1)  # elliptic curve identifier
_COSE_CURVE_P256 = const(1)  # P-256 curve
_COSE_X_COORD_KEY = const(-2)  # x coordinate of the public key
_COSE_Y_COORD_KEY = const(-3)  # y coordinate of the public key

# hid error codes
_ERR_NONE = const(0x00)  # no error
_ERR_INVALID_CMD = const(0x01)  # invalid command
_ERR_INVALID_PAR = const(0x02)  # invalid parameter
_ERR_INVALID_LEN = const(0x03)  # invalid message length
_ERR_INVALID_SEQ = const(0x04)  # invalid message sequencing
_ERR_MSG_TIMEOUT = const(0x05)  # message has timed out
_ERR_CHANNEL_BUSY = const(0x06)  # channel busy
_ERR_LOCK_REQUIRED = const(0x0A)  # command requires channel lock
_ERR_INVALID_CID = const(0x0B)  # command not allowed on this cid
_ERR_INVALID_CBOR = const(0x12)  # error when parsing CBOR
_ERR_CREDENTIAL_EXCLUDED = const(0x19)  # valid credential found in the exclude list
_ERR_UNSUPPORTED_ALGORITHM = const(0x26)  # requested COSE algorithm not supported
_ERR_OPERATION_DENIED = const(0x27)  # user declined or timed out
_ERR_KEY_STORE_FULL = const(0x28)  # internal key storage is full
_ERR_UNSUPPORTED_OPTION = const(0x2B)  # unsupported option
_ERR_NO_CREDENTIALS = const(0x2E)  # no valid credentials provided
_ERR_NOT_ALLOWED = const(0x30)  # continuation command not allowed
_ERR_PIN_AUTH_INVALID = const(0x33)  # pinAuth verification failed
_ERR_OTHER = const(0x7F)  # other unspecified error

# command status responses
_SW_NO_ERROR = const(0x9000)
_SW_WRONG_LENGTH = const(0x6700)
_SW_DATA_INVALID = const(0x6984)
_SW_CONDITIONS_NOT_SATISFIED = const(0x6985)
_SW_WRONG_DATA = const(0x6A80)
_SW_INS_NOT_SUPPORTED = const(0x6D00)
_SW_CLA_NOT_SUPPORTED = const(0x6E00)

# init response
_CAPFLAG_WINK = const(0x01)  # device supports _CMD_WINK
_CAPFLAG_CBOR = const(0x04)  # device supports _CMD_CBOR
_U2FHID_IF_VERSION = const(2)  # interface version

# Key paths
_U2F_KEY_PATH = const(0x80553246)

# register response
_U2F_REGISTER_ID = const(0x05)  # version 2 registration identifier
_U2F_ATT_PRIV_KEY = b"q&\xac+\xf6D\xdca\x86\xad\x83\xef\x1f\xcd\xf1*W\xb5\xcf\xa2\x00\x0b\x8a\xd0'\xe9V\xe8T\xc5\n\x8b"
_U2F_ATT_CERT = b"0\x82\x01\x180\x81\xc0\x02\t\x00\xb1\xd9\x8fBdr\xd3,0\n\x06\x08*\x86H\xce=\x04\x03\x020\x151\x130\x11\x06\x03U\x04\x03\x0c\nTrezor U2F0\x1e\x17\r160429133153Z\x17\r260427133153Z0\x151\x130\x11\x06\x03U\x04\x03\x0c\nTrezor U2F0Y0\x13\x06\x07*\x86H\xce=\x02\x01\x06\x08*\x86H\xce=\x03\x01\x07\x03B\x00\x04\xd9\x18\xbd\xfa\x8aT\xac\x92\xe9\r\xa9\x1f\xcaz\xa2dT\xc0\xd1s61M\xde\x83\xa5K\x86\xb5\xdfN\xf0Re\x9a\x1do\xfc\xb7F\x7f\x1a\xcd\xdb\x8a3\x08\x0b^\xed\x91\x89\x13\xf4C\xa5&\x1b\xc7{h`o\xc10\n\x06\x08*\x86H\xce=\x04\x03\x02\x03G\x000D\x02 $\x1e\x81\xff\xd2\xe5\xe6\x156\x94\xc3U.\x8f\xeb\xd7\x1e\x895\x92\x1c\xb4\x83ACq\x1cv\xea\xee\xf3\x95\x02 _\x80\xeb\x10\xf2\\\xcc9\x8b<\xa8\xa9\xad\xa4\x02\x7f\x93\x13 w\xb7\xab\xcewFZ'\xf5=3\xa1\x1d"
_BOGUS_APPID = b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
_AAGUID = (
    b"\x80\xbc\xc8T\x83\xb9\xf3\x0e\x9d6TF\x00\x08\x08\x86"
)  # First 16 bytes of SHA-256("TREZOR")

# authentication control byte
_AUTH_ENFORCE = const(0x03)  # enforce user presence and sign
_AUTH_CHECK_ONLY = const(0x07)  # check only
_AUTH_FLAG_UP = const(1 << 0)  # user present
_AUTH_FLAG_UV = const(1 << 2)  # user verified
_AUTH_FLAG_AT = const(1 << 6)  # attested credential data included
_AUTH_FLAG_ED = const(1 << 7)  # extension data included

# common raw message format (ISO7816-4:2005 mapping)
_APDU_CLA = const(0)  # uint8_t cla;        // Class - reserved
_APDU_INS = const(1)  # uint8_t ins;        // U2F instruction
_APDU_P1 = const(2)  # uint8_t p1;         // U2F parameter 1
_APDU_P2 = const(3)  # uint8_t p2;         // U2F parameter 2
_APDU_LC1 = const(4)  # uint8_t lc1;        // Length field, set to zero
_APDU_LC2 = const(5)  # uint8_t lc2;        // Length field, MSB
_APDU_LC3 = const(6)  # uint8_t lc3;        // Length field, LSB
_APDU_DATA = const(7)  # uint8_t data[1];    // Data field

_FRAME_INIT_SIZE = 57
_FRAME_CONT_SIZE = 59

# Generate the authenticatorKeyAgreementKey used for ECDH in authenticatorClientPIN getKeyAgreement.
_KEY_AGREEMENT_PRIVKEY = nist256p1.generate_secret()
_KEY_AGREEMENT_PUBKEY = nist256p1.publickey(_KEY_AGREEMENT_PRIVKEY, False)

_ALLOW_RESIDENT_CREDENTIALS = True


def frame_init() -> dict:
    # uint32_t cid;     // Channel identifier
    # uint8_t cmd;      // Command - b7 set
    # uint8_t bcnth;    // Message byte count - high part
    # uint8_t bcntl;    // Message byte count - low part
    # uint8_t data[HID_RPT_SIZE - 7];   // Data payload
    return {
        "cid": 0 | uctypes.UINT32,
        "cmd": 4 | uctypes.UINT8,
        "bcnt": 5 | uctypes.UINT16,
        "data": (7 | uctypes.ARRAY, (_HID_RPT_SIZE - 7) | uctypes.UINT8),
    }


def frame_cont() -> dict:
    # uint32_t cid;                     // Channel identifier
    # uint8_t seq;                      // Sequence number - b7 cleared
    # uint8_t data[HID_RPT_SIZE - 5];   // Data payload
    return {
        "cid": 0 | uctypes.UINT32,
        "seq": 4 | uctypes.UINT8,
        "data": (5 | uctypes.ARRAY, (_HID_RPT_SIZE - 5) | uctypes.UINT8),
    }


def resp_cmd_init() -> dict:
    # uint8_t nonce[8];         // Client application nonce
    # uint32_t cid;             // Channel identifier
    # uint8_t versionInterface; // Interface version
    # uint8_t versionMajor;     // Major version number
    # uint8_t versionMinor;     // Minor version number
    # uint8_t versionBuild;     // Build version number
    # uint8_t capFlags;         // Capabilities flags
    return {
        "nonce": (0 | uctypes.ARRAY, 8 | uctypes.UINT8),
        "cid": 8 | uctypes.UINT32,
        "versionInterface": 12 | uctypes.UINT8,
        "versionMajor": 13 | uctypes.UINT8,
        "versionMinor": 14 | uctypes.UINT8,
        "versionBuild": 15 | uctypes.UINT8,
        "capFlags": 16 | uctypes.UINT8,
    }


def resp_cmd_register(khlen: int, certlen: int, siglen: int) -> dict:
    cert_ofs = 67 + khlen
    sig_ofs = cert_ofs + certlen
    status_ofs = sig_ofs + siglen
    # uint8_t registerId;       // Registration identifier (U2F_REGISTER_ID)
    # uint8_t pubKey[65];       // Generated public key
    # uint8_t keyHandleLen;     // Length of key handle
    # uint8_t keyHandle[khlen]; // Key handle
    # uint8_t cert[certlen];    // Attestation certificate
    # uint8_t sig[siglen];      // Registration signature
    # uint16_t status;
    return {
        "registerId": 0 | uctypes.UINT8,
        "pubKey": (1 | uctypes.ARRAY, 65 | uctypes.UINT8),
        "keyHandleLen": 66 | uctypes.UINT8,
        "keyHandle": (67 | uctypes.ARRAY, khlen | uctypes.UINT8),
        "cert": (cert_ofs | uctypes.ARRAY, certlen | uctypes.UINT8),
        "sig": (sig_ofs | uctypes.ARRAY, siglen | uctypes.UINT8),
        "status": status_ofs | uctypes.UINT16,
    }


# index of keyHandleLen in req_cmd_authenticate struct
_REQ_CMD_AUTHENTICATE_KHLEN = const(64)


def req_cmd_authenticate(khlen: int) -> dict:
    # uint8_t chal[32];         // Challenge
    # uint8_t appId[32];        // Application id
    # uint8_t keyHandleLen;     // Length of key handle
    # uint8_t keyHandle[khlen]; // Key handle
    return {
        "chal": (0 | uctypes.ARRAY, 32 | uctypes.UINT8),
        "appId": (32 | uctypes.ARRAY, 32 | uctypes.UINT8),
        "keyHandleLen": 64 | uctypes.UINT8,
        "keyHandle": (65 | uctypes.ARRAY, khlen | uctypes.UINT8),
    }


def resp_cmd_authenticate(siglen: int) -> dict:
    status_ofs = 5 + siglen
    # uint8_t flags;        // U2F_AUTH_FLAG_ values
    # uint32_t ctr;         // Counter field (big-endian)
    # uint8_t sig[siglen];  // Signature
    # uint16_t status;
    return {
        "flags": 0 | uctypes.UINT8,
        "ctr": 1 | uctypes.UINT32,
        "sig": (5 | uctypes.ARRAY, siglen | uctypes.UINT8),
        "status": status_ofs | uctypes.UINT16,
    }


def overlay_struct(buf, desc):
    desc_size = uctypes.sizeof(desc, uctypes.BIG_ENDIAN)
    if desc_size > len(buf):
        raise ValueError("desc is too big (%d > %d)" % (desc_size, len(buf)))
    return uctypes.struct(uctypes.addressof(buf), desc, uctypes.BIG_ENDIAN)


def make_struct(desc):
    desc_size = uctypes.sizeof(desc, uctypes.BIG_ENDIAN)
    buf = bytearray(desc_size)
    return buf, uctypes.struct(uctypes.addressof(buf), desc, uctypes.BIG_ENDIAN)


class Msg:
    def __init__(
        self, cid: int, cla: int, ins: int, p1: int, p2: int, lc: int, data: bytes
    ) -> None:
        self.cid = cid
        self.cla = cla
        self.ins = ins
        self.p1 = p1
        self.p2 = p2
        self.lc = lc
        self.data = data


class Cmd:
    def __init__(self, cid: int, cmd: int, data: bytes) -> None:
        self.cid = cid
        self.cmd = cmd
        self.data = data

    def to_msg(self) -> Msg:
        cla = self.data[_APDU_CLA]
        ins = self.data[_APDU_INS]
        p1 = self.data[_APDU_P1]
        p2 = self.data[_APDU_P2]
        lc = (
            (self.data[_APDU_LC1] << 16)
            + (self.data[_APDU_LC2] << 8)
            + (self.data[_APDU_LC3])
        )
        data = self.data[_APDU_DATA : _APDU_DATA + lc]
        return Msg(self.cid, cla, ins, p1, p2, lc, data)


async def read_cmd(iface: io.HID) -> Cmd:
    desc_init = frame_init()
    desc_cont = frame_cont()
    read = loop.wait(iface.iface_num() | io.POLL_READ)

    buf = await read

    ifrm = overlay_struct(buf, desc_init)
    bcnt = ifrm.bcnt
    data = ifrm.data
    datalen = len(data)
    seq = 0

    if ifrm.cmd & _TYPE_MASK == _TYPE_CONT:
        # unexpected cont packet, abort current msg
        if __debug__:
            log.warning(__name__, "_TYPE_CONT")
        return None

    if datalen < bcnt:
        databuf = bytearray(bcnt)
        utils.memcpy(databuf, 0, data, 0, bcnt)
        data = databuf
    else:
        data = data[:bcnt]

    while datalen < bcnt:
        buf = await read

        cfrm = overlay_struct(buf, desc_cont)

        if cfrm.seq == _CMD_INIT:
            # _CMD_INIT frame, cancels current channel
            ifrm = overlay_struct(buf, desc_init)
            data = ifrm.data[: ifrm.bcnt]
            break

        if cfrm.cid != ifrm.cid:
            # cont frame for a different channel, reply with BUSY and skip
            if __debug__:
                log.warning(__name__, "_ERR_CHANNEL_BUSY")
            await send_cmd(cmd_error(cfrm.cid, _ERR_CHANNEL_BUSY), iface)
            continue

        if cfrm.seq != seq:
            # cont frame for this channel, but incorrect seq number, abort
            # current msg
            if __debug__:
                log.warning(__name__, "_ERR_INVALID_SEQ")
            await send_cmd(cmd_error(cfrm.cid, _ERR_INVALID_SEQ), iface)
            return None

        datalen += utils.memcpy(data, datalen, cfrm.data, 0, bcnt - datalen)
        seq += 1

    return Cmd(ifrm.cid, ifrm.cmd, data)


async def send_cmd(cmd: Cmd, iface: io.HID) -> None:
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
    iface.write(buf)

    if offset < datalen:
        frm = overlay_struct(buf, cont_desc)

    write = loop.wait(iface.iface_num() | io.POLL_WRITE)
    while offset < datalen:
        frm.seq = seq
        copied = utils.memcpy(frm.data, 0, cmd.data, offset, datalen)
        offset += copied
        if copied < _FRAME_CONT_SIZE:
            frm.data[copied:] = bytearray(_FRAME_CONT_SIZE - copied)
        while True:
            await write
            if iface.write(buf) > 0:
                break
        seq += 1


def boot(iface: io.HID):
    loop.schedule(handle_reports(iface))


async def handle_reports(iface: io.HID):
    dialog_mgr = DialogManager(iface)

    while True:
        try:
            req = await read_cmd(iface)
            if req is None:
                continue
            resp = dispatch_cmd(req, dialog_mgr)
            if resp is not None:
                await send_cmd(resp, iface)
        except Exception as e:
            log.exception(__name__, e)


class State:
    def __init__(self, cid: int) -> None:
        self.cid = cid
        self.app_icon = None

    def user_name(self) -> Optional[str]:
        return None

    def get_dialog(self):
        content = ConfirmContent(self)
        return Confirm(content)

    def keepalive_status(self) -> Optional[int]:
        return None

    def timeout_ms(self) -> int:
        return _U2F_CONFIRM_TIMEOUT_MS

    def load_icon(self, app_id: bytes) -> None:
        from trezor import res
        from apps.webauthn import knownapps

        try:
            namepart = knownapps.knownapps[app_id].lower().replace(" ", "_")
            icon = res.load("apps/webauthn/res/icon_%s.toif" % namepart)
        except Exception as e:
            icon = res.load("apps/webauthn/res/icon_webauthn.toif")
            if __debug__:
                log.exception(__name__, e)
        self.app_icon = icon

    def on_confirm(self) -> Optional[Cmd]:
        return None

    def on_decline(self) -> Optional[Cmd]:
        return None

    def on_timeout(self) -> Optional[Cmd]:
        return self.on_decline()


class U2fState(State):
    def __init__(self, cid: int, checksum: bytes, app_id: bytes) -> None:
        super(U2fState, self).__init__(cid)
        self.app_id = bytes(app_id)  # could be bytearray, which doesn't have __hash__
        self.app_name = None
        self.app_icon = None
        self.checksum = checksum
        self.boot()

    def boot(self) -> None:
        self.load_icon(self.app_id)
        from ubinascii import hexlify
        from apps.webauthn import knownapps

        if self.app_id in knownapps.knownapps:
            name = knownapps.knownapps[self.app_id]
        else:
            name = "%s...%s" % (
                hexlify(self.app_id[:4]).decode(),
                hexlify(self.app_id[-4:]).decode(),
            )
        self.app_name = name


class U2fConfirmRegister(U2fState):
    def __init__(self, cid: int, checksum: bytes, app_id: bytes) -> None:
        super(U2fConfirmRegister, self).__init__(cid, checksum, app_id)

    def get_dialog(self):
        if self.app_id == _BOGUS_APPID:
            text = Text("U2F", ui.ICON_WRONG, ui.RED)
            text.normal(
                "Another U2F device", "was used to register", "in this application."
            )
            return Confirm(text, confirm=None)
        else:
            return super(U2fConfirmRegister, self).get_dialog()

    def get_header(self) -> str:
        return "U2F Register"

    def __eq__(self, other) -> bool:
        return isinstance(other, U2fConfirmRegister) and self.checksum == other.checksum


class U2fConfirmAuthenticate(U2fState):
    def __init__(self, cid: int, checksum: bytes, app_id: bytes) -> None:
        super(U2fConfirmAuthenticate, self).__init__(cid, checksum, app_id)

    def get_header(self) -> str:
        return "U2F Authenticate"

    def __eq__(self, other) -> bool:
        return (
            isinstance(other, U2fConfirmAuthenticate)
            and self.checksum == other.checksum
        )


class Fido2State(State):
    def __init__(self, cid: int) -> None:
        super(Fido2State, self).__init__(cid)

    def keepalive_status(self) -> int:
        return _KEEPALIVE_STATUS_UP_NEEDED

    def timeout_ms(self) -> int:
        return _FIDO2_CONFIRM_TIMEOUT_MS


class Fido2ConfirmMakeCredential(Fido2State):
    def __init__(
        self, cid: int, client_data_hash: bytes, cred: Credential, resident: bool
    ) -> None:
        super(Fido2ConfirmMakeCredential, self).__init__(cid)
        self.client_data_hash = client_data_hash
        self.cred = cred
        self.resident = resident
        self.app_name = cred.rp_id
        self.load_icon(hashlib.sha256(cred.rp_id).digest())

    def get_header(self) -> str:
        return "FIDO2 Register"

    def user_name(self) -> Optional[str]:
        return self.cred.name()

    def on_confirm(self) -> Cmd:
        self.cred.generate_id()

        response_data = cbor_make_credential_sign(self.client_data_hash, self.cred)
        if self.resident:
            if not storage.webauthn.store_resident_credential(self.cred):
                return cbor_error(self.cid, _ERR_KEY_STORE_FULL)
        return Cmd(self.cid, _CMD_CBOR, bytes([_ERR_NONE]) + response_data)

    def on_decline(self) -> Cmd:
        return cbor_error(self.cid, _ERR_OPERATION_DENIED)


class Fido2ConfirmGetAssertion(Fido2State):
    def __init__(
        self,
        cid: int,
        client_data_hash: bytes,
        creds: List[Credential],
        hmac_secret: map,
    ) -> None:
        super(Fido2ConfirmGetAssertion, self).__init__(cid)
        self.client_data_hash = client_data_hash
        self.creds = creds
        self.hmac_secret = hmac_secret
        self.i = 0
        self.app_name = creds[0].rp_id
        self.load_icon(hashlib.sha256(self.app_name).digest())

    def get_header(self):
        return "FIDO2 Authenticate"

    def user_name(self) -> Optional[str]:
        return self.creds[self.i].name()

    def get_dialog(self):
        content = ConfirmContent(self)
        return ConfirmGetAssertion(content, len(self.creds))

    def on_confirm(self) -> Cmd:
        cred = self.creds[self.i]

        try:
            response_data = cbor_get_assertion_sign(
                self.client_data_hash,
                hashlib.sha256(cred.rp_id).digest(),
                cred,
                self.hmac_secret,
            )
            return Cmd(self.cid, _CMD_CBOR, bytes([_ERR_NONE]) + response_data)
        except Exception:
            return cbor_error(self.cid, _ERR_OPERATION_DENIED)

    def on_decline(self) -> Cmd:
        return cbor_error(self.cid, _ERR_OPERATION_DENIED)


class Fido2ConfirmExcluded(Fido2State):
    def __init__(self, cid: int, cred: Credential) -> None:
        super(Fido2ConfirmExcluded, self).__init__(cid)
        self.cred = cred

    def get_dialog(self):
        text = Text("FIDO2 Register", ui.ICON_WRONG, ui.RED)
        text.normal("This token is already", "registered with", self.cred.rp_id + ".")
        return Confirm(text, confirm=None)

    def on_confirm(self) -> Cmd:
        return cbor_error(self.cid, _ERR_CREDENTIAL_EXCLUDED)

    def on_decline(self) -> Cmd:
        return cbor_error(self.cid, _ERR_CREDENTIAL_EXCLUDED)


class Fido2ConfirmNoPin(Fido2State):
    def __init__(self, cid: int) -> None:
        super(Fido2ConfirmNoPin, self).__init__(cid)

    def get_dialog(self):
        text = Text("FIDO2 Verify User", ui.ICON_WRONG, ui.RED)
        text.normal("Unable to verify user.", "Please enable PIN", "protection.")
        return Confirm(text, confirm=None)

    def on_confirm(self) -> Cmd:
        return cbor_error(self.cid, _ERR_OPERATION_DENIED)

    def on_decline(self) -> Cmd:
        return cbor_error(self.cid, _ERR_OPERATION_DENIED)


class Fido2ConfirmNoCredentials(Fido2State):
    def __init__(self, cid: int, rp_id: str) -> None:
        super(Fido2ConfirmNoCredentials, self).__init__(cid)
        self.app_name = rp_id

    def get_dialog(self):
        text = Text("FIDO2 Authenticate", ui.ICON_WRONG, ui.RED)
        text.normal("This token is not", "registered with", self.app_name + ".")
        return Confirm(text, confirm=None)

    def on_confirm(self) -> Cmd:
        return cbor_error(self.cid, _ERR_NO_CREDENTIALS)

    def on_decline(self) -> Cmd:
        return cbor_error(self.cid, _ERR_NO_CREDENTIALS)


class Fido2ConfirmReset(Fido2State):
    def __init__(self, cid: int) -> None:
        super(Fido2ConfirmReset, self).__init__(cid)

    def get_dialog(self):
        text = Text("FIDO2 Reset", ui.ICON_CONFIG)
        text.normal("Do you really want to")
        text.bold("erase all credentials?")
        return Confirm(text)

    def on_confirm(self) -> Cmd:
        storage.webauthn.erase_resident_credentials()
        return Cmd(self.cid, _CMD_CBOR, bytes([_ERR_NONE]))

    def on_decline(self) -> Cmd:
        return cbor_error(self.cid, _ERR_OPERATION_DENIED)

    def keepalive_status(self) -> int:
        return _KEEPALIVE_STATUS_UP_NEEDED

    def timeout_ms(self) -> int:
        return _FIDO2_CONFIRM_TIMEOUT_MS


class DialogManager:
    def __init__(self, iface: io.HID) -> None:
        self.iface = iface
        self._clear()

    def _clear(self) -> None:
        self.state = None
        self.deadline = 0
        self.confirmed = None
        self.workflow = None
        self.keepalive = None

    def reset_timeout(self) -> None:
        self.deadline = utime.ticks_ms() + self.state.timeout_ms()

    def reset(self) -> None:
        if self.workflow is not None:
            loop.close(self.workflow)
        if self.keepalive is not None:
            loop.close(self.keepalive)
        self._clear()

    def is_busy(self) -> bool:
        if self.workflow is None:
            return False
        if utime.ticks_ms() >= self.deadline:
            self.reset()
            return False
        return True

    def compare(self, state: State) -> bool:
        if self.state != state:
            return False
        if utime.ticks_ms() >= self.deadline:
            self.reset()
            return False
        return True

    def set_state(self, state: State) -> bool:
        if utime.ticks_ms() >= self.deadline:
            self.reset()

        if workflow.workflows:
            return False

        self.state = state
        self.reset_timeout()
        if state.keepalive_status() is not None:
            self.confirmed = loop.signal()
            self.keepalive = self.keepalive_loop()
            loop.schedule(self.keepalive)
        else:
            self.confirmed = None
            self.keepalive = None
        self.workflow = self.dialog_workflow()
        loop.schedule(self.workflow)
        return True

    async def keepalive_loop(self) -> None:
        while True:
            waiter = loop.spawn(
                loop.sleep(_KEEPALIVE_INTERVAL_MS * 1000), self.confirmed
            )
            user_confirmed = await waiter
            if self.confirmed in waiter.finished:
                if user_confirmed:
                    await send_cmd(self.state.on_confirm(), self.iface)
                else:
                    await send_cmd(self.state.on_decline(), self.iface)
                return
            if utime.ticks_ms() >= self.deadline:
                await send_cmd(self.state.on_timeout(), self.iface)
                self.reset()
                return
            await send_cmd(
                cmd_keepalive(self.state.cid, self.state.keepalive_status()), self.iface
            )

    async def dialog_workflow(self) -> None:
        try:
            workflow.onstart(self.workflow)
            await self.dialog_layout()
        finally:
            workflow.onclose(self.workflow)
            self.workflow = None

    async def dialog_layout(self) -> None:
        dialog = self.state.get_dialog()
        confirmed = await dialog is CONFIRMED
        if isinstance(self.confirmed, loop.signal):
            self.confirmed.send(confirmed)
        else:
            self.confirmed = confirmed


class ConfirmGetAssertion(Confirm):
    def __init__(self, content: ui.Control, page_count: int):
        super(ConfirmGetAssertion, self).__init__(content)
        self.page_count = page_count
        self.page = 0

    async def handle_paging(self):
        if self.page == 0:
            directions = SWIPE_LEFT
        elif self.page == self.page_count - 1:
            directions = SWIPE_RIGHT
        else:
            directions = SWIPE_HORIZONTAL

        swipe = await Swipe(directions)

        if swipe == SWIPE_LEFT:
            self.page = min(self.page + 1, self.page_count - 1)
        else:
            self.page = max(self.page - 1, 0)

        self.content.state.i = self.page
        self.content.repaint = True
        self.confirm.repaint = True
        self.cancel.repaint = True

    def create_tasks(self):
        tasks = super(ConfirmGetAssertion, self).create_tasks()
        if self.page_count > 1:
            return tasks + (self.handle_paging(),)
        else:
            return tasks

    def dispatch(self, event, x, y):
        PULSE_PERIOD = const(1200000)

        super(ConfirmGetAssertion, self).dispatch(event, x, y)

        if event is ui.RENDER:
            if self.page != 0:
                t = ui.pulse(PULSE_PERIOD)
                c = ui.blend(ui.GREY, ui.DARK_GREY, t)
                icon = res.load(ui.ICON_SWIPE_RIGHT)
                ui.display.icon(18, 68, icon, c, ui.BG)

            if self.page != self.page_count - 1:
                t = ui.pulse(PULSE_PERIOD, PULSE_PERIOD / 2)
                c = ui.blend(ui.GREY, ui.DARK_GREY, t)
                icon = res.load(ui.ICON_SWIPE_LEFT)
                ui.display.icon(205, 68, icon, c, ui.BG)


def text_center_trim_left(
    x: int, y: int, text: str, font: int = ui.NORMAL, width: int = ui.WIDTH - 16
) -> None:
    if ui.display.text_width(text, font) <= width:
        ui.display.text_center(x, y, text, font, ui.FG, ui.BG)
        return

    ELLIPSIS_WIDTH = ui.display.text_width("...", ui.BOLD)
    if width < ELLIPSIS_WIDTH:
        return

    text_length = 0
    for i in range(1, len(text)):
        if ui.display.text_width(text[-i:], font) + ELLIPSIS_WIDTH > width:
            text_length = i - 1
            break

    text_width = ui.display.text_width(text[-text_length:], font)
    x -= (text_width + ELLIPSIS_WIDTH) // 2
    ui.display.text(x, y, "...", ui.BOLD, ui.GREY, ui.BG)
    x += ELLIPSIS_WIDTH
    ui.display.text(x, y, text[-text_length:], font, ui.FG, ui.BG)


def text_center_trim_right(
    x: int, y: int, text: str, font: int = ui.NORMAL, width: int = ui.WIDTH - 16
) -> None:
    if ui.display.text_width(text, font) <= width:
        ui.display.text_center(x, y, text, font, ui.FG, ui.BG)
        return

    ELLIPSIS_WIDTH = ui.display.text_width("...", ui.BOLD)
    if width < ELLIPSIS_WIDTH:
        return

    text_length = 0
    for i in range(1, len(text)):
        if ui.display.text_width(text[:i], font) + ELLIPSIS_WIDTH > width:
            text_length = i - 1
            break

    text_width = ui.display.text_width(text[:text_length], font)
    x -= (text_width + ELLIPSIS_WIDTH) // 2
    ui.display.text(x, y, text[:text_length], font, ui.FG, ui.BG)
    x += text_width
    ui.display.text(x, y, "...", ui.BOLD, ui.GREY, ui.BG)


class ConfirmContent(ui.Control):
    def __init__(self, state: State, font=ui.NORMAL) -> None:
        self.state = state
        self.repaint = True
        self.font = font

    def on_render(self) -> None:
        if self.repaint:
            ui.header(
                self.state.get_header(), ui.ICON_DEFAULT, ui.GREEN, ui.BG, ui.GREEN
            )
            ui.display.image((ui.WIDTH - 64) // 2, 48, self.state.app_icon)

            app_name = self.state.app_name
            user_name = self.state.user_name()
            if app_name is not None and user_name is not None and app_name != user_name:
                text_center_trim_left(ui.WIDTH // 2, 140, app_name)
                text_center_trim_right(ui.WIDTH // 2, 172, user_name)
            elif user_name is not None:
                text_center_trim_right(ui.WIDTH // 2, 156, user_name)
            elif app_name is not None:
                text_center_trim_left(ui.WIDTH // 2, 156, app_name)

            self.repaint = False


def dispatch_cmd(req: Cmd, dialog_mgr: DialogManager) -> Cmd:
    if req.cmd == _CMD_MSG:
        m = req.to_msg()

        if m.cla != 0:
            if __debug__:
                log.warning(__name__, "_SW_CLA_NOT_SUPPORTED")
            return msg_error(req.cid, _SW_CLA_NOT_SUPPORTED)

        if m.lc + _APDU_DATA > len(req.data):
            if __debug__:
                log.warning(__name__, "_SW_WRONG_LENGTH")
            return msg_error(req.cid, _SW_WRONG_LENGTH)

        if m.ins == _MSG_REGISTER:
            if __debug__:
                log.debug(__name__, "_MSG_REGISTER")
            return msg_register(m, dialog_mgr)
        elif m.ins == _MSG_AUTHENTICATE:
            if __debug__:
                log.debug(__name__, "_MSG_AUTHENTICATE")
            return msg_authenticate(m, dialog_mgr)
        elif m.ins == _MSG_VERSION:
            if __debug__:
                log.debug(__name__, "_MSG_VERSION")
            return msg_version(m)
        else:
            if __debug__:
                log.warning(__name__, "_SW_INS_NOT_SUPPORTED: %d", m.ins)
            return msg_error(req.cid, _SW_INS_NOT_SUPPORTED)

    elif req.cmd == _CMD_INIT:
        if __debug__:
            log.debug(__name__, "_CMD_INIT")
        return cmd_init(req)
    elif req.cmd == _CMD_PING:
        if __debug__:
            log.debug(__name__, "_CMD_PING")
        return req
    elif req.cmd == _CMD_WINK:
        if __debug__:
            log.debug(__name__, "_CMD_WINK")
        loop.schedule(ui.alert())
        return req
    elif req.cmd == _CMD_CBOR:
        if req.data[0] == _CBOR_MAKE_CREDENTIAL:
            if __debug__:
                log.debug(__name__, "_CBOR_MAKE_CREDENTIAL")
            return cbor_make_credential(req, dialog_mgr)
        elif req.data[0] == _CBOR_GET_ASSERTION:
            if __debug__:
                log.debug(__name__, "_CBOR_GET_ASSERTION")
            return cbor_get_assertion(req, dialog_mgr)
        elif req.data[0] == _CBOR_GET_INFO:
            if __debug__:
                log.debug(__name__, "_CBOR_GET_INFO")
            return cbor_get_info(req)
        elif req.data[0] == _CBOR_CLIENT_PIN:
            if __debug__:
                log.debug(__name__, "_CBOR_CLIENT_PIN")
            return cbor_client_pin(req)
        elif req.data[0] == _CBOR_RESET:
            if __debug__:
                log.debug(__name__, "_CBOR_RESET")
            return cbor_reset(req, dialog_mgr)
        elif req.data[0] == _CBOR_GET_NEXT_ASSERTION:
            if __debug__:
                log.debug(__name__, "_CBOR_GET_NEXT_ASSERTION")
            return cbor_error(req.cid, _ERR_NOT_ALLOWED)
        else:
            if __debug__:
                log.warning(__name__, "_ERR_INVALID_CMD _CMD_CBOR %d", req.data[0])
            return cbor_error(req.cid, _ERR_INVALID_CMD)

    elif req.cmd == _CMD_CANCEL:
        if __debug__:
            log.debug(__name__, "_CMD_CANCEL")
        dialog_mgr.reset()
        return req
    else:
        if __debug__:
            log.warning(__name__, "_ERR_INVALID_CMD: %d", req.cmd)
        return cmd_error(req.cid, _ERR_INVALID_CMD)


def cmd_init(req: Cmd) -> Cmd:
    if req.cid == 0:
        return cmd_error(req.cid, _ERR_INVALID_CID)
    elif req.cid == _CID_BROADCAST:
        # uint32_t except 0 and 0xffffffff
        resp_cid = random.uniform(0xFFFFFFFE) + 1
    else:
        resp_cid = req.cid

    buf, resp = make_struct(resp_cmd_init())
    utils.memcpy(resp.nonce, 0, req.data, 0, len(req.data))
    resp.cid = resp_cid
    resp.versionInterface = _U2FHID_IF_VERSION
    resp.versionMajor = 2
    resp.versionMinor = 0
    resp.versionBuild = 0
    resp.capFlags = _CAPFLAG_WINK | _CAPFLAG_CBOR

    return Cmd(req.cid, req.cmd, buf)


def msg_register(req: Msg, dialog_mgr: DialogManager) -> Cmd:
    if not storage.is_initialized():
        if __debug__:
            log.warning(__name__, "not initialized")
        return msg_error(req.cid, _SW_CONDITIONS_NOT_SATISFIED)

    # check length of input data
    if len(req.data) != 64:
        if __debug__:
            log.warning(__name__, "_SW_WRONG_LENGTH req.data")
        return msg_error(req.cid, _SW_WRONG_LENGTH)

    # parse challenge and app_id
    chal = req.data[:32]
    app_id = req.data[32:]

    # check equality with last request
    new_state = U2fConfirmRegister(req.cid, req.data, app_id)
    if not dialog_mgr.compare(new_state):
        if not dialog_mgr.set_state(new_state):
            return msg_error(req.cid, _SW_CONDITIONS_NOT_SATISFIED)
    dialog_mgr.reset_timeout()

    # wait for a button or continue
    if not dialog_mgr.confirmed:
        if __debug__:
            log.info(__name__, "waiting for button")
        return msg_error(req.cid, _SW_CONDITIONS_NOT_SATISFIED)

    # sign the registration challenge and return
    if __debug__:
        log.info(__name__, "signing register")
    buf = msg_register_sign(chal, app_id)

    dialog_mgr.reset()

    return Cmd(req.cid, _CMD_MSG, buf)


def generate_credential(app_id: bytes):
    from apps.common import seed

    # derivation path is m/U2F'/r'/r'/r'/r'/r'/r'/r'/r'
    keypath = [HARDENED | random.uniform(0xF0000000) for _ in range(0, 8)]
    nodepath = [_U2F_KEY_PATH] + keypath

    # prepare signing key from random path, compute decompressed public key
    node = seed.derive_node_without_passphrase(nodepath, "nist256p1")
    pubkey = nist256p1.publickey(node.private_key(), False)

    # first half of keyhandle is keypath
    keybuf = ustruct.pack("<8L", *keypath)

    # second half of keyhandle is a hmac of app_id and keypath
    keybase = hmac.Hmac(node.private_key(), app_id, hashlib.sha256)
    keybase.update(keybuf)
    keybase = keybase.digest()

    return keybuf + keybase, pubkey, node.private_key()


def msg_register_sign(challenge: bytes, app_id: bytes) -> bytes:
    keyhandle, pubkey, _ = generate_credential(app_id)

    # hash the request data together with keyhandle and pubkey
    dig = hashlib.sha256()
    dig.update(b"\x00")  # uint8_t reserved;
    dig.update(app_id)  # uint8_t appId[32];
    dig.update(challenge)  # uint8_t chal[32];
    dig.update(keyhandle)  # uint8_t keyHandle[64];
    dig.update(pubkey)  # uint8_t pubKey[65];
    dig = dig.digest()

    # sign the digest and convert to der
    sig = nist256p1.sign(_U2F_ATT_PRIV_KEY, dig, False)
    sig = der.encode_seq((sig[1:33], sig[33:]))

    # pack to a response
    buf, resp = make_struct(
        resp_cmd_register(len(keyhandle), len(_U2F_ATT_CERT), len(sig))
    )
    resp.registerId = _U2F_REGISTER_ID
    utils.memcpy(resp.pubKey, 0, pubkey, 0, len(pubkey))
    resp.keyHandleLen = len(keyhandle)
    utils.memcpy(resp.keyHandle, 0, keyhandle, 0, len(keyhandle))
    utils.memcpy(resp.cert, 0, _U2F_ATT_CERT, 0, len(_U2F_ATT_CERT))
    utils.memcpy(resp.sig, 0, sig, 0, len(sig))
    resp.status = _SW_NO_ERROR

    return buf


def msg_authenticate(req: Msg, dialog_mgr: DialogManager) -> Cmd:
    if not storage.is_initialized():
        if __debug__:
            log.warning(__name__, "not initialized")
        return msg_error(req.cid, _SW_CONDITIONS_NOT_SATISFIED)

    # we need at least keyHandleLen
    if len(req.data) <= _REQ_CMD_AUTHENTICATE_KHLEN:
        if __debug__:
            log.warning(__name__, "_SW_WRONG_LENGTH req.data")
        return msg_error(req.cid, _SW_WRONG_LENGTH)

    # check keyHandleLen
    khlen = req.data[_REQ_CMD_AUTHENTICATE_KHLEN]
    if khlen != 64:
        if __debug__:
            log.warning(__name__, "_SW_WRONG_LENGTH khlen")
        return msg_error(req.cid, _SW_WRONG_LENGTH)

    auth = overlay_struct(req.data, req_cmd_authenticate(khlen))

    # check the keyHandle and generate the signing key
    node = msg_authenticate_genkey(auth.appId, auth.keyHandle, "<8L")
    if node is None:
        # prior to firmware version 2.0.8, keypath was serialized in a
        # big-endian manner, instead of little endian, like in trezor-mcu.
        # try to parse it as big-endian now and check the HMAC.
        node = msg_authenticate_genkey(auth.appId, auth.keyHandle, ">8L")
    if node is None:
        # specific error logged in msg_authenticate_genkey
        return msg_error(req.cid, _SW_WRONG_DATA)

    # if _AUTH_CHECK_ONLY is requested, return, because keyhandle has been checked already
    if req.p1 == _AUTH_CHECK_ONLY:
        if __debug__:
            log.info(__name__, "_AUTH_CHECK_ONLY")
        return msg_error(req.cid, _SW_CONDITIONS_NOT_SATISFIED)

    # from now on, only _AUTH_ENFORCE is supported
    if req.p1 != _AUTH_ENFORCE:
        if __debug__:
            log.info(__name__, "_AUTH_ENFORCE")
        return msg_error(req.cid, _SW_WRONG_DATA)

    # check equality with last request
    new_state = U2fConfirmAuthenticate(req.cid, req.data, auth.appId)
    if not dialog_mgr.compare(new_state):
        if not dialog_mgr.set_state(new_state):
            return msg_error(req.cid, _SW_CONDITIONS_NOT_SATISFIED)
    dialog_mgr.reset_timeout()

    # wait for a button or continue
    if not dialog_mgr.confirmed:
        if __debug__:
            log.info(__name__, "waiting for button")
        return msg_error(req.cid, _SW_CONDITIONS_NOT_SATISFIED)

    # sign the authentication challenge and return
    if __debug__:
        log.info(__name__, "signing authentication")
    buf = msg_authenticate_sign(auth.chal, auth.appId, node.private_key())

    dialog_mgr.reset()

    return Cmd(req.cid, _CMD_MSG, buf)


def msg_authenticate_genkey(app_id: bytes, keyhandle: bytes, pathformat: str):
    from apps.common import seed

    # unpack the keypath from the first half of keyhandle
    keybuf = keyhandle[:32]
    keypath = ustruct.unpack(pathformat, keybuf)

    # check high bit for hardened keys
    for i in keypath:
        if not i & HARDENED:
            if __debug__:
                log.warning(__name__, "invalid key path")
            return None

    # derive the signing key
    nodepath = [_U2F_KEY_PATH] + list(keypath)
    node = seed.derive_node_without_passphrase(nodepath, "nist256p1")

    # second half of keyhandle is a hmac of app_id and keypath
    keybase = hmac.Hmac(node.private_key(), app_id, hashlib.sha256)
    keybase.update(keybuf)
    keybase = keybase.digest()

    # verify the hmac
    if keybase != keyhandle[32:]:
        if __debug__:
            log.warning(__name__, "invalid key handle")
        return None

    return node


def msg_authenticate_sign(challenge: bytes, app_id: bytes, privkey: bytes) -> bytes:
    flags = bytes([_AUTH_FLAG_UP])

    # get next counter
    ctr = storage.device.next_u2f_counter()
    ctrbuf = ustruct.pack(">L", ctr)

    # hash input data together with counter
    dig = hashlib.sha256()
    dig.update(app_id)  # uint8_t appId[32];
    dig.update(flags)  # uint8_t flags;
    dig.update(ctrbuf)  # uint8_t ctr[4];
    dig.update(challenge)  # uint8_t chal[32];
    dig = dig.digest()

    # sign the digest and convert to der
    sig = nist256p1.sign(privkey, dig, False)
    sig = der.encode_seq((sig[1:33], sig[33:]))

    # pack to a response
    buf, resp = make_struct(resp_cmd_authenticate(len(sig)))
    resp.flags = flags[0]
    resp.ctr = ctr
    utils.memcpy(resp.sig, 0, sig, 0, len(sig))
    resp.status = _SW_NO_ERROR

    return buf


def msg_version(req: Msg) -> Cmd:
    if req.data:
        return msg_error(req.cid, _SW_WRONG_LENGTH)
    return Cmd(req.cid, _CMD_MSG, b"U2F_V2\x90\x00")  # includes _SW_NO_ERROR


def msg_error(cid: int, code: int) -> Cmd:
    return Cmd(cid, _CMD_MSG, ustruct.pack(">H", code))


def cmd_error(cid: int, code: int) -> Cmd:
    return Cmd(cid, _CMD_ERROR, ustruct.pack(">B", code))


def cbor_error(cid: int, code: int) -> Cmd:
    return Cmd(cid, _CMD_CBOR, ustruct.pack(">B", code))


def cbor_make_credential(req: Cmd, dialog_mgr: DialogManager) -> Optional[Cmd]:
    if not storage.is_initialized():
        if __debug__:
            log.warning(__name__, "not initialized")
        return cbor_error(req.cid, _ERR_OPERATION_DENIED)

    try:
        param = cbor.decode(req.data[1:])
        rp_id = param[_MAKECRED_CMD_RP]["id"]
        client_data_hash = param[_MAKECRED_CMD_CLIENT_DATA_HASH]
        user = param[_MAKECRED_CMD_USER]
        user_id = user["id"]
        pub_key_cred_params = param[_MAKECRED_CMD_PUB_KEY_CRED_PARAMS]
        rp_id_hash = hashlib.sha256(rp_id).digest()
    except Exception:
        return cbor_error(req.cid, _ERR_INVALID_CBOR)

    exclude_list = param.get(_MAKECRED_CMD_EXCLUDE_LIST, [])
    try:
        for credential_descriptor in exclude_list:
            cred = Credential.from_id(credential_descriptor["id"], rp_id_hash)
            if credential_descriptor["type"] == "public-key" and cred is not None:
                if not dialog_mgr.set_state(Fido2ConfirmExcluded(req.cid, cred)):
                    return cmd_error(req.cid, _ERR_CHANNEL_BUSY)
                return None
    except Exception:
        return cbor_error(req.cid, _ERR_INVALID_CBOR)

    if _COSE_ALG_ES256 not in (alg.get("alg", None) for alg in pub_key_cred_params):
        return cbor_error(req.cid, _ERR_UNSUPPORTED_ALGORITHM)

    hmac_secret = False
    if _MAKECRED_CMD_EXTENSIONS in param:
        try:
            hmac_secret = param[_MAKECRED_CMD_EXTENSIONS].get("hmac-secret", False)
        except Exception:
            return cbor_error(req.cid, _ERR_INVALID_CBOR)

    if not isinstance(hmac_secret, bool):
        return cbor_error(req.cid, _ERR_INVALID_CBOR)

    if _MAKECRED_CMD_PIN_AUTH in param:
        # Client PIN is not supported
        return cbor_error(req.cid, _ERR_PIN_AUTH_INVALID)

    try:
        options = param.get(_MAKECRED_CMD_OPTIONS, {})
        resident_key = options.get("rk", False)
        user_verification = options.get("uv", False)
    except Exception:
        return cbor_error(req.cid, _ERR_INVALID_CBOR)

    if resident_key and not _ALLOW_RESIDENT_CREDENTIALS:
        return cbor_error(req.cid, _ERR_UNSUPPORTED_OPTION)

    cred = Credential()
    cred.rp_id = rp_id
    cred.rp_name = param[_MAKECRED_CMD_RP].get("name", None)
    cred.user_id = user_id
    cred.user_name = user.get("name", None)
    cred.user_display_name = user.get("displayName", None)
    cred.hmac_secret = hmac_secret

    if user_verification and not config.has_pin():
        state_set = dialog_mgr.set_state(Fido2ConfirmNoPin(req.cid))
    else:
        state_set = dialog_mgr.set_state(
            Fido2ConfirmMakeCredential(req.cid, client_data_hash, cred, resident_key)
        )
    if not state_set:
        return cmd_error(req.cid, _ERR_CHANNEL_BUSY)
    return None


def cbor_make_credential_sign(client_data_hash: bytes, cred: Credential) -> bytes:
    privkey = cred.private_key()
    pubkey = nist256p1.publickey(privkey, False)

    flags = _AUTH_FLAG_UP | _AUTH_FLAG_AT
    if config.has_pin():
        flags |= _AUTH_FLAG_UV

    credential_pub_key = cbor.encode(
        {
            _COSE_ALG_KEY: _COSE_ALG_ES256,
            _COSE_KEY_TYPE_KEY: _COSE_KEY_TYPE_EC2,
            _COSE_CURVE_KEY: _COSE_CURVE_P256,
            _COSE_X_COORD_KEY: pubkey[1:33],
            _COSE_Y_COORD_KEY: pubkey[33:],
        }
    )
    att_cred_data = (
        _AAGUID + len(cred.id).to_bytes(2, "big") + cred.id + credential_pub_key
    )

    extensions = b""
    if cred.hmac_secret:
        extensions = cbor.encode({"hmac-secret": True})
        flags |= _AUTH_FLAG_ED

    rp_id_hash = hashlib.sha256(cred.rp_id).digest()
    authenticator_data = (
        rp_id_hash + bytes([flags]) + b"\x00\x00\x00\x00" + att_cred_data + extensions
    )

    # compute self-attestation signature
    dig = hashlib.sha256()
    dig.update(authenticator_data)
    dig.update(client_data_hash)
    sig = nist256p1.sign(privkey, dig.digest(), False)
    sig = der.encode_seq((sig[1:33], sig[33:]))

    return cbor.encode(
        {
            _MAKECRED_RESP_FMT: "packed",
            _MAKECRED_RESP_AUTH_DATA: authenticator_data,
            _MAKECRED_RESP_ATT_STMT: {"alg": _COSE_ALG_ES256, "sig": sig},
        }
    )


def cbor_get_assertion(req: Cmd, dialog_mgr: DialogManager) -> Optional[Cmd]:
    if not storage.is_initialized():
        if __debug__:
            log.warning(__name__, "not initialized")
        return cbor_error(req.cid, _ERR_OPERATION_DENIED)

    try:
        param = cbor.decode(req.data[1:])
        rp_id = param[_GETASSERT_CMD_RP_ID]
        client_data_hash = param[_GETASSERT_CMD_CLIENT_DATA_HASH]
        rp_id_hash = hashlib.sha256(rp_id).digest()
    except Exception:
        return cbor_error(req.cid, _ERR_INVALID_CBOR)

    allow_list = param.get(_GETASSERT_CMD_ALLOW_LIST, [])
    if allow_list:
        try:
            cred_list = []
            for credential_descriptor in allow_list:
                if credential_descriptor["type"] != "public-key":
                    continue
                cred = Credential.from_id(credential_descriptor["id"], rp_id_hash)
                if cred is not None:
                    cred_list.append(cred)
        except Exception:
            return cbor_error(req.cid, _ERR_INVALID_CBOR)
    else:
        if not _ALLOW_RESIDENT_CREDENTIALS:
            # Resident keys are not supported
            return cbor_error(req.cid, _ERR_UNSUPPORTED_OPTION)
        cred_list = storage.webauthn.get_resident_credentials(rp_id_hash)

    cred_list.sort()

    if _GETASSERT_CMD_PIN_AUTH in param:
        # Client PIN is not supported
        return cbor_error(req.cid, _ERR_PIN_AUTH_INVALID)

    try:
        options = param.get(_GETASSERT_CMD_OPTIONS, {})
        user_presence = options.get("up", True)
        user_verification = options.get("uv", False)
    except Exception:
        return cbor_error(req.cid, _ERR_INVALID_CBOR)

    try:
        hmac_secret = param.get(_GETASSERT_CMD_EXTENSIONS, {}).get("hmac-secret", None)
    except Exception:
        return cbor_error(req.cid, _ERR_INVALID_CBOR)

    if user_verification and not config.has_pin():
        state_set = dialog_mgr.set_state(Fido2ConfirmNoPin(req.cid))
    elif not cred_list:
        if user_presence:
            state_set = dialog_mgr.set_state(Fido2ConfirmNoCredentials(req.cid, rp_id))
        else:
            return cbor_error(req.cid, _ERR_NO_CREDENTIALS)
    elif not user_presence:
        try:
            response_data = cbor_get_assertion_sign(
                client_data_hash, rp_id_hash, cred_list[0], hmac_secret, user_presence
            )
            return Cmd(req.cid, _CMD_CBOR, bytes([_ERR_NONE]) + response_data)
        except Exception:
            return cbor_error(req.cid, _ERR_OPERATION_DENIED)
    else:
        state_set = dialog_mgr.set_state(
            Fido2ConfirmGetAssertion(req.cid, client_data_hash, cred_list, hmac_secret)
        )
    if not state_set:
        return cmd_error(req.cid, _ERR_CHANNEL_BUSY)
    return None


def cbor_get_assertion_hmac_secret(cred: Credential, hmac_secret: map) -> bytes:
    key_agreement = hmac_secret[1]
    salt_enc = hmac_secret[2]
    salt_auth = hmac_secret[3]
    x = key_agreement[_COSE_X_COORD_KEY]
    y = key_agreement[_COSE_Y_COORD_KEY]
    if (
        key_agreement[_COSE_ALG_KEY] != _COSE_ALG_ES256
        or key_agreement[_COSE_KEY_TYPE_KEY] != _COSE_KEY_TYPE_EC2
        or key_agreement[_COSE_CURVE_KEY] != _COSE_CURVE_P256
        or len(x) != 32
        or len(y) != 32
        or len(salt_enc) not in (32, 64)
    ):
        raise ValueError

    ecdh_result = nist256p1.multiply(_KEY_AGREEMENT_PRIVKEY, b"\04" + x + y)
    shared_secret = hashlib.sha256(ecdh_result[1:33]).digest()
    if hmac.Hmac(shared_secret, salt_enc, hashlib.sha256).digest()[:16] != salt_auth:
        raise ValueError

    salt = aes(aes.CBC, shared_secret).decrypt(salt_enc)

    cred_random = cred.cred_random()
    output = hmac.Hmac(cred_random, salt[:32], hashlib.sha256).digest()
    if len(salt) == 64:
        output += hmac.Hmac(cred_random, salt[32:], hashlib.sha256).digest()
    return aes(aes.CBC, shared_secret).encrypt(output)


def cbor_get_assertion_sign(
    client_data_hash: bytes,
    rp_id_hash: bytes,
    cred: Credential,
    hmac_secret: map,
    user_presence=True,
) -> bytes:
    flags = 0
    if user_presence:
        flags |= _AUTH_FLAG_UP
    if config.has_pin():
        flags |= _AUTH_FLAG_UV

    extensions = b""
    if hmac_secret:
        extensions = cbor.encode(
            {"hmac-secret": cbor_get_assertion_hmac_secret(cred.id, hmac_secret)}
        )
        flags |= _AUTH_FLAG_ED

    auth_data = rp_id_hash + bytes([flags]) + b"\x00\x00\x00\x00" + extensions
    dig = hashlib.sha256()
    dig.update(auth_data)
    dig.update(client_data_hash)
    dig = dig.digest()

    # sign the digest and convert to der
    privkey = cred.private_key()
    sig = nist256p1.sign(privkey, dig, False)
    sig = der.encode_seq((sig[1:33], sig[33:]))

    response_data = {
        _GETASSERT_RESP_CREDENTIAL: {"type": "public-key", "id": cred.id},
        _GETASSERT_RESP_AUTH_DATA: auth_data,
        _GETASSERT_RESP_SIGNATURE: sig,
        _GETASSERT_RESP_USER: {"id": cred.user_id},
    }
    return cbor.encode(response_data)


def cbor_get_info(req: Cmd) -> Cmd:
    response_data = {
        _GETINFO_RESP_VERSIONS: ["FIDO_2_0"],
        _GETINFO_RESP_EXTENSIONS: ["hmac-secret"],
        _GETINFO_RESP_AAGUID: _AAGUID,
        _GETINFO_RESP_OPTIONS: {
            "rk": _ALLOW_RESIDENT_CREDENTIALS,
            "up": True,
            "uv": config.has_pin(),
        },
    }
    return Cmd(req.cid, _CMD_CBOR, bytes([_ERR_NONE]) + cbor.encode(response_data))


def cbor_client_pin(req: Cmd) -> Cmd:
    try:
        param = cbor.decode(req.data[1:])
        pin_protocol = param[_CLIENTPIN_CMD_PIN_PROTOCOL]
        subcommand = param[_CLIENTPIN_CMD_SUBCOMMAND]
    except Exception:
        return cbor_error(req.cid, _ERR_INVALID_CBOR)

    if pin_protocol != 1:
        return cbor_error(req.cid, _ERR_PIN_AUTH_INVALID)

    if subcommand != _CLIENTPIN_SUBCMD_GET_KEY_AGREEMENT:
        return cbor_error(req.cid, _ERR_UNSUPPORTED_OPTION)

    response_data = {
        _CLIENTPIN_RESP_KEY_AGREEMENT: {
            _COSE_ALG_KEY: _COSE_ALG_ES256,
            _COSE_KEY_TYPE_KEY: _COSE_KEY_TYPE_EC2,
            _COSE_CURVE_KEY: _COSE_CURVE_P256,
            _COSE_X_COORD_KEY: _KEY_AGREEMENT_PUBKEY[1:33],
            _COSE_Y_COORD_KEY: _KEY_AGREEMENT_PUBKEY[33:],
        }
    }

    return Cmd(req.cid, _CMD_CBOR, bytes([_ERR_NONE]) + cbor.encode(response_data))


def cbor_reset(req: Cmd, dialog_mgr: DialogManager) -> Optional[Cmd]:
    if not storage.is_initialized():
        if __debug__:
            log.warning(__name__, "not initialized")
        return cbor_error(req.cid, _ERR_OPERATION_DENIED)

    if not dialog_mgr.set_state(Fido2ConfirmReset(req.cid)):
        return cmd_error(req.cid, _ERR_CHANNEL_BUSY)
    return None


def cmd_keepalive(cid: int, status: int) -> Cmd:
    return Cmd(cid, _CMD_KEEPALIVE, bytes([status]))
