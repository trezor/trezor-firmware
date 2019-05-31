import uctypes
import ustruct
import utime
from micropython import const

from trezor import config, io, log, loop, ui, utils, workflow
from trezor.crypto import der, hashlib, hmac, random
from trezor.crypto.curve import nist256p1
from trezor.ui.confirm import CONFIRMED, Confirm
from trezor.ui.text import Text

from apps.common import HARDENED, cbor, storage

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
_GETASSERT_CMD_OPTIONS = const(0x05)  # map, optional
_GETASSERT_CMD_PIN_AUTH = const(0x06)  # bytes, optional

# CBOR GetAssertion response member keys
_GETASSERT_RESP_CREDENTIAL = const(0x01)  # map, optional
_GETASSERT_RESP_AUTH_DATA = const(0x02)  # bytes, required
_GETASSERT_RESP_SIGNATURE = const(0x03)  # bytes, required
_GETASSERT_RESP_PUB_KEY_CREDENTIAL_USER_ENTITY = const(0x04)  # map, optional
_GETASSERT_RESP_NUM_OF_CREDENTIALS = const(0x05)  # int, optional

# CBOR GetInfo response member keys
_GETINFO_RESP_VERSIONS = const(0x01)  # array of str, required
_GETINFO_RESP_AAGUID = const(0x03)  # bytes(16), required
_GETINFO_RESP_OPTIONS = const(0x04)  # map, optional

# status codes for the keepalive cmd
_KEEPALIVE_STATUS_PROCESSING = const(0x01)  # still processing the current request
_KEEPALIVE_STATUS_UP_NEEDED = const(0x02)  # waiting for user presence

# time intervals and timeouts
_KEEPALIVE_INTERVAL_MS = const(80)  # interval between keepalive commands
_U2F_CONFIRM_TIMEOUT_MS = const(10 * 1000)
_FIDO2_CONFIRM_TIMEOUT_MS = const(30 * 1000)

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

# register response
_U2F_KEY_PATH = const(0x80553246)
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

    def get_dialog(self):
        content = ConfirmContent(self)
        return Confirm(content)

    def get_text(self):
        return ""

    def keepalive_status(self):
        return None

    def timeout_ms(self):
        return _U2F_CONFIRM_TIMEOUT_MS

    def boot(self) -> None:
        from trezor import res
        from apps.webauthn import knownapps

        try:
            namepart = knownapps.knownapps[self.app_id].lower().replace(" ", "_")
            icon = res.load("apps/webauthn/res/icon_%s.toif" % namepart)
        except Exception as e:
            icon = res.load("apps/webauthn/res/icon_webauthn.toif")
            if __debug__:
                log.exception(__name__, e)
        self.app_icon = icon

    def on_confirm(self):
        return None

    def on_decline(self):
        return None

    def on_timeout(self):
        return self.on_decline()


class U2fState(State):
    def __init__(self, cid: int, checksum: bytes, app_id: bytes) -> None:
        super(U2fState, self).__init__(cid)
        self.app_id = bytes(app_id)  # could be bytearray, which doesn't have __hash__
        self.app_name = None
        self.app_icon = None
        self.checksum = checksum
        self.boot()

    def get_text(self):
        return [self.app_name]

    def boot(self) -> None:
        super(U2fState, self).boot()
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
            return Confirm(text)
        else:
            return super(U2fConfirmRegister, self).get_dialog()

    def get_header(self):
        return "U2F Register"

    def __eq__(self, other) -> bool:
        return isinstance(other, U2fConfirmRegister) and self.checksum == other.checksum


class U2fConfirmAuthenticate(U2fState):
    def __init__(self, cid: int, checksum: bytes, app_id: bytes) -> None:
        super(U2fConfirmAuthenticate, self).__init__(cid, checksum, app_id)

    def get_header(self):
        return "U2F Authenticate"

    def __eq__(self, other) -> bool:
        return (
            isinstance(other, U2fConfirmAuthenticate)
            and self.checksum == other.checksum
        )


class Fido2State(State):
    def __init__(self, cid: int, client_data_hash: bytes, rp_id: str) -> None:
        super(Fido2State, self).__init__(cid)
        self.client_data_hash = client_data_hash
        self.rp_id = rp_id
        self.app_id = hashlib.sha256(rp_id).digest()
        self.boot()

    def keepalive_status(self):
        return _KEEPALIVE_STATUS_UP_NEEDED

    def timeout_ms(self):
        return _FIDO2_CONFIRM_TIMEOUT_MS


class Fido2ConfirmMakeCredential(Fido2State):
    def __init__(
        self, cid: int, client_data_hash: bytes, rp_id: str, account_name: str
    ) -> None:
        super(Fido2ConfirmMakeCredential, self).__init__(cid, client_data_hash, rp_id)
        self.account_name = account_name

    def get_header(self):
        return "FIDO2 Register"

    def get_text(self):
        return [self.rp_id, self.account_name]

    def on_confirm(self):
        response_data = cbor_make_credential_sign(
            self.client_data_hash, hashlib.sha256(self.rp_id).digest()
        )
        return Cmd(self.cid, _CMD_CBOR, bytes([_ERR_NONE]) + response_data)

    def on_decline(self):
        return cbor_error(self.cid, _ERR_OPERATION_DENIED)


class Fido2ConfirmGetAssertion(Fido2State):
    def __init__(
        self, cid: int, client_data_hash: bytes, rp_id: str, credentials
    ) -> None:
        super(Fido2ConfirmGetAssertion, self).__init__(cid, client_data_hash, rp_id)
        self.credentials = credentials

    def get_header(self):
        return "FIDO2 Authenticate"

    def get_text(self):
        return [self.rp_id]

    def on_confirm(self):
        # TODO Ask user to select credential from a list.
        credential_id = self.credentials[0][0]
        node = self.credentials[0][1]
        response_data = cbor_get_assertion_sign(
            self.client_data_hash,
            hashlib.sha256(self.rp_id).digest(),
            credential_id,
            node,
        )
        return Cmd(self.cid, _CMD_CBOR, bytes([_ERR_NONE]) + response_data)

    def on_decline(self):
        return cbor_error(self.cid, _ERR_OPERATION_DENIED)


class Fido2ConfirmExcluded(Fido2State):
    def __init__(self, cid: int, client_data_hash: bytes, rp_id: str) -> None:
        super(Fido2ConfirmExcluded, self).__init__(cid, client_data_hash, rp_id)

    def get_header(self):
        return "FIDO2 Register"

    def get_text(self):
        return [self.rp_id, "This token is", "already registered"]

    def get_dialog(self):
        content = ConfirmContent(self)
        return Confirm(content, confirm=None)

    def on_confirm(self):
        return cbor_error(self.cid, _ERR_CREDENTIAL_EXCLUDED)

    def on_decline(self):
        return cbor_error(self.cid, _ERR_CREDENTIAL_EXCLUDED)


class Fido2ConfirmNoPin(Fido2State):
    def __init__(
        self, cid: int, client_data_hash: bytes, rp_id: str, account_name: str
    ) -> None:
        super(Fido2ConfirmNoPin, self).__init__(cid, client_data_hash, rp_id)
        self.account_name = account_name

    def get_header(self):
        return "FIDO2 Register"

    def get_text(self):
        return [self.rp_id, "PIN not set.", "Unable to verify."]

    def get_dialog(self):
        content = ConfirmContent(self)
        return Confirm(content, confirm=None)

    def on_confirm(self):
        return cbor_error(self.cid, _ERR_OPERATION_DENIED)

    def on_decline(self):
        return cbor_error(self.cid, _ERR_OPERATION_DENIED)


class Fido2ConfirmNoCredentials(Fido2State):
    def __init__(self, cid: int, client_data_hash: bytes, rp_id: str) -> None:
        super(Fido2ConfirmNoCredentials, self).__init__(cid, client_data_hash, rp_id)

    def get_header(self):
        return "FIDO2 Authenticate"

    def get_text(self):
        return [self.rp_id, "Token not registered."]

    def get_dialog(self):
        content = ConfirmContent(self)
        return Confirm(content, confirm=None)

    def on_confirm(self):
        return cbor_error(self.cid, _ERR_NO_CREDENTIALS)

    def on_decline(self):
        return cbor_error(self.cid, _ERR_NO_CREDENTIALS)


class DialogManager:
    def __init__(self, iface: io.HID) -> None:
        self.iface = iface
        self._clear()

    def _clear(self):
        self.state = None
        self.deadline = 0
        self.confirmed = None
        self.workflow = None
        self.keepalive = None

    def reset_timeout(self):
        self.deadline = utime.ticks_ms() + self.state.timeout_ms()

    def reset(self):
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


class ConfirmContent(ui.Control):
    def __init__(self, state: State) -> None:
        self.state = state
        self.repaint = True

    def on_render(self) -> None:
        if self.repaint:
            ui.header(
                self.state.get_header(), ui.ICON_DEFAULT, ui.GREEN, ui.BG, ui.GREEN
            )
            ui.display.image((ui.WIDTH - 64) // 2, 48, self.state.app_icon)
            text_top = 112
            text_bot = 188
            text_height = ui.SIZE
            text = self.state.get_text()
            text_sep = (text_bot - text_top - len(text) * text_height) / (len(text) + 1)
            for i, line in enumerate(text):
                ui.display.text_center(
                    ui.WIDTH // 2,
                    int(text_top + (text_sep + text_height) * (i + 1) - 4),
                    line,
                    ui.MONO,
                    ui.FG,
                    ui.BG,
                )
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
            return cbor_error(req.cid, _ERR_INVALID_CMD)
        elif req.data[0] == _CBOR_RESET:
            if __debug__:
                log.debug(__name__, "_CBOR_RESET")
            return cbor_error(req.cid, _ERR_INVALID_CMD)
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


def cbor_make_credential(req: Cmd, dialog_mgr: DialogManager) -> Cmd:
    from ubinascii import hexlify

    try:
        param = cbor.decode(req.data[1:])
        rp_id = param[_MAKECRED_CMD_RP]["id"]
        client_data_hash = param[_MAKECRED_CMD_CLIENT_DATA_HASH]
        user = param[_MAKECRED_CMD_USER]
        account_id = user["id"]
        pub_key_cred_params = param[_MAKECRED_CMD_PUB_KEY_CRED_PARAMS]
        rp_id_hash = hashlib.sha256(rp_id).digest()
    except Exception:
        return cbor_error(req.cid, _ERR_INVALID_CBOR)

    if _MAKECRED_CMD_EXCLUDE_LIST in param:
        try:
            for credential in param[_MAKECRED_CMD_EXCLUDE_LIST]:
                if (
                    credential["type"] == "public-key"
                    and get_node(rp_id_hash, credential["id"]) is not None
                ):
                    if not dialog_mgr.set_state(
                        Fido2ConfirmExcluded(req.cid, client_data_hash, rp_id)
                    ):
                        return cmd_error(req.cid, _ERR_CHANNEL_BUSY)
                    return None
        except Exception:
            return cbor_error(req.cid, _ERR_INVALID_CBOR)

    if _COSE_ALG_ES256 not in (alg.get("alg", None) for alg in pub_key_cred_params):
        return cbor_error(req.cid, _ERR_UNSUPPORTED_ALGORITHM)

    if _GETASSERT_CMD_PIN_AUTH in param:
        # Client PIN is not supported
        return cbor_error(req.cid, _ERR_PIN_AUTH_INVALID)

    user_verification = False
    if _MAKECRED_CMD_OPTIONS in param:
        options = param[_MAKECRED_CMD_OPTIONS]
        if options.get("rk", False):
            # Resident keys are not supported
            return cbor_error(req.cid, _ERR_UNSUPPORTED_OPTION)
        if "uv" in options:
            user_verification = options["uv"]

    if "displayName" in user:
        name = user["displayName"]
    elif "name" in user:
        name = user["name"]
    else:
        name = hexlify(account_id).decode()

    # TODO Store name and account_id in the credential identifier.

    if user_verification and not config.has_pin():
        state_set = dialog_mgr.set_state(
            Fido2ConfirmNoPin(req.cid, client_data_hash, rp_id, name)
        )
    else:
        state_set = dialog_mgr.set_state(
            Fido2ConfirmMakeCredential(req.cid, client_data_hash, rp_id, name)
        )
    if not state_set:
        return cmd_error(req.cid, _ERR_CHANNEL_BUSY)
    return None


def cbor_make_credential_sign(client_data_hash: bytes, rp_id_hash: bytes) -> bytes:
    credential_id, pubkey, privkey = generate_credential(rp_id_hash)

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
        _AAGUID
        + len(credential_id).to_bytes(2, "big")
        + credential_id
        + credential_pub_key
    )

    authenticator_data = (
        rp_id_hash + bytes([flags]) + b"\x00\x00\x00\x00" + att_cred_data
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


def get_node(rp_id_hash: bytes, credential_id: bytes):
    node = msg_authenticate_genkey(rp_id_hash, credential_id, "<8L")
    if node is None:
        # prior to firmware version 2.0.8, keypath was serialized in a
        # big-endian manner, instead of little endian, like in trezor-mcu.
        # try to parse it as big-endian now and check the HMAC.
        node = msg_authenticate_genkey(rp_id_hash, credential_id, ">8L")
    return node


def cbor_get_assertion(req: Cmd, dialog_mgr: DialogManager) -> Cmd:
    try:
        param = cbor.decode(req.data[1:])
        rp_id = param[_GETASSERT_CMD_RP_ID]
        client_data_hash = param[_GETASSERT_CMD_CLIENT_DATA_HASH]
        rp_id_hash = hashlib.sha256(rp_id).digest()
    except Exception:
        return cbor_error(req.cid, _ERR_INVALID_CBOR)

    try:
        allow_list = param[_GETASSERT_CMD_ALLOW_LIST]
    except Exception:
        # Resident keys are not supported
        return cbor_error(req.cid, _ERR_UNSUPPORTED_OPTION)

    try:
        credential_id_list = [
            credential["id"]
            for credential in allow_list
            if credential["type"] == "public-key"
        ]
    except Exception:
        return cbor_error(req.cid, _ERR_INVALID_CBOR)

    if _GETASSERT_CMD_PIN_AUTH in param:
        # Client PIN is not supported
        return cbor_error(req.cid, _ERR_PIN_AUTH_INVALID)

    user_verification = False
    if _GETASSERT_CMD_OPTIONS in param:
        options = param[_GETASSERT_CMD_OPTIONS]
        if "uv" in options:
            user_verification = options["uv"]

    credentials = []
    for credential_id in credential_id_list:
        node = get_node(rp_id_hash, credential_id)
        if node is not None:
            credentials.append((credential_id, node))

    if user_verification and not config.has_pin():
        state_set = dialog_mgr.set_state(
            Fido2ConfirmNoPin(req.cid, client_data_hash, rp_id)
        )
    elif not credentials:
        state_set = dialog_mgr.set_state(
            Fido2ConfirmNoCredentials(req.cid, client_data_hash, rp_id)
        )
    else:
        state_set = dialog_mgr.set_state(
            Fido2ConfirmGetAssertion(req.cid, client_data_hash, rp_id, credentials)
        )
    if not state_set:
        return cmd_error(req.cid, _ERR_CHANNEL_BUSY)
    return None


def cbor_get_assertion_sign(
    client_data_hash: bytes, rp_id_hash: bytes, credential_id: bytes, node
) -> bytes:
    flags = _AUTH_FLAG_UP
    if config.has_pin():
        flags |= _AUTH_FLAG_UV

    # get next counter
    ctr = storage.next_u2f_counter()

    auth_data = rp_id_hash + bytes([flags]) + ctr.to_bytes(4, "big")
    dig = hashlib.sha256()
    dig.update(auth_data)
    dig.update(client_data_hash)
    dig = dig.digest()

    # sign the digest and convert to der
    sig = nist256p1.sign(node.private_key(), dig, False)
    sig = der.encode_seq((sig[1:33], sig[33:]))

    response_data = {
        _GETASSERT_RESP_CREDENTIAL: {"type": "public-key", "id": credential_id},
        _GETASSERT_RESP_AUTH_DATA: auth_data,
        _GETASSERT_RESP_SIGNATURE: sig,
    }
    return cbor.encode(response_data)


def cbor_get_info(req: Cmd) -> Cmd:
    response_data = {
        _GETINFO_RESP_VERSIONS: ["FIDO_2_0", "U2F_V2"],
        _GETINFO_RESP_AAGUID: _AAGUID,
        _GETINFO_RESP_OPTIONS: {"uv": config.has_pin()},
    }
    return Cmd(req.cid, _CMD_CBOR, bytes([_ERR_NONE]) + cbor.encode(response_data))


def cmd_keepalive(cid: int, status: int) -> Cmd:
    return Cmd(cid, _CMD_KEEPALIVE, bytes([status]))
