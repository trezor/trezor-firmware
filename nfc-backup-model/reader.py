import pickle
from collections.abc import Iterator
from contextlib import contextmanager

import commands
from apdu import ApduHeader, ApduRequest, ApduResponse
from card import Card
from card_inner import LogRecord, Pin, Timestamp
from commands import OK
from noise import InitiatorXXPsk3, TransportState

from crypto import PrivateKey, public_key, random_bytes


class Reader:
    def __init__(
        self, powered_card: Card.PoweredCard, reader_private: PrivateKey
    ) -> None:
        self._powered_card = powered_card
        self.static_public = public_key(reader_private)
        self._reader_private = reader_private
        self._transport_state: TransportState | None = None

    def connect(self) -> None:
        select_resp = ApduResponse.from_bytes(
            self._powered_card.handle_request(
                ApduRequest.from_header(
                    commands.SELECT_APPLICATION, commands.TREZOR_APPLICATION_AID
                ).to_bytes()
            )
        )
        assert select_resp.status == OK

        reader_psk = random_bytes(commands.READER_PSK_LENGTH)
        card_psk = self._powered_card.handle_request(reader_psk)
        psk = reader_psk + card_psk

        initiator = InitiatorXXPsk3(self._reader_private, b"", psk)

        hs1_resp = ApduResponse.from_bytes(
            self._powered_card.handle_request(
                ApduRequest.from_header(
                    commands.TREZOR_HANDSHAKE_MESSAGE_1, initiator.create_request1()
                ).to_bytes()
            )
        )
        assert hs1_resp.status == OK
        initiator.handle_response1(hs1_resp.response)

        hs2_resp = ApduResponse.from_bytes(
            self._powered_card.handle_request(
                ApduRequest.from_header(
                    commands.TREZOR_HANDSHAKE_MESSAGE_2, initiator.create_request2()
                ).to_bytes()
            )
        )
        assert hs2_resp.status == OK

        self._transport_state = initiator.get_transport_state()
        self._transport_state.receive_cipher_state.decrypt_with_ad(
            b"", hs2_resp.response
        )

    def _transcieve_encrypted(self, header: ApduHeader, plaintext: bytes) -> bytes:
        assert self._transport_state is not None
        header_bytes = bytes([header.cla, header.ins, header.p1, header.p2])
        encrypted = self._transport_state.send_cipher_state.encrypt_with_ad(
            header_bytes, plaintext
        )
        resp = ApduResponse.from_bytes(
            self._powered_card.handle_request(
                ApduRequest.from_header(header, encrypted).to_bytes()
            )
        )
        assert resp.status == OK
        return self._transport_state.receive_cipher_state.decrypt_with_ad(
            b"", resp.response
        )

    def _select_file(self, file_id: bytes) -> None:
        self._transcieve_encrypted(commands.SELECT_FILE, file_id)

    def _read_binary(self) -> bytes:
        return self._transcieve_encrypted(commands.READ_BINARY, b"")

    def _write_binary(self, data: bytes) -> None:
        self._transcieve_encrypted(commands.WRITE_BINARY, data)

    def authenticate(self, pin: Pin, note: bytes) -> bytes:
        return self._transcieve_encrypted(
            commands.TREZOR_AUTHENTICATE, pickle.dumps((pin, note))
        )

    def set_pin(self, pin: Pin) -> bytes:
        return self._transcieve_encrypted(commands.TREZOR_SET_PIN, bytes(pin))

    def wipe(self) -> None:
        self._transcieve_encrypted(commands.TREZOR_WIPE, b"")

    def read_metadata(self) -> bytes:
        self._select_file(commands.SEED_METADATA_FILE)
        return self._read_binary()

    def read_pin_counter(self) -> int:
        self._select_file(commands.PIN_COUNTER_FILE)
        return int.from_bytes(self._read_binary(), "big")

    def read_successful_access_log_record(self) -> LogRecord | None:
        self._select_file(commands.SUCCESSFUL_LOG_FILE)
        result: LogRecord | None = pickle.loads(self._read_binary())
        return result

    def read_unsuccessful_access_log_records(self) -> list[LogRecord | None]:
        self._select_file(commands.UNSUCCESSFUL_LOG_FILE)
        result: list[LogRecord | None] = pickle.loads(self._read_binary())
        return result

    def read_seed(self) -> bytes:
        self._select_file(commands.SEED_FILE)
        return self._read_binary()

    def write_metadata(self, data: bytes) -> None:
        self._select_file(commands.SEED_METADATA_FILE)
        self._write_binary(data)

    def check_integrity(self) -> bool:
        result = self._transcieve_encrypted(commands.TREZOR_CHECK_INTEGRITY, b"")
        return bool(result[0])

    def refresh_memory(self, timestamp: Timestamp) -> None:
        self._transcieve_encrypted(commands.TREZOR_REFRESH_MEMORY, timestamp)

    def read_last_refresh_timestamp(self) -> Timestamp:
        self._select_file(commands.LAST_REFRESH_TIMESTAMP_FILE)
        return Timestamp(self._read_binary())

    def read_flash_bit_error_count(self) -> int:
        self._select_file(commands.FLASH_BIT_ERROR_COUNT_FILE)
        return int.from_bytes(self._read_binary(), "big")

    def write_seed(self, data: bytes) -> None:
        self._select_file(commands.SEED_FILE)
        self._write_binary(data)


@contextmanager
def session(card: Card, reader_private: PrivateKey) -> Iterator["Reader"]:
    with card.powered() as powered_card:
        reader = Reader(powered_card, reader_private)
        reader.connect()
        yield reader
