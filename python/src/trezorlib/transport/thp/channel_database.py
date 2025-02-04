from __future__ import annotations

import json
import logging
import os
import typing as t

from .channel_data import ChannelData
from .protocol_and_channel import Channel

LOG = logging.getLogger(__name__)

db: "ChannelDatabase | None" = None


def get_channel_db() -> ChannelDatabase:
    if db is None:
        set_channel_database(should_not_store=True)
    assert db is not None
    return db


class ChannelDatabase:

    def load_stored_channels(self) -> t.List[ChannelData]: ...
    def clear_stored_channels(self) -> None: ...

    def save_channel(self, new_channel: Channel): ...

    def remove_channel(self, transport_path: str) -> None: ...


class DummyChannelDatabase(ChannelDatabase):

    def load_stored_channels(self) -> t.List[ChannelData]:
        return []

    def clear_stored_channels(self) -> None:
        pass

    def save_channel(self, new_channel: Channel):
        pass

    def remove_channel(self, transport_path: str) -> None:
        pass


class JsonChannelDatabase(ChannelDatabase):
    def __init__(self, data_path: str) -> None:
        self.data_path = data_path
        super().__init__()

    def load_stored_channels(self) -> t.List[ChannelData]:
        dicts = self._read_all_channels()
        return [dict_to_channel_data(d) for d in dicts]

    def clear_stored_channels(self) -> None:
        LOG.debug("Clearing contents of %s", self.data_path)
        with open(self.data_path, "w") as f:
            json.dump([], f)
        try:
            os.remove(self.data_path)
        except Exception as e:
            LOG.exception("Failed to delete %s (%s)", self.data_path, str(type(e)))

    def _read_all_channels(self) -> t.List:
        ensure_file_exists(self.data_path)
        with open(self.data_path, "r") as f:
            return json.load(f)

    def _save_all_channels(self, channels: t.List[t.Dict]) -> None:
        LOG.debug("saving all channels")
        with open(self.data_path, "w") as f:
            json.dump(channels, f, indent=4)

    def save_channel(self, new_channel: Channel):

        LOG.debug("save channel")
        channels = self._read_all_channels()
        transport_path = new_channel.transport.get_path()

        # If the channel is found in database: replace the old entry by the new
        for i, channel in enumerate(channels):
            if channel["transport_path"] == transport_path:
                LOG.debug("Modified channel entry for %s", transport_path)
                channels[i] = new_channel.get_channel_data().to_dict()
                self._save_all_channels(channels)
                return

        # Channel was not found: add a new channel entry
        LOG.debug("Created a new channel entry on path %s", transport_path)
        channels.append(new_channel.get_channel_data().to_dict())
        self._save_all_channels(channels)

    def remove_channel(self, transport_path: str) -> None:
        LOG.debug(
            "Removing channel with path %s from the channel database.",
            transport_path,
        )
        channels = self._read_all_channels()
        remaining_channels = [
            ch for ch in channels if ch["transport_path"] != transport_path
        ]
        self._save_all_channels(remaining_channels)


def dict_to_channel_data(dict: t.Dict) -> ChannelData:
    return ChannelData(
        protocol_version_major=dict["protocol_version_minor"],
        protocol_version_minor=dict["protocol_version_major"],
        transport_path=dict["transport_path"],
        channel_id=dict["channel_id"],
        key_request=bytes.fromhex(dict["key_request"]),
        key_response=bytes.fromhex(dict["key_response"]),
        nonce_request=dict["nonce_request"],
        nonce_response=dict["nonce_response"],
        sync_bit_send=dict["sync_bit_send"],
        sync_bit_receive=dict["sync_bit_receive"],
        handshake_hash=bytes.fromhex(dict["handshake_hash"]),
    )


def ensure_file_exists(file_path: str) -> None:
    LOG.debug("checking if file %s exists", file_path)
    if not os.path.exists(file_path):
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        LOG.debug("File %s does not exist. Creating a new one.", file_path)
        with open(file_path, "w") as f:
            json.dump([], f)


def set_channel_database(should_not_store: bool):
    global db
    if should_not_store:
        db = DummyChannelDatabase()
    else:
        from platformdirs import user_cache_dir

        APP_NAME = "@trezor"  # TODO
        DATA_PATH = os.path.join(user_cache_dir(appname=APP_NAME), "channel_data.json")

        db = JsonChannelDatabase(DATA_PATH)
