import json
import logging
import os
import typing as t

from .channel_data import ChannelData
from .protocol_and_channel import ProtocolAndChannel

LOG = logging.getLogger(__name__)

FILE_PATH = "channel_data.json"


def load_stored_channels() -> t.List[ChannelData]:
    dicts = read_all_channels()
    return [dict_to_channel_data(d) for d in dicts]


def channel_to_str(channel: ProtocolAndChannel) -> str:
    return json.dumps(channel.get_channel_data().to_dict())


def str_to_channel_data(channel_data: str) -> ChannelData:
    return dict_to_channel_data(json.loads(channel_data))


def dict_to_channel_data(dict: t.Dict) -> ChannelData:
    return ChannelData(
        protocol_version=dict["protocol_version"],
        transport_path=dict["transport_path"],
        channel_id=dict["channel_id"],
        key_request=bytes.fromhex(dict["key_request"]),
        key_response=bytes.fromhex(dict["key_response"]),
        nonce_request=dict["nonce_request"],
        nonce_response=dict["nonce_response"],
        sync_bit_send=dict["sync_bit_send"],
        sync_bit_receive=dict["sync_bit_receive"],
    )


def ensure_file_exists() -> None:
    LOG.debug("checking if file %s exists", FILE_PATH)
    if not os.path.exists(FILE_PATH):
        LOG.debug("File %s does not exist. Creating a new one.", FILE_PATH)
        with open(FILE_PATH, "w") as f:
            json.dump([], f)


def clear_stored_channels() -> None:
    LOG.debug("Clearing contents of %s - to empty list.", FILE_PATH)
    with open(FILE_PATH, "w") as f:
        json.dump([], f)


def read_all_channels() -> t.List:
    ensure_file_exists()
    with open(FILE_PATH, "r") as f:
        return json.load(f)


def save_all_channels(channels: t.List[t.Dict]) -> None:
    LOG.debug("saving all channels")
    with open(FILE_PATH, "w") as f:
        json.dump(channels, f, indent=4)


def save_channel(new_channel: ProtocolAndChannel):
    LOG.debug("save channel")
    channels = read_all_channels()
    transport_path = new_channel.transport.get_path()

    # If channel is modified: replace the old by the new
    for i, channel in enumerate(channels):
        if channel["transport_path"] == transport_path:
            LOG.debug("Modified channel entry for %s", transport_path)
            channels[i] = new_channel.get_channel_data().to_dict()
            save_all_channels(channels)
            return

    # Else: add a new channel entry
    LOG.debug("Created a new channel entry on path %s", transport_path)
    channels.append(new_channel.get_channel_data().to_dict())
    save_all_channels(channels)


def remove_channel(transport_path: str) -> None:
    LOG.debug(
        "Removing channel with path %s from the channel database.",
        transport_path,
    )
    channels = read_all_channels()
    remaining_channels = [
        ch for ch in channels if ch["transport_path"] != transport_path
    ]
    save_all_channels(remaining_channels)
