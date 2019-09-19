import uctypes
import ustruct
import utime
from micropython import const

from trezor import config, io, log, loop, ui, utils, wire, workflow
from trezor.crypto import aes, der, hashlib, hmac, random
from trezor.crypto.curve import nist256p1
from trezor.messages import MessageType
from trezor.ui.confirm import CONFIRMED, Confirm, ConfirmPageable, Pageable
from trezor.ui.text import Text

from apps.common import cbor, storage
from apps.common.storage.webauthn import (
    erase_resident_credentials,
    get_resident_credentials,
    store_resident_credential,
)
from apps.webauthn.confirm import ConfirmContent, ConfirmInfo
from apps.webauthn.credential import Credential, Fido2Credential, U2fCredential

if __debug__:
    from apps.debug import confirm_signal

if False:
    from typing import Any, Coroutine, List, Optional

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
_ERR_INVALID_OPTION = const(0x2C)  # not a valid option for current operation
_ERR_KEEPALIVE_CANCEL = const(0x2D)  # pending keep alive was cancelled
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
_U2F_REGISTER_ID = const(0x05)  # version 2 registration identifier
_U2F_ATT_PRIV_KEY = b"q&\xac+\xf6D\xdca\x86\xad\x83\xef\x1f\xcd\xf1*W\xb5\xcf\xa2\x00\x0b\x8a\xd0'\xe9V\xe8T\xc5\n\x8b"
_U2F_ATT_CERT = b"0\x82\x01\x180\x81\xc0\x02\t\x00\xb1\xd9\x8fBdr\xd3,0\n\x06\x08*\x86H\xce=\x04\x03\x020\x151\x130\x11\x06\x03U\x04\x03\x0c\nTrezor U2F0\x1e\x17\r160429133153Z\x17\r260427133153Z0\x151\x130\x11\x06\x03U\x04\x03\x0c\nTrezor U2F0Y0\x13\x06\x07*\x86H\xce=\x02\x01\x06\x08*\x86H\xce=\x03\x01\x07\x03B\x00\x04\xd9\x18\xbd\xfa\x8aT\xac\x92\xe9\r\xa9\x1f\xcaz\xa2dT\xc0\xd1s61M\xde\x83\xa5K\x86\xb5\xdfN\xf0Re\x9a\x1do\xfc\xb7F\x7f\x1a\xcd\xdb\x8a3\x08\x0b^\xed\x91\x89\x13\xf4C\xa5&\x1b\xc7{h`o\xc10\n\x06\x08*\x86H\xce=\x04\x03\x02\x03G\x000D\x02 $\x1e\x81\xff\xd2\xe5\xe6\x156\x94\xc3U.\x8f\xeb\xd7\x1e\x895\x92\x1c\xb4\x83ACq\x1cv\xea\xee\xf3\x95\x02 _\x80\xeb\x10\xf2\\\xcc9\x8b<\xa8\xa9\xad\xa4\x02\x7f\x93\x13 w\xb7\xab\xcewFZ'\xf5=3\xa1\x1d"
_BOGUS_APPID = b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
_AAGUID = (
    b"\xd6\xd0\xbd\xc3b\xee\xc4\xdb\xde\x8dzenJD\x87"
)  # First 16 bytes of SHA-256("TREZOR 2")
_BOGUS_PRIV_KEY = b"\xAA" * 32

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

_FRAME_INIT_SIZE = 57
_FRAME_CONT_SIZE = 59

# Generate the authenticatorKeyAgreementKey used for ECDH in authenticatorClientPIN getKeyAgreement.
_KEY_AGREEMENT_PRIVKEY = nist256p1.generate_secret()
_KEY_AGREEMENT_PUBKEY = nist256p1.publickey(_KEY_AGREEMENT_PRIVKEY, False)

# FIDO2 configuration.
_ALLOW_FIDO2 = True
_ALLOW_RESIDENT_CREDENTIALS = True

# The attestation type to use in MakeCredential responses. If false, then self attestation will be used.
_USE_BASIC_ATTESTATION = True


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


async def read_cmd(iface: io.HID) -> Optional[Cmd]:
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


def send_cmd_sync(cmd: Cmd, iface: io.HID) -> None:
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


def boot(iface: io.HID) -> None:
    wire.add(
        MessageType.WebAuthnListResidentCredentials,
        __name__,
        "list_resident_credentials",
    )
    wire.add(
        MessageType.WebAuthnAddResidentCredential, __name__, "add_resident_credential"
    )
    wire.add(
        MessageType.WebAuthnRemoveResidentCredential,
        __name__,
        "remove_resident_credential",
    )
    loop.schedule(handle_reports(iface))


async def handle_reports(iface: io.HID) -> None:
    dialog_mgr = DialogManager(iface)

    while True:
        try:
            req = await read_cmd(iface)
            if req is None:
                continue
            if dialog_mgr.is_busy() and req.cid not in (
                dialog_mgr.get_cid(),
                _CID_BROADCAST,
            ):
                resp = cmd_error(req.cid, _ERR_CHANNEL_BUSY)  # type: Optional[Cmd]
            else:
                resp = dispatch_cmd(req, dialog_mgr)
            if resp is not None:
                await send_cmd(resp, iface)
        except Exception as e:
            log.exception(__name__, e)


class KeepaliveCallback:
    def __init__(self, cid: int, iface: io.HID) -> None:
        self.cid = cid
        self.iface = iface

    def __call__(self) -> None:
        send_cmd_sync(cmd_keepalive(self.cid, _KEEPALIVE_STATUS_PROCESSING), self.iface)


async def verify_user(keepalive_callback: KeepaliveCallback) -> bool:
    from apps.common.request_pin import verify_user_pin, PinCancelled, PinInvalid
    import trezor.pin

    try:
        trezor.pin.keepalive_callback = keepalive_callback
        await verify_user_pin()
        ret = True
    except (PinCancelled, PinInvalid):
        ret = False
    finally:
        trezor.pin.keepalive_callback = None

    return ret


async def confirm(*args: Any, **kwargs: Any) -> bool:
    dialog = Confirm(*args, **kwargs)
    if __debug__:
        return await loop.race(dialog, confirm_signal()) is CONFIRMED
    else:
        return await dialog is CONFIRMED


class State:
    def __init__(self, cid: int, iface: io.HID) -> None:
        self.cid = cid
        self.iface = iface

    def keepalive_status(self) -> Optional[int]:
        return None

    def timeout_ms(self) -> int:
        raise NotImplementedError

    async def confirm_dialog(self) -> bool:
        pass

    async def on_confirm(self) -> None:
        pass

    async def on_decline(self) -> None:
        pass

    async def on_timeout(self) -> None:
        pass

    async def on_cancel(self) -> None:
        pass


class U2fState(State, ConfirmInfo):
    def __init__(
        self, cid: int, iface: io.HID, req_data: bytes, cred: Credential
    ) -> None:
        State.__init__(self, cid, iface)
        ConfirmInfo.__init__(self)
        self._cred = cred
        self._req_data = req_data
        self.load_icon(self._cred.rp_id_hash)

    def timeout_ms(self) -> int:
        return _U2F_CONFIRM_TIMEOUT_MS

    def app_name(self) -> str:
        return self._cred.app_name()

    def account_name(self) -> Optional[str]:
        return self._cred.account_name()


class U2fConfirmRegister(U2fState):
    def __init__(
        self, cid: int, iface: io.HID, req_data: bytes, cred: U2fCredential
    ) -> None:
        super().__init__(cid, iface, req_data, cred)

    async def confirm_dialog(self) -> bool:
        if self._cred.rp_id_hash == _BOGUS_APPID:
            text = Text("U2F", ui.ICON_WRONG, ui.RED)
            text.normal(
                "Another U2F device", "was used to register", "in this application."
            )
            return await confirm(text, confirm=None)
        else:
            content = ConfirmContent(self)
            return await confirm(content)

    def get_header(self) -> str:
        return "U2F Register"

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, U2fConfirmRegister)
            and self.cid == other.cid
            and self._req_data == other._req_data
        )


class U2fConfirmAuthenticate(U2fState):
    def __init__(
        self, cid: int, iface: io.HID, req_data: bytes, cred: Credential
    ) -> None:
        super().__init__(cid, iface, req_data, cred)

    def get_header(self) -> str:
        return "U2F Authenticate"

    async def confirm_dialog(self) -> bool:
        content = ConfirmContent(self)
        return await confirm(content)

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, U2fConfirmAuthenticate)
            and self.cid == other.cid
            and self._req_data == other._req_data
        )


class Fido2State(State):
    def __init__(self, cid: int, iface: io.HID) -> None:
        super().__init__(cid, iface)

    def keepalive_status(self) -> int:
        return _KEEPALIVE_STATUS_UP_NEEDED

    def timeout_ms(self) -> int:
        return _FIDO2_CONFIRM_TIMEOUT_MS

    async def on_confirm(self) -> None:
        cmd = cbor_error(self.cid, _ERR_OPERATION_DENIED)
        await send_cmd(cmd, self.iface)

    async def on_decline(self) -> None:
        cmd = cbor_error(self.cid, _ERR_OPERATION_DENIED)
        await send_cmd(cmd, self.iface)

    async def on_timeout(self) -> None:
        await self.on_decline()

    async def on_cancel(self) -> None:
        cmd = cbor_error(self.cid, _ERR_KEEPALIVE_CANCEL)
        await send_cmd(cmd, self.iface)


class Fido2ConfirmMakeCredential(Fido2State, ConfirmInfo):
    def __init__(
        self,
        cid: int,
        iface: io.HID,
        client_data_hash: bytes,
        cred: Fido2Credential,
        resident: bool,
        user_verification: bool,
    ) -> None:
        Fido2State.__init__(self, cid, iface)
        ConfirmInfo.__init__(self)
        self._client_data_hash = client_data_hash
        self._cred = cred
        self._resident = resident
        self._user_verification = user_verification
        self.load_icon(cred.rp_id_hash)

    def get_header(self) -> str:
        return "FIDO2 Register"

    def app_name(self) -> str:
        return self._cred.app_name()

    def account_name(self) -> Optional[str]:
        return self._cred.account_name()

    async def confirm_dialog(self) -> bool:
        content = ConfirmContent(self)
        if not await confirm(content):
            return False
        if self._user_verification:
            return await verify_user(KeepaliveCallback(self.cid, self.iface))
        return True

    async def on_confirm(self) -> None:
        self._cred.generate_id()
        send_cmd_sync(cmd_keepalive(self.cid, _KEEPALIVE_STATUS_PROCESSING), self.iface)
        response_data = cbor_make_credential_sign(
            self._client_data_hash, self._cred, self._user_verification
        )

        cmd = Cmd(self.cid, _CMD_CBOR, bytes([_ERR_NONE]) + response_data)
        if self._resident:
            send_cmd_sync(
                cmd_keepalive(self.cid, _KEEPALIVE_STATUS_PROCESSING), self.iface
            )
            if not store_resident_credential(self._cred):
                cmd = cbor_error(self.cid, _ERR_KEY_STORE_FULL)
        await send_cmd(cmd, self.iface)


class Fido2ConfirmExcluded(Fido2ConfirmMakeCredential):
    def __init__(self, cid: int, iface: io.HID, cred: Fido2Credential) -> None:
        super().__init__(cid, iface, b"", cred, resident=False, user_verification=False)

    async def on_confirm(self) -> None:
        cmd = cbor_error(self.cid, _ERR_CREDENTIAL_EXCLUDED)
        await send_cmd(cmd, self.iface)

        text = Text("FIDO2 Register", ui.ICON_WRONG, ui.RED)
        text.normal("This device is already", "registered with", self._cred.rp_id + ".")
        await confirm(text, confirm=None)


class Fido2ConfirmGetAssertion(Fido2State, ConfirmInfo, Pageable):
    def __init__(
        self,
        cid: int,
        iface: io.HID,
        client_data_hash: bytes,
        creds: List[Credential],
        hmac_secret: Optional[dict],
        user_verification: bool,
    ) -> None:
        Fido2State.__init__(self, cid, iface)
        ConfirmInfo.__init__(self)
        Pageable.__init__(self)
        self._client_data_hash = client_data_hash
        self._creds = creds
        self._hmac_secret = hmac_secret
        self._user_verification = user_verification
        self.load_icon(self._creds[0].rp_id_hash)

    def get_header(self) -> str:
        return "FIDO2 Authenticate"

    def app_name(self) -> str:
        return self._creds[self.page()].app_name()

    def account_name(self) -> Optional[str]:
        return self._creds[self.page()].account_name()

    def page_count(self) -> int:
        return len(self._creds)

    async def confirm_dialog(self) -> bool:
        content = ConfirmContent(self)
        if await ConfirmPageable(self, content) is not CONFIRMED:
            return False
        if self._user_verification:
            return await verify_user(KeepaliveCallback(self.cid, self.iface))
        return True

    async def on_confirm(self) -> None:
        cred = self._creds[self.page()]
        try:
            send_cmd_sync(
                cmd_keepalive(self.cid, _KEEPALIVE_STATUS_PROCESSING), self.iface
            )
            response_data = cbor_get_assertion_sign(
                self._client_data_hash,
                cred.rp_id_hash,
                cred,
                self._hmac_secret,
                True,
                self._user_verification,
            )
            cmd = Cmd(self.cid, _CMD_CBOR, bytes([_ERR_NONE]) + response_data)
        except Exception:
            cmd = cbor_error(self.cid, _ERR_OPERATION_DENIED)

        await send_cmd(cmd, self.iface)


class Fido2ConfirmNoPin(State):
    def __init__(self, cid: int, iface: io.HID) -> None:
        super().__init__(cid, iface)

    def timeout_ms(self) -> int:
        return _FIDO2_CONFIRM_TIMEOUT_MS

    async def confirm_dialog(self) -> bool:
        text = Text("FIDO2 Verify User", ui.ICON_WRONG, ui.RED)
        text.normal("Unable to verify user.", "Please enable PIN", "protection.")
        return await confirm(text, confirm=None)


class Fido2ConfirmNoCredentials(Fido2ConfirmGetAssertion):
    def __init__(self, cid: int, iface: io.HID, rp_id: str) -> None:
        cred = Fido2Credential()
        cred.rp_id = rp_id
        super().__init__(cid, iface, b"", [cred], {}, user_verification=False)

    async def on_confirm(self) -> None:
        cmd = cbor_error(self.cid, _ERR_NO_CREDENTIALS)
        await send_cmd(cmd, self.iface)

        text = Text("FIDO2 Authenticate", ui.ICON_WRONG, ui.RED)
        text.normal(
            "This device is not", "registered with", self._creds[0].app_name() + "."
        )
        await confirm(text, confirm=None)


class Fido2ConfirmReset(Fido2State):
    def __init__(self, cid: int, iface: io.HID) -> None:
        super().__init__(cid, iface)

    async def confirm_dialog(self) -> bool:
        text = Text("FIDO2 Reset", ui.ICON_CONFIG)
        text.normal("Do you really want to")
        text.bold("erase all credentials?")
        return await confirm(text)

    async def on_confirm(self) -> None:
        erase_resident_credentials()
        cmd = Cmd(self.cid, _CMD_CBOR, bytes([_ERR_NONE]))
        await send_cmd(cmd, self.iface)


class DialogManager:
    def __init__(self, iface: io.HID) -> None:
        self.iface = iface
        self._clear()

    def _clear(self) -> None:
        self.state = None  # type: Optional[State]
        self.deadline = 0
        self.result = _RESULT_NONE
        self.workflow = None  # type: Optional[Coroutine]
        self.keepalive = None  # type: Optional[Coroutine]

    def reset_timeout(self) -> None:
        if self.state is not None:
            self.deadline = utime.ticks_ms() + self.state.timeout_ms()

    def reset(self) -> None:
        if self.workflow is not None:
            loop.close(self.workflow)
        if self.keepalive is not None:
            loop.close(self.keepalive)
        self._clear()

    def get_cid(self) -> int:
        if self.state is None:
            return 0
        return self.state.cid

    def is_busy(self) -> bool:
        if utime.ticks_ms() >= self.deadline:
            self.reset()
        return bool(workflow.tasks or self.workflow)

    def compare(self, state: State) -> bool:
        if self.state != state:
            return False
        if utime.ticks_ms() >= self.deadline:
            self.reset()
            return False
        return True

    def set_state(self, state: State) -> bool:
        if self.is_busy():
            return False

        self.state = state
        self.reset_timeout()
        self.result = _RESULT_NONE
        if state.keepalive_status() is not None:
            self.keepalive = self.keepalive_loop()
            loop.schedule(self.keepalive)
        else:
            self.keepalive = None
        self.workflow = self.dialog_workflow()
        loop.schedule(self.workflow)
        return True

    async def keepalive_loop(self) -> None:
        if not isinstance(self.state, Fido2State):
            return
        while utime.ticks_ms() < self.deadline:
            cmd = cmd_keepalive(self.state.cid, self.state.keepalive_status())
            await send_cmd(cmd, self.iface)
            await loop.sleep(_KEEPALIVE_INTERVAL_MS * 1000)

        self.result = _RESULT_TIMEOUT
        self.reset()

    async def dialog_workflow(self) -> None:
        if self.workflow is None or self.state is None:
            return

        try:
            workflow.on_start(self.workflow)
            if await self.state.confirm_dialog():
                self.result = _RESULT_CONFIRM
            else:
                self.result = _RESULT_DECLINE
        finally:
            if self.keepalive is not None:
                loop.close(self.keepalive)
            self.keepalive = None

            if self.result == _RESULT_CONFIRM:
                await self.state.on_confirm()
            elif self.result == _RESULT_CANCEL:
                await self.state.on_cancel()
            elif self.result == _RESULT_TIMEOUT:
                await self.state.on_timeout()
            else:
                await self.state.on_decline()

            workflow.on_close(self.workflow)
            self.workflow = None


def dispatch_cmd(req: Cmd, dialog_mgr: DialogManager) -> Optional[Cmd]:
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
    elif req.cmd == _CMD_CBOR and _ALLOW_FIDO2:
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
        dialog_mgr.result = _RESULT_CANCEL
        dialog_mgr.reset()
        return None
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

    # parse challenge and rp_id_hash
    chal = req.data[:32]
    cred = U2fCredential()
    cred.rp_id_hash = bytes(req.data[32:])
    cred.generate_key_handle()

    # check equality with last request
    new_state = U2fConfirmRegister(req.cid, dialog_mgr.iface, req.data, cred)
    if not dialog_mgr.compare(new_state):
        if not dialog_mgr.set_state(new_state):
            return msg_error(req.cid, _SW_CONDITIONS_NOT_SATISFIED)
    dialog_mgr.reset_timeout()

    # wait for a button or continue
    if dialog_mgr.result != _RESULT_CONFIRM:
        if __debug__:
            log.info(__name__, "waiting for button")
        return msg_error(req.cid, _SW_CONDITIONS_NOT_SATISFIED)

    # sign the registration challenge and return
    if __debug__:
        log.info(__name__, "signing register")
    buf = msg_register_sign(chal, cred)

    dialog_mgr.reset()

    return Cmd(req.cid, _CMD_MSG, buf)


def msg_register_sign(challenge: bytes, cred: U2fCredential) -> bytes:
    pubkey = nist256p1.publickey(cred.private_key(), False)

    # hash the request data together with keyhandle and pubkey
    dig = hashlib.sha256()
    dig.update(b"\x00")  # uint8_t reserved;
    dig.update(cred.rp_id_hash)  # uint8_t appId[32];
    dig.update(challenge)  # uint8_t chal[32];
    dig.update(cred.id)  # uint8_t keyHandle[64];
    dig.update(pubkey)  # uint8_t pubKey[65];

    # sign the digest and convert to der
    sig = nist256p1.sign(_U2F_ATT_PRIV_KEY, dig.digest(), False)
    sig = der.encode_seq((sig[1:33], sig[33:]))

    # pack to a response
    buf, resp = make_struct(
        resp_cmd_register(len(cred.id), len(_U2F_ATT_CERT), len(sig))
    )
    resp.registerId = _U2F_REGISTER_ID
    utils.memcpy(resp.pubKey, 0, pubkey, 0, len(pubkey))
    resp.keyHandleLen = len(cred.id)
    utils.memcpy(resp.keyHandle, 0, cred.id, 0, len(cred.id))
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
    auth = overlay_struct(req.data, req_cmd_authenticate(khlen))

    cred = Credential.from_bytes(auth.keyHandle, bytes(auth.appId))
    if cred is None:
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
    new_state = U2fConfirmAuthenticate(req.cid, dialog_mgr.iface, req.data, cred)
    if not dialog_mgr.compare(new_state):
        if not dialog_mgr.set_state(new_state):
            return msg_error(req.cid, _SW_CONDITIONS_NOT_SATISFIED)
    dialog_mgr.reset_timeout()

    # wait for a button or continue
    if dialog_mgr.result != _RESULT_CONFIRM:
        if __debug__:
            log.info(__name__, "waiting for button")
        return msg_error(req.cid, _SW_CONDITIONS_NOT_SATISFIED)

    # sign the authentication challenge and return
    if __debug__:
        log.info(__name__, "signing authentication")
    buf = msg_authenticate_sign(auth.chal, auth.appId, cred)

    dialog_mgr.reset()

    return Cmd(req.cid, _CMD_MSG, buf)


def msg_authenticate_sign(
    challenge: bytes, rp_id_hash: bytes, cred: Credential
) -> bytes:
    flags = bytes([_AUTH_FLAG_UP])

    # get next counter
    ctr = cred.next_signature_counter()
    ctrbuf = ustruct.pack(">L", ctr)

    # hash input data together with counter
    dig = hashlib.sha256()
    dig.update(rp_id_hash)  # uint8_t appId[32];
    dig.update(flags)  # uint8_t flags;
    dig.update(ctrbuf)  # uint8_t ctr[4];
    dig.update(challenge)  # uint8_t chal[32];

    # sign the digest and convert to der
    sig = nist256p1.sign(cred.private_key(), dig.digest(), False)
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
    from apps.webauthn.knownapps import knownapps

    if not storage.is_initialized():
        if __debug__:
            log.warning(__name__, "not initialized")
        return cbor_error(req.cid, _ERR_OPERATION_DENIED)

    try:
        param = cbor.decode(req.data[1:])
        rp_id = param[_MAKECRED_CMD_RP]["id"]
        rp_id_hash = hashlib.sha256(rp_id).digest()

        # Prepare the new credential.
        user = param[_MAKECRED_CMD_USER]
        cred = Fido2Credential()
        cred.rp_id = rp_id
        cred.rp_id_hash = rp_id_hash
        cred.rp_name = param[_MAKECRED_CMD_RP].get("name", None)
        cred.user_id = user["id"]
        cred.user_name = user.get("name", None)
        cred.user_display_name = user.get("displayName", None)

        # Check if any of the credential descriptors in the exclude list belong to this authenticator.
        exclude_list = param.get(_MAKECRED_CMD_EXCLUDE_LIST, [])
        for credential_descriptor in exclude_list:
            excl_cred = Credential.from_bytes(credential_descriptor["id"], rp_id_hash)
            if credential_descriptor["type"] == "public-key" and excl_cred is not None:
                # This authenticator is already registered.
                if not dialog_mgr.set_state(
                    Fido2ConfirmExcluded(req.cid, dialog_mgr.iface, cred)
                ):
                    return cmd_error(req.cid, _ERR_CHANNEL_BUSY)
                return None

        # Check that the relying party supports ECDSA P-256 with SHA-256. We don't support any other algorithms.
        pub_key_cred_params = param[_MAKECRED_CMD_PUB_KEY_CRED_PARAMS]
        if ("public-key", _COSE_ALG_ES256) not in (
            (pkcp.get("type", None), pkcp.get("alg", None))
            for pkcp in pub_key_cred_params
        ):
            return cbor_error(req.cid, _ERR_UNSUPPORTED_ALGORITHM)

        # Get options.
        options = param.get(_MAKECRED_CMD_OPTIONS, {})
        resident_key = options.get("rk", False)
        user_verification = options.get("uv", False)

        # Get supported extensions.
        cred.hmac_secret = param.get(_MAKECRED_CMD_EXTENSIONS, {}).get(
            "hmac-secret", False
        )

        client_data_hash = param[_MAKECRED_CMD_CLIENT_DATA_HASH]
    except Exception:
        return cbor_error(req.cid, _ERR_INVALID_CBOR)

    cred.use_sign_count = knownapps.get(rp_id_hash, {}).get("use_sign_count", True)

    # Check data types.
    if (
        not cred.check_data_types()
        or not isinstance(client_data_hash, (bytes, bytearray))
        or not isinstance(resident_key, bool)
        or not isinstance(user_verification, bool)
    ):
        return cbor_error(req.cid, _ERR_INVALID_CBOR)

    # Check options.
    if resident_key and not _ALLOW_RESIDENT_CREDENTIALS:
        return cbor_error(req.cid, _ERR_UNSUPPORTED_OPTION)

    if user_verification and not config.has_pin():
        # User verification requested, but PIN is not enabled.
        state_set = dialog_mgr.set_state(Fido2ConfirmNoPin(req.cid, dialog_mgr.iface))
        if state_set:
            return cbor_error(req.cid, _ERR_UNSUPPORTED_OPTION)
        else:
            return cmd_error(req.cid, _ERR_CHANNEL_BUSY)

    # Check that the pinAuth parameter is absent. Client PIN is not supported.
    if _MAKECRED_CMD_PIN_AUTH in param:
        return cbor_error(req.cid, _ERR_PIN_AUTH_INVALID)

    # Ask user to confirm registration.
    state_set = dialog_mgr.set_state(
        Fido2ConfirmMakeCredential(
            req.cid,
            dialog_mgr.iface,
            client_data_hash,
            cred,
            resident_key,
            user_verification,
        )
    )

    if not state_set:
        return cmd_error(req.cid, _ERR_CHANNEL_BUSY)

    return None


def cbor_make_credential_sign(
    client_data_hash: bytes, cred: Fido2Credential, user_verification: bool
) -> bytes:
    privkey = cred.private_key()
    pubkey = nist256p1.publickey(privkey, False)

    flags = _AUTH_FLAG_UP | _AUTH_FLAG_AT
    if user_verification:
        flags |= _AUTH_FLAG_UV

    # Encode the authenticator data (Credential ID, its public key and extensions).
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

    ctr = cred.next_signature_counter()

    authenticator_data = (
        cred.rp_id_hash
        + bytes([flags])
        + ctr.to_bytes(4, "big")
        + att_cred_data
        + extensions
    )

    # Compute the attestation signature of the authenticator data.
    if _USE_BASIC_ATTESTATION:
        privkey = _U2F_ATT_PRIV_KEY

    dig = hashlib.sha256()
    dig.update(authenticator_data)
    dig.update(client_data_hash)
    sig = nist256p1.sign(privkey, dig.digest(), False)
    sig = der.encode_seq((sig[1:33], sig[33:]))

    # Encode the authenticatorMakeCredential response data.
    attestation_statement = {"alg": _COSE_ALG_ES256, "sig": sig}
    if _USE_BASIC_ATTESTATION:
        attestation_statement["x5c"] = [_U2F_ATT_CERT]

    return cbor.encode(
        {
            _MAKECRED_RESP_FMT: "packed",
            _MAKECRED_RESP_AUTH_DATA: authenticator_data,
            _MAKECRED_RESP_ATT_STMT: attestation_statement,
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
        rp_id_hash = hashlib.sha256(rp_id).digest()

        cred_list = []
        allow_list = param.get(_GETASSERT_CMD_ALLOW_LIST, [])
        if allow_list:
            # Get all credentials from the allow list that belong to this authenticator.
            for credential_descriptor in allow_list:
                if credential_descriptor["type"] != "public-key":
                    continue
                cred = Credential.from_bytes(credential_descriptor["id"], rp_id_hash)
                if cred is not None:
                    if cred.rp_id is None:
                        cred.rp_id = rp_id
                    cred_list.append(cred)
        else:
            # Allow list is empty. Get resident credentials.
            if _ALLOW_RESIDENT_CREDENTIALS:
                cred_list = get_resident_credentials(rp_id_hash)

        # Sort credentials by time of creation.
        cred_list.sort()

        # Check that the pinAuth parameter is absent. Client PIN is not supported.
        if _GETASSERT_CMD_PIN_AUTH in param:
            return cbor_error(req.cid, _ERR_PIN_AUTH_INVALID)

        # Get options.
        options = param.get(_GETASSERT_CMD_OPTIONS, {})
        user_presence = options.get("up", True)
        user_verification = options.get("uv", False)

        # Get supported extensions.
        hmac_secret = param.get(_GETASSERT_CMD_EXTENSIONS, {}).get("hmac-secret", None)

        client_data_hash = param[_GETASSERT_CMD_CLIENT_DATA_HASH]
    except Exception:
        return cbor_error(req.cid, _ERR_INVALID_CBOR)

    # Check data types.
    if (
        not isinstance(hmac_secret, (dict, type(None)))
        or not isinstance(client_data_hash, (bytes, bytearray))
        or not isinstance(user_presence, bool)
        or not isinstance(user_verification, bool)
    ):
        return cbor_error(req.cid, _ERR_INVALID_CBOR)

    # Check options.
    if "rk" in options:
        return cbor_error(req.cid, _ERR_INVALID_OPTION)

    if user_verification and not config.has_pin():
        # User verification requested, but PIN is not enabled.
        state_set = dialog_mgr.set_state(Fido2ConfirmNoPin(req.cid, dialog_mgr.iface))
        if state_set:
            return cbor_error(req.cid, _ERR_UNSUPPORTED_OPTION)
        else:
            return cmd_error(req.cid, _ERR_CHANNEL_BUSY)

    if not cred_list:
        # No credentials. This authenticator is not registered.
        if user_presence:
            state_set = dialog_mgr.set_state(
                Fido2ConfirmNoCredentials(req.cid, dialog_mgr.iface, rp_id)
            )
        else:
            return cbor_error(req.cid, _ERR_NO_CREDENTIALS)
    elif not user_presence and not user_verification:
        # Silent authentication.
        try:
            response_data = cbor_get_assertion_sign(
                client_data_hash,
                rp_id_hash,
                cred_list[0],
                hmac_secret,
                user_presence,
                user_verification,
            )
            return Cmd(req.cid, _CMD_CBOR, bytes([_ERR_NONE]) + response_data)
        except Exception:
            return cbor_error(req.cid, _ERR_OPERATION_DENIED)
    else:
        # Ask user to confirm one of the credentials.
        state_set = dialog_mgr.set_state(
            Fido2ConfirmGetAssertion(
                req.cid,
                dialog_mgr.iface,
                client_data_hash,
                cred_list,
                hmac_secret,
                user_verification,
            )
        )

    if not state_set:
        return cmd_error(req.cid, _ERR_CHANNEL_BUSY)

    return None


def cbor_get_assertion_hmac_secret(
    cred: Credential, hmac_secret: dict
) -> Optional[bytes]:
    key_agreement = hmac_secret[1]  # The public key of platform key agreement key.
    salt_enc = hmac_secret[2]  # The encrypted salt.
    salt_auth = hmac_secret[3]  # The HMAC of the encrypted salt.

    x = key_agreement[_COSE_X_COORD_KEY]
    y = key_agreement[_COSE_Y_COORD_KEY]
    if (
        key_agreement[_COSE_ALG_KEY] != _COSE_ALG_ES256
        or key_agreement[_COSE_KEY_TYPE_KEY] != _COSE_KEY_TYPE_EC2
        or key_agreement[_COSE_CURVE_KEY] != _COSE_CURVE_P256
        or len(x) != 32
        or len(y) != 32
        or len(salt_auth) != 16
        or len(salt_enc) not in (32, 64)
    ):
        return None

    # Compute the ECDH shared secret.
    ecdh_result = nist256p1.multiply(_KEY_AGREEMENT_PRIVKEY, b"\04" + x + y)
    shared_secret = hashlib.sha256(ecdh_result[1:33]).digest()

    # Check the authentication tag and decrypt the salt.
    tag = hmac.Hmac(shared_secret, salt_enc, hashlib.sha256).digest()[:16]
    if not utils.consteq(tag, salt_auth):
        return None
    salt = aes(aes.CBC, shared_secret).decrypt(salt_enc)

    # Get cred_random - a constant symmetric key associated with the credential.
    cred_random = cred.hmac_secret_key()
    if cred_random is None:
        # The credential does not have the hmac-secret extension enabled.
        return None

    # Compute the hmac-secret output.
    output = hmac.Hmac(cred_random, salt[:32], hashlib.sha256).digest()
    if len(salt) == 64:
        output += hmac.Hmac(cred_random, salt[32:], hashlib.sha256).digest()

    # Encrypt the hmac-secret output.
    return aes(aes.CBC, shared_secret).encrypt(output)


def cbor_get_assertion_sign(
    client_data_hash: bytes,
    rp_id_hash: bytes,
    cred: Credential,
    hmac_secret: Optional[dict],
    user_presence: bool,
    user_verification: bool,
) -> bytes:
    # Process extensions
    extensions = {}

    # Spec deviation: Do not reveal hmac-secret during silent authentication.
    if hmac_secret and user_presence:
        encrypted_output = cbor_get_assertion_hmac_secret(cred, hmac_secret)
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
    dig = hashlib.sha256()
    dig.update(authenticator_data)
    dig.update(client_data_hash)
    if user_presence:
        privkey = cred.private_key()
    else:
        # Spec deviation: Use a bogus key during silent authentication.
        privkey = _BOGUS_PRIV_KEY
    sig = nist256p1.sign(privkey, dig.digest(), False)
    sig = der.encode_seq((sig[1:33], sig[33:]))

    # Encode the authenticatorGetAssertion response data.
    response = {
        _GETASSERT_RESP_CREDENTIAL: {"type": "public-key", "id": cred.id},
        _GETASSERT_RESP_AUTH_DATA: authenticator_data,
        _GETASSERT_RESP_SIGNATURE: sig,
    }

    if user_presence and cred.user_id is not None:
        response[_GETASSERT_RESP_USER] = {"id": cred.user_id}

    return cbor.encode(response)


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

    # We only support the get key agreement command which is required for the hmac-secret extension.
    if subcommand != _CLIENTPIN_SUBCMD_GET_KEY_AGREEMENT:
        return cbor_error(req.cid, _ERR_UNSUPPORTED_OPTION)

    # Encode the public key of the authenticator key agreement key.
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

    if not dialog_mgr.set_state(Fido2ConfirmReset(req.cid, dialog_mgr.iface)):
        return cmd_error(req.cid, _ERR_CHANNEL_BUSY)
    return None


def cmd_keepalive(cid: int, status: int) -> Cmd:
    return Cmd(cid, _CMD_KEEPALIVE, bytes([status]))
