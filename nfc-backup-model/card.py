import logging
import pickle
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum

import commands
from apdu import ApduRequest, ApduResponse
from card_inner import CardInner, Pin
from commands import OK
from noise import ResponderXXPsk3, TransportState

from crypto import PrivateKey, PublicKey, random_bytes

logger = logging.getLogger(__name__)


class File(Enum):
    NONE = 0
    METADATA = 1
    ENCRYPTED_SEED = 2
    PIN_COUNTER = 3
    SUCCESSFUL_LOG = 4
    UNSUCCESSFUL_LOG = 5


class UnexpectedRequest(Exception):
    pass


# TODO: Decide whether you can switch to another application if the application is
# already selected


@dataclass
class State:
    pass


@dataclass
class RawState(State):
    def handle_raw_request(
        self, card: CardInner, static_key: PrivateKey, raw_request: bytes
    ) -> tuple[bytes, State]:
        raise NotImplementedError


@dataclass
class ApduState(State):
    def handle_apdu_request(
        self, card: CardInner, static_key: bytes, apdu_request: ApduRequest
    ) -> tuple[ApduResponse, State]:
        raise NotImplementedError


@dataclass
class IdleState(ApduState):
    def handle_apdu_request(
        self, card: CardInner, static_key: bytes, apdu_request: ApduRequest
    ) -> tuple[ApduResponse, State]:
        match apdu_request:
            case ApduRequest(
                command=commands.SELECT_APPLICATION,
                data=commands.TREZOR_APPLICATION_AID,
            ):
                logging.debug("command=SELECT_APPLICATION, data=TREZOR_APPLICATION_AID")
                return (
                    ApduResponse.from_status(OK),
                    TrezorNonceState(),
                )
            case _:
                raise UnexpectedRequest


@dataclass
class TrezorNonceState(RawState):
    def handle_raw_request(
        self, card: CardInner, static_key: PrivateKey, raw_request: bytes
    ) -> tuple[bytes, State]:
        remote_psk = raw_request  # TODO: Use error-correcting code in the request
        logging.debug(f'remote_psk=bytes.from_hex("{remote_psk.hex()}")')
        if len(remote_psk) != commands.READER_PSK_LENGTH:
            raise UnexpectedRequest
        psk = random_bytes(commands.CARD_PSK_LENGTH)
        logging.debug(f'psk=bytes.from_hex("{psk.hex()}")')
        responder = ResponderXXPsk3(static_key, b"", remote_psk + psk)
        return (
            psk,
            TrezorHandshakeState1(
                responder=responder,
            ),
        )


@dataclass
class TrezorHandshakeState1(ApduState):
    responder: ResponderXXPsk3

    def handle_apdu_request(
        self, card: CardInner, static_key: bytes, apdu_request: ApduRequest
    ) -> tuple[ApduResponse, State]:
        match apdu_request:
            case ApduRequest(command=commands.TREZOR_HANDSHAKE_MESSAGE_1, data=data):
                logging.debug("command=TREZOR_HANDSHAKE_MESSAGE_1")
                self.responder.handle_request1(data)
                response = self.responder.create_response1()
                return (
                    ApduResponse.from_status(OK, response),
                    TrezorHandshakeState2(
                        responder=self.responder,
                    ),
                )
            case _:
                raise UnexpectedRequest


@dataclass
class TrezorHandshakeState2(ApduState):
    responder: ResponderXXPsk3

    def handle_apdu_request(
        self, card: CardInner, static_key: bytes, apdu_request: ApduRequest
    ) -> tuple[ApduResponse, State]:
        match apdu_request:
            case ApduRequest(command=commands.TREZOR_HANDSHAKE_MESSAGE_2, data=data):
                logging.debug("command=TREZOR_HANDSHAKE_MESSAGE_2")
                self.responder.handle_request2(data)
                assert self.responder.remote_static_public is not None
                remote_static_key = PublicKey(self.responder.remote_static_public)
                transport_state = self.responder.get_transport_state()
                response = transport_state.send_cipher_state.encrypt_with_ad(b"", b"")
                powered_card = CardInner.PoweredInnerCard(
                    card.storage, remote_static_key
                )
                return (
                    ApduResponse.from_status(OK, response),
                    TrezorSecureChannelState(
                        responder=self.responder,
                        remote_static_key=remote_static_key,
                        transport_state=transport_state,
                        selected_file=File.NONE,
                        powered_card=powered_card,
                    ),
                )
            case _:
                raise UnexpectedRequest


@dataclass
class TrezorSecureChannelState(ApduState):
    responder: ResponderXXPsk3
    remote_static_key: PublicKey
    transport_state: TransportState
    selected_file: File
    powered_card: CardInner.PoweredInnerCard

    def handle_apdu_request(
        self, card: CardInner, static_key: bytes, apdu_request: ApduRequest
    ) -> tuple[ApduResponse, State]:
        data = self.transport_state.receive_cipher_state.decrypt_with_ad(
            apdu_request.get_header(), apdu_request.data
        )

        match apdu_request.header:
            case commands.TREZOR_AUTHENTICATE:
                logging.debug("command=TREZOR_AUTHENTICATE")
                # TODO: Decide how to encode PIN and note
                pin, note = pickle.loads(data)
                self.powered_card.authenticate(pin, note)
                response_data = b""
            case commands.TREZOR_SET_PIN:
                logging.debug("command=TREZOR_SET_PIN")
                self.powered_card.set_pin(Pin(data))
                response_data = b""
            case commands.TREZOR_WIPE:
                logging.debug("command=TREZOR_WIPE")
                self.powered_card.wipe()
                response_data = b""
            case commands.SELECT_FILE:
                logging.debug("command=SELECT_FILE")
                match data:
                    case commands.PIN_COUNTER_FILE:
                        logging.debug("selected_file=PIN_COUNTER")
                        self.selected_file = File.PIN_COUNTER
                    case commands.SEED_METADATA_FILE:
                        logging.debug("selected_file=METADATA")
                        self.selected_file = File.METADATA
                    case commands.SEED_FILE:
                        logging.debug("selected_file=ENCRYPTED_SEED")
                        self.selected_file = File.ENCRYPTED_SEED
                    case commands.SUCCESSFUL_LOG_FILE:
                        logging.debug("selected_file=SUCCESSFUL_LOG")
                        self.selected_file = File.SUCCESSFUL_LOG
                    case commands.UNSUCCESSFUL_LOG_FILE:
                        logging.debug("selected_file=UNSUCCESSFUL_LOG")
                        self.selected_file = File.UNSUCCESSFUL_LOG
                    case _:
                        raise UnexpectedRequest
                response_data = b""
            case commands.READ_BINARY:
                logging.debug("command=READ_BINARY")
                match self.selected_file:
                    case File.METADATA:
                        response_data = self.powered_card.read_metadata()
                    case File.ENCRYPTED_SEED:
                        response_data = self.powered_card.read_seed()
                    case File.PIN_COUNTER:
                        response_data = self.powered_card.read_pin_counter().to_bytes(
                            4, "big"
                        )
                    case File.SUCCESSFUL_LOG:
                        # TODO: Decide how to encode the log record
                        response_data = pickle.dumps(
                            self.powered_card.read_successful_access_log_record()
                        )
                    case File.UNSUCCESSFUL_LOG:
                        # TODO: Decide how to encode the log records
                        response_data = pickle.dumps(
                            self.powered_card.read_unsuccessful_access_log_records()
                        )
                    case _:
                        raise UnexpectedRequest
            case commands.WRITE_BINARY:
                logging.debug("command=WRITE_BINARY")
                match self.selected_file:
                    case File.METADATA:
                        self.powered_card.write_metadata(data)
                        response_data = b""
                    case File.ENCRYPTED_SEED:
                        self.powered_card.write_seed(data)
                        response_data = b""
                    case _:
                        raise UnexpectedRequest
            case _:
                raise UnexpectedRequest

        return (
            ApduResponse.from_status(
                OK,
                self.transport_state.send_cipher_state.encrypt_with_ad(
                    b"", response_data
                ),
            ),
            self,
        )


class Card:
    def __init__(self, static_key: PrivateKey) -> None:
        self.card = CardInner()
        self.static_key = static_key

    @contextmanager
    def powered(self) -> Iterator["Card.PoweredCard"]:
        yield Card.PoweredCard(self.card, self.static_key)

    class PoweredCard:
        def __init__(self, card: CardInner, static_key: PrivateKey) -> None:
            self.card = card
            self.static_key = static_key
            self.state: State = IdleState()

        def handle_request(self, request: bytes) -> bytes:
            logger.info("Card.PoweredCard.handle_request()")
            logger.debug(f'request=bytes.fromhex("{request.hex()}")')

            match self.state:
                case ApduState():
                    apdu = ApduRequest.from_bytes(request)
                    logger.debug(f"apdu={apdu}")
                    apdu_response, state = self.state.handle_apdu_request(
                        self.card, self.static_key, apdu
                    )
                    self.state = state
                    logger.debug(f"state={self.state}")
                    logger.debug(f"apdu_response={apdu_response}")
                    response = apdu_response.to_bytes()
                    logger.debug(f'response=bytes.fromhex("{response.hex()}")')
                    return response
                case RawState():
                    response, state = self.state.handle_raw_request(
                        self.card, self.static_key, request
                    )
                    logger.debug(f'response=bytes.fromhex("{response.hex()}")')
                    self.state = state
                    logger.debug(f"state={self.state}")
                    return response
                case _:
                    raise Exception
