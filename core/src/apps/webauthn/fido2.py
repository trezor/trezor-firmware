import uctypes
import ustruct
import utime
from micropython import const
from typing import TYPE_CHECKING

import storage.device as storage_device
from trezor import TR, config, io, log, loop, utils, wire, workflow
from trezor.crypto import hashlib
from trezor.crypto.curve import nist256p1
from trezor.ui import Layout
from trezor.ui.layouts import error_popup

from apps.base import set_homescreen
from apps.common import cbor

from . import common
from .credential import Credential, Fido2Credential

if TYPE_CHECKING:
    from typing import Any, Awaitable, Callable, Coroutine, Iterable, Iterator

    from .credential import U2fCredential

    HID = io.HID


_CID_BROADCAST = const(0xFFFF_FFFF)  # broadcast channel id

# types of frame
_TYPE_MASK = const(0x80)  # frame type mask
_TYPE_INIT = const(0x80)  # initial frame identifier
_TYPE_CONT = const(0x00)  # continuation frame identifier

# U2F HID sizes
_HID_RPT_SIZE = const(64)
_FRAME_INIT_SIZE = const(57)
_FRAME_CONT_SIZE = const(59)
_MAX_U2FHID_MSG_PAYLOAD_LEN = const(_FRAME_INIT_SIZE + 128 * _FRAME_CONT_SIZE)
_CMD_INIT_NONCE_SIZE = const(8)

# types of cmd
_CMD_PING = const(0x81)  # echo data through local processor only
_CMD_MSG = const(0x83)  # send U2F message frame
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

# CBOR GetInfo response member keys
_GETINFO_RESP_VERSIONS = const(0x01)  # array of str, required
_GETINFO_RESP_EXTENSIONS = const(0x02)  # array of str, optional
_GETINFO_RESP_AAGUID = const(0x03)  # bytes(16), required
_GETINFO_RESP_OPTIONS = const(0x04)  # map, optional
_GETINFO_RESP_PIN_PROTOCOLS = const(0x06)  # list of unsigned integers, optional
_GETINFO_RESP_MAX_CRED_COUNT_IN_LIST = const(0x07)  # int, optional
_GETINFO_RESP_MAX_CRED_ID_LEN = const(0x08)  # int, optional

# CBOR ClientPin command parameter keys
_CLIENTPIN_CMD_PIN_PROTOCOL = const(0x01)  # unsigned int, required
_CLIENTPIN_CMD_SUBCOMMAND = const(0x02)  # unsigned int, required
_CLIENTPIN_SUBCMD_GET_KEY_AGREEMENT = const(0x02)

# CBOR ClientPin response member keys
_CLIENTPIN_RESP_KEY_AGREEMENT = const(0x01)  # COSE_Key, optional

# status codes for the keepalive cmd
_KEEPALIVE_STATUS_NONE = const(0x00)
_KEEPALIVE_STATUS_PROCESSING = const(0x01)  # still processing the current request
_KEEPALIVE_STATUS_UP_NEEDED = const(0x02)  # waiting for user presence

# time intervals and timeouts
_KEEPALIVE_INTERVAL_MS = const(80)  # interval between keepalive commands
_CTAP_HID_TIMEOUT_MS = const(
    500
)  # maximum interval between CTAP HID continuation frames
_U2F_CONFIRM_TIMEOUT_MS = const(
    3 * 1000
)  # maximum U2F pollling interval, Chrome uses 200 ms
_FIDO2_CONFIRM_TIMEOUT_MS = const(60 * 1000)
_POPUP_TIMEOUT_MS = const(4 * 1000)
_UV_CACHE_TIME_MS = const(3 * 60 * 1000)  # user verification cache time

# hid error codes
_ERR_NONE = const(0x00)  # no error
_ERR_INVALID_CMD = const(0x01)  # invalid command
_ERR_INVALID_LEN = const(0x03)  # invalid message length
_ERR_INVALID_SEQ = const(0x04)  # invalid message sequencing
_ERR_MSG_TIMEOUT = const(0x05)  # message has timed out
_ERR_CHANNEL_BUSY = const(0x06)  # channel busy
_ERR_INVALID_CID = const(0x0B)  # command not allowed on this cid
_ERR_CBOR_UNEXPECTED_TYPE = const(0x11)  # invalid/unexpected CBOR
_ERR_INVALID_CBOR = const(0x12)  # error when parsing CBOR
_ERR_MISSING_PARAMETER = const(0x14)  # missing non-optional parameter
_ERR_CREDENTIAL_EXCLUDED = const(0x19)  # valid credential found in the exclude list
_ERR_UNSUPPORTED_ALGORITHM = const(0x26)  # requested COSE algorithm not supported
_ERR_OPERATION_DENIED = const(0x27)  # user declined or timed out
_ERR_KEY_STORE_FULL = const(0x28)  # internal key storage is full
_ERR_UNSUPPORTED_OPTION = const(0x2B)  # unsupported option
_ERR_INVALID_OPTION = const(0x2C)  # not a valid option for current operation
_ERR_KEEPALIVE_CANCEL = const(0x2D)  # pending keep alive was cancelled
_ERR_NO_CREDENTIALS = const(0x2E)  # no valid credentials provided
_ERR_NOT_ALLOWED = const(0x30)  # continuation command not allowed
_ERR_PIN_AUTH_INVALID = const(0x33)  # pinAuth verification failed
_ERR_OTHER = const(0x7F)  # other unspecified error
_ERR_EXTENSION_FIRST = const(0xE0)  # extension specific error

# command status responses
_SW_NO_ERROR = const(0x9000)
_SW_WRONG_LENGTH = const(0x6700)
_SW_CONDITIONS_NOT_SATISFIED = const(0x6985)
_SW_WRONG_DATA = const(0x6A80)
_SW_INS_NOT_SUPPORTED = const(0x6D00)
_SW_CLA_NOT_SUPPORTED = const(0x6E00)

# init response
_CAPFLAG_WINK = const(0x01)  # device supports _CMD_WINK
_CAPFLAG_CBOR = const(0x04)  # device supports _CMD_CBOR
_U2FHID_IF_VERSION = const(2)  # interface version

# register response
_U2F_REGISTER_ID = const(0x05)  # version 2 registration identifier
_FIDO_ATT_PRIV_KEY = b"q&\xac+\xf6D\xdca\x86\xad\x83\xef\x1f\xcd\xf1*W\xb5\xcf\xa2\x00\x0b\x8a\xd0'\xe9V\xe8T\xc5\n\x8b"
_FIDO_ATT_CERT = b"0\x82\x01\xcd0\x82\x01s\xa0\x03\x02\x01\x02\x02\x04\x03E`\xc40\n\x06\x08*\x86H\xce=\x04\x03\x020.1,0*\x06\x03U\x04\x03\x0c#Trezor FIDO Root CA Serial 841513560 \x17\r200406100417Z\x18\x0f20500406100417Z0x1\x0b0\t\x06\x03U\x04\x06\x13\x02CZ1\x1c0\x1a\x06\x03U\x04\n\x0c\x13SatoshiLabs, s.r.o.1\"0 \x06\x03U\x04\x0b\x0c\x19Authenticator Attestation1'0%\x06\x03U\x04\x03\x0c\x1eTrezor FIDO EE Serial 548784040Y0\x13\x06\x07*\x86H\xce=\x02\x01\x06\x08*\x86H\xce=\x03\x01\x07\x03B\x00\x04\xd9\x18\xbd\xfa\x8aT\xac\x92\xe9\r\xa9\x1f\xcaz\xa2dT\xc0\xd1s61M\xde\x83\xa5K\x86\xb5\xdfN\xf0Re\x9a\x1do\xfc\xb7F\x7f\x1a\xcd\xdb\x8a3\x08\x0b^\xed\x91\x89\x13\xf4C\xa5&\x1b\xc7{h`o\xc1\xa33010!\x06\x0b+\x06\x01\x04\x01\x82\xe5\x1c\x01\x01\x04\x04\x12\x04\x10\xd6\xd0\xbd\xc3b\xee\xc4\xdb\xde\x8dzenJD\x870\x0c\x06\x03U\x1d\x13\x01\x01\xff\x04\x020\x000\n\x06\x08*\x86H\xce=\x04\x03\x02\x03H\x000E\x02 \x0b\xce\xc4R\xc3\n\x11'\xe5\xd5\xf5\xfc\xf5\xd6Wy\x11+\xe50\xad\x9d-TXJ\xbeE\x86\xda\x93\xc6\x02!\x00\xaf\xca=\xcf\xd8A\xb0\xadz\x9e$}\x0ff\xf4L,\x83\xf9T\xab\x95O\x896\xc15\x08\x7fX\xf1\x95"
_BOGUS_RP_ID = ".dummy"
_BOGUS_APPID_CHROME = b"A" * 32
_BOGUS_APPID_FIREFOX = b"\0" * 32
_BOGUS_APPIDS = (_BOGUS_APPID_CHROME, _BOGUS_APPID_FIREFOX)
_AAGUID = b"\xd6\xd0\xbd\xc3b\xee\xc4\xdb\xde\x8dzenJD\x87"  # First 16 bytes of SHA-256("TREZOR 2")

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

# Dialog results
_RESULT_NONE = const(0)
_RESULT_CONFIRM = const(1)  # User confirmed.
_RESULT_DECLINE = const(2)  # User declined.
_RESULT_CANCEL = const(3)  # Request was cancelled by _CMD_CANCEL.
_RESULT_TIMEOUT = const(4)  # Request exceeded _FIDO2_CONFIRM_TIMEOUT_MS.

# FIDO2 configuration.
_ALLOW_FIDO2 = const(1)
_ALLOW_RESIDENT_CREDENTIALS = const(1)
_ALLOW_WINK = const(0)

# The default attestation type to use in MakeCredential responses. If false, then basic attestation will be used by default.
_DEFAULT_USE_SELF_ATTESTATION = const(1)

# The default value of the use_sign_count flag for newly created credentials.
_DEFAULT_USE_SIGN_COUNT = const(1)

# The maximum number of credential IDs that can be supplied in the GetAssertion allow list.
_MAX_CRED_COUNT_IN_LIST = const(10)

# The CID of the last WINK command. Used to ensure that we do only one WINK at a time on any given CID.
_last_wink_cid = 0

# Indicates whether the last U2F_AUTHENTICATE or CBOR_GET_ASSERTION had a valid key handle / credential ID.
_last_auth_valid = False


class CborError(Exception):
    def __init__(self, code: int) -> None:
        super().__init__()
        self.code = code


def frame_init() -> uctypes.StructDict:
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


def frame_cont() -> uctypes.StructDict:
    # uint32_t cid;                     // Channel identifier
    # uint8_t seq;                      // Sequence number - b7 cleared
    # uint8_t data[HID_RPT_SIZE - 5];   // Data payload
    return {
        "cid": 0 | uctypes.UINT32,
        "seq": 4 | uctypes.UINT8,
        "data": (5 | uctypes.ARRAY, (_HID_RPT_SIZE - 5) | uctypes.UINT8),
    }


def _resp_cmd_init() -> uctypes.StructDict:
    UINT8 = uctypes.UINT8  # local_cache_attribute
    # uint8_t nonce[8];         // Client application nonce
    # uint32_t cid;             // Channel identifier
    # uint8_t versionInterface; // Interface version
    # uint8_t versionMajor;     // Major version number
    # uint8_t versionMinor;     // Minor version number
    # uint8_t versionBuild;     // Build version number
    # uint8_t capFlags;         // Capabilities flags
    return {
        "nonce": (0 | uctypes.ARRAY, 8 | UINT8),
        "cid": 8 | uctypes.UINT32,
        "versionInterface": 12 | UINT8,
        "versionMajor": 13 | UINT8,
        "versionMinor": 14 | UINT8,
        "versionBuild": 15 | UINT8,
        "capFlags": 16 | UINT8,
    }


def _resp_cmd_register(khlen: int, certlen: int, siglen: int) -> dict:
    cert_ofs = 67 + khlen
    sig_ofs = cert_ofs + certlen
    status_ofs = sig_ofs + siglen
    UINT8 = uctypes.UINT8  # local_cache_attribute
    ARRAY = uctypes.ARRAY  # local_cache_attribute
    # uint8_t registerId;       // Registration identifier (U2F_REGISTER_ID)
    # uint8_t pubKey[65];       // Generated public key
    # uint8_t keyHandleLen;     // Length of key handle
    # uint8_t keyHandle[khlen]; // Key handle
    # uint8_t cert[certlen];    // Attestation certificate
    # uint8_t sig[siglen];      // Registration signature
    # uint16_t status;
    return {
        "registerId": 0 | UINT8,
        "pubKey": (1 | ARRAY, 65 | UINT8),
        "keyHandleLen": 66 | UINT8,
        "keyHandle": (67 | ARRAY, khlen | UINT8),
        "cert": (cert_ofs | ARRAY, certlen | UINT8),
        "sig": (sig_ofs | ARRAY, siglen | UINT8),
        "status": status_ofs | uctypes.UINT16,
    }


# index of keyHandleLen in req_cmd_authenticate struct
_REQ_CMD_AUTHENTICATE_KHLEN = const(64)


def _req_cmd_authenticate(khlen: int) -> uctypes.StructDict:
    UINT8 = uctypes.UINT8  # local_cache_attribute
    ARRAY = uctypes.ARRAY  # local_cache_attribute
    return {
        "chal": (0 | ARRAY, 32 | UINT8),
        "appId": (32 | ARRAY, 32 | UINT8),
        "keyHandleLen": 64 | UINT8,
        "keyHandle": (65 | ARRAY, khlen | UINT8),
    }


def _resp_cmd_authenticate(siglen: int) -> uctypes.StructDict:
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


def overlay_struct(buf: bytearray, desc: uctypes.StructDict) -> Any:
    desc_size = uctypes.sizeof(desc, uctypes.BIG_ENDIAN)
    if desc_size > len(buf):
        raise ValueError(f"desc is too big ({desc_size} > {len(buf)})")
    return uctypes.struct(uctypes.addressof(buf), desc, uctypes.BIG_ENDIAN)


def make_struct(desc: uctypes.StructDict) -> tuple[bytearray, Any]:
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
        self_data = self.data  # local_cache_attribute

        cla = self_data[_APDU_CLA]
        ins = self_data[_APDU_INS]
        p1 = self_data[_APDU_P1]
        p2 = self_data[_APDU_P2]
        lc = (
            (self_data[_APDU_LC1] << 16)
            + (self_data[_APDU_LC2] << 8)
            + (self_data[_APDU_LC3])
        )
        data = self_data[_APDU_DATA : _APDU_DATA + lc]
        return Msg(self.cid, cla, ins, p1, p2, lc, data)


async def _read_cmd(iface: HID) -> Cmd | None:
    desc_init = frame_init()
    desc_cont = frame_cont()
    read = loop.wait(iface.iface_num() | io.POLL_READ)

    # wait for incoming command indefinitely
    buf = await read
    while True:
        ifrm = overlay_struct(bytearray(buf), desc_init)
        bcnt = ifrm.bcnt
        data = ifrm.data
        datalen = len(data)
        seq = 0
        ifrm_cid = ifrm.cid  # local_cache_attribute
        warning = log.warning  # local_cache_attribute

        if ifrm.cmd & _TYPE_MASK == _TYPE_CONT:
            # unexpected cont packet, abort current msg
            if __debug__:
                warning(__name__, "_TYPE_CONT")
            return None

        if ifrm_cid == 0 or ((ifrm_cid == _CID_BROADCAST) and (ifrm.cmd != _CMD_INIT)):
            # CID 0 is reserved for future use and _CID_BROADCAST is reserved for channel allocation
            await send_cmd(cmd_error(ifrm_cid, _ERR_INVALID_CID), iface)
            return None

        if bcnt > _MAX_U2FHID_MSG_PAYLOAD_LEN:
            # invalid payload length, abort current msg
            if __debug__:
                warning(__name__, "_MAX_U2FHID_MSG_PAYLOAD_LEN")
            await send_cmd(cmd_error(ifrm_cid, _ERR_INVALID_LEN), iface)
            return None

        if datalen < bcnt:
            databuf = bytearray(bcnt)
            utils.memcpy(databuf, 0, data, 0, bcnt)
            data = databuf
        else:
            data = data[:bcnt]

        # set a timeout for subsequent reads
        read.timeout_ms = _CTAP_HID_TIMEOUT_MS
        while datalen < bcnt:
            try:
                buf = await read
            except loop.Timeout:
                if __debug__:
                    warning(__name__, "_ERR_MSG_TIMEOUT")
                await send_cmd(cmd_error(ifrm_cid, _ERR_MSG_TIMEOUT), iface)
                return None

            cfrm = overlay_struct(bytearray(buf), desc_cont)
            cfrm_cid = cfrm.cid  # local_cache_attribute

            if cfrm.seq == _CMD_INIT:
                if cfrm_cid == ifrm_cid:
                    # _CMD_INIT command on current channel, abort current transaction.
                    if __debug__:
                        warning(
                            __name__,
                            "U2FHID: received CMD_INIT command during active tran, aborting",
                        )
                    break
                else:
                    # _CMD_INIT command on different channel, return synchronization response, but continue on current CID.
                    if __debug__:
                        log.info(
                            __name__,
                            "U2FHID: received CMD_INIT command for different CID",
                        )
                    cfrm = overlay_struct(bytearray(buf), desc_init)
                    await send_cmd(
                        cmd_init(
                            Cmd(cfrm_cid, cfrm.cmd, bytes(cfrm.data[: cfrm.bcnt]))
                        ),
                        iface,
                    )
                    continue

            if cfrm_cid != ifrm_cid:
                # Frame for a different channel, continue waiting for next frame on the active CID.
                # For init frames reply with BUSY. Ignore continuation frames.
                if cfrm.seq & _TYPE_MASK == _TYPE_INIT:
                    if __debug__:
                        warning(
                            __name__,
                            "U2FHID: received init frame for different CID, _ERR_CHANNEL_BUSY",
                        )
                    await send_cmd(cmd_error(cfrm_cid, _ERR_CHANNEL_BUSY), iface)
                else:
                    if __debug__:
                        warning(
                            __name__, "U2FHID: received cont frame for different CID"
                        )
                continue

            if cfrm.seq != seq:
                # cont frame for this channel, but incorrect seq number, abort
                # current msg
                if __debug__:
                    warning(__name__, "_ERR_INVALID_SEQ")
                await send_cmd(cmd_error(cfrm_cid, _ERR_INVALID_SEQ), iface)
                return None

            datalen += utils.memcpy(data, datalen, cfrm.data, 0, bcnt - datalen)
            seq += 1
        else:
            return Cmd(ifrm_cid, ifrm.cmd, bytes(data))


async def send_cmd(cmd: Cmd, iface: HID) -> None:
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

    write = loop.wait(
        iface.iface_num() | io.POLL_WRITE, timeout_ms=_CTAP_HID_TIMEOUT_MS
    )
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


def send_cmd_sync(cmd: Cmd, iface: HID) -> None:
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

    while offset < datalen:
        frm.seq = seq
        copied = utils.memcpy(frm.data, 0, cmd.data, offset, datalen)
        offset += copied
        if copied < _FRAME_CONT_SIZE:
            frm.data[copied:] = bytearray(_FRAME_CONT_SIZE - copied)
        iface.write_blocking(buf, 1000)
        seq += 1


async def handle_reports(iface: HID) -> None:
    dialog_mgr = DialogManager(iface)

    while True:
        try:
            req = await _read_cmd(iface)
            if req is None:
                continue
            if not dialog_mgr.allow_cid(req.cid):
                resp: Cmd | None = cmd_error(req.cid, _ERR_CHANNEL_BUSY)
            else:
                resp = _dispatch_cmd(req, dialog_mgr)
            if resp is not None:
                await send_cmd(resp, iface)
        except Exception as e:
            log.exception(__name__, e)


class KeepaliveCallback:
    def __init__(self, cid: int, iface: HID) -> None:
        self.cid = cid
        self.iface = iface

    def __call__(self) -> None:
        send_cmd_sync(cmd_keepalive(self.cid, _KEEPALIVE_STATUS_PROCESSING), self.iface)


async def verify_user(keepalive_callback: KeepaliveCallback) -> bool:
    import trezor.pin
    from trezor.wire import PinCancelled, PinInvalid

    from apps.common.request_pin import verify_user_pin

    try:
        trezor.pin.keepalive_callback = keepalive_callback
        await verify_user_pin(cache_time_ms=_UV_CACHE_TIME_MS)
        ret = True
    except (PinCancelled, PinInvalid):
        ret = False
    finally:
        trezor.pin.keepalive_callback = None

    return ret


def _confirm_fido_choose(title: str, credentials: list[Credential]) -> Awaitable[int]:
    from trezor.ui.layouts.fido import confirm_fido

    from . import knownapps

    assert len(credentials) > 0
    repr_credential = credentials[0]

    if __debug__:
        for cred in credentials:
            assert cred.rp_id_hash == repr_credential.rp_id_hash

    app_name = repr_credential.app_name()
    app = knownapps.by_rp_id_hash(repr_credential.rp_id_hash)
    icon_name = None if app is None else app.icon_name
    return confirm_fido(
        title, app_name, icon_name, [c.account_name() for c in credentials]
    )


async def _confirm_fido(title: str, credential: Credential) -> bool:
    try:
        await _confirm_fido_choose(title, [credential])
        return True
    except wire.ActionCancelled:
        return False


async def _show_error_popup(
    title: str,
    description: str,
    subtitle: str | None = None,
    description_param: str = "",
    *,
    button: str = "",
    timeout_ms: int = 0,
) -> None:
    popup = error_popup(
        title,
        description,
        subtitle,
        description_param,
        button=button,
        timeout_ms=timeout_ms,
    )
    await Layout(popup).get_result()


async def _confirm_bogus_app(title: str) -> None:
    if _last_auth_valid:
        await _show_error_popup(
            title,
            TR.fido__device_already_registered,
            TR.fido__already_registered,
            timeout_ms=_POPUP_TIMEOUT_MS,
        )
    else:
        await _show_error_popup(
            title,
            TR.fido__device_not_registered,
            TR.fido__not_registered,
            timeout_ms=_POPUP_TIMEOUT_MS,
        )


class State:
    def __init__(self, cid: int, iface: HID) -> None:
        self.cid = cid
        self.iface = iface
        self.finished = False

    def allow_cid(self, cid: int) -> bool:
        # Generally allow any CID, because Safari browser changes CID for every U2F message.
        return True

    def keepalive_status(self) -> int:
        # Run the keepalive loop to check for timeout, but do not send any keepalive messages.
        return _KEEPALIVE_STATUS_NONE

    def timeout_ms(self) -> int:
        raise NotImplementedError

    async def confirm_dialog(self) -> "bool | State":
        raise NotImplementedError

    async def on_confirm(self) -> None:
        pass

    async def on_decline(self) -> None:
        pass

    async def on_timeout(self) -> None:
        pass

    async def on_cancel(self) -> None:
        pass


class U2fState(State):
    def __init__(self, cid: int, iface: HID, req_data: bytes, cred: Credential) -> None:
        State.__init__(self, cid, iface)
        self._cred = cred
        self._req_data = req_data

    def timeout_ms(self) -> int:
        return _U2F_CONFIRM_TIMEOUT_MS

    def app_name(self) -> str:
        return self._cred.app_name()

    def account_name(self) -> str | None:
        return self._cred.account_name()


class U2fConfirmRegister(U2fState):
    async def confirm_dialog(self) -> bool:
        if self._cred.rp_id_hash in _BOGUS_APPIDS:
            await _confirm_bogus_app("U2F")
            return False
        else:
            return await _confirm_fido(TR.fido__title_u2f_register, self._cred)

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, U2fConfirmRegister) and self._req_data == other._req_data
        )


class U2fConfirmAuthenticate(U2fState):
    async def confirm_dialog(self) -> bool:
        return await _confirm_fido(TR.fido__title_u2f_auth, self._cred)

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, U2fConfirmAuthenticate)
            and self._req_data == other._req_data
        )


class U2fUnlock(State):
    def timeout_ms(self) -> int:
        return _U2F_CONFIRM_TIMEOUT_MS

    async def confirm_dialog(self) -> bool:
        from trezor.wire import PinCancelled, PinInvalid

        from apps.common.request_pin import verify_user_pin

        try:
            await verify_user_pin()
            set_homescreen()
        except (PinCancelled, PinInvalid):
            return False
        return True

    def __eq__(self, other: object) -> bool:
        return isinstance(other, U2fUnlock)


class Fido2State(State):
    def allow_cid(self, cid: int) -> bool:
        # In FIDO2 lock out other channels until user interaction or timeout.
        return cid == self.cid

    def keepalive_status(self) -> int:
        return _KEEPALIVE_STATUS_UP_NEEDED

    def timeout_ms(self) -> int:
        return _FIDO2_CONFIRM_TIMEOUT_MS

    async def on_confirm(self) -> None:
        cmd = cbor_error(self.cid, _ERR_OPERATION_DENIED)
        await send_cmd(cmd, self.iface)
        self.finished = True

    async def on_decline(self) -> None:
        cmd = cbor_error(self.cid, _ERR_OPERATION_DENIED)
        await send_cmd(cmd, self.iface)
        self.finished = True

    async def on_timeout(self) -> None:
        await self.on_decline()

    async def on_cancel(self) -> None:
        cmd = cbor_error(self.cid, _ERR_KEEPALIVE_CANCEL)
        await send_cmd(cmd, self.iface)
        self.finished = True


class Fido2Unlock(Fido2State):
    def __init__(
        self,
        process_func: Callable[[Cmd, "DialogManager"], State | Cmd],
        req: Cmd,
        dialog_mgr: "DialogManager",
    ) -> None:
        super().__init__(req.cid, dialog_mgr.iface)
        self.process_func = process_func
        self.req = req
        self.resp: Cmd | None = None
        self.dialog_mgr = dialog_mgr

    async def confirm_dialog(self) -> "bool | State":
        if not await verify_user(KeepaliveCallback(self.cid, self.iface)):
            return False

        set_homescreen()
        resp = self.process_func(self.req, self.dialog_mgr)
        if isinstance(resp, State):
            return resp
        else:
            self.resp = resp
            return True

    async def on_confirm(self) -> None:
        if self.resp:
            await send_cmd(self.resp, self.iface)


class Fido2ConfirmMakeCredential(Fido2State):
    def __init__(
        self,
        cid: int,
        iface: HID,
        client_data_hash: bytes,
        cred: Fido2Credential,
        resident: bool,
        user_verification: bool,
    ) -> None:
        Fido2State.__init__(self, cid, iface)
        self._client_data_hash = client_data_hash
        self._cred = cred
        self._resident = resident
        self._user_verification = user_verification

    async def confirm_dialog(self) -> bool:
        if self._cred.rp_id == _BOGUS_RP_ID:
            await _confirm_bogus_app("FIDO2")
            return True
        if not await _confirm_fido(TR.fido__title_register, self._cred):
            return False
        if self._user_verification:
            return await verify_user(KeepaliveCallback(self.cid, self.iface))
        return True

    async def on_confirm(self) -> None:
        from .resident_credentials import store_resident_credential

        cid = self.cid  # local_cache_attribute

        self._cred.generate_id()
        send_cmd_sync(cmd_keepalive(cid, _KEEPALIVE_STATUS_PROCESSING), self.iface)
        response_data = _cbor_make_credential_sign(
            self._client_data_hash, self._cred, self._user_verification
        )

        cmd = Cmd(cid, _CMD_CBOR, bytes([_ERR_NONE]) + response_data)
        if self._resident:
            send_cmd_sync(cmd_keepalive(cid, _KEEPALIVE_STATUS_PROCESSING), self.iface)
            if not store_resident_credential(self._cred):
                cmd = cbor_error(cid, _ERR_KEY_STORE_FULL)
        await send_cmd(cmd, self.iface)
        self.finished = True


class Fido2ConfirmExcluded(Fido2ConfirmMakeCredential):
    def __init__(self, cid: int, iface: HID, cred: Fido2Credential) -> None:
        super().__init__(cid, iface, b"", cred, resident=False, user_verification=False)

    async def on_confirm(self) -> None:
        cmd = cbor_error(self.cid, _ERR_CREDENTIAL_EXCLUDED)
        await send_cmd(cmd, self.iface)
        self.finished = True

        await _show_error_popup(
            TR.fido__title_register,
            TR.fido__device_already_registered_with_template,
            TR.fido__already_registered,
            self._cred.rp_id,  # description_param
            timeout_ms=_POPUP_TIMEOUT_MS,
        )


class Fido2ConfirmGetAssertion(Fido2State):
    def __init__(
        self,
        cid: int,
        iface: HID,
        client_data_hash: bytes,
        creds: list[Credential],
        hmac_secret: dict | None,
        resident: bool,
        user_verification: bool,
    ) -> None:
        Fido2State.__init__(self, cid, iface)
        self._client_data_hash = client_data_hash
        self._creds = creds
        self._hmac_secret = hmac_secret
        self._resident = resident
        self._user_verification = user_verification
        self._selected_cred: Credential | None = None

    async def confirm_dialog(self) -> bool:
        # There is a choice from more than one credential.
        try:
            index = await _confirm_fido_choose(TR.fido__title_authenticate, self._creds)
        except wire.ActionCancelled:
            return False

        self._selected_cred = self._creds[index]
        if self._user_verification:
            return await verify_user(KeepaliveCallback(self.cid, self.iface))
        return True

    async def on_confirm(self) -> None:
        cid = self.cid  # local_cache_attribute

        assert self._selected_cred is not None
        try:
            send_cmd_sync(cmd_keepalive(cid, _KEEPALIVE_STATUS_PROCESSING), self.iface)
            response_data = cbor_get_assertion_sign(
                self._client_data_hash,
                self._selected_cred.rp_id_hash,
                self._selected_cred,
                self._hmac_secret,
                self._resident,
                True,
                self._user_verification,
            )
            cmd = Cmd(cid, _CMD_CBOR, bytes([_ERR_NONE]) + response_data)
        except CborError as e:
            cmd = cbor_error(cid, e.code)
        except KeyError:
            cmd = cbor_error(cid, _ERR_MISSING_PARAMETER)
        except Exception as e:
            # Firmware error.
            if __debug__:
                log.exception(__name__, e)
            cmd = cbor_error(cid, _ERR_OTHER)

        await send_cmd(cmd, self.iface)
        self.finished = True


class Fido2ConfirmNoPin(State):
    def allow_cid(self, cid: int) -> bool:
        # In FIDO2 lock out other channels until user interaction or timeout.
        return cid == self.cid

    def timeout_ms(self) -> int:
        return _FIDO2_CONFIRM_TIMEOUT_MS

    async def confirm_dialog(self) -> bool:
        cmd = cbor_error(self.cid, _ERR_UNSUPPORTED_OPTION)
        await send_cmd(cmd, self.iface)
        self.finished = True

        await _show_error_popup(
            TR.fido__title_verify_user,
            TR.fido__please_enable_pin_protection,
            TR.fido__unable_to_verify_user,
            timeout_ms=_POPUP_TIMEOUT_MS,
        )
        return False


class Fido2ConfirmNoCredentials(Fido2ConfirmGetAssertion):
    def __init__(self, cid: int, iface: HID, rp_id: str) -> None:
        cred = Fido2Credential()
        cred.rp_id = rp_id
        cred.rp_id_hash = hashlib.sha256(rp_id).digest()
        super().__init__(
            cid, iface, b"", [cred], {}, resident=False, user_verification=False
        )

    async def on_confirm(self) -> None:
        cmd = cbor_error(self.cid, _ERR_NO_CREDENTIALS)
        await send_cmd(cmd, self.iface)
        self.finished = True

        await _show_error_popup(
            TR.fido__title_authenticate,
            TR.fido__not_registered_with_template,
            TR.fido__not_registered,
            self._creds[0].app_name(),  # description_param
            timeout_ms=_POPUP_TIMEOUT_MS,
        )


class Fido2ConfirmReset(Fido2State):
    async def confirm_dialog(self) -> bool:
        from trezor.ui.layouts.fido import confirm_fido_reset

        return await confirm_fido_reset()

    async def on_confirm(self) -> None:
        import storage.resident_credentials

        storage.resident_credentials.delete_all()
        cmd = Cmd(self.cid, _CMD_CBOR, bytes([_ERR_NONE]))
        await send_cmd(cmd, self.iface)
        self.finished = True


class DialogManager:
    def __init__(self, iface: HID) -> None:
        self.iface = iface
        self._clear()

    def _clear(self) -> None:
        self.state: State | None = None
        self.deadline = 0
        self.result = _RESULT_NONE
        self.workflow: loop.spawn | None = None
        self.keepalive: Coroutine | None = None

    def _workflow_is_running(self) -> bool:
        return self.workflow is not None and not self.workflow.finished

    def reset_timeout(self) -> None:
        if self.state is not None:
            self.deadline = utime.ticks_add(utime.ticks_ms(), self.state.timeout_ms())

    def reset(self) -> None:
        if self.workflow is not None:
            self.workflow.close()
        if self.keepalive is not None:
            loop.close(self.keepalive)
        self._clear()

    def allow_cid(self, cid: int) -> bool:
        return (
            not self.is_busy()
            or cid == _CID_BROADCAST
            or (self.state is not None and self.state.allow_cid(cid))
        )

    def is_busy(self) -> bool:
        if utime.ticks_diff(utime.ticks_ms(), self.deadline) >= 0:
            self.reset()

        if not self._workflow_is_running():
            return bool(workflow.tasks)

        if self.state is None or self.state.finished:
            self.reset()
            return False

        return True

    def set_state(self, state: State) -> bool:
        if (
            self.state == state
            and utime.ticks_diff(utime.ticks_ms(), self.deadline) < 0
        ):
            self.reset_timeout()
            return True

        if self.is_busy():
            return False

        self.state = state
        self.reset_timeout()
        self.result = _RESULT_NONE
        self.keepalive = self.keepalive_loop()  # TODO: use loop.spawn here
        loop.schedule(self.keepalive)
        self.workflow = workflow.spawn(self.dialog_workflow())
        return True

    async def keepalive_loop(self) -> None:
        state = self.state  # local_cache_attribute

        try:
            if not state:
                return
            while utime.ticks_diff(utime.ticks_ms(), self.deadline) < 0:
                if state.keepalive_status() != _KEEPALIVE_STATUS_NONE:
                    cmd = cmd_keepalive(state.cid, state.keepalive_status())
                    await send_cmd(cmd, self.iface)
                await loop.sleep(_KEEPALIVE_INTERVAL_MS)
        finally:
            self.keepalive = None

        self.result = _RESULT_TIMEOUT
        self.reset()

    async def dialog_workflow(self) -> None:
        if self.state is None:
            return

        try:
            while self.result is _RESULT_NONE:
                workflow.close_others()
                result = await self.state.confirm_dialog()
                if isinstance(result, State):
                    self.state = result
                    self.reset_timeout()
                elif result is True:
                    self.result = _RESULT_CONFIRM
                else:
                    self.result = _RESULT_DECLINE
        finally:
            if self.keepalive is not None:
                loop.close(self.keepalive)
            result = self.result  # local_cache_attribute
            state = self.state  # local_cache_attribute

            if result == _RESULT_CONFIRM:
                await state.on_confirm()
            elif result == _RESULT_CANCEL:
                await state.on_cancel()
            elif result == _RESULT_TIMEOUT:
                await state.on_timeout()
            else:
                await state.on_decline()


def _dispatch_cmd(req: Cmd, dialog_mgr: DialogManager) -> Cmd | None:
    debug = log.debug  # local_cache_attribute
    warning = log.warning  # local_cache_attribute
    cid = req.cid  # local_cache_attribute
    cmd = req.cmd  # local_cache_attribute

    if cmd == _CMD_MSG:
        try:
            m = req.to_msg()
        except IndexError:
            return cmd_error(cid, _ERR_INVALID_LEN)
        ins = m.ins  # local_cache_attribute

        if m.cla != 0:
            if __debug__:
                warning(__name__, "_SW_CLA_NOT_SUPPORTED")
            return msg_error(cid, _SW_CLA_NOT_SUPPORTED)

        if m.lc + _APDU_DATA > len(req.data):
            if __debug__:
                warning(__name__, "_SW_WRONG_LENGTH")
            return msg_error(cid, _SW_WRONG_LENGTH)

        if ins == _MSG_REGISTER:
            if __debug__:
                debug(__name__, "_MSG_REGISTER")
            return _msg_register(m, dialog_mgr)
        elif ins == _MSG_AUTHENTICATE:
            if __debug__:
                debug(__name__, "_MSG_AUTHENTICATE")
            return _msg_authenticate(m, dialog_mgr)
        elif ins == _MSG_VERSION:
            if __debug__:
                debug(__name__, "_MSG_VERSION")
            # msg_version
            if m.data:
                return msg_error(m.cid, _SW_WRONG_LENGTH)
            return Cmd(m.cid, _CMD_MSG, b"U2F_V2\x90\x00")  # includes _SW_NO_ERROR
        else:
            if __debug__:
                warning(__name__, "_SW_INS_NOT_SUPPORTED: %d", ins)
            return msg_error(cid, _SW_INS_NOT_SUPPORTED)

    elif cmd == _CMD_INIT:
        if __debug__:
            debug(__name__, "_CMD_INIT")
        return cmd_init(req)
    elif cmd == _CMD_PING:
        if __debug__:
            debug(__name__, "_CMD_PING")
        return req
    elif cmd == _CMD_WINK and _ALLOW_WINK:
        if __debug__:
            debug(__name__, "_CMD_WINK")
        return _cmd_wink(req)
    elif cmd == _CMD_CBOR and _ALLOW_FIDO2:
        if not req.data:
            return cmd_error(cid, _ERR_INVALID_LEN)
        req_data_first = req.data[0]
        if req_data_first == _CBOR_MAKE_CREDENTIAL:
            if __debug__:
                debug(__name__, "_CBOR_MAKE_CREDENTIAL")
            return _cbor_make_credential(req, dialog_mgr)
        elif req_data_first == _CBOR_GET_ASSERTION:
            if __debug__:
                debug(__name__, "_CBOR_GET_ASSERTION")
            return _cbor_get_assertion(req, dialog_mgr)
        elif req_data_first == _CBOR_GET_INFO:
            if __debug__:
                debug(__name__, "_CBOR_GET_INFO")
            return _cbor_get_info(req)
        elif req_data_first == _CBOR_CLIENT_PIN:
            if __debug__:
                debug(__name__, "_CBOR_CLIENT_PIN")
            return _cbor_client_pin(req)
        elif req_data_first == _CBOR_RESET:
            if __debug__:
                debug(__name__, "_CBOR_RESET")
            return _cbor_reset(req, dialog_mgr)
        elif req_data_first == _CBOR_GET_NEXT_ASSERTION:
            if __debug__:
                debug(__name__, "_CBOR_GET_NEXT_ASSERTION")
            return cbor_error(cid, _ERR_NOT_ALLOWED)
        else:
            if __debug__:
                warning(__name__, "_ERR_INVALID_CMD _CMD_CBOR %d", req_data_first)
            return cbor_error(cid, _ERR_INVALID_CMD)

    elif cmd == _CMD_CANCEL:
        if __debug__:
            debug(__name__, "_CMD_CANCEL")
        dialog_mgr.result = _RESULT_CANCEL
        dialog_mgr.reset()
        return None
    else:
        if __debug__:
            warning(__name__, "_ERR_INVALID_CMD: %d", cmd)
        return cmd_error(cid, _ERR_INVALID_CMD)


def cmd_init(req: Cmd) -> Cmd:
    from trezor.crypto import random

    cid = req.cid  # local_cache_attribute

    if cid == _CID_BROADCAST:
        # uint32_t except 0 and 0xffff_ffff
        resp_cid = random.uniform(0xFFFF_FFFE) + 1
    else:
        resp_cid = cid

    if len(req.data) != _CMD_INIT_NONCE_SIZE:
        return cmd_error(cid, _ERR_INVALID_LEN)

    buf, resp = make_struct(_resp_cmd_init())
    utils.memcpy(resp.nonce, 0, req.data, 0, len(req.data))
    resp.cid = resp_cid
    resp.versionInterface = _U2FHID_IF_VERSION
    resp.versionMajor = 2
    resp.versionMinor = 0
    resp.versionBuild = 0
    resp.capFlags = (_CAPFLAG_WINK * _ALLOW_WINK) | _CAPFLAG_CBOR

    return Cmd(cid, req.cmd, bytes(buf))


def _cmd_wink(req: Cmd) -> Cmd:
    from trezor import ui

    global _last_wink_cid
    if _last_wink_cid != req.cid:
        _last_wink_cid = req.cid
        ui.alert()
    return req


def _msg_register(req: Msg, dialog_mgr: DialogManager) -> Cmd:
    from .credential import U2fCredential

    cid = req.cid  # local_cache_attribute
    data = req.data  # local_cache_attribute

    if not config.is_unlocked():
        new_state: State = U2fUnlock(cid, dialog_mgr.iface)
        dialog_mgr.set_state(new_state)
        return msg_error(cid, _SW_CONDITIONS_NOT_SATISFIED)

    if not storage_device.is_initialized():
        if __debug__:
            log.warning(__name__, "not initialized")
        # There is no standard way to decline a U2F request, but responding with ERR_CHANNEL_BUSY
        # doesn't seem to violate the protocol and at least stops Chrome from polling.
        return cmd_error(cid, _ERR_CHANNEL_BUSY)

    # check length of input data
    if len(data) != 64:
        if __debug__:
            log.warning(__name__, "_SW_WRONG_LENGTH req_data")
        return msg_error(cid, _SW_WRONG_LENGTH)

    # parse challenge and rp_id_hash
    chal = data[:32]
    cred = U2fCredential()
    cred.rp_id_hash = data[32:]
    cred.generate_key_handle()

    # check equality with last request
    new_state = U2fConfirmRegister(cid, dialog_mgr.iface, data, cred)
    if not dialog_mgr.set_state(new_state):
        return msg_error(cid, _SW_CONDITIONS_NOT_SATISFIED)

    # wait for a button or continue
    if dialog_mgr.result == _RESULT_NONE:
        if __debug__:
            log.info(__name__, "waiting for button")
        return msg_error(cid, _SW_CONDITIONS_NOT_SATISFIED)

    if dialog_mgr.result != _RESULT_CONFIRM:
        if __debug__:
            log.info(__name__, "request declined")
        # There is no standard way to decline a U2F request, but responding with ERR_CHANNEL_BUSY
        # doesn't seem to violate the protocol and at least stops Chrome from polling.
        return cmd_error(cid, _ERR_CHANNEL_BUSY)

    # sign the registration challenge and return
    if __debug__:
        log.info(__name__, "signing register")
    buf = _msg_register_sign(chal, cred)

    dialog_mgr.reset()

    return Cmd(cid, _CMD_MSG, buf)


def basic_attestation_sign(data: Iterable[bytes]) -> bytes:
    from trezor.crypto import der

    dig = hashlib.sha256()
    for segment in data:
        dig.update(segment)
    sig = nist256p1.sign(_FIDO_ATT_PRIV_KEY, dig.digest(), False)
    return der.encode_seq((sig[1:33], sig[33:]))


def _msg_register_sign(challenge: bytes, cred: U2fCredential) -> bytes:
    memcpy = utils.memcpy  # local_cache_attribute
    id = cred.id  # local_cache_attribute

    pubkey = cred.public_key()

    sig = basic_attestation_sign((b"\x00", cred.rp_id_hash, challenge, id, pubkey))

    # pack to a response
    buf, resp = make_struct(_resp_cmd_register(len(id), len(_FIDO_ATT_CERT), len(sig)))
    resp.registerId = _U2F_REGISTER_ID
    memcpy(resp.pubKey, 0, pubkey, 0, len(pubkey))
    resp.keyHandleLen = len(id)
    memcpy(resp.keyHandle, 0, id, 0, len(id))
    memcpy(resp.cert, 0, _FIDO_ATT_CERT, 0, len(_FIDO_ATT_CERT))
    memcpy(resp.sig, 0, sig, 0, len(sig))
    resp.status = _SW_NO_ERROR

    return bytes(buf)


def _msg_authenticate(req: Msg, dialog_mgr: DialogManager) -> Cmd:
    global _last_auth_valid
    _last_auth_valid = False

    cid = req.cid  # local_cache_attribute
    data = req.data  # local_cache_attribute
    info = log.info  # local_cache_attribute

    if not config.is_unlocked():
        new_state: State = U2fUnlock(cid, dialog_mgr.iface)
        dialog_mgr.set_state(new_state)
        return msg_error(cid, _SW_CONDITIONS_NOT_SATISFIED)

    if not storage_device.is_initialized():
        if __debug__:
            log.warning(__name__, "not initialized")
        # Device is not registered with the RP.
        return msg_error(cid, _SW_WRONG_DATA)

    # we need at least keyHandleLen
    if len(data) <= _REQ_CMD_AUTHENTICATE_KHLEN:
        if __debug__:
            log.warning(__name__, "_SW_WRONG_LENGTH req_data")
        return msg_error(cid, _SW_WRONG_LENGTH)

    # check keyHandleLen
    khlen = data[_REQ_CMD_AUTHENTICATE_KHLEN]
    auth = overlay_struct(bytearray(data), _req_cmd_authenticate(khlen))
    challenge = bytes(auth.chal)
    rp_id_hash = bytes(auth.appId)
    key_handle = bytes(auth.keyHandle)

    try:
        cred = Credential.from_bytes(key_handle, rp_id_hash)
    except Exception:
        # specific error logged in _node_from_key_handle
        return msg_error(cid, _SW_WRONG_DATA)

    _last_auth_valid = True

    # if _AUTH_CHECK_ONLY is requested, return, because keyhandle has been checked already
    if req.p1 == _AUTH_CHECK_ONLY:
        if __debug__:
            info(__name__, "_AUTH_CHECK_ONLY")
        return msg_error(cid, _SW_CONDITIONS_NOT_SATISFIED)

    # from now on, only _AUTH_ENFORCE is supported
    if req.p1 != _AUTH_ENFORCE:
        if __debug__:
            info(__name__, "_AUTH_ENFORCE")
        return msg_error(cid, _SW_WRONG_DATA)

    # check equality with last request
    new_state = U2fConfirmAuthenticate(cid, dialog_mgr.iface, data, cred)
    if not dialog_mgr.set_state(new_state):
        return msg_error(cid, _SW_CONDITIONS_NOT_SATISFIED)

    # wait for a button or continue
    if dialog_mgr.result == _RESULT_NONE:
        if __debug__:
            info(__name__, "waiting for button")
        return msg_error(cid, _SW_CONDITIONS_NOT_SATISFIED)

    if dialog_mgr.result != _RESULT_CONFIRM:
        if __debug__:
            info(__name__, "request declined")
        # There is no standard way to decline a U2F request, but responding with ERR_CHANNEL_BUSY
        # doesn't seem to violate the protocol and at least stops Chrome from polling.
        return cmd_error(cid, _ERR_CHANNEL_BUSY)

    # sign the authentication challenge and return
    if __debug__:
        info(__name__, "signing authentication")
    buf = _msg_authenticate_sign(challenge, rp_id_hash, cred)

    dialog_mgr.reset()

    return Cmd(cid, _CMD_MSG, buf)


def _msg_authenticate_sign(
    challenge: bytes, rp_id_hash: bytes, cred: Credential
) -> bytes:
    flags = bytes([_AUTH_FLAG_UP])

    # get next counter
    ctr = cred.next_signature_counter()
    ctrbuf = ustruct.pack(">L", ctr)

    # sign the input data together with counter
    sig = cred.sign((rp_id_hash, flags, ctrbuf, challenge))

    # pack to a response
    buf, resp = make_struct(_resp_cmd_authenticate(len(sig)))
    resp.flags = flags[0]
    resp.ctr = ctr
    utils.memcpy(resp.sig, 0, sig, 0, len(sig))
    resp.status = _SW_NO_ERROR

    return bytes(buf)


def msg_error(cid: int, code: int) -> Cmd:
    return Cmd(cid, _CMD_MSG, ustruct.pack(">H", code))


def cmd_error(cid: int, code: int) -> Cmd:
    return Cmd(cid, _CMD_ERROR, ustruct.pack(">B", code))


def cbor_error(cid: int, code: int) -> Cmd:
    return Cmd(cid, _CMD_CBOR, ustruct.pack(">B", code))


def credentials_from_descriptor_list(
    descriptor_list: list[dict], rp_id_hash: bytes
) -> Iterator[Credential]:
    for credential_descriptor in descriptor_list:
        credential_type = credential_descriptor["type"]
        if not isinstance(credential_type, str):
            raise TypeError
        if credential_type != "public-key":
            continue

        credential_id = credential_descriptor["id"]
        if not isinstance(credential_id, bytes):
            raise TypeError
        try:
            cred = Credential.from_bytes(credential_id, rp_id_hash)
        except Exception:
            continue

        yield cred


def _distinguishable_cred_list(credentials: Iterable[Credential]) -> list[Credential]:
    """Reduces the input to a list of credentials which can be distinguished by
    the user. It is assumed that all input credentials share the same RP ID."""
    cred_list: list[Credential] = []
    for cred in credentials:
        for i, prev_cred in enumerate(cred_list):
            if prev_cred.account_name() == cred.account_name():
                # Among indistinguishable FIDO2 credentials prefer the newest.
                # Among U2F credentials prefer the first in the input.
                if isinstance(cred, Fido2Credential) and cred < prev_cred:
                    cred_list[i] = cred
                break
        else:
            cred_list.append(cred)
    return cred_list


def _algorithms_from_pub_key_cred_params(pub_key_cred_params: list[dict]) -> list[int]:
    alg_list = []
    for pkcp in pub_key_cred_params:
        pub_key_cred_type = pkcp["type"]
        if not isinstance(pub_key_cred_type, str):
            raise TypeError
        if pub_key_cred_type != "public-key":
            continue

        pub_key_cred_alg = pkcp["alg"]
        if not isinstance(pub_key_cred_alg, int):
            raise TypeError
        alg_list.append(pub_key_cred_alg)
    return alg_list


def _cbor_make_credential(req: Cmd, dialog_mgr: DialogManager) -> Cmd | None:
    if config.is_unlocked():
        resp = _cbor_make_credential_process(req, dialog_mgr)
    else:
        resp = Fido2Unlock(_cbor_make_credential_process, req, dialog_mgr)

    if isinstance(resp, State):
        if dialog_mgr.set_state(resp):
            return None
        else:
            return cmd_error(req.cid, _ERR_CHANNEL_BUSY)
    else:
        return resp


def _cbor_make_credential_process(req: Cmd, dialog_mgr: DialogManager) -> State | Cmd:
    from . import knownapps

    cid = req.cid  # local_cache_attribute

    if not storage_device.is_initialized():
        if __debug__:
            log.warning(__name__, "not initialized")
        return cbor_error(cid, _ERR_OTHER)

    try:
        param = cbor.decode(req.data, offset=1)
        rp = param[_MAKECRED_CMD_RP]
        rp_id = rp["id"]
        rp_id_hash = hashlib.sha256(rp_id).digest()

        # Prepare the new credential.
        user = param[_MAKECRED_CMD_USER]
        cred = Fido2Credential()
        cred.rp_id = rp_id
        cred.rp_id_hash = rp_id_hash
        cred.rp_name = rp.get("name", None)
        cred.user_id = user["id"]
        cred.user_name = user.get("name", None)
        cred.user_display_name = user.get("displayName", None)
        cred.truncate_names()

        # Check if any of the credential descriptors in the exclude list belong to this authenticator.
        exclude_list = param.get(_MAKECRED_CMD_EXCLUDE_LIST, [])
        excluded_creds = credentials_from_descriptor_list(exclude_list, rp_id_hash)
        if not utils.is_empty_iterator(excluded_creds):
            # This authenticator is already registered.
            return Fido2ConfirmExcluded(cid, dialog_mgr.iface, cred)

        # Check that the relying party supports ECDSA with SHA-256 or EdDSA. We don't support any other algorithms.
        pub_key_cred_params = param[_MAKECRED_CMD_PUB_KEY_CRED_PARAMS]
        for alg in _algorithms_from_pub_key_cred_params(pub_key_cred_params):
            if alg == common.COSE_ALG_ES256:
                cred.algorithm = alg
                cred.curve = common.COSE_CURVE_P256
                break
            elif alg == common.COSE_ALG_EDDSA:
                cred.algorithm = alg
                cred.curve = common.COSE_CURVE_ED25519
                break
        else:
            return cbor_error(cid, _ERR_UNSUPPORTED_ALGORITHM)

        # Get options.
        options = param.get(_MAKECRED_CMD_OPTIONS, {})
        resident_key = options.get("rk", False)
        user_verification = options.get("uv", False)

        # Get supported extensions.
        cred.hmac_secret = param.get(_MAKECRED_CMD_EXTENSIONS, {}).get(
            "hmac-secret", False
        )

        client_data_hash = param[_MAKECRED_CMD_CLIENT_DATA_HASH]
    except TypeError:
        return cbor_error(cid, _ERR_CBOR_UNEXPECTED_TYPE)
    except KeyError:
        return cbor_error(cid, _ERR_MISSING_PARAMETER)
    except Exception:
        return cbor_error(cid, _ERR_INVALID_CBOR)

    app = knownapps.by_rp_id_hash(rp_id_hash)
    if app is not None and app.use_sign_count is not None:
        cred.use_sign_count = app.use_sign_count
    else:
        cred.use_sign_count = bool(_DEFAULT_USE_SIGN_COUNT)

    if app is not None and app.use_compact:
        # Remove unnecessary information.

        # The user_id is mandatory only for resident credentials.
        if not resident_key:
            cred.user_id = None

        # We prefer to show rp_id, so we don't need rp_name.
        cred.rp_name = None

        # We prefer to show user_name, so we don't need user_display_name if we have user_name.
        if cred.user_name:
            cred.user_display_name = None

    # Check data types.
    if (
        not cred.check_data_types()
        or not isinstance(user.get("icon", ""), str)
        or not isinstance(rp.get("icon", ""), str)
        or not isinstance(client_data_hash, bytes)
        or not isinstance(resident_key, bool)
        or not isinstance(user_verification, bool)
    ):
        return cbor_error(cid, _ERR_CBOR_UNEXPECTED_TYPE)

    # Check options.
    if "up" in options:
        return cbor_error(cid, _ERR_INVALID_OPTION)

    if resident_key and not _ALLOW_RESIDENT_CREDENTIALS:
        return cbor_error(cid, _ERR_UNSUPPORTED_OPTION)

    if user_verification and not config.has_pin():
        # User verification requested, but PIN is not enabled.
        return Fido2ConfirmNoPin(cid, dialog_mgr.iface)

    # Check that the pinAuth parameter is absent. Client PIN is not supported.
    if _MAKECRED_CMD_PIN_AUTH in param:
        return cbor_error(cid, _ERR_PIN_AUTH_INVALID)

    # Ask user to confirm registration.
    return Fido2ConfirmMakeCredential(
        cid,
        dialog_mgr.iface,
        client_data_hash,
        cred,
        resident_key,
        user_verification,
    )


def _cbor_make_credential_sign(
    client_data_hash: bytes, cred: Fido2Credential, user_verification: bool
) -> bytes:
    from . import knownapps

    flags = _AUTH_FLAG_UP | _AUTH_FLAG_AT
    if user_verification:
        flags |= _AUTH_FLAG_UV

    # Encode the authenticator data (Credential ID, its public key and extensions).
    att_cred_data = (
        _AAGUID + len(cred.id).to_bytes(2, "big") + cred.id + cred.public_key()
    )

    extensions = b""
    if cred.hmac_secret:
        extensions = cbor.encode({"hmac-secret": True})
        flags |= _AUTH_FLAG_ED

    ctr = cred.next_signature_counter()

    authenticator_data = (
        cred.rp_id_hash
        + bytes([flags])
        + ctr.to_bytes(4, "big")
        + att_cred_data
        + extensions
    )

    # use_self_attestation
    app = knownapps.by_rp_id_hash(cred.rp_id_hash)
    if app is not None and app.use_self_attestation is not None:
        use_self_attestation = app.use_self_attestation
    else:
        use_self_attestation = _DEFAULT_USE_SELF_ATTESTATION

    if use_self_attestation:
        sig = cred.sign((authenticator_data, client_data_hash))
        attestation_statement = {"alg": cred.algorithm, "sig": sig}
    else:
        sig = basic_attestation_sign((authenticator_data, client_data_hash))
        attestation_statement = {
            "alg": common.COSE_ALG_ES256,
            "sig": sig,
            "x5c": [_FIDO_ATT_CERT],
        }

    # Encode the authenticatorMakeCredential response data.
    return cbor.encode(
        {
            _MAKECRED_RESP_FMT: "packed",
            _MAKECRED_RESP_AUTH_DATA: authenticator_data,
            _MAKECRED_RESP_ATT_STMT: attestation_statement,
        }
    )


def _cbor_get_assertion(req: Cmd, dialog_mgr: DialogManager) -> Cmd | None:
    if config.is_unlocked():
        resp = _cbor_get_assertion_process(req, dialog_mgr)
    else:
        resp = Fido2Unlock(_cbor_get_assertion_process, req, dialog_mgr)

    if isinstance(resp, State):
        if dialog_mgr.set_state(resp):
            return None
        else:
            return cmd_error(req.cid, _ERR_CHANNEL_BUSY)
    else:
        return resp


def _cbor_get_assertion_process(req: Cmd, dialog_mgr: DialogManager) -> State | Cmd:
    from .resident_credentials import find_by_rp_id_hash

    cid = req.cid  # local_cache_attribute

    if not storage_device.is_initialized():
        if __debug__:
            log.warning(__name__, "not initialized")
        return cbor_error(cid, _ERR_OTHER)

    try:
        param = cbor.decode(req.data, offset=1)
        rp_id = param[_GETASSERT_CMD_RP_ID]
        rp_id_hash = hashlib.sha256(rp_id).digest()

        allow_list = param.get(_GETASSERT_CMD_ALLOW_LIST, [])
        cred_list: list[Credential]
        if allow_list:
            # Get all credentials from the allow list that belong to this authenticator.
            allowed_creds = credentials_from_descriptor_list(allow_list, rp_id_hash)
            cred_list = _distinguishable_cred_list(allowed_creds)
            for cred in cred_list:
                if cred.rp_id is None:
                    cred.rp_id = rp_id
            resident = False
        else:
            # Allow list is empty. Get resident credentials.
            if _ALLOW_RESIDENT_CREDENTIALS:
                cred_list = list(find_by_rp_id_hash(rp_id_hash))
            else:
                cred_list = []
            resident = True

        # Sort credentials by time of creation.
        cred_list.sort()

        # Check that the pinAuth parameter is absent. Client PIN is not supported.
        if _GETASSERT_CMD_PIN_AUTH in param:
            return cbor_error(cid, _ERR_PIN_AUTH_INVALID)

        # Get options.
        options = param.get(_GETASSERT_CMD_OPTIONS, {})
        user_presence = options.get("up", True)
        user_verification = options.get("uv", False)

        # Get supported extensions.
        hmac_secret = param.get(_GETASSERT_CMD_EXTENSIONS, {}).get("hmac-secret", None)

        client_data_hash = param[_GETASSERT_CMD_CLIENT_DATA_HASH]
    except TypeError:
        return cbor_error(cid, _ERR_CBOR_UNEXPECTED_TYPE)
    except KeyError:
        return cbor_error(cid, _ERR_MISSING_PARAMETER)
    except Exception:
        return cbor_error(cid, _ERR_INVALID_CBOR)

    # Check data types.
    if (
        not isinstance(hmac_secret, (dict, type(None)))
        or not isinstance(client_data_hash, bytes)
        or not isinstance(user_presence, bool)
        or not isinstance(user_verification, bool)
    ):
        return cbor_error(cid, _ERR_CBOR_UNEXPECTED_TYPE)

    # Check options.
    if "rk" in options:
        return cbor_error(cid, _ERR_INVALID_OPTION)

    if user_verification and not config.has_pin():
        # User verification requested, but PIN is not enabled.
        return Fido2ConfirmNoPin(cid, dialog_mgr.iface)

    global _last_auth_valid
    _last_auth_valid = bool(cred_list)

    if not cred_list:
        # No credentials. This authenticator is not registered.
        if user_presence:
            return Fido2ConfirmNoCredentials(cid, dialog_mgr.iface, rp_id)
        else:
            return cbor_error(cid, _ERR_NO_CREDENTIALS)
    elif not user_presence and not user_verification:
        # Silent authentication.
        try:
            response_data = cbor_get_assertion_sign(
                client_data_hash,
                rp_id_hash,
                cred_list[0],
                hmac_secret,
                resident,
                user_presence,
                user_verification,
            )
            return Cmd(cid, _CMD_CBOR, bytes([_ERR_NONE]) + response_data)
        except Exception as e:
            # Firmware error.
            if __debug__:
                log.exception(__name__, e)
            return cbor_error(cid, _ERR_OTHER)
    else:
        # Ask user to confirm one of the credentials.
        return Fido2ConfirmGetAssertion(
            cid,
            dialog_mgr.iface,
            client_data_hash,
            cred_list,
            hmac_secret,
            resident,
            user_verification,
        )


def _cbor_get_assertion_hmac_secret(
    cred: Credential, hmac_secret: dict
) -> bytes | None:
    from storage.fido2 import KEY_AGREEMENT_PRIVKEY
    from trezor.crypto import aes, hmac

    key_agreement = hmac_secret[1]  # The public key of platform key agreement key.
    # NOTE: We should check the key_agreement[COSE_KEY_ALG] here, but to avoid compatibility issues we don't,
    # because there is currently no valid value which describes the actual key agreement algorithm.
    if (
        key_agreement[common.COSE_KEY_KTY] != common.COSE_KEYTYPE_EC2
        or key_agreement[common.COSE_KEY_CRV] != common.COSE_CURVE_P256
    ):
        return None

    x = key_agreement[common.COSE_KEY_X]
    y = key_agreement[common.COSE_KEY_Y]
    salt_enc = hmac_secret[2]  # The encrypted salt.
    salt_auth = hmac_secret[3]  # The HMAC of the encrypted salt.
    if (
        len(x) != 32
        or len(y) != 32
        or len(salt_auth) != 16
        or len(salt_enc) not in (32, 64)
    ):
        raise CborError(_ERR_INVALID_LEN)

    # Compute the ECDH shared secret.
    ecdh_result = nist256p1.multiply(KEY_AGREEMENT_PRIVKEY, b"\04" + x + y)
    shared_secret = hashlib.sha256(ecdh_result[1:33]).digest()

    # Check the authentication tag and decrypt the salt.
    tag = hmac(hmac.SHA256, shared_secret, salt_enc).digest()[:16]
    if not utils.consteq(tag, salt_auth):
        raise CborError(_ERR_EXTENSION_FIRST)
    salt = aes(aes.CBC, shared_secret).decrypt(salt_enc)

    # Get cred_random - a constant symmetric key associated with the credential.
    cred_random = cred.hmac_secret_key()
    if cred_random is None:
        # The credential does not have the hmac-secret extension enabled.
        return None

    # Compute the hmac-secret output.
    output = hmac(hmac.SHA256, cred_random, salt[:32]).digest()
    if len(salt) == 64:
        output += hmac(hmac.SHA256, cred_random, salt[32:]).digest()

    # Encrypt the hmac-secret output.
    return aes(aes.CBC, shared_secret).encrypt(output)


def cbor_get_assertion_sign(
    client_data_hash: bytes,
    rp_id_hash: bytes,
    cred: Credential,
    hmac_secret: dict | None,
    resident: bool,
    user_presence: bool,
    user_verification: bool,
) -> bytes:
    # Process extensions
    extensions = {}

    # Spec deviation: Do not reveal hmac-secret during silent authentication.
    if hmac_secret and user_presence:
        encrypted_output = _cbor_get_assertion_hmac_secret(cred, hmac_secret)
        if encrypted_output is not None:
            extensions["hmac-secret"] = encrypted_output

    # Encode the authenticator data.
    flags = 0
    if user_presence:
        flags |= _AUTH_FLAG_UP
    if user_verification:
        flags |= _AUTH_FLAG_UV

    encoded_extensions = b""
    if extensions:
        flags |= _AUTH_FLAG_ED
        encoded_extensions = cbor.encode(extensions)

    ctr = cred.next_signature_counter()

    authenticator_data = (
        rp_id_hash + bytes([flags]) + ctr.to_bytes(4, "big") + encoded_extensions
    )

    # Sign the authenticator data and the client data hash.
    if user_presence:
        sig = cred.sign((authenticator_data, client_data_hash))
    else:
        # Spec deviation: Use a bogus signature during silent authentication.
        sig = cred.bogus_signature()

    # Encode the authenticatorGetAssertion response data.
    response = {
        _GETASSERT_RESP_CREDENTIAL: {"type": "public-key", "id": cred.id},
        _GETASSERT_RESP_AUTH_DATA: authenticator_data,
        _GETASSERT_RESP_SIGNATURE: sig,
    }

    if resident and user_presence and cred.user_id is not None:
        response[_GETASSERT_RESP_USER] = {"id": cred.user_id}

    return cbor.encode(response)


def _cbor_get_info(req: Cmd) -> Cmd:
    from .credential import CRED_ID_MAX_LENGTH

    # Note: We claim that the PIN is set even when it's not, because otherwise
    # login.live.com shows an error, but doesn't instruct the user to set a PIN.
    response_data = {
        _GETINFO_RESP_VERSIONS: ["U2F_V2", "FIDO_2_0"],
        _GETINFO_RESP_EXTENSIONS: ["hmac-secret"],
        _GETINFO_RESP_AAGUID: _AAGUID,
        _GETINFO_RESP_OPTIONS: {
            "rk": bool(_ALLOW_RESIDENT_CREDENTIALS),
            "up": True,
            "uv": True,
        },
        _GETINFO_RESP_PIN_PROTOCOLS: [1],
        _GETINFO_RESP_MAX_CRED_COUNT_IN_LIST: _MAX_CRED_COUNT_IN_LIST,
        _GETINFO_RESP_MAX_CRED_ID_LEN: CRED_ID_MAX_LENGTH,
    }
    return Cmd(req.cid, _CMD_CBOR, bytes([_ERR_NONE]) + cbor.encode(response_data))


def _cbor_client_pin(req: Cmd) -> Cmd:
    from storage.fido2 import KEY_AGREEMENT_PUBKEY

    cid = req.cid  # local_cache_attribute

    try:
        param = cbor.decode(req.data, offset=1)
        pin_protocol = param[_CLIENTPIN_CMD_PIN_PROTOCOL]
        subcommand = param[_CLIENTPIN_CMD_SUBCOMMAND]
    except Exception:
        return cbor_error(cid, _ERR_INVALID_CBOR)

    if pin_protocol != 1:
        return cbor_error(cid, _ERR_PIN_AUTH_INVALID)

    # We only support the get key agreement command which is required for the hmac-secret extension.
    if subcommand != _CLIENTPIN_SUBCMD_GET_KEY_AGREEMENT:
        return cbor_error(cid, _ERR_UNSUPPORTED_OPTION)

    # Encode the public key of the authenticator key agreement key.
    # NOTE: There is currently no valid value for COSE_KEY_ALG which describes the actual
    # key agreement algorithm as specified, but COSE_ALG_ECDH_ES_HKDF_256 is allegedly
    # recommended by the latest draft of the CTAP2 spec.
    response_data = {
        _CLIENTPIN_RESP_KEY_AGREEMENT: {
            common.COSE_KEY_ALG: common.COSE_ALG_ECDH_ES_HKDF_256,
            common.COSE_KEY_KTY: common.COSE_KEYTYPE_EC2,
            common.COSE_KEY_CRV: common.COSE_CURVE_P256,
            common.COSE_KEY_X: KEY_AGREEMENT_PUBKEY[1:33],
            common.COSE_KEY_Y: KEY_AGREEMENT_PUBKEY[33:],
        }
    }

    return Cmd(cid, _CMD_CBOR, bytes([_ERR_NONE]) + cbor.encode(response_data))


def _cbor_reset(req: Cmd, dialog_mgr: DialogManager) -> Cmd | None:
    if not storage_device.is_initialized():
        if __debug__:
            log.warning(__name__, "not initialized")
        # Return success, because the authenticator is already in factory default state.
        return cbor_error(req.cid, _ERR_NONE)

    if not dialog_mgr.set_state(Fido2ConfirmReset(req.cid, dialog_mgr.iface)):
        return cmd_error(req.cid, _ERR_CHANNEL_BUSY)
    return None


def cmd_keepalive(cid: int, status: int) -> Cmd:
    return Cmd(cid, _CMD_KEEPALIVE, bytes([status]))
